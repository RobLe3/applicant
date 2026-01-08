# Applicant MVP Project Documentation
Release: v0.5 beta (maturity score: 6.4/10)

## 1) Architecture Overview
Applicant MVP is an offline-first, local pipeline that converts personal artifacts into a structured profile, uses that profile to scope and score job opportunities, and produces review-ready application packages. The system is designed around explicit inputs and outputs with a strict human review gate, and it treats job postings and documents as untrusted input.

### 1.1 System Components
- **Sources + Web Profile Intake**: Local documents from `Sources/` and optional web profile URLs (domain-restricted).
- **Profile Extraction**: Converts sources into `rob_profile.json` with evidence, skills, weighting, and role abstractions.
- **Crawl + Normalize Jobs**: Ingests job data from local files, ATS providers, and optional JSON-LD job pages, then filters by profile-derived and configured criteria.
- **Match + Score**: Computes fit score and alignment metrics, plus prerequisite mapping to evidence.
- **Review UI**: Local-only web UI to browse, filter, and vote on jobs.
- **Draft Generation**: Generates review-required application packages only for approved jobs.
- **Submission Agent**: Generates local email drafts or form-assist summaries after explicit approval.
- **Feedback Tracking**: Records outcomes and optionally adjusts future scoring (opt-in per session).
- **Storage**: JSON outputs in `data/output/`, optional SQLite state in `db/`.

### 1.2 End-to-End Data Flow
1. `extract_profile` reads sources and web profile, builds `rob_profile.json`.
2. `crawl_jobs` derives filters from the profile, merges with config filters, crawls jobs, and writes `latest_jobs.json`.
3. `match_score` extracts job skills and prerequisites, computes alignment and scores against the profile, writes `matched_jobs.json` and summaries.
4. `generate_app` drafts application packages only for approved jobs; all packages are `review_required: true`.
5. `submission_agent` creates `.eml` drafts or form-assist output after checklist approval (no auto-send by default).
6. `feedback` records application outcomes for optional score adjustment.
7. `serve_web` exposes the review UI and APIs; it auto-runs the pipeline if required outputs are missing.

### 1.3 Review Gate and Safety
- **Never auto-send**: Drafts are local and always `review_required: true`.
- **Committee review**: Ambiguous skills/abstractions are held for human approval before they affect scoring.
- **Untrusted input**: Job postings and documents are treated as data only, not instructions.

## Milestone: Applicant v0.5 beta - Usable Review-Driven Job Discovery
This milestone means:
- End-to-end pipeline works (crawl -> score -> review -> vote).
- Phase 10 role-intent calibration is active and verified.
- Sources beyond ATS (RSS/manual) are visible and reviewable.
- Review UI is readable, navigable, and vote-stable.
- Out-of-scope roles are no longer promoted as "apply".
Maturity assessment: beta (6.4/10). Stable for daily review, but coverage and requirement extraction remain limited.

This milestone is not:
- A finished job-market coverage solution.
- Auto-apply or auto-submit.
- Optimized for recall yet.

Note: Phase 10 role-intent logic was not changed; these updates are wiring and usability corrections.

### Version and Maturity Assessment
Derived version: `v0.5 beta` (score 6.4/10).

Scoring rubric (max 10):
- Core pipeline + review gate: 2.0/2.0
- UI usability + vote stability: 1.2/2.0
- Discovery breadth (ATS + RSS + manual): 0.8/2.0
- Scoring quality + intent alignment: 1.3/2.0
- Testing + diagnostics + export gating: 1.1/2.0

Mapping:
- 0.1-0.2: prototype
- 0.3-0.4: alpha
- 0.5-0.6: beta
- 0.7-0.8: release candidate
- 0.9-1.0: stable

## Discovery Sources
Applicant ingests and normalizes jobs from multiple local-first sources:
- **ATS boards** (e.g., Greenhouse/Lever/Ashby via configured boards)
- **RSS feeds** (configured under adapters)
- **Manual sources** (local JSON files in `data/jobs/`)
- **Job pages** (optional JSON-LD parsing)

All enabled sources appear in the Crawl tab under "Sources / Companies" with `source_id`, `source_type`, and a per-source count from the last run. Each job also carries an optional `source_intent` label to describe high-level intent (e.g., consulting, public sector).

## Recommendation Semantics
Recommendations are separate from scoring and alignment:
- **score**: aggregate fit score used for ranking.
- **alignment**: profile-to-job capability/trait fit (from abstractions).
- **recommendation**: advisory label (`apply`, `consider`, `skip`) based on thresholds.

A recommendation guard caps obvious sales/GTM titles at `consider` and adds a `recommendation_reason` (e.g., `role_family_out_of_scope:sales`). This does not change scoring. Phase 10 role-intent calibration remains unchanged.

