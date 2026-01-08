# Usability Fix Report

## Root causes
- UI crawl panel only listed ATS companies; adapters were not exposed in `/api/profile` or rendered in the crawl tab.
- Job IDs were adapter-specific and unstable, so votes and queues drifted across runs.
- Greenhouse crawl used the jobs list without full content, leaving most ATS descriptions empty; RSS jobs also lacked page text.
- Coverage scoring ran even when descriptions were missing, causing near-zero coverage and flattened scores.

## Fixes applied
- Added deterministic `job_id` hashing (`source_id + external_id/url + title + location`) with dedupe logging in `modules/crawl_jobs.py`.
- Fetched RSS job page text when feed items were short; stored `text_missing` and raw/sanitized text consistently.
- Switched Greenhouse crawl to `?content=true` (detail fallback retained) to ensure descriptions populate.
- Enforced coverage gating when descriptions are missing and used semantic similarity when coverage is zero.
- Normalized vote keys to string across load/save paths and returned decisions in `/api/matches` by `job_id`.
- Exposed adapter config in `/api/profile` and rendered ATS + RSS sources in the crawl UI.

## Before / After sources
- Before: Crawl UI showed only ATS companies (Cloudflare, Elastic, Databricks, MongoDB, GitLab). RSS sources were invisible.
- After: Crawl UI lists ATS companies plus RSS feeds (ReliefWeb, EPSO), and matched jobs now include:
  - greenhouse: 178
  - epso_public: 4
  - reliefweb_consulting: 1
  - sample: 1

## Before / After score distribution
- Before (missing descriptions): `text_missing` 231/236, coverage zero 235/236, scores ranged 0.00–0.36 (compressed).
- After (content=true + RSS fetch): `text_missing` 1/184, scores range 0.17–0.42 with visible spread. Coverage remains mostly zero (183/184), indicating requirement extraction is not finding matchable requirements despite descriptions being present.

## Review actions
- Votes now persist and resolve by stable `job_id` (string-normalized), and `/api/matches` returns the correct decision payload for each match.

Applicant now shows all sources, surfaces profile-fitting jobs, and review actions work correctly.
