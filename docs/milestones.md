# Applicant MVP Milestones and Definition of Done
Release: v0.5 beta (maturity score: 6.4/10)

This document is the development logbook and milestone tracker. It records what has been implemented, what is in progress, and the definition of done for each milestone.

## Status Legend
- Completed: implemented and validated locally.
- Implemented: coded and integrated; may need validation.
- Planned: agreed but not started.
- Not started: queued and unimplemented.

## Milestone v0.5 beta: Applicant v0.5 beta - Usable Review-Driven Job Discovery
- Status: Completed
- Definition of done:
  - End-to-end pipeline works (crawl -> score -> review -> vote).
  - Phase 10 role-intent calibration is active and verified.
  - Sources beyond ATS (RSS/manual) are visible and reviewable.
  - Review UI is readable, navigable, and vote-stable.
  - Out-of-scope roles are no longer promoted as "apply".
- Maturity assessment: beta (6.4/10).
- Version rubric: see `docs/project-documentation.md` (Version and Maturity Assessment).
- Not included:
  - Comprehensive job-market coverage.
  - Auto-apply or auto-submit.
  - Recall optimization.
- Evidence:
  - `docs/project-documentation.md`
  - `logs/ui_usability_fixes.md`
  - `logs/usability_fix_report.md`

## Milestone 0: MVP Baseline
- Status: Completed
- Definition of done:
  - End-to-end pipeline runs locally without network.
  - Profile extraction, crawl, scoring, and draft generation produce outputs.
  - Review gate enforced for all drafts.
- Evidence:
  - `modules/pipeline.py`
  - `scripts/run_pipeline.py`
  - `modules/generate_app.py` (forces `review_required: true`)

## Milestone 1: Profile Extraction + Evidence
- Status: Completed
- Definition of done:
  - Source inventory created for all inputs.
  - Structured profile written with evidence and weighting.
  - Committee review queue created for held items.
- Evidence:
  - `modules/extract_profile.py`
  - `utils/parser.py`
  - `data/output/source_inventory.json`

## Milestone 2: Job Ingestion + Filters
- Status: Implemented
- Definition of done:
  - ATS + manual job ingestion normalized into `latest_jobs.json`.
  - Profile-derived filters merged with configured filters.
  - Collection summary includes derived filter counts.
- Evidence:
  - `modules/crawl_jobs.py`
  - `data/jobs/latest_jobs.json`
  - `data/output/derived_job_filters.json`
  - `data/output/job_collection_summary.json`

## Milestone 3: Match Scoring + Alignment
- Status: Implemented
- Definition of done:
  - Fit score and alignment computed for each job.
  - Prerequisites mapped to evidence with coverage + gaps.
  - Job facts extracted (location/workplace/employment/compensation).
- Evidence:
  - `modules/match_score.py`
  - `data/output/matched_jobs.json`
  - `data/output/skill_assessment.json`

## Milestone 4: Review UI + Voting
- Status: Implemented
- Definition of done:
  - Local review UI shows scored jobs and alignment details.
  - Holding queue for not-voted jobs.
  - Votes persisted to SQLite or JSON.
  - Grouping by vote and alignment buckets.
  - Alignment focus filter defaults to 0.90+.
- Evidence:
  - `web/index.html`
  - `web/app.js`
  - `scripts/serve_web.py`

## Milestone 5: Draft Generation (Review-Gated)
- Status: Implemented
- Definition of done:
  - Draft packages created only for approved jobs.
  - `review_required: true` enforced on all packages.
- Evidence:
  - `modules/generate_app.py`
  - `data/output/applications/`

## Milestone 6: Documentation
- Status: Implemented
- Definition of done:
  - Architecture and full system documentation created.
  - v2.0 concept updates captured in docs.
- Evidence:
  - `docs/project-documentation.md`
  - `docs/concept-high-level.md`
  - `docs/concept-detail.md`
  - `README.md`

## Milestone 7: Review-Time Region/Language Filters
- Status: Implemented
- Definition of done:
  - Review UI exposes region/language filters.
  - Filters apply without re-crawl.
  - Filters persisted in config or UI state.
- Evidence:
  - `web/index.html`
  - `web/app.js`
  - `scripts/serve_web.py`

## Milestone 8: Semantic Matching (Embeddings)
- Status: Implemented
- Definition of done:
  - Embedding-based similarity added with fallback to token overlap.
  - Offline-friendly option or cached embeddings.
  - Evaluation fixtures to validate ranking changes.
- Evidence:
  - `utils/vectorizer.py`
  - `modules/match_score.py`
  - `scripts/compare_rankings.py`

## Milestone 9: Job Metadata Enrichment (Depth)
- Status: Implemented
- Definition of done:
  - Seniority, benefits, and contract level extracted and normalized.
  - Stored in `matched_jobs.json` as `job_facts` for review UI use.
- Evidence:
  - `modules/match_score.py`

## Milestone 10: Review Intelligence
- Status: Planned
- Definition of done:
  - Committee quorum rules enforce acceptance before use.
  - Score distribution and cohort analytics in UI.

## Milestone 11: Application Export (DOCX/PDF)
- Status: Implemented
- Definition of done:
  - Drafts export to DOCX/PDF with formatting templates.
  - Export validation ensures required sections present.
- Evidence:
  - `utils/exporter.py`
  - `modules/generate_app.py`
  - `prompts/cover_letter_en.txt`
  - `prompts/cover_letter_de.txt`

## Milestone 12: Submission + Feedback Loop
- Status: Implemented
- Definition of done:
  - Submission agent (manual or automated) added behind explicit approvals.
  - Outcome tracking stored locally.
  - Feedback adjusts matching weights or filters.
  - Submission logs recorded for audit.
- Evidence:
  - `modules/submission_agent.py`
  - `utils/feedback.py`
  - `scripts/serve_web.py`
  - `web/app.js`

## Milestone 13: Prompt Safety Layer
- Status: Implemented
- Definition of done:
  - External job text sanitized for prompt injection.
  - Safety checks applied before any LLM or templating step.
- Evidence:
  - `modules/crawl_jobs.py`

## Milestone 14: Tests and Fixtures
- Status: Implemented
- Definition of done:
  - Deterministic fixtures for extraction and scoring.
  - Offline smoke tests for pipeline outputs.
- Evidence:
  - `scripts/run_smoke_tests.py`
  - `tests/fixtures/`

## Milestone 15 (Phase 5): Reliability + Testing Expansion
- Status: Planned
- Definition of done:
  - Golden output regression suite covers extract/crawl/score/generate.
  - UI snapshot tests cover filters, grouping, and holding queue.
  - Sanitization and submission audit logs validated for completeness.

## Milestone 16 (Phase 6): Intelligence + Personalization
- Status: Planned
- Definition of done:
  - Scoring presets configurable and selectable per session.
  - Outcome-aware adjustments are reversible and traceable.
  - Ranking diagnostics explain deltas across models/presets.

## Milestone 17 (Phase 7): Integrations + Deployment
- Status: Implemented
- Definition of done:
  - Pluggable ATS adapter registry with config validation.
  - Local scheduler runs the pipeline without network dependencies.
  - Optional export-based sync mode remains review-gated and opt-in.
  - Portable initialization and migration tooling available.

## Milestone 18 (Phase 8): UX + Presentation
- Status: Planned
- Definition of done:
  - Score distribution dashboards and cohort views in UI.
  - Application preview panel (docx/pdf + diff) available for approved jobs.
  - Review flow supports keyboard shortcuts and sequential navigation.
