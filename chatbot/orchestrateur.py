"""
orchestrateur.py — Cerveau central du chatbot touristique tunisien.

Pipeline complet :
1. Détection langue
2. Extraction signaux (regex, sans LLM)
3. Classification intention (LLM rapide)
4. Routing vers agents compétents
5. Collecte réponses agents (avec météo intégrée)
6. Synthèse narrative finale (LLM puissant)
7. Mise à jour mémoire

Usage :
    import asyncio
    from orchestrateur import OrchestratorAgent

    orchestrateur = OrchestratorAgent()
    reponse = asyncio.run(orchestrateur.handle_message("user-123", "Bonjour, je veux visiter Carthage"))
    print(reponse)
"""

import asyncio
import json
import logging
import re
import time
from typing import Optional

from groq import Groq

from constants import (
    GROQ_API_KEY,
    MODEL_FAST,
    MODEL_SMART,
    AGENT_TIMEOUT_SECONDS,
    ROUTING_TABLE,
    INTENTIONS_VALIDES,
    INTENT_CONFIDENCE_THRESHOLD,
    LIEUX_OUTDOOR,
    LIEUX_INDOOR,
    SYSTEM_PROMPT_ORCHESTRATEUR,
    SYSTEM_PROMPT_INTENTION,
    SYSTEM_PROMPT_SYNTHESE,
    FALLBACK_MESSAGES,
    CLARIFICATION_MESSAGES,
    PROPOSITION_CIRCUIT,
    texte_lieu,
    is_affirmation_circuit,
    INTENTIONS_BLOQUANT_CIRCUIT,
    contient_demande_reservation,
    get_langue_nom,
)
from session_memory import (
    get_history, set_history, get_profile, update_profile,
    append_to_history, _ensure_session,
)
from agent_meteo_wrapper import get_meteo_wrapper
from agent_circuits_wrapper import get_circuits_wrapper
from agent_reservation_wrapper import get_reservation_wrapper

log = logging.getLogger("chatbot.orchestrateur")
from profil_synthetique import ProfilSynthetique

import onboarding
from circuit_presentation import presenter_recommandations

# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATEUR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class OrchestratorAgent:
    """
    Agent orchestrateur central du chatbot touristique tunisien.

    Orchestre le pipeline complet : détection → routing → agents → synthèse.
    Utilise Groq/llama pour les appels LLM (modèle rapide pour classification,
    modèle puissant pour la synthèse narrative).
    """

    def __init__(self, systeme_recommandation=None):
        """
        Args:
            systeme_recommandation: Instance du système de recommandation (couche math).
                Optionnel — peut être injecté après via inject_systeme().
        """
        # Client Groq
        self._groq = Groq(api_key=GROQ_API_KEY)

        # Wrappers agents
        self._meteo = get_meteo_wrapper()
        self._circuits = get_circuits_wrapper(systeme_recommandation)
        self._reservation = get_reservation_wrapper()

        log.info("[ORCHESTRATEUR] Initialisé")
        log.info(f"  Météo disponible    : {self._meteo._available}")
        log.info(f"  Circuits disponible : {self._circuits._available}")
        log.info(f"  Réservation disponible : {self._reservation._available}")

    def inject_systeme(self, systeme) -> None:
        """
        Injecte le système de recommandation après init.
        À appeler depuis l'application une fois la DB chargée.
        """
        self._circuits.set_systeme(systeme)
        log.info("[ORCHESTRATEUR] Système de recommandation injecté")

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTHODE PRINCIPALE
    # ─────────────────────────────────────────────────────────────────────────

    async def handle_message(self, user_id: str, message: str) -> str:
        """
        Méthode principale appelée à chaque message utilisateur.

        Args:
            user_id: Identifiant unique de la session utilisateur
            message: Message brut de l'utilisateur (toute langue)

        Returns:
            Réponse finale en prose, dans la langue de l'utilisateur, style guide Aziz
        """
        start_ms = int(time.time() * 1000)
        log.info(f"[ORCHESTRATEUR] {user_id} → {message[:80]}")

        try:
            # ── ÉTAPE 1 : Détection langue ────────────────────────────────
            langue = self._detect_language(message)
            log.info(f"  Langue détectée : {langue}")

            # ── ÉTAPE 2 : Récupération historique et profil ───────────────
            historique = get_history(user_id)
            profil = get_profile(user_id)

            # ── ÉTAPE 2bis : Mode onboarding actif → on continue le probing ──
            if profil.get("mode_onboarding"):
                return await self._handle_onboarding_step(
                    user_id, message, profil, historique, langue
                )

            # ── ÉTAPE 2ter : Validation post-onboarding (ex: « ok » après recommandations) ──
            if profil.get("attente_validation_circuit") and is_affirmation_circuit(message):
                return await self._confirmer_circuits_en_attente(
                    user_id, message, profil, historique, langue
                )

            # ── ÉTAPE 3 : Extraction signaux (sans LLM) ───────────────────
            signaux = self._extract_profile_signals(message)
            log.info(f"  Signaux extraits : {signaux}")

            # ── ÉTAPE 4 : Classification intention (LLM rapide) ───────────
            intention_data = await self._detect_intent(message, langue, historique)
            intention = intention_data.get("intention", "SMALLTALK")
            confiance = intention_data.get("confiance", 0.5)
            derniere_intention = profil.get("derniere_intention", "")
            if derniere_intention == "RESERVATION" and intention in ("SMALLTALK", "CIRCUIT") and confiance < 0.90:
                intention = "RESERVATION"
                confiance = max(confiance, 0.85)
                log.info(f"  Intention corrigée → RESERVATION (sticky, dernière intention={derniere_intention})")
            if contient_demande_reservation(message):
                intention = "RESERVATION"
                confiance = max(confiance, 0.9)
                log.info("  Intention forcée → RESERVATION (mots-clés détectés)")
            entites = intention_data.get("entites", {})
            log.info(f"  Intention : {intention} (confiance={confiance:.2f})")

            # Si confiance trop faible → demander clarification
            if confiance < INTENT_CONFIDENCE_THRESHOLD and intention not in ("SMALLTALK", "FEEDBACK"):
                return CLARIFICATION_MESSAGES.get(langue, CLARIFICATION_MESSAGES["FR"])

            # Enrichir signaux avec entités détectées
            signaux.update({k: v for k, v in entites.items() if v and not signaux.get(k)})

            # Réinitialiser la proposition circuit si nouvelle intention forte
            if intention in INTENTIONS_BLOQUANT_CIRCUIT and confiance >= INTENT_CONFIDENCE_THRESHOLD:
                signaux["attente_confirmation_circuit"] = False

            # ── Déclenchement onboarding circuit (après exclusion RESERVATION, etc.) ──
            veut_circuit = intention == "CIRCUIT" or (
                intention not in INTENTIONS_BLOQUANT_CIRCUIT
                and profil.get("attente_confirmation_circuit")
                and is_affirmation_circuit(message)
            )
            if veut_circuit:
                return await self._start_onboarding(user_id, message, profil, historique, langue)

            # ── ÉTAPE 5 : Routing et appels agents ────────────────────────
            agents_responses = await self._route_to_agents(
                intention=intention,
                message=message,
                profil=profil,
                signaux=signaux,
                langue=langue,
                user_id=user_id,
                historique=historique,
            )
            log.info(f"  Agents appelés : {list(agents_responses.keys())}")

            # ── ÉTAPE 6 : Synthèse narrative finale ───────────────────────
            attente_circuit = profil.get("attente_confirmation_circuit", False)

            if intention == "RESERVATION" and "agent_reservation" in agents_responses:
                res_data = agents_responses["agent_reservation"]
                if res_data and isinstance(res_data, dict) and res_data.get("reponse"):
                    reponse_finale = res_data["reponse"]
                else:
                    reponse_finale = FALLBACK_MESSAGES.get(langue, FALLBACK_MESSAGES["FR"])
                attente_circuit = False

            elif intention == "SMALLTALK":
                reponse_finale = await self._respond_smalltalk(message, langue, historique)
            else:
                reponse_finale = await self._synthesize_response(
                    agents_responses=agents_responses,
                    langue=langue,
                    historique=historique,
                    message_utilisateur=message,
                    intention=intention,
                    profil=profil,
                )

            # ── Proposition de circuit (une seule fois par session) ───────
            if (
                intention != "RESERVATION"
                and not attente_circuit
                and not profil.get("proposition_circuit_faite")
                and not profil.get("mode_onboarding")
            ):
                lieu_propose = signaux.get("lieu", "") or profil.get("lieu", "")
                proposition = PROPOSITION_CIRCUIT.get(
                    langue, PROPOSITION_CIRCUIT["FR"]
                ).format(lieu=texte_lieu(langue, lieu_propose))
                reponse_finale = f"{reponse_finale.rstrip()}\n\n{proposition}"
                attente_circuit = True
                signaux["proposition_circuit_faite"] = True

            signaux["attente_confirmation_circuit"] = attente_circuit

            # ── ÉTAPE 7 : Mise à jour mémoire ─────────────────────────────
            await self._update_memory(
                user_id=user_id,
                message=message,
                reponse=reponse_finale,
                signaux=signaux,
                langue=langue,
                intention=intention,
                historique=historique,
                profil=profil,
            )

            latency_ms = int(time.time() * 1000) - start_ms
            log.info(f"[ORCHESTRATEUR] Réponse générée en {latency_ms}ms")

            return reponse_finale

        except Exception as e:
            log.error(f"[ORCHESTRATEUR] Erreur inattendue : {e}", exc_info=True)
            return FALLBACK_MESSAGES.get("FR", "Une erreur est survenue, réessayez dans quelques instants.")

    # ─────────────────────────────────────────────────────────────────────────
    # DÉTECTION LANGUE (sans LLM — regex)
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_language(self, message: str) -> str:
        """
        Détecte la langue du message par règles simples.
        Délègue à Agent Multilingue (TODO) pour les cas ambigus.

        Returns:
            Code langue : "FR", "EN", "AR", "IT", "DE"
        """
        msg = message.lower().strip()

        # Arabe : présence de caractères arabes
        if re.search(r'[\u0600-\u06FF]', message):
            return "AR"

        # Mots-clés forts par langue
        fr_keywords = r'\b(bonjour|je|tu|nous|vous|est|sont|avec|pour|dans|sur|qui|que|quoi|comment|combien|merci|salut|bonsoir)\b'
        en_keywords = r'\b(hello|hi|i|we|you|is|are|with|for|in|on|who|what|how|much|thanks|please|want|need|can)\b'
        it_keywords = r'\b(ciao|buongiorno|voglio|sono|con|per|nel|sulla|chi|cosa|come|grazie|salve)\b'
        de_keywords = r'\b(hallo|guten|ich|wir|sie|ist|sind|mit|für|in|auf|wer|was|wie|danke|bitte)\b'

        scores = {
            "FR": len(re.findall(fr_keywords, msg)),
            "EN": len(re.findall(en_keywords, msg)),
            "IT": len(re.findall(it_keywords, msg)),
            "DE": len(re.findall(de_keywords, msg)),
        }

        best = max(scores, key=lambda k: scores[k])
        if scores[best] > 0:
            return best

        # Par défaut : français
        return "FR"

    # ─────────────────────────────────────────────────────────────────────────
    # EXTRACTION SIGNAUX (sans LLM — regex + règles)
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_profile_signals(self, message: str) -> dict:
        """
        Extrait les signaux du message sans LLM (regex + règles).
        Rapide, déterministe, sans latence réseau.

        Returns:
            Dict avec les signaux trouvés :
            {"budget": 150, "taille_groupe": 4, "type_groupe": "famille",
             "duree": "journée", "lieu": "Carthage", "outdoor_detected": True}
        """
        msg = message.lower()
        signaux = {}

        # ── Budget ────────────────────────────────────────────────────────
        budget_match = re.search(
            r'(\d+)\s*(?:dt|dinar|dinars|tnd|€|eur|euro|euros|\$|dollar)',
            msg
        )
        if budget_match:
            signaux["budget"] = int(budget_match.group(1))

        # ── Taille groupe ─────────────────────────────────────────────────
        groupe_match = re.search(
            r'(\d+)\s*(?:personne|personnes|adulte|adultes|enfant|enfants|pers\.?)',
            msg
        )
        if groupe_match:
            signaux["taille_groupe"] = int(groupe_match.group(1))
        elif re.search(r'\b(seul|solo|alone)\b', msg):
            signaux["taille_groupe"] = 1
        elif re.search(r'\b(couple|deux|2)\b', msg):
            signaux["taille_groupe"] = 2

        # ── Type de groupe ────────────────────────────────────────────────
        if re.search(r'\b(famille|family|enfant|enfants|kids?|children)\b', msg):
            signaux["type_groupe"] = "famille"
        elif re.search(r'\b(couple|romantique|lune de miel|honeymoon)\b', msg):
            signaux["type_groupe"] = "couple"
        elif re.search(r'\b(groupe|groupe scolaire|amis|friends|school)\b', msg):
            signaux["type_groupe"] = "groupe"
        elif re.search(r'\b(solo|seul|backpacker)\b', msg):
            signaux["type_groupe"] = "solo"

        # ── Durée ─────────────────────────────────────────────────────────
        if re.search(r'\b(demi.?journ[eé]e|half.?day|matinée|après.?midi)\b', msg):
            signaux["duree"] = "demi-journée"
        elif re.search(r'\b(journ[eé]e|journée entière|full.?day|toute la journée)\b', msg):
            signaux["duree"] = "journée"
        elif re.search(r'\b(week.?end|2 jours|deux jours)\b', msg):
            signaux["duree"] = "week-end"
        elif re.search(r'\b(\d+)\s*(?:jours?|days?)\b', msg):
            nb_match = re.search(r'(\d+)\s*(?:jours?|days?)', msg)
            if nb_match:
                signaux["duree"] = f"{nb_match.group(1)} jours"

        # ── Lieu ──────────────────────────────────────────────────────────
        lieux_connus = [
            "carthage", "médina", "medina", "bardo", "sidi bou saïd", "sidi bou said",
            "el jem", "dougga", "tozeur", "douz", "kairouan", "monastir", "mahdia",
            "hammamet", "nabeul", "bizerte", "tabarka", "ain draham", "tataouine",
            "matmata", "chenini", "sbeitla", "zaghouan", "kerkouane", "tunis",
        ]
        for lieu in lieux_connus:
            if lieu in msg:
                signaux["lieu"] = lieu.title()
                # Déterminer si outdoor
                signaux["outdoor_detected"] = lieu in LIEUX_OUTDOOR
                break

        # ── Type d'activité ───────────────────────────────────────────────
        if re.search(r'\b(historique|histoire|ruines?|archéologie|antiquité|romain|punique)\b', msg):
            signaux["type_activite"] = "historique"
        elif re.search(r'\b(musée|museum|expo|exposition)\b', msg):
            signaux["type_activite"] = "musee"
        elif re.search(r'\b(ar|vr|réalité augmentée|réalité virtuelle|immersif|numérique)\b', msg):
            signaux["type_activite"] = "ar_vr"
        elif re.search(r'\b(nature|randonnée|plage|mer|montagne|désert|sahara)\b', msg):
            signaux["type_activite"] = "nature"

        return signaux

    # ─────────────────────────────────────────────────────────────────────────
    # DÉTECTION INTENTION (LLM rapide)
    # ─────────────────────────────────────────────────────────────────────────

    async def _detect_intent(self, message: str, langue: str, historique: list = []) -> dict:
        """
        Classifie l'intention du message via LLM rapide (llama-3.1-8b-instant).
        Utilise un prompt JSON strict pour avoir un résultat parsable.

        Returns:
            {"intention": "CIRCUIT", "confiance": 0.92, "entites": {...}}
        """
        try:
            # Contexte conversationnel pour aider la classification
            dernier_contexte = ""
            if historique:
                derniers = historique[-4:]
                dernier_contexte = f"\nDerniers échanges : {json.dumps(derniers, ensure_ascii=False)[:300]}"

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._groq.chat.completions.create,
                    model=MODEL_FAST,
                    max_tokens=150,
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_INTENTION},
                        {"role": "user", "content": f"Message : {message}{dernier_contexte}"},
                    ],
                ),
                timeout=AGENT_TIMEOUT_SECONDS,
            )

            raw = (response.choices[0].message.content or "").strip()
            log.debug(f"[INTENT] Réponse brute : {raw}")

            result = json.loads(raw)

            if result.get("intention") not in INTENTIONS_VALIDES:
                result["intention"] = "SMALLTALK"
                result["confiance"] = 0.5

            tokens = getattr(response, 'usage', None)
            tokens_used = tokens.total_tokens if tokens and getattr(tokens, 'total_tokens', None) else 0
            log.debug(f"[INTENT] Tokens utilisés : {tokens_used}")

            return result

        except asyncio.TimeoutError:
            log.warning("[INTENT] Timeout détection intention")
            return {"intention": "SMALLTALK", "confiance": 0.5, "entites": {}}
        except json.JSONDecodeError as e:
            log.warning(f"[INTENT] JSON invalide : {e}")
            return self._fallback_intent_detection(message)
        except Exception as e:
            log.error(f"[INTENT] Erreur : {e}")
            return {"intention": "SMALLTALK", "confiance": 0.5, "entites": {}}

    def _fallback_intent_detection(self, message: str) -> dict:
        """Détection d'intention par mots-clés si le LLM échoue."""
        msg = message.lower()

        if any(w in msg for w in ["réserver", "réservation", "voiture", "hôtel", "louer", "location"]):
            return {"intention": "RESERVATION", "confiance": 0.8, "entites": {}}
        if any(w in msg for w in ["circuit", "itinéraire", "visite", "excursion", "pack", "famille", "journée"]):
            return {"intention": "CIRCUIT", "confiance": 0.75, "entites": {}}
        if any(w in msg for w in ["carthage", "bardo", "médina", "histoire", "monument", "ruines"]):
            return {"intention": "HISTORIQUE", "confiance": 0.75, "entites": {}}
        if any(w in msg for w in ["météo", "temps", "pluie", "soleil", "température", "weather"]):
            return {"intention": "METEO", "confiance": 0.85, "entites": {}}
        if any(w in msg for w in ["horaire", "prix", "tarif", "accès", "comment y aller", "transport"]):
            return {"intention": "PRATIQUE", "confiance": 0.75, "entites": {}}

        return {"intention": "SMALLTALK", "confiance": 0.6, "entites": {}}
    # ─────────────────────────────────────────────────────────────────────────
    # ROUTING ET APPELS AGENTS
    # ─────────────────────────────────────────────────────────────────────────

    async def _route_to_agents(
        self,
        intention: str,
        message: str,
        profil: dict,
        signaux: dict,
        langue: str,
        user_id: str,
        historique: list,
    ) -> dict:
        """
        Route vers les agents appropriés et collecte leurs réponses.
        Les agents sont appelés en parallèle quand possible.

        Returns:
            Dict {nom_agent: réponse_agent}
        """
        agents_to_call = ROUTING_TABLE.get(intention, ["orchestrateur"])
        responses = {}

        # ── Déterminer si on a besoin de la météo ────────────────────────
        # La météo est enrichie automatiquement pour tous les circuits outdoor
        lieu = signaux.get("lieu", "")
        need_meteo = (
            intention in ("METEO", "CIRCUIT")
            or any(l in message.lower() for l in LIEUX_OUTDOOR)
            or signaux.get("outdoor_detected", False)
        )

        # ── Appels en parallèle ───────────────────────────────────────────
        tasks = {}

        # Météo en premier (résultat utilisé par d'autres agents)
        if need_meteo or "agent_meteo" in agents_to_call:
            tasks["agent_meteo"] = self._call_agent_meteo(message, user_id)

        # Circuits (attend potentiellement la météo)
        if "agent_circuits" in agents_to_call or "moteur_math" in agents_to_call:
            tasks["agent_circuits"] = None  # Sera appelé après la météo

        # Réservation
        if "agent_reservation" in agents_to_call:
            try:
                reservation_data = await asyncio.wait_for(
                    self._call_agent_reservation(message, user_id),
                    timeout=100.0,  # subprocess dourbia : démarrage Python + LLM Groq
                )
                responses["agent_reservation"] = reservation_data
            except asyncio.TimeoutError:
                log.warning("[ORCHESTRATEUR] Timeout agent réservation")
                responses["agent_reservation"] = {"disponible": False, "reponse": None, "erreur": "timeout"}
            except Exception as e:
                log.warning(f"[ORCHESTRATEUR] Erreur agent réservation : {e}", exc_info=True)
                responses["agent_reservation"] = {"disponible": False, "reponse": None, "erreur": str(e)}

        # Guide historique / pratique (TODO: RAG pgvector)
        if "agent_guide" in agents_to_call:
            tasks["agent_guide"] = self._call_agent_guide(message, langue, historique)

        # Feedback math (TODO)
        if "agent_feedback_math" in agents_to_call:
            tasks["agent_feedback_math"] = self._call_agent_feedback(message, user_id)

        # ── Exécution avec timeout ────────────────────────────────────────

        # Météo d'abord (pour enrichir les circuits)
        meteo_data = None
        if "agent_meteo" in tasks:
            try:
                meteo_data = await asyncio.wait_for(
                    tasks.pop("agent_meteo"),
                    timeout=AGENT_TIMEOUT_SECONDS,
                )
                responses["agent_meteo"] = meteo_data
                log.info(f"  Météo : {meteo_data.get('donnees_brutes', {}).get('alerte', {}).get('level', 'N/A')}")
            except asyncio.TimeoutError:
                log.warning("[ORCHESTRATEUR] Timeout agent météo")
                responses["agent_meteo"] = None

        # Circuits avec données météo
        if "agent_circuits" in tasks or ("moteur_math" in agents_to_call and tasks.get("agent_circuits") is None):
            try:
                circuits_data = await asyncio.wait_for(
                    self._call_agent_circuits(message, user_id, signaux, meteo_data),
                    timeout=AGENT_TIMEOUT_SECONDS,
                )
                responses["agent_circuits"] = circuits_data
            except asyncio.TimeoutError:
                log.warning("[ORCHESTRATEUR] Timeout agent circuits")
                responses["agent_circuits"] = None

        # Autres agents en parallèle
        remaining = {k: v for k, v in tasks.items() if k not in ("agent_meteo", "agent_circuits")}
        if remaining:
            results = await asyncio.gather(
                *[asyncio.wait_for(coro, timeout=AGENT_TIMEOUT_SECONDS) for coro in remaining.values()],
                return_exceptions=True,
            )
            for name, result in zip(remaining.keys(), results):
                if isinstance(result, Exception):
                    log.warning(
                        f"[ORCHESTRATEUR] Erreur agent {name} : {result}",
                        exc_info=result,
                    )
                    responses[name] = {
                        "disponible": False,
                        "reponse": None,
                        "erreur": str(result),
                    }
                else:
                    responses[name] = result

        return responses

    async def _call_agent_meteo(self, message: str, user_id: str) -> dict:
        """Appel à l'agent météo."""
        return await self._meteo.get_weather(message, user_id)

    async def _call_agent_circuits(self, message, user_id, signaux, meteo_data):
        """
        Appel à l'agent circuits avec ProfilSynthetique.
        
        CHANGEMENT v2 :
        - Le wrapper construit ProfilSynthetique depuis signaux
        - Plus besoin de client en base
        - Retourne aussi profil_utilise et manquants pour le prompt de synthèse
        """
        result = await self._circuits.get_recommendations(
            user_id=user_id,
            signals=signaux,
            n=3,
            meteo_data=meteo_data,
        )

        # Ajouter conseil météo à chaque circuit
        if meteo_data and meteo_data.get("disponible"):
            donnees_brutes = meteo_data.get("donnees_brutes", {})
            for circuit in result.get("circuits", []):
                lieu_circuit = signaux.get("lieu", "")
                circuit["conseil_meteo"] = self._meteo.get_outdoor_recommendation(
                    donnees_brutes,
                    lieu=lieu_circuit if circuit.get("outdoor") else "",
                )

        return result

    async def _call_agent_reservation(self, message: str, user_id: str) -> dict:
        """
        Appel à l'agent réservation (Yasmine).
        Le session_id est préfixé pour séparer les contextes.
        """
        # Utilise un session_id dédié pour Yasmine (namespace séparé)
        reservation_session_id = f"reservation_{user_id}"
        return await self._reservation.handle_message(message, reservation_session_id)

    async def _call_agent_guide(self, message: str, langue: str, historique: list) -> dict:
        """
        Appel à l'agent guide historique.
        TODO: Intégrer RAG pgvector pour les monuments et l'histoire tunisienne.
        """
        # TODO: Query pgvector avec embeddings du message
        # from rag import query_monuments
        # results = await query_monuments(message, top_k=3)
        # return {"disponible": True, "contexte_rag": results}

        log.info("[GUIDE] TODO: RAG pgvector non encore connecté")
        return {
            "disponible": False,
            "contexte_rag": [],
            "erreur": "rag_non_connecte",
        }

    async def _call_agent_feedback(self, message: str, user_id: str) -> dict:
        """
        Appel à l'agent feedback (moteur math AgentFeedback).
        TODO: Connecter AgentFeedback depuis Agent_principal.py
        """
        # TODO: from Agent_principal import AgentFeedback
        # feedback_agent = AgentFeedback(systeme)
        # feedback_agent.enregistrer_feedback(user_id, circuit_id, note, commentaire)

        log.info("[FEEDBACK] TODO: AgentFeedback non encore connecté")
        return {"disponible": False, "erreur": "feedback_non_connecte"}
    # ─────────────────────────────────────────────────────────────────────────
    # ONBOARDING CIRCUIT (probing 8 questions)
    # ─────────────────────────────────────────────────────────────────────────

    async def _start_onboarding(
        self, user_id: str, message: str, profil: dict, historique: list, langue: str
    ) -> str:
        """Démarre le probing circuit : pose la première question."""
        question, historique_probing = await onboarding.premiere_question(langue)

        update_profile(
            user_id,
            {
                "mode_onboarding": True,
                "onboarding_collecte": {},
                "onboarding_historique": historique_probing,
                "attente_confirmation_circuit": False,
                "langue": langue,
            },
        )

        historique.append({"role": "user", "content": message})
        historique.append({"role": "assistant", "content": question})
        set_history(user_id, historique)

        return question

    async def _handle_onboarding_step(
        self, user_id: str, message: str, profil: dict, historique: list, langue: str
    ) -> str:
        """Traite une réponse de l'utilisateur pendant le probing circuit."""
        profil_collecte = profil.get("onboarding_collecte", {})
        historique_probing = profil.get("onboarding_historique", [])
        langue = langue or profil.get("langue", "FR")

        # Question hors-sujet (météo, pratique…) pendant le probing : répondre sans avancer
        intention_data = await self._detect_intent(message, langue, historique)
        intention_hs = intention_data.get("intention", "SMALLTALK")
        confiance_hs = intention_data.get("confiance", 0.0)
        if intention_hs == "METEO" and confiance_hs >= 0.8:
            meteo_data = await self._call_agent_meteo(message, user_id)
            reponse_meteo = await self._synthesize_response(
                agents_responses={"agent_meteo": meteo_data},
                langue=langue,
                historique=historique,
                message_utilisateur=message,
                intention="METEO",
                profil=profil,
            )
            manquants = onboarding.champs_manquants(profil_collecte)
            if manquants:
                question_courante = onboarding._question_pour_champ(
                    manquants[0], profil_collecte, langue
                )
                if langue == "EN":
                    suite = (
                        "\n\nWhen you're ready, let's continue planning your tour:\n"
                        f"{question_courante}"
                    )
                else:
                    suite = (
                        "\n\nQuand vous voulez, reprenons la personnalisation de votre circuit :\n"
                        f"{question_courante}"
                    )
                reponse_finale = f"{reponse_meteo.rstrip()}{suite}"
            else:
                reponse_finale = reponse_meteo

            historique.append({"role": "user", "content": message})
            historique.append({"role": "assistant", "content": reponse_finale})
            set_history(user_id, historique)
            update_profile(user_id, {"langue": langue})
            return reponse_finale

        result = await onboarding.step(
            historique_probing, profil_collecte, message, langue
        )

        historique.append({"role": "user", "content": message})

        if result["complete"]:
            profil_synth = onboarding.construire_profil_final(result["profil_collecte"])
            try:
                circuits_data = await self._circuits.get_recommendations(
                    user_id=user_id,
                    signals={},
                    n=3,
                    profil_override=profil_synth,
                )
            except Exception as e:
                log.error(
                    f"[ONBOARDING] Erreur récupération circuits : {e}", exc_info=True
                )
                circuits_data = {"circuits": [], "disponible": False}

            presentation = await self._presenter_circuits_onboarding(
                circuits_data, result["profil_collecte"], langue
            )
            reponse_finale = f"{result['reponse']}\n{presentation}"

            update_profile(
                user_id,
                {
                    "mode_onboarding": False,
                    "onboarding_collecte": {},
                    "onboarding_historique": [],
                    "attente_confirmation_circuit": False,
                    "profil_circuit": profil_synth.to_dict(),
                    "profil_collecte_circuit": result["profil_collecte"],
                    "derniers_circuits": circuits_data,
                    "presentation_circuits": presentation,
                    "attente_validation_circuit": True,
                },
            )
        else:
            reponse_finale = result["reponse"]
            update_profile(
                user_id,
                {
                    "onboarding_collecte": result["profil_collecte"],
                    "onboarding_historique": result["historique"],
                    "langue": langue,
                },
            )

        historique.append({"role": "assistant", "content": reponse_finale})
        set_history(user_id, historique)

        return reponse_finale

    async def _confirmer_circuits_en_attente(
        self, user_id: str, message: str, profil: dict, historique: list, langue: str
    ) -> str:
        """Réaffiche les circuits recommandés après validation utilisateur (ex: « ok »)."""
        presentation = profil.get("presentation_circuits")
        if not presentation:
            circuits_data = profil.get("derniers_circuits", {})
            profil_collecte = profil.get("profil_collecte_circuit", {})
            presentation = await self._presenter_circuits_onboarding(
                circuits_data, profil_collecte, langue
            )
        reponse_finale = presentation

        historique.append({"role": "user", "content": message})
        historique.append({"role": "assistant", "content": reponse_finale})
        set_history(user_id, historique)
        update_profile(user_id, {"attente_validation_circuit": False})

        return reponse_finale

    async def _presenter_circuits_onboarding(
        self, circuits_data: dict, profil_collecte: dict, langue: str
    ) -> str:
        """Affiche les circuits comme l'agent circuit : cartes + description LLM."""
        circuits = circuits_data.get("circuits", [])
        if not circuits:
            return FALLBACK_MESSAGES.get(langue, FALLBACK_MESSAGES["FR"])

        tarif = profil_collecte.get("tarif", "etranger")
        transport = profil_collecte.get("transport", "voiture")
        recs = [
            (c.get("donnees_completes", c), float(c.get("score_global", 0.5)))
            for c in circuits[:3]
        ]
        return await presenter_recommandations(
            recs, profil_collecte, tarif=tarif, transport=transport
        )

    # ─────────────────────────────────────────────────────────────────────────
    # RÉPONSE SMALLTALK DIRECTE
    # ─────────────────────────────────────────────────────────────────────────

    async def _respond_smalltalk(
        self,
        message: str,
        langue: str,
        historique: list,
    ) -> str:
        """
        Génère une réponse smalltalk directement (sans passer par les agents).
        L'orchestrateur répond lui-même avec le style Aziz.
        """
        try:
            langue_nom = get_langue_nom(langue)
            messages_llm = [
                {
                    "role": "system",
                    "content": (
                        f"{SYSTEM_PROMPT_ORCHESTRATEUR}\n\n"
                        f"IMPORTANT : réponds UNIQUEMENT en {langue_nom}."
                    ),
                },
                *historique[-6:],
                {"role": "user", "content": message},
            ]

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._groq.chat.completions.create,
                    model=MODEL_SMART,
                    max_tokens=300,
                    temperature=0.7,
                    messages=messages_llm,
                ),
                timeout=AGENT_TIMEOUT_SECONDS,
            )

            return (response.choices[0].message.content or "").strip()

        except Exception as e:
            log.warning(f"[SMALLTALK] Erreur : {e}")
            return FALLBACK_MESSAGES.get(langue, FALLBACK_MESSAGES["FR"])

    # ─────────────────────────────────────────────────────────────────────────
    # SYNTHÈSE NARRATIVE FINALE
    # ─────────────────────────────────────────────────────────────────────────

    async def _synthesize_response(
        self,
        agents_responses: dict,
        langue: str,
        historique: list,
        message_utilisateur: str,
        intention: str,
        profil: dict = {},
    ) -> str:
        """
        Synthétise les réponses des agents en une réponse narrative cohérente.
        Utilise le modèle puissant (llama-3.3-70b) pour la qualité narrative.

        Args:
            agents_responses: Dict des réponses brutes de chaque agent
            langue: Code langue de l'utilisateur
            historique: Historique de la conversation
            message_utilisateur: Message original
            intention: Intention classifiée

        Returns:
            Réponse narrative finale en prose, style guide Aziz
        """
        # ── Préparer le contexte pour le LLM ─────────────────────────────
        contexte_agents = self._format_agents_context(agents_responses, intention)
        langue_nom = get_langue_nom(langue)

        prompt_synthese = f"""Message de l'utilisateur : "{message_utilisateur}"
          Intention détectée : {intention}
          Langue requise : {langue_nom} (code {langue})

         Données des agents :
         {contexte_agents}

         Génère une réponse narrative ENTIÈREMENT en {langue_nom}, style guide Aziz (guide touristique tunisien).
         Maximum 150 mots. Termine par une question de relance."""

        try:
            messages_llm = [
                {
                    "role": "system",
                    "content": (
                        f"{SYSTEM_PROMPT_SYNTHESE}\n\n"
                        f"IMPORTANT : réponds UNIQUEMENT en {langue_nom}."
                    ),
                },
                *historique[-4:],
                {"role": "user", "content": prompt_synthese},
            ]

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._groq.chat.completions.create,
                    model=MODEL_SMART,
                    max_tokens=400,
                    temperature=0.65,
                    messages=messages_llm,
                ),
                timeout=AGENT_TIMEOUT_SECONDS + 5,  # Synthèse a droit à +5s
            )

            tokens = response.usage.total_tokens if response.usage else 0
            log.info(f"[SYNTHESE] Tokens utilisés : {tokens}")

            return (response.choices[0].message.content or "").strip()

        except asyncio.TimeoutError:
            log.warning("[SYNTHESE] Timeout synthèse")
            return FALLBACK_MESSAGES.get(langue, FALLBACK_MESSAGES["FR"])
        except Exception as e:
            log.error(f"[SYNTHESE] Erreur : {e}")
            return FALLBACK_MESSAGES.get(langue, FALLBACK_MESSAGES["FR"])

    def _format_agents_context(self, agents_responses: dict, intention: str) -> str:
        """
        Formate les réponses des agents en texte structuré pour le prompt de synthèse.
        
        AJOUTS v2 :
        - Affiche explication personnalisée de chaque circuit
        - Signale les signaux manquants au LLM de synthèse
        - Affiche les scores détaillés (budget, durée) pour que le LLM puisse les commenter
        """
        lines = []

        # ── Météo ─────────────────────────────────────────────────────────────
        meteo = agents_responses.get("agent_meteo")
        if meteo and meteo.get("disponible"):
            donnees = meteo.get("donnees_brutes", {})
            alerte  = donnees.get("alerte", {})
            temp    = donnees.get("temperature")
            lines.append("[MÉTÉO]")
            if temp:
                lines.append(f"  Température : {temp}°C")
            lines.append(f"  Alerte : {alerte.get('level', 'VERT')}")
            lines.append(f"  Outdoor OK : {alerte.get('outdoor_ok', True)}")
            if meteo.get("final_answer"):
                lines.append(f"  Résumé : {meteo['final_answer'][:200]}")

        # ── Circuits ──────────────────────────────────────────────────────────
        circuits_data = agents_responses.get("agent_circuits")
        if circuits_data:
            circuits = circuits_data.get("circuits", [])
            disponible = circuits_data.get("disponible", False)

            tag = "[CIRCUITS RECOMMANDÉS]" if disponible else "[CIRCUITS PAR DÉFAUT]"
            lines.append(f"\n{tag} ({len(circuits)} circuits)")

            for i, c in enumerate(circuits[:3], 1):
                duree_h = c.get("duree_minutes", 0) // 60
                duree_m = c.get("duree_minutes", 0) % 60
                duree_str = f"{duree_h}h{duree_m:02d}" if duree_h else f"{duree_m}min"

                lines.append(
                    f"  {i}. {c.get('nom', 'Circuit')} "
                    f"— {c.get('prix_dt', 0):.0f} DT/pers "
                    f"— {duree_str}"
                )

                # Scores détaillés (pour que le LLM sache quoi valoriser)
                details = c.get("score_details", {})
                score_budget = details.get("budget", None)
                score_duree  = details.get("duree", None)

                if score_budget is not None:
                    budget_ok = "✓ dans le budget" if score_budget >= 0.7 else "⚠ proche de la limite"
                    lines.append(f"     Budget : {budget_ok} (score {score_budget:.2f})")

                if score_duree is not None:
                    duree_ok = "✓ durée adaptée" if score_duree >= 0.7 else "⚠ un peu long"
                    lines.append(f"     Durée : {duree_ok} (score {score_duree:.2f})")

                # Explication personnalisée
                if c.get("explication"):
                    lines.append(f"     Pourquoi : {c['explication']}")

                # Conseil météo
                if c.get("conseil_meteo"):
                    lines.append(f"     Météo : {c['conseil_meteo']}")

                # Monuments inclus
                monuments = c.get("monuments", [])
                if monuments and isinstance(monuments, list):
                    lines.append(f"     Monuments : {', '.join(str(m) for m in monuments[:5])}")

            # Signaux manquants → le LLM doit poser la question naturellement
            manquants = circuits_data.get("manquants", [])
            if manquants:
                questions_map = {
                    "budget": "Quel est votre budget approximatif ?",
                    "duree":  "Combien de temps avez-vous pour cette visite ?",
                }
                questions = [questions_map[m] for m in manquants if m in questions_map]
                if questions:
                    lines.append(
                        f"\n[À DEMANDER NATURELLEMENT] "
                        f"Pour affiner : {' / '.join(questions)}"
                    )

        # ── Guide historique (RAG) ─────────────────────────────────────────────
        guide = agents_responses.get("agent_guide")
        if guide and guide.get("disponible") and guide.get("contexte_rag"):
            lines.append("\n[INFORMATIONS HISTORIQUES (RAG)]")
            for info in guide["contexte_rag"][:3]:
                lines.append(f"  - {str(info)[:200]}")

        if not lines:
            lines.append(
                "[Aucune donnée agent disponible — "
                "réponds avec tes connaissances générales sur la Tunisie]"
            )

        return "\n".join(lines)
    # ─────────────────────────────────────────────────────────────────────────
    # MISE À JOUR MÉMOIRE
    # ─────────────────────────────────────────────────────────────────────────

    async def _update_memory(
        self,
        user_id: str,
        message: str,
        reponse: str,
        signaux: dict,
        langue: str,
        intention: str,
        historique: list,
        profil: dict,
    ) -> None:
        """
        Met à jour la mémoire session après chaque échange.
        - Ajoute le message et la réponse à l'historique
        - Met à jour le profil avec les nouveaux signaux
        """
        try:
            # Ajouter l'échange à l'historique
            historique.append({"role": "user", "content": message})
            historique.append({"role": "assistant", "content": reponse})
            set_history(user_id, historique)

            # Mettre à jour le profil
            profil_update = {k: v for k, v in signaux.items() if v is not None}
            profil_update["langue"] = langue
            profil_update["derniere_intention"] = intention
            profil_update["nb_echanges"] = profil.get("nb_echanges", 0) + 1
            update_profile(user_id, profil_update)

        except Exception as e:
            log.error(f"[MEMORY] Erreur mise à jour : {e}")