## Review UI Behavior
- **Expand/collapse descriptions**: job cards show a short preview by default, with a per-job toggle.
- **Deterministic job_id**: job IDs are stable across runs and used for vote persistence.
- **Votes**: Approve/Hold/Reject are stored locally and reflected in grouping buckets immediately.

## How to Use Applicant (Daily Workflow)
1. Configure sources
   - Enable ATS, RSS, and/or manual sources in `config/applicant.yaml`.
   - Verify in the Crawl tab that all sources are visible with counts.
2. Run a crawl
   - "Run Job Crawl" pulls sources, normalizes jobs, and updates `latest_jobs.json`.
   - "Refresh Scores" re-runs scoring without re-crawling.
3. Review jobs
   - Use score for ranking, alignment for capability fit, and recommendation as advisory.
   - Expand/collapse descriptions for deeper reading.
   - Out-of-scope roles show a recommendation reason badge.
4. Vote
   - Approve/hold/reject a job; votes persist by `job_id`.
   - Feedback can influence future ranking only when enabled.
5. Apply (optional, gated)
   - "Apply" generates drafts only for approved jobs.
   - Submission is disabled by default and requires explicit checklist approval.

## 2) Repository Layout
```
config/
  applicant.yaml
data/
  jobs/
  output/
  logs/
db/
docs/
modules/
prompts/
scripts/
Sources/
utils/
web/
```

## 3) Configuration (config/applicant.yaml)
Configuration is the single source of truth for paths, matching weights, crawl sources, filters, and review/drafting behavior.

Key sections:
- `paths`: `sources_dir`, `jobs_dir`, `output_dir`, `prompts_dir`, `logs_dir`
- `profile`: profile identity and committee thresholds
- `web_profile`: allowed domains, follow patterns, and max pages
- `language`: default and supported languages (`en`, `de`)
- `meta`: version and maturity metadata
- `matching`: weighted scoring inputs, thresholds, region keywords
- `matching.semantic`: semantic similarity settings (backend, model path, cache path)
- `matching.similarity`: clustering threshold for similar jobs
- `matching.feedback`: opt-in feedback weighting configuration (path, tag/company weight, min_samples)
- `scoring`: scoring presets and active preset selection
- `job_sources`: manual files, ATS providers, job pages, limits, timeouts
- `adapters`: local adapter registry for pluggable ingestion
- `job_filters`: include/exclude keywords, location allow/block, derived filters
- `review`: vote gating for drafts
- `drafting`: review requirement, attachments, and `letter_date` for deterministic exports
- `submission`: submission enablement and SMTP settings
- `schedule`: local scheduler configuration
- `db`: SQLite toggle and paths
- `skills_seed`: seed skills for extraction

Defaults live in `utils/io.py` and are used if `config/applicant.yaml` is missing.

## 4) Core Pipeline (modules/)

### 4.1 `modules/pipeline.py`
Orchestrates the full flow:
1. `extract_profile`
2. `crawl_jobs`
3. `match_score`
4. `generate_app`

Entry points:
- `python scripts/run_pipeline.py`
- `python modules/pipeline.py`

### 4.2 `modules/extract_profile.py`
Purpose: Build a structured profile from local sources and web profile text.

Key responsibilities:
- Inventory all documents in `Sources/` and write `data/output/source_inventory.json`.
- Extract text from PDF/DOCX/TXT using `utils.parser`.
- Optionally fetch and parse a web profile using `utils.web` with domain allowlists.
- Extract skills, experience, education, projects, and evidence snippets.
- Compute skill weighting tiers and role abstractions.
- Queue low-confidence items for committee review.

Main outputs:
- `data/output/rob_profile.json`
- `data/output/profile_comparison.json`
- `data/output/committee_review.json`
- `data/output/source_inventory.json`
- `data/output/source_texts/` (text dumps of sources and web profile)

### 4.3 `modules/crawl_jobs.py`
Purpose: Ingest jobs and filter them using explicit and profile-derived filters.

Job sources:
- Manual JSON files in `data/jobs/` (excluding `latest_jobs.json`)
- ATS APIs: Greenhouse, Lever, Ashby
- Optional JSON-LD job pages (company career pages)
- Adapter registry under `modules/adapters/` (local file ingestion)

Filtering logic:
- Keyword include/exclude lists (`job_filters`)
- Location allow/block lists (location text or description)
- Derived filters from the profile (accepted skills, role abstractions, location hints)

Main outputs:
- `data/jobs/latest_jobs.json`
- `data/output/job_collection_summary.json`
- `data/output/derived_job_filters.json`

### 4.4 `modules/match_score.py`
Purpose: Compare jobs against the profile and compute fit and alignment.

