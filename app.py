from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from AgentPrincipal.chat import chat
from typing import Optional
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator
from geo_service import get_geo_service
from orchestrateur import OrchestratorAgent
from chat import get_orchestrateur
from session_memory import get_active_circuit, get_profile

# Set seed for consistent language detection
DetectorFactory.seed = 0

# Initialize translator

app = FastAPI(title="Dourbia Chatbot API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store session contexts
sessions = {}


# Translation utility functions


def detect_language(text: str) -> str:
    """Detect the language of the input text"""
    try:
        return detect(text)
    except Exception as e:
        print(f"[Dourbia] Language detection ERROR: {e}")
        return "fr"


def translate_to_french(text: str, source_lang: str) -> str:
    """Translate text to French"""
    if source_lang == "fr":
        return text
    try:
        return GoogleTranslator(source=source_lang, target="fr").translate(text)
    except Exception as e:
        print(f"[Dourbia] Translation ERROR (to_fr): {e}")
        return text


def translate_from_french(text: str, target_lang: str) -> str:
    """Translate text from French to target language"""
    if target_lang == "fr":
        return text
    try:
        return GoogleTranslator(source="fr", target=target_lang).translate(text)
    except Exception as e:
        print(f"[Dourbia] Translation ERROR (from_fr): {e}")
        return text


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    detected_language: str


class LocationRequest(BaseModel):
    session_id: str
    lat: float
    lon: float
    langue: Optional[str] = "FR"


class LocationResponse(BaseModel):
    triggered: bool  # True si un monument est détecté
    monument_id: Optional[str] = None
    nom: Optional[str] = None
    distance_m: Optional[float] = None
    message_aziz: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str

session_languages = {}
session_announced: dict[str, set] = {}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        message = request.message
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        session_id = request.session_id or str(uuid.uuid4())
        if session_id not in sessions:
            sessions[session_id] = True
        
        if session_id in session_languages:
            detected_language = session_languages[session_id]
        else:
            
            if len(message.split()) >= 4:
                 detected_language = detect_language(message)
            else:
                detected_language = "fr"  # fallback par défaut
            session_languages[session_id] = detected_language

        print(f"[Dourbia] Detected language: {detected_language}")

        message_fr = translate_to_french(message, detected_language)
        print(f"[Dourbia] Original message: {message}")
        print(f"[Dourbia] Translated to FR: {message_fr}")

        response_fr = await chat(session_id, message_fr)

        response = translate_from_french(response_fr, detected_language)
        print(f"[Dourbia] Response in FR: {response_fr}")
        print(f"[Dourbia] Response translated to {detected_language}: {response}")

        return ChatResponse(
            response=response,
            session_id=session_id,
            detected_language=detected_language,
        )
    except Exception as e:
        print(f"[Dourbia] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions", response_model=SessionResponse)
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = True
    return SessionResponse(session_id=session_id)


@app.post("/api/location", response_model=LocationResponse)
async def location_endpoint(request: LocationRequest):
    """
    Endpoint appelé par le frontend toutes les 30s en mode guide terrain.

    - Reçoit la position GPS de l'utilisateur
    - Détecte les monuments dans un rayon de 150m
    - Si un nouveau monument est trouvé (pas encore annoncé cette session)
      → retourne triggered=True avec le message qu'Aziz va prononcer
    - Sinon → triggered=False (le frontend ne fait rien)

    Anti-spam : chaque monument n'est annoncé qu'une seule fois par session.
    """
    try:
        session_id = request.session_id
        lat = request.lat
        lon = request.lon
        langue = (request.langue or "FR").upper()

        # Récupère ou crée le set des monuments déjà annoncés
        if session_id not in session_announced:
            session_announced[session_id] = set()
        already_announced = session_announced[session_id]

        # Détection monuments proches
        geo = get_geo_service()
        circuit_actif = get_active_circuit(session_id)

        if circuit_actif:
            
            nearby = await geo.get_nearby_monuments_for_circuit(
               lat=lat, lon=lon, circuit_id=circuit_actif, langue=langue, rayon_override_m=150,
           )
        else:
         # Pas de circuit choisi → pas de suggestion proactive (mode narrateur pur)
           nearby = []

        if not nearby:
            return LocationResponse(triggered=False)

        # Prend le monument le plus proche non encore annoncé
        nouveau = None
        for monument in nearby:
            if monument["id"] not in already_announced:
                nouveau = monument
                break

        if not nouveau:
            # Tous les monuments proches ont déjà été annoncés
            return LocationResponse(triggered=False)

        # Marquer comme annoncé
        already_announced.add(nouveau["id"])

        # Synchroniser avec l'orchestrateur : pose monument_en_attente
        # pour que la prochaine réponse "oui" de l'utilisateur déclenche
        # la présentation narrative complète (_handle_terrain_question)
        orchestrateur = get_orchestrateur()
        await orchestrateur.handle_proximity_trigger(
            user_id=session_id,
            monument_id=nouveau["id"],
            monument_nom=nouveau["nom"],
            langue=langue,
        )

        # Construire le message qu'Aziz va prononcer
        message_aziz = _build_proximity_message(nouveau, langue)

        return LocationResponse(
            triggered=True,
            monument_id=nouveau["id"],
            nom=nouveau["nom"],
            distance_m=nouveau["distance_m"],
            message_aziz=message_aziz,
        )

    except Exception as e:
        print(f"[Dourbia] Erreur /api/location : {e}")
        return LocationResponse(triggered=False)


def _build_proximity_message(monument: dict, langue: str) -> str:
    """
    Génère le message de proximité qu'Aziz prononce quand un monument est détecté.
    Multilingue. Simple et direct — pas de LLM pour cette notification.
    """
    nom = monument["nom"]
    distance = int(monument["distance_m"])
    duree = monument.get("duree_visite_min", 0)
    statut = monument.get("statut", "").lower()

    # Alerte statut fermé
    ferme = "fermé" in statut or "ferme" in statut or "closed" in statut.lower()

    if langue == "AR":
        msg = f"🗺️ أنت الآن بالقرب من **{nom}** (على بُعد {distance} متر)."
        if ferme:
            msg += "\n⚠️ المعلم مغلق حالياً."
        else:
            if duree:
                msg += f"\n⏱️ مدة الزيارة المقترحة: {duree} دقيقة."
            msg += "\n\nهل تريدني أن أحكي لك تاريخ هذا المكان؟"

    elif langue == "EN":
        msg = f"🗺️ You are now near **{nom}** ({distance}m away)."
        if ferme:
            msg += "\n⚠️ This site is currently closed."
        else:
            if duree:
                msg += f"\n⏱️ Suggested visit time: {duree} minutes."
            msg += "\n\nWould you like me to tell you about the history of this place?"

    else:  # FR + IT + DE → fallback FR
        msg = f"🗺️ Je remarque que vous êtes près de **{nom}** (à {distance}m)."
        if ferme:
            msg += "\n⚠️ Ce site est actuellement fermé."
        else:
            if duree:
                msg += f"\n⏱️ Durée de visite conseillée : {duree} minutes."
            msg += "\n\nSouhaitez-vous que je vous raconte l'histoire de ce lieu ?"

    return msg


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Dourbia Chatbot API"}


@app.get("/api/guide-status/{session_id}")
async def guide_status(session_id: str):
    """Le frontend poll ceci après chaque réponse chat pour savoir s'il doit démarrer le GPS."""
    profil = get_profile(session_id)
    return {
        "mode_guide_actif": profil.get("mode_guide_actif", False),
        "circuit_id": profil.get("circuit_confirme_id"),
        "circuit_nom": profil.get("circuit_confirme_nom"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
