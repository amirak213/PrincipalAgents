# PrincipalAgents : chatbot Dourbia

Chatbot multi-agents de tourisme pour la région de Carthage et La Marsa (Tunisie). Il génère un circuit de visite, puis un mode guide utilise la position GPS pour donner des informations sur le lieu où l'on se trouve.

## Structure du dépôt

| Dossier | Rôle |
|---|---|
| `app.py` | API FastAPI principale (point d'entrée de production) |
| `AgentPrincipal/` | Orchestrateur, wizard de circuit, mémoire de session, service de géolocalisation |
| `AgentHistorique/` | Moteur de circuits (`backend/app`), données et scripts d'ingestion |
| `AgentLocation/` | Agent de réservation de voitures (optionnel) |
| `AgentMeteo/` | Agent météo (optionnel) |
| `frontend/` | Interface React + Vite |
| `securite/` | Garde-fous (entrées/sorties) |
| `scripts/` | Scripts utilitaires (dont `smoke_render.ps1`) |
| `tests/` | Tests du wizard |

## Prérequis

- Python et `pip`
- Node.js (pour le frontend)
- PostgreSQL et Redis (Redis est obligatoire : le wizard y stocke son état)
- Docker Desktop (pour lancer PostgreSQL et Redis facilement)
- Une clé Groq

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

La première installation est longue (torch). Au premier démarrage, le modèle d'embeddings MiniLM est téléchargé.

Ouvre ensuite `.env` et renseigne les valeurs. Elles te sont transmises séparément : ne les mets jamais sur GitHub.

## Variables d'environnement (noms seulement)

La liste complète est dans `.env.example`. Les principales :

| Variable | Usage |
|---|---|
| `GROQ_API_KEY_PRINCIPAL` | Clé Groq de l'orchestrateur |
| `CIRCUIT_DATABASE_URL` | Base utilisée par le moteur de circuits |
| `HISTORICAL_DATABASE_URL` | Base du RAG historique |
| `DATABASE_URL` | Base de l'agent de réservation |
| `DOURBIA_PG_HOST`, `DOURBIA_PG_PORT`, `DOURBIA_PG_DB`, `DOURBIA_PG_USER`, `DOURBIA_PG_PASSWORD` | Base utilisée pour la position et les infos sur les lieux |
| `REDIS_URL` | Redis (état du wizard) |
| `FRONTEND_ORIGINS` | Origines autorisées par CORS (par défaut : localhost uniquement) |
| `RESERVATION_ENABLED` | `0` pour désactiver la réservation |

## Bases de données

Le moteur de circuits attend un schéma de `monuments` en colonnes anglaises (`id`, `name_fr`, `latitude`...), ainsi que les tables `monument_distances` et `reference_circuits`. Les extraits de données (dump) sont à demander séparément. `À COMPLÉTER` : procédure de restauration du dump.

## Lancer en local

PostgreSQL et Redis, via Docker :

```powershell
docker compose up -d
```

API principale (port 8000) :

```powershell
uvicorn app:app --reload --port 8000
```

Frontend (le proxy Vite redirige `/api` vers le port 8000) :

```powershell
cd frontend
npm install
npm run dev
```

Alternative : `.\start.ps1` lance l'environnement local complet pour Windows. `À COMPLÉTER` : vérifier ce que le script démarre exactement.

## Vérifier que ça marche

```powershell
Invoke-RestMethod http://localhost:8000/health
```

`/health` répond sans dépendance. `/health/ready` vérifie en plus les bases et Redis.

## Tests

```powershell
python -m pytest -q tests
```

## Déploiement

Le `Dockerfile` à la racine est la référence (démarre `uvicorn app:app`). Le déploiement sur Render est en cours de préparation. Pour le mode guide, le frontend doit être servi en HTTPS : les navigateurs bloquent la géolocalisation en HTTP.

## Sécurité

- Ne jamais committer de `.env` : il est ignoré par `.gitignore`.
- Les valeurs des variables se transmettent hors GitHub.