# Gammu is built from source: Alpine ships 1.42.0, on every branch including edge.
# See docs/decisions/0001-build-gammu-from-source.md.
FROM python:3.14-alpine3.23 AS base

RUN apk add --no-cache mariadb-connector-c libcurl libusb bluez-libs curl

# Build gammu, gammu-smsd and libGammu/libgsmsd, always at the same version.
# gettext-dev must stay out: its libintl.h breaks linking against musl's gettext.
FROM base AS gammu
ARG GAMMU_VERSION=1.45.1
ARG GAMMU_SHA256=4003b3df5e4815c36eb4b6614c73ea88d83acd7d5791fdc3fbdab0d3c323c707
RUN apk add --no-cache build-base cmake pkgconf mariadb-connector-c-dev curl-dev libusb-dev bluez-dev linux-headers
ADD https://github.com/gammu/gammu/archive/refs/tags/${GAMMU_VERSION}.tar.gz /tmp/gammu.tar.gz
RUN echo "${GAMMU_SHA256}  /tmp/gammu.tar.gz" | sha256sum -c - \
    && mkdir /tmp/gammu && tar xzf /tmp/gammu.tar.gz -C /tmp/gammu --strip-components=1 \
    && cmake -S /tmp/gammu -B /tmp/build \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_INSTALL_LIBDIR=lib \
        -DREQUIRE_MYSQL=ON \
        -DBUILD_TESTING=OFF \
        -DINSTALL_DOC=OFF \
    && cmake --build /tmp/build -j"$(nproc)" \
    && cmake --install /tmp/build \
    && DESTDIR=/gammu-install cmake --install /tmp/build

# Build the Python dependencies. python-gammu must link against the libGammu above:
# the PyPI wheels have no SQL SMSD service, so InjectSMS would not work.
FROM gammu AS dependencies
COPY pyproject.toml /build/
COPY src/ /build/src/
RUN pip install --prefix=/python-install --no-binary python-gammu /build

# Swagger UI, served locally: a gateway may have no internet access. It must support the
# OpenAPI version FastAPI generates (3.1 needs Swagger UI 5).
FROM base AS swagger-ui
ARG SWAGGER_UI_VERSION=5.34.0
ARG SWAGGER_UI_SHA512=1fab40223af75ea137d4f6e4665d0e1726b5ce244b0df4f087727a38776e98fb4f08b7e34e7c8b79a825ff9e6414d65c4cecfd6bd408f563f415795dc221896a
ADD https://registry.npmjs.org/swagger-ui-dist/-/swagger-ui-dist-${SWAGGER_UI_VERSION}.tgz /tmp/swagger-ui.tgz
RUN echo "${SWAGGER_UI_SHA512}  /tmp/swagger-ui.tgz" | sha512sum -c - \
    && mkdir -p /swagger-ui && tar xzf /tmp/swagger-ui.tgz -C /swagger-ui --strip-components=1 \
        package/swagger-ui-bundle.js package/swagger-ui.css package/favicon-32x32.png package/package.json

FROM base AS runtime
COPY --from=gammu /gammu-install/ /
COPY --from=swagger-ui /swagger-ui/ /usr/local/share/swagger-ui/
COPY --from=dependencies /python-install/ /usr/local/
WORKDIR /opt/sms_gateway
ENV PYTHONUNBUFFERED="1"

ENV SERVER_IP="0.0.0.0"
ENV SERVER_PORT="5000"

ENV GAMMU_SMSD_CONF="/etc/gammu-smsdrc"
ENV GAMMU_DEVICE="/dev/ttyUSB0"
ENV GAMMU_DEVICE_CONNECTION="at"
ENV GAMMU_PIN="1234"
ENV GAMMU_DEBUG_LEVEL="0"

ENV MYSQL_HOST="localhost"
ENV MYSQL_USER="root"
ENV MYSQL_DATABASE="smsd"

ENV JWT_ALGORITHM="HS256"
ENV JWT_ACCESS_TOKEN_EXPIRES="900"

ENV API_SECURITY="None"

COPY entrypoint.sh /usr/local/bin/

# Lint, type check and tests, run by scripts/check.sh.
FROM runtime AS test
COPY pyproject.toml /opt/sms_gateway/
COPY src/ /opt/sms_gateway/src/
COPY tests/ /opt/sms_gateway/tests/
# What the tests compare the schema to: the sources of the Gammu actually built.
COPY --from=gammu /tmp/gammu/docs/sql/mysql.sql /tmp/gammu/smsd/core.h /opt/sms_gateway/tests/gammu_upstream/
RUN pip install --group dev

FROM runtime AS final
ARG APP_VERSION=3.0.0
ENV APP_VERSION="${APP_VERSION}"
CMD ["sh", "/usr/local/bin/entrypoint.sh"]
