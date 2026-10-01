import itertools
import logging
import uuid

from neo4j import Driver, Transaction
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label
from graph.util.util import ensure_connection, get_or_default
from organization.model.organization_resolution import OrganizationResolution
from organization.model.organization_node_enum import OrganizationNodeEnum
from organization.model.organization_relationship_enum import (
    OrganizationRelationshipEnum,
)

logger = logging.getLogger(__name__)


class Neo4jOrganizationAdapter:
    """
    @deprecated v1 organizations, replaced with v2 eugene load
    Adapter to update organization name found for eugene(genieve) graph in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def find_aliases_by_name(self, organization: str) -> list[str]:
        ensure_connection(self.driver)

        logger.info(f"searching for organization aliases. organization: {organization}")
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                aliases = self._find_aliases_by_name(tx=tx, organization=organization)
                logger.info(
                    f"found {len(aliases)} alias(es) for organization {organization}"
                )
                return aliases

    def _find_aliases_by_name(self, tx: Transaction, organization: str) -> list[str]:
        search = self._generate_search()
        params = {"organization_name": organization}
        logger.debug(f"search: {search}")
        logger.debug(f"params: {params}")
        try:
            record = tx.run(
                search,
                params,
            ).single()
            logger.info(f"cypher response: {record}")

            if record is None:
                return []

            return record[f"aliases"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", search, exception)
            raise

    def upsert_organization_resolutions(
        self, organization_resolutions: list[OrganizationResolution] = []
    ) -> list[str]:
        ensure_connection(self.driver)

        logger.info(
            f"upserting aliases for {len(organization_resolutions)} organization name(s)"
        )
        count = 0
        ids = []
        for resolution in organization_resolutions:
            with self.driver.session() as session:
                with session.begin_transaction() as tx:
                    current_id = self._upsert_organization_resolution(
                        tx=tx, organization_resolution=resolution
                    )
                    ids.append(current_id)
                    count += 1
                    if count % 100 == 0:
                        logger.debug(f"updated organization names: {count}")

        logger.info(f"ingested {len(ids)} organization names")
        return ids

    def _upsert_organization_resolution(
        self, tx: Transaction, organization_resolution: OrganizationResolution
    ) -> str | None:

        org_id = (
            organization_resolution.id
            if organization_resolution.id is not None
            else f"organization_{self._id()}"
        )
        search = """
        MERGE (organization:%s { node_name: $offical_name })
        ON MATCH
            SET organization.refresh_date = datetime()
        ON CREATE
            SET organization.refresh_date = datetime(),
                organization.node_id = $org_id,
                organization.node_name = $offical_name,
                organization.offical_name = $offical_name,
                organization.parent = $parent
        """ % (
            normalize_node_label(OrganizationNodeEnum.COMPANY.value[1])
        )

        [
            link_upserts,
            query_params,
        ] = self._generate_organization_alias_upserts(
            organization_resolution=organization_resolution, org_id=org_id
        )

        if len(link_upserts) < 1:
            logger.warning(f"{org_id} missing aliases, skipping...")
            return org_id

        step_size = 200
        stepper = range(0, len(link_upserts), step_size)
        for step in stepper:
            limit = (
                (step + step_size)
                if (step + step_size) < stepper.stop
                else stepper.stop
            )
            logger.info(f"upserting alias range {step}:{limit}")
            current_tx = link_upserts[step:limit]

            upsert_tx = "\n".join(
                list(
                    itertools.chain.from_iterable(
                        [
                            [search],
                            current_tx,
                            ["\tRETURN organization.node_id"],
                        ]
                    )
                )
            )

            logger.info(f"{organization_resolution.official_name} {org_id}")
            logger.info(
                f"upserting {len(current_tx)}/{len(link_upserts)} alias(es) for organization: {org_id}"
            )
            params = {
                "org_id": org_id,
                "offical_name": organization_resolution.official_name,
                "parent": organization_resolution.parent,
            } | query_params
            logger.debug(f"upsert: {upsert_tx}")
            logger.debug(f"params: {params}")
            try:
                record = tx.run(
                    upsert_tx,
                    params,
                ).single()
                logger.info(f"cypher response: {record}")

                if record is None:
                    logger.warning(f"response record was None")
                    return None
                return record["organization.node_id"]

            except (DriverError, Neo4jError) as exception:
                logging.error("%s raised an error: \n%s", upsert_tx, exception)
                raise

        return org_id

    def _generate_organization_alias_upserts(
        self, organization_resolution: OrganizationResolution, org_id: str
    ) -> tuple[list[str], dict[str, str]]:
        params = {}
        link_upserts = []
        if organization_resolution is None:
            return (link_upserts, params)

        subsidiaries = (
            organization_resolution.subsidiaries
            if organization_resolution.subsidiaries is not None
            else set()
        )
        subsidiary_count = len(subsidiaries)

        acquisitions = (
            organization_resolution.acquisitions
            if organization_resolution.acquisitions is not None
            else set()
        )
        acquisition_count = len(acquisitions)

        spelling_variations = (
            organization_resolution.spelling_variations
            if organization_resolution.spelling_variations is not None
            else set()
        )
        spelling_variation_count = len(spelling_variations)

        mergers = (
            organization_resolution.mergers
            if organization_resolution.mergers is not None
            else set()
        )
        merger_count = len(mergers)

        demergers = (
            organization_resolution.demergers
            if organization_resolution.demergers is not None
            else set()
        )
        demerger_count = len(demergers)

        if (
            subsidiary_count < 1
            and acquisition_count < 1
            and spelling_variation_count < 1
            and merger_count < 1
            and demerger_count < 1
        ):
            return (link_upserts, params)

        link_upserts = []
        [subsidiary_upserts, subsidiary_params] = self._generate_subsidiaries_upserts(
            org_id=org_id, aliases=subsidiaries
        )
        [acquisition_upserts, acquisition_params] = self._generate_aquisitions_upserts(
            org_id=org_id, aliases=acquisitions
        )
        [variation_upserts, variation_params] = (
            self._generate_spelling_variation_upserts(
                org_id=org_id,
                aliases=organization_resolution.spelling_variations,
            )
        )
        [merger_upserts, merger_params] = self._generate_merger_upserts(
            org_id=org_id,
            aliases=organization_resolution.spelling_variations,
        )
        [demerger_upserts, demerger_params] = self._generate_merger_upserts(
            org_id=org_id,
            aliases=organization_resolution.spelling_variations,
        )

        link_upserts.extend(subsidiary_upserts)
        link_upserts.extend(acquisition_upserts)
        link_upserts.extend(variation_upserts)
        link_upserts.extend(merger_upserts)
        link_upserts.extend(demerger_upserts)
        params = (
            params
            | subsidiary_params
            | acquisition_params
            | variation_params
            | merger_params
            | demerger_params
        )
        return (link_upserts, params)

    def _generate_subsidiaries_upserts(
        self, org_id: str, aliases: set[str] | None
    ) -> tuple[list[str], dict[str, str]]:
        return self._generate_alias_upserts(
            org_id=org_id,
            aliases=aliases,
            org_node_type=OrganizationNodeEnum.ORGANIZATION,
        )

    def _generate_aquisitions_upserts(
        self, org_id: str, aliases: set[str] | None
    ) -> tuple[list[str], dict[str, str]]:
        return self._generate_alias_upserts(
            org_id=org_id,
            aliases=aliases,
            org_node_type=OrganizationNodeEnum.ORGANIZATION,
        )

    def _generate_spelling_variation_upserts(
        self, org_id: str, aliases: set[str] | None
    ) -> tuple[list[str], dict[str, str]]:
        return self._generate_alias_upserts(
            org_id=org_id,
            aliases=aliases,
            org_node_type=OrganizationNodeEnum.ORGANIZATION,
        )

    def _generate_merger_upserts(
        self, org_id: str, aliases: set[str] | None
    ) -> tuple[list[str], dict[str, str]]:
        return self._generate_alias_upserts(
            org_id=org_id,
            aliases=aliases,
            org_node_type=OrganizationNodeEnum.ORGANIZATION,
        )

    def _generate_demerger_upserts(
        self, org_id: str, aliases: set[str] | None
    ) -> tuple[list[str], dict[str, str]]:
        return self._generate_alias_upserts(
            org_id=org_id,
            aliases=aliases,
            org_node_type=OrganizationNodeEnum.ORGANIZATION,
        )

    def _generate_alias_upserts(
        self,
        org_id: str,
        aliases: set[str] | None,
        org_node_type: OrganizationNodeEnum,
    ) -> tuple[list[str], dict[str, str]]:
        question_params = {}
        link_upserts = []
        if org_id is None:
            return (link_upserts, question_params)
        sorted_aliases = self._sort(aliases)
        sorted_aliases = sorted_aliases if sorted_aliases is not None else []

        alias_count = len(sorted_aliases)
        if alias_count < 1:
            return (link_upserts, question_params)

        link_upserts = []
        count = 0
        node_type = org_node_type.value[1].lower()
        for alias in sorted_aliases:
            key_prefix = node_type
            node_id_key = f"{key_prefix}{count}_node_id"
            node_name_key = f"{key_prefix}{count}_node_name"
            random_id = self._id()
            alias_id = f"{key_prefix}_{random_id}"
            question_params[node_id_key] = f"{org_id}_{alias_id}"
            question_params[node_name_key] = get_or_default(alias)
            upsert = """
            WITH organization
            MERGE (alias:`%s` { node_name: %s })
            ON MATCH
                SET alias.refresh_date = datetime()
            ON CREATE
                SET alias.refresh_date = datetime(),
                    alias.node_id = %s,
                    alias.node_name = %s
            MERGE (organization)-[r1:`%s`]-(alias)
            """.strip() % (
                normalize_node_label(node_type),
                f"${node_name_key}",
                f"${node_id_key}",
                f"${node_name_key}",
                OrganizationRelationshipEnum.HAS_ALIAS.value[1],
            )
            link_upserts.append(upsert)
            count += 1
        return (link_upserts, question_params)

    def _generate_search(self) -> str:
        return """
        MATCH (o:`%s`)
        WHERE o.organization_id = $organization_name
        CALL apoc.path.subgraphNodes([n],
        { 
            relationshipFilter: "%s",
            maxLevel: 2
        }) YIELD org
        RETURN DISTINCT org.node_name as name, toStringOrNull(org.node_id) as org_id,
            toStringOrNull(org.organization_name) as org_name
        """.strip() % (
            OrganizationNodeEnum.ORGANIZATION_V2.value[1],
            OrganizationRelationshipEnum.HAS_ALIAS.value[1],
        )

    def _sort(self, aliases: set[str] | None) -> list[str] | None:
        if aliases is None:
            return None

        return sorted(aliases, key=lambda alias: alias.lower())

    def _id(self) -> str:
        random_uuid = uuid.uuid4()
        return random_uuid.hex
