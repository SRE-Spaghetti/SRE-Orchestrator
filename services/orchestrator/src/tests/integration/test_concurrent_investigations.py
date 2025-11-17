"""
Concurrent investigation tests for native LangGraph implementation.

This module tests the native implementation's ability to handle multiple
concurrent investigations without performance degradation or state leakage.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from app.core.investigation_agent import (
    create_investigation_agent_native,
    investigate_incident,
)

logger = logging.getLogger(__name__)


# Test incidents for concurrent testing
# Include incident ID in description for state leakage verification
CONCURRENT_TEST_INCIDENTS = [
    {
        "id": "concurrent-1",
        "description": "Incident concurrent-1: Pod auth-service-xyz is in CrashLoopBackOff state.",
        "expected_keyword": "crash",
    },
    {
        "id": "concurrent-2",
        "description": "Incident concurrent-2: High memory usage detected on pod payment-processor-abc.",
        "expected_keyword": "memory",
    },
    {
        "id": "concurrent-3",
        "description": "Incident concurrent-3: Service frontend-web is experiencing 503 errors.",
        "expected_keyword": "503",
    },
    {
        "id": "concurrent-4",
        "description": "Incident concurrent-4: Database connection pool exhausted for pod api-gateway-def.",
        "expected_keyword": "connection",
    },
    {
        "id": "concurrent-5",
        "description": "Incident concurrent-5: Pod worker-queue-ghi is stuck in Pending state.",
        "expected_keyword": "pending",
    },
    {
        "id": "concurrent-6",
        "description": "Incident concurrent-6: High CPU usage on pod analytics-service-jkl.",
        "expected_keyword": "cpu",
    },
    {
        "id": "concurrent-7",
        "description": "Incident concurrent-7: Pod notification-service-mno failing health checks.",
        "expected_keyword": "health",
    },
    {
        "id": "concurrent-8",
        "description": "Incident concurrent-8: Service cache-redis-pqr experiencing connection timeouts.",
        "expected_keyword": "timeout",
    },
    {
        "id": "concurrent-9",
        "description": "Incident concurrent-9: Pod batch-processor-stu running out of disk space.",
        "expected_keyword": "disk",
    },
    {
        "id": "concurrent-10",
        "description": "Incident concurrent-10: Service message-queue-vwx has high message backlog.",
        "expected_keyword": "backlog",
    },
]


def create_mock_tools_for_incident(incident_id: str) -> List[Any]:
    """
    Create mock MCP tools that return incident-specific data.

    This ensures each concurrent investigation gets unique data to verify
    no state leakage between investigations.
    """
    from langchain_core.tools import StructuredTool

    async def get_pod_status(pod_name: str) -> dict:
        """Get the status of a Kubernetes pod."""
        await asyncio.sleep(0.05)
        return {
            "incident_id": incident_id,  # Include incident ID to verify no leakage
            "status": "Error",
            "message": f"Status for {incident_id}",
        }

    async def get_pod_logs(pod_name: str) -> str:
        """Get logs from a Kubernetes pod."""
        await asyncio.sleep(0.05)
        return f"Logs for {incident_id}: Error occurred"

    tool_1 = StructuredTool.from_function(
        coroutine=get_pod_status,
        name="get_pod_status",
        description="Get the status of a Kubernetes pod",
    )

    tool_2 = StructuredTool.from_function(
        coroutine=get_pod_logs,
        name="get_pod_logs",
        description="Get logs from a Kubernetes pod",
    )

    return [tool_1, tool_2]


def create_mock_llm_config() -> Dict[str, Any]:
    """Create mock LLM configuration for testing."""
    return {
        "base_url": "http://mock-llm:8000",
        "api_key": "mock-api-key",
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
    }


@pytest.fixture
def mock_llm_concurrent(monkeypatch):
    """
    Mock the ChatOpenAI LLM for concurrent testing.

    Each invocation includes a unique identifier to verify no state leakage.
    """

    # Track invocations per correlation ID to ensure proper isolation
    invocation_counts = {}

    async def mock_ainvoke(messages):
        """Mock LLM invocation with correlation-specific tracking."""
        await asyncio.sleep(0.1)

        # Extract correlation ID from the last human message or tool results
        correlation_id = "unknown"
        import re

        # First try to find it in human messages
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content:
                content_str = str(msg.content)
                match = re.search(r"concurrent-\d+", content_str)
                if match:
                    correlation_id = match.group(0)
                    break

        # If still unknown, try to extract from tool results (which include incident_id)
        if correlation_id == "unknown":
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content:
                    content_str = str(msg.content)
                    # Tool results contain incident_id field
                    match = re.search(
                        r"'incident_id':\s*'(concurrent-\d+)'", content_str
                    )
                    if not match:
                        match = re.search(
                            r'"incident_id":\s*"(concurrent-\d+)"', content_str
                        )
                    if match:
                        correlation_id = match.group(1)
                        break

        # Initialize count for this correlation
        if correlation_id not in invocation_counts:
            invocation_counts[correlation_id] = 0

        invocation_counts[correlation_id] += 1
        count = invocation_counts[correlation_id]

        # First invocation: request tools
        if count == 1:
            response = AIMessage(
                content=f"Investigating {correlation_id}",
                tool_calls=[
                    {
                        "name": "get_pod_status",
                        "args": {"pod_name": f"pod-{correlation_id}"},
                        "id": f"call_{correlation_id}_1",
                    }
                ],
            )
            response.tool_calls = response.tool_calls
            return response

        # Second invocation: request more tools
        elif count == 2:
            response = AIMessage(
                content=f"Checking logs for {correlation_id}",
                tool_calls=[
                    {
                        "name": "get_pod_logs",
                        "args": {"pod_name": f"pod-{correlation_id}"},
                        "id": f"call_{correlation_id}_2",
                    }
                ],
            )
            response.tool_calls = response.tool_calls
            return response

        # Final invocation: provide answer with correlation ID embedded
        else:
            return AIMessage(
                content=f"""Investigation complete for {correlation_id}.

