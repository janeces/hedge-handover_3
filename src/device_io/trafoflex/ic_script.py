"""Combines sensor data into measurements, constructs initial conditions, runs the binary and communicates the results
over MQTT."""
import logging
import argparse

import device_io.trafoflex.io as tio
from device_io.dythera.config import get_main_logger
logger = get_main_logger(logging.INFO)

if __name__ == "__main__":

    # Argument parsing.
    parser = argparse.ArgumentParser(description="Generates the input files for Trafoflex")
    parser.add_argument("model_path", type=str, help="Full path to the binary transformer model")
    args = parser.parse_args()


    cfg = tio.TrafoflexIcConfigurator(args.model_path)

    cfg.thermalise()
    cfg.compute_ampacity()
    #cfg.print_results()
    cfg.upload_result()
    logger.info("Results uploaded.")