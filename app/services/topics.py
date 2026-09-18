from __future__ import annotations

from app.models.domain import Topic

RISK_TERMS = {"政治": "高", "医疗": "中", "治疗": "高", "投资": "高", "股票": "高", "未成年人": "高", "爆料": "高", "犯罪": "高"}


def analyze_topic(keyword: str) -> Topic:
    keyword = keyword.strip()
    levels = [level for term, level in RISK_TERMS.items() if term in keyword]
    risk = max(levels, key=lambda level: {"低": 0, "中": 1, "高": 2}[level], default="低")
    # Transparent heuristic for offline availability; it is not a claim of live trend data.
    seed = sum(ord(char) for char in keyword)
    return Topic(title=keyword, heat=45 + seed % 41, growth=35 + (seed // 7) % 51, competition=30 + (seed // 11) % 51, content_value=50 + (seed // 13) % 41, monetization=30 + (seed // 17) % 51, lifecycle="需通过真实趋势 Provider 更新", risk=risk, angle="普通人影响与行业变化")


def topic_angles(topic: Topic) -> list[str]:
    return ["事件与已知信息解读", "普通人会受到什么影响", "行业变化与竞争格局", "关键原因与限制条件", "未来趋势及待观察信号"]
