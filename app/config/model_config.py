"""Resolve deployment credentials without logging or persisting them."""
from collections.abc import Mapping


def deployed_model(values: Mapping) -> dict:
    key = values.get("DEEPSEEK_API_KEY", "")
    if key:
        return {"enabled": True, "api_key": key, "model": values.get("DEEPSEEK_MODEL", "deepseek-chat"), "base_url": "https://api.deepseek.com"}
    key = values.get("MODEL_API_KEY", "") or values.get("OPENAI_API_KEY", "")
    model = values.get("MODEL_NAME", "") or values.get("OPENAI_MODEL", "")
    if key and model:
        return {"enabled": True, "api_key": key, "model": model, "base_url": values.get("MODEL_BASE_URL", "https://api.openai.com/v1")}
    return {}
