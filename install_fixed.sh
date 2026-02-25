#!/bin/bash
# This script is run on a client machine and uploads and configures the host device to run either
# Trafoflex or Dythera
# Usage: ./install <d | t>
# Choosing d installs Dythera and t installs Trafoflex
echo "[+] starting..."

source config/env.conf

# SSH options to disable strict host key checking
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

prefix=""

if [[ $1 = 'd' ]]; then
    prefix="dythera"
elif [[ $1 = 't' ]]; then
    prefix="trafoflex"
else
  printf "Choose t for Trafoflex or d for Dythera!\n"
  exit 1
fi

printf "Installing $prefix on $HOST_UNAME@$HOST_NAME at $BASE_PATH\n"
# Upload the repository
chmod +x scripts/*  # Enable all scripts to be executable.


echo "[+] Remounting root filesystem as writable..."
sshpass -p $HOST_PWD ssh $SSH_OPTS $HOST_UNAME@$HOST_NAME "mount -o remount,rw /"  # Ensure the root filesystem is writable.

printf "Uploading files\n"
files="bin certificate config models scripts service src tests pyproject.toml README.md requirements.txt" # Files to copy to BASE_PATH

# TODO: replace this with the commented line. It just governs how the connection is established.
sshpass -p $HOST_PWD ssh $SSH_OPTS $HOST_UNAME@$HOST_NAME "mkdir -p $BASE_PATH"

#ssh hedge_device "mkdir -p $BASE_PATH"  # Make the project root directory and create any missing parent directories.
sshpass -p $HOST_PWD rsync -avz -e "ssh $SSH_OPTS" --exclude='__pycache__' --exclude='*.egg-info' $files "$HOST_UNAME@$HOST_NAME:$BASE_PATH"
#rsync -avz --exclude='__pycache__' --exclude='*.egg-info' $files "hedge_device:$BASE_PATH"
printf "Files uploaded.\n\n"

# Run the local installation
printf "Executing remote install\n"
# TODO: replace this with the commented line. It just governs how the connection is established.
sshpass -p $HOST_PWD ssh $SSH_OPTS $HOST_UNAME@$HOST_NAME "cd $BASE_PATH && ./scripts/local_install.sh $prefix"
#ssh hedge_device "cd $BASE_PATH && ./scripts/local_install.sh $prefix"

if [[ $? -eq 0 ]]; then
  printf "Installation completed successfully!\n"
else
  printf "Installation failed!\n"
fi
echo "[+] Remounting root filesystem as read-only..."
sshpass -p $HOST_PWD ssh $SSH_OPTS $HOST_UNAME@$HOST_NAME "mount -o remount,ro  /"  # Ensure the root filesystem is again read-only .
