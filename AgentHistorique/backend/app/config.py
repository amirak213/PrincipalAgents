from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
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
        Field(
             default="postgresql+psycopg://postgres:postgres@localhost:5433/historical_guide",
             validation_alias="CIRCUIT_DATABASE_URL",
        )
     )
    
    database_connect_timeout_seconds: float = 5.0
    

    embedding_provider: str = "e5"
    embedding_model_name: str = "intfloat/multilingual-e5-small"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32

    llm_provider: str = "groq"
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

    web_search_enabled: bool = True
    web_search_provider: str = "duckduckgo"
    web_search_max_results: int = 3
    web_search_region: str = "fr-fr"
    web_search_timeout_seconds: float = 15.0
    tavily_api_key: str = ""
    tavily_search_depth: str = "basic"

    circuit_ga_population_size: int = 40
    circuit_ga_generations: int = 50
    circuit_ga_mutation_rate: float = 0.15
    circuit_ga_crossover_rate: float = 0.8
    circuit_ga_elitism: bool = True
    

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
