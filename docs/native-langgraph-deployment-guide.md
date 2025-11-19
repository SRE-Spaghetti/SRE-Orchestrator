# Native LangGraph Deployment Guide

This guide provides instructions for deploying and monitoring the native LangGraph StateGraph implementation in production.

## Overview

The native LangGraph implementation is now the default for the SRE Orchestrator. This guide covers:
- Deployment strategy (staging → production)
- Monitoring and observability
- Performance validation
- Rollback procedures

## Deployment Strategy

### Phase 1: Deploy to Staging

Deploy the native implementation to staging first to validate behavior in a production-like environment.

**Helm Deployment:**

```bash
# Deploy to staging namespace
helm upgrade --install sre-orchestrator ./charts/sre-orchestrator \
  --namespace sre-orchestrator-staging \
  --create-namespace \
  --set llm.baseUrl="https://api.openai.com/v1" \
  --set llm.modelName="gpt-4" \
  --set llm.apiKey="your-api-key"
```

**Docker Deployment:**

```bash
docker run -d \
  -e LLM_BASE_URL="https://api.openai.com/v1" \
  -e LLM_API_KEY="your-api-key" \
  -e LLM_MODEL_NAME="gpt-4" \
  -v /path/to/mcp_config.yaml:/config/mcp_config.yaml \
  -p 8000:80 \
  sre-orchestrator:latest
```

### Phase 2: Validate Staging

Run validation tests in staging before promoting to production.

**Test Investigation Quality:**

```bash
# Run test investigations with known incidents
curl -X POST http://staging-orchestrator/api/v1/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "test-001",
    "description": "Pod auth-service-xyz is in CrashLoopBackOff state",
    "severity": "high"
  }'
```

**Check Logs:**

```bash
# Kubernetes
kubectl logs -n sre-orchestrator-staging deployment/sre-orch-orchestrator --tail=100

# Docker
docker logs <container-id> --tail=100
```

Look for:
- ✅ "Creating native LangGraph investigation agent"
- ✅ "Agent node executing"
- ✅ "Tool node executing"
- ✅ "Routing to tools" or "Routing to end"
- ❌ No errors or exceptions

### Phase 3: Deploy to Production

Once staging validation is complete, deploy to production.

**Helm Deployment:**

```bash
# Deploy to production namespace
helm upgrade --install sre-orchestrator ./charts/sre-orchestrator \
  --namespace sre-orchestrator \
  --create-namespace \
  --set llm.baseUrl="https://api.openai.com/v1" \
  --set llm.modelName="gpt-4" \
  --set llm.apiKey="your-api-key"
```

## Monitoring

### Key Metrics to Monitor

#### 1. Investigation Success Rate

Monitor the percentage of investigations that complete successfully vs. fail.

**Log Query (Kubernetes):**

```bash
# Count successful investigations
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Investigation completed successfully" | wc -l

# Count failed investigations
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Investigation failed" | wc -l
```

**Expected:** >95% success rate

#### 2. Investigation Duration

Monitor how long investigations take to complete.

**Log Query:**

```bash
# Look for duration in investigation results
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "duration_seconds"
```

**Expected:** 5-15 seconds per investigation (similar to legacy implementation)

#### 3. Graph Execution Logs

Monitor graph node execution to ensure proper workflow.

**Log Query:**

```bash
# Check agent node execution
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Agent node"

# Check tool node execution
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Tool node"

# Check routing decisions
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Routing to"
```

**Expected Pattern:**
1. "Creating native LangGraph investigation agent"
2. "Agent node executing"
3. "Agent node completed"
4. "Routing to tools" (if tools needed)
5. "Tool node executing" (if tools needed)
6. "Agent node executing" (after tools)
7. "Routing to end"
8. "Investigation completed successfully"

#### 4. Error Rate

Monitor for errors in graph execution.

**Log Query:**

```bash
# Check for agent node failures
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Agent node failed"

# Check for tool execution failures
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Tool execution failed"

# Check for graph construction failures
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Failed to create investigation agent"
```

**Expected:** <5% error rate

#### 5. Correlation ID Tracing

Use correlation IDs to trace individual investigations through the logs.

**Log Query:**

```bash
# Trace a specific investigation
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "correlation_id.*<your-correlation-id>"
```

### Performance Validation

Compare performance between native and legacy implementations (if running both).

