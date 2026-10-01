from graph.util.node_util import normalize_node_label
from foundation.conf.const import EMBEDDINGS_FIELD_NAME, GRAPH_EMBEDDINGS_FIELD_NAME


USPTO_PGPUB_NODE_TYPE = normalize_node_label("uspto_pgpub")

USPTO_PGPUB_PATENT_REL_TYPE = normalize_node_label("has_associated_document")

USPTO_PGPUB_GRAPH_EMBEDDINGS_INDEX_NAME = f"pgpub_{GRAPH_EMBEDDINGS_FIELD_NAME}_index"
USPTO_PGPUB_EMBEDDINGS_INDEX_NAME = f"pgpub_{EMBEDDINGS_FIELD_NAME}_index"


USPTO_PGPUB_SUMMARY_NODE_TYPE = normalize_node_label("summary")
USPTO_PGPUB_SUMMARY_FINDING_NODE_TYPE = normalize_node_label("summary_finding")
USPTO_PGPUB_SUMMARY_REL_TYPE = normalize_node_label("has_summary")
USPTO_PGPUB_SUMMARY_FINDING_REL_TYPE = normalize_node_label("has_finding")
USPTO_PGPUB_EXTRACTION_REL_TYPE = normalize_node_label("has_publication")

USPTO_PGPUB_NODE_PRIMARY_KEY = "application_number_text"
