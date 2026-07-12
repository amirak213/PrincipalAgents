# 📦 Guide d'installation — Dourbia Agent v8

## Structure du projet à créer

```
dourbia_v8/                   ← dossier racine (crée-le où tu veux)
│
├── main.py                   ← POINT D'ENTRÉE — c'est ce fichier que tu lances
├── requirements.txt
├── .env.example
├── .env                      ← À CRÉER toi-même (copie de .env.example)
├── frontend.html             ← À COPIER depuis ton projet v7
├── email_service.py          ← À COPIER depuis ton projet v7
├── dataset_location_voitures.xlsx  ← À COPIER depuis ton projet v7
│
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── types.py
│   ├── infra.py
│   └── database.py
│
├── agents/
│   ├── __init__.py
│   ├── agent.py
│   ├── planning.py
│   ├── reflection.py
│   └── tools.py
│
├── memory/
│   ├── __init__.py
│   └── memory_manager.py
│
├── guardrails/
│   ├── __init__.py
│   └── guardrails.py
│
├── observability/
│   ├── __init__.py
│   └── tracing.py
│
├── api/
│   ├── __init__.py
│   └── routes.py
│
└── scheduler/
    ├── __init__.py
    └── scheduler.py
```

---

## Étape 1 — Prérequis système

### Python
```bash
python --version   # 3.11 ou 3.12 recommandé
```

### PostgreSQL avec pgvector
pgvector est une extension PostgreSQL pour les embeddings vectoriels.
C'est la seule chose à installer manuellement — elle n'est PAS dans pip.

**Ubuntu/Debian :**
```bash
sudo apt install postgresql-16-pgvector
# ou pour postgres 15 :
sudo apt install postgresql-15-pgvector
```

**macOS avec Homebrew :**
```bash
brew install pgvector
```

**Windows :**
Télécharge le `.zip` depuis https://github.com/pgvector/pgvector/releases
et suis les instructions du README.

**Docker (recommandé pour le dev) :**
```bash
docker run -d \
  --name dourbia-postgres \
  -e POSTGRES_USER=dourbia \
  -e POSTGRES_PASSWORD=dourbia \
  -e POSTGRES_DB=dourbia \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```
Cette image Docker inclut pgvector — c'est la façon la plus simple.

### Redis
```bash
# Ubuntu
sudo apt install redis-server

# macOS
brew install redis

# Docker
docker run -d --name dourbia-redis -p 6379:6379 redis:7-alpine
```

---

## Étape 2 — Environnement Python

```bash
cd dourbia_v8

# Créer un environnement virtuel
python -m venv venv

# Activer (Linux/macOS)
source venv/bin/activate

# Activer (Windows)
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

**Note importante :** `sentence-transformers` télécharge le modèle MiniLM (~90MB)
au premier lancement. C'est automatique, rien à faire.

---

## Étape 3 — Configuration

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer avec tes valeurs
nano .env   # ou vscode .env
```

**Variables OBLIGATOIRES à remplir :**

| Variable | Description | Où l'obtenir |
|---|---|---|
| `GROQ_API_KEY` | Clé API Groq | https://console.groq.com |
| `DATABASE_URL` | URL PostgreSQL | Ton instance locale ou cloud |
| `REDIS_URL` | URL Redis | Ton instance locale |
| `ADMIN_API_KEY` | Clé pour les endpoints /api/* | Génère-en une : `openssl rand -hex 32` |
| `EMAIL_PROPRIETAIRE` | Email qui reçoit les demandes | Ton email |

---

## Étape 4 — Fichiers à copier depuis ton projet v7

Ces fichiers **ne sont PAS générés** — tu dois les copier depuis ta v7 :

```bash
# Depuis ton dossier v7 :
cp /chemin/v7/frontend.html       ./frontend.html
cp /chemin/v7/email_service.py    ./email_service.py
cp /chemin/v7/dataset_*.xlsx      ./dataset_location_voitures.xlsx
```

**email_service.py** doit exposer :
- `envoyer_email_proprietaire_attente(reservation, token)`
- `envoyer_email_relance_proprietaire(reservation, token)`
- `envoyer_email_confirmation_client(reservation, token_annulation)`
- `envoyer_email_rappel_client(reservation)`
- `envoyer_email_feedback_client(reservation)`
- `envoyer_email_refus_client(reservation, raison)`
- `envoyer_email_annulation_client(reservation, source)`
- `email_svc` object avec méthodes : `.rebooking_suggestion()`, `.alerte_meteo_client()`, `.alerte_feedback_negatif()`

---

## Étape 5 — Initialiser la base de données

La base de données se crée **automatiquement** au premier lancement.
Le DDL (tables, index, extension pgvector) est exécuté dans `core/database.py`.

Si tu veux le faire manuellement :
```bash
psql -U dourbia -d dourbia -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## Étape 6 — Lancer l'agent

```bash
# Développement
python main.py

# Production (recommandé)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

L'agent est disponible sur :
- **Chat :** `POST http://localhost:8000/chat`
- **UI :** `GET http://localhost:8000/ui`
- **Health :** `GET http://localhost:8000/health`
- **Métriques :** `GET http://localhost:8000/metrics`

---

## Étape 7 — Tester

```bash
# Test rapide
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour, je cherche une voiture à Tunis", "session_id": "test-001"}'

# Health check
curl http://localhost:8000/health

# Admin — liste des réservations
curl http://localhost:8000/api/reservations \
  -H "X-API-Key: TON_ADMIN_API_KEY"

# Mémoire épisodique d'une session
curl "http://localhost:8000/api/memory?session_id=test-001" \
  -H "X-API-Key: TON_ADMIN_API_KEY"

# Leçons apprises (mémoire procédurale)
curl http://localhost:8000/api/lessons \
  -H "X-API-Key: TON_ADMIN_API_KEY"
```

---

## Résumé des nouveautés v8 vs v7

| Fonctionnalité | v7 | v8 |
|---|---|---|
| Architecture | Boucle for range(6) | Graphe d'états 6 nœuds |
| Mémoire | Profil CRM basique | Vectorielle (pgvector) + Procédurale (Reflexion) |
| Reflection | Réécriture post-hoc | Replay complet avec leçon injectée |
| Guardrails | Blocklist ASCII | Llama Guard + détection injection indirecte |
| Observabilité | Langfuse optionnel | Traces structurées + LLM-as-judge + Prometheus |
| Intention | Aucune | Planning module (détection + décomposition) |
| Scraping | Injection directe | Sanitisation OWASP LLM02 |
| Circuit breaker | Compteur simple | Sliding window 10 appels |

---

## Problèmes fréquents

**`ImportError: No module named 'sentence_transformers'`**
→ `pip install sentence-transformers`

**`asyncpg: column "embedding" is of type vector but expression is of type text`**
→ L'extension pgvector n'est pas installée. Lance :
`docker run pgvector/pgvector:pg16` ou installe l'extension system.

**`RuntimeError: Circuit groq OPEN`**
→ Trop d'erreurs Groq consécutives. Vérifie ta clé API et attends 60s.

**`sentence_transformers` télécharge à chaque restart**
→ Normal au premier lancement seulement. Le modèle est mis en cache dans `~/.cache/huggingface/`.

**`WARNING: ADMIN_API_KEY non définie`**
→ Les endpoints `/api/*` renvoient 503. Définis `ADMIN_API_KEY` dans `.env`.
