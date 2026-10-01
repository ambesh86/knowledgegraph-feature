import logging

from langchain_core.prompts import ChatPromptTemplate
from infra.llm.prompt.prompt_title import PromptTitle

logger = logging.getLogger(__name__)


def generate_knowlege_graph_extraction_input_params(
    content: str = "",
) -> dict[str, str]:
    return generate_input_params(
        question="\n".join([generate_knowlege_graph_triples_prompt()]),
        document=content,
        title=PromptTitle.KNOWLEGE_GRAPH_EXTRACTION,
    )


def generate_knowlege_graph_summary_input_params(content: str = "") -> dict[str, str]:
    return generate_input_params(
        question="\n".join([generate_knowledge_graph_summary_prompt()]),
        document=content,
        title=PromptTitle.KNOWLEGE_GRAPH_SUMMARY,
    )


def generate_knowledge_graph_community_report_input_params(
    content: str = "",
) -> dict[str, str]:
    return generate_input_params(
        question="\n".join([generate_knowledge_graph_community_report_prompt()]),
        document=content,
        title=PromptTitle.KNOWLEGE_GRAPH_SUMMARY,
    )


def generate_named_entity_input_params(content: str) -> dict[str, str]:
    return generate_input_params(
        question="\n".join([generate_named_entity_hint()]),
        document=content,
        title=PromptTitle.NAMED_ENTITY_EXTRACTION,
    )


def generate_industry_input_params(content: str) -> dict[str, str]:
    return generate_input_params(
        question="\n".join(
            [
                "Based on the content, define the industries impacted by the document. Clearly state the industries in a list.",
                generate_no_halucinate_hint(),
                generate_response_length_hint(),
                generate_response_output_hint(),
            ]
        ),
        document=content,
        title=PromptTitle.SUMMARIZE_INDUSTRY.name,
    )


def generate_monetary_value_input_params(content: str) -> dict[str, str]:
    return generate_input_params(
        question=generate_prompt_question(
            [
                generate_prompt_value_hint("monetary value"),
                "If known, then respond with an enum of [NONE, LOW, MEDIUM, HIGH]",
            ]
        ),
        document=content,
        title=PromptTitle.MONETARY_VALUE,
    )


def generate_business_value_input_params(content: str) -> dict[str, str]:
    return generate_input_params(
        question=generate_prompt_question(
            [generate_prompt_value_hint("business value")]
        ),
        document=content,
        title=PromptTitle.BUSINESS_VALUE,
    )


def generate_questions_input_params(content: str) -> dict[str, str]:
    return generate_input_params(
        question=generate_prompt_question(
            [
                "Based on the content, suggest the top five questions a health sciences organization would make about this document."
            ]
        ),
        document=content,
        title=PromptTitle.TOP_QUESTIONS,
    )


def generate_enrich_suggestions_input_params(content: str) -> dict[str, str]:
    return generate_input_params(
        question=generate_prompt_question(
            [
                """List the type of data found in the document. Only for the data types present, suggest interesting ways to enrich the data.
                    Consider the following data types and tool sources and data types
                    [
                        Geographic: [
                            "https://www.google.com/maps"
                        ],
                        Genomic: [
                            "https://www.ncbi.nlm.nih.gov/datasets/genome/"
                        ],
                        Diseases: [
                            "https://rarediseases.info.nih.gov/"
                        ],
                        Proteins: [
                            "https://www.uniprot.org/"
                        ],
                        Financial Stocks: [
                            "https://www.morningstar.com/"
                        ],
                        Currency: [
                            "https://usa.visa.com/support/consumer/travel-support/exchange-rate-calculator.html"
                        ]
                    ]
            """
            ]
        ),
        document=content,
        title=PromptTitle.ENRICH,
    )


def generate_input_params(
    question: str, document: str, title: PromptTitle
) -> dict[str, str]:
    return {
        "question": question,
        "document": document,
        "title": title.name,
    }


def generate_prompt_question(prompts: list[str]) -> str:
    all = prompts.copy()
    all.extend(
        [
            generate_cot_reasoning_hint(),
            generate_no_halucinate_hint(),
            generate_response_length_hint(),
            generate_response_output_hint(),
        ]
    )

    logger.info(all)
    return "\n".join(all)


