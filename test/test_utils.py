from datetime import datetime

import pytest

from weather_frame.utils import (
    get_weather_icon,
    format_dutch_date,
    dutch_weekday_abbr,
)


class TestGetWeatherIcon:
    def test_known_code_str(self):
        assert get_weather_icon("0") == "clear.svg"

    def test_known_code_int(self):
        # Open-Meteo returns weathercode as an int; lookup must coerce to str.
        assert get_weather_icon(95) == "thunderstorm.svg"

    def test_unknown_code_returns_default(self):
        assert get_weather_icon(123456) == "default.png"


class TestFormatDutchDate:
    @pytest.mark.parametrize("dt, expected", [
        (datetime(2026, 6, 15), "Maandag 15 juni"),
        (datetime(2026, 6, 16), "Dinsdag 16 juni"),
        (datetime(2026, 6, 17), "Woensdag 17 juni"),
        (datetime(2026, 6, 18), "Donderdag 18 juni"),
        (datetime(2026, 6, 19), "Vrijdag 19 juni"),
        (datetime(2026, 6, 20), "Zaterdag 20 juni"),
        (datetime(2026, 6, 21), "Zondag 21 juni"),
        (datetime(2026, 1, 1), "Donderdag 1 januari"),
        (datetime(2026, 12, 31), "Donderdag 31 december"),
    ])
    def test_formatting(self, dt, expected):
        assert format_dutch_date(dt) == expected

    def test_capitalize_only_first_letter(self):
        # 'maandag' -> 'Maandag', month stays lowercase.
        assert format_dutch_date(datetime(2026, 6, 15)).startswith("Maandag ")
        assert "juni" in format_dutch_date(datetime(2026, 6, 15))


class TestDutchWeekdayAbbr:
    @pytest.mark.parametrize("dt, expected", [
        (datetime(2026, 6, 15), "MA"),
        (datetime(2026, 6, 16), "DI"),
        (datetime(2026, 6, 17), "WO"),
        (datetime(2026, 6, 18), "DO"),
        (datetime(2026, 6, 19), "VR"),
        (datetime(2026, 6, 20), "ZA"),
        (datetime(2026, 6, 21), "ZO"),
    ])
    def test_abbr(self, dt, expected):
        assert dutch_weekday_abbr(dt) == expected
