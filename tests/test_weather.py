from unittest.mock import MagicMock

import pytest
from requests.exceptions import Timeout

from src.clients.weather_client import WeatherClient
from src.models.display_payload import WeatherPayload


@pytest.fixture
def weather_client(mocker):
    mocker.patch.dict(
        "os.environ",
        {"OPENWEATHER_API_KEY": "fake_test_key", "OPENWEATHER_CITY": "Wrocław"},
    )
    return WeatherClient()


def test_get_current_weather_success(weather_client, mocker):
    """Weather is reshaped to the board contract: integer temp, detailed capitalized condition."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "name": "Wrocław",
        "main": {"temp": 3.2, "humidity": 65},
        "weather": [{"main": "Rain", "description": "heavy intensity rain"}],
    }

    mocker.patch("src.clients.weather_client.requests.get", return_value=mock_response)

    result = weather_client.get_current_weather()

    assert isinstance(result, WeatherPayload)
    assert result.mode == "weather"
    assert result.temp == 3
    assert result.condition == "Heavy intensity rain"
    assert result.location == "Wrocław"  # non-ASCII preserved for firmware glyph mapping


def test_get_current_weather_timeout(weather_client, mocker):
    mocker.patch("src.clients.weather_client.requests.get", side_effect=Timeout)

    assert weather_client.get_current_weather() is None


def test_missing_api_key_returns_none(mocker):
    mocker.patch.dict("os.environ", {}, clear=True)
    client = WeatherClient()

    assert client.get_current_weather() is None
