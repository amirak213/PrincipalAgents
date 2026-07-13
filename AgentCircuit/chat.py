import sys
import os
import json
import re
import time
from datetime import datetime
from colorama import init, Fore, Style

import db as _db

charger_tous_clients = _db.charger_tous_clients
charger_tous_circuits = _db.charger_tous_circuits
charger_distances_circuit = _db.charger_distances_circuit
sauvegarder_feedback = _db.sauvegarder_feedback
sauvegarder_client = _db.sauvegarder_client
test_connexion = _db.test_connexion

init(autoreset=True)

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

# CORRECTION 1 : la clé n'est JAMAIS en clair dans le code source.
# Lance : export GROQ_API_KEY="gsk_..." avant de démarrer.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Utilise le modèle le plus capable disponible sur Groq pour
# l'extraction JSON (plus fiable que 8b instant)
MODEL_EXTRACTION = "llama-3.3-70b-versatile"  # extraction + réponse principale
MODEL_CHAT = "llama-3.3-70b-versatile"  # conversation

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


# ─────────────────────────────────────────────────────────────
# UTILITAIRES VISUELS TERMINAL
# ─────────────────────────────────────────────────────────────


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════╗
║     🌍  Système de Recommandation de Circuits Touristiques   ║
║              LLaMA 3.3 (70b) via Groq  |  PostgreSQL         ║
╚══════════════════════════════════════════════════════════════╝""")
    print(
        Fore.WHITE
        + f"  Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Modèle : {MODEL_CHAT}\n"
    )


def print_separator():
    print(Fore.BLUE + "─" * 64)


def print_bot(msg: str):
    print(Fore.GREEN + Style.BRIGHT + "\n🤖 Assistant : " + Style.NORMAL)
    for mot in msg.split(" "):
        print(Fore.WHITE + mot + " ", end="", flush=True)
        time.sleep(0.014)
    print()


def print_user_prompt():
    print(Fore.YELLOW + "\n👤 Vous : " + Style.RESET_ALL, end="")


def print_info(msg: str):
    print(Fore.CYAN + f"  ℹ  {msg}")


def print_warning(msg: str):
    print(Fore.YELLOW + f"  ⚠  {msg}")


def print_error(msg: str):
    print(Fore.RED + f"  ✗  {msg}")


def print_success(msg: str):
    print(Fore.GREEN + f"  ✓  {msg}")


def print_loading(msg: str = "Réflexion en cours..."):
    print(Fore.MAGENTA + f"  ⟳  {msg}", end="\r")


def print_circuit_card(
    circuit: dict,
    rank: int,
    score: float,
    transport: str = "voiture",
    tarif: str = "etranger"):
    print(Fore.CYAN + f"\n  ┌─ #{rank} " + "─" * 50)
    nom = circuit.get("nom", circuit.get("circuit_id", "Circuit inconnu"))
    print(Fore.CYAN + "  │ " + Fore.WHITE + Style.BRIGHT + f"🗺  {nom}")

    duree = circuit.get("duree_totale", "?")
    mapping_cout = {
        'resident': 'cout_resident', 'résident': 'cout_resident',
        'etudiant': 'cout_etudiant', 'étudiant': 'cout_etudiant',
        'etranger': 'cout_etranger', 'étranger': 'cout_etranger',
        'enseignant': 'cout_enseignant',
        'retraite': 'cout_retraite', 'retraité': 'cout_retraite',
        'enfant': 'cout_enfant',
    }
    col_prix = mapping_cout.get(tarif, 'cout_etranger')
    prix = circuit.get(col_prix) or circuit.get('cout_etranger') or "?"
    print(
        Fore.CYAN
        + "  │ "
        + Fore.WHITE
        + f"⏱  Durée : {duree} min  |  💰 Prix : {prix} DT  |  ⭐ Score : {score:.0%}"
    )

    monuments = circuit.get("monuments", circuit.get("noms", []))
    if isinstance(monuments, list) and monuments:
        extrait = monuments[:3]
        suite = f" + {len(monuments) - 3} autres" if len(monuments) > 3 else ""
        print(
            Fore.CYAN
            + "  │ "
            + Fore.WHITE
            + f"🏛  {', '.join(str(m) for m in extrait)}{suite}"
        )

    # ── Distances entre lieux consécutifs ─────────────────────
    if isinstance(monuments, list) and len(monuments) >= 2:
        # Normaliser le transport
        transport_norm = transport.lower() if transport else "voiture"
        if transport_norm in ("a_pied", "à pied", "marche", "pied"):
            col_duree = "duree_pied_min"
            icone_transport = "🚶"
        elif transport_norm in ("velo", "vélo", "bicyclette", "bike"):
            col_duree = "duree_velo_min"
            icone_transport = "🚴"
        else:
            col_duree = "duree_voiture_min"
            icone_transport = "🚗"

        distances = charger_distances_circuit(monuments)

        if distances:
            print(
                Fore.CYAN + "  │ " + Fore.YELLOW + f"  {icone_transport} Itinéraire :"
            )
            for d in distances:
                f_lieu = d.get("from_lieu", "?")
                t_lieu = d.get("to_lieu", "?")
                dist_km = d.get("distance_km")
                duree_t = d.get(col_duree)

                dist_str = f"{dist_km} km" if dist_km is not None else "? km"
                duree_str = f"{duree_t} min" if duree_t is not None else "? min"

                print(
                    Fore.CYAN
                    + "  │   "
                    + Fore.WHITE
                    + f"{f_lieu} → {t_lieu}  "
                    + Fore.YELLOW
                    + f"({dist_str}, {duree_str})"
                )

    print(Fore.CYAN + "  └" + "─" * 55)


# ─────────────────────────────────────────────────────────────
# INTERFACE GROQ
# ─────────────────────────────────────────────────────────────


def init_groq_client():
    try:
        from groq import Groq
    except ImportError:
        print_error(
            "Package 'groq' non installé. Lance : pip install groq colorama psycopg2-binary"
        )
        sys.exit(1)

    if not GROQ_API_KEY:
        print_error("Variable GROQ_API_KEY non définie.")
        print_warning('Lance : export GROQ_API_KEY="gsk_..."  puis relance chat.py')
        sys.exit(1)

    return Groq(api_key=GROQ_API_KEY)


def ask_llm(
    client,
    messages: list,
    system: str = "",
    temperature: float = 0.7,
    model: str | None = None
) -> str:
    """Appelle l'API Groq avec gestion d'erreurs complète."""
    used_model = model or MODEL_CHAT
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    try:
        print_loading()
        response = client.chat.completions.create(
            model=used_model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=1024,
        )
        print(" " * 50, end="\r")
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(" " * 50, end="\r")
        err = str(e)
        if "api_key" in err.lower() or "401" in err:
            return "⚠ Clé API Groq invalide. Vérifiez la variable GROQ_API_KEY."
        if "rate_limit" in err.lower() or "429" in err:
            time.sleep(3)
            return "⚠ Limite de requêtes atteinte. Réessayez dans quelques secondes."
        if "model" in err.lower():
            # Fallback sur 8b si le modèle 70b n'est pas dispo sur ce compte
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=full_messages,
                    temperature=temperature,
                    max_tokens=1024,
                )
                return response.choices[0].message.content.strip()
            except Exception:
                pass
        return f"⚠ Erreur Groq : {err}"


# ─────────────────────────────────────────────────────────────
# CHARGEMENT SYSTÈME (PostgreSQL)
# ─────────────────────────────────────────────────────────────


def charger_systeme_pg():
    """
    Charge clients et circuits depuis PostgreSQL sig_dourbia.
    Initialise les agents si possible.
    Retourne (systeme, agent, clients_brut, circuits_brut).
    """

    if not test_connexion():
        print_error("Impossible de joindre PostgreSQL. Vérifiez DB_CONFIG dans db.py")
        sys.exit(1)

    print_loading("Chargement depuis PostgreSQL...")
    clients_brut = charger_tous_clients()
    circuits_brut = charger_tous_circuits()
    print(" " * 50, end="\r")

    print_success(f"{len(clients_brut)} clients chargés depuis sig_dourbia.")
    print_success(f"{len(circuits_brut)} circuits chargés depuis sig_dourbia.")

    systeme = agent = None
    try:
        from Matching_client_circuit import SystemeRecommandation
        from Agent_principal import AgentRecommandationPrincipal

        # On passe les données déjà en mémoire via un adaptateur léger
        systeme = _SystemePG(clients_brut, circuits_brut)
        agent = AgentRecommandationPrincipal(systeme)
        print_success("Système multi-agents initialisé.")
    except Exception as e:
        print_warning(f"Agents indisponibles ({e}) → mode scoring simplifié.")

    return systeme, agent, clients_brut, circuits_brut


class _SystemePG:
    """
    Adaptateur minimal qui expose l'interface attendue par les agents
    (get_client, calculateur.circuits, simuler_feedback)
    à partir des données chargées depuis PostgreSQL.
    """

    def __init__(self, clients_brut: dict, circuits_brut: list):
        import pandas as pd
        from PertinenceCalculator import PertinenceCalculator
        from Standarisation_Clients import ClientProfile

        self.circuits_brut = circuits_brut

        # Calculateur de pertinence alimenté avec les circuits PG
        self.calculateur = PertinenceCalculator()
        self.calculateur.circuits = circuits_brut  # injection directe

        # Construire les objets ClientProfile
        self.clients = {}
        for uid, data in clients_brut.items():
            try:
                types_preferes = data.get("types_preferes", [])
                epoques = list(data.get("preferences_thematiques", {}).keys())
                row_data = {
                    "user_id": uid,
                    "preference_fonction": (
                        ", ".join(types_preferes) if types_preferes else ""
                    ),
                    "preference_epoque": ", ".join(epoques) if epoques else "",
                    "mobilite": data.get("mobilité", data.get("mobilite", "normale")),
                    "zone": data.get("zone_preferee", "Mixte"),
                    "type_tarif": data.get("type_tarif", "resident"),
                    "duree_visite_min": data.get("duree_max", 180),
                    "budget_max": data.get("budget_max", None),
                    "nb_pois": len(types_preferes) if types_preferes else 5,
                }
                c = ClientProfile(pd.Series(row_data))
                c.types_preferes = types_preferes
                c.preference_epoque = epoques
                c.budget_max = data.get("budget_max", None)
                c.duree_max = data.get("duree_max", 180)
                c.mobilite = row_data["mobilite"]
                c.type_tarif = row_data["type_tarif"]
                c.transport = data.get("transport", "voiture")
                c.historique_circuits = data.get("historique_circuits", [])
                c.historique_notes = data.get("historique_notes", {})
                self.clients[uid] = c
            except Exception:
                pass

        self.nb_clients = len(self.clients)
        self.nb_circuits = len(circuits_brut)
        self.historique_recommandations = []

    def get_client(self, user_id: str):
        client = self.clients.get(user_id)
        if client:
            return client
        # Recherche partielle (ex: "42" → "CLIENT_0042")
        for k, v in self.clients.items():
            if user_id in k or k.endswith(user_id.split("_")[-1]):
                return v
        return None

    def simuler_feedback(self, user_id: str, circuit_id: str, note: float):

        sauvegarder_feedback(user_id, circuit_id, note)
        c = self.get_client(user_id)
        if c:
            if not hasattr(c, "historique_circuits"):
                c.historique_circuits = []
            c.historique_circuits.append(circuit_id)
            if not hasattr(c, "historique_notes"):
                c.historique_notes = {}
            c.historique_notes[circuit_id] = note

    def recommander_pour_client(self, user_id: str, n_recommandations: int = 3) -> dict:
        client = self.get_client(user_id)
        if not client:
            return {"error": f"Client {user_id} non trouvé"}
        exclure_ids = getattr(client, "historique_circuits", [])
        try:
            recs = self.calculateur.recommander(
                profil=client,
                n_recommandations=n_recommandations,
                exclure_ids=exclure_ids,
            )
        except Exception as e:
            recs = []
        return {
            "user_id": user_id,
            "recommandations": recs,
            "nb_recommandations": len(recs),
        }


# ─────────────────────────────────────────────────────────────
# SCORING SIMPLIFIÉ (mode dégradé — nouveaux clients)
# ─────────────────────────────────────────────────────────────


def recommander_degrade(profil: dict, circuits: list, n: int = 3) -> list:
    budget = float(profil.get("budget_max", profil.get("budget", 9999)) or 9999)
    duree_max = float(profil.get("duree_max", profil.get("duree", 9999)) or 9999)
    mobilite = profil.get("mobilite", "normale")
    transport = profil.get("transport", "")

    scored = []
    for c in circuits:
        score = 0.5

        try:
            prix = float(
                str(
                    c.get("cout_etranger") or c.get("cout_resident") or None
                ).replace(",", ".")
                or 0
            )
            if prix <= budget:
                score += 0.2
            elif prix <= budget * 1.2:
                score += 0.05
        except Exception:
            pass

        try:
            if float(c.get("duree_totale", 9999)) <= duree_max:
                score += 0.15
        except Exception:
            pass

        try:
            pop = float(c.get("score_moyen", c.get("popularite", 0)) or 0)
            score += (pop / 5.0) * 0.1
        except Exception:
            pass

        if mobilite == "reduite":
            if not c.get("accessible_mobilite_reduite", c.get("accessible", False)):
                score -= 0.1

        transport_circuit = c.get("mode_transport", c.get("transport", ""))
        if transport and transport_circuit:
            if transport.lower() in str(transport_circuit).lower():
                score += 0.05

        scored.append((c, min(max(score, 0.0), 1.0)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:n]


# ─────────────────────────────────────────────────────────────
# EXTRACTION D'ENTITÉS VIA LLM  —  CORRECTION 2
# ─────────────────────────────────────────────────────────────

SYSTEM_EXTRACTION = """\
Tu es un extracteur d'entités JSON pour un système touristique en Tunisie.
Réponds UNIQUEMENT avec un objet JSON valide.
PAS de texte avant, PAS de texte après, PAS de balises markdown, PAS de ```json.
Juste le JSON brut, rien d'autre.

Champs possibles :
- "destination"  : string (ville ou région en Tunisie)
- "epoques"      : liste parmi ["romaine","islamique","punique","ottomane","moderne","prehistorique"]
- "types"        : liste parmi ["culturel","nature","religieux","historique","familial","aventure"]
- "mobilite"     : une valeur parmi ["reduite","normale"]
- "duree"        : nombre entier en minutes
- "transport"    : une valeur parmi ["a_pied","velo","voiture","autre"]
- "budget"       : nombre entier en DT
- "tarif"        : une valeur parmi ["resident","etudiant","etranger","enseignant","retraite","enfant"]
- "user_id"      : string (ex: CLIENT_0042)
- "circuit_id"   : string
- "note"         : nombre entre 0 et 5
- "commentaire"  : string

Synonymes :
  mobilité réduite/PMR/handicap/fauteuil → "reduite"
  à pied/marche                          → "a_pied"
  vélo/bicyclette/bike                   → "velo"
  voiture/auto/taxi/motorisé             → "voiture"

Si rien à extraire → {}
Exemple correct : {"destination":"Djerba","budget":80,"mobilite":"normale"}
"""


def extraire_entites(client, user_msg: str) -> dict:
    """
    CORRECTION 2 : extraction JSON robuste avec 3 stratégies de parsing.
    """
    raw = ask_llm(
        client,
        [{"role": "user", "content": user_msg}],
        system=SYSTEM_EXTRACTION,
        temperature=0.0,  # déterministe pour JSON
        model=MODEL_EXTRACTION,
    )

    if not raw or raw.startswith("⚠"):
        return {}

    # Stratégie 1 : le modèle a bien suivi et retourné du JSON pur
    raw_clean = raw.strip()
    if raw_clean.startswith("{"):
        try:
            return json.loads(raw_clean)
        except json.JSONDecodeError:
            pass

    # Stratégie 2 : extraire le premier bloc JSON même avec du texte autour
    # Ce regex capture les accolades IMBRIQUÉES (listes incluses)
    depth = 0
    start = None
    for i, ch in enumerate(raw_clean):
        if ch == "{":
            if start is None:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                fragment = raw_clean[start : i + 1]
                try:
                    return json.loads(fragment)
                except json.JSONDecodeError:
                    break

    # Stratégie 3 : nettoyage des backticks markdown puis retry
    cleaned = re.sub(r"```(?:json)?", "", raw_clean).strip()
    if cleaned.startswith("{"):
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # Rien trouvé — retour silencieux (pas de crash)
    return {}


