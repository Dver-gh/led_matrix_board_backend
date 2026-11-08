from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from requests.exceptions import RequestException

from src.clients.spotify_client import SpotifyClient
from src.models.display_payload import SpotifyTrackPayload


def _make_response(status_code=200, json_data=None, content=b"{}"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def spotify_client(mocker):
    """SpotifyClient with credentials present and token exchange mocked (no network)."""
    mocker.patch.dict(
        "os.environ",
        {
            "SPOTIFY_CLIENT_ID": "id",
            "SPOTIFY_CLIENT_SECRET": "secret",
            "SPOTIFY_REFRESH_TOKEN": "refresh",
        },
    )
    mocker.patch(
        "src.clients.spotify_client.requests.post",
        return_value=_make_response(200, {"access_token": "tok", "expires_in": 3600}),
    )
    return SpotifyClient()


def test_get_now_playing_success(spotify_client, mocker):
    """A playing track is returned as a reshaped, sanitized payload with a progress percent."""
    playback = {
        "is_playing": True,
        "progress_ms": 177000,
        "item": {
            "name": "Bohemian Rhapsody!",
            "artists": [{"name": "Queen"}],
            "duration_ms": 354000,
        },
    }
    mocker.patch(
        "src.clients.spotify_client.requests.get",
        return_value=_make_response(200, playback, content=b"{...}"),
    )

    result = spotify_client.get_now_playing()

    assert isinstance(result, SpotifyTrackPayload)
    assert result.mode == "spotify"
    assert result.artist == "Queen"
    assert result.track_name == "Bohemian Rhapsody!"
    assert result.progress == 50  # 177000 / 354000


def test_get_now_playing_nothing_playing(spotify_client, mocker):
    """When nothing is actively playing, None is returned."""
    mocker.patch(
        "src.clients.spotify_client.requests.get",
        return_value=_make_response(200, {"is_playing": False}, content=b"{...}"),
    )

    assert spotify_client.get_now_playing() is None


def test_get_now_playing_no_active_device(spotify_client, mocker):
    """A 204 (no active device) with empty body returns None."""
    mocker.patch(
        "src.clients.spotify_client.requests.get",
        return_value=_make_response(204, None, content=b""),
    )

    assert spotify_client.get_now_playing() is None


def test_get_now_playing_request_error(spotify_client, mocker):
    """Network errors are swallowed and surfaced as None."""
    mocker.patch(
        "src.clients.spotify_client.requests.get",
        side_effect=RequestException("boom"),
    )

    assert spotify_client.get_now_playing() is None


def test_missing_credentials_returns_none(mocker):
    """With no credentials, the client cannot get a token and returns None."""
    mocker.patch.dict("os.environ", {}, clear=True)
    client = SpotifyClient()

    assert client.get_now_playing() is None


def test_payload_validation_failure():
    """Empty artist and unexpected fields are rejected by the model."""
    with pytest.raises(ValidationError):
        SpotifyTrackPayload(artist="", track_name="Valid Track", progress=10)

    with pytest.raises(ValidationError):
        SpotifyTrackPayload(
            artist="Queen",
            track_name="Song",
            progress=10,
            malicious_field="injection_attempt",
        )
