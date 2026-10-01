import json
import logging
from pathlib import Path

from patent.pgpub.model.pgpub import Pgpub
from patent.pgpub.json.pgpub_json_encoder import PgpubJsonEncoder

logger = logging.getLogger(__name__)


class JsonWriter:

    def write(self, pgpubs: list[Pgpub], path: Path) -> None:
        """
        Writes json representation of pregrant docs
        """
        if pgpubs is None:
            logger.warning("no pregrant pubs to export to json. moving on...")

        num_applications = len(pgpubs)
        logger.info(f"export {num_applications} json pgpub file(s)")

        for pgpub in pgpubs:
            with open(
                path / "pgpub" / f"{pgpub.application_number_text}.json",
                "w",
                newline="",
            ) as json_file:
                logger.info(f"writing {json_file.name}")
                json.dump(
                    pgpub, fp=json_file, cls=PgpubJsonEncoder, indent=4, sort_keys=True
                )
