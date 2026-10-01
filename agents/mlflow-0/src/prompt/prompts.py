def organization_resolution_prompt() -> str:
    return """-Goal-
Find the company names for the given government, non profit organization, university, hospital, biomedical company, or pharmaceutical company.
-Steps-
1. Categorize the organization name as one of the following types: [company, hospital, university, nonprofit, foundation, government, or organization]
2. Use the generic value "organization" if no given organization category value applies.
1. Find spelling variations, mergers, demergers, parent companies, subsidiaries, and operations in different countries.
2. For international companies be sure to include titles such as; Pte Ltd, SRL, GmbH, Inc, ApS, LLC, Inc, Sp zoo, and AB.
3. If the given company is the parent name list it under parent company.
4. Be sure to include all names.
5. Do not include year of acquisition.
6. When finished, output as JSON with the following schema
{
    "official_name": "",
    "parent": "",
    "subsidiaries": [],
    "acquisitions": [],
    "spelling_variations": [],
    "mergers": [],
    "demergers": [],
    "organization_type": ""
}

#######
-Data-
Organization Name: {{organization_name}}
"""


def generate_organization_name_verification_prompt() -> str:
    return """
-GOAL-
Confirm the following organization data is accurate. Fix fictional organization names. Fix concatenated organization names. Do not hallucinate. Only output the results as JSON with the following schema

-OUTPUT SCHEMA-
{
    “input”: “”,
    “valid_organization_name”: true or false 
}

-INPUT DATA-
Organization Name: {{organization_name}}"""


def generate_on_topic_prompt() -> str:
    return """
You are an biotech/healthcare professional giving guidance on the following on topic question. 

Question: Given a user question, consider if that question is work related to the healthcare or biotechnology industry. Your work includes researching biotechnology and pharmaceutical companies.
Thought: Consider the entities and relationships in the user question. Draw on your healthcare and biotechnology knowledge
Thought: Some queries may be ambigous, consider ambiguous queries as a score of 1
Action: Come to a conclusion. Score you answer on a scale of 0-9. Where 0 means the user question is totally unrelated, and 9 means it is highly correlated with infosec
Final Answer: Return the final answer in the sample JSON schmea given below.

Sample Schema:
```json
{
    "score": <number>
}
```

-INPUT DATA-
User Question: {{user_question}}"""
