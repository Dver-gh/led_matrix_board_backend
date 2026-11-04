import json
import logging
import os

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

class MqttPublisher:
    """Service responsible for connecting to the MQTT broker and publishing validated data payloads."""
    def __init__(self):
        self.broker_host = os.getenv("MQTT_BROKER_HOST", "localhost")
        self.broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.base_topic = os.getenv("MQTT_TOPIC", "home/led/display")

        try:
            self.client = mqtt.Client(
                client_id="led_backend_publisher",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
        except AttributeError:
            self.client = mqtt.Client(client_id="led_backend_publisher")

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback triggered when the client receives a CONNACK response from the broker."""
        if rc == 0:
            logger.info(f"Successfully connected to MQTT broker at {self.broker_host}:{self.broker_port}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback triggered when the client disconnects from the broker."""
        logger.info("Disconnected from MQTT broker.")

    def connect(self):
        """Establishes connection to the broker and starts the background network loop."""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
        except Exception as e: # noqa: BLE001
            logger.error(f"Error connecting to MQTT broker: {e}")

    def publish(self, data_model, sub_topic: str | None = None) -> bool:
        """
        Serializes a Pydantic model (or dict) to JSON and publishes it to the MQTT topic.

        Args:
            data_model: Pydantic model instance (e.g., SpotifyTrackPayload, WeatherPayload)
            sub_topic (str, optional): Optional sub-topic suffix (e.g., 'spotify' or 'weather').

        Returns:
            bool: True if the message was successfully dispatched, False otherwise.
        """
        try:
            target_topic = f"{self.base_topic}/{sub_topic}" if sub_topic else self.base_topic

            if hasattr(data_model, "model_dump_json"):
                payload_json = data_model.model_dump_json()
            elif hasattr(data_model, "dict"):
                payload_json = json.dumps(data_model.dict())
            else:
                payload_json = json.dumps(data_model)

            info = self.client.publish(target_topic, payload_json, qos=1)

            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published payload to topic '{target_topic}': {payload_json}")
                return True
            else:
                logger.error(f"Failed to publish message to MQTT, error code: {info.rc}")
                return False

        except Exception as e: # noqa: BLE001
            logger.error(f"Exception occurred during MQTT publishing: {e}")
            return False

    def disconnect(self):
        """Stops the network background loop and disconnects cleanly from the broker."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT publisher disconnected cleanly.")
        except Exception as e: # noqa: BLE001
            logger.error(f"Error while disconnecting from MQTT broker: {e}")
