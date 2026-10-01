import csv
import logging
from pathlib import Path
from typing import Any

from organization.model.organization_resolution import OrganizationResolution
from organization.model.canonical_organization_key import CanonicalOrganizationKey
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class OrganizationResolutionCsvWriter:
    HEADERS = {
        "ID_KEY": "organization_id",
        "NAME_KEY": "organization_name",
        "CANONICAL_NAME_KEY": "organization_canonical_name",
        "TYPE_KEY": "organization_type",
    }

    """
    write all entries out into a csv one row at a time
    """

    @log_time
    def write(
        self,
        output_path: Path,
        resolutions: list[OrganizationResolution],
    ) -> set[str]:
        """
        Writes json representation of organization name resolutions
        """
        if resolutions is None or len(resolutions) == 0:
            logger.warning("no resolutions to export to csv. moving on...")

        rows = self._uniq_org_names(self._to_rows(resolutions))
        logger.info(f"found {len(rows)} uniq resolution rows")
        logger.info(f"found {len(rows)} uniq rows with ids")
        logger.info(f"writing to {output_path}")
        with open(output_path, "a", newline="") as csvfile:
            fieldnames = [
                OrganizationResolutionCsvWriter.HEADERS["ID_KEY"],
                OrganizationResolutionCsvWriter.HEADERS["TYPE_KEY"],
                OrganizationResolutionCsvWriter.HEADERS["CANONICAL_NAME_KEY"],
                OrganizationResolutionCsvWriter.HEADERS["NAME_KEY"],
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header only once
            if output_path.stat().st_size == 0:
                writer.writeheader()

            for row in rows:
                logger.debug(f"writing row: {row}")
                writer.writerow(row)

        return {el[OrganizationResolutionCsvWriter.HEADERS["ID_KEY"]] for el in rows}

    def _to_rows(
        self, resolutions: list[OrganizationResolution]
    ) -> list[dict[str, Any]]:
        if resolutions is None or len(resolutions) == 0:
            return []

        rows = []
        for resolution in resolutions:
            rows.append(self._to_offical_name_row(resolution))
            rows.append(self._to_parent_name_row(resolution))
            canonical_id = self._canonical_id_or_default(resolution.id)
            canonical_name = self._canonical_name_or_default(resolution.id)
            org_type = resolution.organization_type
            logger.debug(
                f"canonical_id={canonical_id}, canonical_name={canonical_name}"
            )
            rows.extend(
                self._map_org_names_to_rows(
                    canonical_id=canonical_id,
                    canonical_name=canonical_name,
                    org_type=org_type,
                    org_names=resolution.spelling_variations,
                )
            )
            rows.extend(
                self._map_org_names_to_rows(
                    canonical_id=canonical_id,
                    canonical_name=canonical_name,
                    org_type=org_type,
                    org_names=resolution.acquisitions,
                )
            )
            rows.extend(
                self._map_org_names_to_rows(
                    canonical_id=canonical_id,
                    canonical_name=canonical_name,
                    org_type=org_type,
                    org_names=resolution.subsidiaries,
                )
            )
            rows.extend(
                self._map_org_names_to_rows(
                    canonical_id=canonical_id,
                    canonical_name=canonical_name,
                    org_type=org_type,
                    org_names=resolution.mergers,
                )
            )
            rows.extend(
                self._map_org_names_to_rows(
                    canonical_id=canonical_id,
                    canonical_name=canonical_name,
                    org_type=org_type,
                    org_names=resolution.demergers,
                )
            )

        for row in rows[0:8]:
            logger.debug(f"{row[OrganizationResolutionCsvWriter.HEADERS["ID_KEY"]]}")
        return rows

    def _to_offical_name_row(
        self, resolution: OrganizationResolution
    ) -> dict[str, Any]:
        org_name = resolution.official_name
        canonical_id = self._canonical_id_or_default(resolution.id)
        canonical_name = self._canonical_name_or_default(resolution.id)
        org_type = resolution.organization_type
        return self._to_row(
            canonical_id=canonical_id,
            canonical_name=canonical_name,
            org_type=org_type,
            name=org_name,
        )

    def _to_parent_name_row(self, resolution: OrganizationResolution) -> dict[str, Any]:
        org_name = resolution.parent
        canonical_id = self._canonical_id_or_default(resolution.id)
        canonical_name = self._canonical_name_or_default(resolution.id)
        org_type = resolution.organization_type
        return self._to_row(
            canonical_id=canonical_id,
            canonical_name=canonical_name,
            org_type=org_type,
            name=org_name,
        )

    def _map_org_names_to_rows(
        self,
        canonical_id: str | None,
        canonical_name: str,
        org_type: str,
        org_names: set[str],
    ) -> list[dict[str, Any]]:
        if org_names is None or len(org_names) == 0:
            return []

        rows = []
        sorted_names = sorted(org_names)
        for org_name in sorted_names:
            rows.append(
                self._to_row(
                    canonical_id=canonical_id,
                    canonical_name=canonical_name,
                    org_type=org_type,
                    name=org_name,
                )
            )
        return rows

    def _to_row(
        self,
        canonical_id: str | None,
        canonical_name: str,
        org_type: str,
        name: str,
    ) -> dict[str, Any]:
        return {
            OrganizationResolutionCsvWriter.HEADERS["ID_KEY"]: canonical_id,
            OrganizationResolutionCsvWriter.HEADERS["TYPE_KEY"]: org_type,
            OrganizationResolutionCsvWriter.HEADERS["NAME_KEY"]: name,
            OrganizationResolutionCsvWriter.HEADERS[
                "CANONICAL_NAME_KEY"
            ]: canonical_name,
        }

    def _uniq_org_names(self, rows: list[dict[Any, str]]) -> list[dict[Any, str]]:
        seen = set()

        uniq = []
        empty_name_count = 0
        for row in rows:
            name = row[OrganizationResolutionCsvWriter.HEADERS["NAME_KEY"]]
            if name == "":
                empty_name_count += 1
                continue
            if name not in seen:
                uniq.append(row)
                seen.add(name)

        logger.info(f"dropped {empty_name_count} empty names")
        original_count = len(rows)
        uniq_count = len(uniq)
        logger.info(f"found {uniq_count} unique names out of names {original_count}")
        return uniq

    def _canonical_name_or_default(self, key: CanonicalOrganizationKey | None) -> str:
        if key is None or key.name is None:
            return "-1"
        else:
            return key.name

    def _canonical_id_or_default(self, key: CanonicalOrganizationKey | None) -> str:
        if key is None or key.id is None:
            return "-1"
        else:
            return key.id
