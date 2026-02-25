import os
import random
import pytest
import time
import sqlite3
from typing import Type
import xml.etree.ElementTree as ET

import device_io.io as cio

# TODO: Maybe make a test that tests that each sensor class has the appropriate measurement_t set.

random.seed(1)  # Fix the seed for test reproducibility.

@pytest.mark.parametrize("directory_existence", [cio.CREDENTIALS_DIR, cio.CERTIFICATE_DIR])
def test_credentials_existence(directory_existence):
    assert os.path.basename(directory_existence) in os.listdir(cio.CERTIFICATE_PATH), f"{directory_existence} can't be found in {cio.CERTIFICATE_PATH}/"

class TTemperatureMsg(cio.TemperatureMeasurement):

    def randomize(self, t:float):
        max_temp = 50
        min_temp = -30
        self.temperature = (max_temp - min_temp) * random.random() + min_temp
        self.time = t
        self.timestamp = self.sensor.stamp_from_datetime(cio.datetime_from_seconds(t))


class TMcSensorMeasurement(cio.McSensorMeasurement):

    def randomize(self, t:float):
        self.time = t
        self.datetimeUTC = self.sensor.stamp_from_datetime(cio.datetime_from_seconds(t))

        for I in [f"I{i + 1}" for i in range(3)]:  # Only current is used in the measurements.
            setattr(self, I, 10 + (2 * random.random() - 1) * 5)

        for I in [f"U{i + 1}" for i in range(3)]:  # Add just in case.
            setattr(self, I, 150 + (2 * random.random() - 1) * 50)

    def to_jsonstr(self):
        root = ET.Element("data")
        prefix = ["I", "U"]
        for p in prefix:
            for I in [f"{p}{i + 1}" for i in range(3)]:  # Only current is used in the measurements.
                val = getattr(self, I)
                child = ET.SubElement(root, self.xml_value_str)
                child.attrib[self.xml_value_ident_str] = I
                child.text = str(val)

        for attr in self.data_attrs:
            val = getattr(self, attr)
            if val is not None: root.attrib[attr] = getattr(self, attr)

        return ET.tostring(root, encoding="unicode")

class TWeatherStationMeasurement(cio.WeatherMeasurement):

    def randomize(self, t: float):
        """Randomize the measurements relevant for Dythera while not exactly physical"""
        self.time = t  # Timestamp from epoch.
        self.timestamp = self.sensor.stamp_from_datetime(cio.datetime_from_seconds(t))
        max_temp = 50
        min_temp = -30
        Ta = (max_temp - min_temp) * random.random() + min_temp
        self.ambient_temperature = Ta
        self.droplet_temperature = Ta
        self.wind_velocity = 10 * random.random()
        self.wind_angle = 360 * random.random()
        self.pressure = 100e3 + (2 * random.random() - 1) * 1e3
        self.rain_rate = 10 * random.random()
        self.humidity = 80 + 10 * (2 * random.random() - 1)
        self.solar_irradiance = 800 + 100 * (2 * random.random() - 1)
        self.electrical_current = 480 + 100 * (2 * random.random() - 1)



@pytest.mark.parametrize("sensor, sensor_msg", [(cio.WeatherStation, TWeatherStationMeasurement),
                                                (cio.TemperatureSensor, TTemperatureMsg),
                                                (cio.McSensor, TMcSensorMeasurement)])
def test_create_single_table_database(tmp_path, sensor, sensor_msg):
    db_dir = str(tmp_path / f"temp.db")

    t = time.time()
    time_delta = 10
    num_entries = 100
    total_duplicates = 10

    cats = [sensor, ]
    categories = {i : [cio.SQLiteDb.timestamp_str, cio.SQLiteDb.data_str] for i in cats}

    database = cio.SQLiteDb(db_dir, categories)
    database.create_index(sensor)

    # Randomly pick which entries to duplicate.
    duplicates = random.sample([i for i in range(num_entries - 1)], total_duplicates)  # num_entries - 1 due to the nature how the loop below creates duplicates

    print("Duplicates", duplicates)

    for i in range(num_entries):
        msg = sensor_msg()
        msg.randomize(t)
        database.write_data(msg)
        if i not in duplicates: t += max(1, time_delta * random.random())

    conn = sqlite3.connect(f"file:{db_dir}?mode=ro", uri=True)        
    
    cursor = conn.cursor()
    read_database = cio.SQLiteDbReader(cursor)

    result = read_database.read_data(sensor)

    assert len(result) == num_entries - total_duplicates


str_weather = '{"timestamp": "2025-05-13T12:58:26Z", "Dn": "000#", "Dm": "000#", "Dx": "000#", "Sn": "0.0#", "Sm": "99.9#", "Sx": "0.0#02", "Ta": "21.7", "Ua": "51.0", "Pa": "957.503", "Rc": "0.00", "Rd": "0", "Ri": "0.0", "Hc": "0.0", "Hd": "0", "Hi": "0.005", "Th": "23.0", "Vh": "0.0", "Vs": "4.9", "Vr": "3.641", "s_irrad": 900.2820086899666}'
str_temp = '{"timestamp": "2025-6-19 14:25:32", "time": 1750335932.0, "temperature": 32}'
str_mc = """<data logId="033310006" app="ML" storeType="measurement" dataProvider="xml001" 
controlUnit="MC033115" deviceType="MC750A Recorder " part="A" datetimeUTC="2022-04-25 
20:52:06" dst="60" tzone=" 60" tInterval="001">
<value ident="U1  " unit="V ">233.18</value>
<value ident="U2  " unit="V ">94.08</value>
<value ident="U3  " unit="V ">94.13</value>
<value ident="I1  " unit="A ">0.0000</value>
<value ident="I2  " unit="A ">0.0000</value>
<value ident="I3  " unit="A ">0.0000</value>
<value ident="P1  " unit="W ">0.0</value>
<value ident="P2  " unit="W ">0.0</value>
<value ident="P3  " unit="W ">0.0</value>
<value ident="Q1  " unit="var ">0.0</value>
<value ident="Q2  " unit="var ">0.0</value>
<value ident="Q3  " unit="var ">0.0</value>
<value ident="E1  " unit="Wh  ">8e+04</value>
<value ident="E2  " unit="Wh  ">18e+04</value>
<value ident="E3  " unit="varh">0e+04</value>
<value ident="E4  " unit="varh">3e+04</value>
</data>"""
@pytest.mark.parametrize("msg_class, jsonstr", [(cio.WeatherMeasurement, str_weather),
                                                (cio.TemperatureMeasurement, str_temp),
                                                (cio.McSensorMeasurement, str_mc)])
def test_parse(msg_class: Type[cio.SensorMeasurement], jsonstr: str):
    msg = msg_class()
    msg.parse(jsonstr)
    new_str = msg.to_jsonstr()
    new_msg = msg_class.from_jsonstr(new_str)

    assert msg == new_msg

