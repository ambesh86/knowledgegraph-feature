import os
from neo4j import Driver

from foundation.infra.db.adapter.neo4j_foundational_node_count_adapter import (
    Neo4jFoundationalNodeCountAdapter,
)
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from foundation.infra.db.adapter.neo4j_foundational_node_adapter import (
    Neo4jFoundationalNodeAdapter,
)
from foundation.infra.db.adapter.neo4j_onehot_encoding_adapter import (
    Neo4jOnehotEncodingAdapter,
)
from foundation.infra.embedding.foundational_node_embedding_provider import (
    FoundationalNodeEmbeddingProvider,
)
from foundation.provider.foundational_node_fix_orchestrator import (
    FoundationalNodeFixOrchestrator,
)
from foundation.infra.db.adapter.neo4j_missing_node_index_embedding_adapter import (
    Neo4jMissingNodeIndexEmbeddingAdapter,
)
from foundation.infra.embedding.list_embeddings_provider import (
    ListEmbeddingsProvider,
)
from foundation.infra.db.adapter.neo4j_list_embeddings_adapter import (
    Neo4jListEmbeddingsAdapter,
)
from foundation.writer.tsv_embeddings_writer import TsvEmbeddingsWriter
from foundation.infra.db.adapter.neo4j_foundational_one_hop_adapter import (
    Neo4jFoundationalOneHopAdapter,
)
from foundation.infra.db.adapter.neo4j_foundational_facet_adapter import (
    Neo4jFoundationalFacetAdapter,
)
from foundation.infra.db.adapter.neo4j_foundational_similarity_adapter import (
    Neo4jFoundationalSimilarityAdapter,
)
from foundation.infra.db.adapter.neo4j_drug_aliases_adapter import (
    Neo4jDrugAliasesAdapter,
)
from foundation.load.drug_synonyms_loader import DrugSynonymsLoader
from foundation.load.drug_product_names_loader import DrugProductNamesLoader
from foundation.provider.drug_aliases_update_orchestrator import (
    DrugAliasesUpdateOrchestrator,
)
from foundation.infra.db.adapter.neo4j_foundational_n_hop_adapter import (
    Neo4jFoundationalNHopAdapter,
)
from foundation.mapper.graph_mapper import GraphMapper
from foundation.provider.foundational_n_hop_provider import FoundationalNHopProvider
from foundation.infra.db.adapter.neo4j_foundational_path_adapter import (
    Neo4jFoundationalPathAdapter,
)
from foundation.provider.foundational_path_provider import FoundationalPathProvider
from foundation.provider.foundational_node_id_provider import (
    FoundationalNodeIdProvider,
)
from foundation.mapper.node_id_lookup_mapper import NodeIdLookupMapper
from foundation.mapper.node_details_mapper import NodeDetailsMapper
from foundation.infra.db.adapter.neo4j_foundational_node_details_adapter import (
    Neo4jFoundationalNodeDetailsAdapter,
)
from foundation.provider.foundational_node_details_provider import (
    FoundationalNodeDetailsProvider,
)
from foundation.mapper.facts_mapper import FactsMapper
from foundation.provider.foundational_facts_orchestrator import (
    FoundationalFactsOrchestrator,
)
from foundation.infra.db.adapter.neo4j_patent_query_adapter import (
    Neo4jPatentQueryAdapter,
)
from foundation.mapper.patent_search_result_mapper import PatentSearchResultMapper
from foundation.infra.db.adapter.neo4j_patent_export_adapter import (
    Neo4jPatentExportAdapter,
)
from foundation.writer.patent_id_export_writer import PatentIdExportWriter
from foundation.mapper.drug_aliases_result_mapper import DrugAliasesResultMapper
from foundation.infra.db.adapter.neo4j_pubmed_count_adapter import (
    Neo4jPubmedCountAdapter,
)
from foundation.infra.db.adapter.neo4j_pubmed_query_adapter import (
    Neo4jPubmedQueryAdapter,
)
from foundation.mapper.pubmed_search_result_mapper import PubmedSearchResultMapper


