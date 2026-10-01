// Match hemophilia variants
MATCH (dse:disease)
WHERE dse.node_name =~ '(i?).*hemophilia.*'
RETURN dse