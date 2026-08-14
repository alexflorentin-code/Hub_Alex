import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_health_endpoint():
    """Vérifie l'endpoint de santé pour Cloud Monitoring."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "llm_configured" in data
    assert "telegram_configured" in data

def test_basic_auth_required_on_index():
    """Vérifie que l'accès à la page racine '/' est protégé par HTTP Basic Auth."""
    response = client.get("/")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers

def test_basic_auth_success_on_index(monkeypatch):
    """Vérifie que l'accès à '/' est autorisé avec les bons identifiants Basic Auth."""
    monkeypatch.setattr(settings, "BASIC_AUTH_USERNAME", "alex")
    monkeypatch.setattr(settings, "API_KEY", "secret-test-pass")

    response = client.get("/", auth=("alex", "secret-test-pass"))
    assert response.status_code == 200

def test_chat_endpoint_unauthorized():
    """Vérifie que l'accès au chat API est refusé sans clé X-API-Key."""
    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": "mauvaise-cle"},
        json={"message": "salut"}
    )
    assert response.status_code == 401

def test_chat_endpoint_success_with_test_model(monkeypatch):
    """Vérifie le fonctionnement du chat en mode test."""
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "API_KEY", "test-key-123")

    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": "test-key-123"},
        json={"message": "Test de message"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Hub opérationnel en mode test" in data["summary"]

def test_telegram_webhook_unauthorized_user(monkeypatch):
    """Vérifie que le bot Telegram ignore les utilisateurs non autorisés."""
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 123456789)

    # Message provenant d'un ID inconnu (999999999)
    payload = {
        "update_id": 1,
        "message": {
            "from": {"id": 999999999, "first_name": "Hacker"},
            "chat": {"id": 999999999},
            "text": "Hello bot"
        }
    }
    response = client.post("/api/v1/telegram/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "unauthorized"

def test_telegram_webhook_authorized_user(monkeypatch):
    """Vérifie que le bot répond à l'utilisateur autorisé."""
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 123456789)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    payload = {
        "update_id": 2,
        "message": {
            "from": {"id": 123456789, "first_name": "Alex"},
            "chat": {"id": 123456789},
            "text": "/start"
        }
    }
    response = client.post("/api/v1/telegram/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_briefing_endpoint(monkeypatch):
    """Vérifie le déclenchement du briefing matinal (Cloud Scheduler)."""
    monkeypatch.setattr(settings, "API_KEY", "cron-secret")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    response = client.post("/api/v1/briefing", headers={"X-API-Key": "cron-secret"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "briefing" in data
