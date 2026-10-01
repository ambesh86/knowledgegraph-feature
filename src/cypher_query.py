import os

from dotenv import load_dotenv
from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

"""
Semantic to cypher searching
https://python.langchain.com/docs/how_to/graph_semantic/
https://python.langchain.com/docs/integrations/graphs/neo4j_cypher/
https://python.langchain.com/v0.2/docs/integrations/graphs/kuzu_db/
"""

# Load the environment variables from the .env file
load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Choosing the enhanced schema version enables the system to automatically scan for example values within the databases and calculate some distribution metrics.
graph = Neo4jGraph(enhanced_schema=True)
graph.refresh_schema()
# print(graph.schema)


CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Schema:
{schema}
Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.
Examples: Here are a few examples of generated Cypher statements for particular questions:
# What do we know about researchers on a given topic?
MATCH (r:researcher)-[rel]-(t)
WHERE r.description contains "$topic"  OR r.value = "$topic" 
RETURN r, rel, t

# What inflammatory condition respond to a treatment? 
MATCH (a:condition)-[rel]-(c:treatment)
WHERE a.description CONTAINS "inflammatory"
RETURN a, rel, c

The question is:
{question}"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)

# model = "gpt-4-turbo"
model = "o1-mini"
# model = "gpt-4o-mini"
# model = "gpt-4-turbo"
# model = "gpt-3.5-turbo"
llm = ChatOpenAI(model=model, temperature=0.1)
chain = GraphCypherQAChain.from_llm(
    graph=graph,
    llm=llm,
    validate_cypher=True,
    verbose=True,
    allow_dangerous_requests=True,
    cypher_prompt=CYPHER_GENERATION_PROMPT,
)


# q1 = "What treatments respond well to an inflammatory condition?"
# Generated Cypher:
# MATCH (t:treatment)-[rel]-(c:condition)
# WHERE c.description CONTAINS "inflammatory"
# RETURN t, rel, c
# returns correct subgraph

# q1 = "What biomarkers are associated with a hypoinflammatory condition?"
q1 = "What biomarkers are associated with an inflammatory condition?"
# Generated Cypher:
# MATCH (b:biomarker)-[:associated_with]->(c:medicalcondition)
# WHERE c.description CONTAINS "inflammatory"
# RETURN b
# Manually Fixed
# MATCH (b:biomarker)-[rel]-(c:medicalcondition)
# WHERE c.description CONTAINS "inflammatory"
# RETURN b, rel, c

# q1 = "What studies have CSL funded?"
# Generated Cypher:
# []
# q1 = "What do you know about biomarkers?"
# q1 = ""
# MATCH (m:medicalcondition {type: "Sepsis"}) RETURN m;
# q1 = "q1 = "What do you know about the biomarkers?"
# MATCH (b:biomarker)-[r]-() RETURN b, r;
# q1 = "What do you know about the biomarker TROPONIN I?"
# MATCH (b:biomarker {id: "TROPONIN I"})
# OPTIONAL MATCH (b)-[r]-()
# RETURN b, r
# q1 = "What do you know about the biomarker with a value of TROPONIN I?"
# MATCH (b:biomarker {value: "TROPONIN I"})
# RETURN b
# q1 = "Name all authors or researchers for lipoprotein or Lipoprotein(A)"
# MATCH (a:author)-[:has_researcher]->(b:biomolecule {description: 'lipoprotein'})
# RETURN a.description AS AuthorDescription, a.id AS AuthorID
# UNION
# MATCH (a:author)-[:has_researcher]->(b:biomolecule {description: 'Lipoprotein(A)'})
# RETURN a.description AS AuthorDescription, a.id AS AuthorID

# MATCH (a:author)-[:has_researcher|:research_contributor|:member_of|:has_member|:has_collaborator|:has_coauthor*]->(b:biomolecule {description: 'lipoprotein'})
# RETURN a.description AS AuthorDescription, a.id AS AuthorID, a.type AS AuthorType, a.value AS AuthorValue
# UNION
# MATCH (r:researcher)-[:has_researcher|:research_contributor|:member_of|:has_member|:has_collaborator|:has_coauthor*]->(b:biomolecule {description: 'lipoprotein'})
# RETURN r.description AS ResearcherDescription, r.id AS ResearcherID, r.type AS ResearcherType, r.value AS ResearcherValue
# q1 = "Name all authors or researchers"
# MATCH (n)
# WHERE n:author OR n:researcher
# RETURN n.id, n.description, n.type, n.value;
# Full Context:
# [{'n.id': '2mWaQV8e9iIhXTExcsMMaylBW4r', 'n.description': 'Aengevaeren VL is an author who contributed to research on exercise-induced cardiac troponin elevations', 'n.type': 'Author', 'n.value': 'AENGEVAEREN VL'}, {'n.id': '2mWMzZ3BdQwHI9bu9s4NkM8kXx3', 'n.description': 'Weyand AC is an author who has contributed to multiple studies and articles related to hemophilia and bleeding disorders', 'n.type': 'Author', 'n.value': 'WEYAND AC'}, {'n.id': '2mWMzZ2xren4BIR03CPl2ASGrPo', 'n.description': 'Pipe SW is an author who has co-authored articles on new therapies for hemophilia and the efficacy of emicizumab in pediatric patients with type 3 von Willebrand disease.', 'n.type': 'Author', 'n.value': 'PIPE SW'}, {'n.id': '2mWaQVAd6qFmXUHjWKJ8zPqm04M', 'n.description': 'Teerlink JR is an author involved in studies on heart failure', 'n.type': 'Author', 'n.value': 'TEERLINK JR'}, {'n.id': '2mWMzZ3xicHON7rRo9g387nFJX3', 'n.description': 'Lavin M is an author who has co-authored research on new treatment approaches to von Willebrand disease.', 'n.type': 'Author', 'n.value': 'LAVIN M'}, {'n.id': '2mWMzZ4m9z8r4GdcaaA7i3E756Z', 'n.description': "O'Donnell JS is an author who has co-authored research on new treatment approaches to von Willebrand disease.", 'n.type': 'Author', 'n.value': "O'DONNELL JS"}, {'n.id': '2mUkDYVUNYxOr0etVZOkHMQR9ju', 'n.description': 'A researcher involved in the investigation', 'n.type': 'Researcher', 'n.value': 'SH'}, {'n.id': '2mUkDYVf4LIRGuxuKfaAJ5Zp60S', 'n.description': 'The authors of the study that conducted research on fibrinogen concentrates and their effects on coagulation and fibrinolysis.', 'n.type': 'Author', 'n.value': 'GOODARZI ET AL.'}, {'n.id': '2mWMzZ57ETSTe35Ltm2RWeyMHSj', 'n.description': 'Arya S is an author who has contributed to research on barriers to care for women with inherited bleeding disorders and the lived experiences of women with inherited bleeding disorders.', 'n.type': 'Author', 'n.value': 'ARYA S'}, {'n.id': '2mWMzZ3WlUztEFpDLdxQr4NiD0m', 'n.description': 'Wilton P is an author who has co-authored research on barriers to care for women with inherited bleeding disorders and the lived experiences of women with inherited bleeding disorders.', 'n.type': 'Author', 'n.value': 'WILTON P'}]

# instruct = "Hint for creating cyhper queries. Many relationships start with a has prefix. For example has_research. Note, attempt to search a node value attribute first. Do not be sensitive to relationship directions."
# query = f"{instruct} {q1}"
query = q1
response = chain.invoke({"query": query})

print(len(response))
for r in response:
    print(r)