Scoring signals:
- Semantic similarity with embedding backend (hash or local SBERT), fallback to token overlap
- Title and experience similarity
- Language match (supported languages)
- Location keyword match
- Alignment score from weighted skills + role abstractions
- Optional feedback adjustment from outcome history (opt-in)
- Preset-based weights and thresholds (runtime selection)

Clustering:
- Similar jobs are grouped with a `cluster_id` and `cluster_size` when similarity is enabled.

Additional analysis:
- Extract job skills/abstractions using the same logic as the profile.
- Extract job prerequisites and map them to evidence items for coverage + gaps.
- Extract job facts (location, workplace, employment type, compensation).

Main outputs:
- `data/output/matched_jobs.json`
- `data/output/job_suggestions.json`
- `data/output/skill_assessment.json`
- `data/output/job_committee_review.json` (if job committee holds exist)

### 4.5 `modules/generate_app.py`
Purpose: Generate draft application packages (cover letter + metadata).

Rules:
- Only jobs with `approve` votes are eligible.
- Drafts always include `review_required: true`.
- Prompts come from `prompts/` as plain text.
- Exports DOCX/PDF drafts using local templates.

Main outputs:
- `data/output/applications/application_*.json`
- `data/output/applications/application_*.docx`
- `data/output/applications/application_*.pdf`
- `data/output/applications/application_*.eml` (when draft email is created)

### 4.6 `modules/submission_agent.py`
Purpose: Create email drafts, optional SMTP sends, and form-assist output.

Rules:
- Requires an explicit checklist before any submission action.
- Defaults to draft creation; SMTP sending is opt-in and requires local relay.
- Logs every action to `data/logs/submissions/`.

## 5) Utilities (utils/)

### 5.1 `utils/io.py`
- Config loading from YAML/JSON, with defaults.
- JSON read/write helpers.
- Log helper that writes `data/logs/<task>.log`.

### 5.2 `utils/parser.py`
- PDF text extraction via `pypdf` or `pdftotext`.
- DOCX parsing via XML extraction.
- Text file loading.
- Source inventory generation.

### 5.3 `utils/vectorizer.py`
- Lightweight tokenization and Jaccard similarity for scoring.
- Semantic embedding helper with hash backend and optional local model path.

### 5.4 `utils/translator.py`
- Simple language detection (English vs. German) using token hints.

### 5.5 `utils/web.py`
- Domain-allowlisted web fetching.
- HTML to text conversion.
- Link extraction for follow-up crawling.

### 5.6 `utils/db.py`
- SQLite storage for votes and job states.
- Tables: `decisions`, `job_states`.

### 5.7 `utils/exporter.py`
- Deterministic DOCX/PDF export for application drafts.
- Template rendering for cover letters.

### 5.8 `utils/feedback.py`
- Loads/saves feedback history and computes tag statistics.
- Builds feedback tags for score adjustment.

### 5.9 `utils/sanitizer.py`
- Shared sanitization helpers for untrusted text.

### 5.10 `utils/io.py` (export/import)
- `export_data` for offline archival with hash manifest.
- `import_data` with confirmation gates.

## 6) Scripts (scripts/)

### 6.1 `scripts/run_pipeline.py`
Runs the full pipeline end-to-end using `modules/pipeline.py`.

### 6.2 `scripts/serve_web.py`
Local review UI and API server (`http://localhost:9000`).

Endpoints:
- `GET /api/matches`: scored jobs + votes
- `GET /api/insights`: suggestions, assessments, collection, derived filters
- `GET /api/profile`: profile + config + derived filters
- `GET /api/committee`: committee review queues + votes
- `GET /api/applications`: application drafts + submission settings
- `POST /api/crawl`: crawl jobs
- `POST /api/score`: re-run scoring (optional feedback override)
- `POST /api/vote`: save review vote
- `POST /api/committee`: save committee decision
- `POST /api/submit`: create a draft, send via SMTP, or form-assist (checklist gated)
- `POST /api/feedback`: record application outcome

Auto-pipeline behavior:
- If required outputs are missing (including `derived_job_filters.json`), it runs the pipeline automatically.

### 6.3 `scripts/diagnose_rankings.py`
Generates ranking delta reports across raw, preset, and feedback scoring modes.

### 6.4 `scripts/schedule_runner.py`
Generates local scheduler entries for cron/launchd.

### 6.5 `scripts/portable_init.py`
Bootstraps a portable data layout and optional migration.

## 7) Review UI (web/)

### 7.1 `web/index.html`
Static layout for:
- Review tab (job cards, insights, holding queue)
- Profile tab (profile summary and committee review)
- Crawl tab (sources, filters, crawl summary)

