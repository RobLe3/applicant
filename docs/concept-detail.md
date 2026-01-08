# Applicant - Detailed Concept v2.0
Release: v0.5 beta (maturity score: 6.4/10)

## Repository Layout (Current)
```
config/
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

## Source Inventory
- On run, create `data/output/source_inventory.json` with file name, type, and extraction status.
- Source text is stored under `data/output/source_texts/` for traceability.
- Web profile URLs are fetched with allowlisted domains and stored locally.

## Profile Schema (rob_profile.json)
```
identity, hard_skills, soft_skills, experience, projects, education,
skill_weighting, role_abstractions, capability_baseline,
role_intent, role_intent_signals, evidence, source_files
```

## Job Schema (latest_jobs.json)
```
id, title, company, location, language, description, description_raw,
sanitization_notes, source, url, contact_email
```

## Match Output (matched_jobs.json)
```
id, score, score_raw, score_preset, score_intent_adjusted, score_adjusted,
score_preset_adjustment, score_intent_adjustment,
score_feedback_adjustment, score_adjustment,
adjusted_by, adjusted_by_parts, preset_name,
score_breakdown { skills, title, experience, language, location, alignment,
capability_depth, role_target_match },
qualification { coverage, requirements[], gaps[] },
job_analysis { skill_weighting, role_abstractions, committee_review },
alignment { skills, capabilities, traits, alignment_score },
job_facts { location, workplace, employment_type, compensation, work_mode, contract_type, seniority, benefits },
intent { role_intent, job_track, job_intent_tags, intent_alignment, intent_bonus, intent_penalty, intent_adjustment, out_of_scope },
feedback_applied, feedback_tags,
cluster_id, cluster_size,
job
```

`job_facts` enrichment:
- `work_mode`: remote | hybrid | on_site
- `contract_type`: full_time | part_time | contract | freelance | internship | temporary
- `seniority`: junior | mid | senior | lead | principal | director | vp | c_level
- `benefits`: list of normalized benefit tags

## Derived Filters Output (derived_job_filters.json)
```
derived { include_keywords, location_allow, location_block },
merged { include_keywords, exclude_keywords, location_allow, location_block }
```

## Job Collection Summary (job_collection_summary.json)
```
raw_total, manual_total, ats_total, job_page_total, normalized_total,
filtered_out, truncated, derived_filters, generated_at
```

## Skill Assessment Summary (skill_assessment.json)
```
total_jobs, avg_score, avg_coverage, requirements,
recommendations, top_gaps, skill_weighting, role_abstractions
```

## Committee Votes (committee_votes.json)
```
profile { skills, abstractions, emails },
jobs { job_id: { skills, abstractions } }
```

## Draft Output (applications/)
- One JSON per job with `body_draft`, `attachments`, and `review_required: true`.
- Exported files: `application_x.docx` and `application_x.pdf`.
- Drafts only proceed for jobs marked `approve` in review votes.

## Feedback Output (feedback.json)
- Local outcome history used for optional score adjustments.
- Each entry stores `job_id`, `outcome`, `tags`, `note`, and `recorded_at`.

## Extraction Details
- PDF: `pypdf` with `pdftotext` fallback.
- DOCX: unzip XML and strip tags.
- Normalize skills and titles; dedupe by canonical keys.
- Committee voting flags low-confidence artifacts.

## Matching Algorithm
- Build a profile text block from skills and experience summaries.
- Jaccard similarity for baseline overlap.
- Score is a weighted sum from `config/applicant.yaml`.
- Preset weights override base weights for alternate scoring profiles.
- Role intent alignment applies explainable bonuses/penalties, keeping engineering execution roles out-of-scope unless explicitly targeted.
- Feedback adds optional tag/company adjustments with audit labels.
- Map prerequisites to evidence and compute coverage + gaps.
- Extract job skills and abstractions using the same profile logic.
- Compute alignment metrics over accepted skills and abstractions.
- Extract job facts (location, workplace, employment type, compensation).
- Cluster similar jobs using semantic similarity thresholds.

## Review UI + Decisions
- Local UI at `http://localhost:9000`.
- Supports filtering, grouping, holding queue, and alignment buckets.
- Shows prerequisites, matches, and full posting text.
- Votes stored in SQLite or `data/output/review_votes.json`.

