from __future__ import annotations

import re


def character_ngrams(text: str, size: int = 3) -> set[str]:
    normalized = re.sub(r"\s+", "", text)
    return {normalized[index:index + size] for index in range(max(0, len(normalized) - size + 1))}


def highest_similarity(text: str, corpus: list[str]) -> float:
    source_paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not source_paragraphs:
        return 0.0
    scores = []
    for candidate in corpus:
        target_paragraphs = [part.strip() for part in re.split(r"\n\s*\n", candidate) if part.strip()]
        paragraph_scores: list[float] = []
        for source_paragraph in source_paragraphs:
            source_ngrams = character_ngrams(source_paragraph)
            if not source_ngrams:
                continue
            best = 0.0
            for target_paragraph in target_paragraphs:
                target_ngrams = character_ngrams(target_paragraph)
                if target_ngrams:
                    best = max(best, len(source_ngrams & target_ngrams) / len(source_ngrams | target_ngrams))
            paragraph_scores.append(best)
        if paragraph_scores:
            # A shared boilerplate paragraph should not dominate the result.
            # Two strongest matching paragraphs are a better duplicate signal.
            strongest = sorted(paragraph_scores, reverse=True)[:2]
            scores.append(sum(strongest) / len(strongest))
    return max(scores, default=0.0)
