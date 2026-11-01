from unittest.mock import MagicMock

import pytest

from api import app as api_module


TEST_API_KEY = "unit-test-key"


@pytest.fixture
def client(monkeypatch):
    api_module.app.config["TESTING"] = True
    monkeypatch.setattr(api_module, "API_KEY", TEST_API_KEY)

    with api_module.app.test_client() as test_client:
        yield test_client


def valid_measurement():
    return {
        "timestamp": "2026-11-01T11:21:39",
        "hostname": "MON01",
        "ip_address": "10.10.50.20",
        "metric": "cpu",
        "value": 42.5,
        "unit": "%"
    }


def mock_database_connection():
    connection = MagicMock()
    cursor = MagicMock()

    connection.cursor.return_value = cursor
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False

    return connection


def test_health_endpoint_returns_200(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_valid_measurement_returns_201(client, monkeypatch):
    connection = mock_database_connection()

    monkeypatch.setattr(
        api_module,
        "get_database_connection",
        lambda: connection
    )

    response = client.post(
        "/api/v1/measurements",
        headers={"X-API-Key": TEST_API_KEY},
        json=valid_measurement()
    )

    assert response.status_code == 201
    assert response.get_json()["message"] == "Measurement stored"
    connection.cursor.return_value.execute.assert_called_once()
    connection.commit.assert_called_once()


def test_missing_field_returns_400(client):
    payload = valid_measurement()
    del payload["hostname"]

    response = client.post(
        "/api/v1/measurements",
        headers={"X-API-Key": TEST_API_KEY},
        json=payload
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Missing required fields"


def test_unsupported_metric_returns_400(client):
    payload = valid_measurement()
    payload["metric"] = "temperature"

    response = client.post(
        "/api/v1/measurements",
        headers={"X-API-Key": TEST_API_KEY},
        json=payload
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Unsupported metric"


def test_invalid_api_key_returns_401(client):
    response = client.post(
        "/api/v1/measurements",
        headers={"X-API-Key": "wrong-key"},
        json=valid_measurement()
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_database_error_returns_500_without_secrets(client, monkeypatch):
    def broken_database_connection():
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(
        api_module,
        "get_database_connection",
        broken_database_connection
    )

    response = client.post(
        "/api/v1/measurements",
        headers={"X-API-Key": TEST_API_KEY},
        json=valid_measurement()
    )

    body = response.get_json()

    assert response.status_code == 500
    assert body["error"] == "Database error"

    response_text = response.get_data(as_text=True).lower()

    assert "password" not in response_text
    assert "api_key" not in response_text
    assert "unit-test-key" not in response_text
