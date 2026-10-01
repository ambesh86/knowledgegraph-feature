from graph.util.node_util import normalize_node_label


CLINICAL_TRIAL_NODE_TYPE = "Clinical_Trial"

PUBMED_ARTICLE_SUMMARY_REL_TYPE = normalize_node_label("has_summary")
PUBMED_ARTICLE_SUMMARY_FINDING_REL_TYPE = normalize_node_label("has_finding")
PUBMED_ARTICLE_EXTRACTION_REL_TYPE = normalize_node_label("has_extraction")
