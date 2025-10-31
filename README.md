# SRE-Orchestrator

This contains the design and implementation of the SRE-Orchestrator.

The original prompt to the [BMAD-Method](https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/user-guide.md)
using gemini-2.5-pro model with the [Gemini CLI](https://github.com/google-gemini/gemini-cli) was:

```
*plan I’m creating a new project, SRE Orchestrator that acts like a virtual SRE engineer. When users report issues
through a REST interface, the orchestrator uses an LLM (either local or cloud-based) to understand the problem and then
intelligently routes the investigation to specialized agents. THe Orchestrator works given a distributed system based
on cloud native technologies based on Kubernetes, Helm, Docker and simplifies the life of an SRE team by automatically
diagnosing the issue given application logs from pods, metrics from observability stack, event, alarms and the
application Helm structure and the live deployment status of pods, namespaces, persistent volumes, volume claims, and
other kubernetes constructs. The solution is based on AI agents dedicated to the tasks of pulling data from the external
application, these agents are based on the MOdel Context Protocol and some examples are An Authentication agent for
identity and access issues, A Database agent for data-related problems, A Kubernetes agent for container and
infrastructure issues. The product then correlates the different information collected and provides possible issues and
evidence to SRE team. The system should be deployable on a kubernetes cluster that already hosts the external
application under analysis and needs to be runnable together with any other product/app and attach itself to what is
available from the system. The product needs to be able to ingest existing documents provided but the application owner
like best known methods, runbooks and offer them to the agents as searchable elements to help in solution providing. The
system must offer a REST API that provides the error results and suggestions. The orchestrator also maintains context
about the system state through a digital twin or knowledge graph, so it understands how different components relate to
each other. The Orchestrator will leverage existing MCP servers for the agents, so it can start by reuse them if
existing (e.g. Prometheus MCP agent), if not new Langgraph agents can be written. Essentially, it's designed to take an
external application, look for user flow errors (e.g. 400, 500 errors) and automatically coordinate the right diagnostic
agents to pinpoint the possible issues and then provide actionable insights for resolution. 
```

## Usage

### Deploy SRE-Orchestrator

Deploy the SRE-Orchestrator by its helm chart to a Kubernetes cluster, passing in 
a Gemini API Key.

```bash
helm -n sre install sre ./charts/sre-orchestrator/ --set orchestrator.geminiApiKey=<YOUR_GEMINI_API_KEY> --create-namespace
```

### Deploy the MCP Server Kubernetes

The service depends on the MCP Server Kubernetes Helm chart to be deployed. First clone the repo.

```bash
git clone -b helm-charts https://github.com/Andrea-Campanella/mcp-server-kubernetes.git
cd mcp-server-kubernetes
```

Then install this chart with

```bash
helm -n msk install msk charts/mcp-server-kubernetes/ --create-namespace
```

### Test the MCP server

You can test that the service is working, by port forwarding port 3000 in a terminal window

```bash
kubectl -n msk port-forward service/msk-mcp-server-kubernetes 3000
```

and then running a curl command in another terminal:

```bash
curl -X POST \
-H Accept:application/json \
-H Accept:text/event-stream \
-H Content-Type:application/json \
http://localhost:3000/mcp \
-d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name":"ping"}}'
```

> this should give a response like
> `event: message`
> `data: {"result":{},"jsonrpc":"2.0","id":1}`

### Test the SRE orchestrator

To test the orchestrator you've got to give it an incident report.

First create a port-forward for the SRE service in a terminal window:

```bash
kubectl -n sre port-forward service/sre-orch-orchestrator 8080:80
```

Then in another terminal window call the API to create an incident, giving details of some pod
so that it's logs may be retrieved:

```bash
curl -X POST \
-H "Content-Type:application/json" \
localhost:8080/api/v1/incidents \
-d '{"description": "New Test incident pod:etcd-kind-control-plane namespace:kube-system"}'
```

This should return an incident ID in UUID format. The `k8s-agent-service` will go off and retrieve the
logs from the pod and add them to the incident.

These can be viewed by querying the incident by its ID. For example:

```bash
curl -H "Accept:application/json" localhost:8080/api/v1/incidents/b1c3392c-d653-4e77-be5b-b390d2a4ccb1 | jq
```
