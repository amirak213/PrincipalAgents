from __future__ import annotations

import logging
from typing import Literal, Protocol, TypedDict, runtime_checkable

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

ChatRole = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    role: ChatRole
    content: str


@runtime_checkable
class LLMClient(Protocol):
    """Abstraction for text completion backends used by HistoricalAgent."""

    @property
    def model_name(self) -> str:
        ...

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        ...


class LLMClientError(Exception):
    """Raised when the LLM provider fails or is misconfigured."""


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"
OLLAMA_BASE_URL = "http://localhost:11434"


class MockLLMClient:
    """Deterministic LLM for tests and offline development."""

    def __init__(self, response: str = "Réponse de test.", model_name: str = "mock") -> None:
        self._response = response
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        return self._response


class OpenAICompatibleLLMClient:
    """HTTP client for OpenAI-compatible chat completion APIs (OpenAI, Groq, etc.)."""

    def __init__(
        self,
        model_name: str,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key.strip():
            raise LLMClientError("LLM API key is required for this provider.")
        self._model_name = model_name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = _build_timeout(timeout_seconds)

    @property
    def model_name(self) -> str:
        return self._model_name

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise _http_status_error(exc) from exc
        except httpx.HTTPError as exc:
            raise LLMClientError(f"LLM request failed: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError) as exc:
            raise LLMClientError("Unexpected LLM response format.") from exc


class OllamaLLMClient:
    """HTTP client for local Ollama chat API."""

    def __init__(
        self,
        model_name: str,
        *,
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._timeout = _build_timeout(timeout_seconds)

    @property
    def model_name(self) -> str:
        return self._model_name

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise _http_status_error(exc, provider_label="Ollama") from exc
        except httpx.HTTPError as exc:
            raise LLMClientError(f"Ollama request failed: {exc}") from exc

        message = data.get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMClientError("Unexpected Ollama response format.")
        return content.strip()


def validate_llm_settings(settings: Settings | None = None) -> list[str]:
    """Return human-readable configuration warnings."""
    settings = settings or get_settings()
    provider = settings.llm_provider.strip().lower()
    warnings: list[str] = []

    if provider in {"openai", "groq"} and not settings.llm_api_key.strip():
        warnings.append(
            f"LLM_API_KEY is missing for provider '{provider}'. "
            "Set it in your .env file before calling POST /api/chat."
        )
    return warnings


def create_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.strip().lower()

    if provider == "mock":
        logger.info("Using mock LLM provider (model=%s)", settings.llm_model_name)
        return MockLLMClient(model_name=settings.llm_model_name)

    if provider in {"openai", "groq"}:
        base_url = settings.llm_base_url.strip()
        if not base_url:
            base_url = GROQ_BASE_URL if provider == "groq" else OPENAI_BASE_URL
        logger.info(
            "Using %s LLM provider (model=%s, base_url=%s)",
            provider,
            settings.llm_model_name,
            base_url,
        )
        return OpenAICompatibleLLMClient(
            settings.llm_model_name,
            api_key=settings.llm_api_key,
            base_url=base_url,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    if provider == "ollama":
        base_url = settings.llm_base_url.strip() or OLLAMA_BASE_URL
        logger.info(
            "Using Ollama LLM provider (model=%s, base_url=%s)",
            settings.llm_model_name,
            base_url,
        )
        return OllamaLLMClient(
            settings.llm_model_name,
            base_url=base_url,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    raise LLMClientError(
        f"Unsupported LLM provider: {settings.llm_provider!r}. "
        "Expected 'openai', 'groq', 'ollama', or 'mock'."
    )


def _build_timeout(timeout_seconds: float) -> httpx.Timeout:
    total = max(timeout_seconds, 5.0)
    connect = min(5.0, total)
    read = max(total - connect, 1.0)
    return httpx.Timeout(connect=connect, read=read, write=5.0, pool=5.0)


def _http_status_error(
    exc: httpx.HTTPStatusError,
    *,
    provider_label: str = "LLM",
) -> LLMClientError:
    status = exc.response.status_code
    if status == 401:
        return LLMClientError(
            f"{provider_label} authentication failed. Check LLM_API_KEY in your .env file."
        )
    if status == 429:
        return LLMClientError(f"{provider_label} rate limit reached. Try again shortly.")
    return LLMClientError(f"{provider_label} request failed with status {status}.")
