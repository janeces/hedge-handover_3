"""Runs the sensor data collection and writing to the database."""
import logging
from dotenv import dotenv_values

from device_io import io as dio
from device_io.trafoflex.config import get_main_logger, CHECK_CLEANUP_PERIOD, MAX_QUEUE_SIZE, DB_DIR,\
    TEMP_SENSOR_AMBIENT_NAME
from device_io.config import ENV_CONFIG_DIR


logger = get_main_logger(log_level=logging.INFO)  # TODO: determine the log level from some configuration

def main() -> None:
    """Runs the database that collects sensor data."""
    config = dotenv_values(ENV_CONFIG_DIR)
    # MC device
    try:
        mc_sensor = dio.create_mc_sensor(config)
        logger.info(f"Using MC interface: {config.get('MC_INTERFACE')}")
    except ValueError as e:
        logger.error(f"{e}. Exiting.")
        raise SystemExit(1)

    # Temperature probe
    temperature_sensor = dio.TemperatureSensor(TEMP_SENSOR_AMBIENT_NAME, "temp_ambient")

    si = float(config.get("SAMPLE_INTERVAL"))
    sensors = [(s, si) for s in [temperature_sensor, mc_sensor]]

    dio.run_data_collection(sensors, DB_DIR, CHECK_CLEANUP_PERIOD, MAX_QUEUE_SIZE)


if __name__ == "__main__":
    main()