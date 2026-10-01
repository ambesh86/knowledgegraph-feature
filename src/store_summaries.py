import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pymilvus import MilvusClient

from document.load.stored_summaries_loader import StoredSummariesLoader
from graph.mapper.summaries_parser import SummariesParser
from graph.infra.embedding.summary_embedding_provider import SummaryEmbeddingProvider
from graph.infra.db.milvus_vector_adapter import MilvusVectorAdapter
from graph.infra.db.vector_db_connection_factory import VectorDbConnectionFactory

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    """
    Read summaries and store into the vector database
    """
    load_dotenv()

    summaries_parser = SummariesParser()
    stored_summaries_loader = StoredSummariesLoader(summaries_parser=summaries_parser)
    client = _client()
    key = "HF_HUB_CACHE"
    value = os.environ[key] if key in os.environ else None
    vector_adapter = MilvusVectorAdapter(
        client, SummaryEmbeddingProvider(model_cache_dir=value), "pubmed"
    )

    summaries = stored_summaries_loader.load(data_dirs=_data_dirs())
    logger.info(f"ingesting total summaries: {len(summaries)}")
    vector_adapter.ingest(summaries, embedding_dim=384)


def _client() -> MilvusClient:
    milvus_uri = os.environ["MILVUS_URI"]
    milvus_token = os.environ["MILVUS_TOKEN"]
    return VectorDbConnectionFactory.milvus_client(uri=milvus_uri, token=milvus_token)


def _data_dirs() -> list[Path]:
    data_root = Path("./output/checkpoint/pubmed")
    data_dirs = [
        "031123c65bbaef4e772612ad00115ddb",
        "03fdb0da8210efedcaa6bec31f75ba8d",
        "0cda4ea0583deb2b278532416c7bb337",
        "113fb4e6402383b3df5e2eaef2aa824a",
        "160d4427a7f189ad0dbde63f475f541e",
        "1aa50c806d814996dc1de463d47510ee",
        "1afead98d000859869e4deec75fa16e3",
        "1d78fd0c4c5c2334e38e507ce3be12b3",
        "240c6e6c57c9a10740585f3f1bc27419",
        "25280ea77135c4945e820622ca7d47d1",
        "253478261d31fec91323769237cc123d",
        "324f0b71c437662c63b207310b5e2c0f",
        "33c76652210d1704b6066726808f7a9e",
        "376d70473b97438474e2bb8c7dcec012",
        "3ade60cdfc426ddcec3707ae778620b5",
        "40136d279ad7f6a1c2b0a0bab760e907",
        "68e7028d9ad8f32bb644c9a90c93cd7b",
        "6e2de063562384dce1d312593bb36a06",
        "72538bf077561317f489b80fc869f185",
        "763c83da8cb154b737b49f1401656120",
        "7875054d18e2f602e61d0179e85f7b02",
        "792ed1b06c360967a2d542bb964da001",
        "7d9255c015b5243c291d1c00ce38a972",
        "8361813b54f77d68ccfc6c79adbdaf62",
        "844b251c3e28263c250ecd66221575e0",
        "8de4e14f04309110ba0066f584fb0fdc",
        "8fcf8e86f5ec7e7c9d2631016208a1a8",
        "9170716feefdfc65b194939e68fc8db7",
        "930aadd92907a1cfb98c71daaeea474a",
        "9640387f9f73df51282c37c8418bb0f6",
        "aad9f3ede809f2dd66eb18d562507956",
        "acaf9f56b9244e437543b81b1294d914",
        "c07cda67dfa90e9143e4a74a148c019a",
        "c30729a44199d8a447cbdb211256ccc9",
        "e4e9a73e287908041a92580d768cf7b0",
        "ea78edd49b31cbd5f09a89aae51eb81f",
        "eaec4601ec79430fcccda8e30374f6f8",
        "f3dc411e3d1626d20b21bec727bcb840",
        "f9f235eea8591a655b8fad638d6f5a00",
        "fd67628c3b49635b38fd3fa4aefc0781",
        "fda3d3f37c9b500318e5a1d88622cb82",
    ]
    dirs = [(data_root / x) for x in data_dirs]
    return dirs


if __name__ == "__main__":
    main()
