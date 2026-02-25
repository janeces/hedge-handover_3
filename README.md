# About

This code is meant to run on the IotMaxxGW device so some absolute paths reflect that. Its purpose is to:
- Collect data from sensors (over MQTT, local file IO)
- Construct initial condition (IC) files for Trafoflex and Dythera
- Run Trafoflex and Dythera
- Forward the produced results to Sumo

# Details

The extended description of the implementation is contained in the [detailed description](docs/detailed_description.md), but here is a short overview.

## Code

Broadly, this code has to parts: 
- The first one collects data from sensors and stores them in a SQLite database. This script runs constantly and should tollerate restarts and loss of the database.
- The second reads the sensor data from the database, prepares ICs, runs DTR software and forwards the results over MQTT to Sumo

##  Project structure

The following bullet point hierarchy reflects the project structure
- `bin/` - Dythrea and Trafoflex binary executables and their `.so` dependencies
- `certificate/` contains credentials and certificates required for MQTT communication to work.  
    - `operato-mqttca.crt` MQTT certificate  
    - `credentials.xml` XML file with MQTT user credentials and parameters
		```xml  
		<data  
		username="<mqtt username>"
		password="<mqtt password>"
		broker="<mqtt broker>"
		port="<communication port>">
		</data>  
		```
        - `config/` - Contains `env.conf` that can be `source`-d and contains variables that might change between installation devices
- `data/` - Files used to help in development such as an example of an MC device message  
- `models/` - Trafoflex transformer models in binary `.pb` format
- `scripts/` - Shell/bash scripts used either for convenience or installation  
- `service/` - Shell scripts associated with systemd services
- `src/` - Main project code  
    - `device_io/` - Parent module of the package
        - `dythera/` - Module concerned with running line ampacity computations  
            - `config.py` - Constants used in the `dythera` submodule  
            - `generate_proto.py` - Functions that configure Dythera protobuffer `SimulationRequest`
            - `ic_script.py` - Called to combine data, run Dythera and communicates the results
            - `io.py` - Main code of the submodule with abstract class specialization for Dythera  
            - `main.py` - Runs the Dythrea database  
            - `pb2.py` - Protobuf-generated code for protobuffer data classes  
        - `trafoflex/` Module concerning transformer loadability computations  
	        - ... Same as in `dythera/`, but specific to Trafoflex ...  
        - `io.py` Functionality common to both Dythera and Trafoflex modules  
        - `config.py` Main constants of the package
- `tests/` - Tests for the code from `src/`  
- `venv/` - Automatically generated Python virtual environment code
- `install_fixed.sh` - Installation script called on the client machine's side (uses `config/env.conf` SSH credentials)
- `install.sh` - Legacy installation script that relies on a preconfigured `hedge_device` SSH alias
- `pyproject.toml` - `device_io` package configuration

## Tests

To run tests, run
```bash
pytest -m "not network"
```
since this avoids running network connectivity tests that is required to obtain data from some sensors.

## Notes

- Use `loginctl enable-linger <username>` for the service to persist after logout - Only for user services. If 
  installed in `/etc/systemd/system`, this isn't needed.

## Installation

Before installing the code, it has to be configured as specified in the [Configuration](#configuration) section.

The code is now fully configured for deployment by calling `./install_fixed.sh <d | t>` in the root directory of the 
project if one wishes to install the package in production mode. For development purposes do
```bash
source config/env.conf
./scripts/make_tmp_folders.sh
python3 -m venv venv
source venv/bin/activate
pip install <-e, if you wish for the install to be edditable> .
```
and then run tests as described in [Tests](#tests)

If the gateway has a SIM connection but no internet due to route priority, run:
```bash
./scripts/run_fix_gateway_routing_remote.sh
```
This executes [`scripts/fix_gateway_routing.sh`](scripts/fix_gateway_routing.sh) on the gateway over SSH using credentials from [`config/env.conf`](config/env.conf).

- Getting protobuffer's `pb2.py` files is done by using the [`proto_to_py.sh`](scripts/proto_to_py.sh) script, but this is only 
  needed if 
  the protobuffer version changes (the Python protobuffer library and `protoc` generated protobuffer files need to be compatible)

### Uninstallation

There is also the [`uninstall.sh`](scripts/uninstall.sh) script that takes the same arguments as the install script (`install_fixed.sh`) and removes all changes made by installing the software.

## Configuration

There are some difficulties in creating a global configuration file, so where particular parameters can be set are 
listed below. For security reasons with versioning, some configuration files are stored into their `*_base*` versions 
and need to be copied with the suffix removed. These files then need to be adjusted with the configuration specifics.
- General parameters: [`config/env.conf`](config/env.conf)
- MQTT credentials: [`certificate/credentials.xml`](certificate/credentials_base.xml)
- MQTT certificate: The `*.crt` file resides in the [`certificate`](certificate) folder. 
- Dythera upload frequency: [`service/dythera_upload.timer`](`service/dythera_upload.timer`) with `onUnitActiveSec`
- Trafoflex upload frequency: [`service/trafoflex_upload.timer`](service/trafoflex_upload.timer) with `onUnitActiveSec`
- Internal code parameters:
  - General package configuration: [`src/device_io/config.py`](src/device_io/config.py)
  - Trafoflex: [`src/device_io/trafoflex/config.py`](src/device_io/trafoflex/config.py)
  - Dythera: [`src/device_io/dythera/config.py`](src/device_io/dythera/config.py)

The internal code parameters shouldn't need adjusting, but if there are some errors it might be worth looking at these first.
 
### Notes

- It is strange, but it seems that to start a service triggered by a systemd timer, the service has to be started as 
  well as:
  ```bash
    systemd start <service_name>.timer
    systemd start <service_name>.service
    ```

## Networking setup

On the E62 cluster we encountered some issues particular to our environment that required specific adaptations to 
the workflow.

### Connection to the MC device

The device has a single ethernet port. In normal use the device will have wireless access to the internet and use 
the ethernet port to communicate with the MC device. In our case internet access is provided over the ethernet port 
as well as access to the MC device. The latter is connected to ninestein, but the device is connected to the VM on 
ninestein and isn't capable of direct communication with the MC device. The solution to this is a SSH tunnel from 
ninestein to the device over the VM. To simplify this action there is a [`/scripts/tunnel_to_MC.sh`](scripts/tunnel_to_MC.sh) that 
can be 
run.

### MQTT access

At some point the device and ninestein became unable to acces `sumo.operato.eu` over MQTT so 
[`scripts/tunnel_to_MQTT.sh`](scripts/tunnel_to_MQTT.sh) was implemented to enable access through the user's machine.