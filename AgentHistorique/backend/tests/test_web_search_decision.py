from __future__ import annotations

from app.config import Settings
from app.rag.web_search_decision import (
    build_web_search_queries,
    build_web_search_query,
    filter_relevant_web_results,
    filter_sources_for_query,
    is_domain_related_query,
    is_substantive_user_message,
    is_vague_web_follow_up,
    local_chunks_relevant_to_query,
    requests_event_or_schedule,
    requests_archaeology_news,
    resolve_query_for_context,
    should_use_web_search,
    uses_demonstrative_reference,
    is_incomplete_lookup_follow_up,
    references_session_monument,
    user_requests_web_search,
)
from app.tools.web_search_tool import WebSearchResult
from app.agents.historical_agent import SourceRef


def _settings(*, enabled: bool = True) -> Settings:
    return Settings(web_search_enabled=enabled, rag_min_score=0.65)


def test_should_use_web_search_when_local_context_insufficient_and_enabled() -> None:
    chunks = [
        {
            "chunk_text": "court",
            "score": 0.10,
        }
    ]
    assert should_use_web_search(
        "Donne-moi plus de détails historiques sur Byrsa",
        chunks,
        0.10,
        {},
        settings=_settings(enabled=True),
    )


def test_should_not_use_web_search_when_disabled() -> None:
    chunks = [{"chunk_text": "court", "score": 0.10}]
    assert not should_use_web_search(
        "Donne-moi plus de détails historiques sur Byrsa",
        chunks,
        0.10,
        {},
        settings=_settings(enabled=False),
    )


def test_should_use_web_search_for_explicit_request_even_when_off_domain() -> None:
    chunks = [{"chunk_text": "court", "score": 0.91}]
    assert should_use_web_search(
        "parler moi de l'oeuvre salammbo de baston gussiere (fais une recherche)",
        chunks,
        0.91,
        {},
        settings=_settings(enabled=False),
    )


def test_user_requests_web_search_detects_fais_une_recherche() -> None:
    assert user_requests_web_search(
        "parler moi de salammbo (fais une recherche)"
    )
    assert user_requests_web_search("recherche internet sur le tophet")


def test_build_web_search_query_for_carthage_news() -> None:
    query = build_web_search_query("les actualités de carthage ce mois")
    assert "carthage" in query.lower()
    assert "actualites" in query.lower()


def test_filter_relevant_web_results_blocks_periscope_even_when_query_contains_parler() -> None:
    results = [
        WebSearchResult(
            title="Maelle: Venez parler",
            url="https://www.pscp.tv/maelle1000/1MnxnvMlMBExO",
            snippet="Rejoignez le live Periscope.",
        )
    ]
    filtered = filter_relevant_web_results(
        results,
        "parler moi de l'oeuvre artistique salammbo de baston gussiere (fais une recherche)",
    )
    assert filtered == []


def test_filter_relevant_web_results_blocks_pastry_results_for_salammbo_art_query() -> None:
    results = [
        WebSearchResult(
            title="Recette Le salambô - L'atelier des Chefs",
            url="https://www.atelierdeschefs.fr/recettes/32632/le-salambo/",
            snippet="Un dessert traditionnel.",
        ),
        WebSearchResult(
            title="Salammbô — Wikipédia",
            url="https://fr.wikipedia.org/wiki/Salammbô",
            snippet="Salammbô est un roman historique de Gustave Flaubert sur Carthage.",
        ),
    ]
    filtered = filter_relevant_web_results(
        results,
        "fais une recherche sur salambo",
    )
    assert len(filtered) == 1
    assert "Wikipédia" in (filtered[0].title or "")


def test_requests_event_or_schedule_detects_jcc_2026_query() -> None:
    query = (
        "chercher le debut des journées cinématographiques de carthage en 2026"
    )
    assert requests_event_or_schedule(query)


def test_should_use_web_search_for_event_schedule_query() -> None:
    assert should_use_web_search(
        "chercher le debut des journées cinématographiques de carthage en 2026",
        retrieved_chunks=[
            {
                "title": "Circuit Carthage_pédestre",
                "score": 0.69,
                "chunk_text": "Circuit touristique à Carthage.",
            }
        ],
        best_score=0.69,
        memory_context={"preferred_language": "fr"},
        settings=_settings(enabled=True),
    )


