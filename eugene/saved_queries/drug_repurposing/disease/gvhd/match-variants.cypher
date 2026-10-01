// Match gvhd variants
MATCH (n:disease)
WHERE n.node_name =~ '(?i).*aGVHD.*' OR
n.node_name =~ '(?i).*cGVHD.*' OR
n.node_name =~ '(?i).*Graft.*Host Disease.*'
RETURN n