#!/bin/sh
# This script first runs the initial condition generation code and then calls the Trafoflex executable
# that will use this script. After execution it saves the transformer state.
cd $BASE_PATH
source venv/bin/activate

python $IC_SCRIPT_TRAFOFLEX $MODEL_PATH
deactivate

if [ -f trafoflex_input.log ]; then
  rm trafoflex_input.log
fi