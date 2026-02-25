"""Runs the sensor data collection and writing to the database."""
import logging
import sys
from dotenv import dotenv_values

from device_io import io as dio
from device_io.trafoflex.config import get_main_logger, CHECK_CLEANUP_PERIOD, MAX_QUEUE_SIZE, DB_DIR,\
    TEMP_SENSOR_AMBIENT_NAME
from device_io.config import ENV_CONFIG_DIR, MC_INTERFACE_NET, MC_INTERFACE_MQTT


logger = get_main_logger(log_level=logging.INFO)  # TODO: determine the log level from some configuration

def main() -> None:
    """Runs the database that collects sensor data."""
    config = dotenv_values(ENV_CONFIG_DIR)
    # MC device
    mc_interface = config.get("MC_INTERFACE")
    if mc_interface == MC_INTERFACE_NET:
        logger.info(f"Using the local network MC interface")
        mc_sensor = dio.McSensorNet(config.get("MC_HOSTNAME"), int(config.get("MC_PORT")))
    elif mc_interface == MC_INTERFACE_MQTT:
        broker, port, uname, pwd = dio.import_credentials(dio.CREDENTIALS_DIR)
        logger.warning("Replaced broker credentials for \"localhost\"")
        logger.info(f"Using the MQTT MC interface")
        mc_client = dio.MQTTClient(broker, port, dio.MC_TOPIC, uname, pwd, dio.CERTIFICATE_DIR)
        mc_sensor = dio.McSensorMqtt(mc_client, config.get("MC_CONTROL_UNIT"))
    else:
        logger.error(f"Unsupported MC interface: {mc_interface}. Exiting.")
        sys.exit(1)

    # Temperature probe
    temperature_sensor = dio.TemperatureSensor(TEMP_SENSOR_AMBIENT_NAME, "temp_ambient")

    si = float(config.get("SAMPLE_INTERVAL"))
    sensors = [(s, si) for s in [temperature_sensor, mc_sensor]]

    dio.run_data_collection(sensors, DB_DIR, CHECK_CLEANUP_PERIOD, MAX_QUEUE_SIZE)


if __name__ == "__main__":
    main()