def test_build_web_search_query_for_jcc_2026() -> None:
    query = build_web_search_query(
        "chercher le debut des journées cinématographiques de carthage en 2026"
    )
    assert "cinematograph" in query.lower() or "journee" in query.lower()


def test_build_web_search_query_for_salammbo_art_request() -> None:
    query = build_web_search_query(
        "parler moi de l'oeuvre artistique salammbo de baston gussiere",
    )
    assert "salammbo" in query.lower() or "flaubert" in query.lower()


def test_filter_relevant_web_results_rejects_encyclopedia_history_for_news_query() -> None:
    results = [
        WebSearchResult(
            title="Carthage | History, Location, & Facts | Britannica",
            url="https://www.britannica.com/place/Carthage-ancient-city-Tunisia",
            snippet="Carthage was founded by Phoenicians from Tyre in the 9th century BCE.",
        ),
        WebSearchResult(
            title="New excavation announced at Carthage archaeological site in 2025",
            url="https://example.com/carthage-news",
            snippet="Archaeologists announced a recent discovery at Carthage in 2025.",
        ),
    ]
    filtered = filter_relevant_web_results(
        results,
        "les actualités de carthage ce mois",
    )
    assert len(filtered) == 1
    assert "2025" in (filtered[0].snippet or "")


def test_should_use_web_search_for_explicit_request_when_disabled() -> None:
    chunks = [{"chunk_text": "court", "score": 0.91}]
    assert should_use_web_search(
        "Chercher sur le web les fouilles à Carthage",
        chunks,
        0.91,
        {},
        settings=_settings(enabled=False),
    )


def test_should_not_use_web_search_for_unrelated_query() -> None:
    chunks = [{"chunk_text": "court", "score": 0.10}]
    assert not should_use_web_search(
        "Donne-moi une recette de pizza",
        chunks,
        0.10,
        {},
        settings=_settings(enabled=True),
    )


def test_should_use_web_search_for_explicit_online_request() -> None:
    chunks = [
        {
            "chunk_text": (
                "Les Thermes d'Antonin sont un grand complexe thermal romain "
                "situé à Carthage, datant du IIe siècle."
            ),
            "score": 0.91,
        }
    ]
    assert should_use_web_search(
        "Cherche en ligne des informations sur les Thermes d'Antonin",
        chunks,
        0.91,
        {},
        settings=_settings(enabled=True),
    )


def test_user_requests_web_search_detects_french_phrases() -> None:
    assert user_requests_web_search("Recherche sur internet l'histoire du Tophet")
    assert user_requests_web_search("Donne-moi une recherche web sur le port punique")
    assert user_requests_web_search("Faire une recherche web sur ça")
    assert user_requests_web_search("Chercher sur le web les fouillons")
    assert user_requests_web_search("chercher sur web La Nécropole punique")
    assert user_requests_web_search("Faite une recherche sur le port punique de carthage")
    assert user_requests_web_search("faites une recherche web sur le tophet de carthage")
    assert user_requests_web_search("donner les actualités sur le musée oceanographique")
    assert not user_requests_web_search("Explique-moi les Thermes d'Antonin")


def test_is_domain_related_query_uses_memory_context() -> None:
    assert is_domain_related_query(
        "Et les horaires ?",
        {"last_mentioned_monuments": ["Thermes d'Antonin"]},
    )


def test_build_web_search_query_strips_online_search_phrases() -> None:
    query = build_web_search_query(
        "Recherche sur internet des informations récentes sur les fouilles archéologiques à Carthage"
    )
    assert "recherche sur internet" not in query
    assert "fouilles" in query.lower()
    assert "carthage" in query.lower()


def test_build_web_search_query_strips_recherche_web_phrases() -> None:
    query = build_web_search_query("Donne-moi une recherche web sur le port punique")
    assert "recherche web" not in query
    assert "port" in query or "punique" in query
    queries = build_web_search_queries(
        "Recherche sur internet des informations récentes sur les fouilles à Carthage"
    )
    assert any("Carthage archaeological excavation Tunisia" in query for query in queries)


def test_build_web_search_query_for_news_request_uses_monument_subject() -> None:
    query = build_web_search_query(
        "donner les actualités sur le musée oceanographique",
        {"last_mentioned_monuments": ["Musee Oceanographique (Dar El Hout)"]},
    )
    assert "oceanographique" in query.lower()
    assert "carthage" in query.lower()
    assert "actualites" in query.lower()


