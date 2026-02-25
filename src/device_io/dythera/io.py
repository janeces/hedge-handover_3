"""Input/output operations specified for Dythera."""
import logging

import device_io.io as dio
import device_io.dythera.generate_proto as gdp
import device_io.dythera.pb2 as pb
from device_io.dythera.config import *

logger = logging.getLogger(__name__)


class ProtobufMeasurementD(dio.ProtobufMeasurement):
    def set_defaults(self):
        self.electrical_current = 0

class DytheraUpload(dio.UploadResponse):
    """Handles uploading of Dythera run results to Sumo"""
    msg_attrs = dio.UploadResponse.msg_attrs + ["time", "droplet_temperature", "wind_velocity", "pressure", "rain_rate",
                 "humidity", "solar_irradiance", "electrical_current", "I_th"]
    ambient_temperature: float
    droplet_temperature: float  # Same as ambient temperature.
    wind_velocity: float  # Wind speed, average [m/s] Usually over 1-10 minutes.
    wind_angle: float  # Wind angle [deg].
    pressure: float  # Atmospheric pressure [Pa].
    rain_rate: float  # Rainfall intensity [mm]/h Calculated rate.
    humidity: float # Relative humidity [%].
    solar_irradiance: float  # Solar irradiance [w/m^2].
    electrical_current: float  # Current over the line [A].
    time_to_overheat: float  # Time the to line overheating [s].
    I_th: float  # Line loadability.

    def set_data(self, proto: ProtobufMeasurementD, I: float, time_to_overheat:float, I_th: float):
        """
        Set the data that goes into the result message
        :param proto: The last protobuf measurement used
        :param I: Current over the line [A]
        :param time_to_overheat: Time for the line to reach critical temperature [s]
        :param I_th: Loadability [A]
        """
        self.set_timestamp(proto.time)
        self.time = proto.time
        self.ambient_temp = proto.ambient_temperature
        self.droplet_temperature = proto.droplet_temperature
        self.wind_velocity = proto.wind_velocity
        self.wind_angle = proto.wind_angle
        self.pressure = proto.pressure
        self.rain_rate = proto.rain_rate
        self.humidity = proto.humidity
        self.solar_irradiance = proto.solar_irradiance
        self.electrical_current = I
        self.time_to_overheat = time_to_overheat
        self.I_th = I_th


class DytheraIcConfigurator(dio.IcConfigurator):
    """
    Collects the relevant data necessary for running Dythera, runs the Dythera executable and 
    sends results to Sumo
    """
    sensors = SENSORS  # List of sensor types used to assemble measurements.
    uploader: DytheraUpload  # Helper to handle uploads of results to Sumo.
    last_measurement: ProtobufMeasurementD | None

    def __init__(self) -> None:
        super().__init__(EXE, DB_DIR, DytheraUpload(dio.DEVICE_ID), RESULTS_PATH, IC_DIR)

    def initialize_request(self) -> None:
        """Configure request parameters and output folder."""
        self.request = pb.SimulationRequest()
        gdp.configure_request(self.request)
        self.set_output_folder(RESULTS_PATH)

    def compute_ampacity(self) -> None:
        """Compute line ampacity."""
        logger.info(f"Computing ampacity.")
        now = dio.get_current_time_utc().timestamp()
        self.collect_measurements(now)
        logger.debug("Running Dythera.")
        self.run_binary()
        logger.info("Ampacity computed.")

    def collect_measurements(self, t_now:float):
        """
        Collect measurements to add to the simulation request. They are added as if all the variables
        were obtained at the same time, but really it interpolates the latest known value in the past.
        In case of only one measurement present, we select the latest.
        :param t_now: Current time [s] since epoch"""
        measurements = self.parse_data()

        # Select only the most recent measurements since Dythera requires only one.
        current_measurement = [max(m, key=lambda x:x.time) for m in measurements]
        # Set the start and end time.
        self.request.parameters.numerical_setup.end_time = t_now + SIM_TIME
        self.request.parameters.numerical_setup.start_time = t_now

        logger.debug(f"Using measurement {current_measurement[0].__dict__}.")
        meas = ProtobufMeasurementD.default()
        for cm in current_measurement: cm.update_proto(meas)
        meas.time = t_now
        self.add_measurement(meas)  # Project measurements on the same time.
        # TODO: Once you get electrical current data, connect this to a sensor.
        self.last_measurement = meas

    def get_pb_measurement(self):
        return self.request.parameters.measurements.add()

    def parse_results(self, *parameters: str):
        """Retrieves the relevant data from the simulation results.
        :param parameters: names of the columns of the output file to retrieve the data from"""
        with open(TIME_TO_OVERHEAT_DIR, "r") as f:
            text = f.read()

        lines = text.split("\n")
        header = lines[0].split(",")
        param_indices = {p:-1 for p in parameters}

        for i,h in enumerate(header):
            for p in parameters:
                if p in h: param_indices[p] = i

        final_values = (lines[-1] if len(lines[-1]) == len(header) else lines[-2]).split(",")
        return [float(final_values[param_indices[p]].strip()) for p in parameters]

    def upload_results(self) -> None:
        """Upload the results to Sumo."""
        I = self.request.parameters.measurements[-1].electrical_current
        tto, I_th = self.parse_results("time_to_overheat", "I_th" )
        logger.debug(f"Time to overheat: {tto}, type: {type(tto)}")
        self.uploader.set_data(self.last_measurement, I, tto, I_th)
        self.uploader.send_data()


if __name__ == "__main__":
    pass


