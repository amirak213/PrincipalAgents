# État du Projet Dourbia

## Architecture (résumé en 10 lignes max)
Dourbia est un projet modulaire composé d'un backend interagissant avec PostgreSQL, et orchestré par plusieurs agents (AgentPrincipal, AgentHistorique, AgentLocation). L'orchestration est gérée par un script Python (`orchestrateur.py`) lancé via `start.ps1`. Le système intègre des fonctionnalités de génération de circuits (`circuit_agent.py`, moteur génétique + `DijkstraRouter`) sur une base de monuments/distances en PostgreSQL. **Le wizard conversationnel (Redis) est validé de bout en bout, y compris l'activation du mode Guide GPS** (`test-wizard-011`, 3 août 2026), avec un circuit `feasible=True` cohérent. AgentLocation (ex-`dourbia_v10_final`, agent de réservation de voitures) démarre proprement et est appelé par l'orchestrateur via le worker "Yasmine" (`agent_reservation_worker.py`).

**Attention infra (point de vigilance permanent)** : la base PostgreSQL contenant le schéma monuments migré (42 colonnes anglaises) vit dans le conteneur Docker `dourbia_db` (port 5433, base `dourbia`) — **pas** dans l'instance PostgreSQL native (port 5432). Ce conteneur ne redémarre pas automatiquement. Toujours lancer `docker start dourbia_db` (et `dourbia_redis` si utilisé) **avant** `start.ps1`/`uvicorn`, sous peine de timeouts ou d'erreurs `UndefinedTable`/`UndefinedColumn`.

## Décisions récentes (avec dates)

