import logging
import os

import requests
from requests.exceptions import RequestException

from src.models.display_payload import WeatherPayload

logger = logging.getLogger(__name__)


class WeatherClient:
    """Fetches and validates weather data from the OpenWeather API."""

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.city = os.getenv("OPENWEATHER_CITY", "Wroclaw")
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    def get_current_weather(self) -> WeatherPayload | None:
        """
        Fetch current weather for the configured city as a validated payload, or None on error.

        Temperature is returned as a rounded integer; the board composes the ``°C`` suffix itself,
        so the degree symbol never travels over the wire.
        """
        if not self.api_key:
            logger.error("OpenWeather API key is missing in environment variables.")
            return None

        params = {"q": self.city, "appid": self.api_key, "units": "metric"}

        try:
            response = requests.get(self.base_url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()

            location = data.get("name", self.city)
            temp = round(data.get("main", {}).get("temp", 0.0))
            weather_list = data.get("weather", [{}])
            description = weather_list[0].get("description", "Unknown") if weather_list else "Unknown"

            return WeatherPayload(
                temp=int(temp),
                condition=str(description).capitalize(),
                location=str(location),
            )

        except requests.exceptions.Timeout:
            logger.error(f"Timeout occurred while fetching weather data for {self.city}.")
            return None
        except RequestException as e:
            logger.error(f"HTTP request error while fetching weather: {e}")
            return None
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Unexpected error while processing weather data: {e}")
            return None