# ─────────────────────────────────────────────────────────────────────────────
# EXEMPLE D'UTILISATION
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    async def demo():
        """Démonstration du pipeline complet."""
        print("=" * 60)
        print("Chatbot Touristique Tunisien — Démo")
        print("=" * 60)

        orchestrateur = OrchestratorAgent()

        # Exemple 1 : Famille avec budget
        print("\n[TEST 1] Famille, budget 150 DT, journée")
        reponse = await orchestrateur.handle_message(
            user_id="demo-user-001",
            message="Bonjour, je suis avec ma famille, on a une journée à Tunis, budget 150 DT pour 4 personnes",
        )
        print(f"Aziz : {reponse}\n")

        # Exemple 2 : Question historique
        print("[TEST 2] Question historique")
        reponse = await orchestrateur.handle_message(
            user_id="demo-user-001",
            message="C'est quoi l'histoire de Carthage ?",
        )
        print(f"Aziz : {reponse}\n")

        # Exemple 3 : Météo
        print("[TEST 3] Question météo")
        reponse = await orchestrateur.handle_message(
            user_id="demo-user-002",
            message="Quel temps fait-il à Tunis aujourd'hui ?",
        )
        print(f"Aziz : {reponse}\n")

        # Exemple 4 : Réservation voiture
        print("[TEST 4] Réservation voiture")
        reponse = await orchestrateur.handle_message(
            user_id="demo-user-003",
            message="Je voudrais louer une voiture à Tunis du 10 au 15 juillet",
        )
        print(f"Yasmine : {reponse}\n")

        # Exemple 5 : Smalltalk
        print("[TEST 5] Smalltalk")
        reponse = await orchestrateur.handle_message(
            user_id="demo-user-001",
            message="Bonjour !",
        )
        print(f"Aziz : {reponse}\n")

    asyncio.run(demo())