# ─────────────────────────────────────────────────────────────
# GÉNÉRATION D'EXPLICATIONS VIA LLM
# ─────────────────────────────────────────────────────────────

SYSTEM_EXPLICATION = """\
Tu es un guide touristique expert, passionné et chaleureux, spécialisé en Tunisie.
Tu présentes des recommandations de circuits en français, de façon naturelle et convaincante.
Pour chaque circuit : 2-3 phrases. Mets en avant l'expérience vécue, pas les chiffres.
Commence par une phrase d'accroche personnalisée selon le profil du visiteur."""


def generer_explication(
    client, profil_resume: str, circuits_data: list, tarif: str = "etranger"
) -> str:
    mapping_cout = {
        "resident": "cout_resident",
        "résident": "cout_resident",
        "etudiant": "cout_etudiant",
        "étudiant": "cout_etudiant",
        "etranger": "cout_etranger",
        "étranger": "cout_etranger",
        "enseignant": "cout_enseignant",
        "retraite": "cout_retraite",
        "retraité": "cout_retraite",
        "enfant": "cout_enfant",
    }
    col_prix = mapping_cout.get(tarif, "cout_etranger")

    circuits_txt = "\n".join(
        [
            f"Circuit {i+1} — {c.get('nom', c.get('circuit_id', 'Circuit'))} : "
            f"durée {c.get('duree_totale', '?')} min, "
            f"prix {c.get(col_prix) or c.get('cout_etranger') or c.get('prix', '?')} DT, "
            f"monuments : {', '.join(str(m) for m in c.get('monuments', c.get('noms', []))[:4])}"
            for i, c in enumerate(circuits_data)
        ]
    )
    prompt = (
        f"Profil : {profil_resume}\n\n"
        f"Circuits recommandés :\n{circuits_txt}\n\n"
        f"Présente ces circuits de façon personnalisée et enthousiaste."
    )
    return ask_llm(
        client,
        [{"role": "user", "content": prompt}],
        system=SYSTEM_EXPLICATION,
        temperature=0.75,
    )


