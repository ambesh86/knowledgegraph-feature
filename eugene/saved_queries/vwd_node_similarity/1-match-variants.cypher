// [1] Match VWD variants
MATCH (n:disease)
WHERE n.node_name = 'von Willebrand disease' OR
n.node_name = 'pseudo-von Willebrand disease' OR
n.node_name = 'Von Willebrand disease, X-linked form' OR
n.node_name = 'hereditary von Willebrand disease' OR
n.node_name = 'von Willebrand disease (hereditary or acquired)'
RETURN n