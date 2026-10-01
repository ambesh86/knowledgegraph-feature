from abc import abstractmethod
import logging
from tqdm import tqdm

from pymilvus import CollectionSchema, DataType, MilvusClient

from graph.model.summary import Summary
from graph.infra.embedding.summary_embedding_provider import SummaryEmbeddingProvider
from graph.infra.db.vector_adapter import VectorAdapter

logger = logging.getLogger(__name__)


class MilvusVectorAdapter(VectorAdapter):
    def __init__(
        self,
        client: MilvusClient,
        summary_embedding_provider: SummaryEmbeddingProvider,
        collection_name: str,
    ):
        self.client = client
        self.collection_name = collection_name
        self.summary_embedding_provider = summary_embedding_provider

    def ingest(self, summaries: list[Summary], embedding_dim: int = 256) -> dict:
        self._ensure_collection(self.collection_name, embedding_dim)

        items = []
        for i, summary in enumerate(tqdm(summaries, desc="Creating embeddings")):
            embedding = self.summary_embedding_provider.summary_to_embedding(summary)
            findings = []
            for finding in summary.findings:
                findings.append(
                    {
                        "explanation": finding.explanation,
                        "summary": finding.summary,
                    }
                )
            item = {
                "id": i,
                "summary_id": summary.id,
                "vector": embedding,
                "summary": {
                    "title": summary.title,
                    "summary": summary.summary,
                    "rating": summary.rating,
                    "rating_explanation": summary.rating_explanation,
                    "findings": findings,
                },
            }
            items.append(item)

        for item in items:
            logger.debug(f"{item}")

        resp = self.client.insert(collection_name=self.collection_name, data=items)
        logger.info(f"inserted record(s): {resp["insert_count"]}")
        logger.debug(f"inserted id(s): {resp["ids"]}")
        self._create_and_list_indexes(
            collection_name=self.collection_name, embedding_dim=embedding_dim
        )
        logger.info(
            "ingest finished. Schema created, items are inserted and indexes created"
        )
        return resp

    def _ensure_collection(self, collection_name: str, embedding_dim: int) -> None:
        if self.client.has_collection(collection_name):
            logger.warning(f"dropping collection {collection_name}")
            self.client.drop_collection(collection_name)

        logger.info(f"creating collection {collection_name}")
        schema = self._create_schema(embedding_dim=embedding_dim)
        # https://milvus.io/docs/index-vector-fields.md?tab=floating
        # todo: create index
        # https://milvus.io/docs/index-vector-fields.md#Index-a-Collection
        self.client.create_collection(
            collection_name=collection_name,
            dimension=embedding_dim,
            schema=schema,
            metric_type="IP",  # Inner product distance
            consistency_level="Strong",  # Strong consistency level
        )

    def _create_schema(self, embedding_dim: int) -> CollectionSchema:
        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
        )

        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(
            field_name="summary_id", datatype=DataType.VARCHAR, max_length=64
        )
        schema.add_field(
            field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=embedding_dim
        )
        schema.add_field(field_name="summary", datatype=DataType.JSON)
        return schema

    def _create_and_list_indexes(self, collection_name: str, embedding_dim: int):
        logger.info(f"creating indexes...")
        # https://milvus.io/api-reference/pymilvus/v2.4.x/MilvusClient/Management/add_index.md
        # 3. Create indx parameters
        index_params = self.client.prepare_index_params()

        index_params.add_index(field_name="id", index_type="STL_SORT")

        index_params.add_index(field_name="summary_id", index_type="INVERTED")

        index_params.add_index(
            field_name="vector",
            index_type="IVF_FLAT",
            metric_type="COSINE",
            params={"nlist": embedding_dim},
        )

        self.client.create_index(
            collection_name=collection_name, index_params=index_params, sync=False
        )

        self.client.list_indexes(collection_name=collection_name)
