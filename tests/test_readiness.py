from app.models.domain import Evidence, ImageCandidate, QualityReport, PublicationStatus
from app.services.readiness import assess_readiness


def report() -> QualityReport:
    return QualityReport(information_density=80, readability=80, duplication_risk="低", fact_risk="低", sensitivity_risk="低", template_risk="低")


def test_unverified_evidence_is_not_ready_for_publication() -> None:
    readiness = assess_readiness(evidence=[Evidence(claim="claim", source_name="source", confidence="待人工核验")], image=ImageCandidate(), image_requested=False, quality=report())
    assert readiness.status == PublicationStatus.NEEDS_REVIEW


def test_verified_evidence_and_not_requested_image_can_be_ready() -> None:
    readiness = assess_readiness(evidence=[Evidence(claim="claim", source_name="source", confidence="已核验")], image=ImageCandidate(), image_requested=False, quality=report())
    assert readiness.status == PublicationStatus.READY