def test_filter_relevant_web_results_blocks_social_media() -> None:
    results = [
        WebSearchResult(
            title="Donner des défis",
            url="https://www.pscp.tv/example/1",
            snippet="Periscope stream",
        ),
        WebSearchResult(
            title="Carthage — Wikipédia",
            url="https://fr.wikipedia.org/wiki/Carthage",
            snippet="Carthage est une ancienne cité punique en Tunisie.",
        ),
    ]
    filtered = filter_relevant_web_results(
        results,
        "donner les actualités sur le musée oceanographique à Carthage",
    )
    assert len(filtered) == 0


def test_filter_relevant_web_results_requires_topic_term_when_specific() -> None:
    results = [
        WebSearchResult(
            title="Carthage - Wikipedia",
            url="https://en.wikipedia.org/wiki/Carthage",
            snippet="Carthage was an ancient city in Tunisia.",
        ),
        WebSearchResult(
            title="Tophet of Carthage",
            url="https://example.com/tophet",
            snippet="The Tophet of Carthage was a sanctuary.",
        ),
    ]
    filtered = filter_relevant_web_results(
        results,
        "faites une recherche web sur le tophet de carthage",
    )
    assert len(filtered) == 1
    assert "Tophet" in filtered[0].title


def test_filter_relevant_web_results_removes_unrelated_french_pages() -> None:
    results = [
        WebSearchResult(
            title="Fouille — Wikipédia",
            url="https://fr.wikipedia.org/wiki/Fouille",
            snippet="En France, on distingue deux catégories de fouilles archéologiques.",
        ),
        WebSearchResult(
            title="Carthage — Wikipédia",
            url="https://fr.wikipedia.org/wiki/Carthage",
            snippet="Carthage est une ancienne cité punique en Tunisie.",
        ),
    ]
    filtered = filter_relevant_web_results(
        results,
        "Recherche sur internet des fouilles archéologiques à Carthage",
    )
    assert len(filtered) == 1
    assert filtered[0].title.startswith("Carthage")


def test_local_chunks_relevant_to_query_detects_missing_excavation_info() -> None:
    chunks = [
        {
            "title": "Temple",
            "chunk_text": "Monument romain avec horaires et tarifs.",
        }
    ]
    assert not local_chunks_relevant_to_query(
        "Recherche sur internet des fouilles récentes à Carthage",
        chunks,
        {},
    )


def test_local_chunks_not_relevant_for_art_query_on_monument_only_chunk() -> None:
    chunks = [
        {
            "title": "Tophet",
            "chunk_text": (
                "Monument funéraire punique dédié à Ba'al et Tanit. "
                "Durée de visite 20 minutes. Horaires été 08H00-18H00."
            ),
        }
    ]
    assert not local_chunks_relevant_to_query(
        "rechercher les oeuvres artistiques liées au tophet du carthage",
        chunks,
        {},
    )


def test_build_web_search_query_uses_last_substantive_message_for_vague_follow_up() -> None:
    memory = {
        "last_substantive_user_message": (
            "rechercher les oeuvres artistiques liées au tophet du carthage"
        ),
        "last_mentioned_monuments": ["Tophet"],
    }
    query = build_web_search_query("faites une recherche web sur ça", memory)
    assert "tophet" in query.lower()
    assert "art" in query.lower()


def test_is_vague_web_follow_up_detects_ca_reference() -> None:
    assert is_vague_web_follow_up("faites une recherche web sur ça")
    assert not is_vague_web_follow_up("faites une recherche web sur le tophet")


def test_is_substantive_user_message_skips_vague_web_follow_up() -> None:
    assert is_substantive_user_message("parlez du tophet de carthage")
    assert not is_substantive_user_message("faites une recherche web sur ça")


def test_should_use_web_search_for_rechercher_art_query() -> None:
    chunks = [
        {
            "title": "Tophet",
            "chunk_text": "Monument funéraire punique à Carthage.",
            "score": 0.89,
        }
    ]
    assert should_use_web_search(
        "rechercher les oeuvres artistiques liées au tophet du carthage",
        chunks,
        0.89,
        {"last_mentioned_monuments": ["Tophet"]},
        settings=_settings(enabled=True),
    )


