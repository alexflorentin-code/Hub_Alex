import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.rss_service import fetch_single_feed, load_sources_from_docs, DEFAULT_PARAPENTE_SOURCES
from app.agents.parapente import run_parapente_analysis, ParapenteDigest
from app.agents.coordinator import run_coordinator

client = TestClient(app)

@pytest.mark.anyio
async def test_fetch_parapente_feed_mock():
    mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>FSVL / SHV News</title>
            <item>
                <title>Espace Aérien Suisse : Nouveautés et Sécurité Thermique</title>
                <link>https://www.shv-fsvl.ch/news/airspace-2026</link>
                <description>&lt;p&gt;Consignes de sécurité pour le vol alpin et nouvelles zones protégées.&lt;/p&gt;</description>
            </item>
        </channel>
    </rss>
    """
    mock_client = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_rss
    mock_client.get.return_value = mock_resp

    items = await fetch_single_feed(mock_client, "FSVL / SHV", "https://www.shv-fsvl.ch/rss.xml")
    assert len(items) == 1
    assert items[0].title == "Espace Aérien Suisse : Nouveautés et Sécurité Thermique"
    assert items[0].link == "https://www.shv-fsvl.ch/news/airspace-2026"
    assert "Sécurité" in items[0].summary or "Consignes" in items[0].summary

def test_load_parapente_sources_from_docs():
    sources = load_sources_from_docs("parapente_sources.md", DEFAULT_PARAPENTE_SOURCES)
    assert len(sources) >= 3
    source_names = [s[0] for s in sources]
    assert any("FSVL" in name or "SHV" in name for name in source_names)
    assert any("Rock the Outdoor" in name or "Cross Country" in name or "DHV" in name for name in source_names)

@pytest.mark.anyio
async def test_run_parapente_analysis_test_model(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    digest = await run_parapente_analysis()
    assert isinstance(digest, ParapenteDigest)
    assert digest.status == "success"
    assert len(digest.highlights) >= 2
    assert "Tendance" in digest.telegram_formatted_message or "Veille" in digest.telegram_formatted_message
    assert "Newsletter" in digest.email_formatted_digest
    assert "FSVL" in digest.email_formatted_digest or "FSVL" in digest.telegram_formatted_message
    assert "Sécurité" in digest.email_formatted_digest or "Sécurité" in digest.telegram_formatted_message

def test_parapente_endpoint_api(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-secret-parapente")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    response = client.post(
        "/api/v1/parapente/run?send_telegram=false",
        headers={"X-API-Key": "test-secret-parapente"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "macro_trend" in data
    assert "telegram_formatted_message" in data
    assert "email_formatted_digest" in data

def test_telegram_webhook_parapente_command(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 999888777)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    payload = {
        "update_id": 42,
        "message": {
            "from": {"id": 999888777, "first_name": "Alex"},
            "chat": {"id": 999888777},
            "text": "/news_parapente"
        }
    }
    response = client.post("/api/v1/telegram/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.anyio
async def test_coordinator_routing_parapente(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    response = await run_coordinator("Quelles sont les dernières actualités parapente et à la FSVL ?")
    assert response.status == "success"
    assert "Parapente" in response.summary or "FSVL" in response.summary
    assert "Agent Parapente" in response.action_taken
