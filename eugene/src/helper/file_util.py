import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def ensure_exists(file_path: Path) -> None:
    logger.info(f"ensuring {file_path} exists")
    dir_path = os.path.dirname(file_path)
    Path(dir_path).mkdir(parents=True, exist_ok=True)