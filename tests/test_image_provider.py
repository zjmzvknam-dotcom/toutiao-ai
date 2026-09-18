from unittest.mock import Mock, patch

from app.providers.images import PexelsImageProvider


def test_pexels_returns_unverified_candidates_with_attribution() -> None:
    response = Mock()
    response.json.return_value = {"photos": [{"url": "https://www.pexels.com/photo/example", "photographer": "Example Photographer", "src": {"large": "https://images.pexels.com/example.jpg"}}]}
    response.raise_for_status.return_value = None
    with patch("app.providers.images.httpx.get", return_value=response) as request:
        results = PexelsImageProvider("not-a-real-key").find("新能源汽车")
    assert results[0].verified is False
    assert "Pexels" in results[0].source
    assert request.call_args.kwargs["headers"]["Authorization"] == "not-a-real-key"
