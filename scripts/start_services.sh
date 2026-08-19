#!/bin/sh
# Installs and starts the services that will restart operations after reboot.
source config/env.conf

tr_type=$1  # Thermal rating type (either dythera or trafoflex)
service_files="_database.service _upload.service _upload.timer"

# Copy the service files to the standard directory
for suffix in $service_files
do
  cp $SERVICE_LOCAL_PATH/$tr_type$suffix $SERVICE_PATH/.
done
# Copy the general service
cp $SERVICE_LOCAL_PATH/hedge_file_structure.service $SERVICE_PATH/.

# Copy the scripts
chmod +x scripts/*  # Enable all scripts to be executed.
mkdir -p $SCRIPT_PATH

cp scripts/run_${tr_type}.sh $SCRIPT_PATH/.
cp scripts/run_${tr_type}_database.sh $SCRIPT_PATH/.
cp scripts/make_tmp_folders.sh $SCRIPT_PATH/.
cp scripts/wait_for_valid_time.sh $SCRIPT_PATH/.
cp scripts/install_tailscale_time_override.sh $SCRIPT_PATH/.
cp scripts/gateway_diagnostics.sh $SCRIPT_PATH/.

chmod +x $SCRIPT_PATH/wait_for_valid_time.sh
chmod +x $SCRIPT_PATH/install_tailscale_time_override.sh
chmod +x $SCRIPT_PATH/gateway_diagnostics.sh

$SCRIPT_PATH/install_tailscale_time_override.sh || true

systemctl daemon-reload
# Establish the /tmp filesystem
systemctl enable hedge_file_structure.service
systemctl start hedge_file_structure.service

# Enable services and start them
for suffix in $service_files
do
  service=$tr_type$suffix
  systemctl enable $service
  systemctl start $service
done

printf "Checking service status\n"
sleep_time=10
printf "Sleeping for %s s to get some output in logs\n" $sleep_time
sleep $sleep_time

# Show service status with some output
for suffix in $service_files
do
  service=$tr_type$suffix
  systemctl status $service
done