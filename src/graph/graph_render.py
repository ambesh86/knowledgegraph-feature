import matplotlib.pyplot as plt
import networkx
from graph.mapper.graph_mapper import GraphMapper
from graph.model.extraction import Extraction
from networkx import Graph


class GraphRender:
    def __init__(self, graph_mapper: GraphMapper):
        self.graph_mapper = graph_mapper

    def render_graph(self, graph: Graph) -> None:
        # plot the graph
        relation_labels = networkx.get_edge_attributes(graph, "relation")
        pos = networkx.spring_layout(graph)
        options = {
            "node_color": "grey",
            "linewidths": 0.5,
            "node_size": 100,
            "width": 2,
            "arrowstyle": "-|>",
            "arrowsize": 3,
        }
        networkx.draw_networkx(graph, pos=pos, arrows=True, **options)
        networkx.draw_networkx_edge_labels(graph, edge_labels=relation_labels, pos=pos)
        plt.show()

    def render_extraction(self, extraction: Extraction) -> None:
        graph = self.graph_mapper.map(extraction)
        self.render_graph(graph)
