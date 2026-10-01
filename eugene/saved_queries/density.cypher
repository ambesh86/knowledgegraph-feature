// graph density
CALL apoc.meta.stats() YIELD nodeCount, relCount
RETURN toFloat(relCount) / (nodeCount * (nodeCount - 1)) as density