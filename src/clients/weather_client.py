import os
import logging
import requests
from requests.exceptions import RequestException
from src.models.display_payload import WeatherPayload

logger = logging.getLogger(__name__)

class WeatherClient:
    """Client responsible for fetching and validating weather data from OpenWeather API."""

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.city = os.getenv("OPENWEATHER_CITY", "Warsaw")
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    def get_current_weather(self) -> WeatherPayload | None:
        """
        Fetches current weather data for the configured city, validates it,
        and sanitizes it using the Pydantic v2 WeatherPayload model.

        Returns:
            WeatherPayload | None: Validated weather data object or None if an error occurs.
        """
        if not self.api_key:
            logger.error("OpenWeather API key is missing in environment variables.")
            return None

        params = {
            "q": self.city,
            "appid": self.api_key,
            "units": "metric"
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=5.0)

            response.raise_for_status()
            data = response.json()

            city_name = data.get("name", self.city)
            main_data = data.get("main", {})
            weather_list = data.get("weather", [{}])

            temperature = main_data.get("temp", 0.0)
            humidity = main_data.get("humidity", 0)
            condition = weather_list[0].get("main", "Unknown") if weather_list else "Unknown"

            payload = WeatherPayload(
                city=city_name,
                temperature=float(temperature),
                condition=str(condition),
                humidity=int(humidity)
            )
            return payload

        except requests.exceptions.Timeout:
            logger.error(f"Timeout occurred while fetching weather data for {self.city}.")
            return None
        except RequestException as e:
            logger.error(f"HTTP request error while fetching weather: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while processing weather data: {e}")
            return None
