from app.providers.base import ModelProvider
from app.providers.router import MultiModelRouter, RoutedModel


class FakeProvider(ModelProvider):
    name = "Fake"

    def generate(self, prompt: str, *, model: str) -> str:
        return f"{model}:{prompt}"

    def test_connection(self, *, model: str) -> tuple[bool, str]:
        return True, "ok"


def test_multi_model_router_routes_each_workflow_independently() -> None:
    router = MultiModelRouter({"cheap": FakeProvider(), "best": FakeProvider()}, {"analysis": RoutedModel("cheap", "small"), "writing": RoutedModel("best", "large")})
    assert router.generate("analysis", "x") == "small:x"
    assert router.generate("writing", "x") == "large:x"
    assert router.model_for("quality") == "large"
