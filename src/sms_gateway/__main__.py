"""Start the API server: `python -m sms_gateway`."""

import logging

import uvicorn

from sms_gateway.app import create_app
from sms_gateway.settings import Settings


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    # One worker: the outbox injection handle lives in the process.
    uvicorn.run(
        create_app(settings), host=settings.server_ip, port=settings.server_port, access_log=False
    )


if __name__ == "__main__":
    main()