ROOT CAUSE: Error in {correlation_id}
CONFIDENCE: high
EVIDENCE: Status and logs for {correlation_id}
RECOMMENDATIONS: Fix the issue in {correlation_id}"""
            )

    # Mock ChatOpenAI
    mock_llm = MagicMock()
    mock_llm.ainvoke = mock_ainvoke
    mock_llm.bind_tools = lambda tools, **kwargs: mock_llm

    def mock_chat_openai(*args, **kwargs):
        return mock_llm

    monkeypatch.setattr("app.core.investigation_agent.ChatOpenAI", mock_chat_openai)

    return mock_llm


async def run_single_investigation(
    agent: Any, incident: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run a single investigation and return results with timing.

    Args:
        agent: The investigation agent
        incident: Incident dictionary

    Returns:
        Dictionary with result and timing information
    """
    start_time = datetime.utcnow()

    result = await investigate_incident(
        agent=agent,
        incident_id=incident["id"],
        description=incident["description"],
        correlation_id=incident["id"],
    )

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    return {
        "incident_id": incident["id"],
        "result": result,
        "duration": duration,
        "start_time": start_time,
        "end_time": end_time,
    }


@pytest.mark.asyncio
async def test_concurrent_investigations_no_state_leakage(mock_llm_concurrent):
    """
    Test that concurrent investigations don't leak state between each other.

    This test runs multiple investigations concurrently and verifies that
    each investigation maintains its own state and doesn't interfere with others.

    Requirements: 8.4
    """
    logger.info("Starting concurrent investigations state leakage test")

    llm_config = create_mock_llm_config()

    # Use first 5 incidents for this test
    test_incidents = CONCURRENT_TEST_INCIDENTS[:5]

    # Create a single agent (reused for all investigations)
    mock_tools = create_mock_tools_for_incident("shared")
    agent = await create_investigation_agent_native(
        mcp_tools=mock_tools,
        llm_config=llm_config,
        correlation_id="concurrent-test-shared",
    )

    logger.info(f"Running {len(test_incidents)} concurrent investigations")

    # Run all investigations concurrently
    tasks = [run_single_investigation(agent, incident) for incident in test_incidents]

    results = await asyncio.gather(*tasks)

    # Verify each investigation completed successfully
    for investigation in results:
        incident_id = investigation["incident_id"]
        result = investigation["result"]

        logger.info(
            f"Investigation {incident_id} completed",
            extra={
                "incident_id": incident_id,
                "status": result["status"],
                "duration": investigation["duration"],
            },
        )

        # Verify investigation completed
        assert (
            result["status"] == "completed"
        ), f"Investigation {incident_id} failed: {result.get('error')}"

        # Verify root cause contains the incident ID (no state leakage)
        root_cause = result.get("root_cause", "").lower()
        assert incident_id.lower() in root_cause, (
            f"Root cause for {incident_id} doesn't contain incident ID. "
            f"Possible state leakage. Root cause: {root_cause}"
        )

        # Verify no other incident IDs appear in this result (state leakage check)
        for other_incident in test_incidents:
            if other_incident["id"] != incident_id:
                other_id = other_incident["id"].lower()
                assert other_id not in root_cause, (
                    f"Root cause for {incident_id} contains {other_id}. "
                    f"State leakage detected! Root cause: {root_cause}"
                )

    logger.info("✓ No state leakage detected in concurrent investigations")


