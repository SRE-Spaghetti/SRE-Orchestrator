# SRE Orchestrator - Refactored Architecture
# Uses LangChain/LangGraph for intelligent incident investigation
# Integrates with MCP servers for Kubernetes data collection
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependency files to the working directory
# Includes LangChain, LangGraph, and langchain-mcp-adapters
COPY services/orchestrator/pyproject.toml services/orchestrator/poetry.lock ./

# Install dependencies
# Note: k8s-agent dependencies removed in refactoring
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --without dev --no-root && \
    # Clean up pip cache to reduce image size
    pip cache purge && \
    # Remove poetry after installation to reduce image size
    pip uninstall -y poetry

# Copy the application code
COPY services/orchestrator/src/app ./app

# Copy MCP configuration
COPY services/orchestrator/mcp_config.yaml ./mcp_config.yaml

# Create minimal knowledge graph for service metadata
RUN echo "components:" > /knowledge_graph.yaml && \
    echo "  - name: orchestrator-service" >> /knowledge_graph.yaml && \
    echo "    type: service" >> /knowledge_graph.yaml && \
    echo "    relationships: []" >> /knowledge_graph.yaml

# Make port 80 available to the world outside this container
EXPOSE 80

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:80/health')"

# Run uvicorn when the container launches
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]

