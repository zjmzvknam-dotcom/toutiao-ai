from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def test_homepage_renders_without_runtime_exception() -> None:
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
    app.run(timeout=10)
    assert not app.exception
    assert app.title[0].value == "今日头条 AI 内容创作工作台"
    assert any(item.label == "关键词或选题" for item in app.text_input)
    assert any(item.label == "开始创作" for item in app.button)


def test_settings_and_cost_tabs_render() -> None:
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
    app.run(timeout=10)
    assert not app.exception
    assert len(app.tabs) == 5
