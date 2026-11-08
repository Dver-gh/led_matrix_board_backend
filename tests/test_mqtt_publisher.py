from unittest.mock import MagicMock

import pytest

from src.models.display_payload import SpotifyTrackPayload, WeatherPayload
from src.services.mqtt_publisher import MqttPublisher


@pytest.fixture
def mock_mqtt_client(mocker):
    """Mocks paho.mqtt.client.Client so no real network connection is made."""
    mock_client_class = mocker.patch("src.services.mqtt_publisher.mqtt.Client")
    return mock_client_class.return_value


@pytest.fixture
def publisher(mocker, mock_mqtt_client):
    """MqttPublisher with deterministic broker/topic config."""
    mocker.patch.dict(
        "os.environ",
        {
            "MQTT_BROKER_HOST": "localhost",
            "MQTT_BROKER_PORT": "1883",
            "MQTT_TOPIC": "home/led/display/state",
        },
    )
    return MqttPublisher()


def test_publisher_initialization(publisher, mock_mqtt_client):
    assert mock_mqtt_client.on_connect == publisher._on_connect
    assert mock_mqtt_client.on_disconnect == publisher._on_disconnect


def test_connect(publisher, mock_mqtt_client):
    publisher.connect()

    mock_mqtt_client.connect.assert_called_once_with("localhost", 1883, keepalive=60)
    mock_mqtt_client.loop_start.assert_called_once()


def test_publish_to_single_topic(publisher, mock_mqtt_client):
    """Weather publishes to the one topic the firmware subscribes to (no sub-topic)."""
    payload = WeatherPayload(temp=20, condition="Sunny", location="Wroclaw")

    info = MagicMock()
    info.rc = 0
    mock_mqtt_client.publish.return_value = info

    assert publisher.publish(payload) is True

    topic, payload_json = mock_mqtt_client.publish.call_args[0][:2]
    assert topic == "home/led/display/state"
    assert "Sunny" in payload_json
    assert '"temp":20' in payload_json


def test_publish_preserves_utf8(publisher, mock_mqtt_client):
    """Non-ASCII characters are sent as real UTF-8, not \\uXXXX escapes."""
    payload = SpotifyTrackPayload(
        artist="¥$, Kanye West, Ty Dolla $ign",
        track_name="Carnival",
        progress=42,
    )

    info = MagicMock()
    info.rc = 0
    mock_mqtt_client.publish.return_value = info

    publisher.publish(payload)

    payload_json = mock_mqtt_client.publish.call_args[0][1]
    assert "¥" in payload_json
    assert "\\u00a5" not in payload_json


def test_publish_failure(publisher, mock_mqtt_client):
    payload = WeatherPayload(temp=15, condition="Cloudy", location="Krakow")

    info = MagicMock()
    info.rc = 4
    mock_mqtt_client.publish.return_value = info

    assert publisher.publish(payload) is False


def test_disconnect(publisher, mock_mqtt_client):
    publisher.disconnect()

    mock_mqtt_client.loop_stop.assert_called_once()
    mock_mqtt_client.disconnect.assert_called_once()
