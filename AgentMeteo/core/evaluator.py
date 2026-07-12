"""
ResponseEvaluator — Module d'auto-évaluation.
L'agent vérifie lui-même si sa réponse est suffisante avant de répondre.
C'est ce qui différencie un vrai agent d'un simple chatbot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from core.planner import ExecutionPlan
from core.utils import safe_json_parse as _safe_json_parse


@dataclass
class EvalResult:
    """Résultat de l'évaluation d'une réponse."""
    score:         float   # 0.0 → 1.0
    is_sufficient: bool    # True si on peut répondre à l'utilisateur
    reason:        str     # explication
    missing:       list[str]  # infos manquantes identifiées


EVALUATOR_SYSTEM = """Tu es le module d'ÉVALUATION d'un agent météo IA.
Ta SEULE responsabilité : évaluer si les données collectées permettent de répondre correctement.
Tu NE génères JAMAIS de réponse à l'utilisateur.

RETOURNE UNIQUEMENT ce JSON valide :
{
  "score": 0.85,
  "is_sufficient": true,
  "reason": "Les données couvrent la ville et la période demandées.",
  "missing": []
}

Critères d'évaluation :
- score >= 0.7 → is_sufficient = true
- Les données correspondent à la ville demandée
- Les données correspondent à la période demandée (maintenant vs futur)
- Aucune erreur critique dans les tool results
- Si tool_results est vide → score = 0.0
- Si tool_results contient "error" → score <= 0.4"""


class ResponseEvaluator:
    """
    Auto-évaluateur — le LLM s'évalue lui-même.
    Utilise un modèle léger pour réduire les coûts.
    """

    SCORE_THRESHOLD = 0.7

    def __init__(self, llm_client_factory):
        self._get_llm = llm_client_factory

    def evaluate(
        self,
        query:        str,
        tool_results: list[dict],
        plan:         ExecutionPlan,
    ) -> EvalResult:
        """
        Évalue si les tool_results permettent de répondre à query.
        Fallback déterministe si le LLM échoue.
        """
        if not tool_results:
            return EvalResult(
                score=0.0,
                is_sufficient=False,
                reason="Aucune donnée collectée.",
                missing=["données météo"],
            )

        # Vérifie les erreurs critiques sans LLM
        errors = [r for r in tool_results if r.get("result", {}).get("error")]
        if len(errors) == len(tool_results):
            return EvalResult(
                score=0.2,
                is_sufficient=False,
                reason="Tous les tools ont échoué.",
                missing=["données valides"],
            )

        # Évaluation LLM légère
        try:
            summary = json.dumps(
                [{"tool": r.get("tool_name"), "status": "ok" if "error" not in r.get("result", {}) else "error"}
                 for r in tool_results],
                ensure_ascii=False
            )

            client, model = self._get_llm()
            resp = client.chat.completions.create(
                model       = model,
                messages    = [
                    {"role": "system", "content": EVALUATOR_SYSTEM},
                    {"role": "user",   "content":
                        f"Question : {query}\n"
                        f"Intent du plan : {plan.intent}\n"
                        f"Résumé des données : {summary}"
                    },
                ],
                max_tokens  = 150,
                temperature = 0.0,
            )

            raw = resp.choices[0].message.content or "{}"
            d   = _safe_json_parse(raw)

            score = float(d.get("score", 0.5))
            return EvalResult(
                score         = score,
                is_sufficient = score >= self.SCORE_THRESHOLD,
                reason        = d.get("reason", "Évaluation automatique"),
                missing       = d.get("missing", []),
            )

        except Exception:
            # Fallback déterministe : si on a des données sans erreur → suffisant
            has_valid = any("error" not in r.get("result", {}) for r in tool_results)
            return EvalResult(
                score         = 0.8 if has_valid else 0.2,
                is_sufficient = has_valid,
                reason        = "Évaluation par règles (LLM indisponible).",
                missing       = [] if has_valid else ["données valides"],
            )
