"""
Contains functionality common to both dythera and trafoflex modules. This is sensor and measurement classes,
MQTT client wrapper, SQLite database interface classes and functions to help in development.
"""
import os
import sys
import subprocess
import datetime
import json
import socket
import sqlite3
import threading
import time
import logging
import random  # For varied temperatures of the dummy temperature sensor
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from threading import Lock, Thread, Event
from typing import Type, Any, List
from queue import Queue
# Non-Python external
import paho.mqtt.client as mqtt_client
import serial.rs485 as rs485
# Non-package external
from device_io.external import utils_rs485
# Package
from device_io.config import *

logger = logging.getLogger(__name__)


def import_credentials(cred_dir:str):
    """Import credentials from XML file.
    :param cred_dir: Path to directory containing credentials."""
    tree = ET.parse(cred_dir)
    root = tree.getroot()

    return root.attrib['broker'], int(root.attrib['port']), root.attrib['username'], root.attrib['password']


def get_current_time_utc() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


def datetime_from_seconds(t, tz=datetime.timezone.utc):
    return datetime.datetime.fromtimestamp(t, tz=tz)

@dataclass(init=False)
class ProtobufMeasurement:
    """Measurement data class used for both Trafoflex and Dythera. Sensor measurement objects update these objects with their data."""
    time: float  # Time of the measurement [s].
    ambient_temperature: float  # Ambient temperature [deg C].
    droplet_temperature: float  # Droplet temperature [deg C].
    wind_velocity: float  # Wind velocity [m/s].
    wind_angle: float  # Wind angle [deg].
    pressure: float  # Pressure [Pa].
    rain_rate: float  # Rain rate [mm/h].
    humidity: float  # Relative humidity [%].
    solar_irradiance: float  # Solar irradiance [W/m^2].
    electrical_current: float  # Electrical current [A].

    def __init__(self):
        self.time = -1
        self.ambient_temperature = -274
        self.droplet_temperature = -274
        self.wind_velocity = -1
        self.wind_angle = 361
        self.pressure = -1
        self.rain_rate = -1
        self.humidity = -1
        self.solar_irradiance = -1
        self.electrical_current = -1

    def set_defaults(self):
        """Set some "sensible" default values except for time."""
        self.ambient_temperature = 30
        self.droplet_temperature = 30
        self.wind_velocity = 0
        self.wind_angle = 0
        self.pressure = 1e5
        self.rain_rate = 0
        self.humidity = 50
        self.solar_irradiance = 900
        self.electrical_current = 0

    @classmethod
    def default(cls, t = 0.):
        out = cls()
        out.set_defaults()
        out.time = t
        return out


class Sensor:
    """Abstract class used for collecting sensor data."""
    time_format:str = ""  # String formatting for converting float time into a human-readable date.
    category_name:str = ""  # Name of the category the sensor data belongs to. Used to name SQLite DB entries.
    measurement_t: Type["SensorMeasurement"] = None  # Class that stores the sensor's measurements.

    def get_data(self) -> "SensorMeasurement":
        """Returns the latest measurement of the sensor."""
        pass

    def start(self) -> None:
        """Makes the sensor operational"""
        pass

    @classmethod
    def datetime_from_stamp(cls, stamp:str):
        """Return a datetime object from a string timestamp
        :param stamp: The timestamp string to convert to a datetime object"""
        return datetime.datetime.strptime(stamp, cls.time_format)
    
    @classmethod
    def stamp_from_datetime(cls, dt: datetime.datetime):
        """Return a string timestamp from a datetime object
        :param dt: datetime object to get a stamp from
        """
        return dt.strftime(cls.time_format)
    
    @classmethod
    def timestamp_utc_now(cls) -> str:
        """Get the timestamp for the current time in UTC"""
        return cls.stamp_from_datetime(get_current_time_utc())
            
            
@dataclass(init=False)
class SensorMeasurement:
    """Abstract class to define measurements that are produced by Sensor."""
    time: float | None  # Time at which the measurement was taken in seconds since epoch.
    category_name:str = ""  # Name of the category the sensor data belongs to. Used to name SQLite DB entries.
    sensor: Sensor | None = None  # Sensor class that generates measurements.

    def __init__(self) -> None:
        self.time = None  # UTC time since the epoch in seconds

    def parse(self, string: str):
        """Parses a string to values of SensorMeasurement members
        :param string: String that will be used to set the state of the object."""
        pass

    @classmethod
    def from_jsonstr(cls, jsonstr: str):
        """Creates a SensorMeasurement from a JSON string (actually can be any string
         with the right parse implementation."""
        new = cls(); new.parse(jsonstr)
        return new

    def to_jsonstr(self) -> str:
        """Inverse of parse - serializes the object into a string."""
        pass

    def get_primary_column(self) -> str:
        """Get the value that will be used to index the measurement in the database."""
        pass

    def update_proto(self, proto: ProtobufMeasurement):
        """Update the appropriate protobuf's SimulationRequest Measurement's variables.
        :param proto: ProtobufMeasurement object to update."""
        pass

    def copy(self):
        """Returns a copy of the object."""
        new_obj = self.__class__()
        for attr in self.__dict__.keys():
            setattr(new_obj, attr, getattr(self, attr))
        return new_obj
    
    def copy_obj(self, other:"SensorMeasurement"):
        """Copies the state of other into self.
        :param other: The object to copy the state from into self"""
        for key, val in other.__dict__.items():
            setattr(self, key, val)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.to_jsonstr()}>"


Sensor.measurement_t = SensorMeasurement  # Late assignment of the class variable.


