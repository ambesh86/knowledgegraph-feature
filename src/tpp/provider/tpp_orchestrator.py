import logging
from pathlib import Path

from infra.util.file_util import move_failed, move_succeeded
from tpp.analyze.tpp_knowledge_graph_analyzer import TppKnowledgeGraphAnalyzer
from tpp.infra.db.adapter.neo4j_tpp_adapter import Neo4jTppAdapter
from tpp.infra.embedding.tpp_embedding_provider import TppEmbeddingProvider
from tpp.model.tpp import Tpp
from tpp.mapper.tpp_mapper import TppMapper

logger = logging.getLogger(__name__)


class TppOrchestrator:
    """
    class to orchestrator all the steps to parse, analyze and store tpp files
    """

    def __init__(
        self,
        tpp_mapper: TppMapper,
        tpp_embedding_provider: TppEmbeddingProvider,
        neo4j_tpp_adapter: Neo4jTppAdapter,
        tpp_knowledge_graph_analyzer: TppKnowledgeGraphAnalyzer,
    ):
        self.tpp_mapper = tpp_mapper
        self.tpp_embedding_provider = tpp_embedding_provider
        self.neo4j_tpp_adapter = neo4j_tpp_adapter
        self.tpp_knowledge_graph_analyzer = tpp_knowledge_graph_analyzer

    def process_and_move(
        self, files: list[Path], with_analysis_and_linking: bool = True
    ) -> None:
        """
        process all files and move to success or failed folders
        """
        for pptx in files:
            logger.info(f"processing {pptx}")
            try:
                self.process(
                    tpp_file=pptx, with_analysis_and_linking=with_analysis_and_linking
                )
                move_succeeded(pptx)
            except Exception as e:
                logger.warning(f"error processing {pptx}")
                logger.warning(e)
                move_failed(pptx)

    def process(
        self, tpp_file: Path, with_analysis_and_linking: bool = True
    ) -> set[str] | None:
        """
        parse, create embeddings and store target product profiles
        a pptx file can contain multiple tpps, one per slide

        return a set of node ids
        """
        if tpp_file is None:
            return None

        tpps = self.tpp_mapper.map(tpp_file)
        if tpps is None:
            logger.warning(f"no tpps found in file {tpp_file}, skipping...")
            return None

        tpps = self._apply_embeddings(tpps)
        self._log_tpps(tpps)
        node_ids = self._ingest(tpps)

        if with_analysis_and_linking:
            logger.info(f"analyzing and linking {len(tpps)}")
            self.tpp_knowledge_graph_analyzer.analyze(tpps)
        return node_ids

    def _apply_embeddings(self, tpps: set[Tpp]) -> set[Tpp]:
        """
        generate embeddings and set in the value in the given tpps
        """
        for tpp in tpps:
            self.tpp_embedding_provider.apply_embeddings(tpp=tpp)
        return tpps

    def _ingest(self, tpps: set[Tpp]) -> set[str]:
        node_ids = set()
        for tpp in tpps:
            node_id = self.neo4j_tpp_adapter.upsert(tpp)
            node_ids.add(node_id)

        return node_ids

    def _log_tpps(self, tpps: set[Tpp]) -> None:
        for tpp in tpps:
            logger.info(f"---- Found TPP")
            logger.info(f"{tpp.product_description} {tpp.threaputic_area}")
            if tpp.questions is None:
                logger.info(f"no questions found")
                continue
            for question in tpp.questions:
                logger.info(f"---- Question: {question.question_type.name}")
                logger.debug(f"ideal: {question.ideal}")
                logger.debug(f"acceptable: {question.acceptable}")
                logger.debug(f"excluded: {question.excluded}")
                logger.debug(f"embeddings shape: {question.embeddings.shape}")
