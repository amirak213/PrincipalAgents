"""
Analyse de confusion post-merge AgentCircuit -> AgentHistorique
==================================================================

Contexte : le dossier AgentCircuit a été supprimé et son code a été
fusionné dans le dossier AgentHistorique (qui contient déjà le code
d'un collègue : backend/ pour les deux agents + data/).

Ce script cherche les symptômes classiques de ce genre de merge :
  1. Références mortes au dossier "AgentCircuit" supprimé (imports,
     chemins codés en dur, sys.path.append, chaînes de config)
  2. Classes/fonctions dupliquées portant le même nom dans plusieurs
     fichiers (ex: deux HistoricalAgentProxy, deux HistoricalAgent)
  3. Fichiers .env multiples avec des valeurs DB_HOST/DB_PORT/DB_NAME
     différentes (source classique du bug "agent connecté à la
     mauvaise base, donc pgvector vide")
  4. Imports ambigus : le même nom de module importé depuis plusieurs
     chemins différents dans le projet
  5. Fichiers .py en double (même nom de fichier, contenus différents)
     à des endroits différents de l'arborescence

Usage :
    python analyse_confusion_dourbia.py "E:\\ChatbotAgent"

Le script est en LECTURE SEULE : aucune modification n'est faite.
"""

import ast
import hashlib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

IGNORED_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", ".mypy_cache"}


def iter_py_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                yield Path(dirpath) / fn


def iter_env_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fn in filenames:
            if fn == ".env" or fn.startswith(".env."):
                yield Path(dirpath) / fn


# ------------------------------------------------------------------
# 1. Références mortes à AgentCircuit
# ------------------------------------------------------------------
def check_dead_agentcircuit_refs(root: Path):
    print("\n=== 1. Références au dossier supprimé 'AgentCircuit' ===")
    pattern = re.compile(r"AgentCircuit(?!s?_)", re.IGNORECASE)
    # on exclut volontairement "AgentCircuits_wrapper" etc. qui sont des noms
    # de fichiers légitimes conservés ; on affine ensuite à l'oeil
    found = False
    for f in iter_py_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                found = True
                print(f"  {f} : L{i} : {line.strip()}")
    if not found:
        print("  Aucune référence textuelle trouvée.")


# ------------------------------------------------------------------
# 2. Classes/fonctions dupliquées
# ------------------------------------------------------------------
def check_duplicate_definitions(root: Path):
    print("\n=== 2. Classes/fonctions définies à plusieurs endroits ===")
    defs = defaultdict(list)  # nom -> [(fichier, lineno, type)]
    for f in iter_py_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(f))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                defs[node.name].append((f, node.lineno, type(node).__name__))

    interesting = {
        name: locs
        for name, locs in defs.items()
        if len(locs) > 1 and not name.startswith("_")
    }
    if not interesting:
        print("  Aucun doublon de nom significatif trouvé.")
        return

    # priorité aux noms qui sentent le sous-système historique/circuit
    priority_kw = ("historical", "circuit", "agent", "proxy", "wrapper")
    for name, locs in sorted(interesting.items()):
        if any(kw in name.lower() for kw in priority_kw):
            print(f"  '{name}' défini {len(locs)} fois :")
            for f, lineno, kind in locs:
                print(f"      {kind} - {f}:{lineno}")


# ------------------------------------------------------------------
# 3. Fichiers .env divergents
# ------------------------------------------------------------------
def parse_env(path: Path):
    values = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return values


def check_env_divergence(root: Path):
    print("\n=== 3. Fichiers .env et cohérence des connexions DB ===")
    env_files = list(iter_env_files(root))
    if not env_files:
        print("  Aucun fichier .env trouvé.")
        return

    keys_of_interest = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DATABASE_URL",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "REDIS_URL",
        "EMBEDDING_MODEL",
        "WEB_SEARCH_ENABLED",
    ]
    table = defaultdict(dict)  # key -> {file: value}
    for ef in env_files:
        vals = parse_env(ef)
        for k in keys_of_interest:
            if k in vals:
                table[k][str(ef)] = vals[k]

    for k, per_file in table.items():
        distinct_values = set(per_file.values())
        marker = "  /!\\ DIVERGENCE" if len(distinct_values) > 1 else ""
        print(f"  {k}{marker}")
        for f, v in per_file.items():
            print(f"      {f} = {v}")


# ------------------------------------------------------------------
# 4. Imports ambigus (même nom de module importé depuis 2+ chemins)
# ------------------------------------------------------------------
def check_ambiguous_imports(root: Path):
    print("\n=== 4. Modules importés depuis plusieurs chemins différents ===")
    # nom_du_module_final -> set(module_complet)
    module_paths = defaultdict(set)
    for f in iter_py_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(f))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                leaf = node.module.split(".")[-1]
                if leaf.lower() in (
                    "historical_agent",
                    "historical_agent_proxy",
                    "agent_circuits_wrapper",
                    "circuit_engine",
                    "orchestrateur",
                ):
                    module_paths[leaf].add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    leaf = alias.name.split(".")[-1]
                    if leaf.lower() in (
                        "historical_agent",
                        "historical_agent_proxy",
                        "agent_circuits_wrapper",
                        "circuit_engine",
                        "orchestrateur",
                    ):
                        module_paths[leaf].add(alias.name)

    found = False
    for leaf, paths in module_paths.items():
        if len(paths) > 1:
            found = True
            print(f"  '{leaf}' importé via {len(paths)} chemins différents :")
            for p in sorted(paths):
                print(f"      {p}")
    if not found:
        print("  Pas d'ambiguïté d'import détectée pour les modules clés.")


# ------------------------------------------------------------------
# 5. Fichiers .py en double (même nom, contenus différents)
# ------------------------------------------------------------------
def check_duplicate_filenames(root: Path):
    print("\n=== 5. Fichiers portant le même nom à des endroits différents ===")
    by_name = defaultdict(list)
    for f in iter_py_files(root):
        by_name[f.name].append(f)

    found = False
    for name, paths in by_name.items():
        if len(paths) > 1 and name not in ("__init__.py", "config.py", "constants.py"):
            hashes = {}
            for p in paths:
                try:
                    h = hashlib.md5(p.read_bytes()).hexdigest()[:8]
                except Exception:
                    h = "??????"
                hashes[str(p)] = h
            distinct = len(set(hashes.values()))
            found = True
            tag = (
                "(contenus IDENTIQUES)"
                if distinct == 1
                else "(contenus DIFFÉRENTS /!\\)"
            )
            print(f"  {name} {tag}")
            for p, h in hashes.items():
                print(f"      {p}  [{h}]")
    if not found:
        print("  Aucun fichier dupliqué par nom (hors __init__.py/config.py).")


def main():
    if len(sys.argv) < 2:
        print("Usage : python analyse_confusion_dourbia.py <chemin_racine_projet>")
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    if not root.exists():
        print(f"Chemin introuvable : {root}")
        sys.exit(1)

    print(f"Analyse de : {root}")
    check_dead_agentcircuit_refs(root)
    check_duplicate_definitions(root)
    check_env_divergence(root)
    check_ambiguous_imports(root)
    check_duplicate_filenames(root)
    print("\nTerminé. Ce rapport signale des symptômes possibles, pas des certitudes —")
    print("à croiser avec le contexte (ex: deux .env avec des ports différents n'est")
    print("un problème que si le mauvais est chargé au runtime).")


if __name__ == "__main__":
    main()
