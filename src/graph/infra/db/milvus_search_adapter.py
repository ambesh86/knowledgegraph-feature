import json
import logging

from torch import Tensor
from pymilvus import connections, Collection

logger = logging.getLogger(__name__)


class MilvusSearchAdapter:
    def __init__(self, host="localhost", port="19530", collection_name="pubmed"):
        """
        Initialize the Milvus RAG searcher

        Args:
            host: Milvus server host
            port: Milvus server port
            collection_name: Name of the collection to search
        """
        # Connect to Milvus
        try:
            connections.connect(alias="default", host=host, port=port)
            logger.info(f"Connected to Milvus at {host}:{port}")
        except Exception as e:
            logger.error(f"Error connecting to Milvus: {e}")
            raise

        # Load the collection
        self.collection = Collection(collection_name)
        self.collection.load()
        logger.info(f"Collection '{collection_name}' loaded successfully")

    def search_similar_summaries(
        self, query_vector: Tensor, top_k=10, output_fields=None
    ):
        """
        Search for semantically similar summaries

        Args:
            query_string: The search query
            top_k: Number of top results to return
            output_fields: List of fields to return (default: all fields)

        Returns:
            List of matching summaries with similarity scores
        """
        if output_fields is None:
            output_fields = ["id", "summary_id", "summary"]

        # Define search parameters
        search_params = {
            "metric_type": "IP",  # Inner Product
            # "params": {"nprobe": 10}  # Adjust based on your index type
        }

        # Perform the search
        results = self.collection.search(
            data=query_vector.tolist(),
            anns_field="vector",  # The vector field to search
            param=search_params,
            limit=top_k,
            output_fields=output_fields,
        )

        # Format the results
        formatted_results = []
        for i, hit in enumerate(results[0]):
            result_data = {
                "rank": i + 1,
                "score": hit.score,  # Similarity score (lower is better for L2)
                "id": hit.entity.get("id"),
                "summary_id": hit.entity.get("summary_id"),
                "summary": hit.entity.get("summary"),
            }
            formatted_results.append(result_data)

        return formatted_results

    def search_with_filters(
        self, query_vector: Tensor, top_k=10, filter_conditions=None
    ):
        """
        Search with additional filter conditions

        Args:
            query_string: The search query
            top_k: Number of top results to return
            filter_conditions: Optional filter expression (e.g., "summary_id in ['id1', 'id2']")

        Returns:
            List of matching summaries
        """

        # Define search parameters
        search_params = {
            "metric_type": "IP",
            # "params": {"nprobe": 10}
        }

        # Prepare search expression
        search_args = {
            "data": query_vector.tolist(),
            "anns_field": "vector",
            "param": search_params,
            "limit": top_k,
            "output_fields": ["id", "summary_id", "summary"],
        }

        # Add filter if provided
        if filter_conditions:
            search_args["expr"] = filter_conditions

        # Perform the search
        results = self.collection.search(**search_args)

        # Format results
        formatted_results = []
        for i, hit in enumerate(results[0]):
            result_data = {
                "rank": i + 1,
                "score": hit.score,
                "id": hit.entity.get("id"),
                "summary_id": hit.entity.get("summary_id"),
                "summary": hit.entity.get("summary"),
            }
            formatted_results.append(result_data)

        return formatted_results

    def print_results(self, results, query_string):
        """Pretty print the search results"""
        logger.info(f"\n🔍 Search Results for: '{query_string}'\n")
        logger.info("=" * 80)

        for result in results:
            logger.info(f"Rank: {result['rank']}")
            logger.info(f"Score: {result['score']:.4f}")
            logger.info(f"ID: {result['id']}")
            logger.info(f"Summary ID: {result['summary_id']}")

            # Handle the summary JSON field
            summary_data = result["summary"]
            if isinstance(summary_data, str):
                try:
                    summary_data = json.loads(summary_data)
                except:
                    pass

            # Extract text from summary JSON
            if isinstance(summary_data, dict):
                # Try common keys for summary text
                summary_text = summary_data.get(
                    "text",
                    summary_data.get(
                        "summary", summary_data.get("abstract", str(summary_data))
                    ),
                )
            else:
                summary_text = str(summary_data)

            # Truncate long summaries for display
            if len(summary_text) > 200:
                summary_text = summary_text[:200] + "..."

            logger.info(f"Summary: {summary_text}")
            logger.info("-" * 80)

    def close(self):
        """Close the connection"""
        connections.disconnect(alias="default")
        logger.info("Disconnected from Milvus")
