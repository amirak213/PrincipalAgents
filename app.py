import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "AgentPrincipal")
)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uuid
from AgentPrincipal.chat import chat
from typing import Optional, List, Any
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator
from AgentPrincipal.geo_service import get_geo_service
from AgentPrincipal.orchestrateur import (
    OrchestratorAgent,
    _run_circuit_recommendation_sync,
    _load_circuit_v2_modules,
    CircuitRecommendationBusinessError,
)
from AgentPrincipal.chat import get_orchestrateur

from AgentPrincipal.session_memory import (
    get_active_circuit,
    get_profile,
    update_profile,
)
from circuit_engine import (
    recommend_circuit,
    load_circuit_data,
    CircuitProfil,
    MONUMENTS_CACHE,
)
import asyncio
from contextlib import asynccontextmanager
from AgentPrincipal.wizard_state_machine import (
    WizardState,
    WizardStore,
    question_for_state,
)
from AgentPrincipal.redis_client import get_redis

_circuit_v2_mods = _load_circuit_v2_modules()
CircuitRecommendationResponse = _circuit_v2_mods["CircuitRecommendationResponse"]

# Set seed for consistent language detection
DetectorFactory.seed = 0


# Initialize translator
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] Préchargement de l'orchestrateur (modèle embeddings)...")
    get_orchestrateur()
    print("[STARTUP] Orchestrateur prêt.")
    yield


app = FastAPI(title="Dourbia Chatbot API", version="1.0.0", lifespan=lifespan)

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

class PackCard(BaseModel):
    code: Optional[str] = None
    title: str
    emoji: str = "🎒"
    description: Optional[str] = None
    duration: Optional[str] = None
    capacity: Optional[int] = None
    audience: Optional[str] = None
    location: Optional[str] = None

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


class WizardCircuitStop(BaseModel):
    order: int
    name: str
    visit_duration_min: int
    price: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class WizardCircuitSummary(BaseModel):
    title: str
    summary: str
    monuments: List[WizardCircuitStop] = Field(default_factory=list)
    total_duration_min: float
    total_price: float
    route: Optional[dict] = None


class WizardUI(BaseModel):
    state: str
    question: str
    input_type: str  # "single_select" | "multi_select" | "budget_form" | "date_form" | "confirm"
    options: List[WizardOption] = Field(default_factory=list)
    has_more: bool = False  # utilisé par place_selection pour signaler "voir plus"
    budget_ok: Optional[bool] = None  # renseigné uniquement pour CIRCUIT_REVIEW
    budget_warning: Optional[str] = None  # message d'alerte si budget_ok=False
    circuit: Optional[WizardCircuitSummary] = (
        None  # renseigné uniquement pour CIRCUIT_REVIEW
    )


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: List[SourceItem] = Field(default_factory=list)
    memory_context: MemoryContext
    suggested_actions: List[str] = Field(default_factory=list)
    latency_ms: Optional[float] = None
    latency_debug: Optional[LatencyDebug] = None
    wizard_ui: Optional[WizardUI] = None
    packs: Optional[List[PackCard]] = None


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



# --- Logique métier et Cache ---
CIRCUITS_CACHE = []
PERTINENCE_CALC = None


@app.post("/api/circuits/recommend", response_model=CircuitRecommendationResponse)
async def recommend_circuit_endpoint(req: CircuitRecommendRequest):
    mods = _load_circuit_v2_modules()
    NewRequest = mods["CircuitRecommendationRequest"]
    NewPreferences = mods["CircuitPreferences"]

    new_req = NewRequest(
        session_id=req.session_id,
        age=req.age,
        type_tarif=req.type_tarif,
        budget_max=req.budget_max,
        transport=req.transport,
        mobilite=req.mobilite,
        duration_minutes=req.duration_minutes,
        start_time=req.start_time,
        end_time=req.end_time,
        zone=req.zone,
        preferences=NewPreferences(
            epoques=req.preferences.epoques,
            fonctions=req.preferences.fonctions,
            must_visit=req.preferences.must_visit,
            avoid=req.preferences.avoid,
        ),
        start_location=req.start_location,
        end_location=req.end_location,
        max_stops=req.max_stops if req.max_stops is not None else 12,
    )

    try:
        result = await asyncio.to_thread(_run_circuit_recommendation_sync, new_req)
    except CircuitRecommendationBusinessError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result.response


class LocationRequest(BaseModel):
    session_id: str
    lat: float
    lon: float
    langue: Optional[str] = "FR"


class PositionRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    latitude: float
    longitude: float
    langue: Optional[str] = "FR"


class LocationResponse(BaseModel):
    triggered: bool  # True si un monument est détecté
    monument_id: Optional[str] = None
    nom: Optional[str] = None
    distance_m: Optional[float] = None
    message_aziz: Optional[str] = None


