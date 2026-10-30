#!/bin/sh
set -e

cd /opt/sms_gateway

# The configuration holds the database password
umask 077
cat > "$GAMMU_SMSD_CONF" <<EOL
# Configuration file for Gammu SMS Daemon

# Gammu library configuration, see gammurc(5)
[gammu]
device = ${GAMMU_DEVICE}
connection = ${GAMMU_DEVICE_CONNECTION}

# SMSD configuration, see gammu-smsdrc(5)
[smsd]
PIN = ${GAMMU_PIN}
Service = sql
Driver = native_mysql
Host = ${MYSQL_HOST}
User = ${MYSQL_USER}
Password = ${MYSQL_PASSWORD}
Database = ${MYSQL_DATABASE}

logfile = /dev/stdout
debuglevel = ${GAMMU_DEBUG_LEVEL}

EOL
umask 022

# gammu-smsd refuses a database that is not at its schema version
python3 -m sms_gateway.db.migrate

/usr/bin/gammu-smsd --pid=/var/run/gammu-smsd.pid --config "$GAMMU_SMSD_CONF" --daemon

exec python3 -m sms_gateway
