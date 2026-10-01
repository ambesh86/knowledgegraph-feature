import logging

from neo4j import Driver
import neo4j
from neo4j.exceptions import DriverError, Neo4jError

from graph.util.node_util import normalize_node_label
from graph.util.util import ensure_connection
from foundation.model.foundational_node_enum import FoundationalNodeEnum

logger = logging.getLogger(__name__)


class Neo4jFoundationalOneHopAdapter:
    """
    Adapter to collect onehop relations on a given eugene(genieve) graph node in neo4j
    """

    def __init__(self, driver: Driver, database: str = "neo4j"):
        self.driver = driver
        self.database = database

    def collect_one_hop_by_label(
        self, label: FoundationalNodeEnum, value: str
    ) -> str | None:
        ensure_connection(self.driver)
        return self._collect_one_hop_by_label(label=label, value=value)

    def _collect_one_hop_by_label(
        self, label: FoundationalNodeEnum, value: str
    ) -> str | None:
        query = self._build_one_hop_by_label_query(label=label, value=value)
        logger.debug(f"find all: {query}")
        try:
            records = self.driver.execute_query(
                query_=query,
                result_transformer_=neo4j.Result.single,
            )
            logger.info(f"cypher response: {records['json']}")
            return records["json"]
        except (DriverError, Neo4jError) as exception:
            logging.error("%s raised an error: \n%s", query, exception)
            raise exception

    def _build_one_hop_by_label_query(
        self, label: FoundationalNodeEnum, value: str
    ) -> str:
        # FIXME: cypher injection issue
        # WARNING: this is wrong to inject a user query into the cypher
        # however the api does not let me pass a parameter into a query when using a regex like this?

        if (
            label is not FoundationalNodeEnum.DRUG
            and label is not FoundationalNodeEnum.DISEASE
        ):
            raise ValueError(
                f"Found {label} but one hop only suppports drug or disease!"
            )

        if label is FoundationalNodeEnum.DRUG:
            one_hop_query = """
                MATCH (node:`%s`)
                WHERE node.node_name =~ '(?i).*%s.*'
                WITH apoc.map.merge(properties(node), {
                    nodeId: id(node),
                    indications: [(node)-[:indication]-(x:disease) | properties(x)],
                    contraindications: [(node)-[:contraindication]-(x:disease) | properties(x)],
                    offLabelUses: [(node)-[:`off-label use`]-(x:disease) | properties(x)]
                }) as node order by node.title
                WITH collect(node) as nodes,
                [x in apoc.coll.flatten(collect(node.indications)) | x.node_name] as indications,
                [x in apoc.coll.flatten(collect(node.contraindications)) | x.node_name] as contraindications,
                [x in apoc.coll.flatten(collect(node.offLabelUses)) | x.node_name] as offLabelUses
                RETURN {
                    relationships: {
                        indications: indications,
                        contraindications: contraindications,
                        offLabelUses: offLabelUses
                    }
                } as json
                """ % (
                normalize_node_label(label.value[1]),
                value,
            )
        elif label is FoundationalNodeEnum.DISEASE:
            one_hop_query = """
                MATCH (node:`%s`)
                WHERE node.node_name =~ '(?i).*%s.*'
                WITH apoc.map.merge(properties(node), {
                    nodeId: id(node),
                    drugs: [(node)-[]-(x:drug) | properties(x)],
                    geneProteins: [(node)-[]-(x:gene_protein) | properties(x)]
                }) as node order by node.title
                WITH collect(node) as nodes,
                [x in apoc.coll.flatten(collect(node.drugs)) | x.node_name] as drugs,
                [x in apoc.coll.flatten(collect(node.geneProteins)) | x.node_name] as geneProteins
                RETURN {
                    relationships: {
                        drugs: drugs,
                        geneProteins: geneProteins
                    }
                } as json
                """ % (
                normalize_node_label(label.value[1]),
                value,
            )
        return one_hop_query
