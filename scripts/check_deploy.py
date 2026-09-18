"""Offline preflight for Streamlit Community Cloud readiness."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("streamlit_app.py", "requirements.txt", "runtime.txt", ".streamlit/config.toml", ".gitignore")
IGNORED_SECRET_RULES = (".env", ".streamlit/secrets.toml", "*.sqlite*")
FORBIDDEN_PATTERNS = ("sk-", "AKIA", "AIza")


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"缺少部署必需文件：{relative}")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    for rule in IGNORED_SECRET_RULES:
        if rule not in gitignore:
            errors.append(f".gitignore 未覆盖：{rule}")
    for file in ROOT.rglob("*"):
        if not file.is_file() or file.resolve() == Path(__file__).resolve() or ".git" in file.parts or "__pycache__" in file.parts:
            continue
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern in content for pattern in FORBIDDEN_PATTERNS):
            errors.append(f"检测到可能的密钥特征：{file.relative_to(ROOT)}")
    if errors:
        print("部署预检失败：")
        print("\n".join(f"- {item}" for item in errors))
        return 1
    print("部署预检通过：入口、依赖、运行时配置与基础密钥忽略规则均已就绪。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
