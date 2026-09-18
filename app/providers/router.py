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
        self.routes = routes or {"analysis": "", "writing": "", "quality": ""}

    def model_for(self, workflow: str) -> str:
        return self.routes.get(workflow, self.routes.get("writing", ""))

    def generate(self, workflow: str, prompt: str) -> str | None:
        if not self.provider or not self.model_for(workflow):
            return None
        return self.provider.generate(prompt, model=self.model_for(workflow))

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
        return self.providers[route.profile_id].generate(prompt, model=route.model)

    def usage_for(self, workflow: str) -> dict[str, int]:
        route = self.routes.get(workflow) or self.routes.get("writing")
        if not route:
            return {}
        return dict(getattr(self.providers.get(route.profile_id), "last_usage", {}))
