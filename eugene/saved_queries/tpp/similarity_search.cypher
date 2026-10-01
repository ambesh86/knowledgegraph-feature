
# node_id: 'node_id: dd485875e4b59bc35883471d7fc9f01d'
# node_id: 'node_id: 2b991311ba1be0062e29509a1e140329'
# pgpub_embeddings_index
# csl_tpp_embeddings_index
MATCH (tpp:csl_tpp { node_id: '2b991311ba1be0062e29509a1e140329' })
CALL db.index.vector.queryNodes('pgpub_embeddings_index', 200, tpp.embeddings)
YIELD node, score
RETURN score, tpp.product_description, node.application_number_text, node.abstract, node.claims;



// query for patents related to a given csl tpp around hematology
MATCH (tpp:csl_tpp { node_id: 'dd485875e4b59bc35883471d7fc9f01d' })
CALL db.index.vector.queryNodes('pgpub_embeddings_index', 200, tpp.embeddings)
YIELD node, score
RETURN score, tpp.product_description as tpp_description, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims;


// 0.5798563957214355	"Hemophilia A non-viral, in vivo GenMeds"	"17513918"
//  17513918 should rank higher
// patents application claims for hematology
MATCH (n:uspto_pgpub)
WHERE n.application_number_text IN [
    '13374328',
    '13387531',
    '15751166',
    '16925933',
    '17236834',
    '17513918',
    '17518590',
    '17681855',
    '18096449',
    '18569895'
]
RETURN n


// query for patents related to a given csl tpp around hematology MOA question
MATCH (tpp:csl_tpp { node_id: 'dd485875e4b59bc35883471d7fc9f01d' })-[]-(tpp_question:csl_tpp_question { question_type: 'MECANISM_OF_ACTION'})
CALL db.index.vector.queryNodes('pgpub_embeddings_index', 200, tpp_question.embeddings)
YIELD node, score
RETURN score, tpp.product_description as tpp_description, tpp_question.ideal as tpp_ideal_moa, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims;


// query for patents related to a given csl tpp around hematology INDICATION question
MATCH (tpp:csl_tpp { node_id: 'dd485875e4b59bc35883471d7fc9f01d' })-[]-(tpp_question:csl_tpp_question { question_type: 'INDICATION'})
CALL db.index.vector.queryNodes('pgpub_embeddings_index', 200, tpp_question.embeddings)
YIELD node, score
RETURN score, tpp.product_description as tpp_description, tpp_question.ideal as tpp_ideal_indication, node.application_number_text as patent_application_no, node.abstract as patent_abstract, node.claims as patent_claims;
