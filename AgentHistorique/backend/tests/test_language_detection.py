from __future__ import annotations

from app.rag.language_detection import (
    detect_message_language,
    normalize_supported_language,
    resolve_answer_language,
)
from app.rag.language_messages import localized_action, localized_message
from app.rag.language_messages import INSUFFICIENT_CONTEXT_ANSWERS


def test_detect_message_language_arabic_script() -> None:
    assert detect_message_language("ما هي أهم آثار قرطاج؟") == "ar"


def test_detect_message_language_english() -> None:
    assert detect_message_language("What are the main Roman monuments in Carthage?") == "en"


def test_detect_message_language_english_contraction() -> None:
    assert detect_message_language("who's baal hammon ?") == "en"


def test_resolve_answer_language_english_overrides_arabic_memory() -> None:
    language = resolve_answer_language(
        "who's baal hammon ?",
        request_language="auto",
        memory_context={"preferred_language": "ar"},
    )
    assert language == "en"


def test_detect_message_language_french() -> None:
    assert detect_message_language("Quels sont les monuments romains à Carthage ?") == "fr"


def test_resolve_answer_language_prefers_current_message_over_memory() -> None:
    language = resolve_answer_language(
        "Tell me about the Roman theatre in Carthage",
        request_language="auto",
        memory_context={"preferred_language": "fr"},
    )
    assert language == "en"


def test_resolve_answer_language_honors_explicit_request() -> None:
    language = resolve_answer_language(
        "Parlez-moi du théâtre en anglais",
        request_language="auto",
        memory_context={"preferred_language": "fr"},
    )
    assert language == "en"


def test_resolve_answer_language_uses_memory_when_message_is_ambiguous() -> None:
    language = resolve_answer_language(
        "Carthage",
        request_language="auto",
        memory_context={"preferred_language": "ar"},
    )
    assert language == "ar"


def test_normalize_supported_language_accepts_auto() -> None:
    assert normalize_supported_language("auto") == "fr"


def test_localized_messages_and_actions() -> None:
    assert "confidence" in localized_message(INSUFFICIENT_CONTEXT_ANSWERS, "en")
    assert localized_action("show_hours", "ar") == "عرض أوقات الزيارة"
