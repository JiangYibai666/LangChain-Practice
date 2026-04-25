# Week 8 Report (2026-04-17 to 2026-04-23)

## 1. Milestones Achieved

1. **Completed the full system architecture design for A2A_POC** — finalized all key design decisions covering dual traffic path isolation, internal VPC networking (ECS → internal NLB → Zuul Gateway), JWT passthrough, A2A agent communication, LLM integration with AWS Bedrock, RAG with Pinecone, and Aurora PostgreSQL for LangGraph state storage. The architecture is confirmed implementation-ready.

2. **Built and ran A2A_POC end-to-end** in a local environment, validating the multi-agent protocol and orchestration design:
   - **A2A Protocol Layer**: defined Task, Message, and AgentCard data structures; implemented an in-process message router that replaces HTTP while preserving full A2A protocol semantics.
   - **Agent Layer**: built three agents — Orchestrator, Flight Agent and Hotel Agent.
   - **Tool Layer**: implemented two LangChain tools that query mock JSON data, simulating the pattern to be replicated for production Doxa service calls.
   - **Database Layer**: set up SQLAlchemy async engine against PostgreSQL, defined session/agent_task/result tables, and wired up a LangGraph checkpointer.
   - **Frontend Dashboard**: built a local UI covering conversation view, A2A flow visualization, and a real-time log panel.
   - **Infrastructure**: one-command local stack spin-up with PostgreSQL container via Docker Compose.

3. **Validated key architectural decisions through A2A_POC**:
   - In-process A2A routing proves the protocol design before introducing network hops.
   - LangGraph `StateGraph` confirmed as viable orchestration primitive for intent routing and multi-agent task aggregation.
   - Mock data layer confirmed the tool abstraction pattern that production agents will reuse against Doxa's internal APIs.

## 2. Milestones Missed

1. Cloud infrastructure provisioning (API Gateway WebSocket, ECS Fargate cluster, internal NLB, Route 53 private zone, Aurora PostgreSQL Serverless v2, Bedrock VPC endpoint) was not completed.
   - **Cause**: Infrastructure access permissions remain partially unconfirmed; the team decided to front-load the local POC to de-risk A2A protocol design and LangGraph orchestration patterns before committing to cloud resource provisioning.
   - **Resolution**: Now that the POC has validated core design assumptions, Phase 1 cloud provisioning becomes the immediate priority for Week 9. Access requests for ECS, Aurora, and Bedrock VPC endpoints will be escalated with the confirmed POC as justification.

2. Production Orchestrator agent skeleton was not started.
   - **Cause**: Blocked by cloud infrastructure not yet being available; the local POC used in-process routing rather than real WebSocket flows.
   - **Resolution**: Phase 1 infrastructure deployment in Week 9 will unblock this; the POC orchestrator code will be directly ported as the skeleton, minimizing rework.

## 3. Plan and Effort Adjustments

- **2026-04-17**: Confirmed that Week 8 scope would be "architecture design + A2A_POC local build" rather than cloud infrastructure bring-up, given unresolved access permissions. POC domain was set to flight/hotel travel (neutral, all-mock data) to isolate A2A protocol validation from Doxa-specific business complexity.
- **2026-04-20**: Decided to use in-process A2A routing (replacing HTTP) for A2A_POC to eliminate network setup overhead, while explicitly preserving all A2A protocol semantics so the same code path transfers cleanly to the real HTTP-based implementation.
- **2026-04-22**: Reviewed the A2A_POC system architecture with the team; confirmed that the internal NLB + JWT passthrough design fully preserves Zuul Gateway's existing RBAC chain (6 of 7 checks, NGINX skipped intentionally), removing a previously open design risk.

## 4. Forecasted Risks and Mitigations

1. **Cloud infrastructure access still unconfirmed for ECS / Aurora / Bedrock**
   - Risk: Continued delay will push Phase 1 delivery past the planned window and cascade into Phase 2 (invoice agent + RAG).
   - Mitigation: Use A2A_POC and the completed architecture design as concrete deliverables to accelerate access approval. Identify a minimum verifiable subset (e.g., ECS cluster + Aurora only) to start integration testing while remaining access is pending.

2. **Gap between POC domain (travel) and production domain (invoices, entities, purchasing)**
   - Risk: Mock tool patterns may not cleanly map to Doxa's internal API response shapes, requiring rework in the tool layer.
   - Mitigation: Schedule a business team sync in Week 9 to walk through invoice and entity API contracts; write tool adapters against the actual Doxa API specs before building the full agent.

3. **LangGraph checkpoint schema divergence between local PostgreSQL and Aurora Serverless v2**
   - Risk: Migration scripts tested locally may behave differently against Aurora due to serverless cold-start or connection pooling differences.
   - Mitigation: Provision RDS Proxy alongside Aurora as specified in the architecture; run checkpoint migration smoke tests immediately after Aurora is accessible.

4. **JWT token expiry during long agent workflows**
   - Risk: A multi-step agent task (orchestrator → sub-agent → Zuul → service) may span a token expiry window, causing downstream 401 errors mid-conversation.
   - Mitigation: Implement token expiry pre-check in the orchestrator before each sub-agent dispatch; design the token refresh flow (Phase 4 item) as an early backstop even in the Phase 1 skeleton.

---

# Week 9 Plan (2026-04-24 to 2026-04-30)

## 1. Work Assignment

- **Phase 1 cloud infrastructure provisioning** (highest priority, unblocks all subsequent work):
  - Provision API Gateway WebSocket API with Lambda JWT authorizer.
  - Set up ECS Fargate cluster + Cloud Map private namespace.
  - Deploy Kubernetes Service (internal NLB) + Route 53 private hosted zone record.
  - Provision Aurora PostgreSQL Serverless v2 + RDS Proxy; run LangGraph checkpoint schema migrations.
  - Enable Bedrock model access + create VPC endpoint for ECS-to-Bedrock communication.

- **Port A2A_POC Orchestrator to production skeleton**:
  - Adapt the Orchestrator from in-process A2A routing to real HTTP-based A2A calls via Cloud Map DNS.
  - Wire up connection state persistence to Aurora (ported from A2A_POC database layer).
  - Front-end WebSocket client: implement ping keepalive and auto-reconnect.

- **Validate the internal VPC call chain**:
  - Deploy a minimal ECS task with a real user JWT and confirms Zuul's RBAC chain returns a 200.

- **Business domain alignment for Phase 2 preparation**:
  - Sync with the business/backend team to document invoice and entity API contracts (endpoints, request/response shapes, RBAC requirements).

## 2. Expected Milestones

1. **Phase 1 minimum viable environment operational**:
   - API Gateway WebSocket API + Lambda authorizer live and accepting connections.
   - ECS Fargate cluster running with Cloud Map namespace registered.
   - Bedrock VPC endpoint reachable from ECS tasks; Bedrock Claude model returns a test completion.

2. **Internal NLB + Route 53 private zone verified**:
   - A test ECS task successfully calls a Zuul-proxied service endpoint using a valid JWT and receives a non-401 response.

3. **Production Orchestrator skeleton deployed to ECS**:
   - Supports `connect / message / disconnect` lifecycle events.
   - Persists connection state to Aurora PostgreSQL.
   - WebSocket client can ping and auto-reconnect on task restart.

4. **Aurora + LangGraph checkpoint migration confirmed**:
   - Checkpoint tables created and validated against a real LangGraph state write/read cycle on Aurora Serverless v2.
