FROM debian:buster-slim

ENV DEBIAN_FRONTEND noninteractive
ENV TERM xterm

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

RUN apt-get update \
	&& apt-get install -y \
		python3 \
		python3-pip \
		gammu=1.40.0-1 \
		gammu-smsd=1.40.0-1 \
		libgammu-dev=1.40.0-1 \
		libmariadb-dev \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/* 

COPY entrypoint.sh /usr/local/bin/
COPY src/ /opt/sms_gateway/

RUN pip3 install -r requirements.txt

CMD ["bash", "/usr/local/bin/entrypoint.sh"]
