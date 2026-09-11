#!/bin/sh
# Runs the data collection and storage for Trafoflex.
cd $BASE_PATH
source venv/bin/activate

python $DB_SCRIPT_TRAFOFLEX
deactivate