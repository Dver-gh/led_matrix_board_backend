import pytest
from pydantic import ValidationError

from src.models.display_payload import SpotifyTrackPayload, WeatherPayload


def test_renderable_symbols_are_preserved():
    """°, ¥, $ and accents survive sanitization (the firmware maps them to font glyphs)."""
    track = SpotifyTrackPayload(artist="¥$, Beyoncé", track_name="Déjà Vu", progress=0)
    assert track.artist == "¥$, Beyoncé"
    assert track.track_name == "Déjà Vu"

    weather = WeatherPayload(temp=3, condition="Cloudy", location="Wrocław")
    assert weather.location == "Wrocław"


def test_control_characters_are_stripped():
    """Control / non-printable characters are removed, surrounding whitespace trimmed."""
    track = SpotifyTrackPayload(
        artist="  Queen\x00\x07  ",
        track_name="Bohemian\x1fRhapsody",
        progress=0,
    )
    assert track.artist == "Queen"
    assert track.track_name == "BohemianRhapsody"


def test_progress_bounds_enforced():
    with pytest.raises(ValidationError):
        SpotifyTrackPayload(artist="A", track_name="B", progress=101)


def test_temp_bounds_enforced():
    with pytest.raises(ValidationError):
        WeatherPayload(temp=200, condition="Hot", location="Nowhere")


def test_mode_is_fixed():
    """mode defaults correctly and cannot be set to something else."""
    assert WeatherPayload(temp=1, condition="Clear", location="X").mode == "weather"
    assert SpotifyTrackPayload(artist="A", track_name="B", progress=0).mode == "spotify"

    with pytest.raises(ValidationError):
        WeatherPayload(mode="spotify", temp=1, condition="Clear", location="X")
