# SRE Orchestrator Helm Chart

This chart deploys the SRE Orchestrator application to a Kubernetes cluster.

The default values expect that there is a Kubernetes MCP server installed in the `msk` namespace
with the release name `msk` thereby giving a service name like:

```
msk-mcp-server.msk.svc.cluster.local
```

> If this is not the case override the `values.yaml`

## Prerequisites

- A running Kubernetes cluster
- `helm` command-line tool installed

## Installation

To install the chart, use the following command:

```bash
helm install sre-orchestrator . --namespace sre-orchestrator --create-namespace
```

## Uninstallation

To uninstall the chart, use the following command:

```bash
helm uninstall sre-orchestrator --namespace sre-orchestrator
```
