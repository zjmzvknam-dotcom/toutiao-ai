import base64
import json
from io import BytesIO
from zipfile import ZipFile

from PIL import Image

from app.models.domain import Article, TaskStatus
from app.providers.image_generation import configured_generator, HuggingFaceImageGenerator
from app.services.illustrations import illustrate, inline_content, image_budget
from app.services.export import word_document, markdown
from app.services.quality import assess
from app.repositories.sqlite import SQLiteRepository


BODY = "周末去菜市场，挑一把青菜，别买太多。\n\n布袋提在手里，路过摊位时可以慢慢看。"


def article(body=BODY):
    return Article(topic="买菜", title="买菜", body=body, model="test", quality=assess(body, "低"))


class Planner:
    calls = 0
    def generate(self, workflow, prompt):
        self.calls += 1
        assert "挑一把青菜" in prompt
        assert "safe_generic" in prompt
        return json.dumps([{"paragraph": 0, "anchor": "青菜", "safe_generic": True, "prompt": "A bunch of fresh green vegetables at a modest everyday Chinese market stall."}])


class Generator:
    name, model, calls = "Fake image", "mock-no-cloud", 0
    def generate(self, prompt):
        self.calls += 1
        assert "natural lighting" in prompt
        result = BytesIO()
        Image.new("RGB", (64, 48), "green").save(result, format="PNG")
        return result.getvalue()


def test_off_makes_zero_planner_or_image_calls():
    planner, generator = Planner(), Generator()
    original = article()
    assert illustrate(original, planner, generator, enabled=False) is original
    assert planner.calls == generator.calls == 0


def test_missing_key_keeps_body_without_planner_call():
    planner = Planner()
    result = illustrate(article(), planner, None, enabled=True)
    assert result.body == BODY and not result.illustrations
    assert planner.calls == 0
    assert result.metadata["ai_images"]["failed"]


def test_generation_insert_export_save_and_no_repeat(tmp_path):
    planner, generator = Planner(), Generator()
    result = illustrate(article(), planner, generator, enabled=True)
    assert len(result.illustrations) == 1
    assert list(inline_content(result))[0][1][0].subject == "青菜"
    assert list(inline_content(result))[1][1] == []
    assert "AI生成示意图" in markdown(result)
    with ZipFile(BytesIO(word_document(result))) as archive:
        assert any(name.startswith("word/media/") for name in archive.namelist())
    repo = SQLiteRepository(tmp_path / "test.db")
    repo.save_article(result)
    assert repo.list_articles()[0].illustrations == result.illustrations
    illustrate(result, planner, generator, enabled=True)
    assert planner.calls == generator.calls == 1
    edited = result.model_copy(update={"body": "正文已经彻底换了。"})
    assert not list(inline_content(edited))[0][1]


def test_timeout_does_not_discard_article_or_leak_key():
    class Broken(Generator):
        def generate(self, prompt):
            self.calls += 1
            raise TimeoutError("HF_PRIVATE_SECRET")
    generator = Broken()
    result = illustrate(article(), Planner(), generator, enabled=True)
    assert result.body == BODY and result.status == TaskStatus.PARTIAL_SUCCESS
    assert generator.calls == 1
    assert "HF_PRIVATE_SECRET" not in result.model_dump_json()


def test_sensitive_news_does_not_call_planner_or_generator():
    planner, generator = Planner(), Generator()
    result = illustrate(article("这是一场真实车祸的报道。"), planner, generator, enabled=True)
    assert "跳过" in result.metadata["ai_images"]["status"]
    assert planner.calls == generator.calls == 0


def test_unanchored_unsafe_duplicate_plans_are_rejected():
    class Invalid:
        def generate(self, *args):
            return json.dumps([
                {"paragraph": 0, "anchor": "汽车", "safe_generic": True, "prompt": "A random car parked outside a building."},
                {"paragraph": 1, "anchor": "布袋", "safe_generic": False, "prompt": "A generic bag at a market in natural light."},
            ])
    generator = Generator()
    result = illustrate(article(), Invalid(), generator, enabled=True)
    assert generator.calls == 0 and not result.illustrations


def test_budget_and_lazy_configuration():
    assert [image_budget("字" * n) for n in (300, 700, 1200, 2200)] == [1, 2, 3, 4]
    assert configured_generator({}) is None
    assert configured_generator({"HF_TOKEN": "private"}).model == "black-forest-labs/FLUX.1-schnell"
    assert configured_generator({"HF_TOKEN": "private", "AI_IMAGE_MODEL": "test-model"}).model == "test-model"


def test_official_sdk_contract_without_live_charges(monkeypatch):
    calls = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs == {"api_key": "test-only", "provider": "auto", "timeout": 45}
        def text_to_image(self, prompt, **kwargs):
            calls.append((prompt, kwargs))
            return Image.new("RGB", (64, 48))
        def close(self):
            pass
    monkeypatch.setattr("huggingface_hub.InferenceClient", Client)
    data = HuggingFaceImageGenerator("test-only", "configurable-model").generate("vegetables")
    assert data.startswith(b"\xff\xd8")
    assert calls[0][1]["model"] == "configurable-model"
