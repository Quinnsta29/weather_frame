import time
import atexit
from datetime import datetime, timedelta
from threading import Lock, Thread

from flask import Flask, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler

from weather_frame import logger
from weather_frame.display_service import DisplayService
from weather_frame.weather_service import WeatherService
from weather_frame.utils import get_weather_icon, format_dutch_date, dutch_weekday_abbr

app = Flask(__name__)

NEXT_API_CALL_TIME = None
NEXT_API_CALL_LOCK = Lock()

# Initialize services
weather_service = WeatherService()
display_service = DisplayService()

def update_weather_and_display():
    """Update weather data and display"""
    global NEXT_API_CALL_TIME
    with NEXT_API_CALL_LOCK:
        NEXT_API_CALL_TIME = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)

    # One line per update (~24/day) instead of a per-minute countdown heartbeat.
    logger.info(f"Weather update run; next scheduled at {NEXT_API_CALL_TIME:%H:%M}")

    if weather_service.update_weather_data():
        # Wait a bit for the web page to update with new data
        time.sleep(2)
        display_service.update_display_async()

@app.route("/")
def dashboard():
    # Use cached data if available, otherwise fetch it
    weather_data = weather_service.get_cached_data()
    if not weather_data:
        weather_service.update_weather_data()
        weather_data = weather_service.get_cached_data()

    # No data available (API unreachable on first load): render a fallback
    # instead of crashing the template on undefined variables.
    if not weather_data or 'current' not in weather_data:
        logger.warning("No weather data available, rendering unavailable page")
        return render_template("unavailable.html"), 503

    # Format Dutch date strings (locale-free; see weather_frame.utils).
    current_time = weather_data['current']['time_obj']
    weather_data['current']['formatted_date'] = format_dutch_date(current_time)

    if 'daily' in weather_data and 'time_objects' in weather_data['daily']:
        weather_data['daily']['time'] = [
            dutch_weekday_abbr(day_obj)
            for day_obj in weather_data['daily']['time_objects']
        ]

    return render_template("index.html", **weather_data)

@app.route("/refresh")
def refresh():
    """Manual refresh endpoint.

    Runs the update in a background thread so the HTTP response isn't blocked
    by the API fetch + the 2s settle sleep in update_weather_and_display.
    """
    Thread(target=update_weather_and_display).start()
    logger.info("Manual weather refresh triggered")
    return "", 204

@app.after_request
def add_refresh_header(response):
    """Add auto-refresh header to index page"""
    if request.path == "/":
        now = datetime.now()
        seconds_until_next_hour = 3600 - (now.minute * 60 + now.second)
        response.headers['Refresh'] = str(seconds_until_next_hour)
    return response

# Register template function
app.jinja_env.globals.update(
    get_weather_icon=get_weather_icon
)

# Scheduler is created lazily and only started when run as a program (see
# _start_scheduler). This keeps `import weather_frame.main` side-effect-free so
# the Flask app can be imported by the test suite without spawning live jobs.
scheduler = BackgroundScheduler()

def _start_scheduler():
    """Register jobs and start the background scheduler."""
    scheduler.add_job(func=update_weather_and_display, trigger="interval", hours=1)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    _start_scheduler()
    update_weather_and_display()  # Initial data fetch
    app.run(host='0.0.0.0', port=8080, debug=False)