"""Configuration constants specific to Dythera."""
import sys
from dotenv import dotenv_values

from device_io.config import BASE_PATH, TMP_PATH, ENV_CONFIG_DIR, WEATHER_INTERFACE_MQTT, WEATHER_INTERFACE_LOCAL
from device_io.config import get_main_logger as gml
import device_io.io as dio
import logging

def get_main_logger(log_level=logging.INFO) -> logging.Logger:
    """
    Returns the main logger of the script
    :param log_level: logging level
    """
    return gml(log_level=log_level)


EXE = BASE_PATH + "/bin/Dythera_exe" # Path to the Dythera executable.
MAX_QUEUE_SIZE = 1000  # Maximum size of the queue that accepts sensor measurements.
SIM_TIME = 10000  # Simulation time [s].
DB_DIR = f"{TMP_PATH}/dythera_database.db"  # Path of the database.
CHECK_CLEANUP_PERIOD = 10000  # Number of database updates aftet which to check whether old entries should be deleted and the db vacuumed.
OUTPUT_NAME = "dythera_simulation_output"  # Name of the simulation output folder.
IC_NAME = "dythera_input"  # Name of the initial condition file.
RESULTS_PATH = f"{TMP_PATH}/{OUTPUT_NAME}"  # Folder where Dythera results are output to.
RESULTS_TIME_TO_OVERHEAT_SUFFIX = "_history.csv"  # Suffix of the file where the time to overheat is stored.
IC_DIR = f"{TMP_PATH}/{IC_NAME}.pb"  # Folder where the initial conditions for Dythera are written to.
# File where the time to overheat is output to.
TIME_TO_OVERHEAT_DIR = f"{RESULTS_PATH}/{IC_NAME}{RESULTS_TIME_TO_OVERHEAT_SUFFIX}"

SENSORS = [dio.WeatherStation, ]
# Configure which values are needed for the computation.
dio.WeatherStation.used_values += ["Ta", "Sm", "Dm", "Pa", "Ri", "Ua", "s_irrad"]
dio.WeatherStationLocal.split_char = {"Ta": 'C', "Sm": 'M', "Dm": 'D', "Pa": 'H', "Ri": 'M', "Ua": 'P'}



