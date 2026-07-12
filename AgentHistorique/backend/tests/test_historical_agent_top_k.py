from __future__ import annotations

from unittest.mock import MagicMock

from app.agents.historical_agent import HistoricalAgent
from app.config import Settings
from app.llm.llm_client import MockLLMClient
from app.rag.retriever import RetrievalFilters


class TrackingRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, RetrievalFilters | None]] = []

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> list[dict]:
        self.calls.append((query, top_k, filters))
        return [
            {
                "source_type": "monument",
                "source_id": 1.0,
                "title": "Thermes d'Antonin",
                "score": 0.91,
                "chunk_text": "Court extrait.",
                "metadata": {},
            }
        ]


def test_historical_agent_uses_top_k_5_for_complex_questions() -> None:
    retriever = TrackingRetriever()
    agent = HistoricalAgent(
        MagicMock(),
        retriever=retriever,
        llm=MockLLMClient(response="Réponse détaillée."),
        settings=Settings(llm_provider="mock", rag_top_k=3, rag_top_k_complex=5),
    )

    agent.answer(
        user_message="Explique en détail l'histoire complète de Carthage punique",
        memory_context={"preferred_language": "fr"},
        language="fr",
    )

    assert retriever.calls[0][1] == 5
