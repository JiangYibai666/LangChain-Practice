# Week 9 Report (2026-04-24 to 2026-04-30)

## 1. Milestones Achieved

1. **ECS Fargate cluster provisioned and Cloud Map private namespace registered** — the base compute layer is live. A minimal ECS task definition was created and verified to launch successfully. Cloud Map namespace `internal.doxa.local` is registered and resolving within the VPC.

2. **API Gateway WebSocket API created with Lambda authorizer stub** — the WebSocket API endpoint is reachable; the Lambda JWT authorizer is deployed but currently returns a hardcoded `allow` policy pending integration with the real token validation library. Functional authorization validation is deferred to Week 10.

3. **Business domain alignment sync completed** — held a 90-minute session with the business and backend teams. Invoice and entity API endpoint names were catalogued; response shape examples for three invoice query endpoints were collected. Full request/response contracts and RBAC requirements are still being compiled by the backend team and are not yet available for tool adapter development.

## 2. Milestones Missed

1. **Phase 1 minimum viable environment not fully operational** — Aurora was blocked by a pending IAM role approval (arrived 2026-04-29, too late to act on). Bedrock VPC endpoint quota request is still pending. Aurora provisioning starts 2026-05-01; a public-endpoint Bedrock fallback is being evaluated.

2. **Internal NLB + Route 53 private zone not verified** — depends on Aurora being live first. NLB configuration was started but not completed; will be finished alongside Aurora in Week 10.

3. **Production Orchestrator skeleton not deployed to ECS** — local porting is ~40% complete but blocked on Aurora for connection state persistence. Container build and deployment will follow within 1–2 days of Aurora being reachable.

4. **Aurora + LangGraph checkpoint migration not confirmed** — blocked by Aurora not yet provisioned. Migration scripts are written and tested locally; ready to run on Aurora immediately.

## 3. Plan and Effort Adjustments

- **2026-04-24**: Began ECS cluster and Cloud Map setup; identified that the Aurora IAM role was missing before any database provisioning could begin. Opened an access request ticket with the cloud platform team.
- **2026-04-25**: Shifted focus to API Gateway WebSocket API setup to make forward progress while waiting for IAM approval. Completed the stub Lambda authorizer.
- **2026-04-28**: Conducted the business domain alignment sync. Decision was made to accept partial API contract documentation this week and complete it in Week 10, rather than wait for the full specification before starting tool adapter design.
- **2026-04-29**: IAM role approval received late in the day. Aurora provisioning was not started this week as a result; it becomes the first action item for Week 10.
- **Overall**: The week was substantially impacted by external dependencies — IAM access and Bedrock quota approval — that were outside the team's direct control. Internal execution items (local Orchestrator porting, migration script preparation, business sync) progressed as planned.

## 4. Forecasted Risks and Mitigations

1. **Aurora delay cascading into Phase 2** — all downstream work (NLB, Orchestrator, LangGraph, Phase 2 agents) is blocked on Aurora. Mitigation: provision Aurora first thing on 2026-05-01; run checkpoint migration and Orchestrator container build in parallel.

2. **Bedrock quota approval timeline unknown** — without approval, LLM integration testing is blocked. Mitigation: activate public-endpoint fallback while quota escalation continues with the technical lead.

3. **Incomplete invoice API contracts** — backend team has not delivered full request/response shapes or RBAC requirements. Mitigation: request a firm delivery deadline; begin tool adapter design against the three documented endpoints, stubbing the rest.

4. **Lambda JWT authorizer still a stub** — the current authorizer allows all traffic through, unsafe outside isolated dev testing. Mitigation: real token validation integration is a Week 10 prerequisite before the WebSocket API enters any shared environment.

---

# Week 10 Plan (2026-05-01 to 2026-05-07)

## 1. Work Assignment

- **Complete Phase 1 cloud infrastructure** (carry-over, highest priority):
  - Provision Aurora PostgreSQL Serverless v2 + RDS Proxy immediately on 2026-05-01.
  - Run LangGraph checkpoint schema migrations against Aurora; validate with a real state write/read cycle.
  - Configure internal NLB with ECS service as target; create Route 53 private hosted zone record.
  - Resolve Bedrock VPC endpoint quota; configure VPC endpoint or activate public-endpoint fallback.

- **Complete API Gateway Lambda JWT authorizer**:
  - Integrate the stub authorizer with the real JWT validation library.
  - Test with a valid and an invalid token before the WebSocket API is promoted to shared test environment.

- **Finalize and deploy Production Orchestrator skeleton to ECS**:
  - Complete the remaining ~60% of the A2A_POC Orchestrator port (HTTP-based A2A calls via Cloud Map DNS).
  - Containerize and push to ECR; deploy ECS task definition.
  - Wire Aurora connection string; validate `connect / message / disconnect` lifecycle events end-to-end.
  - Confirm WebSocket client ping keepalive and auto-reconnect behavior.

- **Validate internal VPC call chain**:
  - Deploy a test ECS task that calls a Zuul-proxied service endpoint with a real user JWT; confirm 200 response and full RBAC chain pass.

- **Phase 2 preparation**:
  - Obtain complete invoice and entity API contracts from backend team.
  - Sketch invoice tool adapter interfaces; identify any RBAC or authentication edge cases.

## 2. Expected Milestones

1. **Aurora PostgreSQL Serverless v2 live and validated**:
   - Cluster provisioned with RDS Proxy; LangGraph checkpoint tables created; write/read cycle confirmed against Aurora.

2. **Full Phase 1 environment operational**:
   - API Gateway WebSocket API with real JWT authorization accepting connections.
   - Internal NLB routing to ECS; Route 53 private zone record resolving.
   - Bedrock model reachable from ECS tasks and returning a test completion.

3. **Production Orchestrator skeleton deployed and verified**:
   - Running in ECS Fargate, persisting connection state to Aurora, handling full `connect / message / disconnect` lifecycle via real HTTP-based A2A calls.

4. **Internal VPC call chain end-to-end validated**:
   - Test ECS task → internal NLB → Zuul Gateway → service: 200 response with valid JWT confirmed.