def test_filter_sources_for_query_keeps_only_matching_monuments_and_web() -> None:
    sources = [
        SourceRef(source_type="monument", source_id=1.0, title="Tophet", score=0.9, url=None),
        SourceRef(
            source_type="monument",
            source_id=2.0,
            title="Maison de la cachette",
            score=0.7,
            url=None,
        ),
        SourceRef(
            source_type="web",
            source_id=None,
            title="Tophet art",
            score=None,
            url="https://example.com/tophet-art",
        ),
    ]
    filtered = filter_sources_for_query(
        sources,
        "rechercher les oeuvres artistiques liées au tophet",
        {"last_substantive_user_message": "rechercher les oeuvres artistiques liées au tophet"},
    )
    titles = {source.title for source in filtered}
    assert "Tophet" in titles
    assert "Tophet art" in titles
    assert "Maison de la cachette" not in titles


def test_filter_relevant_web_results_blocks_tourism_pages_for_art_query() -> None:
    results = [
        WebSearchResult(
            title="Tophet de Carthage — Tripadvisor",
            url="https://www.tripadvisor.fr/Attraction_Review-tophet",
            snippet="Avis des voyageurs sur le Tophet de Carthage.",
        ),
        WebSearchResult(
            title="Stèles du Tophet — Musée",
            url="https://example.com/tophet-art",
            snippet="Stèles et sculptures du tophet punique à Carthage.",
        ),
    ]
    filtered = filter_relevant_web_results(
        results,
        "rechercher les oeuvres artistiques liées au tophet",
        {},
    )
    assert len(filtered) == 1
    assert "Stèles" in filtered[0].title


def test_uses_demonstrative_reference_detects_ce_monument() -> None:
    assert uses_demonstrative_reference(
        "rechercher des oeuvres artistiques liées à ce monument"
    )
    assert not uses_demonstrative_reference("Explique-moi les Thermes d'Antonin")


def test_resolve_query_for_context_maps_ce_monument_to_last_mentioned() -> None:
    memory = {
        "last_mentioned_monuments": ["Thermes d'Antonin"],
        "last_substantive_user_message": "Explique-moi les Thermes d'Antonin",
    }
    resolved = resolve_query_for_context(
        "rechercher des oeuvres artistiques liées à ce monument",
        memory,
    )
    assert "thermes" in resolved.lower()
    assert "antonin" in resolved.lower()
    assert "oeuvres" in resolved.lower()


def test_build_web_search_query_resolves_ce_monument_art_follow_up() -> None:
    memory = {"last_mentioned_monuments": ["Thermes d'Antonin"]}
    query = build_web_search_query(
        "rechercher des oeuvres artistiques liées à ce monument",
        memory,
    )
    assert "thermes" in query.lower()
    assert "antonin" in query.lower()
    assert "art" in query.lower()


def test_local_chunks_not_relevant_for_art_on_wrong_monument_with_ce_reference() -> None:
    chunks = [
        {
            "title": "Monument a absides",
            "chunk_text": "Monument culte romain fermé actuellement.",
        },
        {
            "title": "Temple",
            "chunk_text": "Monument culte de l'époque romaine.",
        },
    ]
    memory = {"last_mentioned_monuments": ["Thermes d'Antonin"]}
    assert not local_chunks_relevant_to_query(
        "rechercher des oeuvres artistiques liées à ce monument",
        chunks,
        memory,
    )


def test_should_use_web_search_for_demonstrative_art_follow_up() -> None:
    chunks = [
        {
            "title": "Monument a absides",
            "chunk_text": "Monument culte romain.",
            "score": 0.75,
        }
    ]
    memory = {"last_mentioned_monuments": ["Thermes d'Antonin"]}
    assert should_use_web_search(
        "rechercher des oeuvres artistiques liées à ce monument",
        chunks,
        0.75,
        memory,
        settings=_settings(enabled=True),
    )


def test_filter_sources_for_query_drops_unrelated_monuments_for_ce_monument() -> None:
    sources = [
        SourceRef(source_type="monument", source_id=1.0, title="Monument a absides", score=0.75, url=None),
        SourceRef(
            source_type="monument",
            source_id=2.0,
            title="Thermes d'Antonin",
            score=0.9,
            url=None,
        ),
        SourceRef(
            source_type="web",
            source_id=None,
            title="Thermes Antonin art",
            score=None,
            url="https://example.com/thermes-art",
        ),
    ]
    memory = {"last_mentioned_monuments": ["Thermes d'Antonin"]}
    filtered = filter_sources_for_query(
        sources,
        "rechercher des oeuvres artistiques liées à ce monument",
        memory,
    )
    titles = {source.title for source in filtered}
    assert "Thermes d'Antonin" in titles
    assert "Thermes Antonin art" in titles
    assert "Monument a absides" not in titles


