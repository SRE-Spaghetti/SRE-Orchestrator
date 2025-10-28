# SRE Orchestrator Helm Chart

This chart deploys the SRE Orchestrator application to a Kubernetes cluster.

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