class TemperatureSensor(Sensor):
    """Gets the temperature reading from a temperature probe."""
    time_format = "%Y-%m-%d %H:%M:%S"
    category_name = "temperature"
    label: str  # User-friendly label string.
    name: str  # Name of the sensor in the filesystem.
    meas: "TemperatureMeasurement"  # Last sensor measurement.
    temperature_dir: str  # Full directory of the sensor.

    def __init__(self, name:str, label:str):
        """
        :param name: The name of the sensor as seen in the filesystem
        :param label: A user-friendly label of the sensor
        """
        self.label = label
        self.name = name
        self.temperature_dir = f"{SENSOR_PATH}/{name}/temperature"
        self.meas = TemperatureMeasurement()
    
    def get_temperature(self) -> float:
        """Reads the temperature from a temperature probe."""
        with open(self.temperature_dir, 'r') as f:
            temp = float(f.read()) / TEMP_DENOMINATOR

        self.meas.temperature = temp
        now = get_current_time_utc()
        self.meas.timestamp = self.stamp_from_datetime(now)
        self.meas.time = now.timestamp()

        return self.meas.temperature

    def get_temperature_dummy(self) -> float:
        logger.warning("Using dummy temperature sensor. If you want real data, change the get_data() function of TemperatureSensor.")
        self.meas.temperature = 20 + 2 * random.random()
        now = get_current_time_utc()
        self.meas.timestamp = self.stamp_from_datetime(now)
        self.meas.time = now.timestamp()

        return self.meas.temperature

    def get_data(self) -> "TemperatureMeasurement":
        self.get_temperature()  # TODO: Replace this with the get_temperature function after you are done testing.
        return self.meas.copy()


class TemperatureMeasurement(SensorMeasurement):
    """Measurement produced by the TemperatureSensor class object."""
    category_name = TemperatureSensor.category_name
    sensor = TemperatureSensor
    temperature: float | None  # Temperature in degrees Celsius.
    timestamp: str | None  # String timestamp of the measurement time.

    def __init__(self) -> None:
        super().__init__()
        self.temperature = None
        self.timestamp = None
    
    def parse(self, string: str):
        attrs = json.loads(string)
        for k,v in attrs.items():
            setattr(self, k, v)
    
    def to_jsonstr(self) -> str:
        return json.dumps(self.__dict__)

    def get_primary_column(self) -> str:
        return self.timestamp

    def update_proto(self, proto: ProtobufMeasurement):
        proto.time = self.time
        proto.ambient_temperature = self.temperature
        proto.droplet_temperature = self.temperature


TemperatureSensor.measurement_t = TemperatureMeasurement

class McSensor(Sensor):
    """Abstract McSensor class that can be specified to receive data either through MQTT or network"""
    time_format = "%Y-%m-%d %H:%M:%S"
    category_name = "mc"
    msg_encoding = 'utf-8'
    message_part = "A"  # Part of the message we want to use (specified in the xml data field).
    meas: "McSensorMeasurement"  # Stores the latest state sampled by the sensor.
    temp_meas: "McSensorMeasurement"  # Temporary storage for measurements.
    write_lock: Lock  # Lock used to prevent simultaneous reading and writing.
    first_time: Event  # Prevents reading from the sensor before it has received data.

    def __init__(self) -> None:
        """Initialize the McSensor basics."""
        self.meas = McSensorMeasurement()
        self.temp_meas = McSensorMeasurement()  # Temporary message to hold the data while receiving.
        self.write_lock = Lock()  # Prevents simultaneous reading/writing to the message.
        self.first_time = Event()  # To prevent having the first call to get_data() before the first message is received.

    def get_data(self) -> "McSensorMeasurement":
        self.first_time.wait()
        self.write_lock.acquire()
        data = self.meas.copy()
        self.write_lock.release()
        logger.debug(f"MC timestamp: {self.meas.datetimeUTC}, time: {self.meas.time}")
        return data

    def start(self) -> None:
        """Start listening for connections."""
        pass


class McSensorNet(McSensor):
    """Interface for collecting measurements by the MC device that measures electrical current."""
    xml_end_string = b"</data>"  # End of message string so we can determine when to stop reading from a socket.
    sock: socket.socket  # The socket that listens for MC device messages.
    address: tuple[str, int]  # Host, port socket pair.
    process: Thread  # Parallel thread that listens for socket transmissions.

    def __init__(self, host: str, port: int) -> None:
        """Initialize the McSensor with host and port.
        :param host: Hostname or IP address of the server.
        :param port: Port number of the server.
        """
        super().__init__()
        self.address = (host, port)

        if not TESTING:
            assert type(port) == int, "Port number must be an integer"
            logger.info(f"Connecting to MC device at {host}:{port}")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(self.address)
            self.sock.listen(10)

        self.process = Thread(target=self.dummy_recv if TESTING else self.receive_messages, daemon=True)

    def dummy_recv(self) -> None:
        """A dummy function used for tests when just the input was needed"""
        with open("data/test.xml", 'r') as f:
            self.meas.parse(f.read())

        while True:
            time.sleep(5)
            self.write_lock.acquire()
            now = get_current_time_utc()
            self.meas.datetimeUTC = self.stamp_from_datetime(now)
            self.meas.time = now.timestamp()
            self.write_lock.release()
            self.first_time.set()

    def recv(self) -> None:
        """Waits for messages from the connection."""
        logger.debug(f"Waiting for connection on {self.address}")
        conn, addr = self.sock.accept()
        buffer = b""  # Byte message buffer.

        while True:
            chunk = conn.recv(BUFF_LEN)
            if not chunk:
                logger.debug("Connection closed by the client")
                break  # connection closed

            buffer += chunk

            if self.xml_end_string in buffer:
                logger.debug("End tag found in buffer")
                break  # we've received the full message
        
        self.temp_meas.parse(buffer.decode(self.msg_encoding))
        self.send_response(conn)
        conn.close()

        if self.temp_meas.part == self.message_part:
            logger.debug(f"Writing message:\n{self.temp_meas.xmlstr}")
            logger.debug("Writing message to main object")
            self.write_lock.acquire()

            self.meas.copy_obj(self.temp_meas)  # Copy the temporary message to the main message object
            self.meas.time = self.datetime_from_stamp(self.meas.datetimeUTC).timestamp()

            self.write_lock.release()
            self.first_time.set()

    def receive_messages(self) -> None:
        """Continuously receive messages from the socket and update the message object."""
        while True:
            try:
                self.recv()
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                time.sleep(1)

    def create_response(self) -> str:
        """Create the response sent back to the MC device to acknowledge message reception."""
        now = get_current_time_utc()
        timestamp_high = self.stamp_from_datetime(get_current_time_utc())
        timestamp_low = f":{(now.microsecond // 1000):03d}"
        return rf'<ack logId="{self.temp_meas.logId}" datetimeUTC="{timestamp_high + timestamp_low}" deviceID="{self.temp_meas.get_deviceID()}" />'

    def send_response(self, conn:socket.socket):
        """Sends a response to the client.
        :param conn: Connection to send the response over"""
        response = self.create_response()
        logger.debug(f"Sending response: {response}")
        conn.send(response.encode(self.msg_encoding))

    def start(self) -> None:
        """Start listening for connections."""
        self.process.start()

    def join(self) -> None:
        """Finalize listening for connections."""
        self.process.join()