def model_cache_dir() -> str | None:
    key = "HF_HUB_CACHE"
    value = os.environ[key] if key in os.environ else None
    return value


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def neo4j_foundational_node_count_adapter() -> Neo4jFoundationalNodeCountAdapter:
    return _neo4j_foundational_node_count_adapter(driver=_neo4j_driver())


def _neo4j_foundational_node_count_adapter(
    driver: Driver,
) -> Neo4jFoundationalNodeCountAdapter:
    return Neo4jFoundationalNodeCountAdapter(driver=driver)


def neo4j_foundational_node_adapter() -> Neo4jFoundationalNodeAdapter:
    return _neo4j_foundational_node_adapter(driver=_neo4j_driver())


def _neo4j_foundational_node_adapter(driver: Driver) -> Neo4jFoundationalNodeAdapter:
    return Neo4jFoundationalNodeAdapter(driver=driver)


def neo4j_foundational_node_details_adapter() -> Neo4jFoundationalNodeDetailsAdapter:
    return _neo4j_foundational_node_details_adapter(driver=_neo4j_driver())


def _neo4j_foundational_node_details_adapter(
    driver: Driver,
) -> Neo4jFoundationalNodeDetailsAdapter:
    return Neo4jFoundationalNodeDetailsAdapter(driver=driver)


def neo4j_foundational_one_hop_adapter() -> Neo4jFoundationalOneHopAdapter:
    return _neo4j_foundational_one_hop_adapter(driver=_neo4j_driver())


def _neo4j_foundational_one_hop_adapter(
    driver: Driver,
) -> Neo4jFoundationalOneHopAdapter:
    return Neo4jFoundationalOneHopAdapter(driver=driver)


def neo4j_foundational_n_hop_adapter() -> Neo4jFoundationalNHopAdapter:
    return _neo4j_foundational_n_hop_adapter(driver=_neo4j_driver())


def _neo4j_foundational_n_hop_adapter(
    driver: Driver,
) -> Neo4jFoundationalNHopAdapter:
    return Neo4jFoundationalNHopAdapter(driver=driver)


def neo4j_foundational_path_adapter() -> Neo4jFoundationalPathAdapter:
    return _neo4j_foundational_path_adapter(driver=_neo4j_driver())


def _neo4j_foundational_path_adapter(
    driver: Driver,
) -> Neo4jFoundationalPathAdapter:
    return Neo4jFoundationalPathAdapter(driver=driver)


def neo4j_foundational_facet_adapter() -> Neo4jFoundationalFacetAdapter:
    return _neo4j_foundational_facet_adapter(driver=_neo4j_driver())


def _neo4j_foundational_facet_adapter(
    driver: Driver,
) -> Neo4jFoundationalFacetAdapter:
    return Neo4jFoundationalFacetAdapter(driver=driver)


def neo4j_patent_export_adapter() -> Neo4jPatentExportAdapter:
    return _neo4j_patent_export_adapter(driver=_neo4j_driver())


def _neo4j_patent_export_adapter(
    driver: Driver,
) -> Neo4jPatentExportAdapter:
    return Neo4jPatentExportAdapter(driver=driver)


def neo4j_foundational_similarity_adapter() -> Neo4jFoundationalSimilarityAdapter:
    return _neo4j_foundational_similarity_adapter(driver=_neo4j_driver())


def _neo4j_foundational_similarity_adapter(
    driver: Driver,
) -> Neo4jFoundationalSimilarityAdapter:
    return Neo4jFoundationalSimilarityAdapter(driver=driver)


def _neo4j_onehot_encoding_adapter(driver: Driver) -> Neo4jOnehotEncodingAdapter:
    return Neo4jOnehotEncodingAdapter(driver=driver)


def neo4j_drug_aliases_adapter() -> Neo4jDrugAliasesAdapter:
    return _neo4j_drug_aliases_adapter(driver=_neo4j_driver())


def _neo4j_drug_aliases_adapter(driver: Driver) -> Neo4jDrugAliasesAdapter:
    return Neo4jDrugAliasesAdapter(driver=driver)


def neo4j_patent_query_adapter() -> Neo4jPatentQueryAdapter:
    return _neo4j_patent_query_adapter(driver=_neo4j_driver())


