import logging
import os

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


def api_endpoint_or_default() -> str:
    api_env_key = "EUGENE_AGENT_API_URL"
    api_endpoint = os.getenv(api_env_key)
    if api_endpoint:
        logger.info(f"ENV[{api_env_key}] set API Endpoint: {api_endpoint}")
    else:
        logger.info(f"{api_env_key} not found in the env, using a default local url")
        port = 8000
        base_path = "agent/api"
        api_endpoint = f"http://localhost:{port}/{base_path}/query"
    return api_endpoint
