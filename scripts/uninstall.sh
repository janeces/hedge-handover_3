#!/bin/sh
# Removes all installed files and disables services that were installed.
# It is called from the project root as ./scripts/uninstall.sh <d | t> to uninstall either Dythera or Trafoflex.
source config/env.conf

if [[ $1 = 'd' ]]; then
    prefix="dythera"
elif [[ $1 = 't' ]]; then
    prefix="trafoflex"
else
  echo "Choose t for Trafoflex or d for Dythera!"
  exit 1
fi

service_files="_database.service _upload.service _upload.timer"

systemctl disable hedge_file_structure.service
systemctl stop hedge_file_structure.service
rm $SERVICE_PATH/hedge_file_structure.service

for suffix in $service_files
do
  service=$prefix$suffix
  systemctl disable $service
  systemctl stop $service
  rm $SERVICE_PATH/$service
done
systemctl daemon-reload

cd ..

rm -rf $SCRIPT_PATH  # Remove scripts
rm -rf $CONFIG_DIR  # Remove configuration

rm -rf $TMP_PATH  # Remove /tmp files
rm -rf $BASE_PATH  # Remove the project directory
