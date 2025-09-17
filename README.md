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

