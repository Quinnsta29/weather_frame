import requests
from datetime import datetime
from geopy.geocoders import Nominatim

from weather_frame import logger
from weather_frame.config.api_config import API_URL, PARAMS

DEFAULT_LOCATION = "Leiden"

class WeatherService:
    def __init__(self):
        self.cache = {}
        # Reverse-geocoding cache: coordinates are effectively static, so we hit
        # Nominatim at most once per (lat, long) instead of every hourly update
        # (their usage policy forbids heavy automated querying).
        self._location_cache = {}

    def fetch_weather(self, api_url=API_URL, params=PARAMS):
        """Fetch weather data from API"""
        r = requests.get(api_url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_location(self, lat, long):
        """Get location name from coordinates, cached per coordinate pair."""
        key = (round(lat, 4), round(long, 4))
        if key in self._location_cache:
            return self._location_cache[key]

        location_name = DEFAULT_LOCATION
        try:
            geolocator = Nominatim(user_agent="weather-frame", timeout=10)
            location = geolocator.reverse(f"{lat}, {long}", language='nl')

            if location:
                address = location.raw['address']
                if 'city' in address:
                    location_name = address['city']
                elif 'town' in address:
                    location_name = address['town']
                elif 'village' in address:
                    location_name = address['village']
                else:
                    location_name = location.address.split(',')[0]
        except Exception as e:
            logger.error(f"Error getting location: {e}")

        self._location_cache[key] = location_name
        return location_name
    
    def process_weather_data(self, data):
        """Process and format weather data"""
        current = data['current']
        current_time = datetime.fromisoformat(current['time'])
        current['time_obj'] = current_time
        
        hourly = data['hourly']
        current_hour_index = 0

        for i, time_str in enumerate(hourly['time']):
            hourly_time = datetime.fromisoformat(time_str)
            if hourly_time.hour == current_time.hour and hourly_time.date() == current_time.date():
                current_hour_index = i
                break
        
        daily = data['daily']
        daily_times = []
        for i, day in enumerate(daily['time']):
            daily_time = datetime.fromisoformat(day)
            daily_times.append(daily_time)

        daily['time_objects'] = daily_times

        location = self.get_location(data['latitude'], data['longitude'])
        
        return {
            'current': current,
            'hourly': hourly,
            'current_hour_index': current_hour_index,
            'daily': daily,
            'location': location,
            'last_updated': datetime.now()
        }
    
    def update_weather_data(self):
        """Update weather data cache"""
        logger.info(f"Updating weather data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            data = self.fetch_weather()
            self.cache = self.process_weather_data(data)
            return True
        except Exception as e:
            logger.error(f"Error updating weather data: {e}")
            return False
    
    def get_cached_data(self):
        """Get cached weather data"""
        return self.cache