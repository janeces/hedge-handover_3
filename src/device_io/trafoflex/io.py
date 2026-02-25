"""Input/output operations specified for Trafoflex."""
import sys
import time
import datetime
import logging
from typing import Any

import device_io.io as dio
import device_io.trafoflex.generate_proto as gtp
import device_io.trafoflex.pb2 as pb
from device_io.trafoflex.config import *

logger = logging.getLogger(__name__)


class TrafoflexUpload(dio.UploadResponse):
    """Handles uploading of Trafoflex run results to Sumo."""
    msg_attrs = dio.UploadResponse.msg_attrs + ["I", "Ith", "Tlt", "tlt", "Hst"]
    I: float  # Average current over the different phases [A].
    Ith: float  # Electrical current at which the critical temperature is achieved [A].
    Tlt: float  # Calculated temperature of oil at the top of the transformer [deg C].
    Hst: float  # Hot spot temperature [deg C].
    tlt: float  # Top oil temperature measured by a probe used for to verify the computed result [deg C].

    def set_data(self, proto: dio.ProtobufMeasurement, tlt_temp: dio.TemperatureMeasurement, result):
        """
        Set the data that goes into the result message
        :param proto: Last protobuffer measurement used
        :param tlt_temp: Top oil temperature measurement for verification
        :param result: Trafoflex's SimulationResponse protobuf object
        """
        self.set_timestamp(proto.time)
        self.ambient_temp = proto.ambient_temperature
        self.time_to_overheat = result.time_to_overheat
        self.I = proto.electrical_current
        self.Ith = result.thermal_electrical_current
        self.Tlt = result.top_oil_temperature
        self.Hst = result.hot_spot_temperature
        self.tlt = tlt_temp.temperature

    def set_data_dummy(self, *args):
        """Version of set_data for use in testing."""
        dt = datetime.datetime.fromtimestamp(time.time(), tz=datetime.timezone.utc)
        self.ts = dt.strftime(dio.MQTT_TIME_FORMAT_OUT)
        logger.debug(f"Timestamp for upload: {self.ts}")
        self.ambient_temp = 21
        self.time_to_overheat = 200000
        self.I = 1
        self.Ith = 2
        self.Tlt = 21
        self.Hst = 21


