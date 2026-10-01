import logging

from pubmed.provider.pubmed_fetch_provider import PubmedFetchProvider
from pubmed.infra.db.neo4j_article_adapter import Neo4jArticleAdapter
from pubmed.infra.db.neo4j_affiliation_adapter import Neo4jAffiliationAdapter
from pubmed.embedding.article_embedding_provider import ArticleEmbeddingProvider
from graph.analyze.summary_orchestrator import SummaryOrchestrator
from pubmed.helper.util import extract_pmcid
from pubmed.model.article import Article
from document.parse.parsed_file import ParsedFile
from clinicaltrail.infra.db.neo4j_clinical_trial_adapter import (
    Neo4jClinicalTrialAdapter,
)
from pubmed.model.affiliation import Affiliation

logger = logging.getLogger(__name__)


class PubmedFixOrchestrator(SummaryOrchestrator):
    """
    Fix or update fields for pubmed document graph
    """

    def __init__(
        self,
        pubmed_fetch_provider: PubmedFetchProvider,
        article_embedding_provider: ArticleEmbeddingProvider,
        neo4j_article_adapter: Neo4jArticleAdapter,
        neo4j_clinical_trial_adapter: Neo4jClinicalTrialAdapter,
        neo4j_affiliation_adapter: Neo4jAffiliationAdapter,
    ):

        self.pubmed_fetch_provider = pubmed_fetch_provider
        self.article_embedding_provider = article_embedding_provider
        self.neo4j_article_adapter = neo4j_article_adapter
        self.neo4j_clinical_trial_adapter = neo4j_clinical_trial_adapter
        self.neo4j_affiliation_adapter = neo4j_affiliation_adapter

    def summarize(self, parsed_file: ParsedFile) -> None:
        if parsed_file is None:
            logger.warning(f"parsed file is null, moving on...")
            return

        pmcid = extract_pmcid(parsed_file.path)
        if pmcid is None or len(pmcid) == 0:
            logger.info(
                "skipping linking entities step, because pmcid is empty. Check the file name and ensure it starts with a pmcid"
            )
            return

        self.update_article(pmcid)

    def update_articles(self, pmcids: list[str]) -> None:
        for pmcid in pmcids:
            self.update_article(pmcid)

    def update_article(self, pmcid: str) -> None:
        logger.info(f"step 1/5 - lookup article for pmcid: {pmcid}")
        article = self._lookup_pubmed_article(pmcid)
        if article is None:
            logger.info(f"skipping remaining steps on {pmcid} article is None...")
            return None

        logger.info(f"step 2/5 - generating article embeddings pmcid: {pmcid}")
        article = self._generate_pubmed_embeddings(article)
        # todo: consider doing merge and linking across a single transaction
        logger.info(f"step 3/5 - updating article pmcid: {pmcid}")
        self.neo4j_article_adapter.upsert_article(article=article)

        num_affiliations = len(
            article.affiliations
            if article is not None and article.affiliations is not None
            else []
        )
        logger.info(
            f"step 4/5 - upserting and linking {num_affiliations} affilication(s) to article pmcid: {pmcid}"
        )
        self._link_affiliations(pmcid=pmcid, affiliations=article.affiliations)

        num_nct_ids = len(article.nct_ids if article.nct_ids is not None else [])
        logger.info(
            f"step 5/5 - linking {num_nct_ids} clinical trials to article pmcid: {pmcid}"
        )
        self._link_clinical_trials(article.pmcid, article.nct_ids)
        logger.info(f"finished updating article pmcid: {pmcid}")

    def _lookup_pubmed_article(self, pmcid: str) -> Article | None:
        logger.info(f"fetching for pmcid={pmcid}...")
        article = self.pubmed_fetch_provider.fetch_by_id(pmcid=pmcid)
        logger.debug(f"article: {article}")
        return article

    def _generate_pubmed_embeddings(self, article: Article | None) -> Article | None:
        if article is None:
            return None

        [title_embeddings, keywords_embeddings, merged_embeddings] = (
            self.article_embedding_provider.to_embedding(article=article)
        )
        article.title_embeddings = title_embeddings
        article.keywords_embeddings = keywords_embeddings
        article.merged_embeddings = merged_embeddings
        return article

    def _link_clinical_trials(self, pmcid: int, nct_ids: set[str] | None) -> None:
        if nct_ids is None:
            return None

        failed_ids = set()
        success_ids = set()
        for nct_id in nct_ids:
            clinical_trial_node_id = (
                self.neo4j_clinical_trial_adapter.find_node_id_by_nct(nct_id)
            )
            if clinical_trial_node_id is None:
                failed_ids.add(nct_id)
                continue
            self.neo4j_article_adapter.link_article_and_clinical_trial(
                str(pmcid), clinical_trial_node_id
            )
            success_ids.add(nct_id)

        if len(failed_ids) > 0:
            logger.warning(
                f"Failed to link {len(failed_ids)}/{len(nct_ids)} clinical trial(s) to article pmcid: {pmcid}"
            )
            logger.warning(
                f"The database was missing clinical trials data for node(s):"
            )
            logger.warning(f"{failed_ids}")
        if len(success_ids) > 0:
            logger.info(f"Linked {len(success_ids)} clinical trial(s)")
            logger.info(f"Linked the following clinical trial ids:")
            logger.info(f"{success_ids}")

    def _link_affiliations(
        self, pmcid: str, affiliations: list[Affiliation] | None
    ) -> None:
        if affiliations is None:
            return None

        count = 0
        for affiliation in affiliations:
            affiliation_id = f"doc_{pmcid}_aff_{count}"
            count += 1
            affiliation.affiliation_id = affiliation_id
            node_id = self.neo4j_affiliation_adapter.upsert(
                pmcid=pmcid, affiliation=affiliation
            )
            if node_id is None:
                logger.warning(
                    f"Failed to link to article pmcid: {pmcid} to affiliation id: {affiliation_id}"
                )
                continue
