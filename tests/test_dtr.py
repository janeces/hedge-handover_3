import os
import pytest

import device_io.io as cio

import device_io.dythera.io as dio
import device_io.dythera.pb2 as dy_pb
from device_io.dythera.generate_proto import dythera_IEEE_params
from device_io.dythera.config import EXE as DYTHERA_EXE

import device_io.trafoflex.io as tio
import device_io.trafoflex.pb2 as tr_pb
from device_io.trafoflex.generate_proto import configure_test_request
from device_io.trafoflex.config import EXE as TRAFOFLEX_EXE

IEEE_TARGET_TEMP = 80  # Target temperature [degreees C] of the Dythera IEEE IC test.
IEEE_TARGET_TEMP_ERR = 1  # Acceptable absolute error [degreees C] of the Dythera IEEE IC test.

TF_REL_ERR = 0.01  # Acceptable relative error of the results of the Trafoflex test run.

@pytest.mark.parametrize("binary_name", [pytest.param(DYTHERA_EXE, id="dythera"),
                                         pytest.param(TRAFOFLEX_EXE, id="trafoflex")])
def test_binary_existence(binary_name):
    assert os.path.basename(binary_name) in os.listdir(cio.BINARY_PATH), f"{binary_name} can't be found in {cio.BINARY_PATH}/"


class TDytheraIcConfigurator(dio.DytheraIcConfigurator):
    """Used to circumvent the initializer of the parent class."""
    def __init__(self, exe_dir: str, ic_dir: str, results_path: str):
        self._exe_dir = exe_dir
        self._ic_dir = ic_dir
        self._results_path = results_path
        self.env = os.environ.copy()
        self.env["LD_LIBRARY_PATH"] = os.path.dirname(self._exe_dir)
        self.configure_output_folder()

@pytest.mark.dythera
@pytest.mark.dtr_exe
def test_run_dythera(tmp_path):

    # dio.IC_DIR = tmp_path / f"{dio.IC_NAME}.pb"
    # dio.RESULTS_PATH = tmp_path / "dythera_simulation_output"
    # dio.TIME_TO_OVERHEAT_DIR = f"{dio.RESULTS_PATH}/{dio.IC_NAME}{dio.RESULTS_TIME_TO_OVERHEAT_SUFFIX}"
    
    cio.TMP_PATH = str(tmp_path)
    dio.RESULTS_PATH = f"{cio.TMP_PATH}/dythera_simulation_output"  # Folder where Dythera results are output to.
    dio.IC_DIR = f"{cio.TMP_PATH}/{dio.IC_NAME}.pb"  # Folder where the initial conditions for Dythera are written to.
    dio.TIME_TO_OVERHEAT_DIR = f"{dio.RESULTS_PATH}/{dio.IC_NAME}{dio.RESULTS_TIME_TO_OVERHEAT_SUFFIX}"
    
    configurator = TDytheraIcConfigurator(DYTHERA_EXE, dio.IC_DIR, dio.RESULTS_PATH)
    configurator.request = dy_pb.SimulationRequest()
    dythera_IEEE_params(configurator.request)
    configurator.request.output_folder = str(dio.RESULTS_PATH)

    configurator.run_binary()

    temp = -300  # Set something unphysical just in case.
    with open(dio.TIME_TO_OVERHEAT_DIR, "r") as f:
        text = f.read()
        lines = text.split("\n")
        if len(lines[-1]) == 0: lines = lines[:-1]

        temp = float(lines[-1].split(",")[2])

    assert abs(temp - IEEE_TARGET_TEMP) < IEEE_TARGET_TEMP_ERR, \
        f"Dythera IEEE benchmark temperature is {temp} instead of {IEEE_TARGET_TEMP} which is \
          outside the acceptable error range of {IEEE_TARGET_TEMP_ERR}"


class TTrafoflexIcConfigurator(tio.TrafoflexIcConfigurator):
    """Used to circumvent the initializer of the parent class."""
    def __init__(self, trafo_exe_dir:str, ic_dir:str, results_path:str):
        self._exe_dir = trafo_exe_dir
        self._ic_dir = ic_dir
        self._results_path = results_path
        self.env = os.environ.copy()
        self.env["LD_LIBRARY_PATH"] = os.path.dirname(self._exe_dir)

        self.transformer_state = tr_pb.TransformerState()

        self.configure_output_folder()

        self.request = tr_pb.SimulationRequest()
        configure_test_request(self.request)
        self.request.output_folder = tio.RESULTS_PATH


@pytest.mark.trafoflex
@pytest.mark.dtr_exe
def test_run_trafoflex(tmp_path):
    cio.TMP_PATH = str(tmp_path)
    tio.IC_DIR = f"{cio.TMP_PATH}/{tio.IC_NAME}.pb"  # Folder where the initial conditions for Trafoflex are written to.
    tio.RESULTS_PATH = f"{cio.TMP_PATH}/trafoflex_simulation_output"  # Folder where Trafoflex results are output to.
    tio.STATE_DIR = f"{tio.RESULTS_PATH}/{tio.IC_NAME}{tio.OUTPUT_SUFFIX}"  # Directory where the transformer state is stored.

    configurator = TTrafoflexIcConfigurator(TRAFOFLEX_EXE, tio.IC_DIR, tio.RESULTS_PATH)

    configurator.run_binary()

    configurator.get_last_transformer_state()  # Gets the results of the simulaiton.
    ts = configurator.transformer_state
    assert abs((ts.internal_mass_temperatures[0] - 40.7) / 40.7) < TF_REL_ERR, "Internal mass temperature 0 is not at the expected value"
    assert abs((ts.internal_mass_temperatures[1] - 39.794) / 39.794) < TF_REL_ERR, "Internal mass temperature 1 is not at the expected value"
    assert abs((ts.hot_spot_temperature - 44.8924) / 44.8924) < TF_REL_ERR, "Hot spot temperature is not at the expected value"
    assert abs((ts.top_oil_temperature - 39.79446) / 39.79446) < TF_REL_ERR, "Top oil temperature is not at the expected value"
    
