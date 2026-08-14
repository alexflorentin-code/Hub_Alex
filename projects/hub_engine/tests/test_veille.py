import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.rss_service import clean_html, FeedItem, fetch_single_feed
from app.agents.veille import run_veille_analysis, VeilleDigest

client = TestClient(app)

def test_clean_html():
    raw_html = "<p>Découverte d'un <b>nouveau modèle</b> incroyable. <a href='https://example.com'>Lien</a></p>"
    cleaned = clean_html(raw_html)
    assert "nouveau modèle" in cleaned
    assert "<p>" not in cleaned
    assert "<b>" not in cleaned

@pytest.mark.anyio
async def test_fetch_single_feed_mock():
    mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test AI Blog</title>
            <item>
                <title>Lancement de SuperModel v1</title>
                <link>https://example.com/supermodel</link>
                <description>&lt;p&gt;Un modèle révolutionnaire.&lt;/p&gt;</description>
            </item>
        </channel>
    </rss>
    """
    mock_client = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_rss
    mock_client.get.return_value = mock_resp

    items = await fetch_single_feed(mock_client, "Test Source", "https://example.com/rss")
    assert len(items) == 1
    assert items[0].title == "Lancement de SuperModel v1"
    assert items[0].link == "https://example.com/supermodel"
    assert "révolutionnaire" in items[0].summary

@pytest.mark.anyio
async def test_run_veille_analysis_test_model(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    digest = await run_veille_analysis()
    assert isinstance(digest, VeilleDigest)
    assert digest.status == "success"
    assert len(digest.highlights) >= 1
    assert "Tendance" in digest.telegram_formatted_message
    assert "Newsletter" in digest.email_formatted_digest

def test_veille_endpoint_api(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "secret-key-123")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    response = client.post(
        "/api/v1/veille/run?send_telegram=false",
        headers={"X-API-Key": "secret-key-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "macro_trend" in data
    assert "telegram_formatted_message" in data
    assert "email_formatted_digest" in data

def test_telegram_webhook_news_ia_command(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 123456789)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    payload = {
        "update_id": 10,
        "message": {
            "from": {"id": 123456789, "first_name": "Alex"},
            "chat": {"id": 123456789},
            "text": "/news_ia"
        }
    }
    response = client.post("/api/v1/telegram/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
