import os

# Force debug mode BEFORE any weather_frame import so the e-ink hardware path
# (the `inky` import in display_service) is gated off during tests.
os.environ["DEBUG_MODE"] = "1"

import pytest

from weather_frame.weather_service import WeatherService


@pytest.fixture
def weather_service():
    """Return a fresh WeatherService instance for testing."""
    return WeatherService()


@pytest.fixture
def sample_weather_data():
    """Return sample raw Open-Meteo weather data for testing."""
    return {
        "latitude": 52.16,
        "longitude": 4.49,
        "current": {
            "time": "2025-08-12T14:00",
            "temperature_2m": 21.5,
            "weathercode": 1,
        },
        "hourly": {
            "time": [
                "2025-08-12T00:00", "2025-08-12T01:00", "2025-08-12T02:00",
                "2025-08-12T03:00", "2025-08-12T04:00", "2025-08-12T05:00",
                "2025-08-12T06:00", "2025-08-12T07:00", "2025-08-12T08:00",
                "2025-08-12T09:00", "2025-08-12T10:00", "2025-08-12T11:00",
                "2025-08-12T12:00", "2025-08-12T13:00", "2025-08-12T14:00",
                "2025-08-12T15:00",
            ],
            "temperature_2m": [
                18.0, 17.5, 17.0, 16.5, 16.0, 16.5,
                17.0, 18.0, 19.0, 20.0, 21.0, 21.5,
                22.0, 22.0, 21.5, 21.0,
            ],
            "weathercode": [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1],
            "rain": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        },
        "daily": {
            "time": [
                "2025-08-12", "2025-08-13", "2025-08-14",
                "2025-08-15", "2025-08-16", "2025-08-17", "2025-08-18",
            ],
            "temperature_2m_max": [22.0, 23.5, 24.0, 21.0, 20.5, 22.0, 23.0],
            "temperature_2m_min": [16.0, 17.0, 18.0, 15.0, 14.5, 16.0, 17.0],
            "weathercode": [1, 1, 2, 3, 80, 1, 0],
        },
    }


@pytest.fixture
def client():
    """Flask test client with a side-effect-free app import."""
    from weather_frame.main import app
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