class TrafoflexIcConfigurator(dio.IcConfigurator):
    """
    Collects the relevant data necessary for running Trafoflex, runs the simulation and communicates with Sumo.
    """
    # List of measurements and a final time since epoch as the time of the measurement.
    last_measurement: dio.ProtobufMeasurement | None
    uploader: TrafoflexUpload  # Helper to handle uploads of results to Sumo.
    model: Any  # Transformer model.
    transformer_state: Any  # Holds transformer state (for results or startup).
    blank_start: bool | None  # Whether a prior transformer state is known.
    sensors = SENSORS  # List of sensor types used to assemble measurements.
    tlt_probe: dio.TemperatureSensor  # The temperature probe used for verification of the top oil temperature.
    tlt_output: dio.TemperatureMeasurement  # Top oil temperature measurement.

    def __init__(self, model_dir:str):
        """:param model_dir: Directory of the binary format transformer model"""
        self.model = pb.TransformerModel()
        self.transformer_state = pb.TransformerState()

        self.blank_start = None  # Whether we have no prior transformer state.
        self.get_last_transformer_state()
        self.get_model(model_dir)
        super().__init__(EXE, DB_DIR, TrafoflexUpload(dio.DEVICE_ID), RESULTS_PATH, IC_DIR)
        self.last_measurement = None  # The last measurement, used for sending input data over MQTT
        self.tlt_probe = dio.TemperatureSensor(TEMP_SENSOR_TLT_NAME, "temp_tlt")
        self.tlt_output = dio.TemperatureMeasurement()

    def initialize_request(self) -> None:
        """Configure request parameters and output folder."""
        self.request = pb.SimulationRequest()
        gtp.configure_request(self.request)
        self.request.transformer_model.CopyFrom(self.model)
        self.configure_transformer_state()
        self.set_output_folder(self._results_path)

    def get_last_transformer_state(self) -> None:
        """Retrieve the last transformer state if there is one."""
        try:
            with open(STATE_DIR, "rb") as f:
                response = pb.SimulationResponse()
                response.ParseFromString(f.read())
                self.transformer_state.CopyFrom(response.states[-1])
            self.blank_start = False
        except FileNotFoundError:
            self.blank_start = True

    def get_model(self, model_dir:str):
        """Load the transformer model."""
        try:
            with open(model_dir, "rb") as f:
                self.model.ParseFromString(f.read())
        except FileNotFoundError:
            logger.error(f"Model file {model_dir} not found. Exiting.")
            sys.exit(1)

    def configure_transformer_state(self) -> None:
        """If there is a preexisting transformer state, configure the request."""
        if not self.blank_start:  # If there is a preexisting transformer state stored.
            self.request.transformer_model.internal_state.CopyFrom(self.transformer_state)            

    def default_transformer_internal_state(self, temp: float):
        """Set the transformer internal temperatures to a chosen temperature
        :param temp: The temperature [deg C] of the transformer internal components"""
        for i in range(len(self.request.transformer_model.internal_state.internal_mass_temperatures)):
            logger.debug(f"Setting temperature {i} to {temp} C")
            self.request.transformer_model.internal_state.internal_mass_temperatures[i] = temp

    def configure_blank_start(self, time_now:float, temp:float):
        """
        Configures the request for thermalization
        :param time_now: Current time [s] since epoch
        :param temp: The temperature [deg C] to set the transfomer to start thermalization
        """
        logger.debug("Getting current time and ambient temperature due to no prior transformer state.")
        self.request.transformer_model.internal_state.time = time_now
        self.default_transformer_internal_state(temp)

    def thermalise(self) -> None:
        """Execute a longer run for the transformer to reach a steady state that will resemble the 
        actual state."""
        now = dio.get_current_time_utc().timestamp()
        if self.blank_start or now - self.request.transformer_model.internal_state.time > MAX_TRAFO_STATE_AGE:
            logger.debug(f"Blank start: {self.blank_start}, age condition {now - self.request.transformer_model.internal_state.time > MAX_TRAFO_STATE_AGE}")
            logger.info(f"Computing thermalization due to a too old or missing transformer state.")
            self.request.numerical_setup.training_mode = True  # Don't compute ampacity for faster computation.
            # Set the starting time.
            if self.blank_start: t = now - BLANK_START_DURATION
            else: t = self.request.transformer_model.internal_state.time
            self.collect_measurements(t, now, sparse_measurements=True)
            logger.debug(f"Thermalization request:\n{self.request}")
            self.run_binary()
            logger.info("Thermalization computed.")
        else:
            logger.info("Skipping thermalization.")

    def compute_ampacity(self) -> None:
        """Compute the transformer tolerances."""
        logger.info(f"Computing ampacity.")
        self.get_last_transformer_state()
        if self.blank_start: 
            logger.error(f"Couldn't find a previous transformer state at {STATE_DIR}. \
                         Have you performed thermalization? Exiting.")
            sys.exit()
        self.initialize_request()

        now = dio.get_current_time_utc().timestamp()
        t = self.request.transformer_model.internal_state.time

        if now - t < MIN_STATE_PRESENT_DIST:
            logger.debug("Shifting the transformer state slightly back in time to allow for stepping.")
            t = now - MIN_STATE_PRESENT_DIST
            self.request.transformer_model.internal_state.time = t
        
        self.collect_measurements(t, now)
        self.request.numerical_setup.training_mode = False
        logger.debug(f"Ampacity computation request:\n{self.request}")
        self.run_binary()
        logger.info("Ampacity computed.")
        self.tlt_output = self.tlt_probe.get_data()

    def collect_measurements(self, t:float, t_now:float, sparse_measurements=False):
        """
        Collect measurements to add to the simulation request. They are added as if all the variables
        were obtained at the same time, but really it interpolates the latest known value in the past.
        :param t: Initial time of the simulation [s] since epoch
        :param t_now: End of the simulation [s] since epoch
        :param sparse_measurements: Whether some measurements should be skipped when adding to the request
        """
        measurements = self.parse_data()

        logger.debug(f"Measurements: {measurements}")
        logger.debug(f"Time start: {t}, time now: {t_now}, time_now - time_start: {t_now - t}")
        
        # Sort the measurements and remove any that are more than just prior to the measurement time.
        for i, m in enumerate(measurements):
            m.sort(key=lambda w : w.time)
            min_idx = self.smallest_below(m,  t)
            measurements[i] = m[min_idx:]

        # Concatenate measurements.        
        cm = [[k.time, i, j] for i, m in enumerate(measurements) for j, k in enumerate(m)]
        cm.sort(key = lambda x : x[0])

        current_measurement = dio.ProtobufMeasurement.default()
        for m in measurements: m[0].update_proto(current_measurement) # Project measurements on the same time.
        current_measurement.time = t
        self.add_measurement(current_measurement)
        # If there is no prior known transformer state, create one where all parts have ambient temperature.
        if self.blank_start:
            self.configure_blank_start(t, current_measurement.ambient_temperature)

        max_measurement = [(m[0].time if m[0].time <= t else -1) for m in measurements]

        # If at least one of the measurements was taken before or at the last transformer state.
        if max(max_measurement) > 0: 
            # Find the measurement type that was taken the least amount of time before the transformer state.
            cut_idx = self.max_idx(max_measurement)
            
            # Remove all prior measurements.
            for i, c in enumerate(cm):
                if c[1] == cut_idx:
                    if i + 1 < len(cm):  # Avoid zero-length arrays.
                        logger.debug(f"Removing residual entries at index {i + 1}")
                        cm = cm[i + 1:]
                    else:
                        logger.debug(f"Setting a blank array for cm")
                        cm = []
                    break        
        
        # Add measurements one by one and each time create a new measurement entry.
        t_last = t
        for j, c in enumerate(cm):
            idx_m = c[1]  # Index of the measurement type.
            i = c[2]  # Index of the measurement in the list of this type.
            measurements[idx_m][i].update_proto(current_measurement)
            
            current_time = current_measurement.time
            # If the next measurement has the same time, don't add this measurement yet
            if j + 1 < len(cm) and measurements[cm[j+1][1]][cm[j+1][2]].time == current_time:
                continue
            
            if sparse_measurements:
                if current_time - t_last > THERMALIZATION_MEASUREMENT_SPACING:
                    logger.debug(f"Adding measurement at time {current_time}")
                    self.add_measurement(current_measurement)
                    t_last = current_time
                else:
                    logger.debug(f"Skipping measurement at time {current_time - t} due to last time {t_last} delta {current_time - t_last}")
            else:
                logger.debug(f"Adding measurement at time {current_time - t}")
                self.add_measurement(current_measurement)

        logger.debug(f"Adding measurement at time now {t_now} or delta: {t_now - t}")
        current_measurement.time = t_now
        self.add_measurement(current_measurement)  # Add a dummy measurement to set the simulation time

        self.last_measurement = current_measurement

    def add_measurement(self, proto: dio.ProtobufMeasurement):
        """
         Add a measurement to the SimulationRequest protobuffer message and account for a lack of current.
        :param proto: ProtobufMeasurement parameter set
        """
        if proto.electrical_current == 0:
            logger.warning("Reported average current is zero, substituting with transformer model's I_n to correctly"
                           " compute loadability.")
            proto.electrical_current = self.request.transformer_model.coeff[0].joule_heating.I_n
        super().add_measurement(proto)

    def get_pb_measurement(self):
        return self.request.measurements.add()

    @staticmethod
    def smallest_below(arr: list[dio.SensorMeasurement], t:float):
        """Find the index of the measurement that is the least below a given time.
        In case that the time is below all measurements return 0 index.
        In case that the time is above all measurements return the index of the last measurement.
        :param arr: Array of sorted sensor measurements
        :param t: Time below which to find the nearest measurement"""
        if arr[0].time > t: return 0  # In case we only have the transformer state and no measurements prior to that state.

        min_idx = -1
        for i in range(len(arr) - 1):
            if arr[i].time <= t < arr[i + 1].time:
                min_idx = i
                break

        if min_idx == -1: min_idx = len(arr) - 1
        
        return min_idx

    @staticmethod
    def max_idx(arr:list) -> int:
        """Find the index of the largest element in the array.
        :param arr: The array to find the index of the largest element of"""
        out = -1
        max_val = -1
        for i,j in enumerate(arr):
            if j > max_val:
                max_val = j
                out = i

        return out
    
    def print_results(self) -> None:
        """Print human-readable results."""
        self.get_last_transformer_state()
        print(self.transformer_state)

    def upload_result(self) -> None:
        """Upload the results to Sumo."""
        self.get_last_transformer_state()
        self.uploader.set_data(self.last_measurement, self.tlt_output, self.transformer_state)
        self.uploader.send_data()
        logger.info("Results uploaded.")


