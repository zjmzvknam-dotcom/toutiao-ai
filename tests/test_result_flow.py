from datetime import datetime, timezone
from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

from app.config.model_config import deployed_model
from app.providers.images import WikimediaCommonsImageProvider
from app.repositories.sqlite import SQLiteRepository

ROOT = Path(__file__).resolve().parents[1]
BODY = ("人到中年，最难说出口的，往往不是忙，而是累。\n\n" + "工作和家庭的责任交织在一起，能留给自己的时间越来越少。我们也需要允许自己停下来，和家人说说真实的感受。\n\n" * 4).strip()


def isolated_app(monkeypatch, tmp_path):
    from app.providers.trends import MultiSourceTrendProvider
    from app.config.settings import Settings
    monkeypatch.setattr(MultiSourceTrendProvider, "fetch", lambda *a, **kw: ([], [], datetime.now(timezone.utc)))
    monkeypatch.setattr("app.config.settings.settings", Settings(database_path=tmp_path / "isolated.sqlite3"))
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
    return app


def test_first_submit_body_edit_and_repeat_visible(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.model_config.deployed_model", lambda values: {"api_key": "test-only", "enabled": True, "base_url": "https://example.com", "model": "fake"})
    monkeypatch.setattr("app.providers.openai_compatible.OpenAICompatibleProvider.generate", lambda *a, **kw: BODY)
    app = isolated_app(monkeypatch, tmp_path).run(timeout=15)
    next(w for w in app.text_input if w.label == "关键词或选题").set_value("中年人的心酸")
    next(w for w in app.button if w.label == "开始创作").click().run(timeout=15)
    assert not app.exception
    assert app.session_state["current_article"].body == BODY
    assert any(w.value == BODY for w in app.markdown)
    next(w for w in app.text_area if w.label == "完整正文").set_value(BODY + "\n保存的修改。")
    next(w for w in app.button if w.label == "保存修改").click().run(timeout=15)
    assert not app.exception
    assert "保存的修改" in app.session_state["current_article"].body
    next(w for w in app.button if w.label == "开始创作").click().run(timeout=15)
    assert not app.exception
    assert any(w.value == BODY for w in app.markdown)


def test_no_model_shows_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.model_config.deployed_model", lambda values: {})
    app = isolated_app(monkeypatch, tmp_path).run(timeout=15)
    next(w for w in app.text_input if w.label == "关键词或选题").set_value("中年人的心酸")
    next(w for w in app.button if w.label == "开始创作").click().run(timeout=15)
    assert not app.exception
    assert any("尚未连接写作模型" in w.value for w in app.error)
    assert "current_article" not in app.session_state


def test_commons_excludes_books_and_unrelated_images(monkeypatch):
    def page(title, mime, description):
        return {"pageid": 1, "title": title, "imageinfo": [{"mime": mime, "url": "https://upload.wikimedia.org/test.jpg", "extmetadata": {"ImageDescription": {"value": description}, "LicenseShortName": {"value": "CC BY-SA"}}}]}
    pages = [page("book.djvu", "image/vnd.djvu", "中年人的心酸"), page("rocket.jpg", "image/jpeg", "rocket"), page("street.jpg", "image/jpeg", "黄昏街道")]
    monkeypatch.setattr("app.providers.images.httpx.get", lambda *a, **kw: httpx.Response(200, json={"query": {"pages": pages}}, request=httpx.Request("GET", "https://example.com")))
    assert WikimediaCommonsImageProvider().find("中年人的心酸") == []
    assert len(WikimediaCommonsImageProvider().find("黄昏街道")) == 1


def test_deployment_deepseek_config():
    cfg = deployed_model({"DEEPSEEK_API_KEY": "test-only"})
    assert cfg["model"] == "deepseek-chat"
    assert cfg["enabled"]
