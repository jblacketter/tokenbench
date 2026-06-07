# Incident Postmortem: API Latency Spike (2026-05-22)

## Executive Summary
On 2026-05-22 between 14:02 and 14:51 UTC, the public API experienced p99 latency
of 4.8s (baseline 180ms). Root cause was connection-pool exhaustion in the billing
service triggered by a retry storm. No data was lost. SLA credits apply to 3 tier-2
customers.

## Timeline
- 14:02 — Deploy of billing-svc v2.18 begins (rolling, 6 pods).
- 14:09 — First p99 alert fires; on-call paged.
- 14:18 — Retry storm identified; billing connection pool saturated at 100/100.
- 14:31 — Pool size raised 100 → 300 via config flag; partial relief.
- 14:44 — billing-svc v2.18 rolled back to v2.17.
- 14:51 — p99 returns to baseline; incident resolved.

## Root Cause
v2.18 changed the default HTTP client timeout from 30s to 2s without adjusting the
retry policy (3 retries, no backoff). Under a brief downstream slowdown, requests
timed out at 2s and immediately retried, tripling effective load and exhausting the
connection pool. The pool had no queue limit, so callers blocked instead of
fast-failing, propagating latency upstream to the public API.

## Contributing Factors
- No load test covered the new timeout under downstream slowness.
- Connection pool lacked a bounded wait queue and circuit breaker.
- Retry policy had no exponential backoff or jitter.
- The timeout change was buried in an unrelated refactor PR.

## What Went Well
- Alerting fired within 7 minutes of customer impact.
- The pool-size config flag allowed mitigation without a deploy.
- Rollback path was clean and fast.

## Action Items
1. Add exponential backoff + jitter to the billing client retry policy. (owner: dana)
2. Bound the connection pool wait queue and add a circuit breaker. (owner: lee)
3. Add a load test exercising downstream-slowness scenarios in CI. (owner: priya)
4. Lint rule: timeout/retry changes require an explicit reviewer sign-off. (owner: sam)
5. Document the pool-size flag in the runbook. (owner: dana)

## Appendix: Metrics
- Requests affected: ~412,000
- Error rate peak: 6.1%
- p50 / p95 / p99 at peak: 240ms / 2.1s / 4.8s
- Pods involved: billing-svc (6), api-gateway (12)
