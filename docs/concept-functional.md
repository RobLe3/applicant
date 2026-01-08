# Applicant - Functional Description
Release: v0.5 beta (maturity score: 6.4/10)

## Functional Requirements
- Source ingestion from `Sources/` plus optional web profile URLs.
- Source inventory report listing filename, type, and extraction status.
- Profile extraction into normalized JSON with evidence per field.
- Skill weighting tiers (major/median/minor) with committee review for questionable artifacts.
- Role abstractions (capabilities and traits) derived from weighted skills for job language alignment.
- Role intent classification to distinguish leadership/architecture/consulting targets from execution-only roles.
- Separate capability depth signals from role target fit in scoring diagnostics.
- Job ingestion from a local CSV/JSON list and ATS adapters (Greenhouse, Lever, Ashby).
- Optional job page crawling via JSON-LD (`job_pages`) for company career pages.
- Job collection summary output for validation of ingestion and filters.
- Language detection for job postings and drafts (en, de).
- Multi-factor match scoring with explainable sub-scores.
- Role intent adjustments that boost strategy/architecture roles and downrank execution-heavy roles when misaligned.
- Qualification coverage with requirement-to-evidence mapping and gap list.
- Job analysis uses the same skill extraction/weighting/abstraction logic for objective alignment metrics.
- Committee votes stored in `committee_votes.json` and applied on the next run.
- Draft generation for cover letter, email body, and attachment list.
- Review queue that blocks any automatic send, plus a local web UI for voting.
- Submission agent that creates `.eml` drafts or form-assist summaries behind a checklist.
- Outcome feedback capture for accepted/rejected/interview/no_response (opt-in scoring).
- Export artifacts in JSON, DOCX, and PDF for easy edits.
- Store decisions in a local SQLite DB with a JSON export.
- Store job state snapshots (score, recommendation) in SQLite when DB is enabled.
- Generate job suggestions and skill assessment summaries for review.
- Out-of-scope flags when execution-heavy roles are downranked due to role intent.

## User Workflow
1. Place documents into `Sources/` and set web profile URLs in config.
2. Run `extract_profile` to build `rob_profile.json` (or start the review UI which auto-runs if outputs are missing).
3. Add job postings to `data/jobs` or run `crawl_jobs` adapters.
4. Run `match_score` to create `matched_jobs.json`.
5. Run `generate_app` to create drafts in `data/output/applications`.
6. Review, vote, and edit drafts before any external use.
7. Optionally generate `.eml` drafts or form-assist output; record outcomes later.

## Interfaces
- CLI entry points per task: `python modules/<task>.py`.
- Optional orchestrator: `python -m applicant pipeline`.
- Config file: `config/applicant.yaml` (paths, regions, scoring weights).
- Review UI: `python scripts/serve_web.py`.
- Review UI default port: `http://localhost:9000`.

## Logging and Errors
- Log each step to `data/logs/<task>.log`.
- Fail fast on missing required inputs; continue on non-critical parsing errors.
- Output a summary report with counts and warnings.

## Security and Privacy
- Keep all data local by default.
- Never upload artifacts or drafts without explicit user action.
- Redact PII in logs where possible.

## Acceptance Tests
- Can run pipeline end-to-end on local data without network.
- Produces deterministic output for the same inputs and config.
- Drafts exist for top-N matches and are editable.
- Submission drafts remain local and require explicit checklist approval.
