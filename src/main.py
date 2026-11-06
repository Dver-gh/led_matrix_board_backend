import logging
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from src.clients.spotify_client import SpotifyClient
from src.clients.weather_client import WeatherClient
from src.services.mqtt_publisher import MqttPublisher

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting LED Matrix Backend Service...")

    spotify = SpotifyClient()
    weather = WeatherClient()
    mqtt_pub = MqttPublisher()

    mqtt_pub.connect()

    try:
        while True:
            logger.info("Fetching data from external APIs...")

            weather_data = weather.get_current_weather()
            if weather_data:
                mqtt_pub.publish(weather_data, sub_topic="weather")
                logger.info(f"Published weather for: {weather_data.city}, {weather_data.temperature}°C")

            spotify_data = spotify.get_current_track()
            if spotify_data:
                mqtt_pub.publish(spotify_data, sub_topic="spotify")
                logger.info(f"Published track: {spotify_data.artist} - {spotify_data.track_name}")
            else:
                logger.info("No active Spotify playback or user offline.")

            time.sleep(15)

    except KeyboardInterrupt:
        logger.info("Shutting down service gracefully...")
    finally:
        mqtt_pub.disconnect()

if __name__ == "__main__":
    main()