- **3 Août 2026 — Session complète, 5 chantiers traités :**

  1. **`.gitignore` corrigé et nettoyage git** — le fichier `.gitignore` avait été corrompu lors d'une édition précédente (préfixes `+` de diff collés littéralement, encodage UTF-16 avec BOM via `Add-Content` au lieu d'UTF-8). Réécrit proprement (`Set-Content -Encoding utf8`). `frontend/node_modules/` (des centaines de fichiers) et `AgentMeteo/weather_agent.log` retirés de l'index git (`git rm --cached`), sans suppression physique sur disque. `.env` et `dump.rdb` confirmés correctement ignorés (`git check-ignore`). Commit isolé poussé, séparé des fixes fonctionnels en attente.

  2. **`meta.priority` renvoyé en string corrigé** — `app.py` ligne ~332 (construction de `WizardOption` dans `_get_sorted_monument_options()`) transmettait `m.priority` (type `Decimal` issu de la colonne `Numeric`) directement, sérialisé en JSON comme string (`"5.00"`) au lieu d'un nombre. Fix : `float(m.priority) if m.priority is not None else None`, aligné sur le pattern déjà utilisé ailleurs dans le même fichier (ligne ~703). Validé via `/api/monuments`.

  3. **Bug critique résolu : `CIRCUIT_DATABASE_URL` pointait vers le mauvais environnement** — le test end-to-end du wizard jusqu'à `GUIDE_MODE_READY` (jamais testé jusqu'ici, seulement jusqu'à `confirm_circuit`) a révélé une chaîne d'erreurs en cascade :
     - Timeout de connexion sur le port 5433 : le conteneur Docker `dourbia_db` était arrêté (`Exited (255)`, crash silencieux entre deux sessions).
     - Après redémarrage du conteneur, tentative de correction en redirigeant `CIRCUIT_DATABASE_URL` vers le port 5432 natif (base `dourbia`) → erreur `relation "monuments" does not exist` (cette base n'a pas de table monuments).
     - Tentative avec la base `sig_dourbia` (aussi native, port 5432) → erreur `column "id" does not exist` : cette base contient l'**ancien schéma français pré-migration** (`id_monument`, `nom_monument_fr`, `priorit`...), un vestige jamais mis à jour.
     - Root cause réelle : la **seule** base avec le schéma migré à 42 colonnes anglaises (`id`, `name_fr`, `priority`...) est `dourbia` **à l'intérieur du conteneur Docker** `dourbia_db` (port 5433 externe). `CIRCUIT_DATABASE_URL` remis à sa valeur d'origine (`postgresql+psycopg://dourbia:dourbia@localhost:5433/dourbia`) une fois le conteneur redémarré proprement.
     - **Validé de bout en bout** (`test-wizard-011`) : séquence complète `CITY_SELECTION → PLACE_SELECTION → BUDGET → MOBILITY → PREFERENCES → DATES → CIRCUIT_GENERATION → CIRCUIT_REVIEW (budget_ok=true) → GUIDE_MODE_READY → confirmation "Mode Guide GPS activé !"`. Premier test réel de la portion GPS guide mode du wizard.
     - **Bug mineur découvert en testant** : le handler `GUIDE_MODE_READY` attend `confirm_guide_mode` avec `value: "yes"` (string), pas un booléen JSON (`true`) — à vérifier côté frontend React que le payload envoyé est bien la string.

  4. **Redis client `AgentPrincipal`** — vérification a montré que `AgentPrincipal/redis_client.py` **existe déjà** et est complet (singleton `get_redis()`/`close_redis()`, aligné sur le pattern `AgentLocation/core/infra.py`, `redis.asyncio`, lit `REDIS_URL` depuis `constants.py`). Aucune création nécessaire. Un gap a été repéré et corrigé : le `lifespan` de `app.py` ne fermait jamais la connexion Redis au shutdown (rien après le `yield`). Fix : ajout de `await close_redis()` après le `yield` dans le `lifespan`, avec logs `[SHUTDOWN]`. Validé (arrêt propre sans traceback).

  5. **`output_guard.py` — décision assumée de garder le mode logging seul** (pas de blocage actif). Les scores de similarité cosinus observés en usage réel sur des messages de wizard parfaitement légitimes (`start_wizard`, questions structurées) étaient bas (0.03–0.35, loggés comme "hors-sujet potentiel"), ce qui suggère que le seuil actuel produirait des faux positifs s'il servait à bloquer. Risque de contenu inapproprié (langage) jugé faible pour ce cas d'usage (chatbot tourisme) ; le guard reste utile en observation, mais nécessiterait une calibration du seuil sur un corpus de test dédié avant d'envisager un blocage actif. Pas de changement de code — décision produit documentée ici.

- **1er Août 2026 — Session complète, 6 chantiers clos :**

  1. Retest end-to-end post-nettoyage validé (`test-wizard-005`), aucune régression suite au nettoyage du code mort dans `app.py`/`circuit_engine.py`.

  2. `/api/monuments` migrée du cache CSV (`MONUMENTS_CACHE`/`load_circuit_data()`) vers une requête SQLAlchemy directe sur `Monument`, réutilisant le pattern de `_get_sorted_monument_options()`. `load_circuit_data()`/`MONUMENTS_CACHE` supprimés de `circuit_engine.py` (aucun autre appelant — `geo_service.py` a des caches homonymes mais indépendants).

  3. Écart `feasible=False` (log serveur) vs `budget_ok=true` (réponse API) résolu — deux root causes :
     - `monument_distances`/`reference_circuits` vides → `DijkstraRouter` tombait systématiquement en fallback Haversine. Fix : nouveau script `AgentHistorique/backend/scripts/import_monument_distances.py` (Haversine + vitesses moyennes marche/vélo/voiture), upsert sur `(from_monument_id, to_monument_id)`. 60 monuments → 3540 arêtes.
     - `load_graph()` dans `data_loader.py` indexait le graphe avec `str(monument.id)` (`"12.00"`, Decimal brut) au lieu de `monument.id_str` (`"12"`) — mismatch avec le reste du pipeline (candidates, chromosome GA), rendait le graphe inutilisable même une fois les distances importées. Fix : `monument_ids = [monument.id_str for monument in monuments ...]`.
     - Validé (`test-wizard-007`) : `feasible=True score=0.84` (contre `False`/`0.74` avant), cohérent avec `budget_ok: true`.
     - `inspect_distance_matches.py` corrigé au passage (anciennes colonnes `id_monument`/`nom_monument_fr` → `id`/`name_fr`).

  4. AgentLocation ("problème port 5432 vs 5433") — cause réelle différente de l'hypothèse initiale : `AgentLocation/core/config.py` chargeait `.env` via un chemin **relatif** (`env_file=".env"`), jamais résolu selon le CWD de lancement, donc `Settings()` retombait sur des credentials par défaut invalides (`user:pass@localhost`). Fix : ajout de `_resolve_env_files()` (même mécanisme que dans `AgentHistorique/backend/app/config.py`), résout `E:\claude\.env` en priorité. `asyncpg.create_pool()` dans `core/infra.py` consomme `settings.database_url` correctement, aucun changement nécessaire là. Démarrage validé : `Application startup complete` sans exception, `DB_CONFIG` loggé confirme les bonnes credentials (`dourbia:dourbia@127.0.0.1:5432/dourbia`).

  5. `Réservation disponible : False` (découvert en creusant le point 4) — le dossier `dourbia_v10_final`, référencé en dur par le worker de réservation "Yasmine", avait été renommé en `AgentLocation` sans mise à jour des chemins. Deux fichiers corrigés :
     - `AgentPrincipal/agent_reservation_wrapper.py` : `DOURBIA_PATH` → pointe vers `AgentLocation` (corrige la détection `_available`).
     - `AgentPrincipal/agent_reservation_worker.py` : `DOURBIA` → pointe vers `AgentLocation` (corrige le crash `os.chdir()` au démarrage du subprocess worker).
     - Validé : worker démarre sans traceback, `Réservation disponible : True`.

*(historique antérieur : migration monuments CSV→PostgreSQL, réparation modèle SQLAlchemy Monument, câblage must_visit dans le wizard — voir mémoire du projet)*

## En cours

(rien en cours — les chantiers des 1er et 3 août sont clos)

## Bloqué / à résoudre

- **Colonnes descriptives vides en DB** : `name_en`, `name_ar`, `visit_duration_minutes`, `dominant_period`, `function`, `panoramic_image_url` existent dans le schéma `Monument` mais sont `null` pour les 60 monuments — jamais peuplées lors de la migration CSV→PostgreSQL du 30 juillet. Import à prévoir séparément si ces champs doivent être exploités côté front.
- **Bases PostgreSQL obsolètes à nettoyer/documenter** : `sig_dourbia` (native, port 5432) contient encore l'ancien schéma français pré-migration (`id_monument`, `nom_monument_fr`...) — vestige jamais mis à jour, source de confusion potentielle (a fait perdre du temps le 3 août). À vider/supprimer ou documenter clairement comme obsolète pour éviter toute reconnexion accidentelle dessus.
- **Conteneur Docker `dourbia_db`** : contient la base de référence pour les monuments (schéma migré, 42 colonnes) — ne redémarre pas automatiquement, doit être démarré manuellement à chaque session (`docker start dourbia_db`). Envisager `restart: unless-stopped` dans le `docker-compose.yml` pour éviter les oublis.
- **Distances calculées en Haversine, pas en distances de marche réelles** : `import_monument_distances.py` utilise une estimation à vol d'oiseau + vitesse moyenne, pas un vrai calcul d'itinéraire (rues, obstacles). Suffisant pour lever le fallback et rendre `feasible` cohérent, mais les durées de trajet restent approximatives. Un remplacement par un service de routage réel (ex. OpenRouteService) resterait une amélioration possible, ciblée sur le calcul dans ce script.
- **`output_guard.py` en mode logging seul** (décision assumée, voir 3 août) — nécessiterait une calibration du seuil de similarité cosinus sur un corpus de test avant d'envisager un blocage actif.
- **À vérifier côté frontend React** : le payload attendu pour `confirm_guide_mode` est `value: "yes"`/`"no"` (string), pas un booléen — à confirmer que le client envoie bien le bon format.

## Prochaines étapes

1. Décider si les colonnes descriptives vides doivent être peuplées à court terme, et depuis quelle source.
2. Nettoyer ou documenter clairement `sig_dourbia` comme base obsolète (éviter la confusion avec `dourbia` du conteneur).
3. Envisager `restart: unless-stopped` sur `dourbia_db`/`dourbia_redis` dans `docker-compose.yml` pour éviter les oublis de démarrage manuel.
4. (Optionnel) Remplacer les distances Haversine par un vrai service de routage si la précision des trajets devient un besoin.
5. (Optionnel) Calibrer le seuil de `output_guard.py` sur un corpus de test si un blocage actif devient souhaitable.