if __name__ == "__main__":
    pass
    # TODO: consider how this is related to the timed rollover defined at the start of this folder
    logging.basicConfig(
    level=logging.DEBUG,  # Set the lowest level to capture all messages
    format='%(levelname)s: %(message)s'
    )

    broker, port, uname, pwd = dio.import_credentials(dio.CREDENTIALS_DIR)
    client = dio.MQTTClient(broker, port, dio.WEATHER_TOPIC, uname, pwd, dio.CERTIFICATE_DIR)
    station = dio.WeatherStationMqtt(client)
    logger.debug(f"Station data: {station.get_data()}")

    # mc_sensor = cio.McSensor('host','port')

    # temperature_sensor = cio.TemperatureSensor("temp", "28-e6ce7d0a6461")

    # w_interval = 10
    # t_interval = 10
    # mc_interval = 10

    # cats = [cio.WeatherStation, cio.TemperatureSensor, cio.McSensor]
    # categories = {i : [cio.SQLiteDb.timestamp_str, cio.SQLiteDb.data_str] for i in cats}

    # db_dir = DB_DIR

    # database = Database(db_dir, categories)
    # database.create_index(cio.TemperatureSensor)
    # database.create_index(cio.McSensor)

    # state_collector = EnvironmentStateCollector(database, station, mc_sensor, temperature_sensor,\
    #                                             w_interval, t_interval, mc_interval)

    # state_collector.start()
    # state_collector.join()
