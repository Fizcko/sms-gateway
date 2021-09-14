import os

# Environment config
port = os.environ.get("SERVER_PORT", "5000")
ip = os.environ.get("SERVER_IP", "0.0.0.0")
security = os.environ.get("API_SECURITY", "None")

if security == 'Bearer':
    require_bearer = True
    require_basic = False
elif security == 'Basic':
    require_bearer = False
    require_basic = True
else:
    security = []
    require_bearer = False
    require_basic = False

environment_config = {
    "ip": ip,
    "port": port,
    "swagger-url": "/",
    "security": security,
    "require_bearer": require_bearer,
    "require_basic": require_basic
}

# JWT config
jwt_secret = os.environ.get("JWT_SECRET", "change-it")
jwt_algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
jwt_access_token_expires = os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", "900")

jwt_config = {
    "secret": jwt_secret,
    "algorithm": jwt_algorithm,
    "token_expires": int(jwt_access_token_expires) if jwt_access_token_expires.isnumeric() else 900
}

# DB config
mysql_host = os.environ.get("MYSQL_HOST", "localhost")
mysql_username = os.environ.get("MYSQL_USERNAME", "root")
mysql_password = os.environ.get("MYSQL_PASSWORD", "toor")
mysql_database = os.environ.get("MYSQL_DATABASE", "smsd")

database_config = {
    "host": mysql_host,
    "username": mysql_username,
    "password": mysql_password,
    "database": mysql_database
}

# Gammu-smsd config
gammu_smsd_conf = os.environ.get("GAMMU_SMSD_CONF", "/etc/gammu-smsdrc")

gammu_smsd_config = {
    "conf": gammu_smsd_conf
}
