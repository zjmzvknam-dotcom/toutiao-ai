from app.models.domain import ImageCandidate
from app.services.images import verify_candidate


def test_image_without_provenance_is_rejected() -> None:
    candidate = verify_candidate(ImageCandidate(url="https://example.com/image.jpg"), required_terms=["汽车"])
    assert candidate.verified is False
    assert candidate.label == "未使用"


def test_manual_confirmation_can_be_stored_without_claiming_automatic_verification() -> None:
    candidate = ImageCandidate(url="https://images.example.com/a.jpg", source="Pexels · Photographer · https://www.pexels.com/photo/a", label="真实来源候选", verified=False, reason="待人工审核")
    approved = candidate.model_copy(update={"verified": True, "label": "真实来源图片（人工确认）"})
    assert approved.verified is True
    assert "人工确认" in approved.label
