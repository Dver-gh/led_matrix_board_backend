import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def sanitize_display_text(v: str) -> str:
    """
    Strip only control / non-printable characters from text destined for the LED panel.

    Printable Unicode (including ``°``, ``¥`` and accented letters) is preserved: the
    firmware maps known codepoints to its CP437 font and renders ``?`` for anything it
    cannot map, so the backend no longer needs to pre-strip symbols.
    """
    clean_val = re.sub(r'[\x00-\x1f\x7f]', '', v)
    return clean_val.strip()


class SpotifyTrackPayload(BaseModel):
    """Wire contract for Spotify display state (matches led_board_code/sketch.ino)."""
    model_config = {"extra": "forbid"}

    mode: Literal["spotify"] = "spotify"
    artist: str = Field(..., min_length=1, max_length=50)
    track_name: str = Field(..., min_length=1, max_length=100)
    progress: int = Field(0, ge=0, le=100)

    @field_validator("artist", "track_name")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return sanitize_display_text(v)


class WeatherPayload(BaseModel):
    """Wire contract for weather display state (matches led_board_code/sketch.ino)."""
    model_config = {"extra": "forbid"}

    mode: Literal["weather"] = "weather"
    temp: int = Field(..., ge=-100, le=100)
    condition: str = Field(..., min_length=1, max_length=30)
    location: str = Field(..., min_length=1, max_length=50)

    @field_validator("condition", "location")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return sanitize_display_text(v)
