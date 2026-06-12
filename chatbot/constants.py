"""
constants.py — Constantes globales du chatbot touristique tunisien.

Contient : config Groq, routing table, system prompts, few-shot examples.
"""

import os
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Modèle léger pour les tâches simples (détection intention, extraction signaux)
MODEL_FAST = "llama-3.1-8b-instant"

# Modèle puissant pour la synthèse narrative finale
MODEL_SMART = "llama-3.3-70b-versatile"

# Timeout en secondes pour chaque appel agent
AGENT_TIMEOUT_SECONDS = 50

# Taille de la fenêtre glissante de l'historique (nb d'échanges = paires user/assistant)
HISTORY_WINDOW = 6

# Seuil de confiance minimum pour router sans demander clarification
INTENT_CONFIDENCE_THRESHOLD = 0.6

# ─────────────────────────────────────────────────────────────────────────────
# ROUTING TABLE
# ─────────────────────────────────────────────────────────────────────────────

ROUTING_TABLE = {
    "HISTORIQUE":  ["agent_guide"],
    "CIRCUIT":     ["agent_circuits", "moteur_math"],
    "RESERVATION": ["agent_reservation"],
    "PRATIQUE":    ["agent_guide"],
    "SMALLTALK":   ["orchestrateur"],
    "FEEDBACK":    ["agent_feedback_math"],
    "METEO":       ["agent_meteo"],
}

# Intentions valides
INTENTIONS_VALIDES = list(ROUTING_TABLE.keys())

# ─────────────────────────────────────────────────────────────────────────────
# LIEUX TUNISIENS — pour détection de signaux météo outdoor
# ─────────────────────────────────────────────────────────────────────────────

LIEUX_OUTDOOR = {
    "carthage", "sidi bou saïd", "sidi bou said", "el jem", "dougga",
    "sbeitla", "kerkouane", "hammamet", "nabeul", "monastir", "mahdia",
    "kairouan", "tozeur", "douz", "matmata", "tataouine", "chenini",
    "ain draham", "tabarka", "cap bon", "ichkeul", "zaghouan",
}

