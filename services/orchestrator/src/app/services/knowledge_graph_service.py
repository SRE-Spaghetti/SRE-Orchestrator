import yaml
from pathlib import Path
from typing import List
from ..models.knowledge_graph import KnowledgeGraph, Component


class KnowledgeGraphService:
    def __init__(self, knowledge_graph_path: Path):
        self.knowledge_graph_path = knowledge_graph_path
        self._graph: KnowledgeGraph
        self._component_map: dict[str, Component]
        self._graph, self._component_map = self._load_graph()

    def _load_graph(self) -> tuple[KnowledgeGraph, dict[str, Component]]:
        with open(self.knowledge_graph_path, "r") as f:
            data = yaml.safe_load(f)
            if data is None:
                raise ValueError(
                    f"Knowledge graph file is empty: {self.knowledge_graph_path}"
                )
            if not isinstance(data, dict):
                raise TypeError(
                    f"Knowledge graph file content is not a valid mapping (dictionary): {self.knowledge_graph_path}"
                )

        graph = KnowledgeGraph(**data)
        component_map = {component.name: component for component in graph.components}
        return graph, component_map

    def get_dependencies(self, component_name: str) -> List[str]:
        """Retrieves a list of dependency names for a given component."""
        component = self.get_component(component_name)
        if component and component.relationships:
            return [rel.depends_on for rel in component.relationships]
        return []

    def get_component(self, component_name: str) -> Component | None:
        """
        Retrieves a component by its name using an efficient dictionary lookup.
        Returns the Component object or None if not found.
        """
        return self._component_map.get(component_name)
