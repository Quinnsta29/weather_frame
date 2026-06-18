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
