"""
ModelRouter v2 — Routeur LLM avec fallback intelligent.
- Sépare les usages : planning (léger) vs synthèse (puissant)
- Tracking par provider avec circuit breaker
- Jamais de NameError sur provider non défini
"""

from __future__ import annotations

import os
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from openai import OpenAI


class TaskType(Enum):
    PLAN      = "plan"       # Léger + déterministe
    EVALUATE  = "evaluate"   # Léger
    SYNTHESIZE = "synthesize" # Puissant + créatif
    CHAT      = "chat"        # Générique


@dataclass
class ModelConfig:
    provider:   str
    model_id:   str
    task_types: list[TaskType]
    priority:   int = 0        # plus grand = priorité plus haute
    max_tokens_supported: int = 4096


@dataclass
class ProviderState:
    """État d'un provider — circuit breaker simplifié."""
    name:          str
    error_count:   int   = 0
    last_error_ts: float = 0.0
    cooldown_s:    float = 60.0   # 60s de cooldown après erreur

    def is_available(self) -> bool:
        if self.error_count == 0:
            return True
        elapsed = time.time() - self.last_error_ts
        if elapsed > self.cooldown_s:
            self.error_count = 0   # reset après cooldown
            return True
        return self.error_count < 3  # tolère 2 erreurs avant circuit breaker

    def report_error(self) -> None:
        self.error_count += 1
        self.last_error_ts = time.time()
        if self.error_count >= 3:
            print(f"  [ROUTER] Circuit breaker ouvert pour {self.name} ({self.cooldown_s}s)")

    def report_success(self) -> None:
        if self.error_count > 0:
            self.error_count = max(0, self.error_count - 1)


class ModelRouter:
    """
    Router LLM avec :
    - Sélection par TaskType (plan léger ≠ synthèse puissante)
    - Circuit breaker par provider
    - Fallback automatique sans crash
    """

    # Pool de modèles — configurable via env
    MODEL_POOL: list[ModelConfig] = [
        ModelConfig(
            provider   = "groq",
            model_id   = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant"),
            task_types = [TaskType.PLAN, TaskType.EVALUATE],
            priority   = 10,
        ),
        ModelConfig(
            provider   = "groq",
            model_id   = os.getenv("GROQ_MODEL_MAIN", "llama-3.3-70b-versatile"),
            task_types = [TaskType.SYNTHESIZE, TaskType.CHAT],
            priority   = 10,
        ),
        ModelConfig(
            provider   = "openrouter",
            model_id   = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct"),
            task_types = [TaskType.PLAN, TaskType.EVALUATE, TaskType.SYNTHESIZE, TaskType.CHAT],
            priority   = 5,
        ),
    ]

    def __init__(self):
        self._provider_states: dict[str, ProviderState] = {}
        self._clients:         dict[str, OpenAI]        = {}
        self._lock = threading.Lock()
        self._init_clients()

    def _init_clients(self) -> None:
        groq_key = os.getenv("GROQ_API_KEY", "")
        or_key   = os.getenv("OPENROUTER_API_KEY", "")

        if groq_key:
            self._clients["groq"] = OpenAI(
                api_key  = groq_key,
                base_url = "https://api.groq.com/openai/v1",
            )
            self._provider_states["groq"] = ProviderState(name="groq")

        if or_key:
            self._clients["openrouter"] = OpenAI(
                api_key  = or_key,
                base_url = "https://openrouter.ai/api/v1",
            )
            self._provider_states["openrouter"] = ProviderState(name="openrouter")

    def get(self, task_type: TaskType) -> tuple[OpenAI, str]:
        """
        Retourne (client, model_id) pour le task_type demandé.
        Respecte les circuit breakers et la priorité.
        Lève RuntimeError si aucun provider disponible.
        """
        with self._lock:
            candidates = [
                m for m in self.MODEL_POOL
                if task_type in m.task_types
                and m.provider in self._clients
                and self._provider_states.get(m.provider, ProviderState(m.provider)).is_available()
            ]

            if not candidates:
                # Dernier recours : tous les providers sans filtre task_type
                candidates = [
                    m for m in self.MODEL_POOL
                    if m.provider in self._clients
                    and self._provider_states.get(m.provider, ProviderState(m.provider)).is_available()
                ]

            if not candidates:
                raise RuntimeError("Tous les providers LLM sont indisponibles.")

            # Tri par priorité décroissante
            candidates.sort(key=lambda m: m.priority, reverse=True)
            best = candidates[0]

            return self._clients[best.provider], best.model_id

    def report_error(self, provider: str, error: Exception) -> None:
        """Signale une erreur sur un provider — alimente le circuit breaker."""
        with self._lock:
            if provider in self._provider_states:
                self._provider_states[provider].report_error()

    def report_success(self, provider: str) -> None:
        with self._lock:
            if provider in self._provider_states:
                self._provider_states[provider].report_success()

    def get_provider_for_model(self, model_id: str) -> str:
        """Retourne le provider d'un model_id — évite le NameError de v3."""
        for m in self.MODEL_POOL:
            if m.model_id == model_id:
                return m.provider
        return "unknown"

    def status(self) -> dict:
        """État de santé de tous les providers."""
        with self._lock:
            return {
                provider: {
                    "available":    state.is_available(),
                    "error_count":  state.error_count,
                    "last_error_s": round(time.time() - state.last_error_ts, 1)
                    if state.last_error_ts > 0 else None,
                }
                for provider, state in self._provider_states.items()
            }