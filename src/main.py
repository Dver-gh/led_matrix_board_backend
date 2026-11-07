import base64
import json
import os
import time

import paho.mqtt.client as mqtt
import requests
from dotenv import load_dotenv

load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_DISPLAY = "home/led/display/state"

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHER_CITY = os.getenv("WEATHER_CITY", "Wroclaw")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

def fetch_weather_data():
    """Fetch live weather data from OpenWeatherMap API."""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={WEATHER_CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            temp = f"{round(data['main']['temp'])}°C"
            condition = data['weather'][0]['description'].capitalize()
            return {
                "mode": "weather",
                "temp": temp,
                "condition": condition,
                "location": WEATHER_CITY
            }
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error fetching weather data: {e}")

    return {
        "mode": "weather",
        "temp": "N/A",
        "condition": "Unavailable",
        "location": WEATHER_CITY
    }

def get_spotify_access_token():
    """Exchange refresh token for a fresh Spotify access token."""
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": SPOTIFY_REFRESH_TOKEN
    }

    try:
        response = requests.post(url, headers=headers, data=data, timeout=5)
        if response.status_code == 200:
            return response.json().get("access_token")
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error refreshing Spotify token: {e}")

    return None

def fetch_spotify_playback():
    """Fetch current live playback state from Spotify API."""
    token = get_spotify_access_token()
    if not token:
        return None

    url = "https://api.spotify.com/v1/me/player"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200 and response.content:
            data = response.json()
            if data and data.get("is_playing"):
                item = data.get("item", {})
                images = item.get("album", {}).get("images", [])
                album_art_url = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else "")

                return {
                    "is_playing": True,
                    "track_name": item.get("name"),
                    "artist": ", ".join([artist["name"] for artist in item.get("artists", [])]),
                    "progress_ms": data.get("progress_ms", 0),
                    "duration_ms": item.get("duration_ms", 0),
                    "album_art_url": album_art_url
                }
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error fetching Spotify playback: {e}")

    return {"is_playing": False}

def generate_ascii_bar(progress_ms, duration_ms, bar_length=20):
    """Generate an ASCII progress bar string based on playback progress."""
    if not duration_ms or duration_ms <= 0:
        return "--------------------"
    progress_pct = min(max(progress_ms / duration_ms, 0.0), 1.0)
    filled_length = int(bar_length * progress_pct)
    return "█" * filled_length + "-" * (bar_length - filled_length)

def main():
    print("LED Matrix Board system started. Default mode: WEATHER.")

    current_mode = "weather"
    last_weather_check = 0
    WEATHER_INTERVAL = 900
    SPOTIFY_POLL_INTERVAL = 2

    while True:
        current_time = time.time()

        spotify_data = fetch_spotify_playback()

        if spotify_data and spotify_data.get("is_playing"):
            if current_mode != "spotify":
                print("Music playback detected -> Switching to SPOTIFY mode.")
                current_mode = "spotify"

            track_name = spotify_data.get("track_name")
            artist = spotify_data.get("artist")
            progress_ms = spotify_data.get("progress_ms", 0)
            duration_ms = spotify_data.get("duration_ms", 1)

            ascii_bar = generate_ascii_bar(progress_ms, duration_ms)

            payload = {
                "mode": "spotify",
                "artist": artist,
                "track_name": track_name,
                "progress_bar": ascii_bar,
                "progress_ms": progress_ms,
                "duration_ms": duration_ms
            }

            client.publish(TOPIC_DISPLAY, json.dumps(payload))
            time.sleep(SPOTIFY_POLL_INTERVAL)

        else:
            if current_mode != "weather" or (current_time - last_weather_check >= WEATHER_INTERVAL):
                if current_mode != "weather":
                    print("No active music playback -> Switching to WEATHER mode.")
                    current_mode = "weather"

                print("Fetching current weather data...")
                weather_payload = fetch_weather_data()

                client.publish(TOPIC_DISPLAY, json.dumps(weather_payload))
                last_weather_check = current_time

            time.sleep(5)

if __name__ == "__main__":
    main()
