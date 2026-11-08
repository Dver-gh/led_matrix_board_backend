import logging
import os
import time

from dotenv import load_dotenv

from src.clients.spotify_client import SpotifyClient
from src.clients.weather_client import WeatherClient
from src.services.mqtt_publisher import MqttPublisher

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("led_backend")

WEATHER_INTERVAL = 900      # seconds between weather refreshes while idle
SPOTIFY_POLL_INTERVAL = 2   # seconds between Spotify polls while playing
IDLE_SLEEP = 5              # seconds between loops while no music is playing


def main():
    spotify = SpotifyClient()
    weather = WeatherClient()
    publisher = MqttPublisher()
    publisher.connect()

    fallback_city = os.getenv("OPENWEATHER_CITY", "Wroclaw")

    logger.info("LED Matrix Board system started. Default mode: WEATHER.")
    current_mode = "weather"
    last_weather_check = 0.0

    while True:
        now = time.time()
        track = spotify.get_now_playing()

        if track is not None:
            if current_mode != "spotify":
                logger.info("Music playback detected -> switching to SPOTIFY mode.")
                current_mode = "spotify"

            publisher.publish(track)
            time.sleep(SPOTIFY_POLL_INTERVAL)
            continue

        # Nothing playing -> weather mode.
        if current_mode != "weather" or (now - last_weather_check >= WEATHER_INTERVAL):
            if current_mode != "weather":
                logger.info("No active music playback -> switching to WEATHER mode.")
                current_mode = "weather"

            logger.info("Fetching current weather data...")
            payload = weather.get_current_weather()
            if payload is not None:
                publisher.publish(payload)
            else:
                # Keep temp absent so the board shows "--" instead of a stale value.
                publisher.publish(
                    {"mode": "weather", "condition": "Unavailable", "location": fallback_city}
                )
            last_weather_check = now

        time.sleep(IDLE_SLEEP)


if __name__ == "__main__":
    main()
