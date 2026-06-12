from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # FIX CORS : restreindre les origines autorisées en production
    # Mettre ALLOWED_ORIGINS=https://dourbia.tn,https://app.dourbia.tn dans .env
    allowed_origins: list[str] = ["*"]
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_model_fast: str = "llama-3.1-8b-instant"
    groq_model_guard: str = "llama-guard-3-8b"
    database_url: str = "postgresql://user:pass@localhost/dourbia"
    redis_url: str = "redis://localhost:6379/0"
    flask_port: int = 8000
    uvicorn_workers: int = 4
    excel_path: str = "dataset_location_voitures.xlsx"
    weather_agent_url: str = "http://localhost:5001/weather/chat"
    chatbot_url: str = "http://localhost:3000"
    serveur_base_url: str = "http://localhost:8000"
    email_expediteur: str = ""
    email_mot_de_passe: str = ""
    email_proprietaire: str = ""
    delai_relance_proprietaire_h: int = 24
    admin_api_key: str = ""
    token_expiry_hours: int = 72
    cache_ttl_seconds: int = 7200
    history_ttl_seconds: int = 14400
    vector_cache_ttl: int = 86400
    agent_max_iterations: int = 8
    reflection_enabled: bool = True
    auto_confirm_actif: bool = False
    seuil_auto_confirm: float = 0.90
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    guardrails_enabled: bool = True
    injection_score_threshold: float = 0.7
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    vector_top_k: int = 5

settings = Settings()