class McSensorMeasurement(SensorMeasurement):
    """Measurement produced by the McSensor class object"""
    data_attrs = ['logId', 'app', 'storeType', 'dataProvider', 'controlUnit', 'deviceType',
                        'part', 'datetimeUTC', 'dst', 'tzone', 'tInterval']  # Attributes of the data element.
    value_attrs = ['U1', 'U2', 'U3', 'I1', 'I2', 'I3', 'P1', 'P2', 'P3', 'Q1', 'Q2', 'Q3',
                        'E1', 'E2', 'E3', 'E4']  # Attributes of value elements.
    xml_value_str = "value"  # Value of the XML tag that denotes a measurement value
    xml_value_ident_str = "ident"  # Value of the XML attribute that describes the measurement value type
    category_name = McSensor.category_name
    sensor = McSensor
    logId:str; app:str; storeType:str;dataProvider:str;controlUnit:str
    deviceType:str;part:str;datetimeUTC:str;dst:str;tzone:str;tInterval:str
    U1:float;U2:float;U3:float;I1:float;I2:float;I3:float
    P1:float;P2:float;P3:float;Q1:float;Q2:float;Q3:float
    P1:float;P2:float;P3:float;P4:float
    xmlstr:str  # XML string that contains data about class attributes

    def __init__(self) -> None:
        
        self.xmlstr = ""

        for attr in self.data_attrs:
            setattr(self, attr, None)
        
        for attr in self.value_attrs:
            setattr(self, attr, None)
        
        self.time = None

    def parse(self, string:str):
        root = ET.fromstring(string)
        self.xmlstr = string.replace("\r", "\n") # MC device terminates lines with "\r" instead of "\n".

        for attr in self.data_attrs:
            if attr in root.attrib:
                setattr(self, attr, root.attrib[attr])
            else:
                setattr(self, attr, None)

        for child in root:
            if child.tag == self.xml_value_str:
                ident = child.attrib[self.xml_value_ident_str].strip()
                if ident in self.value_attrs:
                    try:
                        value = float(child.text)
                    except TypeError:
                        # logger.debug(f"Could not convert value for {ident} to float. Setting to None.")
                        value = None
                    setattr(self, ident, value)
                else:
                    pass
                    # logger.debug(f"Unknown value identifier: {ident}")
            else:
                pass
                # logger.debug(f"Unknown tag: {child.tag}")
        now = time.time()
        mc_time = self.sensor.datetime_from_stamp(self.datetimeUTC).timestamp()
        if mc_time > now: logger.warning(f"McSensor measurement time {mc_time} exceeded current time {now}, setting time to now.")
        self.time = mc_time if mc_time < now else now  # TODO Fix this to only mc_time once you are done with testing

    def get_primary_column(self) -> str:
        return self.datetimeUTC
    
    def to_jsonstr(self) -> str:
        return self.xmlstr

    def get_deviceID(self) -> str:
        """Maps from the controlUnit attribute to the deviceID used in the response."""
        return self.controlUnit

    def update_proto(self, proto: ProtobufMeasurement):
        proto.time = self.time
        proto.electrical_current = (self.I1 + self.I2 + self.I3) / 3

McSensorNet.measurement_t = McSensorMeasurement
McSensor.measurement_t = McSensorMeasurement


class MQTTClient:
    """A convenience class to simplify MQTT message handling"""
    broker: str  # MQTT broker.
    port: int  # Broker port.
    topic: str  # MQTT topic.
    username: str  # MQTT user.
    password: str  # MQTT user password.
    certificate_dir: str  # Directory of the MQTT certificate file.
    client: mqtt_client.Client  # Underlying MQTT client.
    publish_queue: list[mqtt_client.MQTTMessageInfo]  # Stores sent message statuses.

    def __init__(self, broker:str, port:int, topic:str, username:str, password:str, certificate_dir:str):
        """
        :param broker: MQTT broker
        :param port: Broker port
        :param topic: MQTT topic
        :param username: MQTT user
        :param password: MQTT user password
        :param certificate_dir: Directory of the MQTT certificate file
        """
        self.broker = broker
        self.port = port
        self.topic = topic
        self.username = username
        self.password = password
        self.certificate_dir = certificate_dir
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(self.username, self.password)
        self.client.tls_set(ca_certs=certificate_dir)
        self.set_on_connect(self.on_connect_default)
        self.publish_queue = []

    def connect(self, wait=-1) -> None:
        """Connect to the topic
        :param wait: Wait time in seconds if the connection is lost. If negative, exit."""
        while True:
            try:
                val = self.client.connect(self.broker, self.port)
                logger.debug(f"MQTT topic {self.topic} connection value: {val}")
                break
            except Exception as e:
                if wait > 0:
                    logger.warning(f"Failed to connect to {self.broker}:{self.port}: {e}. Sleeping for {wait} seconds.")
                    time.sleep(wait)
                else:
                    logger.error(f"Failed to connect to {self.broker}:{self.port}: {e}. Exiting.")
                    sys.exit(1)

    def set_on_connect(self, on_connect) -> None:
        self.client.on_connect = on_connect

    def set_on_message(self, on_message) -> None:
        self.client.on_message = on_message

    def set_on_publish(self, on_publish) -> None:
        self.client.on_publish = on_publish

    def set_userdata(self, userdata) -> None:
        self.client.user_data_set(userdata)

    def start_loop(self):
        return self.client.loop_start()
    
    def stop_loop(self) -> None:
        self.client.loop_stop()

    def publish(self, data:str) -> None:
        """Publish message
        :param data: String to set as a message"""
        self.publish_queue.append(self.client.publish(self.topic, data, qos=PUBLISH_QOS))

    def wait_publish(self) -> None:
        """Wait for all published messages to be received"""
        for i,m in enumerate(self.publish_queue):
            m.wait_for_publish(timeout=PUBLISH_TIMEOUT)
            self.publish_queue.pop(i)

    def on_connect_default(self, client, userdata, flags, rc, properties) -> None:
        """The default callback when a connection is established. The signature corresponds to the standard paho.mqtt
        signature."""
        if rc == mqtt_client.CONNACK_ACCEPTED:
            logger.info(f"Successfully connected to {self.topic}.")
            client.subscribe(self.topic)
        else:
            logger.error(f"Connection failed with code {rc}")


