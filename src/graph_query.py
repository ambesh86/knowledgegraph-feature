import sys
import logging
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain.chains import GraphQAChain
from langchain_community.graphs import NetworkxEntityGraph
from networkx import Graph

from document.load.stored_triples_loader import StoredTriplesLoader
from graph.mapper.graph_mapper import GraphMapper
from infra.llm.llm_chat_factory import LlmChatFactory
from infra.llm.prompt.prompt_response import PromptResponse
from infra.util.file_util import write_report
from infra.llm.callback.qa_context_callback_handler import QaContextCallbackHandler

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main():
    load_dotenv()
    graph = _load_data()
    questions = [sys.argv[1]]
    # INFO:__main__:total entities: 2261 total relationships: 1911
    # questions = [
    #     # this question works the best across all models
    #     "What is CSL112?",
    #     # "Is CSL112 a country?",
    #     # "Is CSL112 a country in Europe?",
    #     # "Does CSL112 have health applications?",
    #     # "The NEW ENGLAND JOURNAL OF MEDICINE only publishes studies for legal drugs. Is CSL112 a legal drug?",
    #     # "Which drugs are approved by HEALTH CANADA?",
    #     # "Name things are predicted by TROPONIN I",
    #     # "Name things correlated with TROPONIN I",
    #     # "What neighbors does the graph have for TROPONIN I?",
    #     # "What nodes are related to CD19+ B cells?",
    #     # "What are the neighbors to MONOCLONAL ANTIBODIES?",
    #     # "What is Apolipoprotein(a)?",
    #     # "What biomarkers are included in plasma level measurements",
    #     # "What cell type is cloned from MONOCLONAL ANTIBODIES?",
    #     # "Explain uses for CREATININE",
    #     # "What is the drug NOREPINEPHRINE used to treat?",
    #     # "Who is FABIAN HALLECK?",
    #     # "Who is FABIAN HALLECK and who are they affiliated with?",
    #     # "What are the drugs mentioned in the VASST study?",
    #     # "How do you measure kidney function?",
    #     # "What is Glanzmann Thrombasthenia?",
    #     # "Name treatments for the Glanzmann Thrombasthenia disease.",
    #     # warn: the GraphQA chain does not allow the generic questions based on types
    #     #   the chain takes a graph with nodes of exact values only
    #     #   in other words it expects a triples graph, not a property graph
    #     #   to get around this, we could expand to add new nodes of the given type
    #     #   or we could modify the chain w/ either call backs or extension
    #     # "What organization was approved by ETHICAL COMMITTEE OF NORTHWEST SWITZERLAND?",
    #     # "What are some facts about funding and research available in the given graph?",
    #     # "Name people and organizations with funding?",
    #     # "Name the entities with a type of disease, therapy or treatment",
    # ]
    logger.debug(questions)
    _answer_questions(graph, questions)


# def _retrieve_answer_for_questions(graph: NetworkxEntityGraph, questions: list[str]) -> None:
#     """
#     ask the graph only
#     """
#     graph_retriever = GraphRetriever(graph)

# RetrievalQAChain moved and this does not work atm
# https://github.com/langchain-ai/langchain/issues/2725
#     retriever_qa = RetrievalQAWithSourcesChain.from_chain_type(
#         llm=_llm(),
#         chain_type="query graph",
#         retriever=graph_retriever,
#         return_source_documents=True
#     )
#     for question in questions:
#         result = retriever_qa({"query": question})
#         print(result['result'])


def _answer_questions(graph: NetworkxEntityGraph, questions: list[str]) -> None:
    """
    ask the graph for context and send to a chat bot
    """
    handler = QaContextCallbackHandler()
    config = {"callbacks": [handler]}
    chain = GraphQAChain.from_llm(
        graph=graph,
        llm=_llm(),
        verbose=True,
        include_run_info=True,
    )

    responses = []
    count = 0
    for question in questions:
        count += 1
        logger.debug(f"{question}")
        response = chain.invoke(question, config=config)
        logger.debug(response)
        title = f"Question {count:02}"
        prompt_response = PromptResponse(
            title=title, question=response["query"], llm_response=response["result"]
        )
        responses.append(prompt_response)
        logger.info(f"question: {prompt_response.question}")
        logger.info(f"result: {prompt_response.llm_response}")
        logger.info("\n")

    write_report("./output/report.md", responses)


