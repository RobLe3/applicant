# Source Intent Taxonomy + Source Selection Policy (Refined)

## 1) CV-Derived Source Requirements (Evidence-Based)
- Dominant role targets: executive AI strategy leadership; platform and protocol architecture; consulting/public sector leadership; governance/compliance focus.
- Secondary acceptable roles: architecture-heavy technical leadership (principal/lead architect, platform lead).
- Deprioritize by default: execution-heavy IC engineering roles (engineer/developer) unless explicitly targeted.

Evidence from CV:
- “Executive Profile AI Strategy Leader…”
- “Director AI Strategy” role; “Manager Cyber Security (Defense) / Public Sector Consulting”.
- “Leadership & Strategy”, “Governance / Compliance / Zero‑trust”, “Protocol design”, “SaaS model design”.

## 2) Canonical Source Intent Taxonomy (Frozen)
Enum set (max 6):
- engineering_first
- architecture_platform
- consulting_advisory
- executive_search
- go_to_market
- public_sector_defense

Definitions (CV-aligned):
1) engineering_first
   - Commonly contains: software engineer, data engineer, ML engineer, SRE, backend/fullstack IC roles (mid–senior).
   - Rarely contains: director/head/strategy roles.
   - Relevance: capability depth only; should be capped for this candidate by default.

2) architecture_platform
   - Commonly contains: principal/lead architect, platform architect, solutions/enterprise architect, systems design leadership.
   - Rarely contains: pure IC implementation roles or executive search.
   - Relevance: directly aligned with platform/protocol and architecture ownership in the CV.

3) consulting_advisory
   - Commonly contains: consulting lead, advisory, pre‑sales architect, transformation lead, program lead.
   - Rarely contains: entry-level engineering IC roles.
   - Relevance: matches public sector consulting and leadership roles in the CV.

4) executive_search
   - Commonly contains: director/head/VP/Chief roles, strategy leadership, business unit leadership.
   - Rarely contains: IC roles.
   - Relevance: aligns with executive AI strategy and leadership positioning.

5) go_to_market
   - Commonly contains: product strategy, partnerships, commercial strategy, solutions consulting, sales engineering leadership.
   - Rarely contains: pure engineering IC.
   - Relevance: aligns with SaaS/white‑label business models and partner ecosystem leadership.

6) public_sector_defense
   - Commonly contains: public sector consulting, defense security leadership, government transformation.
   - Rarely contains: startup IC engineering roles.
   - Relevance: CV includes public sector/defense cybersecurity leadership and compliance work.

## 3) Source Policy Schema (Safe by Default)
Proposed YAML under `discovery.source_policy`:
```
discovery:
  source_policy:
    mode: disabled            # disabled | advisory | enforced (default: disabled)
    eligible_source_intents: [engineering_first, architecture_platform, consulting_advisory, executive_search, go_to_market, public_sector_defense]
    preferred_source_intents: [executive_search, consulting_advisory, architecture_platform, public_sector_defense, go_to_market]
    caps:
      max_share_per_source: 0.30
      max_share_per_intent: 0.50
      apply_to: ingestion     # explicit; no enforcement in this task
    allowlist_sources: []
    blocklist_sources: []
    rationale: "Align source mix with profile.role_intent while keeping discovery broad."
    reviewed_by_human: false
    last_reviewed_at: ""
```
Safety rules:
- mode == disabled or advisory: MUST NOT change any crawling, matching, scoring, or ranking behavior.
- mode == enforced requires reviewed_by_human == true; otherwise hard-fail.
- Unknown enums or fields must hard-fail with a clear error.

## 4) Role-Intent → Preferred Source-Intent Mapping (Advisory)
| role_intent | prioritize | deprioritize (cap, not ban) |
| --- | --- | --- |
| executive_strategy | executive_search, consulting_advisory, architecture_platform, public_sector_defense, go_to_market | engineering_first |
| principal_architecture | architecture_platform, consulting_advisory, engineering_first | executive_search |
| consulting_leadership | consulting_advisory, public_sector_defense, go_to_market | engineering_first |
| engineering_execution | engineering_first, architecture_platform | executive_search |

## 5) Diagnostics Specification (No Behavior Change)
Output: `data/output/source_policy_diagnostic.json` containing:
- `profile_role_intent`
- `active_sources` with `source.intent_label`
- `eligible_source_intents`, `preferred_source_intents`
- `warnings` (e.g., preferred intents missing from active sources)

Warnings:
- “Preferred source intents missing: executive_search, consulting_advisory”
- “Source intent exceeds max_share_per_intent” (diagnostic only unless enforced)

## 6) Safety Guarantees + Non-Goals
Guarantees:
- With mode == disabled, ranking outputs remain identical to Phase 10 baseline.
- Verification: compare `matched_jobs.json` hashes or `run_smoke_tests.py --compare`.

Non-goals:
- No new sources, no scrapers, no crawling changes.
- No ranking/scoring/filtering changes.
- No automation without explicit human approval.

Taxonomy is minimal, CV-aligned, and safe by default.
