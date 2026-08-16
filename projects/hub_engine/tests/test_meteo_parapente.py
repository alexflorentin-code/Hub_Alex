import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.weather_service import compute_wind_cardinal, SPOTS, SYNOPTIC_POINTS
from app.agents.meteo_parapente import run_meteo_analysis, MeteoParapenteDigest, FlyabilityType
from app.agents.coordinator import run_coordinator

client = TestClient(app)

def test_compute_wind_cardinal():
    assert compute_wind_cardinal(0) == "N"
    assert compute_wind_cardinal(45) == "NE"
    assert compute_wind_cardinal(90) == "E"
    assert compute_wind_cardinal(180) == "S"
    assert compute_wind_cardinal(225) == "SW"
    assert compute_wind_cardinal(270) == "W"
    assert compute_wind_cardinal(360) == "N"

def test_spots_configuration():
    assert "val_d_illiez" in SPOTS
    assert SPOTS["val_d_illiez"]["is_primary"] is True
    assert "le_suchet" in SPOTS
    assert "vercorin" in SPOTS
    assert "sonchaux" in SPOTS

    assert "lugano" in SYNOPTIC_POINTS
    assert "zurich" in SYNOPTIC_POINTS

@pytest.mark.anyio
async def test_run_meteo_analysis_mock(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    digest = await run_meteo_analysis()
    assert isinstance(digest, MeteoParapenteDigest)
    assert digest.status == "success"
    assert digest.synoptic.regime_name != ""
    assert len(digest.weekly_flyability) == 7
    assert len(digest.best_days_ranking) >= 1
    assert digest.cross_comparison.has_cross_potential is True
    assert "Valais" in digest.cross_comparison.recommended_region or "Jura" in digest.cross_comparison.recommended_region
    assert any("Val d'Illiez" in f.spot_name for f in digest.detailed_forecasts)
    assert "bulletin météo" in digest.telegram_formatted_message.lower()
    assert "val d'illiez" in digest.telegram_formatted_message.lower()
    assert "cross" in digest.email_formatted_digest.lower()

def test_meteo_endpoint_api(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-meteo-key")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    response = client.post(
        "/api/v1/meteo/run?send_telegram=false&send_email=false",
        headers={"X-API-Key": "test-meteo-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "synoptic" in data
    assert "weekly_flyability" in data
    assert "cross_comparison" in data
    assert "telegram_formatted_message" in data

def test_telegram_webhook_meteo_commands(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_TELEGRAM_USER_ID", 11223344)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    for cmd in ["/meteo", "/cross", "/weekend"]:
        payload = {
            "update_id": 100,
            "message": {
                "from": {"id": 11223344, "first_name": "Alex"},
                "chat": {"id": 11223344},
                "text": cmd
            }
        }
        response = client.post("/api/v1/telegram/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

@pytest.mark.anyio
async def test_coordinator_routing_meteo(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    response = await run_coordinator("Est-ce qu'on peut voler ce week-end au Val d'Illiez ou faire du cross ?")
    assert response.status == "success"
    assert "Météo" in response.summary or "Vol Libre" in response.summary
    assert "Agent Météo Parapente" in response.action_taken
