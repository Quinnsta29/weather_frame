from unittest.mock import MagicMock

import pytest

from weather_frame import main
from weather_frame.weather_service import WeatherService


@pytest.fixture
def processed_data(sample_weather_data):
    """Run the real processing pipeline (with geocoding stubbed) once."""
    svc = WeatherService()
    svc.get_location = MagicMock(return_value="Leiden")
    return svc.process_weather_data(sample_weather_data)


def test_dashboard_ok(client, monkeypatch, processed_data):
    """Happy path: cached data renders the dashboard with Dutch labels."""
    monkeypatch.setattr(main.weather_service, "cache", processed_data)

    resp = client.get("/")

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Leiden" in body
    # 2025-08-12 is a Tuesday -> daily.time replaced with abbrevs incl. "DI".
    assert "DI" in body
    # Formatted current date is Dutch (12 Aug 2025 = Tuesday -> Dinsdag).
    assert "Dinsdag" in body


def test_dashboard_unavailable(client, monkeypatch):
    """No data + failed fetch -> 503 unavailable page, no template crash."""
    monkeypatch.setattr(main.weather_service, "get_cached_data", lambda: {})
    monkeypatch.setattr(main.weather_service, "update_weather_data", lambda: False)

    resp = client.get("/")

    assert resp.status_code == 503
    assert "niet beschikbaar" in resp.get_data(as_text=True)


def test_refresh_returns_204(client, monkeypatch):
    """/refresh triggers an update (in a background thread) and returns 204."""
    from threading import Event
    done = Event()

    monkeypatch.setattr(main, "update_weather_and_display", done.set)

    resp = client.get("/refresh")

    assert resp.status_code == 204
    assert resp.get_data() == b""
    # Update runs asynchronously; it must fire shortly after the response.
    assert done.wait(timeout=2.0)


def test_status_ok_with_data(client, monkeypatch, processed_data):
    """With cached data, /status returns 200 and reports last_updated."""
    from datetime import datetime

    monkeypatch.setattr(main.weather_service, "cache", processed_data)
    monkeypatch.setattr(main, "NEXT_API_CALL_TIME", datetime(2025, 8, 12, 15, 0))

    resp = client.get("/status")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["has_data"] is True
    assert body["last_updated"] is not None
    assert body["next_api_call"] == "2025-08-12T15:00:00"


def test_status_no_data(client, monkeypatch):
    """With no cached data, /status reports no_data and 503 (frame up, no fetch yet)."""
    monkeypatch.setattr(main.weather_service, "cache", {})
    monkeypatch.setattr(main, "NEXT_API_CALL_TIME", None)

    resp = client.get("/status")

    assert resp.status_code == 503
    body = resp.get_json()
    assert body["status"] == "no_data"
    assert body["has_data"] is False
    assert body["last_updated"] is None
    assert body["next_api_call"] is None


def test_refresh_header_present_on_index(client, monkeypatch, processed_data):
    """The index response carries a Refresh header."""
    monkeypatch.setattr(main.weather_service, "cache", processed_data)

    resp = client.get("/")

    assert "Refresh" in resp.headers


def test_refresh_header_absent_on_other_paths(client):
    """Non-index responses (e.g. 404) must not get the Refresh header."""
    resp = client.get("/does-not-exist")

    assert resp.status_code == 404
    assert "Refresh" not in resp.headers
