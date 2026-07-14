"""
Unit-тесты для CVCCClassifier.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.external.cvc_classifier import CVCCClassifier

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_health_check_cached_within_ttl():
    classifier = CVCCClassifier("http://cvc.test", timeout=1.0, health_cache_ttl=60.0)
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch.object(classifier._http_client, "get", AsyncMock(return_value=mock_response)) as mock_get:
        assert await classifier.is_available() is True
        assert await classifier.is_available() is True
        mock_get.assert_called_once()

    await classifier.aclose()


@pytest.mark.asyncio
async def test_classify_uses_async_post():
    classifier = CVCCClassifier("http://cvc.test", timeout=1.0, health_cache_ttl=60.0)

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"command": "give_paw", "confidence": 0.9}

    with patch.object(
        classifier._http_client,
        "post",
        AsyncMock(return_value=FakeResponse()),
    ) as mock_post:
        result = await classifier.classify("лапу")
        assert result == {"function": "give_paw", "confidence": 0.9}
        mock_post.assert_called_once()

    await classifier.aclose()
