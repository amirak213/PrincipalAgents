"""
agent_reservation_wrapper.py — Pont entre l'orchestrateur et l'agent Yasmine (Dourbia).
Lance dourbia dans un subprocess isolé pour éviter les conflits sys.modules avec weather_agent.
"""

import asyncio
import json
import logging
import sys
import os
import os as _os


from typing import Optional

log = logging.getLogger("chatbot.agent_reservation")

WORKER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "agent_reservation_worker.py")
)
DOURBIA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "dourbia_v10_final")
)


class AgentReservationWrapper:
    def __init__(self):
        self._available = os.path.exists(WORKER_PATH) and os.path.exists(DOURBIA_PATH)
        if self._available:
            log.info("[RESERVATION] Worker subprocess prêt")
        else:
            log.error(
                f"[RESERVATION] Worker introuvable — WORKER={WORKER_PATH} DOURBIA={DOURBIA_PATH}"
            )

    async def handle_message(self, message: str, session_id: str) -> dict:
        if not self._available:
            return self._fallback_response()
        try:
            payload = json.dumps({"message": message, "session_id": session_id})

            # Windows : subprocess nécessite ProactorEventLoop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._run_worker_sync, payload)
            return result

        except Exception as e:
            log.error(f"[RESERVATION] Erreur : {e}", exc_info=True)
            return self._fallback_response(erreur=str(e))

    def _run_worker_sync(self, payload: str) -> dict:
        """Lance le worker en subprocess synchrone (compatible Windows SelectorEventLoop)."""
        import subprocess
        try:
            proc = subprocess.run(
                [sys.executable, WORKER_PATH],
                input=payload.encode("utf-8"),
                capture_output=True,
                timeout=120,
                cwd=DOURBIA_PATH,
                env={**_os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            stderr_text = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ""
            if stderr_text:
                log.debug(f"[RESERVATION] worker stderr : {stderr_text[:2000]}")
            if proc.returncode != 0:
                log.error(f"[RESERVATION] Worker exit {proc.returncode} : {stderr_text[:300]}")
                return self._fallback_response(erreur=f"worker_exit_{proc.returncode}")
            result = json.loads(proc.stdout.decode("utf-8", errors="replace").strip())
            return {
                "disponible": True,
                "reponse": result["reply"],
                "tokens_uses": result.get("tokens", 0),
                "erreur": None,
            }
        except subprocess.TimeoutExpired:
            log.warning("[RESERVATION] Timeout worker (60s)")
            return self._fallback_response(erreur="timeout")
        except Exception as e:
            log.error(f"[RESERVATION] Erreur worker sync : {e}", exc_info=True)
            return self._fallback_response(erreur=str(e))

    def _fallback_response(self, erreur: Optional[str] = None) -> dict:
        return {
            "disponible": False,
            "reponse": (
                "Notre service de réservation est momentanément indisponible. "
                "Vous pouvez nous contacter directement au +216 XX XXX XXX "
                "ou réessayer dans quelques instants."
            ),
            "tokens_uses": 0,
            "erreur": erreur or "service_indisponible",
        }


_reservation_wrapper_instance: Optional[AgentReservationWrapper] = None


def get_reservation_wrapper() -> AgentReservationWrapper:
    global _reservation_wrapper_instance
    if _reservation_wrapper_instance is None:
        _reservation_wrapper_instance = AgentReservationWrapper()
    return _reservation_wrapper_instance
