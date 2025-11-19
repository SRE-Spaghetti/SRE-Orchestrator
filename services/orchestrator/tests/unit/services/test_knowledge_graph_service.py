"""Unit tests for KnowledgeGraphService."""

import pytest
import yaml

from app.services.knowledge_graph_service import KnowledgeGraphService


class TestKnowledgeGraphService:
    """Test suite for KnowledgeGraphService."""

    def test_load_valid_knowledge_graph(self, tmp_path):
        """Test loading a valid knowledge graph YAML file."""
        # Arrange
        kg_file = tmp_path / "knowledge_graph.yaml"
        kg_data = {
            "components": [
                {
                    "name": "api-gateway",
                    "type": "service",
                    "relationships": [{"depends_on": "auth-service"}],
                },
                {
                    "name": "auth-service",
                    "type": "service",
                    "relationships": [],
                },
            ]
        }
        kg_file.write_text(yaml.dump(kg_data))

        # Act
        service = KnowledgeGraphService(kg_file)

        # Assert
        assert service._graph is not None
        assert len(service._graph.components) == 2
        assert service._component_map["api-gateway"].name == "api-gateway"
        assert service._component_map["auth-service"].name == "auth-service"

    def test_get_component_returns_correct_component(self, tmp_path):
        """Test get_component returns the correct component."""
        # Arrange
        kg_file = tmp_path / "knowledge_graph.yaml"
        kg_data = {
            "components": [
                {"name": "api-gateway", "type": "service", "relationships": []},
                {"name": "database", "type": "database", "relationships": []},
            ]
        }
        kg_file.write_text(yaml.dump(kg_data))
        service = KnowledgeGraphService(kg_file)

        # Act
        component = service.get_component("api-gateway")

        # Assert
        assert component is not None
        assert component.name == "api-gateway"
        assert component.type == "service"

    def test_get_component_returns_none_for_nonexistent(self, tmp_path):
        """Test get_component returns None for non-existent component."""
        # Arrange
        kg_file = tmp_path / "knowledge_graph.yaml"
        kg_data = {"components": [{"name": "api-gateway", "type": "service"}]}
        kg_file.write_text(yaml.dump(kg_data))
        service = KnowledgeGraphService(kg_file)

        # Act
        component = service.get_component("nonexistent-service")

        # Assert
        assert component is None

    def test_get_dependencies_returns_dependency_list(self, tmp_path):
        """Test get_dependencies returns correct dependency list."""
        # Arrange
        kg_file = tmp_path / "knowledge_graph.yaml"
        kg_data = {
            "components": [
                {
                    "name": "api-gateway",
                    "type": "service",
                    "relationships": [
                        {"depends_on": "auth-service"},
                        {"depends_on": "database"},
                    ],
                }
            ]
        }
        kg_file.write_text(yaml.dump(kg_data))
        service = KnowledgeGraphService(kg_file)

        # Act
        dependencies = service.get_dependencies("api-gateway")

        # Assert
        assert len(dependencies) == 2
        assert "auth-service" in dependencies
        assert "database" in dependencies

    def test_get_dependencies_returns_empty_list_for_no_relationships(self, tmp_path):
        """Test get_dependencies returns empty list when component has no relationships."""
        # Arrange
        kg_file = tmp_path / "knowledge_graph.yaml"
        kg_data = {"components": [{"name": "standalone-service", "type": "service"}]}
        kg_file.write_text(yaml.dump(kg_data))
        service = KnowledgeGraphService(kg_file)

        # Act
        dependencies = service.get_dependencies("standalone-service")

        # Assert
        assert dependencies == []

    def test_get_dependencies_returns_empty_list_for_nonexistent_component(
        self, tmp_path
    ):
        """Test get_dependencies returns empty list for non-existent component."""
        # Arrange
        kg_file = tmp_path / "knowledge_graph.yaml"
        kg_data = {"components": [{"name": "api-gateway", "type": "service"}]}
        kg_file.write_text(yaml.dump(kg_data))
        service = KnowledgeGraphService(kg_file)

        # Act
        dependencies = service.get_dependencies("nonexistent-service")

        # Assert
        assert dependencies == []

    def test_load_graph_raises_error_for_missing_file(self, tmp_path):
        """Test that loading a non-existent file raises FileNotFoundError."""
        # Arrange
        kg_file = tmp_path / "nonexistent.yaml"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            KnowledgeGraphService(kg_file)

    def test_load_graph_raises_error_for_empty_file(self, tmp_path):
        """Test that loading an empty file raises ValueError."""
        # Arrange
        kg_file = tmp_path / "empty.yaml"
        kg_file.write_text("")

        # Act & Assert
        with pytest.raises(ValueError, match="Knowledge graph file is empty"):
            KnowledgeGraphService(kg_file)

    def test_load_graph_raises_error_for_invalid_yaml(self, tmp_path):
        """Test that loading invalid YAML raises yaml.YAMLError."""
        # Arrange
        kg_file = tmp_path / "invalid.yaml"
        kg_file.write_text("invalid: yaml: content: [unclosed")

        # Act & Assert
        with pytest.raises(yaml.YAMLError):
            KnowledgeGraphService(kg_file)

    def test_load_graph_raises_error_for_non_dict_content(self, tmp_path):
        """Test that loading non-dict YAML content raises TypeError."""
        # Arrange
        kg_file = tmp_path / "list.yaml"
        kg_file.write_text("- item1\n- item2")

        # Act & Assert
        with pytest.raises(
            TypeError, match="Knowledge graph file content is not a valid mapping"
        ):
            KnowledgeGraphService(kg_file)

    def test_component_map_provides_efficient_lookup(self, tmp_path):
        """Test that component_map provides O(1) lookup performance."""
        # Arrange
        kg_file = tmp_path / "knowledge_graph.yaml"
        components = [{"name": f"service-{i}", "type": "service"} for i in range(100)]
        kg_data = {"components": components}
        kg_file.write_text(yaml.dump(kg_data))
        service = KnowledgeGraphService(kg_file)

        # Act
        component = service.get_component("service-50")

        # Assert
        assert component is not None
        assert component.name == "service-50"
        assert len(service._component_map) == 100
