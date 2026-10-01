import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TxtWriter:

    def write(self, pgpubs: list[dict[str, Any]], out_path_base: Path) -> None:
        """
        Writes txt representation of pregrant docs
        """
        if pgpubs is None:
            logger.warning("no pregrant pubs to write. moving on...")

        num_applications = len(pgpubs)
        logger.info(f"writing {num_applications} pgpub file(s)")

        for pgpub in pgpubs:
            logger.debug(f"{pgpub}")
            application_number_text = pgpub["application_number_text"]
            with open(
                out_path_base / f"{application_number_text}.txt",
                "w",
                newline="",
            ) as file:
                logger.debug(f"writing {file.name}")
                lines = self._pgpub_to_lines(pgpub=pgpub)
                file.writelines(lines)

        logger.info("done writing files")

    def _pgpub_to_lines(self, pgpub: dict[str, Any]) -> list[str]:
        if pgpub is None:
            return []

        abstract = pgpub["abstract"]
        organizations = pgpub["organizations"] if "organizations" in pgpub else ""
        application_number = (
            pgpub["application_number_text"]
            if "application_number_text" in pgpub
            else ""
        )
        claims = pgpub["claims"] if "claims" in pgpub else []
        description_paragraphs = pgpub["description"] if "description" in pgpub else []

        lines = [
            f"application: {application_number}",
            f"organziations: {organizations}",
            f"abstract: {abstract}",
            "claims:",
            *claims,
        ]

        return [line + "\n" for line in lines]
