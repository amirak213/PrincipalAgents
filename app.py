import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "AgentPrincipal"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uuid
from AgentPrincipal.chat import chat
from typing import Optional, List, Any
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator
from AgentPrincipal.geo_service import get_geo_service
from AgentPrincipal.orchestrateur import OrchestratorAgent
from AgentPrincipal.chat import get_orchestrateur
from AgentPrincipal.session_memory import get_active_circuit, get_profile
from circuit_engine import (
    recommend_circuit,
    load_circuit_data,
    CircuitProfil,
    MONUMENTS_CACHE,
)
import asyncio
from AgentPrincipal.wizard_state_machine import (
    WizardState,
    WizardStore,
    question_for_state,
)
from AgentPrincipal.redis_client import get_redis

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


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = None
    action: Optional[dict] = None


from typing import List, Optional

class SourceItem(BaseModel):
    source_type: str
    source_id: Optional[int] = None
    title: Optional[str] = None
    score: Optional[float] = None
    url: Optional[str] = None
    provider: Optional[str] = None

class MemoryContext(BaseModel):
    preferred_language: str
    interests: List[str]
    available_time_minutes: Optional[int] = None
    mobility_mode: Optional[str] = None
    last_mentioned_monuments: List[str]
    primary_site_id: Optional[int] = None
    primary_site_name: Optional[str] = None
    last_substantive_user_message: Optional[str] = None

class LatencyDebug(BaseModel):
    memory_retrieval_ms: Optional[float] = None
    retrieval_ms: Optional[float] = None
    prompt_construction_ms: Optional[float] = None
    llm_generation_ms: Optional[float] = None
    memory_update_ms: Optional[float] = None
    web_search_ms: Optional[float] = None

class WizardOption(BaseModel):
    value: str
    label: str
    meta: Optional[dict] = None


class WizardUI(BaseModel):
    state: str
    question: str
    input_type: str  # "single_select" | "multi_select" | "budget_form" | "date_form" | "confirm"
    options: List[WizardOption] = Field(default_factory=list)
    has_more: bool = False  # utilisé par place_selection pour signaler "voir plus"
    budget_ok: Optional[bool] = None  # renseigné uniquement pour CIRCUIT_REVIEW
    budget_warning: Optional[str] = None  # message d'alerte si budget_ok=False


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: List[SourceItem] = Field(default_factory=list)
    memory_context: MemoryContext
    suggested_actions: List[str] = Field(default_factory=list)
    latency_ms: Optional[float] = None
    latency_debug: Optional[LatencyDebug] = None
    wizard_ui: Optional[WizardUI] = None

# --- Modèles de Requête / Réponse Circuits ---
class CircuitPreferences(BaseModel):
    epoques: List[str]
    fonctions: List[str]
    must_visit: List[str]
    avoid: List[str]

class CircuitRecommendRequest(BaseModel):
    session_id: str
    age: Optional[int] = None
    type_tarif: str
    budget_max: float
    transport: str
    mobilite: str
    duration_minutes: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    zone: str
    preferences: CircuitPreferences
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    max_stops: Optional[int] = None

class MonumentItem(BaseModel):
    order: int
    monument_id: Optional[int] = None
    name: str
    latitude: float
    longitude: float
    visit_duration_min: int
    price: float
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    reason: str

class CircuitData(BaseModel):
    title: str
    summary: str
    monuments: List[MonumentItem]
    total_visit_duration_min: int
    total_travel_duration_min: int
    total_duration_min: int
    total_distance_km: float
    total_price: float
    score: float

class RouteData(BaseModel):
    transport: str
    polyline: List[List[float]]
    segments: List[Any]

class ConstraintsData(BaseModel):
    budget_ok: bool
    duration_ok: bool
    mobility_ok: bool

class CircuitRecommendResponse(BaseModel):
    session_id: str
    circuit: CircuitData
    route: RouteData
    constraints: ConstraintsData
    explanation: List[str]
    alternatives: List[Any]
    warnings: List[str]
    feasible: bool

# --- Logique métier et Cache ---
MONUMENTS_CACHE = []
CIRCUITS_CACHE = []
PERTINENCE_CALC = None