class McSensorMqtt(McSensor):
    """Implements receiving of MC messages over MQTT."""
    client: MQTTClient  # MQTT client to use to set the current state.
    controlUnit: str   # Name of the control unit we want to receive messages from.
    restart_sleep = 20  # Time to wait before trying to connect to the topic again. [s]

    def __init__(self, client: MQTTClient, control_unit):
        """Obtains MC sensor measurements over MQTT for a specified control unit.
        :param client: MQTT client
        :param control_unit: Control unit of measurement"""
        super().__init__()
        self.controlUnit = control_unit
        self.client = client
        self.client.set_on_message(self.store_msg)
        logger.info(f"Connecting to {self.client.broker}:{self.client.port} on topic {self.client.topic}")
        self.client.connect(self.restart_sleep)

    def start(self):
        self.client.start_loop()

    def store_msg(self, client, userdata, msg) -> None:
        """Thread safe storage of MC measurement received over MQTT. Signature is standard for paho.mqtt"""
        self.temp_meas.parse(msg.payload.decode())
        if self.temp_meas.controlUnit == self.controlUnit and self.temp_meas.part == self.message_part:
            self.write_lock.acquire()
            self.meas.copy_obj(self.temp_meas)
            self.first_time.set()
            self.write_lock.release()


class WeatherStation(Sensor):
    """Base class for the collecting data from a weather station."""
    time_format = "%Y-%m-%dT%H:%M:%SZ"
    timestamp_str = "timestamp"
    category_name = "weather"
    meas: "WeatherMeasurement"  # Internal state of the sensor.
    meas_tmp: "WeatherMeasurement"  # Temporary storage for the internal state.
    used_values: list[str] = [timestamp_str]  # List of WeatherMeasurement attributes that are actually by the DTR software.

    def __init__(self):
        self.meas = WeatherMeasurement()
        self.meas_tmp = WeatherMeasurement()

    def check_used_values(self) -> bool:
        """Checks whether all values that are needed are present in the measurement."""
        return None not in [getattr(self.meas_tmp, i) for i in self.used_values]

    def report_missing_values(self):
        none_list = [i for i in self.used_values if getattr(self.meas_tmp, i) is None]
        logger.warning(f"Skipping the measurement due to {' '.join(none_list)} being invalid.")


class WeatherStationLocal(WeatherStation):
    """Collects weather station data over the device's serial port"""
    combined_data_str = "0R"  # Command to communicate to a sensor to send all data.
    comm: rs485.RS485  #  RS485 communication port.
    split_char:dict[str, str] = {}  # Characters that split the numerical value and metadata.
    response_sleep = 0.1  # Sleep time before reading the response.

    def __init__(self):
        super().__init__()

    def start(self):
        self.comm = utils_rs485.init_rs485_communication()

    def parse(self, message: str, timestamp: str):
        """Parses the message received over the serial port
        :param message: Message received over the serial port
        :param timestamp: Human-readable timestamp of the time at which the message was received"""
        parsed = message.replace('\r','').replace('\n','')
        logger.warning("Solar irradiance set to 0 due to missing simulated data. Results might be invalid.")
        meas_dct = {self.timestamp_str: timestamp, "s_irrad": -1}
        for e in parsed.split(','):
            if '=' in e:
                k,v = e.split('=')
                if k in self.used_values and '#' not in v:
                    meas_dct[k] = v.split(self.split_char[k])[0]

        self.meas_tmp.parse(json.dumps(meas_dct), from_sensor=True)

        if self.check_used_values():
            self.meas.copy_obj(self.meas_tmp)
        else:
            self.report_missing_values()

    def get_data(self) -> "WeatherMeasurement":
        utils_rs485.write_command(self.comm, self.combined_data_str)
        msg = utils_rs485.read_response_1(self.comm, sleep_time=self.response_sleep)

        stamp = self.timestamp_utc_now()

        self.parse(msg, stamp)

        return self.meas.copy()


