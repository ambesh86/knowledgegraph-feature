import logging
import os
from getpass import getpass

logger = logging.getLogger(__name__)


def load_openai_api_key():
    if "OPENAI_API_KEY" not in os.environ:
        os.environ["OPENAI_API_KEY"] = getpass("Enter your OpenAI API key: ")
