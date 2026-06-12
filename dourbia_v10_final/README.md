# Dourbia Agent Yasmine v8.0

Agent IA de location de voitures — architecture 2026.

---

## Ce que fait la v8 que la v7 ne faisait pas

| Fonctionnalité | v7 | v8 |
|---|---|---|
| Mémoire | Profil CRM basique | Vectorielle pgvector (épisodique + procédurale) |
| Reflexion | Réécriture post-hoc | Vrai replay avec leçon stockée (Shinn 2023) |
| Guardrails | Blocklist ASCII | Llama Guard 3 + détection Unicode + injection indirecte |
| Planning | Aucun | Module intention + décomposition tâches |
| Observabilité | `except: pass` | Spans structurés + LLM-Judge + Prometheus |
| Architecture | Boucle for range(6) | Graphe d'états (GUARD→PLAN→EXECUTE→REFLECT→MEMORIZE→OBSERVE) |

---

## Prérequis

- Python 3.11+
- PostgreSQL 14+ avec extension **pgvector**
- Redis 7+
- Compte Groq (gratuit sur console.groq.com)

---

## Installation étape par étape

### 1. Cloner / créer le dossier projet

```
dourbia_v8/
├── agents/
│   ├── __init__.py
│   ├── agent.py          ← boucle principale
│   ├── planning.py       ← intention + décomposition tâches
│   ├── reflection.py     ← boucle Reflexion
│   └── tools.py          ← fonctions métier
├── api/
│   ├── __init__.py
│   └── routes.py         ← toutes les routes FastAPI
├── core/
│   ├── __init__.py
│   ├── config.py         ← settings Pydantic
│   ├── database.py       ← DDL + seed
│   ├── infra.py          ← pool DB, Redis, circuit breaker
│   └── types.py          ← modèles partagés
├── guardrails/
│   ├── __init__.py
│   └── guardrails.py     ← Llama Guard + injection detection
├── memory/
│   ├── __init__.py
│   └── memory_manager.py ← mémoire épisodique + procédurale
├── observability/
│   ├── __init__.py
│   └── tracing.py        ← spans, LLM-Judge, Prometheus
├── scheduler/
│   ├── __init__.py
│   └── scheduler.py      ← tâches de fond horaires
├── .env                  ← (copier depuis .env.example)
├── .env.example
├── dataset_location_voitures.xlsx
├── email_service.py      ← TON fichier existant (copier ici)
├── frontend.html         ← TON fichier existant (copier ici)
├── main.py               ← point d'entrée
└── requirements.txt
```

### 2. Installer PostgreSQL + pgvector

**Ubuntu/Debian :**
```bash
sudo apt update
sudo apt install postgresql-16 postgresql-16-pgvector
sudo systemctl start postgresql
```

**macOS :**
```bash
brew install postgresql@16
brew install pgvector
```

**Docker (plus simple) :**
```bash
docker run -d \
  --name dourbia-postgres \
  -e POSTGRES_USER=dourbia_user \
  -e POSTGRES_PASSWORD=motdepasse \
  -e POSTGRES_DB=dourbia_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 3. Installer Redis

**Ubuntu/Debian :**
```bash
sudo apt install redis-server
sudo systemctl start redis
```

**Docker :**
```bash
docker run -d --name dourbia-redis -p 6379:6379 redis:7-alpine
```

### 4. Créer l'environnement Python

```bash
cd dourbia_v8
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

> ⚠️ `sentence-transformers` télécharge ~90MB de modèle au premier démarrage.
> C'est normal, il est ensuite mis en cache dans `~/.cache/huggingface/`.

### 5. Configurer le .env

```bash
cp .env.example .env
nano .env   # ou vim, ou VS Code
```

Remplir **au minimum** :
```env
GROQ_API_KEY=gsk_...          # https://console.groq.com → API Keys
DATABASE_URL=postgresql://dourbia_user:motdepasse@localhost:5432/dourbia_db
REDIS_URL=redis://localhost:6379/0
ADMIN_API_KEY=une_cle_secrete_longue
EMAIL_PROPRIETAIRE=ton@email.com
```

