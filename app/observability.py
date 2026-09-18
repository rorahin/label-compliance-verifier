import logging
import re
import sys
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"

SAFE_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def configure_logger() -> logging.Logger:
    """
    Configure application logging once.

    Logs intentionally exclude:
    - uploaded image contents
    - OCR text
    - form/application values
    - filenames
    """
    logger = logging.getLogger("label_verifier")

    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )

        handler.setFormatter(formatter)

        logger.addHandler(handler)

    logger.propagate = False

    return logger


def get_request_id(
    supplied_request_id: str | None = None,
) -> str:
    """
    Reuse a safe caller-provided request ID or create
    a new UUID.

    Validation prevents log-injection through malicious
    request headers.
    """
    if supplied_request_id and SAFE_REQUEST_ID_PATTERN.fullmatch(
        supplied_request_id
    ):
        return supplied_request_id

    return str(uuid4())


logger = configure_logger()