def generate_prompt_value_hint(value: str) -> str:
    return f"Based on the content, define the {value} for a health care and life sciences company, employees or customers."


def generate_response_length_hint() -> str:
    return "Keep the response short."


def generate_no_halucinate_hint() -> str:
    # return "Specify your answer as Uknown, if your answer is unknown or the data is too ambiguous. Do not extrapolate too much. Do not halluciante."
    return "Specify your answer as Uknown, if your answer is unknown or the data is too ambiguous."


def generate_cot_reasoning_hint() -> str:
    # return "Answer using chain of thought (CoT) and think step by step."
    return "Answer using chain of thought (CoT) reasoning."


def generate_response_output_hint(output_format: str = "markdown"):
    return f"Return the response output in {output_format} format."


def generate_knowlege_graph_triples_prompt():
    # return """Extract knowlege graph and facts from the document. Generate graph triples in the form of subject object predict. Return the output as JSON only.
    # Extract the values as short word tokens.

    # List the following relationships;
    #     "capableOf",
    #     "definedAs",
    #     "hasA",
    #     "hasPrerequisite",
    #     "hasProperty",
    #     "isA",
    #     "isCapitalOf"
    #     "locatedAt",
    #     "uses",
    #     "madeOf",
    #     "symbolOf",
    #     "partOf",
    #     "relatedTo"

    # JSON schema:
    # [
    #     {
    #         "s": "<string>",
    #         "p": "<string>",
    #         "o": "<string>"
    #     }
    # ]
    # """
    # https://github.com/microsoft/graphrag/blob/main/graphrag/index/graph/extractors/graph/prompts.py
    return """-Goal-
        Given a text document, identify all entities and their entity types from the text and all relationships among the identified entities.

        -Steps-
        1. Identify all entities. For each identified entity, extract the following information:
        - entity_name: Name of the entity, capitalized
        - entity_type: Type of the entity
        - entity_description: Comprehensive description of the entity's attributes and activities
        Format each entity as ("entity"/<entity_name>/<entity_type>/<entity_description>)

        Only include the following entity types;
            "drug",
            "disease",
            "gene_protein",
            "pathway",
            "anatomy",
            "biological_process",
            "cellular_component",
            "effect_phenotype",
            "exposure",
            "molecular_function",
            "chemical_synonym"

        2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
        For each pair of related entities, extract the following information:
        - source_entity: name of the source entity, as identified in step 1
        - target_entity: name of the target entity, as identified in step 1
        - relation: relationship between source_entity and target_entity
        - relationship_description: explanation as to why you think the source entity and the target entity are related to each other

        Format each relationship as ("relationship"/<source_entity>/<target_entity>/<relation>/<relationship_description>)

        Only include the following relation types;
            "drug_drug",
            "drug_protein",
            "drug_effect",
            "disease_disease",
            "disease_protein",
            "pathway_protein",
            "pathway_pathway",
            "protein_protein",
            "bioprocess_protein",
            "indication"

        3. When finished, output as JSON with the following schema
        {
            "entities": [
                {
                    "entity_name": "<string>",
                    "entity_type": "<string>",
                    "entity_description": "<string>"
                }
            ],
            "relationships": [
                {
                    "source_entity": "<string>",
                    "target_entity": "<string>",
                    "relation": "<string>",
                    "relation_description": "<string>"
                }
            ]
        }

    """


def generate_knowledge_graph_summary_prompt() -> str:
    """
    https://github.com/microsoft/graphrag/blob/main/graphrag/index/graph/extractors/summarize/prompts.py
    """
    #  When finished, output as JSON with the following schema
    #     {
    #     "entities": [
    #         {
    #             "entity_name": "<string>",
    #             "entity_type": "<string>",
    #             "entity_description": "<string>"
    #         }
    #     ],
    #     "relationships": [
    #         {
    #             "source_entity": "<string>",
    #             "target_entity": "<string>",
    #             "relation": "<string>",
    #             "relation_description": "<string>"
    #         }
    #     ]
    # }
    return """
        You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
        Given one or two entities, and a list of descriptions, all related to the same entity or group of entities.
        Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions.
        If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
        Make sure it is written in third person, and include the entity names so we have the full context.

        #######
        -Data-
        Entities: {entity_name}
        Description List: {description_list}
        #######
        Output:

    """