# ─────────────────────────────────────────────────────────────
# APPEL AGENT PRINCIPAL  —  CORRECTION 3
# ─────────────────────────────────────────────────────────────


def appeler_agent_principal(
    agent, systeme, user_id: str, circuits_brut: list, n: int = 3
) -> list:
    """
    Appelle recommander_intelligemment() et consomme CORRECTEMENT
    le dict retourné (clé 'recommandations', pas itération directe).
    Retourne une liste de tuples (circuit_dict, score).
    """
    try:
        resultat = agent.recommander_intelligemment(user_id, n=n)

        # CORRECTION 3 : le retour est un dict, pas une liste
        if not isinstance(resultat, dict):
            raise ValueError("Format de retour inattendu de recommander_intelligemment")
        if not resultat.get("success", False):
            raise ValueError(resultat.get("error", "Erreur inconnue"))

        recs_raw = resultat.get("recommandations", [])
        recs = []
        for r in recs_raw:
            cid = r.get("circuit_id", r.get("id", ""))
            score = float(
                r.get("score_global", r.get("score_final", r.get("score", 0.5)))
            )
            # Retrouver les données complètes du circuit dans circuits_brut
            c_data = next(
                (
                    c
                    for c in circuits_brut
                    if c.get("circuit_id") == cid or c.get("id") == cid
                ),
                r,  # fallback : utiliser le dict de la reco lui-même
            )
            recs.append((c_data, score))
        return recs

    except Exception as e:
        print_warning(f"Agent principal : {e} → scoring simplifié.")
        return []  # le caller utilisera recommander_degrade en fallback


