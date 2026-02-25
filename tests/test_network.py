import pytest
import time

import paho.mqtt.client as mqtt_client

import device_io.io as dio

TIMEOUT = 0.1  # Timeout time [s]
MSG_WAIT_TIME = 10  # Wait time for a message over MQTT [s]
MSG_CHECK_TIME = 0.5  # Interval between loop checks [s]

@pytest.mark.network
@pytest.mark.parametrize("mqtt_topic", [dio.WEATHER_TOPIC, dio.UPLOAD_TOPIC])
def test_MQTT_client(mqtt_topic):
    broker, port, uname, pwd = dio.import_credentials(dio.CREDENTIALS_DIR)
    client = dio.MQTTClient(broker, port, mqtt_topic, uname, pwd, dio.CERTIFICATE_DIR)
    client.client.connect_timeout = TIMEOUT
    client.connect()
    client.start_loop()
    time.sleep(TIMEOUT)
    assert client.client.is_connected(), f"MQTT client failed to connect in {TIMEOUT} s."

@pytest.mark.network
def test_weather_availability():
    broker, port, uname, pwd = dio.import_credentials(dio.CREDENTIALS_DIR)
    mcl = dio.MQTTClient(broker, port, dio.WEATHER_TOPIC, uname, pwd, dio.CERTIFICATE_DIR)
    mcl.client.user_data_set(False)

    def on_connect(client, userdata, flags, rc, properties):
        if rc == mqtt_client.CONNACK_ACCEPTED:
            client.subscribe(mcl.topic)
        else:
            print(f"Connection failed with code {rc}")

    def on_message(client, userdata, msg):
        client.user_data_set(True)

    mcl.set_on_connect(on_connect)
    mcl.set_on_message(on_message)
    mcl.connect()
    mcl.start_loop()

    t_wait = MSG_WAIT_TIME
    t_check = 0.5
    t0 = time.time()

    while not mcl.client.user_data_get() and time.time() - t0 < t_wait:
        time.sleep(t_check)

    assert mcl.client.user_data_get(), f"No response from topic {mcl.topic} in {MSG_WAIT_TIME} s"

