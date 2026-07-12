"""
web_fallback.py — Recherche web DuckDuckGo pour l'Agent Historique

Activé uniquement si WEB_SEARCH_ENABLED=true et RAG insuffisant.
Adapté depuis app/tools/web_search_tool.py de l'agent externe.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Mots-clés pour filtrer les résultats non pertinents (Carthage Tunisie uniquement)
_RELEVANCE_KEYWORDS = {
    "carthage", "tunisie", "tunisia", "tunisian", "punique", "punic",
    "romain", "roman", "byrsa", "tophet", "hamilcar", "hannibal",
    "baal", "tanit", "magon", "thermes", "antonin", "patrimoine",
}


def search_web(query: str, *, language: str = "fr", max_results: int = 3) -> list[dict[str, Any]]:
    """
    Effectue une recherche DuckDuckGo et filtre les résultats pertinents.

    Returns:
        Liste de dicts {"title": str, "body": str, "url": str}
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.warning("duckduckgo-search non installé — fallback web désactivé.")
        return []

    # Enrichir la query avec le contexte Carthage si besoin
    enriched_query = _enrich_query(query, language)

    region = "fr-fr" if language == "fr" else ("us-en" if language == "en" else "wt-wt")

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(
                enriched_query,
                region=region,
                max_results=max_results * 3,  # sur-fetch pour filtrer
            ))
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return []

    # Filtrer : garder uniquement les résultats liés à Carthage/Tunisie
    filtered = [
        r for r in raw_results
        if _is_relevant(r)
    ]

    return filtered[:max_results]


def _enrich_query(query: str, language: str) -> str:
    """Ajoute 'Carthage Tunisie' si pas déjà présent."""
    lower = query.lower()
    if "carthage" not in lower and "tunisie" not in lower and "tunisia" not in lower:
        suffix = "Carthage Tunisie" if language == "fr" else "Carthage Tunisia"
        return f"{query} {suffix}"
    return query


def _is_relevant(result: dict[str, Any]) -> bool:
    """Vérifie si un résultat web est pertinent pour Carthage/patrimoine tunisien."""
    text = " ".join([
        (result.get("title") or "").lower(),
        (result.get("body") or "").lower(),
    ])
    return any(keyword in text for keyword in _RELEVANCE_KEYWORDS)
