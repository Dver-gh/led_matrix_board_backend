from unittest.mock import MagicMock

import pytest

from src.models.display_payload import WeatherPayload
from src.services.mqtt_publisher import MqttPublisher


@pytest.fixture
def mock_mqtt_client(mocker):
    """
    Fixture that mocks the paho.mqtt.client.Client class,
    preventing any real network connections during tests.
    """
    mock_client_class = mocker.patch("src.services.mqtt_publisher.mqtt.Client")
    mock_instance = mock_client_class.return_value
    return mock_instance


@pytest.fixture
def publisher(mock_mqtt_client):
    """Fixture providing an instance of MqttPublisher with a mocked MQTT client."""
    return MqttPublisher()


def test_publisher_initialization(mock_mqtt_client):
    """Test that MqttPublisher initializes and sets callbacks correctly."""
    publisher = MqttPublisher()

    assert mock_mqtt_client.on_connect == publisher._on_connect
    assert mock_mqtt_client.on_disconnect == publisher._on_disconnect


def test_connect(publisher, mock_mqtt_client):
    """Test establishing connection to the MQTT broker and starting the loop."""
    publisher.connect()

    mock_mqtt_client.connect.assert_called_once_with("localhost", 1883, keepalive=60)
    mock_mqtt_client.loop_start.assert_called_once()


def test_publish_success(publisher, mock_mqtt_client):
    """Test successful serialization and publishing of a Pydantic model to a sub-topic."""
    weather_data = WeatherPayload(
        city="Warsaw",
        temperature=20.0,
        condition="Sunny",
        humidity=50
    )

    mock_info = MagicMock()
    mock_info.rc = 0
    mock_mqtt_client.publish.return_value = mock_info

    success = publisher.publish(weather_data, sub_topic="weather")

    assert success is True
    mock_mqtt_client.publish.assert_called_once()

    call_args = mock_mqtt_client.publish.call_args[0]
    topic = call_args[0]
    payload_json = call_args[1]

    assert topic == "home/led/display/weather"
    assert "Warsaw" in payload_json
    assert "20.0" in payload_json


def test_publish_failure(publisher, mock_mqtt_client):
    """Test handling of publishing failure returned by the broker."""
    weather_data = WeatherPayload(
        city="Krakow",
        temperature=15.0,
        condition="Cloudy",
        humidity=70
    )

    mock_info = MagicMock()
    mock_info.rc = 4
    mock_mqtt_client.publish.return_value = mock_info

    success = publisher.publish(weather_data)

    assert success is False
    mock_mqtt_client.publish.assert_called_once()


def test_disconnect(publisher, mock_mqtt_client):
    """Test clean disconnection from the broker."""
    publisher.disconnect()

    mock_mqtt_client.loop_stop.assert_called_once()
    mock_mqtt_client.disconnect.assert_called_once()