**Metrics to Compare:**
- Average investigation duration
- P95 investigation duration
- Success rate
- Error rate
- Memory usage
- CPU usage

**Acceptance Criteria:**
- Duration within 10% of legacy implementation
- Success rate ≥ legacy implementation
- Error rate ≤ legacy implementation

### Investigation Quality Validation

Validate that investigation results maintain quality.

**Metrics to Check:**
- Root cause identification accuracy
- Confidence levels (high/medium/low distribution)
- Evidence completeness
- Recommendation relevance

**Validation Method:**
1. Run same incidents through both implementations
2. Compare root cause analysis
3. Verify tool usage patterns
4. Check recommendation quality

## Troubleshooting

### Issue: Investigations Failing

**Symptoms:**
- High error rate
- "Agent node failed" in logs
- "Investigation failed" status

**Diagnosis:**

```bash
# Check for LLM connection issues
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "LLM"

# Check for tool execution issues
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Tool execution failed"
```

**Solutions:**
1. Verify LLM credentials and connectivity
2. Check MCP server availability
3. Review tool configuration
4. Check for rate limiting

### Issue: Slow Performance

**Symptoms:**
- Investigation duration >20 seconds
- Timeouts

**Diagnosis:**

```bash
# Check node execution times
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Agent node executing" -A 5

# Check tool execution times
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "Tool node executing" -A 5
```

**Solutions:**
1. Check LLM response times
2. Verify MCP server performance
3. Review network latency
4. Consider increasing timeouts

### Issue: Incorrect Results

**Symptoms:**
- Wrong root cause identified
- Low confidence scores
- Missing evidence

**Diagnosis:**

```bash
# Review full investigation trace
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator | \
  grep "correlation_id.*<id>" | less
```

**Solutions:**
1. Review system prompt configuration
2. Check tool availability and results
3. Verify LLM model configuration
4. Review routing logic

## Rollback Procedure

If critical issues are detected in production, you can rollback to a previous version.

### Image Rollback

Rollback to a previous image version that contains the legacy implementation (if available):

```bash
helm rollback sre-orchestrator -n sre-orchestrator
```

Or specify a specific revision:

```bash
# List available revisions
helm history sre-orchestrator -n sre-orchestrator

# Rollback to specific revision
helm rollback sre-orchestrator <revision-number> -n sre-orchestrator
```

### Verification After Rollback

```bash
# Check pod status
kubectl get pods -n sre-orchestrator

# Check logs for errors
kubectl logs -n sre-orchestrator deployment/sre-orch-orchestrator --tail=100

# Verify health endpoint
kubectl port-forward -n sre-orchestrator svc/sre-orchestrator 8080:80
curl http://localhost:8080/health
```

**Note:** The legacy implementation has been removed from the codebase. If you need to rollback, you must use a previous image version that still contains the legacy code.

## Monitoring Dashboard (Optional)

Consider setting up a monitoring dashboard with:

### Prometheus Metrics (Future Enhancement)

```yaml
# Example metrics to expose
- investigation_total{status="success|failed"}
- investigation_duration_seconds{quantile="0.5|0.95|0.99"}
- graph_node_execution_total{node="agent|tools"}
- graph_node_duration_seconds{node="agent|tools"}
- tool_execution_total{tool_name="...", status="success|failed"}
```

### Grafana Dashboard (Future Enhancement)

Create dashboards showing:
- Investigation success rate over time
- Investigation duration percentiles
- Error rate by type
- Tool usage patterns
- Correlation ID traces

## Best Practices

1. **Always deploy to staging first** - Validate behavior before production
2. **Monitor for 24-48 hours** - Ensure stability over time
3. **Compare with baseline** - Track metrics against legacy implementation
4. **Keep rollback ready** - Have rollback procedure documented and tested
5. **Use correlation IDs** - Always include correlation IDs for tracing
6. **Review logs regularly** - Check for patterns or anomalies
7. **Test with real incidents** - Use actual production incidents for validation

## Support

If you encounter issues:

1. Check this guide for troubleshooting steps
2. Review logs with correlation ID tracing
3. Compare behavior with legacy implementation
4. Consider rollback if critical issues detected
5. Report issues with full log context

## Next Steps

After successful deployment:

1. Monitor for 1-2 weeks in production
2. Gather performance metrics
3. Validate investigation quality
4. Plan removal of legacy implementation (task 12)
5. Consider adding custom nodes for enhanced workflows