@app.post("/api/circuits/recommend", response_model=CircuitRecommendResponse)
async def recommend_circuit_endpoint(req: CircuitRecommendRequest):
    profil = CircuitProfil(
        budget_max=req.budget_max,
        type_tarif=req.type_tarif,
        mobilite=req.mobilite,
        transport=req.transport,
        duree_max=req.duration_minutes,
        preference_epoque=req.preferences.epoques,
        types_preferes=req.preferences.fonctions,
    )
    result = await asyncio.to_thread(recommend_circuit, profil, 3)

    if not result["circuits"]:
        return CircuitRecommendResponse(
            session_id=req.session_id,
            circuit=CircuitData(
                title="Aucun circuit disponible",
                summary="Nous n'avons trouvé aucun circuit correspondant à vos critères stricts.",
                monuments=[],
                total_visit_duration_min=0,
                total_travel_duration_min=0,
                total_duration_min=0,
                total_distance_km=0.0,
                total_price=0.0,
                score=0.0,
            ),
            route=RouteData(transport=req.transport, polyline=[], segments=[]),
            constraints=ConstraintsData(
                budget_ok=False, duration_ok=False, mobility_ok=False
            ),
            explanation=[],
            alternatives=[],
            warnings=result["warnings"]
            or ["Aucun circuit précalculé ne correspond à votre demande exacte."],
            feasible=False,
        )

    top = result["circuits"][0]
    return CircuitRecommendResponse(
        session_id=req.session_id,
        circuit=CircuitData(
            title=top["title"],
            summary=top["summary"],
            monuments=[
                MonumentItem(**m, arrival_time=None, departure_time=None)
                for m in top["monuments"]
            ],
            total_visit_duration_min=top["total_visit_duration_min"],
            total_travel_duration_min=top["total_travel_duration_min"],
            total_duration_min=top["total_duration_min"],
            total_distance_km=0.0,
            total_price=top["total_price"],
            score=top["score"],
        ),
        route=RouteData(transport=req.transport, polyline=[], segments=[]),
        constraints=ConstraintsData(
            budget_ok=top["budget_ok"], duration_ok=top["duration_ok"], mobility_ok=True
        ),
        explanation=[f"Score de pertinence globale : {int(top['score']*100)}%"],
        alternatives=[],
        warnings=result["warnings"],
        feasible=top["feasible"],
    )


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


def _get_sorted_monument_options(
    offset: int = 0, limit: int = 5
) -> tuple[List[WizardOption], bool]:
    """Retourne les monuments triés par popularité décroissante, paginés."""
    load_circuit_data()

    def _popularite(row: dict) -> float:
        try:
            return float(str(row.get("popularite", "0")).replace(",", "."))
        except (ValueError, TypeError):
            return 0.0

    indexed = list(enumerate(MONUMENTS_CACHE))
    indexed.sort(key=lambda pair: _popularite(pair[1]), reverse=True)

    page = indexed[offset : offset + limit]
    has_more = (offset + limit) < len(indexed)

    options = [
        WizardOption(
            value=str(idx),
            label=row.get("nom", "Inconnu"),
            meta={"popularite": _popularite(row)},
        )
        for idx, row in page
    ]
    return options, has_more


