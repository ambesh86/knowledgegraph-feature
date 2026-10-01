import logging
from dotenv import find_dotenv, load_dotenv

logger = logging.getLogger(__name__)


def load_env() -> None:
    # Attempt to find the .env file, but don't raise an error if it's not found
    dotenv_path = find_dotenv(raise_error_if_not_found=False)
    logger.info(f".env file {dotenv_path}")

    if dotenv_path:
        load_dotenv(dotenv_path, verbose=True)
    else:
        logger.warning(".env file not found")
