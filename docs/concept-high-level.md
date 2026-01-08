# Applicant - High Level Concept v2.0
Release: v0.5 beta (maturity score: 6.4/10)

## Overview
Applicant is a modular, offline-first job application agent that extracts identity, maps opportunities, and builds tailored application packages under full user control. It converts local career artifacts into a structured profile, uses that profile to scope and score job opportunities, and produces review-only drafts.

## Purpose (Refined Objective)
Enable Rob to discover, assess, and apply to high-fit roles with minimal manual effort while preserving transparency, review control, and adaptability across languages and geographies.

## Core Design Principles (Updated)
| Principle | Description |
| --- | --- |
| Extracted identity | Qualifications, skills, and background are parsed once into a live profile. |
| Broad discovery, narrow review | Jobs are crawled broadly and filtered later in the review UI. |
| Semantic matching | Fit is based on meaning, not just keyword overlap; improves with feedback. |
| Review-gated autonomy | All applications are human reviewed; no auto-send. |
| Composable automation | Each module has explicit input and output paths. |
| Multi-language, multi-region | English and German supported; region focus is review-configurable. |
| Feedback awareness | Outcomes can refine matching and suggestions when enabled. |

## System Layers and Responsibilities
1. Identity inference: sources in, structured profile out (`rob_profile.json`).
2. Opportunity discovery: crawlers and APIs in, raw jobs out (`latest_jobs.json`).
3. Matching and enrichment: profile + jobs in, scored jobs out (`matched_jobs.json`).
4. Review and filtering: scored jobs in, approvals out (votes + review UI).
5. Application builder: approved jobs in, draft packages out (`applications/*.json`).
6. Submission and feedback: draft/send + outcomes in, learning signals out (opt-in).

## Key Architectural Shifts and Adaptations
| Topic | Adaptation |
| --- | --- |
| Region filtering | Shifted from crawl-time to review-time to allow broader discovery. |
| Matching | Embedding-based similarity added with offline hash backend; optional local SBERT path. |
| Job metadata parsing | Location/work mode plus seniority, contract type, and benefits extracted. |
| Application quality | Templates are modular; DOCX/PDF export implemented. |
| Submission control | Review-first; no auto-submit unless explicitly approved. |
| Feedback learning | Outcome tracking with opt-in score adjustments. |
| Safety | Prompt injection sanitization for external content is implemented. |

## Workflow Overview
1. `extract_profile.py` builds `rob_profile.json`.
2. `crawl_jobs.py` collects jobs using configured + derived filters.
3. `match_score.py` scores and aligns jobs vs profile.
4. Review UI filters, groups, and votes on roles.
5. `generate_app.py` creates review-required drafts for approved jobs.
6. `submission_agent.py` creates `.eml` drafts or form-assist summaries (checklist gated).
7. Feedback outcomes are stored locally and can optionally adjust scoring.

## V2.0 Milestones and Requirements
1. Broader discovery with review-time filters
   - Status: Implemented in UI flow.
   - Needed: None (available in review filters).
2. Semantic matching via embeddings
   - Status: Implemented (hash backend + optional local model).
   - Needed: Optional model tuning and ranking analysis.
3. Job metadata enrichment
   - Status: Implemented (seniority, contract type, benefits, work mode).
   - Needed: Optional enrichment for additional benefits.
4. Review intelligence upgrades
   - Status: Partial (alignment buckets, holding queue).
   - Needed: quorum rules, score distribution analytics.
5. Application export quality
   - Status: Implemented (DOCX/PDF exports).
   - Needed: Optional format validation.
6. Submission and feedback loop
   - Status: Implemented (drafts, form assist, feedback tracking).
   - Needed: Optional SMTP relay usage.
7. Prompt safety layer
   - Status: Implemented (sanitization + raw text preservation).
   - Needed: Optional policy checks.
8. Tests and fixtures
   - Status: Implemented (deterministic fixtures + smoke tests).
   - Needed: Optional UI regression tests.

## Post-MVP Expansion (Phases 5-8)
The next phases extend reliability, personalization, integration, and UX while preserving the review-gated, local-first model.

**New capabilities**
- Reliability: golden output regression suite, UI snapshots, audit validation for sanitization and submissions.
- Intelligence: scoring presets and outcome-aware adjustments with reversible history.
- Integrations: pluggable ATS adapters and an opt-in local scheduler.
- UX: score distribution dashboards and application preview tooling.

**System properties**
- Review-gated autonomy remains mandatory.
- Local-first data control; optional cloud sync is opt-in and export-based.

## High-Level Additions Needed (Post v0.5)
- Broader discovery and intelligence: expand beyond ATS/RSS/manual with opt-in, ToS-compliant aggregation and semantic search across career sites; add proactive opportunity signals (e.g., funding/news monitoring for unposted roles).
- Advanced matching and personalization: deeper feedback loops, role trajectory modeling, and company/culture alignment inference.
- Multi-device support: optional encrypted sync or self-hosted relay while keeping local-first defaults.
- End-to-end automation with safeguards: optional assisted submission and follow-up tracking, always gated by human approval and audit logs.
- Ecosystem integrations: calendar/email linking for deadlines and follow-ups, portfolio linking, and export to professional networks.
- UX maturity: evolve the local UI into a polished, responsive app-like experience (desktop/mobile-friendly).