# ─────────────────────────────────────────────────────────────
# CONSTRUCTION DU CONTEXTE CIRCUIT POUR LE LLM
# ─────────────────────────────────────────────────────────────


def construire_contexte_circuits(recs_circuits: list, tarif: str = "etranger") -> str:
    if not recs_circuits:
        return "Aucun circuit disponible."

    mapping_cout = {
        "resident": "cout_resident",
        "résident": "cout_resident",
        "etudiant": "cout_etudiant",
        "étudiant": "cout_etudiant",
        "etranger": "cout_etranger",
        "étranger": "cout_etranger",
        "enseignant": "cout_enseignant",
        "retraite": "cout_retraite",
        "retraité": "cout_retraite",
        "enfant": "cout_enfant",
    }
    col_prix = mapping_cout.get(tarif, "cout_etranger")
    lignes = []
    for i, (c, _) in enumerate(recs_circuits, 1):
        prix = (
            c.get(col_prix)
            or c.get("cout_etranger")
            or c.get("cout_total")
            or c.get("prix")
        )
        prix_str = (
            f"{prix} DT"
            if prix not in (None, "", "NON DISPONIBLE")
            else "prix non disponible"
        )
        monuments = c.get("monuments", c.get("noms", []))
        mon_str = ", ".join(str(m) for m in monuments) or "non renseignés"
        lignes.append(
            f"Circuit {i} (ID: {c.get('circuit_id','?')})\n"
            f"  - Nom     : {c.get('nom', 'Circuit sans nom')}\n"
            f"  - Durée   : {c.get('duree_totale','?')} min\n"
            f"  - Prix    : {prix_str}\n"
            f"  - Monuments : {mon_str}"
        )
    return "\n\n".join(lignes)


# ─────────────────────────────────────────────────────────────
# MODE 1 : CLIENT EXISTANT
# ─────────────────────────────────────────────────────────────


