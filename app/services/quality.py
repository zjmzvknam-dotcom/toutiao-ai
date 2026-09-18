from __future__ import annotations

from app.models.domain import QualityReport


def assess(body: str, risk: str) -> QualityReport:
    words = len(body.replace("\n", ""))
    paragraphs = [item.strip() for item in body.split("\n") if item.strip()]
    repetitive = len(set(paragraphs)) < len(paragraphs)
    notes = []
    if words < 300:
        notes.append("正文较短，建议补充可核实的案例、数据或来源。")
    if risk != "低":
        notes.append("题材存在风险：发布前需人工核验事实、措辞与平台规则。")
    notes.append("本地质量评分为辅助信号，不等同于原创或平台审核结论。")
    return QualityReport(information_density=min(90, 45 + words // 20), readability=78 if len(paragraphs) >= 3 else 60, duplication_risk="中" if repetitive else "低", fact_risk="中" if risk != "低" else "待来源核验", sensitivity_risk=risk, template_risk="低" if len(paragraphs) >= 4 else "中", notes=notes)
