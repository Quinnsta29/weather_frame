from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from weather_frame.weather_service import DEFAULT_LOCATION
from weather_frame.config.api_config import API_URL, PARAMS

# Fixtures `weather_service` and `sample_weather_data` come from conftest.py.


@patch('weather_frame.weather_service.requests.get')
def test_fetch_weather(mock_get, weather_service, sample_weather_data):
    """Test fetching weather data from API."""
    mock_response = MagicMock()
    mock_response.json.return_value = sample_weather_data
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = weather_service.fetch_weather()

    assert result == sample_weather_data
    mock_get.assert_called_once_with(API_URL, params=PARAMS, timeout=10)


@patch('weather_frame.weather_service.Nominatim')
def test_get_location_city(mock_nominatim, weather_service):
    """Test getting location when city is available."""
    mock_geolocator = MagicMock()
    mock_location = MagicMock()
    mock_location.raw = {'address': {'city': 'Leiden'}}
    mock_geolocator.reverse.return_value = mock_location
    mock_nominatim.return_value = mock_geolocator

    result = weather_service.get_location(52.16, 4.49)

    assert result == 'Leiden'
    mock_nominatim.assert_called_once_with(user_agent="weather-frame", timeout=10)
    mock_geolocator.reverse.assert_called_once_with("52.16, 4.49", language='nl')


@patch('weather_frame.weather_service.Nominatim')
def test_get_location_town(mock_nominatim, weather_service):
    """Test getting location when town is available but not city."""
    mock_geolocator = MagicMock()
    mock_location = MagicMock()
    mock_location.raw = {'address': {'town': 'Oegstgeest'}}
    mock_geolocator.reverse.return_value = mock_location
    mock_nominatim.return_value = mock_geolocator

    result = weather_service.get_location(52.18, 4.46)

    assert result == 'Oegstgeest'


@patch('weather_frame.weather_service.Nominatim')
def test_get_location_village(mock_nominatim, weather_service):
    """Test getting location when only village is available."""
    mock_geolocator = MagicMock()
    mock_location = MagicMock()
    mock_location.raw = {'address': {'village': 'Warmond'}}
    mock_geolocator.reverse.return_value = mock_location
    mock_nominatim.return_value = mock_geolocator

    result = weather_service.get_location(52.20, 4.49)

    assert result == 'Warmond'


@patch('weather_frame.weather_service.Nominatim')
def test_get_location_address_fallback(mock_nominatim, weather_service):
    """Test fallback to first component of address when no place key matches."""
    mock_geolocator = MagicMock()
    mock_location = MagicMock()
    mock_location.raw = {'address': {'suburb': 'Somewhere'}}
    mock_location.address = "Hoofdstraat 1, Somewhere, Nederland"
    mock_geolocator.reverse.return_value = mock_location
    mock_nominatim.return_value = mock_geolocator

    result = weather_service.get_location(52.0, 4.0)

    assert result == 'Hoofdstraat 1'


@patch('weather_frame.weather_service.Nominatim')
def test_get_location_none_returns_default(mock_nominatim, weather_service):
    """Test that a None geocoder result falls back to the default location."""
    mock_geolocator = MagicMock()
    mock_geolocator.reverse.return_value = None
    mock_nominatim.return_value = mock_geolocator

    result = weather_service.get_location(0.0, 0.0)

    assert result == DEFAULT_LOCATION


@patch('weather_frame.weather_service.Nominatim')
def test_get_location_exception(mock_nominatim, weather_service):
    """Test getting location when an exception occurs."""
    mock_geolocator = MagicMock()
    mock_geolocator.reverse.side_effect = Exception("API Error")
    mock_nominatim.return_value = mock_geolocator

    result = weather_service.get_location(52.16, 4.49)

    assert result == DEFAULT_LOCATION


@patch('weather_frame.weather_service.Nominatim')
def test_get_location_is_cached(mock_nominatim, weather_service):
    """Same coordinates must hit Nominatim only once (usage-policy friendly)."""
    mock_geolocator = MagicMock()
    mock_location = MagicMock()
    mock_location.raw = {'address': {'city': 'Leiden'}}
    mock_geolocator.reverse.return_value = mock_location
    mock_nominatim.return_value = mock_geolocator

    first = weather_service.get_location(52.16, 4.49)
    second = weather_service.get_location(52.16, 4.49)

    assert first == second == 'Leiden'
    mock_nominatim.assert_called_once()
    mock_geolocator.reverse.assert_called_once()


def test_process_weather_data(weather_service, sample_weather_data):
    """Test processing weather data."""
    weather_service.get_location = MagicMock(return_value="Leiden")

    result = weather_service.process_weather_data(sample_weather_data)

    assert 'current' in result
    assert 'hourly' in result
    assert 'daily' in result
    assert 'location' in result
    assert 'last_updated' in result

    assert result['current']['time_obj'] == datetime.fromisoformat("2025-08-12T14:00")
    assert result['current_hour_index'] == 14
    assert len(result['daily']['time_objects']) == 7
    assert result['daily']['time_objects'][0] == datetime.fromisoformat("2025-08-12")


def test_process_weather_data_hour_not_found(weather_service, sample_weather_data):
    """When current hour isn't in the hourly series, index defaults to 0."""
    weather_service.get_location = MagicMock(return_value="Leiden")
    # Move 'current' to a time absent from the hourly list.
    sample_weather_data['current']['time'] = "2025-08-12T23:00"

    result = weather_service.process_weather_data(sample_weather_data)

    assert result['current_hour_index'] == 0


def test_process_weather_data_missing_key_raises(weather_service):
    """A malformed payload must raise (caught upstream by update_weather_data)."""
    with pytest.raises(KeyError):
        weather_service.process_weather_data({"current": {"time": "2025-08-12T14:00"}})


@patch('weather_frame.weather_service.WeatherService.fetch_weather')
@patch('weather_frame.weather_service.WeatherService.process_weather_data')
def test_update_weather_data_success(mock_process, mock_fetch, weather_service, sample_weather_data):
    """Test updating weather data cache - successful case."""
    mock_fetch.return_value = sample_weather_data
    processed_data = {'processed': True, 'data': sample_weather_data}
    mock_process.return_value = processed_data

    result = weather_service.update_weather_data()

    assert result is True
    mock_fetch.assert_called_once()
    mock_process.assert_called_once_with(sample_weather_data)
    assert weather_service.cache == processed_data


@patch('weather_frame.weather_service.WeatherService.fetch_weather')
def test_update_weather_data_failure(mock_fetch, weather_service):
    """Test updating weather data cache - failure case (fetch raises)."""
    mock_fetch.side_effect = Exception("API Error")

    result = weather_service.update_weather_data()

    assert result is False
    mock_fetch.assert_called_once()
    assert weather_service.cache == {}


@patch('weather_frame.weather_service.WeatherService.fetch_weather')
def test_update_weather_data_malformed_payload(mock_fetch, weather_service):
    """A malformed payload propagates as a handled failure, cache untouched."""
    mock_fetch.return_value = {}  # missing all expected keys

    result = weather_service.update_weather_data()

    assert result is False
    assert weather_service.cache == {}


def test_get_cached_data(weather_service):
    """Test getting cached weather data."""
    test_data = {'test': 'data'}
    weather_service.cache = test_data

    result = weather_service.get_cached_data()

    assert result == test_data
    assert result is weather_service.cache
