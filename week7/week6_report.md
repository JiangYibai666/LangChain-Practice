# Week 6 Report (2026-04-03 to 2026-04-09)

## 1. Milestones Met

1. Finalized the procure-to-pay agent architecture and role boundaries, including specific responsibilities for RFQ agent, PO creation agent, receiving matching agent, invoice matching agent, and payment scheduling agent. Each agent adheres to the single-responsibility principle, with clear task allocation and collaboration modes defined.
2. Implemented resilience iteration for the current version, including procure-to-pay process validation and supplementation of citation/ID schema to ensure robust data handling and error recovery.
3. Demonstrated document-level closed-loop validation for the core business flow (request-approval-order-receipt-payment), achieving end-to-end verification of the procure-to-pay cycle.
4. Completed the technical route (The AI multi-agent architecture for Doxa Connex). Details the system design for embedding a chat-based AI assistant into the existing platform, utilizing multiple specialized agents to answer queries about invoices, entities, procurement, and payments while maintaining the platform's existing authentication and RBAC models without impacting production services. Key elements formulated include:
   - Architecture overview with independent traffic paths for chat and existing browser flows.
   - Decision summary covering choices for agent runtime (ECS Fargate), WebSocket layer (AWS API Gateway), agent communication (A2A protocol), LLM integration (AWS Bedrock with Claude and Titan models), RAG (Pinecone vector database), and data storage (Aurora PostgreSQL Serverless v2).
   - User flow descriptions for connection establishment, message handling, token refresh, and session recovery during task restarts.
   - Authentication and authorization framework ensuring zero compromise, with seven-layer security checks including JWT validation, RBAC enforcement, and agent-to-service communication through internal VPC paths.
   - Implementation phases structured into four stages: foundation setup, first agent with RAG, additional agents, and production hardening.

## 2. Milestones Missed

1. Deepened understanding of sub-platform business processes and database structures not fully completed, reason:
   - Ongoing discussions with business teams to refine interaction flows and database familiarity, expected to conclude in the next week.
2. Specific implementation of agent list and responsibilities not finalized, reason:
   - Infrastructure access confirmations are still pending from the access team, requiring additional coordination.
3. Initiated foundational infrastructure setup not fully completed, reason:
   - Infrastructure provisioning faced delays due to pending access confirmations from the access team.
   - Resolution: Daily sync meetings and prioritized access resolution.

## 3. Adjustments to schedule and effort

1. Optimized team collaboration for technical implementation:
   - Date: 2026-04-03, Background: Successful completion of architecture finalization allowed shift to infrastructure setup, Decision: Allocate additional resources to technical route documentation and initial phase implementation to build momentum.
2. Enhanced focus on business process understanding:
   - Date: 2026-04-05, Background: Identified gaps in database structure knowledge during validation demonstrations, Decision: Extend timeline for business process deep dive by one week to ensure solid foundation before full agent development.

## 4. Foreseeable risks and resolution

1. Infrastructure access delays impacting agent development:
   - Resolution: Daily sync meetings with access team, maintain requirements-output-action items board for transparency.
2. Token costs exceeding budget during LLM integration:
   - Resolution: Continue prioritizing Bedrock, implement mock+fallback pipelines, monitor usage with alerts.
3. Incomplete business logic refinement affecting agent role definitions:
   - Resolution: Adhere to single-responsibility principle, schedule weekly reviews with business teams to validate progress.

---

# Week 7 Plan (2026-04-10 to 2026-04-16)

## 1. Work assignment

- Mark and Neville: Complete business logic proposal formulation, including detailed Concierge and sub-agent interaction flows, and finalize sub-platform business process understanding.
- Yibai and SunRui: Deepen understanding of database structures and complete agent list and responsibilities definition.
- Technical expert team (Anand, Gota, SunRui, Yibai): Continue first-phase infrastructure setup, including orchestrator agent development and frontend WebSocket client implementation.
- Access team: Confirm all infrastructure access requirements and provide necessary credentials.
- Project lead and Nabil: Coordinate all parties, drive project progress, and prepare for second-phase agent development.

## 2. Milestones to be met

- Provision API Gateway WebSocket API + Lambda authorizer.
- Set up ECS Fargate cluster + Cloud Map namespace.
- Deploy `zuul-gateway-internal` K8s Service + internal NLB + Route 53 private zone.
- Provision Aurora PostgreSQL Serverless v2 + RDS Proxy.
- Run LangGraph checkpoint migration.
- Enable AWS Bedrock model access + create VPC endpoint.
- Build orchestrator agent skeleton (connect / message / disconnect).
- Frontend WebSocket client, implement ping and auto-reconnect.</content>
<parameter name="filePath">/Users/kyle/Documents/Doxa/LangChain-Practice/week6/week6_report.md