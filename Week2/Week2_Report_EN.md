# Weekly Plan and Progress Report (Week 2: 2026-03-09 ~ 2026-03-13)

## I. Week 2 Report

### 1. Milestones Met

1. **Completed Core Capability Validation**
   - Verified the Large Language Model pipeline (basic prompts, sequential chains, structured outputs, routing chains, RAG retrieval).
   - Verified the feasibility of the document retrieval vector database (`CSVLoader` + `VectorstoreIndexCreator` + `InMemoryVectorStore`) for business Q&A scenarios.
2. **Advanced Business & Management Tasks**
   - Reviewed month 1 design phase deliverables: BRD (Business Requirement Document), architecture, data models, API specifications, security & compliance, risk management, and KPIs.
   - Completed the requirements interview template, organizing the 4 core scenarios and their priorities: "Procurement - Invoice - Financing - Delivery".
   - Drafted the Project Management Dashboard: tracking the progress of 16 agents, risk registry, and resource/time consumption.

### 2. Milestones Missed

1. The comprehensive and detailed BRD is not yet complete (Agents for procurement orders, invoice matching, risk early-warning, and cash flow prediction still need to be finalized).
2. Connex API specifications are not yet finalized (Unified documentation is missing for request/response/error codes/authentication/version management).
3. The evaluation system is not yet implemented (Quantified KPIs, evaluation metrics, and regression testing plans are unfinished).

**Reason for Missed Milestones:**
- The focus of Week 2 was heavily shifted towards requirements alignment, solution confirmation, and continued self-practice. Coding and integration iterations became secondary.
- The cross-team review process requires more input from business and compliance teams, which prolonged the document delivery cycle.

**Resolution:**
- In Week 3, enhance communication with the company's business departments to secure more resource support, further clarify development use cases, and define iteration milestones.

### 3. Adjustments to Schedule and Effort

- **2026-03-11** (Context: Identified multi-model benchmarking needs in Week 2)
  *Decision:* Considering expanding the LangChain downstream model selection from "OpenAI only" to "Google/Anthropic/Custom", and attempting to add end-to-end inspections.
- **2026-03-13** (Context: Increased demand for requirements documentation)
  *Decision:* In Week 3, increase communication with business departments, clarify BRD and API specs, and consider writing documentation to synchronize with the project repository.

### 4. Foreseeable Risks and Resolution

1. **Risk:** Version compatibility explosion across multiple models and libraries leading to repetitive debugging.
   - **Response:** Pin the versions of `langchain`, `langchain-google-genai`, and `langchain-anthropic`. Set up a `requirements.txt` and lock testing environments.
2. **Risk:** Insufficient model API keys or quotas interrupting local validation.
   - **Response:** Prepare backup keys and use `FakeEmbeddings` as an offline capability validation tool.

## II. Week 3 Plan (2026-03-16 ~ 2026-03-20)

### 1. Who Will Do What

- **Business & Product:** Complete the BRD (for the 4 sub-agents: Procurement Orders, Invoice Matching, Risk Early-Warning, Cash Flow Prediction).
- **Engineering:** Refine code for key capability validations (routing chains, vector retrieval, tool calling) and output test results.
- **Data:** Build validation datasets (several test cases for Q&A, retrieval, and tool calling failures).
- **Testing:** Design regression tests, and record key metrics (success rate / response time / consistency).

### 2. Milestones to Be Met

1. Complete the BRD and confirm it with the business departments.
2. Complete core capability validation (including multi-model comparisons) and output the results report.