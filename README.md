# Aziz — Plateforme IA Tourisme Tunisie (Monorepo)

Ce dépôt regroupe **4 sous-projets** développés au fil du temps dans le cadre du stage / startup
"Tunisia Circuits & Experiences". Ils sont à des stades de maturité différents et ne sont
**pas encore unifiés** (architectures et stacks différentes). Ce README donne une vue
d'ensemble, le statut de chaque module, et comment les lancer.

---

## 📁 Structure du dépôt

```
claude/
├── stage_AI_agentique--master/   (alias: claude/)  → Système legacy "v1" (scoring Python + Streamlit + chat Groq)
├── dourbia_v10_final/            → Agent location de voitures "Yasmine" v10 (architecture agentique 2026)
├── chatbot/                      → "Aziz" — chatbot multi-agents tourisme Tunisie (en développement actif)
└── weather_agent_v4/             → Agent météo autonome (Observe-Plan-Act-Evaluate)
```

---

## 1. `stage_AI_agentique--master/` (aussi dupliqué dans `claude/`) — Système legacy

**Statut : prototype / legacy, contient des bugs bloquants connus.**

Système de recommandation de circuits touristiques basé sur :
- Un moteur de scoring Python (`PertinenceCalculator.py`, `Agent_circuit.py`, `Agent_feedback.py`, `Agent_principal.py`, `Agent_profil.py`)
- Une interface Streamlit (`Application_streamlit.py`) — **chemins Windows en dur, à corriger**
- Un chatbot terminal (`chat.py`) connecté à PostgreSQL + Groq (LLaMA 3.3 70b)
- Des scripts ETL (`Standarisation_Circuits.py`, `Standarisation_Clients.py`, `Circuit_optimizer.py` avec DEAP/algorithme génétique)

**Problèmes connus (voir analyse détaillée)** :
- `calculer_score_thematique` / `calculer_score_type` dans `PertinenceCalculator.py` retournent des scores **constants** (0.7/0.6), non discriminants.
- Incohérence de schéma entre `_charger_depuis_dataframe` (clés `cout_*`) et `_charger_depuis_json` (clé `tarifs`).
- Chemins absolus `C:\Users\anasd\...` dans `Application_streamlit.py`, `Matching_client_circuit.py`, `Standarisation_*.py`, `Circuit_optimizer.py`.

**Lancer le chatbot terminal** :
```bash
cd stage_AI_agentique--master
pip install -r requirements.txt
export GROQ_API_KEY="gsk_..."
python chat.py
```

---

## 2. `dourbia_v10_final/` — Agent location de voitures "Yasmine" v10

**Statut : architecture agentique mature (2026), API FastAPI fonctionnelle.**

Agent conversationnel pour une agence de location de voitures tunisienne, suivant un
graphe d'états **GUARD → PLAN → EXECUTE → REFLECT → MEMORIZE → OBSERVE** :

- `agents/` — boucle principale, planning (décomposition de tâches), reflection (Reflexion/Shinn 2023)
- `core/` — config Pydantic, accès DB (asyncpg + pgvector), infra (pool, Redis, circuit breaker)
- `guardrails/` — Llama Guard 3 + détection injection/Unicode
- `memory/` — mémoire épisodique + procédurale (pgvector)
- `observability/` — tracing structuré, LLM-as-judge, métriques Prometheus
- `scheduler/` — tâches planifiées
- `api/` — routes FastAPI

**Prérequis** : Python 3.11+, PostgreSQL 14+ avec `pgvector`, Redis 7+, compte Groq.

**Lancer** :
```bash
cd dourbia_v10_final
pip install -r requirements.txt
cp .env.example .env   # renseigner GROQ_API_KEY, DB, Redis
docker compose up -d   # ou lancer postgres/redis manuellement
python main.py
```
Voir `dourbia_v10_final/README.md` et `INSTALL.md` pour le détail complet.

---

## 3. `chatbot/` — "Aziz", chatbot multi-agents tourisme Tunisie