class WeatherStationMqtt(WeatherStation):
    """Collects data from a weather station over MQTT."""
    client: MQTTClient  # MQTTClient that listens on the WEATHER_TOPIC.
    restart_sleep = 20  # Time to wait before trying to connect to the topic again. [s]
    write_lock: Lock  # Lock used to prevent simultaneous reading and writing.
    first_time: Event  # Prevents reading from the sensor before it has received data.

    def __init__(self, client:MQTTClient):
        """Constructor for the WeatherStationMqtt class.
        :param client: MQTT client"""
        super().__init__()
        self.lock = Lock()
        self.first_time = Event()  # To prevent having the first call to get_data() before the first message is received
        self.client = client
        self.client.set_on_message(self.store_msg)
        logger.info(f"Connecting to {self.client.broker}:{self.client.port} on topic {self.client.topic}")
        self.client.connect(self.restart_sleep)

    def start(self):
        self.client.start_loop()
        
    def store_msg(self, client, userdata, msg) -> None:
        """Thread safe storage of weather data received over MQTT. Signature is standard for paho.mqtt"""
        self.meas_tmp.parse(msg.payload.decode(), from_sensor=True)
        # If the used_values are specified, check if all are present, otherwise don't update the state.
        if self.check_used_values():
            self.lock.acquire()
            self.first_time.set()
            self.meas.copy_obj(self.meas_tmp)
            self.lock.release()
        else:
            self.report_missing_values()

    def get_data(self) -> "WeatherMeasurement":
        self.first_time.wait()
        self.lock.acquire()
        data = self.meas.copy()
        self.lock.release()
        return data


class WeatherMeasurement(SensorMeasurement):
    """Measurement produced by the WeatherStation class object."""
    timestamp_str = WeatherStation.timestamp_str
    attrs = [timestamp_str, "time", 'Dn', 'Dm', 'Dx', 'Sn', 'Sm', 'Sx', 'Ta', 'Tp', 'Ua', 'Pa', 'Rc', 'Rd', 'Ri',\
             'Hc', 'Hd', 'Hi', 'Rp', 'Hp', 'Tr', 'Ra', 'Sl', 'Rt', 'Sr', 'Th', 'Vh', 'Vs', 'Vr', 's_irrad']
    important_attrs = ["Sm", "Dm", "Pa", "Ri", "Ua"]  # Attributes relevant to DTR.
    sensor = WeatherStationMqtt
    category_name = sensor.category_name
    timestamp: str  # A human-readable timestamp [s].
    Dn:float  # Wind direction, minimum [Degrees] Min over averaging period.
    Dm:float  # Wind direction, average [Degrees] Usually over 1-10 minutes.
    Dx:float  # Wind direction, maximum [Degrees] Max over averaging period.
    Sn:float  # Wind speed, minimum [m/s] Min wind speed during period.
    Sm:float  # Wind speed, average [m/s] Usually over 1-10 minutes.
    Sx:float  # Wind speed, maximum [m/s] Peak gust.
    Ta:float  # Air temperature [°C].
    Tp:float  # Dew point temperature [°C].
    Ua:float  # Relative humidity [%].
    Pa:float  # Atmospheric pressure [Pa].
    Rc:float  # Rainfall accumulation [mm] Since last report or interval.
    Rd:float  # Rainfall duration [s] How long it rained.
    Ri:float  # Rainfall intensity [mm]/h Calculated rate.
    Hc:float  # Hail accumulation [hits/cm²] If hail sensor active.
    Hd:float  # Hail duration [s] How long hail occurred.
    Hi:float  # Hail intensity [hits/cm²h] Hail rate.
    Rp:float  # Rain peak intensity [mm/h] Highest rain rate during interval.
    Hp:float  # Hail peak intensity [hits/cm²h] Highest hail rate during interval.
    Tr:str  # Time of rain start [hhmmss].
    Ra:float  # Total rainfall [mm].
    Sl:Any  # Status of liquid sensor —.
    Rt:float  # Rain event time [s].
    Sr:float  # Heating status [%] or flag.
    Th:float  # Internal temperature [°C].
    Vh:float  # Heater supply voltage [V].
    Vs:float  # Supply voltage [V].
    Vr:float  # Reference voltage [V].
    s_irrad:float  # Solar irradiance [w/m^2].
    
    def __init__(self) -> None:
        super().__init__()
        for attr in self.attrs:
            setattr(self, attr, None)

    def parse(self, string:str, from_sensor=False):
        """Parses object serialized as a JSON string.
        :param string: Object serialized as a JSON string
        :param from_sensor: Whether the JSON string was obtained by reading a sensor state."""
        dct = json.loads(string)

        for attr in self.attrs:
            # Check if the attribute exists in the dictionary and if the value is valid
            if attr == self.timestamp_str:
                setattr(self, attr, dct[attr])
            elif attr in dct:
                try:
                    val = float(dct[attr])
                    if attr == 'Pa' and from_sensor: val *= 100 # Convert from hPa to Pa
                except (ValueError, TypeError):
                    if attr in self.important_attrs:
                        logger.debug(f"Attribute {attr} = {dct[attr]} could not be converted to float")
                    val = None
                                
                setattr(self, attr, val)
            else:
                setattr(self, attr, None)
        
        self.time = WeatherStationMqtt.datetime_from_stamp(self.timestamp).timestamp()

    def get_primary_column(self) -> str:
        return self.timestamp

    def to_jsonstr(self) -> str:
        return json.dumps(self.__dict__)

    def update_proto(self, proto: ProtobufMeasurement):
        proto.time = self.time
        proto.ambient_temperature = self.Ta
        proto.droplet_temperature = self.Ta
        proto.wind_velocity = self.Sm
        proto.wind_angle = self.Dm
        proto.pressure = self.Pa
        proto.rain_rate = self.Ri
        proto.humidity = self.Ua
        proto.solar_irradiance = self.s_irrad

# Assign some class variables after the measurement definition.
WeatherStation.measurement_t = WeatherMeasurement


