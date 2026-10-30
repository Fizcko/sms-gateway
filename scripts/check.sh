#!/bin/sh
# Lint, type check and all the tests, in the same image as production (Python 3.14,
# Gammu 1.45.1), against a throwaway MariaDB. Usage: scripts/check.sh [pytest args]
set -eu

cd "$(dirname "$0")/.."
NAME="sms-gateway-check-$$"
PASSWORD=test

cleanup() {
    docker rm -f "$NAME-db" >/dev/null 2>&1 || true
    docker network rm "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker build -q --target test -t sms-gateway:test . >/dev/null
docker network create "$NAME" >/dev/null
docker run -d --name "$NAME-db" --network "$NAME" -e MARIADB_ROOT_PASSWORD="$PASSWORD" \
    mariadb:11.4 >/dev/null
until docker exec "$NAME-db" healthcheck.sh --connect --innodb_initialized >/dev/null 2>&1; do
    sleep 1
done

docker run --rm --network "$NAME" -e TEST_MYSQL_HOST="$NAME-db" \
    -e TEST_MYSQL_PASSWORD="$PASSWORD" -e PYTHONDONTWRITEBYTECODE=1 sms-gateway:test sh -c '
    set -e
    ruff check src tests
    ruff format --check src tests
    mypy src tests
    pytest -p no:cacheprovider -q "$@"
' -- "$@"
