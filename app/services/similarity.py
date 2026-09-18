from __future__ import annotations

import re


def character_ngrams(text: str, size: int = 3) -> set[str]:
    normalized = re.sub(r"\s+", "", text)
    return {normalized[index:index + size] for index in range(max(0, len(normalized) - size + 1))}


def highest_similarity(text: str, corpus: list[str]) -> float:
    source = character_ngrams(text)
    if not source:
        return 0.0
    scores = []
    for candidate in corpus:
        target = character_ngrams(candidate)
        scores.append(len(source & target) / len(source | target) if target else 0.0)
    return max(scores, default=0.0)