@pytest.mark.asyncio
async def test_concurrent_investigations_performance(mock_llm_concurrent):
    """
    Test that concurrent investigations don't cause performance degradation.

    This test compares the performance of sequential vs concurrent investigations
    to ensure concurrent execution doesn't introduce significant overhead.

    Requirements: 8.4
    """
    logger.info("Starting concurrent investigations performance test")

    llm_config = create_mock_llm_config()

    # Use first 5 incidents
    test_incidents = CONCURRENT_TEST_INCIDENTS[:5]

    # Create agent
    mock_tools = create_mock_tools_for_incident("perf")
    agent = await create_investigation_agent_native(
        mcp_tools=mock_tools,
        llm_config=llm_config,
        correlation_id="concurrent-perf-test",
    )

    # Run investigations sequentially
    logger.info("Running investigations sequentially")
    sequential_start = datetime.utcnow()

    sequential_results = []
    for incident in test_incidents:
        result = await run_single_investigation(agent, incident)
        sequential_results.append(result)

    sequential_end = datetime.utcnow()
    sequential_duration = (sequential_end - sequential_start).total_seconds()

    # Run investigations concurrently
    logger.info("Running investigations concurrently")
    concurrent_start = datetime.utcnow()

    tasks = [run_single_investigation(agent, incident) for incident in test_incidents]
    concurrent_results = await asyncio.gather(*tasks)

    concurrent_end = datetime.utcnow()
    concurrent_duration = (concurrent_end - concurrent_start).total_seconds()

    # Calculate speedup
    speedup = (
        sequential_duration / concurrent_duration if concurrent_duration > 0 else 0
    )

    logger.info(
        "Concurrent performance results",
        extra={
            "sequential_duration": sequential_duration,
            "concurrent_duration": concurrent_duration,
            "speedup": speedup,
            "incident_count": len(test_incidents),
        },
    )

    # Concurrent should be faster (at least 1.5x speedup for 5 concurrent tasks)
    assert speedup >= 1.5, (
        f"Concurrent execution not efficient enough. "
        f"Speedup: {speedup:.2f}x (expected >= 1.5x). "
        f"Sequential: {sequential_duration:.3f}s, "
        f"Concurrent: {concurrent_duration:.3f}s"
    )

    # Verify all concurrent investigations completed successfully
    for investigation in concurrent_results:
        assert investigation["result"]["status"] == "completed"

    logger.info(f"✓ Concurrent performance test passed (speedup: {speedup:.2f}x)")

    print("\n" + "=" * 80)
    print("CONCURRENT PERFORMANCE RESULTS")
    print("=" * 80)
    print(f"\nIncidents Tested:       {len(test_incidents)}")
    print(f"Sequential Duration:    {sequential_duration:.3f}s")
    print(f"Concurrent Duration:    {concurrent_duration:.3f}s")
    print(f"Speedup:                {speedup:.2f}x")
    print("Expected Speedup:       >= 1.5x")
    print(f"Status:                 {'✓ PASS' if speedup >= 1.5 else '✗ FAIL'}")
    print("=" * 80 + "\n")


