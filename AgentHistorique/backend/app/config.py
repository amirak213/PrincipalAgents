from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent


def _resolve_env_files() -> tuple[str, ...]:
    candidates = (_BACKEND_DIR / ".env", _PROJECT_ROOT / ".env")
    return tuple(str(path) for path in candidates if path.exists())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_files() or (str(_PROJECT_ROOT / ".env"),),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Historical Guide RAG Agent"
    debug: bool = False
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5433/historical_guide"
    )
    database_connect_timeout_seconds: float = 5.0

    embedding_provider: str = "e5"
    embedding_model_name: str = "intfloat/multilingual-e5-small"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32

    # Reranker neuronal (cross-encoder) appliqué après la recherche vectorielle.
    # Remplace/complète le scoring heuristique à poids fixes de scoring.py.
    # Modèle mMiniLMv2 entraîné sur mMARCO (multilingue, inclut le français).
    # Si le chargement échoue (pas de réseau au premier démarrage, modèle non
    # encore téléchargé, etc.), le retriever retombe automatiquement sur le
    # scoring heuristique existant — reranker_enabled=False désactive aussi
    # explicitement le reranker sans toucher au code.
    reranker_enabled: bool = True
    reranker_model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    reranker_device: str = "cpu"

    llm_provider: str = "groq"
    # NOTE (02/07/2026): llama-3.1-8b-instant est déprécié sur Groq (annonce
    # du 17/06/2026, décommission ~août 2026). Remplaçant officiel Groq:
    # openai/gpt-oss-120b ou qwen/qwen3.6-27b. Migration reportée volontairement
    # par décision produit -> ne pas changer sans validation explicite.
    llm_model_name: str = "llama-3.1-8b-instant"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_temperature: float = 0.2
    llm_max_tokens: int = 300
    llm_timeout_seconds: float = 30.0
    llm_structured_output: bool = False

    rag_top_k: int = 3
    rag_top_k_complex: int = 5
    rag_score_gap_from_best: float = 0.08
    rag_min_score: float = 0.65

    web_search_enabled: bool = False
    web_search_provider: str = "duckduckgo"
    web_search_max_results: int = 3
    web_search_region: str = "fr-fr"
    web_search_timeout_seconds: float = 15.0
    tavily_api_key: str = ""
    tavily_search_depth: str = "basic"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