def mode_client_existant(
    client, systeme, agent, clients_brut: dict, circuits_brut: list
):
    historique_conv = []
    profil = None
    user_id = None
    recs_circuits = []  
    tarif_client = "etranger"
    print_bot(
        "Bonjour ! Je suis votre assistant de recommandation touristique. 🌍\n"
        "  Pouvez-vous me donner votre identifiant client ?\n"
        "  (Format : CLIENT_0001 — ou juste le numéro)"
    )

    while True:
        print_user_prompt()
        try:
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            print_bot("Au revoir et bonne visite en Tunisie ! 🌟")
            break

        if not user_input:
            continue
        if user_input.lower() in ["exit", "quitter", "quit", "q"]:
            print_bot("Au revoir et bonne visite en Tunisie ! 🌟")
            break

        # ── Étape 1 : résolution du user_id ───────────────────────
        if user_id is None:
            uid_resolved = _resoudre_user_id(user_input, clients_brut)
            if uid_resolved:
                user_id = uid_resolved
            else:
                # Tentative via LLM extraction
                entites = extraire_entites(client, user_input)
                if "user_id" in entites:
                    user_id = entites["user_id"]

        # ── Étape 2 : chargement du profil ────────────────────────
        if user_id and profil is None:
            profil = clients_brut.get(user_id)

            # Recherche partielle si non trouvé exact
            if profil is None:
                for k in clients_brut:
                    if user_id in k or k.endswith(user_id.split("_")[-1]):
                        user_id = k
                        profil = clients_brut[k]
                        break

            if profil is None:
                exemples = ", ".join(list(clients_brut.keys())[:4])
                print_bot(
                    f"Identifiant '{user_id}' introuvable.\n"
                    f"  Exemples valides : {exemples}..."
                )
                user_id = None
                continue

            # Affichage du profil
            _afficher_profil(user_id, profil)

            # Calcul des recommandations
            print_loading("Calcul des recommandations personnalisées...")
            recs_circuits = appeler_agent_principal(
                agent, systeme, user_id, circuits_brut
            )
            if not recs_circuits:
                recs_circuits = recommander_degrade(profil, circuits_brut, n=3)

            transport_client = (
                profil.get("transport", "voiture") if profil else "voiture"
            )

            tarif_client = profil.get("type_tarif", profil.get("tarif", "etranger")) if profil else "etranger"
            for i, (circuit, score) in enumerate(recs_circuits, 1):
                print_circuit_card(circuit, i, score, transport=transport_client, tarif=tarif_client)

            profil_resume = _resume_profil(user_id, profil)
            explication = generer_explication(
                client, profil_resume, [c for c, _ in recs_circuits], tarif=tarif_client
            )
            print_bot(explication)
            print_bot(
                "Des questions sur ces circuits ? Vous pouvez aussi noter "
                "un circuit en donnant une note de 0 à 5."
            )
            continue  # attendre la prochaine saisie

        # ── Étape 3 : conversation post-chargement ────────────────
        if profil is None:
            # Pas encore de profil (l'utilisateur n'a pas fourni un ID valide)
            print_bot(
                "Je n'ai pas encore pu identifier votre profil. "
                "Pouvez-vous me donner votre identifiant client ?"
            )
            continue

        entites = extraire_entites(client, user_input)

        # Détection d'une question explicite (ne pas confondre avec un feedback)
        mots_question = [
            "parle",
            "dis",
            "explique",
            "décris",
            "détail",
            "info",
            "raconte",
            "montre",
            "présente",
            "qu'est",
            "quels",
            "?",
            "comment",
            "pourquoi",
            "combien",
            "quelle",
            "quel",
        ]
        est_question = any(m in user_input.lower() for m in mots_question)

        # ── Feedback ───────────────────────────────────────────────
        if "note" in entites and recs_circuits and not est_question:
            note = float(entites["note"])
            commentaire = entites.get("commentaire", "")
            cid = entites.get("circuit_id")
            if not cid and recs_circuits:
                cid = recs_circuits[0][0].get(
                    "circuit_id", recs_circuits[0][0].get("id", "")
                )

            # Persistance PostgreSQL

            if user_id and cid:
                sauvegarder_feedback(str(user_id), str(cid), note, commentaire)

            # Mise à jour via agent si disponible
            if agent and user_id and cid:
                try:
                    agent.traiter_feedback_utilisateur(user_id, cid, note, commentaire)
                except Exception:
                    pass

            print_success(
                f"Feedback enregistré en base : {note}/5"
                + (f' — "{commentaire}"' if commentaire else "")
            )
            print_bot("Merci pour votre retour ! Vos préférences ont été mises à jour.")
            continue

        # ── Conversation générale ──────────────────────────────────
        contexte = construire_contexte_circuits(recs_circuits, tarif=tarif_client)
        system_dyn = (
            "Tu es un assistant de recommandation touristique pour la Tunisie.\n"
            "Tu réponds en français, de façon concise et utile.\n\n"
            f"Circuits recommandés à ce visiteur :\n{contexte}\n\n"
            "RÈGLES :\n"
            "- Réponds UNIQUEMENT avec les informations ci-dessus.\n"
            "- Si le prix est 'prix non disponible', dis-le clairement.\n"
            "- N'invente AUCUN monument, prix ou détail absent des données.\n"
            "- Pour noter, l'utilisateur doit dire explicitement une note chiffrée."
        )

        # CORRECTION 4 : un seul append par tour (plus de doublon)
        historique_conv.append({"role": "user", "content": user_input})
        reponse = ask_llm(client, historique_conv[-8:], system=system_dyn)
        historique_conv.append({"role": "assistant", "content": reponse})
        print_bot(reponse)


# ─────────────────────────────────────────────────────────────
# MODE 2 : NOUVEAU CLIENT
# ─────────────────────────────────────────────────────────────

# Ordre de collecte imposé — NE PAS modifier l'ordre
CHAMPS_COLLECTE = [
    "destination",
    "epoques",
    "types",
    "mobilite",
    "duree",
    "transport",
    "budget",
    'tarif',
]