**Statut : en développement actif, architecture cible 4 couches.**

Pipeline cible :
1. **Détection langue** (FR/EN/AR/IT/DE)
2. **Extraction de signaux** (regex, sans LLM) — `constants.py`
3. **Classification d'intention** (LLM rapide — `llama-3.1-8b-instant`)
4. **Routing** vers agents spécialisés via `ROUTING_TABLE` (HISTORIQUE, CIRCUIT, RESERVATION, PRATIQUE, SMALLTALK, FEEDBACK, METEO)
5. **Exécution agents** : `agent_circuits_wrapper.py`, `agent_meteo_wrapper.py`, `agent_reservation_wrapper.py` (+ worker async)
6. **Synthèse narrative finale** (LLM puissant — `llama-3.3-70b-versatile`)
7. **Mise à jour mémoire de session** (`session_memory.py`)

Modules clés : `orchestrateur.py` (cerveau central), `constants.py` (config + prompts),
`onboarding.py`, `circuit_presentation.py`, `profil_synthetique.py`, `systeme_loader.py`.

**Lancer** :
```bash
cd chatbot
pip install -r requirements.txt   # voir requirements global à la racine
export GROQ_API_KEY="gsk_..."
python chat.py
```

> ⚠️ Ce module dépend en partie de PostgreSQL/pgvector (via `systeme_loader.py`) — vérifier `.env`.

---

## 4. `weather_agent_v4/` — Agent météo autonome

**Statut : agent autonome 2026 fonctionnel, avec API et tests.**

Vrai agent au sens agentique : cycle **Observe → Plan → Act → Evaluate → Respond**
(`core/agent.py`), avec :
- `core/planner.py` — génération de plans d'exécution
- `core/evaluator.py` — auto-évaluation de la réponse (LLM-as-judge)
- `core/model_router.py` — routage modèle selon complexité
- `tools/` — registre d'outils + exécuteur (appels API météo)
- `memory/context.py` — mémoire contextuelle persistée (`weather_memory.json`)
- `observability/tracer.py` — traces structurées
- `api/app.py` — API FastAPI
- `tests/test_agent.py` — tests unitaires

**Lancer** :
```bash
cd weather_agent_v4
pip install -r requirements.txt   # voir requirements global à la racine
uvicorn api.app:app --reload
# ou exécuter les tests :
pytest tests/
```

---

## ⚙️ Installation rapide (tous modules)

```bash
python -m venv venv
source venv/bin/activate   # ou venv\Scripts\activate sous Windows
pip install -r requirements.txt
```

Chaque sous-dossier a aussi son `.env` propre (clé Groq, identifiants PostgreSQL/Redis,
chemins de fichiers). **Ne jamais committer les `.env` réels** — utiliser `.env.example`.

---

## 🔑 Variables d'environnement communes

| Variable | Description | Utilisé par |
|---|---|---|
| `GROQ_API_KEY` | Clé API Groq (LLaMA 3.x) | tous les modules |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL | `stage_AI_agentique`, `dourbia_v10_final`, `chatbot` |
| `REDIS_URL` | Redis | `dourbia_v10_final` |
| `OPENROUTESERVICE_API_KEY` | Calcul d'itinéraires GPS | `chatbot` (calcul_trajets) |

---

## 🗺️ Roadmap / Travaux en cours

- [ ] Unifier les schémas circuits/tarifs entre `PertinenceCalculator` (legacy) et `chatbot`.
- [ ] Supprimer tous les chemins Windows absolus du module legacy.
- [ ] Finaliser `Agent_profil.py` et son intégration dans `Agent_principal.py`.
- [ ] Migrer le module legacy vers PostgreSQL/pgvector (actuellement JSON local).
- [ ] Intégrer la couche de normalisation linguistique (NLLB-200) dans `chatbot/`.

---

## 📄 Licence / Auteur

Projet interne — Tunisia Circuits & Experiences. Usage privé / stage.