class PositionResponse(BaseModel):
    triggered: bool
    monument: Optional[str] = None
    monument_id: Optional[str] = None
    distance_m: Optional[float] = None


class SessionResponse(BaseModel):
    session_id: str


session_languages = {}
session_announced: dict[str, set] = {}


def _matches_city(row: dict, city: Optional[str]) -> bool:
    if not city:
        return True

    city_key = str(city).strip().lower()
    if city_key == "carthage":
        return True

    if city_key == "la_marsa":
        name = str(row.get("nom", "")).lower()
        return "marsa" in name

    return True


def _get_sorted_monument_options(
    offset: int = 0, limit: int = 5, city: Optional[str] = None
) -> tuple[List[WizardOption], bool]:
    """Retourne les monuments triés par popularité décroissante, paginés."""
    load_circuit_data()

    def _popularite(row: dict) -> float:
        try:
            return float(str(row.get("popularite", "0")).replace(",", "."))
        except (ValueError, TypeError):
            return 0.0

    indexed = [
        (idx, row) for idx, row in enumerate(MONUMENTS_CACHE) if _matches_city(row, city)
    ]
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
    page = indexed[offset : offset + limit]
    has_more = (offset + limit) < len(indexed)
    print(f"[DEBUG] MONUMENTS_CACHE len={len(MONUMENTS_CACHE)}, page len={len(page)}")
    return options, has_more


