import pytest
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.models.knowledge_graph import KnowledgeGraph


# Create a temporary knowledge_graph.yaml for testing
@pytest.fixture
def temp_knowledge_graph_file(tmp_path):
    content = """
components:
  - name: orchestrator-service
    type: service
    relationships: []
  - name: database
    type: datastore
    relationships:
      - depends_on: orchestrator-service
"""
    file_path = tmp_path / "knowledge_graph.yaml"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def knowledge_graph_service(temp_knowledge_graph_file):
    return KnowledgeGraphService(knowledge_graph_path=temp_knowledge_graph_file)


def test_load_graph_success(knowledge_graph_service):
    assert isinstance(knowledge_graph_service._graph, KnowledgeGraph)
    assert len(knowledge_graph_service._graph.components) == 2

    orchestrator = knowledge_graph_service.get_component("orchestrator-service")
    assert orchestrator is not None
    assert orchestrator.name == "orchestrator-service"
    assert orchestrator.type == "service"
    assert len(orchestrator.relationships) == 0

    database = knowledge_graph_service.get_component("database")
    assert database is not None
    assert database.name == "database"
    assert database.type == "datastore"
    assert len(database.relationships) == 1
    assert database.relationships[0].depends_on == "orchestrator-service"


def test_get_dependencies(knowledge_graph_service):
    deps = knowledge_graph_service.get_dependencies("orchestrator-service")
    assert deps == []

    deps = knowledge_graph_service.get_dependencies("database")
    assert deps == ["orchestrator-service"]

    deps = knowledge_graph_service.get_dependencies("non-existent-component")
    assert deps == []


def test_get_component(knowledge_graph_service):
    component = knowledge_graph_service.get_component("orchestrator-service")
    assert component.name == "orchestrator-service"

    component = knowledge_graph_service.get_component("non-existent-component")
    assert component is None
