import json
import logging
import os
from pathlib import Path

from patent.application.model.application import Application
from patent.application.json.application_json_decoder import ApplicationJsonDecoder


logger = logging.getLogger(__name__)


class ApplicationLoader:

    def load_all(self, data_dir: Path) -> list[Application]:
        if data_dir is None:
            return []

        try:
            all_dir_entries = os.listdir(data_dir)
            files = [
                entry
                for entry in all_dir_entries
                if os.path.isfile(os.path.join(data_dir, entry))
            ]
            logger.info(f"Files in {data_dir}: {len(files)}")
            data = []
            for file_name in files:
                with open(data_dir / file_name, "r", encoding="utf-8") as file:
                    logger.info(f"reading {file_name}...")
                    current = json.load(fp=file, cls=ApplicationJsonDecoder)
                    data.append(current)
                    logger.debug(f"{current}")

            return data
        except FileNotFoundError as e:
            logger.warning(e)
            raise e
