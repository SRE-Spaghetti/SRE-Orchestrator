import pytest
from unittest.mock import MagicMock
from app.core.correlation_engine import CorrelationEngine


@pytest.fixture
def mock_knowledge_graph_service():
    """Fixture for a mocked KnowledgeGraphService."""
    return MagicMock()


def test_correlate_oomkilled(mock_knowledge_graph_service):
    """Test the OOMKilled correlation rule."""
    engine = CorrelationEngine(mock_knowledge_graph_service)
    evidence = {"logs": "OOMKilled", "restarts": 1}
    root_cause, confidence = engine.correlate(evidence)
    assert root_cause == "Insufficient Memory"
    assert confidence == "high"


def test_correlate_failed_scheduling(mock_knowledge_graph_service):
    """Test the FailedScheduling correlation rule."""
    engine = CorrelationEngine(mock_knowledge_graph_service)
    evidence = {"events": "FailedScheduling"}
    root_cause, confidence = engine.correlate(evidence)
    assert root_cause == "Insufficient Cluster Resources"
    assert confidence == "high"


def test_correlate_database_unreachable(mock_knowledge_graph_service):
    """Test the Database Unreachable correlation rule."""
    engine = CorrelationEngine(mock_knowledge_graph_service)
    evidence = {"logs": "connection refused"}
    root_cause, confidence = engine.correlate(evidence)
    assert root_cause == "Database Unreachable"
    assert confidence == "medium"


def test_correlate_no_match(mock_knowledge_graph_service):
    """Test that no root cause is suggested when no rules match."""
    engine = CorrelationEngine(mock_knowledge_graph_service)
    evidence = {"logs": "some other error"}
    root_cause, confidence = engine.correlate(evidence)
    assert root_cause is None
    assert confidence is None