## Detailed-Level Additions Needed (Post v0.5)
**Job ingestion and coverage**
- Add adapters for additional ATS sources (e.g., Workable, BambooHR) and a generic HTML parser.
- Improve requirement extraction so coverage is not frequently 0.00 (better parsing and evidence matching).

**Scoring and feedback**
- Add more granular feedback tags and decay over time.
- Add committee-style review for edge-case scoring and intent calibration per role family.

**Application generation**
- Expand prompt templates (more languages, role variants, and tailored variants).
- Support richer outputs (tailored resumes and questionnaire answers).

**UI and UX polish**
- Improve keyboard navigation, search/filter ergonomics, and preview quality.
- Persist user UI preferences (e.g., dark mode, filters).
- Add visual dashboards (fit distribution, pipeline funnel).

**Setup and maintainability**
- Add `requirements.txt`, sample `config/applicant.yaml`, and LICENSE.
- Expand unit/integration coverage for regex, embeddings, and end-to-end pipeline.
- Add containerization for onboarding (Docker).

**Reliability and edge cases**
- Harden exception handling and sanitization.
- Rate limit crawl requests and improve offline model management.

## Post-MVP Architecture Extensions (Phases 5-8)
**Reliability + Testing**
- Golden output regression suite for the full pipeline.
- UI snapshot coverage for filters and grouping states.
- Audit validation for sanitization and submission logs.

**Intelligence + Personalization**
- Scoring presets that capture different personal priorities.
- Outcome-aware adjustments using feedback tags with rollback history.
- Clustering and diagnostics to explain rank changes.

**Integrations + Deployment**
- Pluggable ATS adapters with explicit config ownership.
- Optional local scheduler to run the pipeline on a cadence.
- Opt-in, export-based sync mode (no automatic sharing).

**UX + Presentation**
- Score distribution dashboards and alignment cohort views.
- Application package preview panels and diffable drafts.

## Configuration Layers (Post-MVP)
- `scoring.presets`: named scoring presets for weight/threshold sets.
- `matching.similarity`: clustering thresholds and enablement.
- `adapters`: adapter registry with per-source configs.
- `testing.snapshots`: UI snapshot config and golden output paths.
- `submission.smtp`: explicit SMTP opt-in and connection settings.
- `sync.export`: export/import definitions for optional sync.

## V2.0 Milestones and What Is Needed
1. Review-time region and language filters
   - Status: Implemented in review UI.
   - Need: None (available in filters).
2. Semantic matching via embeddings
   - Status: Implemented with offline hash backend and optional local model.
   - Need: Optional model tuning and rank evaluation.
3. Job metadata enrichment
   - Status: Implemented (seniority, benefits, contract type, work mode).
   - Need: Optional additional benefit parsing.
4. Review intelligence upgrades
   - Status: Partial (alignment buckets, holding queue).
   - Need: quorum rules and score distribution analytics.
5. Application export quality
   - Status: Implemented (DOCX/PDF export pipeline).
   - Need: Optional render checks.
6. Submission and feedback loop
   - Now: submission agent, response tracking, feedback weighting (opt-in).
7. Prompt safety layer
   - Status: Implemented (content sanitization with raw preservation).
   - Need: Optional policy checks.
8. Tests and fixtures
   - Status: Implemented (deterministic fixtures and smoke tests).
   - Need: Optional UI regression coverage.

## Optional Future Extensions
- Vector store or graph DB for semantic search and reasoning.
- Additional ATS adapters and job page scrapers.
- Multi-language templates beyond EN/DE.

## Phase 7 Integrations (Implemented)
- Adapter registry under `modules/adapters/` for local file ingestion.
- Scheduler wrapper scripts for cron/launchd (opt-in).
- Portable initialization + migration tooling.
- Export/import for offline archiving with hash manifests.

## Testing
- Unit tests for parsers and scoring.
- Golden file tests for profile extraction and draft output.
- Smoke test that runs the pipeline on a small fixture set.
  db/
    applicant.db
    applicant_dev.db
