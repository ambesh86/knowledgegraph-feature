from graph.util.node_util import normalize_node_label


TPP_NODE_TYPE = normalize_node_label("csl_tpp")
TPP_QUESTION_NODE_TYPE = normalize_node_label("csl_tpp_question")

TPP_QUESTION_REL_TYPE = normalize_node_label("has_associated_question")
TPP_QUESTION_REL_TYPE = normalize_node_label("has_associated_question")

TPP_NODE_PRIMARY_KEY = "node_id"


TPP_SUMMARY_NODE_TYPE = normalize_node_label("summary")
TPP_SUMMARY_FINDING_NODE_TYPE = normalize_node_label("summary_finding")
TPP_SUMMARY_REL_TYPE = normalize_node_label("has_summary")
TPP_SUMMARY_FINDING_REL_TYPE = normalize_node_label("has_finding")
TPP_EXTRACTION_REL_TYPE = normalize_node_label("has_publication")
