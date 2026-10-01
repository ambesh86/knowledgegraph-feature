from pathlib import Path

from neo4j import Driver
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from pubmed.helper.const import DEFAULT_BIO_EMAIL
from pubmed.mapper.article_mapper import ArticleMapper
from pubmed.provider.pubmed_download_provider import PubmedDownloadProvider
from pubmed.provider.pubmed_fetch_provider import PubmedFetchProvider
from pubmed.provider.pubmed_orchestrator import PubmedOrchestrator
from pubmed.provider.pubmed_search_provider import PubmedSearchProvider
from pubmed.infra.db.neo4j_article_adapter import Neo4jArticleAdapter
from pubmed.embedding.article_embedding_provider import ArticleEmbeddingProvider
from pubmed.provider.pubmed_fix_orchestrator import PubmedFixOrchestrator
from pubmed.infra.db.neo4j_affiliation_adapter import Neo4jAffiliationAdapter
from clinicaltrail.infra.db.neo4j_clinical_trial_adapter import (
    Neo4jClinicalTrialAdapter,
)


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def _neo4j_article_adapter(driver: Driver) -> Neo4jArticleAdapter:
    return Neo4jArticleAdapter(driver=driver)


def _neo4j_clinical_trial_adapter(driver: Driver) -> Neo4jClinicalTrialAdapter:
    return Neo4jClinicalTrialAdapter(driver=driver)


def _neo4j_affiliation_adapter(driver: Driver) -> Neo4jAffiliationAdapter:
    return Neo4jAffiliationAdapter(driver=driver)


def _article_embedding_provider() -> ArticleEmbeddingProvider:
    return ArticleEmbeddingProvider()


def _default_bio_email():
    return DEFAULT_BIO_EMAIL


def _article_mapper():
    return ArticleMapper()


def _pubmed_fetch_provider(article_mapper: ArticleMapper):
    return PubmedFetchProvider(
        article_mapper=article_mapper, email=_default_bio_email()
    )


def _pubmed_search_provider():
    return PubmedSearchProvider(email=_default_bio_email())


def _pubmed_download_provider():
    return PubmedDownloadProvider(download_dest=Path("./resources/data/pubmed"))


def pubmed_orchestrator():
    driver = _neo4j_driver()
    return _pubmed_orchestrator(
        pubmed_search_provider=_pubmed_search_provider(),
        pubmed_fetch_provider=_pubmed_fetch_provider(_article_mapper()),
        pubmed_download_provider=_pubmed_download_provider(),
        neo4j_article_adapter=_neo4j_article_adapter(driver),
    )


def _pubmed_orchestrator(
    pubmed_search_provider: PubmedSearchProvider,
    pubmed_fetch_provider: PubmedFetchProvider,
    pubmed_download_provider: PubmedDownloadProvider,
    neo4j_article_adapter: Neo4jArticleAdapter,
):
    return PubmedOrchestrator(
        pubmed_search_provider=pubmed_search_provider,
        pubmed_fetch_provider=pubmed_fetch_provider,
        pubmed_download_provider=pubmed_download_provider,
        neo4j_article_adapter=neo4j_article_adapter,
    )


def pubmed_fix_orchestrator():
    driver = _neo4j_driver()
    return _pubmed_fix_orchestrator(
        pubmed_fetch_provider=_pubmed_fetch_provider(_article_mapper()),
        article_embedding_provider=_article_embedding_provider(),
        neo4j_article_adapter=_neo4j_article_adapter(driver),
        neo4j_clinical_trial_adapter=_neo4j_clinical_trial_adapter(driver),
        neo4j_affiliation_adapter=_neo4j_affiliation_adapter(driver),
    )


def _pubmed_fix_orchestrator(
    pubmed_fetch_provider: PubmedFetchProvider,
    article_embedding_provider: ArticleEmbeddingProvider,
    neo4j_article_adapter: Neo4jArticleAdapter,
    neo4j_clinical_trial_adapter: Neo4jClinicalTrialAdapter,
    neo4j_affiliation_adapter: Neo4jAffiliationAdapter,
) -> PubmedFixOrchestrator:
    return PubmedFixOrchestrator(
        pubmed_fetch_provider=pubmed_fetch_provider,
        article_embedding_provider=article_embedding_provider,
        neo4j_article_adapter=neo4j_article_adapter,
        neo4j_clinical_trial_adapter=neo4j_clinical_trial_adapter,
        neo4j_affiliation_adapter=neo4j_affiliation_adapter,
    )
