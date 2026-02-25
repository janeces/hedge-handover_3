import logging
# Uncomment if required by the get_main_logger function if its relevant parts are uncommented.
#from logging.handlers import TimedRotatingFileHandler
import time
from dotenv import dotenv_values

logging.Formatter.converter = time.gmtime  # Sets the global logging time to UTC

TESTING = False  # Enable some options that are used for testing purposes.
ENV_CONFIG_DIR = "config/env.conf"  # Path to the file with environment variables
config = dotenv_values(ENV_CONFIG_DIR)
BASE_PATH = config.get("BASE_PATH")  # Base directory of the project.
BINARY_PATH = BASE_PATH + "/bin"  # Location of the Dythera or Trafoflex binaries
TMP_PATH = config.get("TMP_PATH")  # Directory to store temporary files such as databases and simulation results.
DEVICE_ID = config.get("HEDGE_DEVICE_ID")  # ID of the GW IotMaxx device.
SENSOR_PATH = config.get("TEMP_PROBE_DIR")  # Directory where temperature sensors are found in the filesystem.
CERTIFICATE_PATH = BASE_PATH + "/certificate"  # Path where MQTT certificates and credentials can be found.
CERTIFICATE_DIR = f"{CERTIFICATE_PATH}/{config.get('CERTIFICATE_NAME')}"  # MQTT certificate.
CREDENTIALS_DIR = f"{CERTIFICATE_PATH}/credentials.xml"  # Directory of MQTT credentials for the JSI user.
WEATHER_INTERFACE_LOCAL = "local"  # | Constants related to WEATHER_INTERFACE in env.conf to determine how
WEATHER_INTERFACE_MQTT = "mqtt"    # | weather station data is obtained.
WEATHER_TOPIC = config.get("WEATHER_MQTT_TOPIC")  # MQTT topic for downloading weather data.
UPLOAD_TOPIC = config.get("UPLOAD_TOPIC")  # MQTT topic for uploading results.
PUBLISH_TIMEOUT = 60  # MQTT publish timeout [s].
PUBLISH_QOS = 2  # Publish quality of service (0: on send, 1: on receiver acknowledge, 2: on receiver completion)
MC_TOPIC = config.get("MC_MQTT_TOPIC")  # MQTT topic for MC device data.
MC_INTERFACE_NET= "net"   # | Constants related to MC_INTERFACE in env.conf to determine how MC data is obtained
MC_INTERFACE_MQTT= "mqtt" # |
BUFF_LEN = 4096  # Length of the receive buffer for socket.recv in bytes.
MQTT_TIME_FORMAT_OUT = "%Y-%m-%dT%H:%M:%SZ"  # Timestamp format for uploading DTR results.
TEMP_DENOMINATOR = 1000  # Denominator to get the temperature in Celsius
#LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # This is for testing
LOG_FORMAT = "[%(asctime)sZ] %(levelname)s: %(message)s"

class LoggerType:
    """Standardizes how logs are referenced wrt ENV_CONFIG_DIR"""
    DB = "DB"  # Database logs
    IC = "IC"  # Initial condition constructor and binary runs log

def get_main_logger(log_level=logging.INFO) -> logging.Logger:
    """
    Gets the main logger of the script
    :param log_level: Logging level
    """

    logging.basicConfig(
            level=log_level,
            format=LOG_FORMAT,
        )

    logger = logging.getLogger("device_io")


    # In case someone would want to have timed rotating logs, but services take care of log management
    # if not TESTING:
    #     config = dotenv_values(ENV_CONFIG_DIR)
    #     handler = TimedRotatingFileHandler(config.get(log_dir), when='midnight',
    #                                     backupCount=int(config.get("LOG_DAYS")), utc=True)
    #     formatter = logging.Formatter(LOG_FORMAT)
    #     formatter.converter = time.gmtime  # Use UTC timestamps
    #     handler.setFormatter(formatter)
    #
    #     logger.addHandler(handler)

    return logger