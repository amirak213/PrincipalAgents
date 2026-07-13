"""
test_historical_worker.py — Test complet du worker Agent Historique

Lance depuis la racine du projet :
    cd E:\claude
    python test_historical_worker.py

Ce script :
1. Génère le vrai embedding de la query
2. Envoie la requête JSON au worker via subprocess
3. Affiche la réponse formatée
"""

import json
import subprocess
import sys
import os
import os

print(os.getcwd())
print(os.path.exists(".env"))
# ── Chargement du modèle d'embedding (même que Dourbia) ──────────────────────
print("Chargement du modèle d'embedding...")
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    os.environ.get(
        "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
)
print("✅ Modèle chargé\n")

# ── Queries de test ───────────────────────────────────────────────────────────
TEST_QUERIES = [
    {"query": "Explique les Thermes d'Antonin", "language": "fr"},
    {"query": "What is the Tophet of Carthage?", "language": "en"},
    {"query": "ما هي قرطاج؟", "language": "ar"},
    {"query": "Qui était Hannibal Barca ?", "language": "fr"},
]

# ── Démarrage du worker subprocess ───────────────────────────────────────────
print("Démarrage du worker historique...")
proc = subprocess.Popen(
    [sys.executable, "-m", "AgentPrincipal.agents.historical.worker"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False,  # On lit en bytes, on décode manuellement
    bufsize=1,
    env=os.environ.copy(),
)

# Attendre le signal ready
ready_line = proc.stdout.readline().decode("utf-8", errors="replace").strip()
try:
    ready_data = json.loads(ready_line)
    if ready_data.get("status") == "ready":
        print("✅ Worker prêt\n")
    else:
        print(f"❌ Signal inattendu : {ready_line}")
        proc.kill()
        sys.exit(1)
except Exception:
    print(f"❌ Worker non démarré : {ready_line}")
    # Afficher stderr pour debug
    import threading, time

    time.sleep(1)
    proc.kill()
    err = proc.stderr.read().decode("utf-8", errors="replace")
    print(f"STDERR:\n{err}")
    sys.exit(1)

# ── Envoi des requêtes ────────────────────────────────────────────────────────
print("=" * 60)
for i, test in enumerate(TEST_QUERIES, 1):
    query = test["query"]
    language = test["language"]

    print(f"\n[TEST {i}] {query}")
    print(f"  Langue : {language}")

    # Générer l'embedding
    embedding = model.encode(query).tolist()
    print(f"  Embedding dim : {len(embedding)}")

    payload = {
        "query": query,
        "query_embedding": embedding,
        "language": language,
        "session_context": {},
        "web_search_enabled": False,
    }

    # Envoyer au worker
    line_bytes = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    proc.stdin.write(line_bytes)
    proc.stdin.flush()

    # Lire la réponse
    response_line = proc.stdout.readline().decode("utf-8", errors="replace").strip()
    try:
        result = json.loads(response_line)
    except Exception as e:
        print(f"  ❌ JSON invalide : {e}")
        print(f"  Raw : {response_line[:200]}")
        continue

    # Afficher le résultat
    if result.get("error"):
        print(f"  ❌ Erreur : {result['error']}")
    else:
        print(f"  ✅ Score retrieval : {result['retrieval_score']:.4f}")
        print(f"  Sources : {[s.get('title', '?') for s in result.get('sources', [])]}")
        print(f"  Web fallback : {result.get('used_web_fallback', False)}")
        answer = result.get("answer", "")
        print(f"\n  Réponse :\n  {answer[:400]}")

    print("-" * 60)

# ── Nettoyage ─────────────────────────────────────────────────────────────────
proc.stdin.close()
proc.wait(timeout=5)
print("\n✅ Worker arrêté proprement")
