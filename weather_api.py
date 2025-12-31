# weather_api.py
import requests

class WeatherClient:
    def __init__(self, api_key: str, location: str = "Ho Chi Minh"):
        self.api_key = api_key
        self.location = location

    def get_current(self):
        url = "https://api.weatherapi.com/v1/current.json"
        params = {"key": self.api_key, "q": self.location, "aqi": "no"}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return float(data["current"]["temp_c"]), float(data["current"]["humidity"]), float(data["current"]["uv"])