class SQLiteDbReader:
    """A simple class that is capable of reading data from a SQLite database."""
    timestamp_str = "timestamp"  # Name of the timestamp column in the table.
    data_str = "data"  # Name of the data column in the table.
    metadata = "metadata"  # Name of the metadata table.
    meta_keyvalue = ["key", "value"]  # Name of metadata table columns.
    cursor: sqlite3.Cursor  # Database cursor.

    def __init__(self, cursor: sqlite3.Cursor):
        """:param cursor: Cursor used for reading the database."""
        self.cursor = cursor

    def read_data(self, cls: Type[Sensor]):
        """
        Reads data from a certain sensor
        :param cls: Sensor child class to read the data from
        :return: List of measurements from the sensor type
        """
        db_out = self.cursor.execute(f"SELECT {self.timestamp_str}, {self.data_str} FROM \
                                   {cls.category_name} ORDER BY {self.timestamp_str}").fetchall()
        return [cls.measurement_t.from_jsonstr(d[1]) for d in db_out]
    
    def read_metadata(self, key: str):
        """
        Read from the metadata table of the database.
        :param key: The key to the value we want to retireve
        """
        res = self.cursor.execute(f"SELECT {self.meta_keyvalue[1]} FROM {self.metadata} WHERE \
                                  {self.meta_keyvalue[0]} = ?", (key,))
        output = res.fetchone()
        return None if (output is None) else output[0]


class SQLiteDb(SQLiteDbReader):
    """Class that enables interface with the database and generalized writing to it from sensors"""
    cutoff = {"days": 0, "minutes": 60}  # Determines how old measurements have to be, to be removed from the database.
    # Keys are {days, minutes, seconds} (arguments for datetime.timedelta)
    # TODO: change "cutoff" to some sensible values when you are done testing.
    time_index_name = "time"  # The name of the index which indexes tables by the "timestamp" column
    last_vacuum = "last_vacuum"  # Name of the metadata key for the last vacuum time.
    journal_mode = "journal_mode"  # Makes sure that journal_mode is set to WAL only once.
    wal_mode = "WAL"  # SQL database writing mode that permits stable multiple parallel readers and a single writer.
    db_dir: str  # Directory of the database.
    cleanup_period: int  # Period in seconds when the database should be vacuumed.
    categories: dict[Type[Sensor], list[str]]  # Dictionary of sensor class keys and list of table measurement columns.
    conn: sqlite3.Connection  # Connection to the SQLite database.
    last_vacuum_time: int  # The last time the database was vacuumed in seconds since epoch.

    def __init__(self, db_dir:str, categories:dict[Type[Sensor], list[str]], cleanup_period=-1):
        """
        :param db_dir: Directory of the database
        :param categories: A dict of keys (Sensor.catogory_name) and values which are either timestamp_str or data_str
        :param cleanup_period: Period in seconds when the database should be vacuumed
        """
        logger.info(f"Initializing database at {db_dir}.")
        self.db_dir = db_dir
        self.conn = sqlite3.connect(self.db_dir)
        super().__init__(self.conn.cursor())
        self.cleanup_period = cleanup_period
        self.categories = categories
        # Create metadata table.
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.metadata} ({self.meta_keyvalue[0]} \
                            TEXT PRIMARY KEY, {self.meta_keyvalue[1]})")

        if not self.read_metadata(self.journal_mode):
            self.cursor.execute("PRAGMA journal_mode=WAL")
            self.write_metadata(self.journal_mode, self.wal_mode)

        # Separate tables for every sensor.
        for key, value in self.categories.items():
            N = len(value)
            self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {key.category_name} (" +\
                                "".join([(f"{value[i]} " + 
                                ("PRIMARY KEY" if value[i] == self.timestamp_str else "TEXT NOT NULL")\
                                + (", " if (i < N - 1) else "") ) for i in range(N)]) + ")")
            self.create_index(key)
            
        self.last_vacuum_time = int(time.time())
        self.write_metadata(self.last_vacuum, self.last_vacuum_time, overwrite=False)
        self.last_vacuum_time = self.read_metadata(self.last_vacuum)

        self.conn.commit()
        logger.info("Database initialized.")

    def write_data(self, data: SensorMeasurement):
        """Write data from a measurement to the database. Skip entries with the same timestamp.
        :param data: Measurement to write"""
        self.cursor.execute(f"INSERT INTO {data.category_name} ({self.timestamp_str}, {self.data_str})\
                             VALUES (?, ?) ON CONFLICT({self.timestamp_str}) DO NOTHING",
                             (data.get_primary_column(), data.to_jsonstr()))

        self.conn.commit()

    def write_metadata(self, key: str, value, overwrite=True):
        """
        Write to the metadata table
        :param key: Key of the value
        :param value: Value to be stored
        :param overwrite: Whether to overwrite a preexisting value in the table
        """
        insert_word = "REPLACE" if overwrite else "INSERT"
        conflict_word = "" if overwrite else f" ON CONFLICT({self.meta_keyvalue[0]}) DO NOTHING"
        self.cursor.execute(f"{insert_word} INTO {self.metadata} ({self.meta_keyvalue[0]}, {self.meta_keyvalue[1]})\
                             VALUES (?, ?){conflict_word}", (key, value))
        self.conn.commit()

    def remove_old_entries(self, cls: Type[Sensor]):
        """
        Remove old entries from the table belonging to a sensor.
        :param cls: Class of a sensor for which to remove database entries
        """
        logger.info("Removing old entries.")
        cut_time = get_current_time_utc() - datetime.timedelta(**self.cutoff) 
        cutoff = cls.stamp_from_datetime(cut_time)

        self.cursor.execute(f"DELETE FROM {cls.category_name} WHERE {self.timestamp_str} < ?", (cutoff,))

        self.conn.commit()
        logger.info("Old entries removed")

    def create_index(self, cls: Type[Sensor]):
        """
        Create an index for sensor measurements for faster lookup.
        :param cls: Class of sensor to create the index for
        """
        self.cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {self.time_index_name} ON {cls.category_name} ({self.timestamp_str})")
        self.conn.commit()

    def cleanup(self) -> None:
        """Remove old database entries"""
        logger.info("Performing database cleanup.")

        self.update_last_vacuum_time()
        for c in self.categories: self.remove_old_entries(c)
        if 0 < self.cleanup_period < (time.time() - self.last_vacuum_time): self.vacuum()

        logger.info("Cleanup complete.")
        
    def update_last_vacuum_time(self) -> None:
        self.last_vacuum_time = self.read_metadata(self.last_vacuum)

    def vacuum(self) -> None:
        """Vacuum the database"""
        self.cursor.execute("VACUUM")
        self.last_vacuum_time = int(time.time())
        self.write_metadata(self.last_vacuum, self.last_vacuum_time)
        self.conn.commit()