def _neo4j_patent_query_adapter(
    driver: Driver,
) -> Neo4jPatentQueryAdapter:
    return Neo4jPatentQueryAdapter(driver=driver)


def neo4j_pubmed_count_adapter() -> Neo4jPubmedCountAdapter:
    return _neo4j_pubmed_count_adapter(driver=_neo4j_driver())


def _neo4j_pubmed_count_adapter(
    driver: Driver,
) -> Neo4jPubmedCountAdapter:
    return Neo4jPubmedCountAdapter(driver=driver)


def neo4j_pubmed_query_adapter() -> Neo4jPubmedQueryAdapter:
    return _neo4j_pubmed_query_adapter(driver=_neo4j_driver())


def _neo4j_pubmed_query_adapter(
    driver: Driver,
) -> Neo4jPubmedQueryAdapter:
    return Neo4jPubmedQueryAdapter(driver=driver)


def _node_id_lookup_mapper() -> NodeIdLookupMapper:
    return NodeIdLookupMapper()


def _node_details_mapper() -> NodeDetailsMapper:
    return NodeDetailsMapper()


def drug_aliases_result_mapper() -> DrugAliasesResultMapper:
    return DrugAliasesResultMapper()


def _neo4j_missing_node_index_embedding_adapter(
    driver: Driver,
) -> Neo4jMissingNodeIndexEmbeddingAdapter:
    return Neo4jMissingNodeIndexEmbeddingAdapter(driver=driver)


def _foundational_node_embedding_provider() -> FoundationalNodeEmbeddingProvider:
    return FoundationalNodeEmbeddingProvider(model_cache_dir=model_cache_dir())


def drug_product_names_loader() -> DrugProductNamesLoader:
    return DrugProductNamesLoader()


def drug_synonyms_loader() -> DrugSynonymsLoader:
    return DrugSynonymsLoader()


def graph_mapper() -> GraphMapper:
    return GraphMapper()


def facts_mapper() -> FactsMapper:
    return FactsMapper()


def patent_search_result_mapper() -> PatentSearchResultMapper:
    return PatentSearchResultMapper()


def pubmed_search_result_mapper() -> PubmedSearchResultMapper:
    return PubmedSearchResultMapper()


def drug_aliases_update_orchestrator() -> DrugAliasesUpdateOrchestrator:
    return _drug_aliases_update_orchestrator(
        drug_product_names_loader=drug_product_names_loader(),
        drug_synonyms_loader=drug_synonyms_loader(),
        neo4j_drug_aliases_adapter=neo4j_drug_aliases_adapter(),
    )


def _drug_aliases_update_orchestrator(
    drug_product_names_loader: DrugProductNamesLoader,
    drug_synonyms_loader: DrugSynonymsLoader,
    neo4j_drug_aliases_adapter: Neo4jDrugAliasesAdapter,
) -> DrugAliasesUpdateOrchestrator:
    return DrugAliasesUpdateOrchestrator(
        drug_product_names_loader=drug_product_names_loader,
        drug_synonyms_loader=drug_synonyms_loader,
        neo4j_drug_aliases_adapter=neo4j_drug_aliases_adapter,
    )


def foundational_node_fix_orchestrator():
    driver = _neo4j_driver()
    return _foundational_node_fix_orchestrator(
        foundational_node_embedding_provider=_foundational_node_embedding_provider(),
        neo4j_foundational_node_adapter=_neo4j_foundational_node_adapter(driver),
        neo4j_onehot_encoding_adapter=_neo4j_onehot_encoding_adapter(driver),
        neo4j_missing_node_index_embedding_adapter=_neo4j_missing_node_index_embedding_adapter(
            driver
        ),
    )


def _foundational_node_fix_orchestrator(
    foundational_node_embedding_provider: FoundationalNodeEmbeddingProvider,
    neo4j_foundational_node_adapter: Neo4jFoundationalNodeAdapter,
    neo4j_onehot_encoding_adapter: Neo4jOnehotEncodingAdapter,
    neo4j_missing_node_index_embedding_adapter: Neo4jMissingNodeIndexEmbeddingAdapter,
) -> FoundationalNodeFixOrchestrator:
    return FoundationalNodeFixOrchestrator(
        foundational_node_embedding_provider=foundational_node_embedding_provider,
        neo4j_foundational_node_adapter=neo4j_foundational_node_adapter,
        neo4j_onehot_encoding_adapter=neo4j_onehot_encoding_adapter,
        neo4j_missing_node_index_embedding_adapter=neo4j_missing_node_index_embedding_adapter,
    )


