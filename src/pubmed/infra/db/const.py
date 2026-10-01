from graph.util.node_util import normalize_node_label


PUBMED_ARTICLE_NODE_TYPE = normalize_node_label("pubmed_document")
PUBMED_ARTICLE_SUMMARY_NODE_TYPE = normalize_node_label("pubmed_summary")
PUBMED_ARTICLE_SUMMARY_FINDING_NODE_TYPE = normalize_node_label(
    "pubmed_summary_finding"
)
PUBMED_ARTICLE_AFFILIATION_NODE_TYPE = normalize_node_label("affiliation")

PUBMED_ARTICLE_SUMMARY_REL_TYPE = normalize_node_label("has_summary")
PUBMED_ARTICLE_SUMMARY_FINDING_REL_TYPE = normalize_node_label("has_finding")
PUBMED_ARTICLE_EXTRACTION_REL_TYPE = normalize_node_label("has_extraction")