def test_references_session_monument_detects_au_monument() -> None:
    memory = {"last_mentioned_monuments": ["Thermes d'Antonin"]}
    assert references_session_monument(
        "rechercher les oeuvres artistiques liées au monument",
        memory,
    )
    assert not references_session_monument(
        "rechercher les oeuvres artistiques liées au monument",
        {},
    )


def test_resolve_query_for_context_maps_au_monument_to_last_mentioned() -> None:
    memory = {
        "last_mentioned_monuments": ["Thermes d'Antonin"],
        "last_substantive_user_message": "Explique-moi les Thermes d'Antonin",
    }
    resolved = resolve_query_for_context(
        "rechercher les oeuvres artistiques liées au monument",
        memory,
    )
    assert "thermes" in resolved.lower()
    assert "antonin" in resolved.lower()


def test_build_web_search_query_resolves_au_monument_art_follow_up() -> None:
    memory = {"last_mentioned_monuments": ["Thermes d'Antonin"]}
    query = build_web_search_query(
        "rechercher les oeuvres artistiques liées au monument",
        memory,
    )
    assert "thermes" in query.lower()
    assert "antonin" in query.lower()
    assert "art" in query.lower()


def test_filter_relevant_web_results_blocks_petit_fute_for_monument_art_query() -> None:
    results = [
        WebSearchResult(
            title="Ouvrages d'art à voir de CARTHAGE - Petit Futé",
            url="https://www.petitfute.com/v44418-carthage/c967-ouvrage-d-art",
            snippet="Liste des monuments à visiter à Carthage avec notes et avis.",
        ),
        WebSearchResult(
            title="Mosaïques romaines des Thermes d'Antonin",
            url="https://example.com/thermes-mosaic",
            snippet="Découverte de mosaïques artistiques aux Thermes d'Antonin à Carthage.",
        ),
    ]
    memory = {"last_mentioned_monuments": ["Thermes d'Antonin"]}
    filtered = filter_relevant_web_results(
        results,
        "rechercher les oeuvres artistiques liées au monument",
        memory,
    )
    assert len(filtered) == 1
    assert "Thermes" in filtered[0].title


def test_filter_blocks_wikipedia_without_art_content_for_tophet() -> None:
    results = [
        WebSearchResult(
            title="Tophet de Carthage — Wikipédia",
            url="https://fr.wikipedia.org/wiki/Tophet_de_Carthage",
            snippet=(
                "Site archéologique important dédié à Tanit et Baal à Carthage, Tunisie."
            ),
        )
    ]
    filtered = filter_relevant_web_results(
        results,
        "oeuvres artistiques du tophet de carthage",
        {},
    )
    assert filtered == []


def test_filter_keeps_art_discovery_for_tophet() -> None:
    results = [
        WebSearchResult(
            title="Masque en marbre du Tophet de Carthage",
            url="https://www.geo.fr/culture/masque-tophet",
            snippet=(
                "Un masque en marbre unique découvert dans le Tophet de Carthage, "
                "datant du IVe siècle av. J.-C."
            ),
        )
    ]
    filtered = filter_relevant_web_results(
        results,
        "oeuvres artistiques du tophet de carthage",
        {},
    )
    assert len(filtered) == 1


def test_filter_blocks_viamichelin_for_art_query() -> None:
    memory = {"last_mentioned_monuments": ["Thermes d'Antonin"]}
    results = [
        WebSearchResult(
            title="Parc des thermes d'Antonin - ViaMichelin",
            url="https://www.viamichelin.fr/cartes-plans/sites-touristiques/poi/carthage",
            snippet="Les Thermes d'Antonin sont un site touristique majeur à Carthage.",
        )
    ]
    filtered = filter_relevant_web_results(
        results,
        "rechercher les oeuvres artistiques liées au monument",
        memory,
    )
    assert filtered == []


def test_filter_blocks_routard_for_tophet_art_query() -> None:
    results = [
        WebSearchResult(
            title="Tophet de Carthage — Routard.com",
            url="https://www.routard.com/guide/code_dest/tophet.htm",
            snippet="Site archéologique important et débattu à Carthage.",
        )
    ]
    filtered = filter_relevant_web_results(
        results,
        "oeuvres artistiques du tophet de carthage",
        {},
    )
    assert filtered == []