def _build_wizard_ui(wizard) -> Optional[WizardUI]:
    """Construit la spec de cards pour l'état wizard courant. None si pas de card à afficher."""
    if wizard is None:
        return None

    state = wizard.state
    state_value = state.value if isinstance(state, WizardState) else str(state)

    if state in (
        WizardState.IDLE,
        WizardState.CIRCUIT_GENERATION,
    ):
        return None

    question = question_for_state(state, lang="FR")

    if state == WizardState.CITY_SELECTION:
        return WizardUI(
            state=state_value,
            question=question,
            input_type="single_select",
            options=[
                WizardOption(value="carthage", label="Carthage"),
                WizardOption(value="la_marsa", label="La Marsa"),
            ],
        )

    if state == WizardState.GUIDE_MODE_READY:
        return WizardUI(
            state=state_value,
            question=question,
            input_type="confirm",
            options=[
                WizardOption(value="yes", label="Oui, activer le Guide GPS"),
                WizardOption(value="no", label="Non merci"),
            ],
        )

    if state == WizardState.CIRCUIT_ADJUSTMENT:
        return WizardUI(
            state=state_value,
            question=question,
            input_type="single_select",
            options=[
                WizardOption(value="budget", label="Ajuster le budget"),
                WizardOption(value="mobility", label="Ajuster le mode de déplacement"),
                WizardOption(value="dates", label="Ajuster les dates"),
                WizardOption(value="places", label="Ajuster les lieux"),
            ],
        )

    if state == WizardState.PLACE_SELECTION:
        options, has_more = _get_sorted_monument_options(
            offset=wizard.places_offset if getattr(wizard, "places_offset", 0) else 0,
            limit=5,
            city=wizard.city,
        )
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
                WizardOption(value="etudiant", label="Étudiant"),
                WizardOption(value="resident", label="Résident"),
                WizardOption(value="etranger", label="Étranger"),
                WizardOption(value="enseignant", label="Enseignant"),
                WizardOption(value="retraite", label="Retraité"),
                WizardOption(value="enfant", label="Enfant"),
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

    if state == WizardState.CUSTOMIZATION_PREFERENCES:
        return WizardUI(
            state=state_value,
            question=question,
            input_type="preferences_form",
            options=[
                WizardOption(value="Antiquité", label="Antiquité", meta={"type": "epoque"}),
                WizardOption(value="Punique", label="Punique", meta={"type": "epoque"}),
                WizardOption(value="Romaine", label="Romaine", meta={"type": "epoque"}),
                WizardOption(value="Byzantine", label="Byzantine", meta={"type": "epoque"}),
                WizardOption(value="Islamique", label="Islamique", meta={"type": "epoque"}),
                WizardOption(value="Ottomane", label="Ottomane", meta={"type": "epoque"}),
                WizardOption(value="Contemporaine", label="Contemporaine", meta={"type": "epoque"}),
                WizardOption(value="Religieux", label="Religieux", meta={"type": "fonction"}),
                WizardOption(value="Militaire", label="Militaire", meta={"type": "fonction"}),
                WizardOption(value="Civil", label="Civil", meta={"type": "fonction"}),
                WizardOption(value="Funéraire", label="Funéraire", meta={"type": "fonction"}),
                WizardOption(value="Culturel", label="Culturel", meta={"type": "fonction"}),
                WizardOption(value="Public", label="Public", meta={"type": "fonction"}),
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
        result = wizard.circuit_result or {}
        circuit_data = result.get("circuit", {})
        constraints = result.get("constraints", {})
        route_data = result.get("route")

        budget_ok = constraints.get("budget_ok")
        budget_warning = None
        if budget_ok is False:
            budget_warning = (
                f"Ce circuit dépasse votre budget : "
                f"{circuit_data.get('total_price', '?')} contre votre limite fixée."
            )
        circuit_summary = None
        if circuit_data:
            circuit_summary = WizardCircuitSummary(
                title=circuit_data.get("title", "Votre circuit"),
                summary=circuit_data.get("summary", ""),
                monuments=[
                    WizardCircuitStop(
                        order=m.get("order", i + 1),
                        name=m.get("name", "?"),
                        visit_duration_min=m.get("visit_duration_min", 0),
                        price=m.get("price", 0.0),
                        latitude=m.get("latitude"),
                        longitude=m.get("longitude"),
                    )
                    for i, m in enumerate(circuit_data.get("monuments", []))
                ],
                total_duration_min=circuit_data.get("total_duration_min", 0),
                total_price=circuit_data.get("total_price", 0.0),
                route=route_data,
            )
        return WizardUI(
            state=state_value,
            question=question,
            input_type="confirm",
            options=[
                WizardOption(value="confirm_circuit", label="Confirmer ce circuit"),
                WizardOption(value="adjust_circuit", label="Ajuster ce circuit"),
            ],
            budget_ok=budget_ok,
            budget_warning=budget_warning,
            circuit=circuit_summary,
        )

    # État non mappé explicitement (ex: CIRCUIT_ADJUSTMENT pas encore branché) — pas de card
    return None


def _translate_chat_response(response_fr: str, detected_language: str) -> str:
    if not detected_language or detected_language == "fr":
        return response_fr
    return translate_from_french(response_fr, detected_language)


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
            response = (
                response_fr  # pas de traduction pour l'instant sur les réponses wizard
            )
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

        response = _translate_chat_response(response_fr, detected_language)

        profil = get_profile(session_id)
        wizard_store = WizardStore(await get_redis())
        wizard = await wizard_store.get(session_id)
        wizard_ui = _build_wizard_ui(wizard)

        raw_packs = profil.get("last_packs")
        packs_ui = [PackCard(**p) for p in raw_packs] if raw_packs else None
        if raw_packs:
            update_profile(
                session_id, {"last_packs": None}
            )  # évite de refaire apparaître les packs au tour suivant

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
            packs=packs_ui,
        )
    except Exception as e:
        print(f"[Dourbia] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/position", response_model=PositionResponse)
async def position_endpoint(request: PositionRequest):
    """Reçoit une mise à jour GPS et déclenche un événement de proximité si un monument du circuit actif est à portée."""
    session_id = request.user_id or request.session_id or ""
    if not session_id:
        return PositionResponse(triggered=False)

    profil = get_profile(session_id)
    circuit_id = profil.get("circuit_confirme_id") or get_active_circuit(session_id)
    if not circuit_id:
        return PositionResponse(triggered=False)

    try:
        geo = get_geo_service()
        nearby = await geo.get_nearby_monuments_for_circuit(
            lat=request.latitude,
            lon=request.longitude,
            circuit_id=str(circuit_id),
            langue=(request.langue or "FR").upper(),
            rayon_override_m=100,
        )
    except Exception as exc:
        print(f"[Dourbia] Erreur /api/position : {exc}")
        return PositionResponse(triggered=False)

    if not nearby:
        return PositionResponse(triggered=False)

    monument = nearby[0]
    orchestrateur = get_orchestrateur()
    await orchestrateur.handle_proximity_trigger(
        user_id=session_id,
        monument_id=str(monument.get("id", "")),
        monument_nom=monument.get("nom", "Monument"),
        langue=(request.langue or "FR").upper(),
    )

    return PositionResponse(
        triggered=True,
        monument=monument.get("nom"),
        monument_id=str(monument.get("id", "")),
        distance_m=monument.get("distance_m"),
    )


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
            lat = float(str(row["latitude"]).replace(",", "."))
            lon = float(str(row["longitude"]).replace(",", "."))
        except (ValueError, KeyError):
            continue

        try:
            duration = int(row.get("duree_visite_min", 0))
        except ValueError:
            duration = None

        try:
            pop = float(str(row.get("popularite", "0")).replace(",", "."))
        except ValueError:
            pop = None

        result.append(
            MonumentItemResponse(
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
                image_url=None,
            )
        )

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
                lat=lat,
                lon=lon,
                circuit_id=circuit_actif,
                langue=langue,
                rayon_override_m=150,
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
        raise HTTPException(
            status_code=400, detail="Wizard pas en état PLACE_SELECTION"
        )

    options, has_more = _get_sorted_monument_options(offset=offset, limit=limit)
    return {"options": [o.model_dump() for o in options], "has_more": has_more}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
