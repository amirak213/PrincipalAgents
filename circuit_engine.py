"""
circuit_engine.py — Moteur de génération de circuit (PertinenceCalculator).

Extrait de app.py pour être importable à la fois par :
  - app.py (endpoint /api/circuits/recommend, résultat mappé vers les
    modèles Pydantic CircuitRecommendResponse)
  - AgentPrincipal/orchestrateur.py (wizard, état CIRCUIT_GENERATION,
    consomme directement le dict brut)

Placé À LA RACINE (E:\\claude, même niveau que app.py) pour éviter tout
import circulaire : app.py importe AgentPrincipal.orchestrateur, et
orchestrateur.py importe ce module — si ce module vivait dans app.py,
orchestrateur.py devrait importer app.py en retour, ce qui casse au
démarrage.

Ce module NE FAIT PAS d'appel LLM ni HTTP — logique mathématique pure
(DEAP / PertinenceCalculator), synchrone et CPU-bound. À appeler depuis
du code async via asyncio.to_thread(...).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Caches module-level (chargés une seule fois, paresseusement)
# ---------------------------------------------------------------------------

MONUMENTS_CACHE: list[dict] = []
CIRCUITS_CACHE: list[dict] = []
PERTINENCE_CALC = None

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
_AGENT_CIRCUIT_DIR = os.path.join(_ROOT_DIR, "AgentCircuit")


def load_circuit_data() -> None:
    """Charge monuments.csv, Profile_circuit.json et instancie
    PertinenceCalculator. Idempotent — ne recharge pas si déjà fait."""
    global MONUMENTS_CACHE, CIRCUITS_CACHE, PERTINENCE_CALC
    if MONUMENTS_CACHE:
        return

    if _AGENT_CIRCUIT_DIR not in sys.path:
        sys.path.append(_AGENT_CIRCUIT_DIR)
    try:
        from PertinenceCalculator import PertinenceCalculator  # legacy, peut être absent
    except ModuleNotFoundError:
        PertinenceCalculator = None

    monuments_path = os.path.join(_AGENT_CIRCUIT_DIR, "monuments.csv")
    monuments_path = os.path.join(_AGENT_CIRCUIT_DIR, "monuments.csv")
    print(
        f"[DEBUG] monuments_path={monuments_path!r}, exists={os.path.exists(monuments_path)}"
    )
    if os.path.exists(monuments_path):
        with open(monuments_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            if os.path.exists(monuments_path):
                
                print(f"[DEBUG] file size={os.path.getsize(monuments_path)} bytes")
                with open(monuments_path, "r", encoding="utf-8") as f:
                    content_preview = f.read(300)
                    print(f"[DEBUG] first 300 chars: {content_preview!r}")
                with open(monuments_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter=";")
                    print(f"[DEBUG] fieldnames={reader.fieldnames}")
                    for row in reader:
                      MONUMENTS_CACHE.append(row)
        print(f"[DEBUG] rows appended={len(MONUMENTS_CACHE)}")
            

    circuits_path = os.path.join(_AGENT_CIRCUIT_DIR, "Profile_circuit.json")
    if os.path.exists(circuits_path):
        with open(circuits_path, "r", encoding="utf-8") as f:
            CIRCUITS_CACHE.extend(json.load(f))

    if PertinenceCalculator is not None:
        PERTINENCE_CALC = PertinenceCalculator(fichier_circuits_json=circuits_path)


# ---------------------------------------------------------------------------
# Profil d'entrée attendu par PertinenceCalculator.recommander()
# ---------------------------------------------------------------------------


class CircuitProfil:
    """Remplace DummyProfil (qui était défini dans app.py, couplé au
    modèle Pydantic CircuitRecommendRequest). Ici, champs simples,
    indépendants de toute couche HTTP."""

    def __init__(
        self,
        budget_max: float,
        type_tarif: str,
        mobilite: str,
        transport: str,
        duree_max: Optional[int] = None,
        preference_epoque: Optional[list[str]] = None,
        types_preferes: Optional[list[str]] = None,
    ):
        self.budget_max = budget_max
        self.type_tarif = type_tarif
        self.duree_max = duree_max or 9999
        self.mobilite = mobilite
        self.transport = transport
        self.preference_epoque = preference_epoque or []
        self.types_preferes = types_preferes or []


# ---------------------------------------------------------------------------
# Génération de circuit — logique pure, retourne un dict brut
# ---------------------------------------------------------------------------


def recommend_circuit(
    profil: CircuitProfil, n: int = 3, must_visit_indices: Optional[list[int]] = None
) -> dict[str, Any]:
    """
    Retourne un dict brut (pas de modèle Pydantic ici — c'est à l'appelant
    de mapper vers ce qu'il a besoin : app.py vers CircuitRecommendResponse,
    orchestrateur.py directement pour peupler wizard.circuit_result).

    Format retourné :
    {
        "feasible": bool,
        "circuits": [
            {
                "circuit_id": str,
                "title": str,
                "summary": str,
                "monuments": [ {order, monument_id, name, latitude,
                                 longitude, visit_duration_min, price, reason} ],
                "total_visit_duration_min": int,
                "total_travel_duration_min": int,
                "total_duration_min": int,
                "total_price": float,
                "score": float,
                "budget_ok": bool,
                "duration_ok": bool,
                "feasible": bool,
            },
            ...
        ],
        "warnings": [str],
    }
    """
    load_circuit_data()
    assert (
        PERTINENCE_CALC is not None
    ), "PERTINENCE_CALC non initialisé — vérifier monuments.csv/Profile_circuit.json"

    pool_size = len(PERTINENCE_CALC.circuits) if must_visit_indices else n
    recos = PERTINENCE_CALC.recommander(profil, n_recommandations=pool_size)
    if not recos:
        return {
            "feasible": False,
            "circuits": [],
            "warnings": [
                "Aucun circuit précalculé ne correspond à votre demande exacte."
            ],
        }

    if must_visit_indices:
        must_visit_names = {
            MONUMENTS_CACHE[i]["nom"]
            for i in must_visit_indices
            if 0 <= i < len(MONUMENTS_CACHE)
        }

        def _coverage(reco: dict) -> int:
            circuit_data = next(
                (c for c in CIRCUITS_CACHE if c["circuit_id"] == reco["circuit_id"]),
                None,
            )
            if not circuit_data:
                return 0
            return len(must_visit_names & set(circuit_data.get("noms", [])))

        recos.sort(key=lambda r: (_coverage(r), r["score_global"]), reverse=True)
        recos = recos[:n]

    resultats = []
    for top_reco in recos:
        circuit_data = next(
            (c for c in CIRCUITS_CACHE if c["circuit_id"] == top_reco["circuit_id"]),
            None,
        )
        if not circuit_data:
            continue

        monuments_enrichis = []
        prix_total = 0.0
        duree_visite_totale = 0
        col_tarif = f"Tarif_{profil.type_tarif.lower()}"

        for idx, (monument_idx, nom) in enumerate(
            zip(circuit_data["indices"], circuit_data["noms"])
        ):
            monument_info = MONUMENTS_CACHE[monument_idx]
            try:
                prix = float(str(monument_info.get(col_tarif, "0")).replace(",", "."))
            except ValueError:
                prix = 0.0
            try:
                duree_visite = int(monument_info.get("duree_visite_min", 0))
            except ValueError:
                duree_visite = 0

            prix_total += prix
            duree_visite_totale += duree_visite

            score_thematique = int(top_reco["details"].get("thematique", 0) * 100)
            score_pop = int(top_reco["details"].get("popularite", 0) * 100)

            monuments_enrichis.append(
                {
                    "order": idx + 1,
                    "monument_id": monument_idx,
                    "name": monument_info.get("nom", nom),
                    "latitude": float(str(monument_info["latitude"]).replace(",", ".")),
                    "longitude": float(
                        str(monument_info["longitude"]).replace(",", ".")
                    ),
                    "visit_duration_min": duree_visite,
                    "price": prix,
                    "reason": (
                        f"Ce monument illustre parfaitement votre thématique "
                        f"({score_thematique}%) et est très apprécié ({score_pop}%)."
                    ),
                }
            )

        budget_ok = prix_total <= profil.budget_max
        duration_ok = (
            top_reco["duree"] <= profil.duree_max if profil.duree_max != 9999 else True
        )
        feasible = budget_ok and duration_ok

        resultats.append(
            {
                "circuit_id": top_reco["circuit_id"],
                "title": f"Circuit recommandé : {top_reco['circuit_id']}",
                "summary": f"Un parcours adapté avec {len(monuments_enrichis)} étapes.",
                "monuments": monuments_enrichis,
                "total_visit_duration_min": duree_visite_totale,
                "total_travel_duration_min": max(
                    0, int(top_reco["duree"] - duree_visite_totale)
                ),
                "total_duration_min": int(top_reco["duree"]),
                "total_price": prix_total,
                "score": top_reco["score_global"],
                "budget_ok": budget_ok,
                "duration_ok": duration_ok,
                "feasible": feasible,
            }
        )

    warnings = []
    if resultats and not any(r["feasible"] for r in resultats):
        warnings.append(
            "Aucun circuit ne respecte strictement toutes vos contraintes — voici les plus proches."
        )

    return {
        "feasible": any(r["feasible"] for r in resultats) if resultats else False,
        "circuits": resultats,
        "warnings": warnings,
    }
