"""Combines sensor data into measurements, constructs initial conditions, runs the binary and communicates the results
over MQTT."""
import logging
import device_io.dythera.io as dio
from device_io.dythera.config import get_main_logger

logger = get_main_logger(log_level=logging.INFO)

if __name__ == "__main__":

    cfg = dio.DytheraIcConfigurator()

    cfg.compute_ampacity()
    cfg.upload_results()
    logger.info("Results uploaded")
    # cfg.print_results()