class StateCollector:
    """Collection of sensor data and writing to the database."""
    database: SQLiteDb  # Database to store the sampled data.
    sensors: List[Sensor]  # List of sensors to sample.
    sample_intervals: dict[Sensor, float]  # Interval between two sensor samplings [s].
    sensor_threads: list[threading.Thread]  # Parallel threads that sample the sensors.
    queue: Queue  # Queue to which parallel threads write sensor measurements to.
    def __init__(self, database: SQLiteDb, sensors: list[tuple[Sensor, float]], max_queue_size: int, check_cleanup_period) -> None:
        """Initialize the state collector that collects data from sensors and writes them to the database.
        :param database: SQLiteDb instance
        :param sensors: List of sensors-sampling_frequency pairs to collect data from. Frequency is in seconds.
        :param max_queue_size: Maximum size of the queue the sensors write to.
        :param check_cleanup_period: Period in terms of the number of database entries when the database is checked for cleanup."""
        self.database = database
        self.sensors = [i[0] for i in sensors]
        self.sample_intervals = {i[0]: i[1] for i in sensors}
        self.queue = Queue(maxsize=max_queue_size)

        self._check_cleanup_period = check_cleanup_period

        self.sensor_threads = [threading.Thread(target=self.sample_sensor, args=(s,), daemon=True) for s in self.sensors]

    def sample_sensor(self, sensor: Sensor):
        """Samples the current state of the sensor and writes it to the queue.
        :param sensor: Sensor to sample"""
        while True:
            self.queue.put(sensor.get_data())
            time.sleep(self.sample_intervals[sensor])

    def store_data(self):
        """Writes the data from the queue into the database."""
        count = 0
        while True:
            data: SensorMeasurement = self.queue.get()
            logger.info(f"Received data at time {data.time} from {data.category_name}")

            self.database.write_data(data)

            if count % self._check_cleanup_period == 0:
                logger.info("Starting database cleanup")
                self.database.cleanup()
                logger.info(f"Cleaned up data at time {data.time}")

            count += 1

    def start(self) -> None:
        """Start parallel sensor reading and database writing."""
        logger.debug("Starting data collection")
        for s in self.sensors: s.start()  # Start sensors.
        for t in self.sensor_threads: t.start()  # Start threads.
        logger.debug("Data collection started")

        self.store_data()  # Is blocking since processes with sqlite3 can't be launched in a separate thread.

    def join(self):
        """Conclude the parallel sensor reading and database writing."""
        for t in self.sensor_threads: t.join()
        logger.info(f"Data collection finished")


class IcConfigurator:
    """Abstract class for the class that handles generation of initial condition files and runs the relevant binary"""
    env: dict[str, str]  # Dictionary of environment variables.
    database: SQLiteDbReader  # Database from which the initial condition data will be read from.
    conn: sqlite3.Connection  # Connection to the database.
    uploader: "UploadResponse"  # Uploader object which uploads results over MQTT.
    sensors: list[Type[Sensor]]  # List of sensor types which provide the measurements.
    request: Any  # Protobuffer simulation request.
    _results_path: str; _ic_dir: str; _exe_dir: str
    last_measurement: ProtobufMeasurement | None  # Last measurement used in the SimulationRequest.

    def __init__(self, exe_dir: str, db_dir: str, uploader: "UploadResponse", results_path: str, ic_dir: str):
        """Initializes the IcConfigurator class.
        :param exe_dir: Path to the DTR executable
        :param db_dir: Path to the SQLite database
        :param uploader: UploadResponse object to communicate results
        :param results_path: Path to the result output file
        :param ic_dir: Path to the initial condition file"""
        self._exe_dir = exe_dir
        self.env = os.environ.copy()
        self.env["LD_LIBRARY_PATH"] = os.path.dirname(self._exe_dir)

        self.uploader = uploader
        self.database_setup(db_dir)
        self._results_path = results_path
        self._ic_dir = ic_dir
        self.initialize_request()
        self.configure_output_folder()

    def database_setup(self, db_dir) -> None:
        """Set up the database in read-only mode.
        :param db_dir: Path to the SQLite database"""
        try:
            self.conn = sqlite3.connect(f"file:{db_dir}?mode=ro", uri=True)
        except sqlite3.OperationalError:
            logger.error("Failed to connect to the database. Exiting")
            sys.exit()

        self.database = SQLiteDbReader(self.conn.cursor())

    def parse_data(self):
        """Collect the measurements from the database."""

        out: list[list[SensorMeasurement]] = []

        for sensor in self.sensors:
            out.append(self.database.read_data(sensor))

            if len(out[-1]) == 0:
                logger.error(f"No measurements found for {sensor.category_name}. Exiting.")
                sys.exit(1)

        return out

    def configure_output_folder(self) -> None:
        """Create the folder for results if it doesn't exist."""
        if os.path.isdir(self._results_path):
            logger.debug(f"{self._results_path} exists")
        else:
            os.makedirs(self._results_path)
            logger.debug("Created simulation output directory")

    def set_output_folder(self, folder:str):
        """:param folder: Folder to output the results to"""
        self.request.output_folder = folder

    def write_request(self, filename:str):
        """Write the request to a file.
        :param filename: Name of the file to write the request to"""
        with open(filename, "wb") as f:
            f.write(self.request.SerializeToString())

    def run_binary(self) -> None:
        """Run the simulation."""
        self.write_request(self._ic_dir)
        subprocess.run([f"{self._exe_dir}", self._ic_dir], env=self.env)

    def initialize_request(self):
        """Initialize the request to run the simulation."""
        pass

    def compute_ampacity(self):
        """Compute the "ampacity" for the DTR object"""
        pass

    def get_pb_measurement(self) -> Any:
        """Gets the protobuffer Measurement from the simulation request."""
        pass

    def add_measurement(self, proto: ProtobufMeasurement):
        """Add a measurement to the SimulationRequest protobuffer message.
        :param proto: ProtobufMeasurement parameter set"""
        measurement = self.get_pb_measurement()
        measurement.time = proto.time  # Timestamp from epoch.
        measurement.ambient_temperature = proto.ambient_temperature
        measurement.droplet_temperature = proto.droplet_temperature
        measurement.wind_velocity = proto.wind_velocity
        measurement.wind_angle = proto.wind_angle
        measurement.pressure = proto.pressure
        measurement.rain_rate = proto.rain_rate
        measurement.humidity = proto.humidity
        measurement.solar_irradiance = proto.solar_irradiance
        measurement.electrical_current = proto.electrical_current

    def collect_measurements(self, *args, **kwargs) -> None:
        """Collect measurements and assemble them into protobuffer MeasurementPoints."""
        pass

    def upload_results(self):
        """Upload the results to the MQTT topic."""
        pass


