from __future__ import annotations

from app.rag.language_detection import normalize_supported_language

INSUFFICIENT_CONTEXT_ANSWERS = {
    "fr": (
        "Je ne dispose pas d'informations suffisantes dans ma base documentaire "
        "pour répondre à cette question avec certitude."
    ),
    "en": (
        "I do not have enough information in the local knowledge base "
        "to answer this question with confidence."
    ),
    "ar": (
        "لا أملك معلومات كافية في قاعدة المعرفة المحلية "
        "للإجابة على هذا السؤال بثقة."
    ),
}

NO_RELEVANT_WEB_RESULTS_ANSWERS = {
    "fr": (
        "Je n'ai pas trouvé de résultats web clairement liés à votre question. "
        "Ma base documentaire locale ne contient pas non plus d'informations "
        "pertinentes sur ce sujet."
    ),
    "en": (
        "I could not find web results clearly related to your question. "
        "The local knowledge base also does not contain relevant information "
        "on this topic."
    ),
    "ar": (
        "لم أجد نتائج ويب مرتبطة بوضوح بسؤالك. "
        "كما أن قاعدة المعرفة المحلية لا تحتوي على معلومات مناسبة "
        "حول هذا الموضوع."
    ),
}

NO_ART_WEB_RESULTS_ANSWERS = {
    "fr": (
        "Je n'ai pas trouvé, dans la base locale ni en ligne, d'informations "
        "précises sur des œuvres artistiques liées à ce monument. "
        "Les sources consultées décrivent surtout l'histoire ou la visite du site, "
        "sans identifier d'objets ou de créations artistiques particulières."
    ),
    "en": (
        "I could not find precise information about artworks linked to this monument "
        "in the local knowledge base or online. Available sources mainly describe "
        "the site's history or visit, without identifying specific artistic objects."
    ),
    "ar": (
        "لم أجد معلومات دقيقة عن أعمال فنية مرتبطة بهذا الأثر في المصادر المحلية "
        "أو عبر الإنترنت. المصادر المتاحة تصف تاريخ الموقع أو زيارته دون تحديد "
        "قطع أو أعمال فنية محددة."
    ),
}

LOCAL_CONTEXT_NOT_RELEVANT_NOTES = {
    "fr": (
        "La base documentaire locale ne contient pas d'informations pertinentes "
        "pour cette question (monuments et circuits touristiques uniquement)."
    ),
    "en": (
        "The local knowledge base does not contain relevant information for this "
        "question (tourist monuments and circuits only)."
    ),
    "ar": (
        "قاعدة المعرفة المحلية لا تحتوي على معلومات مناسبة لهذا السؤال "
        "(الآثار والمسارات السياحية فقط)."
    ),
}

EMPTY_RETRIEVED_CONTEXT = {
    "fr": "Aucune source récupérée.",
    "en": "No retrieved sources.",
    "ar": "لا توجد مصادر مسترجعة.",
}

EMPTY_WEB_CONTEXT = {
    "fr": "Aucun résultat web.",
    "en": "No web results.",
    "ar": "لا توجد نتائج ويب.",
}

SUGGESTED_ACTIONS = {
    "show_hours": {
        "fr": "Afficher les horaires",
        "en": "Show opening hours",
        "ar": "عرض أوقات الزيارة",
    },
    "circuit_detail": {
        "fr": "Voir le détail du circuit",
        "en": "View circuit details",
        "ar": "عرض تفاصيل المسار",
    },
    "roman_circuit": {
        "fr": "Proposer un circuit romain",
        "en": "Suggest a Roman tour",
        "ar": "اقتراح مسار روماني",
    },
    "time_adapted_visit": {
        "fr": "Proposer une visite adaptée à votre temps",
        "en": "Suggest a visit suited to your time",
        "ar": "اقتراح زيارة مناسبة لوقتك",
    },
    "nearby_monuments": {
        "fr": "Voir les monuments proches",
        "en": "View nearby monuments",
        "ar": "عرض الآثار القريبة",
    },
    "ask_another": {
        "fr": "Poser une autre question sur Carthage",
        "en": "Ask another question about Carthage",
        "ar": "اطرح سؤالاً آخر عن قرطاج",
    },
}


def localized_message(catalog: dict[str, str], language: str) -> str:
    normalized = normalize_supported_language(language)
    return catalog.get(normalized, catalog["fr"])


def localized_action(action_key: str, language: str) -> str:
    catalog = SUGGESTED_ACTIONS[action_key]
    return localized_message(catalog, language)
