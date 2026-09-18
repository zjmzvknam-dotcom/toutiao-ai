from __future__ import annotations

from dataclasses import dataclass

from app.providers.base import ModelProvider


@dataclass
class ModelRoute:
    workflow: str
    model: str


class ModelRouter:
    def __init__(self, provider: ModelProvider | None, routes: dict[str, str] | None = None) -> None:
        self.provider = provider
        self.usage_log: list[dict] = []
        self.routes = routes or {"analysis": "", "writing": "", "quality": ""}

    def model_for(self, workflow: str) -> str:
        return self.routes.get(workflow, self.routes.get("writing", ""))

    def generate(self, workflow: str, prompt: str) -> str | None:
        if not self.provider or not self.model_for(workflow):
            return None
        return _logged_generate(self, self.provider, "default", workflow, prompt)

    def usage_for(self, workflow: str) -> dict[str, int]:
        return dict(getattr(self.provider, "last_usage", {})) if self.provider else {}


@dataclass(frozen=True)
class RoutedModel:
    profile_id: str
    model: str


class MultiModelRouter:
    """Routes each workflow to an independently configured provider profile."""

    def __init__(self, providers: dict[str, ModelProvider], routes: dict[str, RoutedModel]) -> None:
        self.providers = providers
        self.usage_log: list[dict] = []
        self.routes = routes

    def model_for(self, workflow: str) -> str:
        route = self.routes.get(workflow) or self.routes.get("writing")
        return route.model if route else ""

    def provider_for(self, workflow: str) -> str:
        route = self.routes.get(workflow) or self.routes.get("writing")
        return route.profile_id if route else ""

    def generate(self, workflow: str, prompt: str) -> str | None:
        route = self.routes.get(workflow) or self.routes.get("writing")
        if not route or not route.model or route.profile_id not in self.providers:
            return None
        return _logged_generate(self, self.providers[route.profile_id], route.profile_id, workflow, prompt)

    def usage_for(self, workflow: str) -> dict[str, int]:
        route = self.routes.get(workflow) or self.routes.get("writing")
        if not route:
            return {}
        return dict(getattr(self.providers.get(route.profile_id), "last_usage", {}))


def _logged_generate(router, provider, provider_name, workflow, prompt):
    usage = {}
    try:
        result = provider.generate(prompt, model=router.model_for(workflow))
        usage = router.usage_for(workflow)
        return result
    finally:
        router.usage_log.append({"provider": provider_name, "model": router.model_for(workflow), "workflow": workflow, "tokens": usage.get("total_tokens", 0)})