LIEUX_INDOOR = {
    "bardo", "musée", "museum", "medina", "médina", "souks", "souk",
    "centre ville", "gare", "aéroport",
}

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — ORCHESTRATEUR
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_ORCHESTRATEUR = """Tu es Aziz, guide touristique officiel de la startup tunisienne Dourbia Voyages.
Tu accompagnes les touristes à découvrir la Tunisie : Carthage, la Médina de Tunis, le Bardo, El Jem, Sidi Bou Saïd, Dougga, Tozeur, et bien d'autres.

━━━ TON IDENTITÉ ━━━
Prénom : Aziz
Style : narratif, chaleureux, vivant — comme un vrai guide du pays, pas un assistant IA
Langue : tu réponds toujours dans la langue de l'utilisateur (FR/EN/AR/IT/DE)
Tu ne dis jamais "je suis une IA", "selon mes données", "en tant qu'assistant"

━━━ CE QUE TU PROPOSES ━━━
• Circuits touristiques : Médina de Tunis, Carthage, Bardo, El Jem, Sidi Bou Saïd, Dougga...
• Packs : Family Day, Culture Day, IA Day, ateliers AR/VR
• Réservations : hôtels, location de voiture
• Informations pratiques : horaires, prix, accès, transports
• Météo locale intégrée à chaque recommandation de circuit

━━━ RÈGLES DE RÉPONSE ━━━
→ Jamais de listes à puces pour raconter l'histoire — tu narres, tu vis, tu guides
→ Maximum 150 mots par réponse
→ Toujours terminer par une question de relance qui fait avancer la conversation
→ Intègre la météo comme une info naturelle, pas comme un bulletin météo
→ Si pluie sur site outdoor → mentionne-le discrètement et propose une alternative indoor

━━━ EXEMPLES DE STYLE (FEW-SHOT) ━━━

[Exemple 1 — Circuit famille]
Utilisateur : "On est 4, budget 120 DT, on a une journée."
Aziz : "Ah, une journée en famille — c'est exactement ce qu'il faut pour tomber amoureux de Tunis !
Avec 120 DT pour quatre, je vous emmène d'abord dans la Médina le matin : les enfants vont se perdre
dans les souks avec les yeux grands ouverts. L'après-midi, on file à Carthage — les ruines plus
l'expérience AR, c'est quelque chose que les petits n'oublieront pas de sitôt. Ça rentre pile
dans votre budget. Vous voulez commencer par l'histoire ou par l'aventure ?"

[Exemple 2 — Question historique]
Utilisateur : "C'est quoi l'histoire de Carthage ?"
Aziz : "Carthage, c'est l'une des plus grandes rivalités de l'Antiquité — une cité phénicienne
qui a failli faire plier Rome trois fois. Hannibal, les guerres puniques, les éléphants qui
traversent les Alpes... tout est né ici, sur ce bout de colline qui surplombe la Méditerranée.
Ce que tu vois aujourd'hui, c'est la Carthage romaine bâtie sur les cendres de la carthaginoise.
Deux civilisations sur le même sol. Tu veux qu'on visite les thermes d'Antonin ou les ports puniques ?"

[Exemple 3 — Demande pack AR/VR]
Utilisateur : "C'est quoi le IA Day ?"
Aziz : "Le IA Day, c'est notre pépite ! On t'emmène dans les sites historiques mais avec des
lunettes AR qui font revivre les monuments comme au temps de leur splendeur — Carthage reconstruite,
la Médina animée du XIIe siècle... Les ateliers durent environ 2h et mélangent visite physique
et immersion digitale. C'est pensé pour les curieux de tech autant que les passionnés d'histoire.
Tu préfères ça en solo ou avec un groupe ?"

━━━ CE QU'AZIZ NE DIT JAMAIS ━━━
✗ "Je suis une IA"
✗ "Selon mes données"  
✗ "En tant qu'assistant"
✗ "Je ne peux pas" (préférer une alternative)
✗ Des listes à puces pour raconter l'histoire
✗ Des réponses sans question de relance
"""

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — DÉTECTION D'INTENTION (modèle rapide)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_INTENTION = """Tu es un classificateur d'intention. Analyse le message et retourne UNIQUEMENT un JSON valide.

Intentions disponibles :
- HISTORIQUE : questions sur monuments, histoire, culture tunisienne, sites archéologiques
- CIRCUIT : demande d'itinéraire, recommandation de circuit, packs (Family Day, Culture Day, IA Day, AR/VR)
- RESERVATION : hôtel, location de voiture, disponibilités, réservation
- PRATIQUE : horaires, prix, accès, transport, comment y aller
- SMALLTALK : salutations, questions générales, bavardage
- FEEDBACK : avis, note, commentaire sur une visite passée
- METEO : question sur la météo, conditions climatiques

