CREATE VECTOR INDEX csl_tpp_prediction_embeddings_index IF NOT EXISTS
    FOR (n:csl_tpp)
    ON n.prediction_embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 512,
        `vector.similarity_function`: 'cosine'
    }
};

CREATE VECTOR INDEX pgpub_prediction_embeddings_index IF NOT EXISTS
    FOR (n:uspto_pgpub)
    ON n.prediction_embeddings
    OPTIONS { indexConfig: {
        `vector.dimensions`: 512,
        `vector.similarity_function`: 'cosine'
    }
};

MATCH (tpp:csl_tpp { node_id: 'f6fb4e9335f4fb989cad45fefad267d7' })
CALL db.index.vector.queryNodes('pgpub_prediction_embeddings_index', 200, tpp.prediction_embeddings)
YIELD node, score
RETURN score, tpp.product_description as tpp_description, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims;


MATCH (tpp:csl_tpp { node_id: '2b991311ba1be0062e29509a1e140329' })
CALL db.index.vector.queryNodes('pgpub_prediction_embeddings_index', 200, tpp.prediction_embeddings)
YIELD node, score
RETURN score, tpp.product_description as tpp_description, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims;
