import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_health_endpoint():
    """Vérifie que l'endpoint de santé fonctionne et renvoie un statut en ligne."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "database" in data
    assert "llm_configured" in data

def test_chat_endpoint_unauthorized():
    """Vérifie que l'accès au chat est refusé sans clé d'API valide."""
    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": "mauvaise-cle"},
        json={"message": "salut"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Clé d'API invalide."

def test_chat_endpoint_success_with_test_model(monkeypatch):
    """Vérifie le fonctionnement du chat en mode test (sans vrais appels LLM)."""
    # On force les clés LLM à None pour activer le TestModel (simulé) de PydanticAI
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    # On utilise la clé d'accès configurée pour le test
    monkeypatch.setattr(settings, "API_KEY", "test-key-123")

    response = client.post(
        "/api/v1/chat",
        headers={"X-API-Key": "test-key-123"},
        json={"message": "Test de message"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["status"] == "success"
    assert "Hub opérationnel en mode test" in data["summary"]