### 6. Copier tes fichiers existants

```bash
# Copier depuis ton projet v7 :
cp /chemin/vers/v7/email_service.py ./email_service.py
cp /chemin/vers/v7/frontend.html    ./frontend.html
cp /chemin/vers/v7/dataset_location_voitures.xlsx ./
```

### 7. Lancer

```bash
python main.py
```

Tu devrais voir :
```
09:00:00 [INFO] dourbia.main — [STARTUP] Initialisation Dourbia v8...
09:00:01 [INFO] dourbia.infra — [DB] Pool asyncpg créé (5-20 connexions)
09:00:01 [INFO] dourbia.infra — [REDIS] Connecté
09:00:03 [INFO] dourbia.memory — [MEMORY] Embedding model chargé : ...MiniLM-L12-v2
09:00:03 [INFO] dourbia.main — [STARTUP] ✅ Prêt — 150 véhicules (148 disponibles)
```

### 8. Tester

```bash
# Health check
curl http://localhost:8000/

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour, je cherche une voiture à Tunis", "session_id": "test-1"}'

# Stats admin
curl http://localhost:8000/api/flotte

# Métriques Prometheus
curl http://localhost:8000/metrics

# Traces admin (nécessite ADMIN_API_KEY)
curl http://localhost:8000/api/traces \
  -H "X-API-Key: ta_cle_admin"

# Mémoire d'une session (debug)
curl "http://localhost:8000/api/memory/test-1?query=voiture+tunis" \
  -H "X-API-Key: ta_cle_admin"
```

---

## Architecture en détail

### Graphe d'états (chaque tour agent)

```
Message entrant
      │
      ▼
  [GUARD] ──── bloqué ────► "Je ne peux pas traiter..."
      │ safe
      ▼
  [PLAN]  ← détecte intention + charge mémoire vectorielle
      │       (épisodique + procédurale) EN PARALLÈLE
      ▼
 [EXECUTE] ← boucle ReAct (max 8 tours)
      │       tool calls en parallèle (asyncio.gather)
      ▼
 [REFLECT] ← évalue → si erreur critique : REPLAY avec leçon
      │       stocke la leçon en mémoire procédurale
      ▼
[MEMORIZE] ← résume l'épisode → embedding → pgvector
      │       mise à jour profil CRM
      ▼
 [OBSERVE] ← spans structurés, Langfuse, Prometheus
      │
      ▼
   Réponse
```

### Mémoire vectorielle

L'agent stocke un résumé de chaque conversation sous forme de vecteur (384 dimensions).
Au prochain tour, il récupère automatiquement les 4-5 épisodes les plus similaires
via recherche cosine sur pgvector (index HNSW).

**Avantage vs v7** : au lieu d'injecter tout le profil CRM dans le prompt,
l'agent retrouve uniquement le contexte pertinent pour la question posée.

### Reflexion (Shinn et al., 2023)

Si l'évaluateur détecte une erreur critique (voiture inventée, données incomplètes, etc.) :
1. Il formule une leçon ("dans ce contexte, tu dois d'abord appeler rechercher_voitures")
2. Il stocke la leçon en base (mémoire procédurale)
3. Il **rejoue le tour** avec la leçon injectée dans le prompt
4. Les leçons sont rappelées automatiquement aux tours suivants

---

## Problèmes fréquents

### "pgvector extension not found"
```bash
# PostgreSQL doit avoir pgvector installé
sudo apt install postgresql-16-pgvector
# Puis dans psql :
CREATE EXTENSION IF NOT EXISTS vector;
```

### "sentence-transformers not found"
```bash
pip install sentence-transformers torch
```

### "GROQ_API_KEY manquante"
Créer un compte sur https://console.groq.com et générer une clé API gratuite.

### Le modèle d'embedding est lent au premier démarrage
Normal — il télécharge ~90MB. Ensuite il est mis en cache.

### "email_service module not found"
Copier ton `email_service.py` de la v7 dans le dossier `dourbia_v8/`.