class UploadResponse:
    """Abstract class for uploading ampacity results over MQTT"""
    msg_attrs = ["ts", "device_id", "ambient_temp", "time_to_overheat"]  # Attributes to send as a message.
    device_id: str  # Unique identifier of the GW IotMaxx device.
    client: MQTTClient  # MQTTClient object that sends the results over MQTT.
    time: float  # Time of the reuslts [s] since epoch.
    ts: str  # Timestamp of the results.
    ambient_temp: float  # Ambient temperature [deg C].
    time_to_overheat: float  # Time to overheat the DTR element [s].

    def __init__(self, device_id:str):
        """:param device_id: Unique identifier of the GW IotMaxx device"""
        self.device_id = device_id
        broker, port, uname, pwd = import_credentials(CREDENTIALS_DIR)
        self.client = MQTTClient(broker, port, UPLOAD_TOPIC, uname, pwd, CERTIFICATE_DIR)
        self.client.connect()
        self.client.start_loop()
    
    def set_data(self, *args) -> None:
        """Set the data of the msg_attrs.
        :param args: Arguments needed for setting data"""
        pass

    def create_msg(self) -> str:
        """Create the message to send over MQTT"""
        return json.dumps({i: getattr(self, i) for i in self.msg_attrs})
    
    def set_timestamp(self, t: float) -> None:
        """
        Set the timestamp of the message.
        :param t: Time in seconds since epoch to set the message timestamp
        """
        dt = datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc)
        self.ts = dt.strftime(MQTT_TIME_FORMAT_OUT)

    def send_data(self) -> None:
        """Send the message over MQTT."""
        msg = self.create_msg()
        logger.debug(f"Uploader sending data:\n{msg}")
        #self.client.publish(msg.encode())  # TODO: check if this receives correctly. Apparently should be string
        self.client.publish(msg)  # TODO: check if this receives correctly. Apparently should be string
        logger.debug("Data sent")
        self.client.wait_publish()
        logger.debug("Data confirmed published.")


def run_data_collection(sensors: list[tuple[Sensor, float]], db_dir: str, check_cleanup_period: int, max_queue_size:int):
    """Establish data collection for the DTR application.
    :param sensors: List of (sensor, sensor sampling interval) tuples
    :param db_dir: Path to the SQLite database
    :param check_cleanup_period: How often to check for data cleanup in terms the number of database entries
    :param max_queue_size: Maximum number of entries to store in the database entry queue"""
    categories = {type(i[0]): [SQLiteDb.timestamp_str, SQLiteDb.data_str] for i in sensors}

    database = SQLiteDb(db_dir, categories, check_cleanup_period)

    state_collector = StateCollector(database, sensors, max_queue_size, check_cleanup_period)

    state_collector.start()
    state_collector.join()


def connection_listener(topic: str) -> None:
    """Used to verify successful uploads in development."""
    broker, port, uname, pwd = import_credentials(CREDENTIALS_DIR)
    client = MQTTClient(broker, port, topic, uname, pwd, CERTIFICATE_DIR)

    def on_msg(client, userdata, msg):
        logger.debug(f"Message: {msg.payload.decode()}")

    def on_connect(client, userdata, flags, rc, properties):
        if rc == mqtt_client.CONNACK_ACCEPTED:
            logger.info(f"Successfully connected to {topic}.")
            client.subscribe(topic)
        else:
            logger.error(f"Connection failed with code {rc}")

    client.set_on_message(on_msg)
    client.set_on_connect(on_connect)

    logger.info(f"Connecting to {client.broker}:{client.port} on topic {client.topic}")
    client.connect()
    client.client.loop_forever()


if __name__ == "__main__":
    logging.basicConfig(
    level=logging.DEBUG,  # Set the lowest level to capture all messages
    format='%(levelname)s: %(message)s'
    )

    #check_output()
    #create_input()
    # ts = TemperatureSensor("28-e6ce7d0a6461", "test")
    # print(ts.get_temperature())

    #test_mqtt()
    
    # broker, port, uname, pwd = import_credentials(CREDENTIALS_DIR)
    # client = MQTTClient(broker, port, WEATHER_TOPIC, uname, pwd, CERTIFICATE_DIR)
    # station = WeatherStation(client)


    # categories = {WeatherStation.category_name : [SQLiteDb.timestamp_str, SQLiteDb.data_str]}

    # db = SQLiteDb("tmp/dtr/database.db", categories)


    # db.update_last_vacuum_time()
    # print(db.last_vacuum_time)
    # db.vacuum()
    # db.update_last_vacuum_time()
    # print(db.last_vacuum_time)

    # for i in range(10):
    #     time.sleep(3)
    #     print(i)
    #     msg = station.get_data()
    #     db.write_data(msg)
    
    # wdata = db.read_data(WeatherStation)

    # for w in wdata: print(w[0], w[1])

    # wdata = db.read_weather()
    # for w in wdata: print(w[0], json.loads(w[1]))

    # # print(station.get_data().__dict__)