SYSTEM_ONBOARDING = """\
Tu es un conseiller touristique chaleureux spécialisé en Tunisie.
Tu collectes les préférences d'un nouveau visiteur pour lui recommander des circuits.

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
                          
Étape 8 — tarif : "Quelle est votre situation tarifaire ?
                    (résident tunisien, étudiant, étranger, enseignant, retraité, enfant)"

Quand les 8 étapes sont complètes, écris EXACTEMENT [PROFIL_COMPLET] puis résume chaleureusement.
Ne conclus pas la conversation après [PROFIL_COMPLET] : le système affiche les recommandations.
Reste concis et enthousiaste.\
"""


def mode_nouveau_client(groq_client, systeme, agent, circuits_brut: list):
    print_bot(
        "Bienvenue ! 🌍 Laissez-moi vous aider à trouver le circuit parfait en Tunisie.\n"
        "  Je vais vous poser 8 questions rapides."
    )

    historique = []
    profil_collecte = {}
    profil_temp = {}

    # Première question du LLM
    premiere = ask_llm(
        groq_client,
        [
            {
                "role": "user",
                "content": "Commence la collecte. Pose uniquement la première question.",
            }
        ],
        system=SYSTEM_ONBOARDING,
        temperature=0.6,
    )
    print_bot(premiere)
    historique.append({"role": "assistant", "content": premiere})

    profil_complet = False
    while not profil_complet:
        print_user_prompt()
        try:
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ["exit", "quitter", "quit", "q"]:
            print_bot("Au revoir ! N'hésitez pas à revenir. 🌟")
            return

        # Extraction et accumulation des entités
        entites = extraire_entites(groq_client, user_input)
        for champ in CHAMPS_COLLECTE:
            if champ in entites and entites[champ] not in (None, "", [], {}):
                profil_collecte[champ] = entites[champ]

        historique.append({"role": "user", "content": user_input})

        # CORRECTION 4 : on stocke la réponse UNE SEULE FOIS
        reponse = ask_llm(
            groq_client, historique[-12:], system=SYSTEM_ONBOARDING, temperature=0.6
        )

        # Garde-fou budget : bloquer [PROFIL_COMPLET] si budget manquant
        if "[PROFIL_COMPLET]" in reponse and "budget" not in profil_collecte:
            reponse = (
                reponse.replace("[PROFIL_COMPLET]", "").strip()
                + "\n\nUne dernière question : quel est votre budget "
                "approximatif en dinars tunisiens (DT) ? (ex: 50 DT, 100 DT)"
            )

        # Garde-fou transport PMR
        if (
            "transport" not in profil_collecte
            and profil_collecte.get("mobilite") == "reduite"
            and any(m in reponse.lower() for m in ["à pied", "a pied", "vélo", "velo"])
        ):
            reponse = (
                "Quel mode de transport préférez-vous ?\n"
                "Compte tenu de votre mobilité réduite, les options adaptées sont :\n"
                "  • voiture\n  • autre transport adapté PMR"
            )

        # UN SEUL append assistant (CORRECTION 4)
        historique.append({"role": "assistant", "content": reponse})

        if "[PROFIL_COMPLET]" in reponse:
            profil_complet = True
            print_bot(
                reponse.replace("[PROFIL_COMPLET]", "").strip()
                or "Parfait, j'ai tout ce qu'il me faut !"
            )
        else:
            print_bot(reponse)

    # Vérification minimale
    champs_presents = [c for c in CHAMPS_COLLECTE if c in profil_collecte]
    if len(champs_presents) < 3:
        print_warning(
            "Pas assez d'informations collectées pour une recommandation fiable."
        )
        return

    # Récapitulatif
    print_separator()
    print_info(f"Destination  : {profil_collecte.get('destination', 'non renseignée')}")
    print_info(f"Époques      : {profil_collecte.get('epoques', [])}")
    print_info(f"Types        : {profil_collecte.get('types', [])}")
    print_info(f"Mobilité     : {profil_collecte.get('mobilite', 'normale')}")
    print_info(f"Durée max    : {profil_collecte.get('duree', '?')} min")
    print_info(f"Transport    : {profil_collecte.get('transport', 'non renseigné')}")
    print_info(f"Budget       : {profil_collecte.get('budget', '?')} DT")
    print_info(f"Tarif        : {profil_collecte.get('tarif', 'non renseigné')}")

    print_separator()

    # Profil temporaire structuré
    profil_temp = {
        "destination": profil_collecte.get("destination", ""),
        "budget_max": profil_collecte.get("budget", 100),
        "duree_max": profil_collecte.get("duree", 300),
        "epoques_preferees": profil_collecte.get("epoques", []),
        "types_preferes": profil_collecte.get("types", []),
        "mobilite": profil_collecte.get("mobilite", "normale"),
        "transport": profil_collecte.get("transport", "voiture"),
        "tarif": profil_collecte.get("tarif", "etranger"),
    }
    # Générer un user_id unique pour ce nouveau client
    from datetime import datetime as _dt

    nouveau_id = f"CLIENT_{_dt.now().strftime('%Y%m%d%H%M%S')}"
    profil_temp["user_id"] = nouveau_id

    # Persister en PostgreSQL

    if sauvegarder_client(profil_temp):
        print_success(f"Profil sauvegardé : {nouveau_id}")
    else:
        print_warning("Profil non persisté (base inaccessible)")

    # CORRECTION 5 : essayer les vrais agents avant le mode dégradé
    print_loading("Calcul des recommandations personnalisées...")
    recs_circuits = []

    if systeme and agent:
        # Injection du profil temporaire comme client virtuel
        try:
            import pandas as pd
            from Standarisation_Clients import ClientProfile

            row_data = {
                "user_id": "VISITEUR_TEMP",
                "preference_fonction": ", ".join(profil_temp["types_preferes"]),
                "preference_epoque": ", ".join(profil_temp["epoques_preferees"]),
                "mobilite": profil_temp["mobilite"],
                "zone": "Mixte",
                "type_tarif": profil_temp["tarif"],
                "duree_visite_min": profil_temp["duree_max"],
                "budget_max": profil_temp["budget_max"],
                "nb_pois": 5,
            }
            c_tmp = ClientProfile(pd.Series(row_data))
            c_tmp.types_preferes = profil_temp["types_preferes"]
            c_tmp.preference_epoque = profil_temp["epoques_preferees"]
            c_tmp.budget_max = profil_temp["budget_max"]
            c_tmp.duree_max = profil_temp["duree_max"]
            c_tmp.mobilite = profil_temp["mobilite"]
            c_tmp.transport = profil_temp["transport"]
            c_tmp.type_tarif = profil_temp["tarif"]
            c_tmp.historique_circuits = []

            raw_recs = systeme.calculateur.recommander(
                profil=c_tmp, n_recommandations=3, exclure_ids=[]
            )
            for r in raw_recs:
                cid = r.get("circuit_id", "")
                score = float(r.get("score_global", 0.5))
                c_data = next(
                    (c for c in circuits_brut if c.get("circuit_id") == cid), r
                )
                recs_circuits.append((c_data, score))
        except Exception as e:
            print_warning(f"Scoring via calculateur échoué ({e}) → mode dégradé.")

    if not recs_circuits:
        recs_circuits = recommander_degrade(profil_temp, circuits_brut, n=3)

    print_separator()
    for i, (circuit, score) in enumerate(recs_circuits, 1):
        print_circuit_card(
            circuit, i, score, transport=profil_temp.get("transport", "voiture"),tarif=profil_temp.get('tarif', 'etranger')
        )

    epoques_str = " et ".join(profil_temp["epoques_preferees"]) or "variés"
    profil_resume = (
        f"Visiteur souhaitant découvrir {profil_temp['destination'] or 'la Tunisie'}, "
        f"passionné par {epoques_str}, mobilité {profil_temp['mobilite']}, "
        f"transport {profil_temp['transport']}, budget {profil_temp['budget_max']} DT, "
        f"durée max {profil_temp['duree_max']} min"
    )
    explication = generer_explication(
        groq_client, profil_resume, [c for c, _ in recs_circuits],tarif=profil_temp.get('tarif', 'etranger')
    )
    print_bot(explication)
    print_bot(
        "Ces circuits vous intéressent ? Vous pouvez :\n"
        '  • préciser une préférence (ex: "je préfère un budget de 80 DT")\n'
        '  • demander des détails  (ex: "parle-moi du circuit 2")\n'
        "  • taper 'quitter' pour terminer"
    )

    # ── Boucle de suivi / affinement ──────────────────────────────
    historique_suivi = []

    while True:
        print_user_prompt()
        try:
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quitter", "quit", "q", "merci", "non merci"]:
            print_bot("Merci et bonne découverte de la Tunisie ! 🌟")
            break

        nouvelles = extraire_entites(groq_client, user_input)
        maj_champs = {
            k: v
            for k, v in nouvelles.items()
            if k
            in [
                "destination",
                "budget",
                "duree",
                "epoques",
                "types",
                "mobilite",
                "transport",
            ]
            and v not in (None, "", [], {})
        }

        if maj_champs:
            # Mise à jour du profil et recalcul
            if "destination" in maj_champs:
                profil_temp["destination"] = maj_champs["destination"]
            if "budget" in maj_champs:
                profil_temp["budget_max"] = maj_champs["budget"]
            if "duree" in maj_champs:
                profil_temp["duree_max"] = maj_champs["duree"]
            if "epoques" in maj_champs:
                profil_temp["epoques_preferees"] = maj_champs["epoques"]
            if "types" in maj_champs:
                profil_temp["types_preferes"] = maj_champs["types"]
            if "mobilite" in maj_champs:
                profil_temp["mobilite"] = maj_champs["mobilite"]
            if "transport" in maj_champs:
                profil_temp["transport"] = maj_champs["transport"]

            recs_circuits = recommander_degrade(profil_temp, circuits_brut, n=3)
            print_separator()
            for i, (circuit, score) in enumerate(recs_circuits, 1):
                print_circuit_card(circuit, i, score,transport=profil_temp.get('transport', 'voiture'),tarif=profil_temp.get('tarif', 'etranger'))
            print_bot(
                generer_explication(
                    groq_client,
                    profil_resume,
                    [c for c, _ in recs_circuits],
                    tarif=profil_temp.get("tarif", "etranger")
                )
            )
        else:
            contexte = construire_contexte_circuits(recs_circuits, tarif=profil_temp.get('tarif', 'etranger'))
            system_suivi = (
                "Tu es un guide touristique expert en Tunisie. Tu réponds en français.\n\n"
                f"Circuits disponibles pour ce visiteur :\n{contexte}\n\n"
                "RÈGLES ABSOLUES :\n"
                "- Réponds UNIQUEMENT avec les informations ci-dessus.\n"
                "- Si le prix est 'prix non disponible', dis-le clairement.\n"
                "- N'invente AUCUN monument, prix ou détail absent des données.\n"
                "- Si une information est absente, dis-le clairement."
            )
            # CORRECTION 4 : un seul append par tour
            historique_suivi.append({"role": "user", "content": user_input})
            reponse = ask_llm(groq_client, historique_suivi[-6:], system=system_suivi)
            historique_suivi.append({"role": "assistant", "content": reponse})
            print_bot(reponse)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────


