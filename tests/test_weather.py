import pytest
from unittest.mock import MagicMock
from requests.exceptions import Timeout
from src.clients.weather_client import WeatherClient
from src.models.display_payload import WeatherPayload

@pytest.fixture
def weather_client(mocker):
    """Fixture providing a WeatherClient instance."""
    mocker.patch.dict("os.environ", {"OPENWEATHER_API_KEY": "fake_test_key", "OPENWEATHER_CITY": "Warsaw"})
    return WeatherClient()

def test_get_current_weather_success(weather_client, mocker):
    """Test successful weather data fetching and Pydantic validation."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "name": "Warsaw",
        "main": {"temp": 18.5, "humidity": 65},
        "weather": [{"main": "Clear"}]
    }

    mocker.patch("src.clients.weather_client.requests.get", return_value=mock_response)

    result = weather_client.get_current_weather()

    assert result is not None
    assert isinstance(result, WeatherPayload)
    assert result.city == "Warsaw"
    assert result.temperature == 18.5
    assert result.condition == "Clear"
    assert result.humidity == 65

def test_get_current_weather_timeout(weather_client, mocker):
    """Test resilience against request timeout."""
    mocker.patch("src.clients.weather_client.requests.get", side_effect=Timeout)

    result = weather_client.get_current_weather()
    assert result is None