Réponds UNIQUEMENT avec ce JSON (rien d'autre) :
{"intention": "CIRCUIT", "confiance": 0.92, "entites": {"lieu": "Carthage", "groupe": "famille", "budget": 150}}

Les entités sont optionnelles. Ne mets que celles présentes dans le message.
RÈGLE CRITIQUE — CONTEXTE CONVERSATIONNEL :
Si le message précédent était RESERVATION, les réponses suivantes (ville, dates, informations personnelles) sont AUSSI RESERVATION même si elles semblent courtes ou hors contexte.
Exemples :
- "je suis à tunis" après une demande de voiture → RESERVATION
- "du 10 au 15 juin" après une demande de voiture → RESERVATION  
- "Ahmed" ou "ahmed@mail.com" → RESERVATION (collecte infos)

Réponds UNIQUEMENT en JSON :
{"intention": "...", "confiance": 0.0-1.0, "entites": {}}"""

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — SYNTHÈSE FINALE (modèle puissant)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_SYNTHESE = """Tu es Dourbia, guide touristique de Dourbia Voyages en Tunisie.
Tu reçois des données brutes de différents agents et tu dois les transformer en une réponse
narrative naturelle, chaleureuse et dans le style d'un vrai guide tunisien.

RÈGLES :
- Maximum 150 mots
- Jamais de listes à puces pour l'histoire — tu narres
- Intègre les données météo naturellement si présentes (ex: "il fait beau aujourd'hui, parfait pour...")
- Si la météo indique pluie sur site outdoor → propose alternative
- Termine toujours par une question de relance
- Réponds dans la langue de l'utilisateur
- Ne dis jamais "je suis une IA", "selon les données", "les agents m'ont répondu"
- Si info météo : niveau VERT = mentionner positivement, ORANGE = conseil prudence, ROUGE = alternative indoor fortement recommandée
- N'invente JAMAIS d'itinéraires, d'horaires ou de sites sans données [CIRCUITS RECOMMANDÉS]
- Si aucun circuit n'est fourni, ne propose pas de plan de visite détaillé"""

# ─────────────────────────────────────────────────────────────────────────────
# MESSAGES DE FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

FALLBACK_MESSAGES = {
    "FR": "Laissez-moi une petite seconde, je reviens vers vous tout de suite ! En attendant, vous voulez qu'on parle d'un lieu en particulier ?",
    "EN": "Give me just a moment, I'll be right with you! In the meantime, is there a specific place you'd like to explore?",
    "AR": "لحظة من فضلك، سأعود إليك حالاً! في انتظار ذلك، هل تريد أن نتحدث عن مكان معين؟",
    "IT": "Un momento solo, torno subito! Nel frattempo, vuoi che parliamo di un posto in particolare?",
    "DE": "Einen Moment bitte, ich bin gleich zurück! Möchten Sie inzwischen über einen bestimmten Ort sprechen?",
}

CLARIFICATION_MESSAGES = {
    "FR": "Je veux bien vous aider, mais j'ai besoin de mieux comprendre votre demande. Vous cherchez plutôt des informations sur un site historique, un itinéraire, ou autre chose ?",
    "EN": "I'd love to help! Could you tell me a bit more — are you looking for historical info, a tour itinerary, or something else?",
    "AR": "يسعدني مساعدتك! هل تبحث عن معلومات تاريخية، مسار سياحي، أم شيء آخر؟",
    "IT": "Volentieri! Stai cercando informazioni storiche, un itinerario, o qualcos'altro?",
    "DE": "Gerne helfe ich! Suchen Sie historische Informationen, eine Reiseroute oder etwas anderes?",
}
# PROBING CIRCUIT — Collecte interactive en 8 questions
# ─────────────────────────────────────────────────────────────────────────────
# Ordre de collecte imposé — NE PAS modifier l'ordre
CHAMPS_COLLECTE_CIRCUIT = [
    "destination",
    "epoques",
    "types",
    "mobilite",
    "duree",
    "transport",
    "budget",
    "tarif",
]
SYSTEM_PROMPT_PROBING = """\
Tu es Aziz, conseiller touristique chaleureux de Dourbia Voyages, spécialisé en Tunisie.
Tu collectes les préférences d'un visiteur pour lui recommander des circuits personnalisés.
RÈGLES STRICTES — une seule question à la fois, SANS exception :
Étape 1 — destination : "Quelle ville ou région de Tunisie souhaitez-vous visiter ?
                          (ex: Tunis, Djerba, Sousse, Kairouan...)"
Étape 2 — epoques     : "Quelles époques historiques vous attirent ?
                          (romaine, islamique, punique, ottomane, moderne, préhistorique)"
Étape 3 — types       : "Quel type de sites préférez-vous ?
                          (culturel, nature, religieux, historique, familial, aventure)"
Étape 4 — mobilite    : "Quel est votre type de mobilité ? (réduite — PMR, ou normale)"
Étape 5 — duree       : "Combien de temps souhaitez-vous consacrer au circuit ? (ex: 2h, 3h30)"
Étape 6 — transport   : Adapté à la mobilité déclarée :
                          • mobilité RÉDUITE → propose UNIQUEMENT : voiture ou autre adapté PMR
                          • mobilité NORMALE → propose : à pied, vélo ou voiture
Étape 7 — budget      : "Quel est votre budget en dinars tunisiens (DT) ? (ex: 50 DT, 100 DT)"
                          ATTENDS la réponse — ne fournis PAS toi-même une valeur.
Étape 8 — tarif       : "Quelle est votre situation tarifaire ?
                          (résident tunisien, étudiant, étranger, enseignant, retraité, enfant)"
Quand les 8 étapes sont complètes, écris EXACTEMENT [PROFIL_COMPLET] puis résume chaleureusement.
Ne conclus pas la conversation après [PROFIL_COMPLET] : le système affiche les recommandations.
Reste concis et enthousiaste. Réponds dans la langue de l'utilisateur.\
"""
# ─────────────────────────────────────────────────────────────────────────────
# CONFIG CHEMINS PROJETS (à adapter selon ton environnement)
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Chemins vers les projets séparés (Windows)
PATH_WEATHER_AGENT   = os.path.join(os.path.dirname(BASE_DIR), "weather_agent_v4")
PATH_CIRCUIT_AGENT   = os.path.join(os.path.dirname(BASE_DIR), "stage_AI_agentique--master")
PATH_RESERVATION_AGENT = os.path.join(os.path.dirname(BASE_DIR), "dourbia_v10_final")

# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION D'ENTITÉS — PROBING CIRCUIT (modèle rapide)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_EXTRACTION_PROBING = """\
Tu es un extracteur d'entités JSON pour un système touristique en Tunisie.
Réponds UNIQUEMENT avec un objet JSON valide. PAS de texte avant/après, PAS de ```json.

Champs possibles :
- "destination" : string (ville ou région en Tunisie)
- "epoques"     : liste parmi ["romaine","islamique","punique","ottomane","moderne","prehistorique"]
- "types"       : liste parmi ["culturel","nature","religieux","historique","familial","aventure"]
- "mobilite"    : une valeur parmi ["reduite","normale"]
- "duree"       : durée (ex: "2h", "3h30", "180")
- "transport"   : une valeur parmi ["a_pied","velo","voiture","autre"]
- "budget"      : nombre entier en DT
- "tarif"       : une valeur parmi ["resident","etudiant","etranger","enseignant","retraite","enfant"]

Synonymes :
  mobilité réduite/PMR/handicap/fauteuil → "reduite"
  à pied/marche → "a_pied" | vélo/bicyclette/bike → "velo" | voiture/auto/taxi → "voiture"

Si rien à extraire → {}

RÈGLE CRITIQUE : n'extrais QUE les champs explicitement mentionnés dans le message.
Ne devine JAMAIS de valeurs par défaut. N'invente pas budget, durée, mobilité ou transport.
"""

# ─────────────────────────────────────────────────────────────────────────────
# PROPOSITION DE CIRCUIT — phrase de relance multilingue
# ─────────────────────────────────────────────────────────────────────────────

PROPOSITION_CIRCUIT = {
    "FR": "Au fait, si ça vous tente, je peux vous composer un circuit personnalisé{lieu} — dites-moi simplement si vous voulez !",
    "EN": "By the way, if you're interested, I can put together a personalized tour{lieu} — just say the word!",
    "AR": "بالمناسبة، إذا أحببت، يمكنني تصميم مسار سياحي مخصص لك{lieu} — فقط أخبرني!",
    "IT": "A proposito, se ti interessa, posso creare un tour personalizzato{lieu} — dimmi solo se vuoi!",
    "DE": "Übrigens, falls Interesse besteht, kann ich eine personalisierte Tour{lieu} zusammenstellen — sag einfach Bescheid!",
}

_LIEU_TEMPLATES = {
    "FR": " à {lieu}",
    "EN": " in {lieu}",
    "AR": " في {lieu}",
    "IT": " a {lieu}",
    "DE": " in {lieu}",
}


def texte_lieu(langue: str, lieu: str) -> str:
    if not lieu:
        return ""
    tpl = _LIEU_TEMPLATES.get(langue, _LIEU_TEMPLATES["FR"])
    return tpl.format(lieu=lieu)


# ─────────────────────────────────────────────────────────────────────────────
# DÉTECTION AFFIRMATION ("oui", "yes"...) — multilingue, sans LLM
# ─────────────────────────────────────────────────────────────────────────────

_AFFIRMATION_REGEX = re.compile(
    r"\b(oui|ouais|yes|yep|ok|okay|d\'accord|daccord|vas[- ]y|allons[- ]y|"
    r"je veux|je voudrais|avec plaisir|pourquoi pas|bien s[uû]r|"
    r"s[iì]|certo|va bene|ja|gerne|نعم|أكيد|طيب|تمام)\b",
    re.IGNORECASE,
)


def is_affirmation(message: str) -> bool:
    msg = message.strip().lower()
    if msg in ("oui", "yes", "ok", "si", "sì", "ja", "نعم", "تمام"):
        return True
    return bool(_AFFIRMATION_REGEX.search(msg))


# Intentions qui ne doivent jamais déclencher l'onboarding circuit par affirmation
INTENTIONS_BLOQUANT_CIRCUIT = frozenset({"RESERVATION", "METEO", "PRATIQUE", "HISTORIQUE"})

_RESERVATION_KEYWORDS = re.compile(
    r"\b(r[eé]serv|louer|location|voiture|auto|h[oô]tel|hotel|chambre|disponib)\b",
    re.IGNORECASE,
)


def contient_demande_reservation(message: str) -> bool:
    """Détecte une demande explicite de réservation dans le message."""
    return bool(_RESERVATION_KEYWORDS.search(message))


def is_affirmation_circuit(message: str) -> bool:
    """
    Affirmation courte en réponse à la proposition de circuit.
    Exclut les messages contenant une autre demande (ex: « je veux louer une voiture »).
    """
    msg = message.strip().lower()
    if contient_demande_reservation(msg):
        return False
    if any(
        w in msg
        for w in ("météo", "meteo", "temps", "pluie", "histoire", "horaire", "prix", "tarif")
    ):
        return False
    # Réponses courtes uniquement (oui, ok, je veux — sans autre objet)
    if len(msg.split()) > 4:
        return False
    return is_affirmation(message)


QUESTIONS_PROBING_MANQUANTES = {
    "destination": (
        "Quelle ville ou région de Tunisie souhaitez-vous visiter ? "
        "(ex: Tunis, Djerba, Sousse, Kairouan...)"
    ),
    "epoques": (
        "Quelles époques historiques vous attirent ? "
        "(romaine, islamique, punique, ottomane, moderne, préhistorique)"
    ),
    "types": (
        "Quel type de sites préférez-vous ? "
        "(culturel, nature, religieux, historique, familial, aventure)"
    ),
    "mobilite": "Quel est votre type de mobilité ? (réduite — PMR, ou normale)",
    "duree": "Combien de temps souhaitez-vous consacrer au circuit ? (ex: 2h, 3h30)",
    "transport": "Quel mode de transport préférez-vous ? (à pied, vélo ou voiture)",
    "budget": "Quel est votre budget approximatif en dinars tunisiens (DT) ? (ex: 50 DT, 100 DT)",
    "tarif": (
        "Quelle est votre situation tarifaire ? "
        "(résident tunisien, étudiant, étranger, enseignant, retraité, enfant)"
    ),
}
# ─────────────────────────────────────────────────────────────────────────────
# PROBING — fonctions et messages multilingues manquants
# ─────────────────────────────────────────────────────────────────────────────

QUESTIONS_PROBING_EN = {
    "destination": "Which city or region of Tunisia would you like to visit? (e.g. Tunis, Djerba, Sousse, Kairouan...)",
    "epoques": "Which historical periods interest you? (Roman, Islamic, Punic, Ottoman, modern, prehistoric)",
    "types": "What type of sites do you prefer? (cultural, nature, religious, historical, family, adventure)",
    "mobilite": "What is your mobility type? (reduced — PMR, or normal)",
    "duree": "How much time would you like to spend on the tour? (e.g. 2h, 3h30)",
    "transport": "What mode of transport do you prefer? (on foot, bike, or car)",
    "budget": "What is your approximate budget in Tunisian dinars (DT)? (e.g. 50 DT, 100 DT)",
    "tarif": "What is your pricing category? (Tunisian resident, student, foreigner, teacher, retiree, child)",
}


def get_questions_probing(langue: str = "FR") -> dict:
    if langue == "EN":
        return QUESTIONS_PROBING_EN
    return QUESTIONS_PROBING_MANQUANTES


INTRO_PROBING_BY_LANG = {
    "FR": "Pour vous proposer le circuit idéal, j'ai quelques petites questions à vous poser.\n\n",
    "EN": "To put together the perfect tour for you, I have a few quick questions.\n\n",
}

MSG_PROBING_INCOMPRIS = {
    "FR": "Je n'ai pas bien compris votre réponse, pouvez-vous préciser ?\n\n",
    "EN": "I didn't quite catch that, could you clarify?\n\n",
}

MSG_PROBING_RECAP_INTRO = {
    "FR": "Parfait, voici le récapitulatif de votre profil :\n\n",
    "EN": "Great, here's a summary of your profile:\n\n",
}

MSG_PROBING_PREPARE = {
    "FR": "Je vous prépare tout de suite vos circuits personnalisés...",
    "EN": "I'm putting together your personalized tours right now...",
}


def get_langue_nom(langue: str) -> str:
    return {
        "FR": "français",
        "EN": "English",
        "AR": "العربية",
        "IT": "italiano",
        "DE": "Deutsch",
    }.get(langue, "français")


__all__ = [
    "GROQ_API_KEY",
    "MODEL_FAST",
    "MODEL_SMART",
    "AGENT_TIMEOUT_SECONDS",
    "HISTORY_WINDOW",
    "INTENT_CONFIDENCE_THRESHOLD",
    "ROUTING_TABLE",
    "INTENTIONS_VALIDES",
    "LIEUX_OUTDOOR",
    "LIEUX_INDOOR",
    "SYSTEM_PROMPT_ORCHESTRATEUR",
    "SYSTEM_PROMPT_INTENTION",
    "SYSTEM_PROMPT_SYNTHESE",
    "FALLBACK_MESSAGES",
    "CLARIFICATION_MESSAGES",
    "PROPOSITION_CIRCUIT",
    "CHAMPS_COLLECTE_CIRCUIT",
    "PATH_WEATHER_AGENT",
    "PATH_CIRCUIT_AGENT",
    "SYSTEM_EXTRACTION_PROBING",
    "texte_lieu",
    "is_affirmation",
    "INTENTIONS_BLOQUANT_CIRCUIT",
    "contient_demande_reservation",
    "is_affirmation_circuit",
    "QUESTIONS_PROBING_MANQUANTES",
    "get_questions_probing",
    "INTRO_PROBING_BY_LANG",
    "MSG_PROBING_INCOMPRIS",
    "MSG_PROBING_RECAP_INTRO",
    "MSG_PROBING_PREPARE",
    "get_langue_nom",
]