def _resoudre_user_id(user_input: str, clients_brut: dict) -> str | None:
    """
    Tente de résoudre un identifiant client depuis la saisie brute.
    Gère : CLIENT_42, client_0042, 42, 0042, user_42, etc.
    """
    s = user_input.strip().lower()

    # Format exact client_NNNN / user_NNNN
    m = re.match(r"^(client|user)_(\d+)$", s)
    if m:
        prefix, num = m.group(1), m.group(2)
        candidate = f"{prefix}_{num.zfill(4)}"
        if candidate in clients_brut:
            return candidate
        # Chercher la clé qui contient ce numéro
        for k in clients_brut:
            if k.lower().endswith(f"_{num}") or k.lower().endswith(f"_{num.zfill(4)}"):
                return k
        return None

    # Numéro seul : 1 à 4 chiffres
    m = re.match(r"^(\d{1,4})$", s)
    if m:
        num = m.group(1)
        for prefix in ("client", "user"):
            for pad in (num, num.zfill(2), num.zfill(3), num.zfill(4)):
                candidate = f"{prefix}_{pad}"
                if candidate in clients_brut:
                    return candidate
        return None

    return None


def _afficher_profil(user_id: str, profil: dict):
    epoques = profil.get(
        "epoques_preferees", list(profil.get("preferences_thematiques", {}).keys())
    )
    types = profil.get("types_preferes", [])
    budget = profil.get("budget_max", profil.get("budget", "?"))
    duree = profil.get("duree_max", profil.get("duree", "?"))
    mobilite = profil.get("mobilite", profil.get("mobilité", "non renseigné"))
    transport = profil.get("transport", profil.get("mode_transport", "non renseigné"))
    destination = profil.get("destination", "non renseignée")

    print_separator()
    print_success(f"Profil '{user_id}' chargé.")
    print_info(f"Destination        : {destination}")
    print_info(f"Époques préférées  : {epoques or 'non renseigné'}")
    print_info(f"Types de sites     : {types or 'non renseigné'}")
    print_info(f"Mobilité           : {mobilite}")
    print_info(f"Durée maximum      : {duree} min")
    print_info(f"Transport          : {transport}")
    print_info(f"Budget maximum     : {budget} DT")
    print_separator()


