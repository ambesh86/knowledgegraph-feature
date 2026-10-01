import csv
from pathlib import Path


class CsvWriter:
    """
    Class responsible for writing study data to a CSV file.
    """

    def __init__(self, output_file: str):
        self.output_file = Path(output_file)

    def write_studies_to_csv(self, studies: list) -> None:
        """
        Writes the parsed study data to a CSV file.
        """
        with open(self.output_file, "a", newline="") as csvfile:
            fieldnames = [
                "NCTId",
                "BriefTitle",
                "Condition",
                "InterventionName",
                "OutcomeMeasure",
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header only once
            if self.output_file.stat().st_size == 0:
                writer.writeheader()

            for study in studies:
                # Flatten lists for CSV writing
                row = {
                    "NCTId": study["NCTId"],
                    "BriefTitle": study["BriefTitle"],
                    "Condition": ", ".join(study["Condition"]),
                    "InterventionName": ", ".join(study["InterventionName"]),
                    "OutcomeMeasure": "\n".join(
                        [
                            f"{measure[0]} ({measure[1]})"
                            for measure in study["OutcomeMeasure"]
                        ]
                    ),
                }
                writer.writerow(row)
