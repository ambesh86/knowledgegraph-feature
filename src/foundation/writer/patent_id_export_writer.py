import logging
import csv

from pathlib import Path
from typing import Tuple


logger = logging.getLogger(__name__)


class PatentIdExportWriter:
    """
    Class responsible for writing us patent id to other asset relationships as a CSV file
    """

    def write_csv(self, output_path: Path, rows: list[Tuple[str, str, str]]) -> None:
        """
        Writes nodes to a CSV file.
        """
        if output_path is None:
            return None
        if rows is None:
            return None

        with open(output_path, "a", newline="") as csv_file:
            fieldnames = ["ID", "USPTO_ID", "USPTO_FILING_DATE"]

            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            # Write header only once
            if output_path.stat().st_size == 0:
                writer.writeheader()

            for row in rows:
                write_row = {
                    "ID": row[0],
                    "USPTO_ID": row[1],
                    "USPTO_FILING_DATE": row[2],
                }
                writer.writerow(write_row)
