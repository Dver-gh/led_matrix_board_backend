import re

from pydantic import BaseModel, Field, field_validator


class SpotifyTrackPayload(BaseModel):
    """Pydantic model for validating and sanitizing Spotify playback data."""
    model_config = {"extra": "forbid"}

    artist: str = Field(..., min_length=1, max_length=50)
    track_name: str = Field(..., min_length=1, max_length=100)
    is_playing: bool = False
    progress_ms: int = Field(0, ge=0)
    duration_ms: int = Field(0, ge=0)

    @field_validator("artist", "track_name")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """
        Sanitizes entry data from API.
        Leaves only letters, digits and punctuation, preventing unwated characters being
	injected onto the LED screen.
        """
        clean_val = re.sub(r'[^\w\s\-\.\,\&\(\)\!\?\$]', '', v)
        return clean_val.strip()

class WeatherPayload(BaseModel):
    """Pydantic model for validating and sanitizing weather data from OpenWeather API."""
    model_config = {"extra": "forbid"}

    city: str = Field(..., min_length=1, max_length=50)
    temperature: float = Field(..., ge=-100.0, le=100.0)
    condition: str = Field(..., min_length=1, max_length=30)
    humidity: int = Field(..., ge=0, le=100)

    @field_validator("city", "condition")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """Sanitize text input to ensure safe characters for LED rendering."""
        clean_val = re.sub(r'[^\w\s\-\.]', '', v)
        return clean_val.strip()
