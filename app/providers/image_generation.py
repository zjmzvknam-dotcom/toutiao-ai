"""Remote inference only. No local weights, GPU, credentials in output or retries."""
from typing import Protocol
from io import BytesIO

DEFAULT_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"


class ImageGenerator(Protocol):
    name: str
    model: str

    def generate(self, prompt: str) -> bytes: ...


class HuggingFaceImageGenerator:
    def __init__(self, api_key: str, model: str, provider: str = "auto"):
        self._api_key = api_key
        self.model = model
        self.provider = provider
        self.name = f"Hugging Face / {provider}"

    def generate(self, prompt: str) -> bytes:
        # Lazy import: text-only articles don't need even an initialized image client.
        from huggingface_hub import InferenceClient
        client = InferenceClient(api_key=self._api_key, provider=self.provider, timeout=45)
        try:
            picture = client.text_to_image(prompt, model=self.model, width=1024, height=768)
            picture.thumbnail((1024, 768))
            output = BytesIO()
            picture.convert("RGB").save(output, format="JPEG", quality=85)
            return output.getvalue()
        finally:
            client.close()


def configured_generator(values: dict) -> ImageGenerator | None:
    key = str(values.get("HF_TOKEN", "")).strip()
    model = str(values.get("AI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)).strip()
    provider = str(values.get("AI_IMAGE_PROVIDER", "auto")).strip() or "auto"
    return HuggingFaceImageGenerator(key, model, provider) if key and model else None
