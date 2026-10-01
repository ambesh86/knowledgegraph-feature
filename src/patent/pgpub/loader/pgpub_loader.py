import json
import logging
import os
from pathlib import Path

from patent.pgpub.model.pgpub import Pgpub
from patent.pgpub.json.pgpub_json_decoder import PgpubJsonDecoder


logger = logging.getLogger(__name__)


class PgpubLoader:

    def load_all(self, data_dir: Path) -> list[Pgpub]:
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
            pgpubs = []
            for file_name in files:
                with open(data_dir / file_name, "r", encoding="utf-8") as file:
                    current_pgpub = json.load(fp=file, cls=PgpubJsonDecoder)
                    pgpubs.append(current_pgpub)
                    logger.debug(f"{current_pgpub}")

            return pgpubs
        except FileNotFoundError as e:
            logger.warning(e)
            raise e
