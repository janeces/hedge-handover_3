"""Configuration constants specific to Trafoflex."""
import logging
from dotenv import dotenv_values

from device_io.config import BASE_PATH, TMP_PATH, ENV_CONFIG_DIR
from device_io.config import get_main_logger as gml
import device_io.io as dio


EXE = BASE_PATH + "/bin/trafoflex_main"  # Path to the Trafoflex executable.
MAX_QUEUE_SIZE = 1000  # Maximum size of the queue that accepts sensor measurements.

OUTPUT_SUFFIX = "_response.pb"  # Suffix of the response in the output folder directory.

DB_DIR = f"{TMP_PATH}/trafoflex_database.db"  # Path of the database.
CHECK_CLEANUP_PERIOD = 10000  # Number of database updates after which to check whether old entries should be deleted and the db vacuumed

IC_NAME = "trafoflex_input"  # Directory where the input for trafoflex_main is stored.
IC_DIR = f"{TMP_PATH}/{IC_NAME}.pb"  # Folder where the initial conditions for Trafoflex are written to.
RESULTS_PATH = f"{TMP_PATH}/trafoflex_simulation_output"  # Folder where Trafoflex results are output to.
STATE_DIR = f"{RESULTS_PATH}/{IC_NAME}{OUTPUT_SUFFIX}"  # Directory where the transformer state is stored.

MAX_TRAFO_STATE_AGE = 15 * 60  # Maximum age of the transformer state where no thermalization is conducted [s].
THERMALIZATION_MEASUREMENT_SPACING = 15 * 60  # Spacing of the thermalization measurements [s].
MIN_STATE_PRESENT_DIST = 1 * 60  # Minimum run length for the ampacity computation [s].


BLANK_START_DURATION = 86400 * 3  # Duration of relaxation of the start from no prior transformer state [s].

config = dotenv_values(ENV_CONFIG_DIR)
TEMP_SENSOR_AMBIENT_NAME = config.get("TEMP_PROBE_AMBIENT_NAME")  # Name of the ambient temperature probe as seen by the filesystem.
TEMP_SENSOR_TLT_NAME = config.get("TEMP_PROBE_TLT_NAME")  # Name of the top oil temperature validation probe as seen by the filesystem.

SENSORS = [dio.TemperatureSensor, dio.McSensor]  # Sensor types to collect data from.

# Typing helper types.
measurement_t = list[dio.TemperatureMeasurement | dio.McSensorMeasurement]
parsed_t = list[list[dio.TemperatureMeasurement] | list[dio.McSensorMeasurement]]

def get_main_logger(log_level=logging.INFO) -> logging.Logger:
    """
    Returns the main logger of the script.
    :param log_level: Logging level
    """
    return gml(log_level=log_level)