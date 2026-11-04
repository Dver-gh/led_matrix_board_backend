import logging
import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from src.models.display_payload import SpotifyTrackPayload

logger = logging.getLogger(__name__)

class SpotifyClient:
    def __init__(self):
        self.auth_manager = SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8080"),
            scope="user-read-currently-playing user-read-playback-state",
            cache_path=".cache-spotify",
            open_browser=False
        )
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)

    def get_current_track(self) -> SpotifyTrackPayload | None:
        """
        Downloads currently playing track from Spotify.
	Validates and sanitises it using Pydantic v2.
        """
        try:
            current = self.sp.current_playback()

            if not current or not current.get("item"):
                logger.info("No active tracks on Spotify.")
                return None

            item = current["item"]
            is_playing = current.get("is_playing", False)

            artists = [artist["name"] for artist in item.get("artists", [])]
            artist_str = ", ".join(artists) if artists else "Unknown artist"
            track_name = item.get("name", "Unknown track")

            progress_ms = current.get("progress_ms", 0)
            duration_ms = item.get("duration_ms", 0)

            payload = SpotifyTrackPayload(
                artist=artist_str,
                track_name=track_name,
                is_playing=is_playing,
                progress_ms=progress_ms,
                duration_ms=duration_ms
            )
            return payload

        except spotipy.SpotifyException as e:
            logger.error(f"Spotify API error: {e}")
            return None
        except Exception as e: # noqa: BLE001
            logger.error(f"Unexpected error while fetching track data from Spotify: {e}")
            return None
