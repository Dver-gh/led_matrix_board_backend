import base64
import logging
import os
import time

import requests
from requests.exceptions import RequestException

from src.models.display_payload import SpotifyTrackPayload

logger = logging.getLogger(__name__)

TOKEN_URL = "https://accounts.spotify.com/api/token"
PLAYER_URL = "https://api.spotify.com/v1/me/player"
# Refresh a little before the token actually expires to avoid edge-of-expiry 401s.
TOKEN_EXPIRY_BUFFER_S = 60


class SpotifyClient:
    """
    Fetches current Spotify playback state.

    Auth is a headless refresh-token exchange (no SpotifyOAuth / browser / cache file),
    which is safe to run inside a container. The short-lived access token is cached in
    memory and only re-requested when it expires.
    """

    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    def _get_access_token(self) -> str | None:
        """Return a valid access token, refreshing via the refresh-token grant if needed."""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        if not (self.client_id and self.client_secret and self.refresh_token):
            logger.error("Spotify credentials are missing in environment variables.")
            return None

        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}

        try:
            response = requests.post(TOKEN_URL, headers=headers, data=data, timeout=5.0)
            response.raise_for_status()
            body = response.json()
            self._access_token = body.get("access_token")
            self._token_expires_at = time.time() + body.get("expires_in", 3600) - TOKEN_EXPIRY_BUFFER_S
            return self._access_token
        except RequestException as e:
            logger.error(f"Error refreshing Spotify token: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid token response from Spotify: {e}")
            return None

    def get_now_playing(self) -> SpotifyTrackPayload | None:
        """
        Return the currently playing track as a validated payload, or None when nothing
        is actively playing (or on any error).
        """
        token = self._get_access_token()
        if not token:
            return None

        try:
            response = requests.get(
                PLAYER_URL,
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )

            # 204 (no active device) or empty body → nothing playing.
            if response.status_code == 204 or not response.content:
                return None
            response.raise_for_status()

            data = response.json()
            if not data or not data.get("is_playing"):
                return None

            item = data.get("item") or {}
            artists = [a["name"] for a in item.get("artists", []) if a.get("name")]
            artist_str = ", ".join(artists) if artists else "Unknown artist"

            progress_ms = data.get("progress_ms", 0) or 0
            duration_ms = item.get("duration_ms", 0) or 0
            progress = int(progress_ms / duration_ms * 100) if duration_ms > 0 else 0
            progress = max(0, min(100, progress))

            return SpotifyTrackPayload(
                artist=artist_str,
                track_name=item.get("name") or "Unknown track",
                progress=progress,
            )

        except RequestException as e:
            logger.error(f"Error fetching Spotify playback: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid playback response from Spotify: {e}")
            return None