def _resume_profil(user_id: str, profil: dict) -> str:
    epoques = profil.get(
        "epoques_preferees", list(profil.get("preferences_thematiques", {}).keys())
    )
    mobilite = profil.get("mobilite", profil.get("mobilité", "normale"))
    transport = profil.get("transport", "voiture")
    budget = profil.get("budget_max", profil.get("budget", "?"))
    duree = profil.get("duree_max", profil.get("duree", "?"))
    dest = profil.get("destination", "Tunisie")
    return (
        f"Client {user_id}, destination {dest}, "
        f"aime {'et '.join(epoques) if epoques else 'les sites variés'}, "
        f"mobilité {mobilite}, transport {transport}, "
        f"budget {budget} DT, durée max {duree} min"
    )


# ─────────────────────────────────────────────────────────────
# MENU PRINCIPAL
# ─────────────────────────────────────────────────────────────


def menu_principal() -> str:
    print_separator()
    print(Fore.CYAN + "\n  Que souhaitez-vous faire ?\n")
    print(
        Fore.WHITE
        + Style.BRIGHT
        + "    [1]"
        + Style.NORMAL
        + Fore.YELLOW
        + "  Recommandations pour un client existant (avec ID)"
    )
    print(
        Fore.WHITE
        + Style.BRIGHT
        + "    [2]"
        + Style.NORMAL
        + Fore.GREEN
        + "  Nouveau client — créer un profil et obtenir des recommandations"
    )
    print(
        Fore.WHITE + Style.BRIGHT + "    [Q]" + Style.NORMAL + Fore.RED + "  Quitter\n"
    )
    print_separator()
    print(Fore.WHITE + "  Votre choix : ", end="")
    try:
        return input().strip().upper()
    except (EOFError, KeyboardInterrupt):
        return "Q"


# ─────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────


def main():
    clear()
    print_header()

    print_info("Connexion à Groq (LLaMA 3.3 — 70b)...")
    groq_client = init_groq_client()
    print_success(f"Groq connecté — modèle '{MODEL_CHAT}' prêt.")

    print_info("Connexion à PostgreSQL (sig_dourbia)...")
    systeme, agent, clients_brut, circuits_brut = charger_systeme_pg()

    if not circuits_brut:
        print_error(
            "Aucun circuit chargé depuis PostgreSQL. Vérifiez la table 'circuits'."
        )
        sys.exit(1)

    while True:
        choix = menu_principal()

        if choix == "1":
            clear()
            print_header()
            print(Fore.CYAN + Style.BRIGHT + "  ── Mode : Client Existant ──\n")
            mode_client_existant(
                groq_client, systeme, agent, clients_brut, circuits_brut
            )

        elif choix == "2":
            clear()
            print_header()
            print(Fore.CYAN + Style.BRIGHT + "  ── Mode : Nouveau Client ──\n")
            mode_nouveau_client(groq_client, systeme, agent, circuits_brut)

        elif choix in ["Q", "QUITTER", "EXIT"]:
            clear()
            print(Fore.CYAN + "\n  À bientôt ! Bonne découverte de la Tunisie. 🌍\n")
            sys.exit(0)

        else:
            print_warning("Choix invalide. Entrez 1, 2 ou Q.")
            continue

        print_separator()
        print(Fore.WHITE + "\n  Appuyez sur Entrée pour revenir au menu...", end="")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)
        clear()
        print_header()


if __name__ == "__main__":
    main()
