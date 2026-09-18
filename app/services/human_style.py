"""Context-sensitive prose signals; never an AI authorship detector."""
from __future__ import annotations

import json
import re
from statistics import mean, pstdev

from app.services.personas import resolve_persona

CONNECTORS = ("首先", "其次", "最后", "此外", "与此同时", "值得注意的是", "不可否认", "不难发现", "由此可见", "综上所述", "总而言之")
PATTERNS = (r"随着.{0,18}不断", r"在当今", r"在这个.{0,12}时代", r"这不仅.{0,40}更", r"无论是.{0,40}还是", r"对于.{0,20}而言")
FIRSTHAND = r"我(?:昨天|亲眼|亲自|朋友|买过|去过|试驾过|家孩子|退休前)"


def paragraphs(body: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]


def inspect_style(body: str) -> dict:
    ps = paragraphs(body)
    issues: dict[int, list[str]] = {}
    def add(i, reason):
        issues.setdefault(i, []).append(reason)
    connector_count = sum(sum(p.count(w) for w in CONNECTORS) for p in ps)
    # One natural "最后" is not a violation. Repeated paragraph scaffolds are.
    starts = [i for i, p in enumerate(ps) if p.lstrip("*# ").startswith(CONNECTORS)]
    if len(starts) >= 3 or connector_count >= 5:
        for i in starts:
            add(i, "连接词密集，段落推进机械")
    templates = [i for i, p in enumerate(ps) if any(re.search(pattern, p) for pattern in PATTERNS)]
    if len(templates) >= 3:
        for i in templates:
            add(i, "同类模板句重复")
    lengths = [len(p) for p in ps if not p.startswith("#")]
    if len(lengths) >= 5 and mean(lengths) > 40 and pstdev(lengths) / mean(lengths) < .12:
        add(len(ps) // 2, "段落长度过于整齐，可合并或改变表达节奏")
    headings = [i for i, p in enumerate(ps) if p.startswith("#") or re.match(r"^\*\*[^*]{1,25}\*\*", p)]
    if len(headings) >= 4:
        for i in headings[1:]:
            add(i, "小标题连续出现，像提纲")
    if ps and ps[-1].startswith(("综上所述", "总而言之", "由此可见")) and (connector_count >= 3 or len(ps[-1]) > 120):
        add(len(ps) - 1, "收尾复述或总结腔")
    return {"connector_count": connector_count, "paragraph_count": len(ps), "issues": [{"paragraph": i, "reasons": reasons} for i, reasons in sorted(issues.items())]}


def improve_locally(body: str, persona: str, router, *, enabled: bool = True) -> tuple[str, dict]:
    before = inspect_style(body)
    report = {"before": before, "after": before, "calls": 0, "accepted": [], "status": "无需局部润色"}
    if not enabled or not before["issues"]:
        return body, report
    ps = paragraphs(body)
    chosen = before["issues"][:2]
    # One bounded call, only the flagged paragraphs, never a whole-article pass.
    inputs = [{"paragraph": row["paragraph"], "text": ps[row["paragraph"]], "reasons": row["reasons"]} for row in chosen]
    prompt = (
        "局部编辑中文正文，保留事实、专名、数字、引文和立场。不要新增经历、数据或因果结论。"
        "只改给定段落的节奏和措辞，不写全文，不添加标题。\n"
        + resolve_persona(persona).instruction()
        + '\n只返回 JSON 数组，每项 {"paragraph": 原索引, "text": 新段落}。原文如下：'
        + json.dumps(inputs, ensure_ascii=False)
    )
    try:
        report["calls"] = 1
        raw = router.generate("writing", prompt)
        changes = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        if not isinstance(changes, list):
            raise ValueError("invalid changes")
        allowed = {row["paragraph"] for row in chosen}
        for change in changes:
            if not isinstance(change, dict):
                continue
            i, text = change.get("paragraph"), change.get("text")
            if type(i) is not int or i not in allowed or not isinstance(text, str):
                continue
            original = ps[i]
            # Reject changed numeric facts, citations, quoted material, or invented first-person claims.
            protected = r"\d+(?:\.\d+)?%?|https?://[^\s]+|[“「][^”」]+[”」]|[A-Z][A-Za-z0-9_-]+"
            if re.findall(protected, original) != re.findall(protected, text):
                continue
            if re.search(FIRSTHAND, text) and not re.search(FIRSTHAND, original):
                continue
            if not .45 * len(original) <= len(text) <= 1.4 * len(original):
                continue
            ps[i] = text.strip()
            allowed.remove(i)
            report["accepted"].append(i)
        result = "\n\n".join(ps)
        after = inspect_style(result)
        if len(after["issues"]) > len(before["issues"]):
            result, after, report["accepted"] = body, before, []
        report.update(after=after, status="已局部润色" if report["accepted"] else "保留原稿")
        return result, report
    except Exception:
        report["status"] = "局部润色不可用，保留原稿"
        return body, report
