import pytest
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.telegram_service import split_message, send_telegram_message, get_bot_info

client = TestClient(app)

def test_split_message_short():
    text = "Hello world"
    chunks = split_message(text, max_length=100)
    assert chunks == ["Hello world"]

def test_split_message_long():
    text = "Line 1\n" + ("A" * 50) + "\nLine 2\n" + ("B" * 50)
    chunks = split_message(text, max_length=60)
    assert len(chunks) >= 2
    assert "Line 1" in chunks[0]

@pytest.mark.anyio
async def test_send_telegram_message_missing_token(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 123456)
    
    result = await send_telegram_message("Test message")
    assert result is False

@pytest.mark.anyio
async def test_send_telegram_message_missing_chat_id(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", None)
    
    result = await send_telegram_message("Test message")
    assert result is False

@pytest.mark.anyio
async def test_send_telegram_message_mock_success(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 123456)

    class MockResponse:
        status_code = 200
        def json(self):
            return {"ok": True, "result": {"message_id": 1}}

    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, json=None):
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())

    result = await send_telegram_message("Test message")
    assert result is True

@pytest.mark.anyio
async def test_send_telegram_message_markdown_fallback(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 123456)

    calls = []

    class MockResponseFail:
        status_code = 400
        text = "Bad Request: can't parse entities"
        def json(self):
            return {"ok": False, "description": "Bad Request: can't parse entities"}

    class MockResponseSuccess:
        status_code = 200
        text = "OK"
        def json(self):
            return {"ok": True, "result": {"message_id": 2}}

    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, json=None):
            calls.append(json)
            if "parse_mode" in json:
                return MockResponseFail()
            return MockResponseSuccess()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())

    result = await send_telegram_message("Texte avec *markdown_invalide [")
    assert result is True
    assert len(calls) == 2
    assert "parse_mode" in calls[0]
    assert "parse_mode" not in calls[1]

def test_telegram_status_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
    
    response = client.get("/api/v1/telegram/status", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["bot_configured"] is False