@pytest.mark.asyncio
async def test_high_concurrency_stress(mock_llm_concurrent):
    """
    Stress test with high number of concurrent investigations.

    This test runs many concurrent investigations to verify the system
    can handle high load without failures or state corruption.

    Requirements: 8.4
    """
    logger.info("Starting high concurrency stress test")

    llm_config = create_mock_llm_config()

    # Use all 10 incidents
    test_incidents = CONCURRENT_TEST_INCIDENTS

    # Create agent
    mock_tools = create_mock_tools_for_incident("stress")
    agent = await create_investigation_agent_native(
        mcp_tools=mock_tools,
        llm_config=llm_config,
        correlation_id="concurrent-stress-test",
    )

    logger.info(
        f"Running {len(test_incidents)} concurrent investigations (stress test)"
    )

    start_time = datetime.utcnow()

    # Run all investigations concurrently
    tasks = [run_single_investigation(agent, incident) for incident in test_incidents]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = datetime.utcnow()
    total_duration = (end_time - start_time).total_seconds()

    # Count successes and failures
    successes = 0
    failures = 0
    exceptions = 0

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            exceptions += 1
            logger.error(
                f"Investigation {test_incidents[i]['id']} raised exception",
                extra={"error": str(result)},
            )
        elif result["result"]["status"] == "completed":
            successes += 1
        else:
            failures += 1
            logger.warning(
                f"Investigation {test_incidents[i]['id']} failed",
                extra={"error": result["result"].get("error")},
            )

    success_rate = (successes / len(test_incidents)) * 100

    logger.info(
        "High concurrency stress test results",
        extra={
            "total_investigations": len(test_incidents),
            "successes": successes,
            "failures": failures,
            "exceptions": exceptions,
            "success_rate": success_rate,
            "total_duration": total_duration,
        },
    )

    # Assert at least 90% success rate
    assert success_rate >= 90, (
        f"Success rate too low: {success_rate:.1f}% "
        f"(successes: {successes}, failures: {failures}, exceptions: {exceptions})"
    )

    # Assert no exceptions
    assert exceptions == 0, f"Exceptions occurred: {exceptions}"

    logger.info(
        f"✓ High concurrency stress test passed "
        f"({successes}/{len(test_incidents)} successful, {success_rate:.1f}%)"
    )

    print("\n" + "=" * 80)
    print("HIGH CONCURRENCY STRESS TEST RESULTS")
    print("=" * 80)
    print(f"\nTotal Investigations:   {len(test_incidents)}")
    print(f"Successful:             {successes}")
    print(f"Failed:                 {failures}")
    print(f"Exceptions:             {exceptions}")
    print(f"Success Rate:           {success_rate:.1f}%")
    print(f"Total Duration:         {total_duration:.3f}s")
    print(f"Avg Duration:           {total_duration/len(test_incidents):.3f}s")
    print("Expected Success Rate:  >= 90%")
    print(
        f"Status:                 {'✓ PASS' if success_rate >= 90 and exceptions == 0 else '✗ FAIL'}"
    )
    print("=" * 80 + "\n")


@pytest.mark.asyncio
async def test_concurrent_investigations_isolation(mock_llm_concurrent):
    """
    Test that concurrent investigations are properly isolated.

    This test verifies that each investigation maintains its own correlation ID
    and doesn't mix data from other concurrent investigations.

    Requirements: 8.4
    """
    logger.info("Starting concurrent investigations isolation test")

    llm_config = create_mock_llm_config()

    # Use first 3 incidents for detailed isolation testing
    test_incidents = CONCURRENT_TEST_INCIDENTS[:3]

    # Create agent
    mock_tools = create_mock_tools_for_incident("isolation")
    agent = await create_investigation_agent_native(
        mcp_tools=mock_tools,
        llm_config=llm_config,
        correlation_id="concurrent-isolation-test",
    )

    # Run investigations concurrently
    tasks = [run_single_investigation(agent, incident) for incident in test_incidents]

    results = await asyncio.gather(*tasks)

    # Verify isolation
    for investigation in results:
        incident_id = investigation["incident_id"]
        result = investigation["result"]

        # Verify correlation ID matches incident ID
        assert result["correlation_id"] == incident_id, (
            f"Correlation ID mismatch for {incident_id}: "
            f"expected {incident_id}, got {result['correlation_id']}"
        )

        # Verify root cause is specific to this incident
        root_cause = result.get("root_cause", "")
        assert (
            incident_id in root_cause
        ), f"Root cause for {incident_id} doesn't contain incident ID: {root_cause}"

        # Verify tool calls are specific to this incident
        tool_calls = result.get("tool_calls", [])
        for tool_call in tool_calls:
            tool_args = tool_call.get("args", {})
            # Tool args should reference this incident's pod
            if "pod_name" in tool_args:
                assert (
                    incident_id in tool_args["pod_name"]
                ), f"Tool call for {incident_id} references wrong pod: {tool_args}"

    logger.info("✓ Concurrent investigations isolation test passed")