def _build_wizard_ui(wizard) -> Optional[WizardUI]:
    """Construit la spec de cards pour l'état wizard courant. None si pas de card à afficher."""
    if wizard is None:
        return None

    state = wizard.state
    state_value = state.value if isinstance(state, WizardState) else str(state)

    if state in (
        WizardState.IDLE,
        WizardState.GUIDE_MODE_READY,
        WizardState.CIRCUIT_GENERATION,
    ):
        return None

    question = question_for_state(state, lang="FR")

    if state == WizardState.CIRCUIT_ADJUSTMENT:
        return WizardUI(
            state=state_value,
            question=question,
            input_type="single_select",
            options=[
                WizardOption(value="retry_budget", label="Ajuster le budget"),
                WizardOption(value="retry_dates", label="Ajuster les dates"),
            ],
        )

    if state == WizardState.PLACE_SELECTION:
        options, has_more = _get_sorted_monument_options(offset=0, limit=5)
        return WizardUI(
            state=state_value,
            question=question,
            input_type="multi_select",
            options=options,
            has_more=has_more,
        )

    if state == WizardState.CUSTOMIZATION_BUDGET:
        return WizardUI(
            state=state_value,
            question=question,
            input_type="budget_form",
            options=[
                WizardOption(value="resident", label="Résident"),
                WizardOption(value="etranger", label="Étranger"),
            ],
        )

    if state == WizardState.CUSTOMIZATION_MOBILITY:
        return WizardUI(
            state=state_value,
            question=question,
            input_type="single_select",
            options=[
                WizardOption(value="walking", label="À pied"),
                WizardOption(value="car", label="En voiture"),
                WizardOption(value="bike", label="À vélo"),
            ],
        )

    if state == WizardState.CUSTOMIZATION_DATES:
        return WizardUI(
            state=state_value,
            question=question,
            input_type="date_form",
            options=[],
        )

    if state == WizardState.CIRCUIT_REVIEW:
        # TODO: ajouter l'option d'ajustement une fois l'event CIRCUIT_ADJUSTMENT confirmé/testé
        circuit = wizard.circuit_result or {}
        budget_ok = circuit.get("budget_ok")
        budget_warning = None
        if budget_ok is False:
            budget_warning = (
                f"Ce circuit dépasse votre budget : "
                f"{circuit.get('total_price', '?')} contre votre limite fixée."
            )
        return WizardUI(
            state=state_value,
            question=question,
            input_type="confirm",
            options=[
                WizardOption(value="confirm_circuit", label="Confirmer ce circuit")
            ],
            budget_ok=budget_ok,
            budget_warning=budget_warning,
        )

    # État non mappé explicitement (ex: CIRCUIT_ADJUSTMENT pas encore branché) — pas de card
    return None


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:

        message = request.message or ""
        if not message and not request.action:
            raise HTTPException(status_code=400, detail="Message is required")

        session_id = request.session_id or str(uuid.uuid4())
        if session_id not in sessions:
            sessions[session_id] = True

        if request.action:
            # Payload structuré (clic sur card) — pas de traduction nécessaire,
            # question_for_state() gère déjà le texte de sortie en FR
            detected_language = session_languages.get(session_id, "fr")
            session_languages[session_id] = detected_language

            response_fr = await chat(session_id, message, action=request.action)
            response = response_fr  # pas de traduction pour l'instant sur les réponses wizard
        else:
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

            response_fr = await chat(session_id, message_fr, action=request.action)

            response = translate_from_french(response_fr, detected_language)
            print(f"[Dourbia] Response in FR: {response_fr}")
            print(f"[Dourbia] Response translated to {detected_language}: {response}")

        response = translate_from_french(response_fr, detected_language)
        print(f"[Dourbia] Response in FR: {response_fr}")
        print(f"[Dourbia] Response translated to {detected_language}: {response}")

        response = translate_from_french(response_fr, detected_language)
        print(f"[Dourbia] Response in FR: {response_fr}")
        print(f"[Dourbia] Response translated to {detected_language}: {response}")

        profil = get_profile(session_id)
        wizard_store = WizardStore(
            await get_redis()
        )  
        wizard = await wizard_store.get(session_id)
        wizard_ui = _build_wizard_ui(wizard)

        return ChatResponse(
            session_id=session_id,
            answer=response,
            sources=[],
            memory_context=MemoryContext(
                preferred_language=detected_language,
                interests=profil.get("preferences", []),
                available_time_minutes=profil.get("duree_min"),
                mobility_mode=profil.get("mobilite"),
                last_mentioned_monuments=profil.get("lieux_vus", []),
                primary_site_id=profil.get("monument_en_attente_id"),
                primary_site_name=profil.get("monument_en_attente_nom"),
                last_substantive_user_message=request.message,
            ),
            suggested_actions=[],
            latency_ms=None,
            latency_debug=None,
            wizard_ui=wizard_ui,
        )
    except Exception as e:
        print(f"[Dourbia] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions", response_model=SessionResponse)
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = True
    return SessionResponse(session_id=session_id)


class MonumentItemResponse(BaseModel):
    id: int
    name_fr: str
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    latitude: float
    longitude: float
    visit_duration_min: Optional[int] = None
    dominant_period: Optional[str] = None
    function: Optional[str] = None
    popularity: Optional[float] = None
    image_url: Optional[str] = None

class MonumentsListResponse(BaseModel):
    monuments: List[MonumentItemResponse]

@app.get("/api/monuments", response_model=MonumentsListResponse)
async def get_monuments():
    # On force le chargement du CSV au cas où cet endpoint est appelé en premier
    load_circuit_data()
    
    result = []
    for idx, row in enumerate(MONUMENTS_CACHE):
        try:
            lat = float(str(row["latitude"]).replace(',', '.'))
            lon = float(str(row["longitude"]).replace(',', '.'))
        except (ValueError, KeyError):
            continue
            
        try:
            duration = int(row.get("duree_visite_min", 0))
        except ValueError:
            duration = None
            
        try:
            pop = float(str(row.get("popularite", "0")).replace(',', '.'))
        except ValueError:
            pop = None

        result.append(MonumentItemResponse(
            id=idx,
            name_fr=row.get("nom", "Inconnu"),
            latitude=lat,
            longitude=lon,
            visit_duration_min=duration,
            popularity=pop,
            # Champs absents du CSV mais optionnels dans le front :
            name_en=None,
            name_ar=None,
            dominant_period=None,
            function=None,
            image_url=None
        ))
        
    return MonumentsListResponse(monuments=result)

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

@app.get("/api/wizard-options/{session_id}")
async def wizard_options(session_id: str, offset: int = 0, limit: int = 5):
    """Pagination read-only pour select_places — n'écrit jamais dans Redis."""
    wizard_store = WizardStore(await get_redis())
    wizard = await wizard_store.get(session_id)
    if wizard is None or wizard.state != WizardState.PLACE_SELECTION:
        raise HTTPException(status_code=400, detail="Wizard pas en état PLACE_SELECTION")

    options, has_more = _get_sorted_monument_options(offset=offset, limit=limit)
    return {"options": [o.model_dump() for o in options], "has_more": has_more}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
