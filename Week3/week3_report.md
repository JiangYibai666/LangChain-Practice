# Week 3 Report (2026-03-13 to 2026-03-19)

## 1. Achieved milestones

1. Completed production-grade RAG pipeline in `Week3/SKP_New.py` through code review and functional testing:
   - `--task ingest`: CSV loading, text chunking, embedding, ChromaDB persistence;
   - `--task ask`: retrieval-augmented QA via `get_retriever`, returns `answer/sources/latency_s`;
   - `--task chat`: interactive QA loop with `exit/quit/q` support.
2. Merged `Doc_Retrieval.py` robustness features into `SKP_New.py`:
   - added `resolve_csv_path` (path resolution supports `./`, `../`, `../Week3`);
   - added `get_embeddings_with_fallback` (GoogleGenerativeAIEmbeddings -> FakeEmbeddings fallback);
   - `ask_once` now logs status `Retrieved X documents`;
   - introduced `GoogleGenerativeAIError`, handles `RESOURCE_EXHAUSTED` in embedding/indexing stage with auto downgrade.
3. Updated `README.md` and `read_new.md` SKP_New sections, clarifying new coverage and expected behavior.
4. Code validation passed: `python3 -m py_compile SKP_New.py` succeeded, and logic tested under local standard paths.

## 2. Unfinished milestones

1. pytest suite not yet implemented (to be completed next week).
2. `Doc_Retrieval.py` migration of `stable_id` and `sources` schema not complete (non-critical, to synchronize later).

Reason: this week focused on capability delivery and quality hardening; testing split planned for week 4.

## 3. Plan and workload adjustment

1. 2026-03-17: the Week2 “multi-model comparison and capability validation” direction was shifted to Week 3, focusing on the full SKP_New pipeline; in practice work concentrated on `ingest/retrieval/chat` with fault-tolerance scenarios.
2. 2026-03-19: added `Doc_Retrieval` FakeEmbeddings fallback to lower model-key quota risk and improve reproducibility.

## 4. Forecasted risks and mitigation

1. Gemini API quota constraints
   - mitigation: `SKP_New.py` auto-fallback to FakeEmbeddings to keep integration testing runnable.
2. multi-path CSV resolution issues
   - mitigation: `resolve_csv_path` evaluates candidates and throws clear errors.
3. dependency drift
   - mitigation: recommend creating `requirements.txt`, pinning test dependencies, staying aligned with Week2 plan.

---

# Week 4 Plan (2026-03-20 to 2026-03-26)

## Goal stage

- The 16th week (April) enters the “Test & Go-live” phase. Core goals align with `plan.md` month 4 deliverables: UAT, performance/load testing, training, and staged production rollout.

## 1. Key activities (aligned with plan.md)

- User acceptance testing (UAT): execute with 2-3 pilot customers, collect feedback, complete signed UAT report.
- Performance and load testing: run online simulation, identify bottlenecks, apply tuning, deliver performance test report.
- Sprint-3 feature completion verification:
  - Delivery order agent and goods receipt agent (deliver version and test results);
  - Spend analysis agent and cash flow forecast agent (deliver evaluation reports).
- Security and compliance: conduct penetration testing and track remediation.
- Pre-release deployment and smoke test: validate pre-release environment availability and CI/CD pipeline acceptance.
- Training delivery: create materials, operation manuals, and demo videos for internal team, customer support, and pilot customers.
- Production staged rollout: pilot first, followed by broader release, complete post-launch monitoring and alert configuration.

## 2. Deliverables

- Signed UAT report and customer feedback log
- Performance test report and optimization record
- Sprint-3 agent acceptance checklist
- Penetration test report and remediation tracking
- Training materials and go-live handbook
- Production launch report and monitoring/on-call runbook

## 3. Expected outcomes

1. Verify end-to-end availability and stability, meeting “production-ready” commitments.
2. Surface and remediate risks (performance/security/accuracy) early to ensure stable production.
3. Validate in real business scenarios to increase customer confidence and delivery trust.

---

## Notes

This report has been aligned to `plan.md` month 4 and reconciled with Week2/Week3 actual progress for project review and evaluation.
