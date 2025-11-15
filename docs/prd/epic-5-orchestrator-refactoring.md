# Epic 5: Orchestrator Refactoring

**Goal:** This epic focuses on modernizing the SRE Orchestrator architecture by eliminating the separate k8s-agent microservice in favor of MCP-based Kubernetes integration, replacing the native Gemini API client with LangChain for better LLM flexibility, implementing a LangGraph-based agentic workflow for intelligent incident analysis, and adding a CLI for natural language interaction. By the end of this epic, we will have a more maintainable, extensible, and intelligent architecture while maintaining API compatibility.

## Overview

The refactoring will modernize the architecture by:
- **Eliminating k8s-agent service**: Replace with MCP-based Kubernetes integration for simplified architecture
- **LangChain integration**: Replace native Gemini API with LangChain for LLM flexibility and provider independence
- **LangGraph workflow**: Implement a ReAct agent pattern for autonomous incident investigation
- **CLI application**: Add interactive command-line interface for natural language interaction
- **Enhanced observability**: Comprehensive error handling and logging throughout the system

## Architecture Changes

### Removed Components
- **k8s-agent service**: Entire microservice eliminated
- **k8s_agent_client**: Client library removed from orchestrator
- **google-generativeai**: Native Gemini SDK removed

### New Components
- **LangGraph Workflow Engine**: State machine for incident investigation using ReAct pattern
- **LangChain LLM Client**: Unified LLM interface with OpenAI compatibility
- **CLI Application**: Interactive command-line interface
- **MCP Tool Executor**: Dynamic tool execution from MCP servers

### Modified Components
- **Orchestrator Service**: Enhanced with LangGraph workflow
- **MCP Connection Manager**: Extended to support tool discovery and execution
- **Incident Repository**: Updated to support async workflow execution

## Requirements Mapping

### Requirement 1: Remove K8s Agent Service
- The orchestrator uses MCP servers for Kubernetes integration
- No dependency on k8s-agent service
- All k8s-agent code and deployment configs removed
- k8s_agent_client module removed from orchestrator

### Requirement 2: Replace Gemini Client with LangChain
- LangChain used for all LLM interactions
- Support for OpenAI-compatible API endpoints
- google-generativeai dependency removed
- LLM configuration via environment variables
- Structured output using LangChain capabilities

### Requirement 3: Implement LangGraph Agentic Workflow
- LangGraph state machine for incident investigation
- Workflow nodes: intake, entity extraction, data collection, analysis, root cause determination
- MCP tools used for Kubernetes data collection
- Investigation state maintained throughout execution
- Conditional branching based on evidence
- Asynchronous workflow execution
- Status updates as workflow progresses

### Requirement 4: Enhance MCP Integration
- Tool discovery from connected MCP servers
- Dynamic MCP tool invocation based on investigation needs
- Graceful error handling for tool execution
- Logging of all tool invocations with parameters and results
- Support for multiple MCP servers simultaneously

### Requirement 5: Create Interactive CLI
- Chat-like interface for natural language interaction
- Connection to orchestrator via REST API
- Incident creation and result display
- Streaming response support for real-time progress
- Formatted output with syntax highlighting
- Configuration via command-line arguments
- Conversation history within session
- Commands for listing and viewing past incidents

### Requirement 6: Update Architecture Documentation
- Remove k8s-agent references
- Document LangChain integration approach
- Include LangGraph workflow diagram
- Document CLI architecture and usage
- Update component diagram for MCP-based architecture
- Update technology stack table

### Requirement 7: Maintain Backward Compatibility
- Existing POST /api/v1/incidents endpoint maintained
- Existing GET /api/v1/incidents/{id} endpoint maintained
- Existing GET /health endpoint maintained
- Incident response model includes all existing fields
- API response format remains compatible

### Requirement 8: Improve Error Handling and Observability
- LangGraph workflow logs state transitions and decisions
- All MCP tool invocations logged with timing
- Error context captured and incident status updated on failures
- Structured JSON logs for all operations
- Health endpoint includes LangChain and MCP connection status

## Stories

### Story 5.1: Update Dependencies and Add LangChain/LangGraph
Establish the foundation by updating project dependencies to include LangChain and LangGraph while removing the Gemini SDK.

### Story 5.2: Implement LangChain LLM Client
Create a new LLM client based on LangChain that supports OpenAI-compatible endpoints and provides structured output capabilities.

### Story 5.3: Implement MCP Tool Integration with LangChain
Build the MCP tool manager that discovers and provides LangChain-compatible tools from MCP servers.

### Story 5.4: Implement LangGraph ReAct Agent Workflow
Create the core investigation workflow using LangGraph's ReAct agent pattern for autonomous incident analysis.

### Story 5.5: Update Incident Repository for Async Workflow
Refactor the incident repository to work with the asynchronous LangGraph workflow and track investigation steps.

### Story 5.6: Remove K8s-Agent Service and Dependencies
Clean up the codebase by removing all k8s-agent related code, dependencies, and deployment configurations.

### Story 5.7: Implement CLI Application
Build an interactive command-line interface for natural language interaction with the orchestrator.

### Story 5.8: Update Documentation
Comprehensively update all documentation to reflect the refactored architecture.

### Story 5.9: Update Helm Chart Configuration
Modify deployment configurations to support the new architecture with LLM and MCP settings.

### Story 5.10: Add Comprehensive Error Handling and Logging
Enhance observability throughout the system with structured logging and robust error handling.

### Story 5.11: Write Tests for Refactored Components
Create comprehensive test coverage for all new and modified components.

### Story 5.12: Update Deployment and CI/CD
Finalize deployment artifacts and CI/CD pipeline for the refactored system.

## Migration Path

The refactoring follows an incremental approach to minimize risk:

1. **Phase 1**: Add LangChain and LangGraph alongside existing code
2. **Phase 2**: Enhance MCP integration with tool discovery and execution
3. **Phase 3**: Remove k8s-agent service and switch to new workflow
4. **Phase 4**: Add CLI application
5. **Phase 5**: Final testing and documentation updates

Each phase can be rolled back independently if issues arise.

## Performance Considerations

### Expected Latency
- Entity Extraction: 1-2 seconds (LLM call)
- Tool Discovery: < 100ms (cached)
- Data Collection: 2-5 seconds (MCP calls)
- Analysis: 2-3 seconds (LLM call)
- **Total**: 5-10 seconds per investigation

### Resource Usage
- Memory: ~100-200 MB for orchestrator
- CPU: Minimal (I/O bound workload)
- Network: External LLM API calls

## Security Considerations

- LLM API keys stored in Kubernetes secrets
- Rate limiting to prevent API abuse
- MCP server certificate validation
- Sanitized tool inputs to prevent injection attacks
- CLI config file with secure permissions (0600)
- Token-based authentication for orchestrator API

## Success Criteria

1. All existing API endpoints remain functional
2. Investigation workflow completes successfully using LangGraph
3. MCP tools are discovered and executed correctly
4. CLI can interact with orchestrator and display results
5. All tests pass with 80% coverage
6. Documentation is comprehensive and accurate
7. Deployment succeeds in Kubernetes using updated Helm chart
8. Performance meets or exceeds existing system (5-10 seconds per investigation)
