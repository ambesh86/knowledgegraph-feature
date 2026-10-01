from abc import abstractmethod


class GraphragLinkingAdapter:
    """
    Class to lookup nodes to be linked
    TODO: the initial logic for linking should be improved
    """

    @abstractmethod
    def find_node_index_by_node_name(
        self, entity_type: str, node_name: str
    ) -> str | None:
        raise NotImplementedError()

    @abstractmethod
    def link_publication_node(
        self,
        source_node_label: str,
        source_primary_key_label: str,
        source_primary_key: str | int,
        target_node_index: str,
    ) -> str | None:
        raise NotImplementedError()
