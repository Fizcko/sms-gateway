FROM python:3.11-alpine3.20 as base

RUN apk update \
	&& apk add --no-cache \
		gammu=1.42.0-r1 \
		gammu-libs=1.42.0-r1 \
		gammu-smsd=1.42.0-r1 \
		mariadb-dev

RUN python -m pip install -U pip

# Build dependencies 
FROM base AS dependencies
COPY src/requirements.txt .
RUN apk add --no-cache gcc musl-dev python3-dev gammu-dev=1.42.0-r1 cargo \
    && pip install -r requirements.txt

# Build final image 
FROM base AS final

WORKDIR /opt/sms_gateway

RUN mkdir -p /opt/sms_gateway 

ENV SERVER_IP "0.0.0.0"
ENV SERVER_PORT "5000"

ENV GAMMU_SMSD_CONF "/etc/gammu-smsdrc"
ENV GAMMU_DEVICE "/dev/ttyUSB0"
ENV GAMMU_DEVICE_CONNECTION "at"
ENV GAMMU_PIN "1234"
ENV GAMMU_DEBUG_LEVEL "0"

ENV MYSQL_HOST "localhost"
ENV MYSQL_USERNAME "root"
ENV MYSQL_PASSWORD "toor"
ENV MYSQL_DATABASE "smsd"

ENV JWT_SECRET "Change-this-secret-phrase"
ENV JWT_ALGORITHM "HS256"
ENV JWT_ACCESS_TOKEN_EXPIRES "900"

ENV API_SECURITY "None"
ENV API_USERNAME "admin"
ENV API_PASSWORD "admin"


COPY entrypoint.sh /usr/local/bin/
COPY src/ /opt/sms_gateway/

COPY --from=dependencies /root/.cache /root/.cache
RUN pip install -r requirements.txt && rm -rf /root/.cache

CMD ["sh", "/usr/local/bin/entrypoint.sh"]
