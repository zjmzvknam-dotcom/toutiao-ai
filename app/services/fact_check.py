from __future__ import annotations

from app.models.domain import Evidence


def verification_notes(evidence: list[Evidence], body: str) -> list[str]:
    notes: list[str] = []
    if not evidence or all(item.confidence == "未核实" for item in evidence):
        notes.append("没有可核验的外部来源；任何具体数据、人物、时间或产品结论都应补充一手来源。")
    else:
        notes.append("检索结果是来源线索，不代表对正文每项表述的确认；发布前需逐条打开原始链接复核。")
    high_certainty = ("一定", "必然", "官方确认", "已经证实")
    if any(term in body for term in high_certainty):
        notes.append("正文含高确定性措辞；请确认存在对应的一手来源，或改为条件性表达。")
    return notes
