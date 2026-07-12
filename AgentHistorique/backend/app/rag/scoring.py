from __future__ import annotations

from dataclasses import dataclass

from app.rag.query_intent import QueryIntent, source_type_score
from app.rag.text_utils import token_overlap_score

# Poids utilisés quand aucun reranker neuronal n'est disponible (désactivé ou
# échec de chargement) — comportement identique à avant l'introduction du
# cross-encoder, pour une dégradation gracieuse.
VECTOR_WEIGHT = 0.75
KEYWORD_WEIGHT = 0.15
SOURCE_TYPE_WEIGHT = 0.10

# Poids utilisés quand un score de cross-encoder est disponible : il devient
# la composante dominante car il capture la pertinence sémantique bien mieux
# que le score vectoriel seul ou l'overlap de tokens, qui restent en
# tie-breakers.
NEURAL_WEIGHT = 0.65
VECTOR_WEIGHT_WITH_NEURAL = 0.20
KEYWORD_WEIGHT_WITH_NEURAL = 0.10
SOURCE_TYPE_WEIGHT_WITH_NEURAL = 0.05


@dataclass
class HybridScore:
    vector_score: float
    keyword_score: float
    source_type_component: float
    final_score: float
    neural_score: float | None = None


def compute_hybrid_score(
    query: str,
    title: str | None,
    chunk_text: str | None,
    source_type: str,
    vector_score: float,
    intent: QueryIntent,
    neural_score: float | None = None,
) -> HybridScore:
    keyword_score = token_overlap_score(query, title, chunk_text)
    source_type_component = source_type_score(source_type, intent)

    if neural_score is not None:
        final_score = (
            NEURAL_WEIGHT * neural_score
            + VECTOR_WEIGHT_WITH_NEURAL * vector_score
            + KEYWORD_WEIGHT_WITH_NEURAL * keyword_score
            + SOURCE_TYPE_WEIGHT_WITH_NEURAL * source_type_component
        )
    else:
        final_score = (
            VECTOR_WEIGHT * vector_score
            + KEYWORD_WEIGHT * keyword_score
            + SOURCE_TYPE_WEIGHT * source_type_component
        )

    return HybridScore(
        vector_score=vector_score,
        keyword_score=keyword_score,
        source_type_component=source_type_component,
        final_score=final_score,
        neural_score=neural_score,
    )
