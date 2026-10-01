from pymilvus import MilvusClient


class VectorDbConnectionFactory:
    _MILVUS_CLIENT = None

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    @classmethod
    def instance(cls) -> MilvusClient:
        return VectorDbConnectionFactory.milvus_client()

    @classmethod
    def milvus_client(
        cls, uri: str = ".db/knowledge_graph_db", token: str = ""
    ) -> MilvusClient:
        if cls._MILVUS_CLIENT is None:
            client = MilvusClient(uri=uri, token=token)
            cls._MILVUS_CLIENT = client
        return cls._MILVUS_CLIENT
