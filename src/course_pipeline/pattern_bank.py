
from __future__ import annotations

PATTERN_BANK: dict[str, list[str]] = {
    "entry": [
        "What is {x}?",
        "What does {x} mean?",
        "Can you explain {x} in simple terms?",
    ],
    "purpose": [
        "Why does {x} matter?",
        "Why do we use {x}?",
        "What problem does {x} solve?",
    ],
    "mechanism": [
        "How does {x} work?",
        "What is the basic idea behind {x}?",
    ],
    "procedure": [
        "How do you use {x}?",
        "When would you use {x}?",
        "What are the steps for {x}?",
    ],
    "comparison": [
        "How is {x} different from {y}?",
        "When would I use {x} instead of {y}?",
    ],
    "failure": [
        "What can go wrong with {x}?",
        "What mistakes do people make with {x}?",
    ],
    "interpretation": [
        "What does {x} tell us?",
        "How should I interpret {x}?",
    ],
    "prerequisite": [
        "What do I need to know before {x}?",
    ],
    "example": [
        "What is a simple example of {x}?",
    ],
    "decision": [
        "How do I know whether to use {x}?",
        "When should I not use {x}?",
    ],
}


TOPIC_TYPE_FAMILIES: dict[str, list[str]] = {
    "concept": ["entry", "purpose", "example"],
    "procedure": ["entry", "procedure", "purpose", "failure"],
    "method": ["entry", "procedure", "purpose", "failure"],
    "tool": ["entry", "procedure", "purpose", "failure"],
    "metric": ["entry", "interpretation", "purpose"],
    "test": ["entry", "interpretation", "purpose"],
    "comparison_pair_candidate": [],
    "wrapper_or_container_candidate": [],
    "unknown": ["entry"],
    "chapter_wrapper": [],
    "example_block": [],
    "case_study_container": [],
    "other": ["entry"],
}
