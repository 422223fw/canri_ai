"""
UnderstandingDk - Dictionary, Grammar & Connections Engine
"""

from .loader import (
    load,

    # dictionary functions
    search_word,
    search_prefix,
    search_range,
    search_type,
    search_definition,
    search_ending,
    search_length,
    search_length_range,

    related,
    random_word,
    suggest,

    get_meanings,
    count_words,
    get_all_words,
    get_word_types,
    word_exists,
    stats,

    # grammar functions (NEW)
    grammar_exists,
    get_forms,
    get_tense,
    convert_tense,
    get_all_by_tense,
    detect_tense,
    get_verb_base,
    analyze_sentence,
    fix_sentence
)

# טעינה אוטומטית ובטוחה
try:
    load()
except Exception as e:
    print("UnderstandingDk failed to load:", e)


__all__ = [

    # core
    "load",

    # dictionary
    "search_word",
    "search_prefix",
    "search_range",
    "search_type",
    "search_definition",
    "search_ending",
    "search_length",
    "search_length_range",

    "related",
    "random_word",
    "suggest",

    "get_meanings",
    "count_words",
    "get_all_words",
    "get_word_types",
    "word_exists",
    "stats",

    # grammar
    "grammar_exists",
    "get_forms",
    "get_tense",
    "convert_tense",
    "get_all_by_tense",
    "detect_tense",
    "get_verb_base",
    "analyze_sentence",
    "fix_sentence"
]