def generate_knowledge_graph_community_report_prompt() -> str:
    """
    https://github.com/microsoft/graphrag/blob/main/graphrag/index/graph/extractors/community_reports/prompts.py
    """
    return """
        You are an AI assistant that helps a human analyst to perform general information discovery. Information discovery is the process of identifying and assessing relevant information associated with certain entities (e.g., organizations and individuals) within a network.

        # Goal
        Write a comprehensive report of a community, given a list of entities that belong to the community as well as their relationships and optional associated claims. The report will be used to inform decision-makers about information associated with the community and their potential impact. The content of this report includes an overview of the community's key entities, their legal compliance, technical capabilities, reputation, and noteworthy claims.

        # Report Structure

        The report should include the following sections:

        - TITLE: community's name that represents its key entities - title should be short but specific. When possible, include representative named entities in the title.
        - SUMMARY: An executive summary of the community's overall structure, how its entities are related to each other, and significant information associated with its entities.
        - IMPACT SEVERITY RATING: a float score between 0-10 that represents the severity of IMPACT posed by entities within the community.  IMPACT is the scored importance of a community.
        - RATING EXPLANATION: Give a single sentence explanation of the IMPACT severity rating.
        - DETAILED FINDINGS: A list of 5-10 key insights about the community. Each insight should have a short summary followed by multiple paragraphs of explanatory text grounded according to the grounding rules below. Be comprehensive.

        Return output as a well-formed JSON-formatted string with the following format:
            {{
                "title": <report_title>,
                "summary": <executive_summary>,
                "rating": <impact_severity_rating>,
                "rating_explanation": <rating_explanation>,
                "findings": [
                    {{
                        "summary":<insight_1_summary>,
                        "explanation": <insight_1_explanation>
                    }},
                    {{
                        "summary":<insight_2_summary>,
                        "explanation": <insight_2_explanation>
                    }}
                ]
            }}

        # Grounding Rules

        Points supported by data should list their data references as follows:

        "This is an example sentence supported by multiple data references [Data: <dataset name> (record ids); <dataset name> (record ids)]."

        Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record ids and add "+more" to indicate that there are more.

        For example:
        "Person X is the owner of Company Y and subject to many allegations of wrongdoing [Data: Reports (1), Entities (5, 7); Relationships (23); Claims (7, 2, 34, 64, 46, +more)]."

        where 1, 5, 7, 23, 2, 34, 46, and 64 represent the id (not the index) of the relevant data record.

        Do not include information where the supporting evidence for it is not provided.


        # Example Input
        -----------
        Text:

        Entities

        id,entity,description
        5,VERDANT OASIS PLAZA,Verdant Oasis Plaza is the location of the Unity March
        6,HARMONY ASSEMBLY,Harmony Assembly is an organization that is holding a march at Verdant Oasis Plaza

        Relationships

        id,source,target,description
        37,VERDANT OASIS PLAZA,UNITY MARCH,Verdant Oasis Plaza is the location of the Unity March
        38,VERDANT OASIS PLAZA,HARMONY ASSEMBLY,Harmony Assembly is holding a march at Verdant Oasis Plaza
        39,VERDANT OASIS PLAZA,UNITY MARCH,The Unity March is taking place at Verdant Oasis Plaza
        40,VERDANT OASIS PLAZA,TRIBUNE SPOTLIGHT,Tribune Spotlight is reporting on the Unity march taking place at Verdant Oasis Plaza
        41,VERDANT OASIS PLAZA,BAILEY ASADI,Bailey Asadi is speaking at Verdant Oasis Plaza about the march
        43,HARMONY ASSEMBLY,UNITY MARCH,Harmony Assembly is organizing the Unity March

        Output:
        {{
            "title": "Verdant Oasis Plaza and Unity March",
            "summary": "The community revolves around the Verdant Oasis Plaza, which is the location of the Unity March. The plaza has relationships with the Harmony Assembly, Unity March, and Tribune Spotlight, all of which are associated with the march event.",
            "rating": 5.0,
            "rating_explanation": "The impact severity rating is moderate due to the potential for unrest or conflict during the Unity March.",
            "findings": [
                {{
                    "summary": "Verdant Oasis Plaza as the central location",
                    "explanation": "Verdant Oasis Plaza is the central entity in this community, serving as the location for the Unity March. This plaza is the common link between all other entities, suggesting its significance in the community. The plaza's association with the march could potentially lead to issues such as public disorder or conflict, depending on the nature of the march and the reactions it provokes. [Data: Entities (5), Relationships (37, 38, 39, 40, 41,+more)]"
                }},
                {{
                    "summary": "Harmony Assembly's role in the community",
                    "explanation": "Harmony Assembly is another key entity in this community, being the organizer of the march at Verdant Oasis Plaza. The nature of Harmony Assembly and its march could be a potential source of threat, depending on their objectives and the reactions they provoke. The relationship between Harmony Assembly and the plaza is crucial in understanding the dynamics of this community. [Data: Entities(6), Relationships (38, 43)]"
                }},
                {{
                    "summary": "Unity March as a significant event",
                    "explanation": "The Unity March is a significant event taking place at Verdant Oasis Plaza. This event is a key factor in the community's dynamics and could be a potential source of threat, depending on the nature of the march and the reactions it provokes. The relationship between the march and the plaza is crucial in understanding the dynamics of this community. [Data: Relationships (39)]"
                }},
                {{
                    "summary": "Role of Tribune Spotlight",
                    "explanation": "Tribune Spotlight is reporting on the Unity March taking place in Verdant Oasis Plaza. This suggests that the event has attracted media attention, which could amplify its impact on the community. The role of Tribune Spotlight could be significant in shaping public perception of the event and the entities involved. [Data: Relationships (40)]"
                }}
            ]
        }}


        # Real Data

        Use the following text for your answer. Do not make anything up in your answer.

        Text:
        {input_text}

        The report should include the following sections:

        - TITLE: community's name that represents its key entities - title should be short but specific. When possible, include representative named entities in the title.
        - SUMMARY: An executive summary of the community's overall structure, how its entities are related to each other, and significant information associated with its entities.
        - IMPACT SEVERITY RATING: a float score between 0-10 that represents the severity of IMPACT posed by entities within the community.  IMPACT is the scored importance of a community.
        - RATING EXPLANATION: Give a single sentence explanation of the IMPACT severity rating.
        - DETAILED FINDINGS: A list of 5-10 key insights about the community. Each insight should have a short summary followed by multiple paragraphs of explanatory text grounded according to the grounding rules below. Be comprehensive.

        Return output as a well-formed JSON-formatted string with the following format:
            {{
                "title": <report_title>,
                "summary": <executive_summary>,
                "rating": <impact_severity_rating>,
                "rating_explanation": <rating_explanation>,
                "findings": [
                    {{
                        "summary":<insight_1_summary>,
                        "explanation": <insight_1_explanation>
                    }},
                    {{
                        "summary":<insight_2_summary>,
                        "explanation": <insight_2_explanation>
                    }}
                ]
            }}

        # Grounding Rules

        Points supported by data should list their data references as follows:

        "This is an example sentence supported by multiple data references [Data: <dataset name> (record ids); <dataset name> (record ids)]."

        Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record ids and add "+more" to indicate that there are more.

        For example:
        "Person X is the owner of Company Y and subject to many allegations of wrongdoing [Data: Reports (1), Entities (5, 7); Relationships (23); Claims (7, 2, 34, 64, 46, +more)]."

        where 1, 5, 7, 23, 2, 34, 46, and 64 represent the id (not the index) of the relevant data record.

        Do not include information where the supporting evidence for it is not provided.

        Output:"""


def generate_named_entity_hint():
    return """Extract nouns and realtionships from the document. 

    Return the output as JSON only. List the entities and their type as a JSON. 
    Use the following JSON schema. Extract the values as short word tokens.
    [
        {
            "entity": "<string>",
            "type": "<string>"
        }
    ]
    """


def generate_prompt() -> ChatPromptTemplate:
    template = """Question: {question}

    Contents to analyze: {document}
    """

    return of_prompt(template)


def of_prompt(template: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_template(template)
