import logging

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label
from graph.util.util import ensure_connection
from foundation.model.foundational_node_enum import FoundationalNodeEnum

logger = logging.getLogger(__name__)


class Neo4jFoundationalFacetAdapter:
    """
    Adapter to collect facet count on a given eugene(genieve) graph node in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def collect_facet_by_label(
        self, label: FoundationalNodeEnum, values: list[str] = []
    ) -> str | None:
        ensure_connection(self.driver)
        return self._collect_facet_by_label(label=label, values=values)

    def _collect_facet_by_label(
        self, label: FoundationalNodeEnum, values: list[str]
    ) -> str | None:
        query = self._build_facet_by_label_query(label=label, values=values)
        logger.info(f"facet: {query}")
        try:
            records = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.single,
            )
            logger.debug(f"cypher response: {records['json']}")
            return records["json"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_facet_by_label_query(
        self, label: FoundationalNodeEnum, values: list[str]
    ) -> str:
        # FIXME: cypher injection issue
        # WARNING: this is wrong to inject a user query into the cypher
        # however the api does not let me pass a parameter into a query when using a regex like this?

        if (
            label is not FoundationalNodeEnum.DRUG
            and label is not FoundationalNodeEnum.DISEASE
        ):
            raise ValueError(f"Found {label} but facet only suppports drug or disease!")

        normalized_node_label = normalize_node_label(label.value[1])
        match_clause = f"MATCH (node:`{normalized_node_label}`)"
        where_clauses = []
        for value in values:
            where_clause = f"node.node_name =~ '(?i).*{value}.*'"
            where_clauses.append(where_clause)

        optional_where_clause = ""
        if len(where_clauses) > 0:
            optional_where_clause = "where " + "\nor ".join(where_clauses)

        if label is FoundationalNodeEnum.DRUG:
            facet_count_clause = """
                WITH apoc.map.merge(properties(node), {
                    nodeId: id(node),
                    indications: [(node)-[:indication]-(x:disease) | properties(x)],
                    contraindications: [(node)-[:contraindication]-(x:disease) | properties(x)],
                    offLabelUses: [(node)-[:`off-label use`]-(x:disease) | properties(x)]
                }) as node order by node.title
                WITH collect(node) as nodes,
                    [x in apoc.coll.flatten(collect(node.indications)) | x.node_name] as indications,
                    [x in apoc.coll.flatten(collect(node.contraindications)) | x.node_name] as contraindications,
                    [x in apoc.coll.flatten(collect(node.offLabelUses)) | x.node_name] as offLabelUses,
                    [x in apoc.coll.flatten(collect(node.indicationCount)) | x.node_name] as indicationCount,
                    [x in apoc.coll.flatten(collect(node.contraindicationCount)) | x.node_name] as contraindicationCount,
                    [x in apoc.coll.flatten(collect(node.offLabelCount)) | x] as offLabelCount
                WITH nodes,
                    apoc.coll.frequenciesAsMap(indications) as indications,
                    apoc.coll.frequenciesAsMap(contraindications) as contraindications,
                    apoc.coll.frequenciesAsMap(offLabelUses) as offLabelUses
                RETURN {
                    facets: {
                        indications: indications,
                        contraindications: contraindications,
                        offLabelUses: offLabelUses
                    }
                } as json
            """
        elif label is FoundationalNodeEnum.DISEASE:
            facet_count_clause = """
                WITH apoc.map.merge(properties(node), {
                    nodeId: id(node),
                    drugs: [(node)-[]-(x:drug) | properties(x)],
                    geneProteins: [(node)-[]-(x:gene_protein) | properties(x)]
                }) as node order by node.title
                WITH collect(node) as nodes,
                    [x in apoc.coll.flatten(collect(node.drugs)) | x.node_name] as drugs,
                    [x in apoc.coll.flatten(collect(node.geneProteins)) | x.node_name] as geneProteins,
                    [x in apoc.coll.flatten(collect(node.drugCount)) | x] as drugCount,
                    [x in apoc.coll.flatten(collect(node.geneProteinCount)) | x.node_name] as geneProteinCount
                WITH nodes,
                    apoc.coll.frequenciesAsMap(drugs) as drugs,
                    apoc.coll.frequenciesAsMap(geneProteins) as geneProteins
                RETURN {
                    facets: {
                        drugs: drugs,
                        geneProteins: geneProteins
                    }
                } as json
            """

        facet_count_query = "\n".join(
            [match_clause, optional_where_clause, facet_count_clause]
        )
        return facet_count_query
