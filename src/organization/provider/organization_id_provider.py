import logging

from organization.model.organization_resolution import OrganizationResolution
from organization.provider.organization_id_generator import OrganizationIdGenerator
from organization.model.canonical_organization_key import CanonicalOrganizationKey
from annotation.timer_annotation import log_time


logger = logging.getLogger(__name__)


class OrganizationIdProvider:

    def __init__(self, organization_id_generator: OrganizationIdGenerator):
        self.organization_id_generator = organization_id_generator

    @log_time
    def assign_canonical_ids(
        self, resolutions: list[OrganizationResolution]
    ) -> list[OrganizationResolution]:
        """
        assign ids to the root official or canonical names
        """
        if resolutions is None or len(resolutions) == 0:
            return []

        ids = self.generate_canonical_ids(resolutions)
        id_map = {canonical_key.name: canonical_key for canonical_key in ids}
        fail_count = 0
        for resolution in resolutions:
            current_name = self._pick_name(resolution=resolution)
            logger.info(f"finding key {current_name}")
            if current_name == "":
                logger.warning(f"unexpected resolution {resolution}")
            canonical_key = id_map[current_name]
            if canonical_key is None:
                logger.warning(
                    f"failed to find canonical key for {current_name}. This should not happen, moving on..."
                )
                fail_count += 1
            resolution.id = canonical_key

        logger.info(
            f"assigned {len(resolutions)} resolutions a canonical id. Fail count was {fail_count}"
        )
        return resolutions

    @log_time
    def generate_canonical_ids(
        self, resolutions: list[OrganizationResolution]
    ) -> list[CanonicalOrganizationKey]:
        """
        assign ids to the root official or canonical names
        """
        if resolutions is None or len(resolutions) == 0:
            return []

        keys = self._canonical_keys(resolutions)
        ids = self._generate_ids(self._uniq_keys(keys))
        logger.info(f"generated {len(ids)} canonical ids")
        return ids

    def _canonical_keys(
        self, resolutions: list[OrganizationResolution]
    ) -> list[CanonicalOrganizationKey]:
        canonical_keys = []

        for resolution in resolutions:
            # roll up id to the highest of parent or offical name
            name = self._pick_name(resolution)
            # TODO: fix me
            # WARN: is the parent the same type as the child?
            # it is a bad assumption but the only data we have to work with
            current_key = CanonicalOrganizationKey(
                name=name,
                organization_type=resolution.organization_type,
            )
            canonical_keys.append(current_key)
        return canonical_keys

    def _uniq_keys(
        self, canonical_keys: list[CanonicalOrganizationKey]
    ) -> list[CanonicalOrganizationKey]:
        if canonical_keys is None:
            return canonical_keys

        seen = set()
        uniq = []
        empty_name_count = 0
        for canonical_key in canonical_keys:
            name = canonical_key.name
            if name == "":
                empty_name_count += 1
                continue
            if name not in seen:
                uniq.append(canonical_key)
                seen.add(name)

        logger.info(f"dropped {empty_name_count} empty names")
        original_count = len(canonical_keys)
        uniq_count = len(uniq)
        logger.info(f"found {uniq_count} unique names out of names {original_count}")
        return uniq

    def _generate_ids(
        self, canonical_keys: list[CanonicalOrganizationKey]
    ) -> list[CanonicalOrganizationKey]:
        for canonical_key in canonical_keys:
            org_type = canonical_key.organization_type
            id = self.organization_id_generator.generate_id(org_type)
            canonical_key.id = id

        return canonical_keys

    def _pick_name(self, resolution: OrganizationResolution) -> str:
        # roll up id to parent
        # if resolution.parent is not None and len(resolution.parent) > 0:
        #     name = resolution.parent
        # else:
        #     name = resolution.official_name
        name = resolution.official_name
        return name
