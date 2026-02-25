"""Runs the sensor data collection and writing to the database."""
import sys
import logging
from dotenv import dotenv_values

from device_io import io as dio
from device_io.config import ENV_CONFIG_DIR, WEATHER_INTERFACE_LOCAL, WEATHER_INTERFACE_MQTT
from device_io.dythera.config import get_main_logger, CHECK_CLEANUP_PERIOD, MAX_QUEUE_SIZE, DB_DIR

logger = get_main_logger(log_level=logging.INFO)

def main() -> None:
    """Runs the database that collects sensor data"""
    logger.info("Starting Dythera IC configuration and computation.")
    config = dotenv_values(ENV_CONFIG_DIR)

    weather_interface = config.get("WEATHER_INTERFACE")

    if weather_interface == WEATHER_INTERFACE_MQTT:
        logger.info("Connecting to MQTT interface.")
        broker, port, uname, pwd = dio.import_credentials(dio.CREDENTIALS_DIR)
        client = dio.MQTTClient(broker, port, dio.WEATHER_TOPIC, uname, pwd, dio.CERTIFICATE_DIR)
        station = dio.WeatherStationMqtt(client)
    elif weather_interface == WEATHER_INTERFACE_LOCAL:
        logger.info("Connecting over RS485.")
        station = dio.WeatherStationLocal()
    else:
        logger.error(f"Unsupported weather interface: {weather_interface}. Exiting.")
        sys.exit(1)

    interval = float(config.get("SAMPLE_INTERVAL"))
    sensors = [(s, interval) for s in [station, ]]

    dio.run_data_collection(sensors, DB_DIR, CHECK_CLEANUP_PERIOD, MAX_QUEUE_SIZE)


if __name__ == "__main__":
    main()