def _llm() -> BaseChatModel:
    model = "o1-mini"
    # model = "gpt-4o-mini"
    # model = "gpt-4-turbo"
    # model = "gpt-3.5-turbo"
    # llm = LlmChatFactory.local_instance(model="llama3.2")
    llm = LlmChatFactory.openai_instance(model=model)
    return llm


def _load_data() -> NetworkxEntityGraph:
    logger.debug("loading data...")
    stored_triples_loader = StoredTriplesLoader()
    extraction = stored_triples_loader.load(data_dirs=_data_dirs())
    logger.info(
        f"total entities: {len(extraction.entities)} total relationships: {len(extraction.relationships)}"
    )
    logger.debug("mapping to graph...")
    graph_mapper = GraphMapper()

    graph_nx = graph_mapper.map(extraction, directed=True)
    logger.debug(f"{graph_nx}")
    graph = _nx_to_langchain_graph(graph_nx)
    _print_graph(graph)
    return graph


def _inspect(state):
    """Print the state passed between Runnables in a langchain and pass it on"""
    print(state)
    return state


def _nx_to_langchain_graph(graph_nx: Graph) -> NetworkxEntityGraph:
    # warning: we need a DiGraph or we get a langchain error
    # ValueError: Passed in graph is not of correct shape
    # graph = NetworkxEntityGraph(graph_nx.to_directed())

    # warning: the graph entities need to be a str and can have attrs
    # if the graph entity is a Entity object, the QA chain fails to find nodes
    entity_graph = NetworkxEntityGraph()
    for node_tuple in graph_nx.nodes(data=True):
        logger.debug(f"{node_tuple}")
        node_data = node_tuple[1]
        logger.debug(f"node = {node_data} value = {node_data["value"]}")
        entity_graph._graph.add_node(
            node_data["value"],
            value=node_data["value"],
            type=node_data["type"],
            id=node_data["id"],
            description=node_data["description"],
        )

    # Add edges to the graph
    for edge in graph_nx.edges(data=True):
        relation = graph_nx.edges[edge[0], edge[1]]["relation"]
        description = graph_nx.edges[edge[0], edge[1]]["description"]
        logger.debug(f"{edge[0]} {relation} {edge[1]}")
        entity_graph._graph.add_edge(
            edge[0].value,
            edge[1].value,
            relation=relation,
            description=description,
        )
    return entity_graph


def _print_graph(graph: NetworkxEntityGraph) -> None:
    for triple in graph.get_triples():
        logger.debug(f"{triple}")
    _print_nodes("TROPONIN I", graph)


def _print_nodes(node_val: str, graph: NetworkxEntityGraph) -> None:
    logger.debug(f"has node: {node_val}: {graph.has_node(node_val)}")
    for neighbor in graph.get_neighbors(node_val):
        logger.debug(f"neighbors: {neighbor}")


def _data_dirs() -> list[Path]:
    data_root = Path("./output")
    data_dirs = [
        "01681224922d6072340533cd82bedc4b",
        "0223be7bb7cfc12ffab1529a7f30222a",
        "19e024b4954abfc429b19754155fada9",
        "23cf851a351d0d89174b9c76360396bf",
        "27c6f1b40b214416ca20a66258b889b8",
        "5cb17ba0e0a201abc979aac1bca9d67c.leiden",
        "7fb83630f305e6148cbb1e7e6df53452",
        "ba533502204a4ecb4e5dc61977cc93d2",
        "bd0c11b505f8450a061d354f7add39f2",
        "e5976811cbf1095d1382cafbf8a14dc7",
        "eb9fa170776163c7800d97c5709bb122",
        "f2b8598844db225aad5878a1222365b8",
        "4a24f1c15fdce726ebd6340c7dff2f2a",
        "a010cedd52addd77371973b6cca48396",
    ]
    dirs = [(data_root / x) for x in data_dirs]
    return dirs


if __name__ == "__main__":
    main()
