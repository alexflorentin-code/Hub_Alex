import pytest
import base64
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.gmail_service import extract_body_from_payload, EmailItem
from app.agents.email_agent import analyze_inbox, draft_email, InboxDigest, DraftProposal

client = TestClient(app)

def test_extract_body_from_payload_plain():
    raw_text = "Bonjour Alexandre, voici les infos demandées."
    encoded = base64.urlsafe_b64encode(raw_text.encode()).decode()
    payload = {
        "body": {"data": encoded}
    }
    extracted = extract_body_from_payload(payload)
    assert "Bonjour Alexandre" in extracted

@pytest.mark.anyio
async def test_analyze_inbox_mock(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    digest = await analyze_inbox()
    assert isinstance(digest, InboxDigest)
    assert digest.status == "success"
    assert digest.unread_count >= 1
    assert "Gmail" in digest.telegram_formatted_message

@pytest.mark.anyio
async def test_draft_email_mock(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    proposal = await draft_email("Réponds à Pierre pour lui dire ok pour lundi", recipient="pierre@example.com")
    assert isinstance(proposal, DraftProposal)
    assert proposal.to == "pierre@example.com"
    assert "Alexandre Florentin" in proposal.body

def test_emails_unread_endpoint_api(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "secret-key-123")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    response = client.get(
        "/api/v1/emails/unread",
        headers={"X-API-Key": "secret-key-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "unread_count" in data

def test_create_draft_endpoint_api(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "secret-key-123")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    response = client.post(
        "/api/v1/emails/draft",
        headers={"X-API-Key": "secret-key-123"},
        json={"instruction": "Dis à client@test.com que je valide le devis", "recipient": "client@test.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["to"] == "client@test.com"
    assert "body" in data

def test_telegram_webhook_emails_command(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 123456789)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    payload = {
        "update_id": 20,
        "message": {
            "from": {"id": 123456789, "first_name": "Alex"},
            "chat": {"id": 123456789},
            "text": "/emails"
        }
    }
    response = client.post("/api/v1/telegram/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_telegram_webhook_draft_command(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 123456789)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    payload = {
        "update_id": 21,
        "message": {
            "from": {"id": 123456789, "first_name": "Alex"},
            "chat": {"id": 123456789},
            "text": "/draft Rédige un mail de confirmation pour demain 10h"
        }
    }
    response = client.post("/api/v1/telegram/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_markdown_to_html_newsletter():
    from app.services.gmail_service import markdown_to_html_newsletter
    md = "# Titre Newsletter\n\n> Tendance de fond\n\n* [Article 1](https://example.com) — Description de l'article"
    html = markdown_to_html_newsletter(md, title="Test Newsletter")
    assert "<!DOCTYPE html>" in html
    assert "Titre Newsletter" in html
    assert "href='https://example.com'" in html
    assert "Hub_Alex" in html

def test_send_email_to_self_simulated(monkeypatch):
    from app.services.gmail_service import send_email_to_self
    monkeypatch.setattr(settings, "GMAIL_REFRESH_TOKEN", None)
    monkeypatch.setattr(settings, "ALLOWED_GOOGLE_EMAIL", "alex.florentin@gmail.com")

    res = send_email_to_self("Test Subject", "# Contenu Markdown")
    assert res["status"] == "simulated"
    assert res["to"] == "alex.florentin@gmail.com"

@pytest.mark.anyio
async def test_coordinator_newsletter_by_email_intent(monkeypatch):
    from app.agents.coordinator import run_coordinator
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "ALLOWED_GOOGLE_EMAIL", "alex.florentin@gmail.com")

    res = await run_coordinator("Envoie-moi la newsletter IA par mail s'il te plaît")
    assert res.status == "success"
    assert "alex.florentin@gmail.com" in res.detailed_response

