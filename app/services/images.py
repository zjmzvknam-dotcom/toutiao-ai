from __future__ import annotations

from app.models.domain import ImageCandidate


def verify_candidate(candidate: ImageCandidate, *, required_terms: list[str]) -> ImageCandidate:
    """Conservative verifier: absent provenance or missing required context means rejection."""
    corpus = " ".join([candidate.source, candidate.reason]).lower()
    if not candidate.url or not candidate.source:
        return candidate.model_copy(update={"verified": False, "label": "未使用", "reason": "缺少可核验的来源或原始 URL。"})
    if not all(term.lower() in corpus for term in required_terms if term.strip()):
        return candidate.model_copy(update={"verified": False, "label": "未使用", "reason": "图片元数据无法证明与人物、产品或事件匹配。"})
    return candidate.model_copy(update={"verified": True, "label": "真实来源图片", "reason": "仅通过来源元数据的初筛；发布前仍应人工复核版权和现场语境。"})
