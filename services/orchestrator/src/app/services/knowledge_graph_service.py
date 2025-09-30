import yaml
from pathlib import Path
from typing import List
from ..models.knowledge_graph import KnowledgeGraph, Component


class KnowledgeGraphService:
    def __init__(self, knowledge_graph_path: Path):
        self.knowledge_graph_path = knowledge_graph_path
        self._graph: KnowledgeGraph = self._load_graph()

    def _load_graph(self) -> KnowledgeGraph:
        with open(self.knowledge_graph_path, "r") as f:
            data = yaml.safe_load(f)
        return KnowledgeGraph(**data)

    def get_dependencies(self, component_name: str) -> List[str]:
        dependencies = []
        for component in self._graph.components:
            if component.name == component_name:
                if component.relationships:
                    for relationship in component.relationships:
                        dependencies.append(relationship.depends_on)
                break
        return dependencies

    def get_component(self, component_name: str) -> Component | None:
        for component in self._graph.components:
            if component.name == component_name:
                return component
        return None
