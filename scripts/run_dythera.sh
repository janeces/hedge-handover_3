#!/bin/sh
# This script first runs the initial condition generation code and then calls the Dythera executable
# that will use this script.
cd $BASE_PATH
source venv/bin/activate

python $IC_SCRIPT_DYTHERA
deactivate


