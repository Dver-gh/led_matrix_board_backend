from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from spotipy import SpotifyException

from src.clients.spotify_client import SpotifyClient
from src.models.display_payload import SpotifyTrackPayload


@pytest.fixture
def spotify_client(mocker):
    """
    Fixture configuring the Spotify client with mocked authorization (SpotifyOAuth),
    preventing it from attempting real network calls or opening a browser.
    """
    mocker.patch("src.clients.spotify_client.SpotifyOAuth")
    mocker.patch("src.clients.spotify_client.spotipy.Spotify")

    client = SpotifyClient()
    return client


def test_get_current_track_success(spotify_client, mocker):
    """Test successfully playing track: validation and data sanitization via Pydantic."""

    mock_playback_response = {
        "is_playing": True,
        "progress_ms": 15000,
        "item": {
            "name": "Bohemian Rhapsody!",
            "artists": [{"name": "Queen"}],
            "duration_ms": 354000
        }
    }

    spotify_client.sp.current_playback = MagicMock(return_value=mock_playback_response)

    result = spotify_client.get_current_track()

    assert result is not None
    assert isinstance(result, SpotifyTrackPayload)

    assert result.artist == "Queen"
    assert result.track_name == "Bohemian Rhapsody!"
    assert result.is_playing is True
    assert result.progress_ms == 15000
    assert result.duration_ms == 354000


def test_get_current_track_nothing_playing(spotify_client):
    """Test scenario when the user is not currently playing anything (returns None)."""
    spotify_client.sp.current_playback = MagicMock(return_value=None)

    result = spotify_client.get_current_track()
    assert result is None


def test_get_current_track_api_exception(spotify_client):
    """Test resilience against exceptions raised by the spotipy library."""
    spotify_client.sp.current_playback = MagicMock(side_effect=SpotifyException(401, -1, "Bad OAuth token"))

    result = spotify_client.get_current_track()
    assert result is None


def test_pydantic_payload_validation_failure():
    """Test forcing rejection of data that does not meet strict Pydantic v2 rules."""

    with pytest.raises(ValidationError):
        SpotifyTrackPayload(
            artist="",
            track_name="Valid Track",
            is_playing=True
        )

    with pytest.raises(ValidationError):
        SpotifyTrackPayload(
            artist="Queen",
            track_name="Song",
            is_playing=True,
            malicious_field="injection_attempt"
        )