### 7.2 `web/app.js`
Client logic for:
- Fetching matches, insights, profile data, and committee queues
- Filters (search, recommendation, region, language, alignment focus, vote)
- Grouping (by vote or alignment buckets)
- Holding queue for not-voted jobs
- Job cards showing score, prerequisites, alignment, facts, and full posting text
- Score distribution panel (raw/preset/adjusted views)
- Role-family template selection per job (saved to `template_overrides.json`)
- Application preview panel (DOCX text with previous-draft comparison)
- Focus review mode with keyboard shortcuts for sequential voting
- Voting and committee decisions
- Submission drafts, form-assist output, and feedback outcomes (checklist gated)

### 7.3 `web/styles.css`
Visual styling for panels, cards, badges, and review controls.

## 8) Data Outputs and Schemas

### 8.1 `data/output/rob_profile.json`
Profile fields (excerpt):
```
identity, hard_skills, soft_skills, experience, projects, education,
skill_weighting, role_abstractions, evidence, source_files
```

### 8.2 `data/jobs/latest_jobs.json`
Normalized job fields:
```
id, title, company, location, language, description, description_raw,
sanitization_notes, source, source_type, source_intent, external_id,
text_missing, url, contact_email
```

### 8.3 `data/output/matched_jobs.json`
Core job scoring output:
```
id, score, score_raw, score_preset, score_adjusted,
score_preset_adjustment, score_feedback_adjustment, score_adjustment,
adjusted_by, adjusted_by_parts, preset_name,
score_breakdown, qualification, job_analysis, alignment,
job_facts, feedback_applied, feedback_tags,
cluster_id, cluster_size, job
```

`job_facts` includes:
- `work_mode` (remote/hybrid/on_site)
- `contract_type` (full_time/part_time/contract/freelance/internship/temporary)

### 8.4 `data/output/template_overrides.json`
Per-job role-family template overrides for cover letters:
```
{ "12345": "engineering", "67890": "strategy" }
```
- `seniority` (junior/mid/senior/lead/principal/director/vp/c_level)
- `benefits` (health/pension/equity/bonus/relocation/visa/training/wellness/pto)

### 8.4 `data/output/derived_job_filters.json`
Derived filters from the profile:
```
{
  "derived": { "include_keywords": [], "location_allow": [], "location_block": [] },
  "merged": { "...": "combined filters used by crawl_jobs" }
}
```

### 8.5 `data/output/skill_assessment.json`
Aggregated scoring + profile alignment metrics across all jobs.

### 8.6 `data/output/review_votes.json`
Vote storage (approve/hold/reject) when DB is disabled.

### 8.7 `data/output/feedback.json`
Outcome history used for feedback-aware scoring (opt-in).

### 8.8 `data/logs/submissions/`
Audit logs for each submission action (draft, SMTP, or form-assist).

## 9) Prompts (prompts/)
Prompt templates are plain text and used by `generate_app`:
- `icar_umbrella.txt`
- `icar_cover_letter_detail.txt`
- `icar_reference_letter_detail.txt`
- `cover_letter_en.txt`
- `cover_letter_de.txt`

These are injected into `prompt_bundle` inside each draft so the entire context is preserved locally.

## 10) Database (db/)
SQLite schema (see `utils/db.py`):
```
decisions(job_id, vote, note, updated_at)
job_states(job_id, score, recommendation, updated_at)
```

## 11) Security and Privacy Guarantees
- Local-only by default; web access is optional and explicitly configured.
- Job postings and documents are treated as untrusted input.
- External job descriptions are sanitized before matching or drafting; raw text is preserved for traceability.
- No auto-send of drafts or emails; human review is mandatory.
- Submission actions require an explicit checklist and default to local email drafts.
- All outputs are written to local disk for auditability.

## 12) Extension Points
Common extension areas:
- New adapters in `modules/adapters/`.
- Alternative scoring strategies in `modules/match_score.py`.
- Additional fields in `job_facts` or prerequisite extraction.
- UI enhancements in `web/` for new filters or analytics.
- Additional prompt templates in `prompts/`.

## 13) Operational Notes
- Primary entry point: `python scripts/run_pipeline.py`.
- Review UI: `python scripts/serve_web.py`.
- Offline smoke tests: `python scripts/run_smoke_tests.py`.
- Ranking comparison (fixtures): `python scripts/compare_rankings.py`.
- Scheduler setup: `python scripts/schedule_runner.py` (dry-run by default).
- Portable setup: `python scripts/portable_init.py` (see `docs/portable.md`).
- Offline export/import: `utils.io.export_data` / `utils.io.import_data`.
- Output files are deterministic for the same inputs and config.
- Logs for each task live in `data/logs/`.
