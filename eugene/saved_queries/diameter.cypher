MATCH (n)
WITH collect(n) AS nodes
UNWIND nodes AS a
UNWIND nodes AS b
WITH a, b
WHERE id(a) < id(b)
MATCH path=shortestPath((a)-[*]-(b))
RETURN length(path) AS diameter
ORDER BY diameter
DESC LIMIT 1
  