from __future__ import annotations

from unittest.mock import MagicMock

from app.agents.historical_agent import HistoricalAgent
from app.config import Settings
from app.llm.llm_client import MockLLMClient


def test_post_filter_chunks_removes_cartagena_spain_for_baal_hammon_query() -> None:
    agent = HistoricalAgent(
        MagicMock(),
        retriever=MagicMock(),
        llm=MockLLMClient(response="ok"),
        settings=Settings(llm_provider="mock"),
    )
    chunks = [
        {
            "title": "Parc du Musee Paleochretien Basilique de Cartagena",
            "chunk_text": "Rue baal hammon dans le parc.",
            "score": 0.74,
        },
        {
            "title": "Tophet de Carthage",
            "chunk_text": "Sanctuaire punique dédié à Baal Hammon en Tunisie.",
            "score": 0.70,
        },
    ]

    filtered = agent._post_filter_chunks(
        chunks,
        user_message="who's baal hammon ?",
    )

    titles = [chunk["title"] for chunk in filtered]
    assert "Parc du Musee Paleochretien Basilique de Cartagena" not in titles
    assert "Tophet de Carthage" in titles