def _neo4j_list_embeddings_adapter(driver: Driver) -> Neo4jListEmbeddingsAdapter:
    return Neo4jListEmbeddingsAdapter(driver=driver)


def patent_id_export_writer() -> PatentIdExportWriter:
    return PatentIdExportWriter()


def _tsv_embeddings_writer() -> TsvEmbeddingsWriter:
    return TsvEmbeddingsWriter()


def list_embeddings_provider() -> ListEmbeddingsProvider:
    driver = _neo4j_driver()
    return ListEmbeddingsProvider(
        neo4j_list_embeddings_adapter=_neo4j_list_embeddings_adapter(driver=driver),
        tsv_embeddings_writer=_tsv_embeddings_writer(),
    )


def foundational_n_hop_provider() -> FoundationalNHopProvider:
    return _foundational_n_hop_provider(
        neo4j_foundational_n_hop_adapter=neo4j_foundational_n_hop_adapter(),
        graph_mapper=graph_mapper(),
    )


def _foundational_n_hop_provider(
    neo4j_foundational_n_hop_adapter: Neo4jFoundationalNHopAdapter,
    graph_mapper: GraphMapper,
) -> FoundationalNHopProvider:
    return FoundationalNHopProvider(
        neo4j_foundational_n_hop_adapter=neo4j_foundational_n_hop_adapter,
        graph_mapper=graph_mapper,
    )


def foundational_path_provider() -> FoundationalPathProvider:
    return _foundational_path_provider(
        neo4j_foundational_path_adapter=neo4j_foundational_path_adapter(),
    )


def _foundational_path_provider(
    neo4j_foundational_path_adapter: Neo4jFoundationalPathAdapter,
) -> FoundationalPathProvider:
    return FoundationalPathProvider(
        neo4j_foundational_path_adapter=neo4j_foundational_path_adapter,
    )


def foundational_node_id_provider() -> FoundationalNodeIdProvider:
    return _foundational_node_id_provider(
        neo4j_foundational_node_adapter=neo4j_foundational_node_adapter(),
        node_id_lookup_mapper=_node_id_lookup_mapper(),
    )


def _foundational_node_id_provider(
    neo4j_foundational_node_adapter: Neo4jFoundationalNodeAdapter,
    node_id_lookup_mapper: NodeIdLookupMapper,
) -> FoundationalNodeIdProvider:
    return FoundationalNodeIdProvider(
        neo4j_foundational_node_adapter=neo4j_foundational_node_adapter,
        node_id_lookup_mapper=node_id_lookup_mapper,
    )


def foundational_node_details_provider() -> FoundationalNodeDetailsProvider:
    return _foundational_node_details_provider(
        neo4j_foundational_node_details_adapter=neo4j_foundational_node_details_adapter(),
        node_details_mapper=_node_details_mapper(),
    )


def _foundational_node_details_provider(
    neo4j_foundational_node_details_adapter: Neo4jFoundationalNodeDetailsAdapter,
    node_details_mapper: NodeDetailsMapper,
) -> FoundationalNodeDetailsProvider:
    return FoundationalNodeDetailsProvider(
        neo4j_foundational_node_details_adapter=neo4j_foundational_node_details_adapter,
        node_details_mapper=node_details_mapper,
    )


def foundational_facts_orchestrator() -> FoundationalFactsOrchestrator:
    return _foundational_facts_orchestrator(
        foundational_n_hop_provider=foundational_n_hop_provider(),
        facts_mapper=facts_mapper(),
    )


def _foundational_facts_orchestrator(
    foundational_n_hop_provider: FoundationalNHopProvider,
    facts_mapper: FactsMapper,
) -> FoundationalFactsOrchestrator:
    return FoundationalFactsOrchestrator(
        foundational_n_hop_provider=foundational_n_hop_provider,
        facts_mapper=facts_mapper,
    )
