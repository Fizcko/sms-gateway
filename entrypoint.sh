#!/bin/bash

# Define variables
ROOT_PATH="/opt/sms_gateway"

# Go into ROOT_PATH
cd $ROOT_PATH

# Create config files
cat > $GAMMU_SMSD_CONF <<EOL
# Configuration file for Gammu SMS Daemon

# Gammu library configuration, see gammurc(5)
[gammu]
device = ${GAMMU_DEVICE}
connection = ${GAMMU_DEVICE_CONNECTION}

# SMSD configuration, see gammu-smsdrc(5)
[smsd]
Service = sql
Driver = native_mysql
Host = ${MYSQL_HOST}
User = ${MYSQL_USERNAME}
Password = ${MYSQL_PASSWORD}
Database = ${MYSQL_DATABASE}

logfile = /dev/stdout
debuglevel = ${GAMMU_DEBUG_LEVEL}

EOL

# Delay start gammu-smsd
sleep 5s && /usr/bin/gammu-smsd --pid=/var/run/gammu-smsd.pid --config $GAMMU_SMSD_CONF --daemon &

# Start backend
python3 ./main.py
