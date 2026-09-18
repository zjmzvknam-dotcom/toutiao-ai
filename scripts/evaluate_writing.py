"""Bounded live acceptance run. Credentials never enter the saved report."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config.model_config import deployed_model
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.router import ModelRouter
from app.services.topics import analyze_topic
from app.workflows.article import ArticleWorkflow

CASES = [
    ("中年人的心酸", "普通上班族"),
    ("旧手机还能用，要不要换新手机", "年轻消费者"),
    ("周末去菜市场买菜", "普通城市居民"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["before", "after"], required=True)
    parser.add_argument("--revision", default="")
    args = parser.parse_args()
    cfg = deployed_model(os.environ)
    if not cfg:
        print("No configured writer; live evaluation not run.")
        return 2
    client = OpenAICompatibleProvider(cfg["api_key"], cfg["base_url"], timeout_seconds=90)
    router = ModelRouter(client, {"writing": cfg["model"]})
    cases = CASES + ([("中年人的心酸", "退休老人"), ("旧手机还能用，要不要换新手机", "数码爱好者")] if args.phase == "after" else [])
    folder = Path("outputs/writing-evaluation")
    folder.mkdir(parents=True, exist_ok=True)
    for index, (topic, persona) in enumerate(cases, 1):
        target = folder / f"{args.phase}{args.revision}-{index}.json"
        if target.exists():
            print(f"Already evaluated {args.phase}-{index}", flush=True)
            continue
        try:
            article = ArticleWorkflow(router).run(analyze_topic(topic), length=650, persona=persona)
            target.write_text(json.dumps({"topic": topic, "persona": persona, "model": cfg["model"], "body": article.body, "style": article.metadata.get("human_style", {}), "usage": client.last_usage}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{args.phase}-{index}: {len(article.body)} chars", flush=True)
        except Exception as exc:
            print(f"{args.phase}-{index}: failed ({type(exc).__name__}); no response body logged", flush=True)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
