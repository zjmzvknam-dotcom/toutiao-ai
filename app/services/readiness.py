from __future__ import annotations

from app.models.domain import Evidence, ImageCandidate, PublicationReadiness, PublicationStatus, QualityReport


def assess_readiness(*, evidence: list[Evidence], image: ImageCandidate, image_requested: bool, quality: QualityReport) -> PublicationReadiness:
    checks = ["标题策略与本地质量检测已完成。", "高风险题材已在生成前经过确认门槛。"]
    blockers: list[str] = []
    if not evidence or all(item.confidence in {"未核实", "待人工核验"} for item in evidence):
        blockers.append("资料来源尚未完成人工核验，不能把正文中的具体结论视为已确认事实。")
    else:
        checks.append("存在至少一项已核验的资料来源。")
    if quality.sensitivity_risk == "高":
        blockers.append("高风险题材需要发布前人工复核措辞、事实和平台规则。")
    if quality.duplication_risk != "低":
        blockers.append("同质化风险尚未降至低水平。")
    if image_requested and not image.verified:
        blockers.append("已请求配图，但没有人工确认的图片来源与语义匹配。")
    elif image.verified:
        checks.append("图片已人工确认来源与语义匹配。")
    else:
        checks.append("未请求配图；图片不影响文字发布。")
    return PublicationReadiness(status=PublicationStatus.READY if not blockers else PublicationStatus.NEEDS_REVIEW, checks=checks, blockers=blockers)
