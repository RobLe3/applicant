# Applicant MVP Configuration Guide
Release: v0.5 beta (maturity score: 6.4/10)

This document summarizes the most important configuration sections in `config/applicant.yaml`.

## Paths
Defines local folders for sources, jobs, outputs, prompts, and logs.

## Profile
Identity and profile extraction settings (name, location, email, committee threshold).

## Matching
Base scoring weights and thresholds used for raw scoring.

Key fields:
- `matching.weights`: base weights for skills/title/location/language/experience/alignment.
- `matching.apply_threshold`, `matching.consider_threshold`: base recommendation cutoffs.
- `matching.semantic`: semantic backend and cache settings.
- `matching.similarity`: clustering toggle and threshold for similar jobs.
- `matching.feedback`: opt-in feedback configuration.
  - `enabled`: allow feedback to influence scoring.
  - `tag_weight`, `company_weight`: weighting for tag vs company feedback.
  - `min_samples`: minimum outcomes before a tag influences scoring.
  - `max_adjustment`: maximum absolute adjustment applied to a score.
- `matching.role_intent`: intent-aware scoring adjustments.
  - `enabled`: toggle intent adjustments.
  - `mismatch_penalty`: penalty for execution-heavy roles when intent is leadership/architecture/consulting.
  - `alignment_bonus`: bonus for strategy/architecture/consulting roles when aligned.
  - `execution_bonus`: optional bonus for execution roles when intent is execution.
- `matching.recommendation_guard`: caps recommendations for clearly out-of-scope sales/GTM titles.
  - `enabled`: toggle the guard without changing scoring.

## Scoring Presets
Presets provide alternate weighting profiles without editing base weights.

```
scoring:
  active_preset: balanced
  presets:
    balanced:
      label: Balanced
      weights: { ... }
      thresholds: { apply: 0.25, consider: 0.15 }
    growth:
      label: Growth
      weights: { ... }
      thresholds: { apply: 0.23, consider: 0.12 }
```

Presets are selected at runtime in the review UI and do not modify the base weights.

## Job Sources + Filters
Controls which job sources are crawled and which keywords/locations are filtered.

## Meta (Version)
Project metadata fields:
- `meta.version`: derived release label (e.g., `0.5.0-beta`).
- `meta.maturity_label`: alpha/beta/rc/stable.
- `meta.maturity_score`: numeric score used for version mapping.

## Adapters
Adapter registry for local ingestion modules.

```
adapters:
  stepstone:
    enabled: true
    source_path: data/jobs/stepstone_jobs.json
    max_total: 0
  linkedin:
    enabled: false
    source_path: data/jobs/linkedin_jobs.json
    max_total: 0
```

Adapters read local files only and export raw + sanitized job JSON into `data/jobs/`.

## Schedule
Local scheduler configuration used by `scripts/schedule_runner.py`.

```
schedule:
  daily: false
  hour: 9
  frequency: "24h"
```

## Export and Import
Local export/import helpers for offline archiving:
- `export_data(path, encrypted=True)`
- `import_data(path, require_confirm=True)`

Environment flags:
- `APPLICANT_EXPORT_KEY`: optional key for XOR encryption.
- `APPLICANT_IMPORT_CONFIRM`: set to `true` to allow imports.
- `APPLICANT_IMPORT_OVERWRITE`: set to `true` to overwrite existing files.

## Drafting
Controls application draft behavior (review gate, letter date, attachments).

Role-family templates:
- `drafting.role_families`: list of template families (e.g., `engineering`, `data`, `strategy`).
- `drafting.default_role_family`: optional default family when no override is set.

Overrides are stored per job in `data/output/template_overrides.json` and are applied during draft generation.

## Submission
Controls draft email creation and optional SMTP sending (opt-in).

## Database
Toggles SQLite usage for votes and job states.
