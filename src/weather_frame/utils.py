from weather_frame.config.icon_config import WEATHER_ICONS

def get_weather_icon(weather_code):
    """Get weather icon filename for a given weather code"""
    return WEATHER_ICONS.get(str(weather_code), "default.png")

# Dutch date names, indexed by datetime.weekday()/.month so we don't depend on a
# system locale (nl_NL is frequently absent on Raspberry Pi OS, and
# locale.setlocale is process-global and not thread-safe under Flask).
_DUTCH_WEEKDAYS = [
    "maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag",
]
_DUTCH_WEEKDAY_ABBR = ["MA", "DI", "WO", "DO", "VR", "ZA", "ZO"]
_DUTCH_MONTHS = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]

def format_dutch_date(dt):
    """Format a datetime as e.g. 'Woensdag 18 juni'."""
    weekday = _DUTCH_WEEKDAYS[dt.weekday()]
    month = _DUTCH_MONTHS[dt.month - 1]
    return f"{weekday} {dt.day} {month}".capitalize()

def dutch_weekday_abbr(dt):
    """Two-letter uppercase Dutch weekday, e.g. 'WO'."""
    return _DUTCH_WEEKDAY_ABBR[dt.weekday()]