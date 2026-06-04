#!/bin/sh
# This script is called after install.sh is called on a client machine and this is then run on the host
# It is assumed that it is called from the project root directory.
# It is called as ./local_install.sh <dythera | trafoflex> where the single argument specifies the DTR software we are installing.
source config/env.conf
# Copy the configuration file in a standard directory
mkdir -p $CONFIG_DIR
cp config/env.conf $CONFIG_DIR/.

prefix=$1
other=""

if [ $prefix = "dythera" ]
then
    other="trafoflex"
elif [ $prefix = "trafoflex" ]
then
    other="dythera"
else
  printf "local_install.sh: Choose either 'dythera' or 'trafoflex' for the input!\n"
  exit 1
fi


printf "Creating virtual environment\n"
python3 -m venv venv
printf "Creating virtual environment done.\n\n"

source venv/bin/activate
printf "Bootstrapping packaging tools in virtual environment.\n"
python -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true

printf "Installing the Python package.\n"
pip install --no-build-isolation .
if [ $? -ne 0 ]; then
    printf "❌ Python package installation failed. Aborting.\n"
    deactivate
    exit 1
fi
printf "Installation of the Python package done.\n\n"

printf "Testing the installed package\n"
python -m pytest -m "not network and not $other"

if [ $? -eq 0 ]; then
    printf "✅ All tests passed. Proceeding...\n"
else
    printf "❌ Tests failed. Aborting.\n"
    exit 1
fi
deactivate
printf "Testing done.\n\n"


# Install the service files and start the services (filesystem creation in /tmp at startup, database and upload python scripts)
printf "Installing services.\n"
./scripts/start_services.sh $prefix
printf "Installation of services done.\n\n"
