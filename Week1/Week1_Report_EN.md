# Weekly Plan & Progress Report (Week 1)

## Part 1: Week 1 Report (2026-03-02 ~ 2026-03-06)

### 1. Milestones Met

1. Completed project environment setup and model integration verification
   - Connected two LLM providers (`ChatGoogleGenerativeAI` and `ChatAnthropic`) and validated end-to-end invocation. Built a parameterized translation task using `ChatPromptTemplate` with `style` and `text` variables, confirming that the core LangChain workflow — model connection, prompt engineering, and structured output — functions correctly and forms a stable foundation for all subsequent modules.
2. Studied the basic structure and workflow of Retrieval-Augmented Generation (RAG)
   - Gained a clear understanding of the core components: external documents are first processed by an embedding model and stored as vectors in a vector database. When a user submits a query, it triggers a similarity search against this database to retrieve the most relevant documents. These documents are then integrated into a prompt, which is fed into a large language model (LLM) to generate a context‑aware response. This architecture effectively augments the LLM’s knowledge with external, up‑to‑date information without requiring model retraining.
3. Completed basic data preparation and sample set generation
   - Loaded a large Amazon product review dataset from a CSV source and extracted the top 10% of rows by index as a lightweight working sample. This subset reduces compute cost and API usage during rapid prototyping while remaining representative enough for chain and retrieval experiments.
4. Completed prototype implementations of multiple LangChain chain types
   - Built and validated three distinct chain architectures using real review data:
   - **Simple chain**: demonstrates the basic Prompt → LLM → output pipeline, applied to single-sentence summarization of product reviews.
   - **Sequential chain**: chains three LLM steps in order — summarization, language detection, and follow-up response generation — passing intermediate outputs as inputs to the next stage.
   - **Router chain**: implements `MultiPromptChain` to classify incoming questions by subject (physics, math, history, computer science) and dispatch each to a domain-specific sub-chain with tailored system instructions.
5. Completed conversational memory capability verification
   - Implemented `ConversationBufferMemory` paired with `ConversationChain` to maintain full dialogue history across turns. Verified that the model correctly recalls user-provided context (e.g., name) and respects style instructions issued mid-conversation (e.g., switching to short-form answers), confirming robust multi-turn state management.
6. Completed document retrieval and vector index prototype
   - Built a retrieval pipeline using `CSVLoader` to ingest product catalog data as LangChain `Document` objects, `GoogleGenerativeAIEmbeddings` to generate semantic embeddings, `VectorstoreIndexCreator` with `DocArrayInMemorySearch` as the in-memory vector store, and `RetrievalQA` to answer natural language queries over the indexed documents. Validated end-to-end with a structured Markdown-formatted query response.
7. Completed initial implementation of a tool-calling Agent
   - Defined four tools — arithmetic operations (`add`, `multiply`), external data lookup (`get_weather`), and structured file output (`save_to_csv_with_path`) — and registered them with a `create_agent` loop backed by an Anthropic model. Verified that the agent correctly selects and invokes the appropriate tool based on user intent, closing the full tool-calling orchestration loop.

### 2. Milestones Missed

As this week's work was practice-oriented, there are no missed project milestones. However, the following inconveniences in the current code are noted for reference:

1. Practice modules are spread across separate notebooks and scripts with no shared entry point, making it cumbersome to run or demonstrate multiple capabilities together.
2. No real-world use case has been applied yet — review data and a product catalog were used as stand-ins, which limits the relevance of current outputs.
3. The `get_weather` tool is a hardcoded placeholder and does not reflect a realistic agent tool implementation.

These are expected limitations of a practice codebase. The specific direction for improvement will be determined once the supervisor provides the real project plan next week.

### 3. Adjustments to Schedule and Effort

- 2026-03-04 (Context: basic pipeline verification completed)
  Decision: Expanded practice scope to cover Router Chain, RetrievalQA, and Memory to ensure broad familiarity with core LangChain capabilities before the real project begins.

- 2026-03-06 (Context: supervisor confirmed real project plan will be provided next week, with focus on AI Agent and RAG)
  Decision: Deferred any engineering integration or evaluation work; next week's tasks will be restructured around the actual project requirements.

### 4. Foreseeable Risks and Resolutions

1. Risk: The real project scope (to be provided next week) may require frameworks or patterns not yet covered in practice.
   Mitigation: Review LangChain Agent and RAG documentation proactively to reduce onboarding time when the project starts.

2. Risk: Practice code habits (e.g., hardcoded configs, no error handling) may carry over into the real project.
   Mitigation: Treat practice notebooks as reference only; start the real project with clean, structured code from the outset.

---

## Part 2: Week 2 Plan (2026-03-09 ~ 2026-03-13)

### 1. Who Will Do What

1. Project kickoff: Receive the real project plan and specific use case from the supervisor; clarify requirements, expected deliverables, and timeline.
2. Technical preparation: Review LangChain Agent orchestration patterns and RAG pipeline design based on the confirmed project direction.
3. Environment setup: Configure the project environment, API keys, and data sources according to the actual project requirements.
4. Initial implementation: Begin building the first working prototype based on the supervisor's use case.

### 2. Milestones to be Met

1. Receive and fully understand the real project plan and use case from the supervisor.
2. Complete environment and toolchain setup aligned with the actual project requirements.
3. Deliver a first working prototype or proof-of-concept for the assigned use case.

---

## Part 3: Appendix — Overall Project Plan / Progress Table

| Phase                                        | Planned Timeline        | Target Deliverables                                                 | Current Status                                              | Progress |
| -------------------------------------------- | ----------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------- | -------- |
| Phase 1: Environment & Data Preparation      | 2026-03-02 ~ 2026-03-04 | API integration, data loading, and sample generation                | Completed                                                   | 100%     |
| Phase 2: Core Capability Prototypes          | 2026-03-04 ~ 2026-03-07 | Simple / sequential / router / memory / retrieval chains            | Mostly completed                                            | 85%      |
| Phase 3: Agent Tooling & External Interfaces | 2026-03-06 ~ 2026-03-10 | Tool registration, task orchestration, file output, API integration | Partially completed (weather tool is a placeholder pending) | 60%      |
| Phase 4: Real Project Kickoff                | 2026-03-09 ~ 2026-03-13 | Receive project plan, set up environment, deliver first prototype   | Not started (pending supervisor's project plan)             | 0%       |

> Note: This week completed the foundational build-out from "single-capability verification" to "multi-capability coverage". Next week's focus shifts from "making it work" to "making it evaluable, reproducible, and demonstrable".