def test_requests_archaeology_news_detects_carthage_discoveries() -> None:
    assert requests_archaeology_news(
        "Quelles sont les dernières découvertes archéologiques à Carthage en 2026 ?"
    )
    assert requests_archaeology_news("les découvertes archéologiques en carthage")


def test_resolve_incomplete_lookup_follow_up_uses_prior_question() -> None:
    memory = {
        "last_substantive_user_message": (
            "Quelles sont les dernières découvertes archéologiques à Carthage en 2026 ?"
        )
    }
    resolved = resolve_query_for_context("rechercher les dernières découvertes", memory)
    assert "carthage" in resolved.lower()
    assert "2026" in resolved


def test_should_use_web_search_for_archaeology_follow_up() -> None:
    memory = {
        "last_substantive_user_message": (
            "Quelles sont les dernières découvertes archéologiques à Carthage en 2026 ?"
        )
    }
    chunks = [
        {
            "title": "Thermes d'Antonin",
            "chunk_text": "Monument romain avec horaires et tarifs.",
            "score": 0.91,
        }
    ]
    assert should_use_web_search(
        "rechercher les dernières découvertes",
        chunks,
        0.91,
        memory,
        settings=_settings(enabled=True),
    )


def test_filter_blocks_generic_science_for_recherche_web_follow_up() -> None:
    memory = {
        "last_substantive_user_message": (
            "Quelles sont les dernières découvertes archéologiques à Carthage en 2026 ?"
        )
    }
    results = [
        WebSearchResult(
            title="Les grandes découvertes scientifiques — National Geographic",
            url="https://www.nationalgeographic.com/science/article/discoveries",
            snippet="Le boson de Higgs et le séquençage du génome humain.",
        )
    ]
    filtered = filter_relevant_web_results(
        results,
        "recherche web",
        memory,
    )
    assert filtered == []


def test_build_web_search_query_for_archaeology_follow_up() -> None:
    memory = {
        "last_substantive_user_message": (
            "Quelles sont les dernières découvertes archéologiques à Carthage en 2026 ?"
        )
    }
    query = build_web_search_query("recherche web", memory)
    assert "fouill" in query.lower()
    assert "carthage" in query.lower()
    assert "2026" in query


def test_archaeology_lookup_follow_up_builds_carthage_query() -> None:
    query = build_web_search_query("rechercher les dernières découvertes", {})
    assert "carthage" in query.lower()
    assert "fouill" in query.lower() or "decouverte" in query.lower()


def test_filter_blocks_tgm_exhibition_for_thermes_sculpture_query() -> None:
    results = [
        WebSearchResult(
            title="Exposition collective de Sculptures : Mémoire de la Main chez TGM",
            url="https://tunisie.co/article/21466/sortir/expos-et-vernissages/exposition",
            snippet="Exposition à La Marsa.",
        ),
        WebSearchResult(
            title="Une mosaïque de voûte des thermes d'Antonin à Carthage - Persée",
            url="https://www.persee.fr/doc/antaf_0066-4871_1980_num_15_1_1041",
            snippet="Mosaïque polychrome des thermes d'Antonin à Carthage.",
        ),
    ]
    filtered = filter_relevant_web_results(
        results,
        "Quelles sculptures exactes sont exposées aux Thermes d'Antonin ?",
        {"last_mentioned_monuments": ["Thermes d'Antonin"]},
    )
    assert len(filtered) == 1
    assert "persee" in filtered[0].url.lower()


def test_filter_blocks_destination_tunis_for_archaeology_query() -> None:
    results = [
        WebSearchResult(
            title="Visitez les sites archéologiques de Carthage - Destination Tunis",
            url="https://destination-tunis.fr/patrimoine/carthage",
            snippet="Planifiez votre visite des sites touristiques de Carthage.",
        ),
        WebSearchResult(
            title="Nouvelles découvertes archéologiques sur le site de Carthage",
            url="https://kapitalis.com/tunisie/2025/02/26/nouvelles-decouvertes-archeologiques-sur-le-site-de-carthage",
            snippet="Des fouilles récentes et découvertes archéologiques à Carthage en 2025.",
        ),
    ]
    filtered = filter_relevant_web_results(
        results,
        "les découvertes archéologiques en carthage",
        {},
    )
    assert len(filtered) == 1
    assert "kapitalis" in filtered[0].url.lower()
