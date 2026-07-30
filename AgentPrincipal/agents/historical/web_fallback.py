"""
web_fallback.py — Recherche web DuckDuckGo (HTML scraping via httpx) pour l'Agent Historique

Activé uniquement si WEB_SEARCH_ENABLED=true et RAG insuffisant.

Implémentation directe via httpx contre https://html.duckduckgo.com/html/
plutôt que via le package duckduckgo_search (qui utilise le binding Rust
`primp` en interne — observé comme bloquant indéfiniment dans cet
environnement réseau, sans lever d'exception ni respecter les timeouts).
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

import httpx
from lxml import html as lxml_html

logger = logging.getLogger(__name__)

DDG_HTML_URL = "https://html.duckduckgo.com/html/"
REQUEST_TIMEOUT = 8.0

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

# Mots-clés pour filtrer les résultats non pertinents (Carthage Tunisie uniquement)
_RELEVANCE_KEYWORDS = {
    "carthage",
    "tunisie",
    "tunisia",
    "tunisian",
    "punique",
    "punic",
    "romain",
    "roman",
    "byrsa",
    "tophet",
    "hamilcar",
    "hannibal",
    "baal",
    "tanit",
    "magon",
    "thermes",
    "antonin",
    "patrimoine",
}


def search_web(
    query: str, *, language: str = "fr", max_results: int = 3
) -> list[dict[str, Any]]:
    """
    Effectue une recherche DuckDuckGo (scraping HTML direct) et filtre
    les résultats pertinents.

    Returns:
        Liste de dicts {"title": str, "body": str, "url": str}
    """
    cleaned_query = " ".join(query.split()).strip()
    if not cleaned_query:
        return []

    enriched_query = _enrich_query(cleaned_query, language)
    region = "fr-fr" if language == "fr" else ("us-en" if language == "en" else "wt-wt")

    try:
        with httpx.Client(
            timeout=REQUEST_TIMEOUT, headers=_HEADERS, follow_redirects=True
        ) as client:
            response = client.post(
                DDG_HTML_URL,
                data={"q": enriched_query, "kl": region},
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        logger.warning(
            "DuckDuckGo search timed out after %.0fs (query=%r)",
            REQUEST_TIMEOUT,
            cleaned_query,
        )
        return []
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return []

    try:
        raw_results = _parse_ddg_html(response.text)
    except Exception as exc:
        logger.warning("DuckDuckGo HTML parsing failed: %s", exc)
        return []

    filtered = [r for r in raw_results if _is_relevant(r)]
    return filtered[:max_results]


def _parse_ddg_html(html_text: str) -> list[dict[str, str]]:
    """Parse la page de résultats HTML de DuckDuckGo."""
    tree = lxml_html.fromstring(html_text)
    results: list[dict[str, str]] = []

    for node in tree.cssselect("div.result"):
        title_el = node.cssselect("a.result__a")
        snippet_el = node.cssselect("a.result__snippet") or node.cssselect(
            "div.result__snippet"
        )

        title = title_el[0].text_content().strip() if title_el else ""
        url = title_el[0].get("href", "").strip() if title_el else ""
        body = snippet_el[0].text_content().strip() if snippet_el else ""

        if not title and not body:
            continue

        results.append({"title": title, "url": url, "body": body})

    return results


def _enrich_query(query: str, language: str) -> str:
    """Ajoute 'Carthage Tunisie' si pas déjà présent."""
    lower = query.lower()
    if "carthage" not in lower and "tunisie" not in lower and "tunisia" not in lower:
        suffix = "Carthage Tunisie" if language == "fr" else "Carthage Tunisia"
        return f"{query} {suffix}"
    return query


def _is_relevant(result: dict[str, Any]) -> bool:
    """Vérifie si un résultat web est pertinent pour Carthage/patrimoine tunisien."""
    text = " ".join(
        [
            (result.get("title") or "").lower(),
            (result.get("body") or "").lower(),
        ]
    )
    return any(keyword in text for keyword in _RELEVANCE_KEYWORDS)
