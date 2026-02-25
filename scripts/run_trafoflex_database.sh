#!/bin/sh
# Runs the data collection and storage for Dythera.
cd $BASE_PATH
source venv/bin/activate

python $DB_SCRIPT_TRAFOFLEX
deactivate