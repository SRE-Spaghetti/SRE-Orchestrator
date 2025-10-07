# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependency files to the working directory
COPY pyproject.toml poetry.lock ./

# Install any needed packages specified in pyproject.toml
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --without dev --no-root

# Copy the rest of the application code to the working directory
COPY ./src/app ./app

RUN echo "components:" > /knowledge_graph.yaml && \
    echo "  - name: k8s-agent" >> /knowledge_graph.yaml && \
    echo "    type: service" >> /knowledge_graph.yaml

# Make port 80 available to the world outside this container
EXPOSE 80

# Run uvicorn when the container launches
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]

