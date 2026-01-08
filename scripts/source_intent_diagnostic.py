import argparse
import json
import os
import sys
from collections import Counter, defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from utils.io import load_config  # noqa: E402

ROLE_FAMILIES = ["leadership", "architecture", "strategy", "engineering", "data_science", "other"]


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _classify_role(title):
    text = (title or "").lower()
    if any(token in text for token in ["director", "head", "vp", "vice president", "chief", "cxo"]):
        return "leadership"
    if any(
        token in text
        for token in [
            "architect",
            "architecture",
            "solutions architect",
            "solution architect",
            "enterprise architect",
            "principal architect",
        ]
    ):
        return "architecture"
    if any(token in text for token in ["strategy", "strategist", "ai strategy", "transformation"]):
        return "strategy"
    if any(token in text for token in ["data scientist", "research scientist", "ml scientist"]):
        return "data_science"
    if any(
        token in text
        for token in [
            "engineer",
            "developer",
            "fullstack",
            "full-stack",
            "backend",
            "sre",
            "platform engineer",
        ]
    ):
        return "engineering"
    return "other"


def _format_pct(value, total):
    return (value / total * 100.0) if total else 0.0


def _format_dist(dist, total):
    return {label: _format_pct(dist.get(label, 0), total) for label in ROLE_FAMILIES}


def _source_key(job):
    source = (job.get("source") or "unknown").lower()
    company = job.get("company") or ""
    return source, company


def _assign_source_intent(dist, total):
    pct = _format_dist(dist, total)
    leadership = pct.get("leadership", 0)
    architecture = pct.get("architecture", 0)
    strategy = pct.get("strategy", 0)
    engineering = pct.get("engineering", 0)

    if engineering >= 50:
        return "engineering_first"
    if (leadership + strategy) >= 30:
        return "executive_search"
    if architecture >= 25:
        return "consulting / advisory"
    if strategy >= 20:
        return "consulting / advisory"
    if (leadership + architecture + strategy) >= 35:
        return "product_first"
    return "go_to_market"


def _reweight_sources(results, cap=0.30):
    source_counts = Counter()
    rows = []
    for row in results:
        job = row.get("job") or {}
        source = (job.get("source") or "unknown").lower()
        source_counts[source] += 1
        rows.append((row, source))

    total = sum(source_counts.values()) or 1
    source_weights = {}
    for source, count in source_counts.items():
        share = count / total
        if share > cap:
            weight = cap / share
        else:
            weight = 1.0
        source_weights[source] = weight

    weighted = []
    for row, source in rows:
        base_score = row.get("score")
        score = base_score if isinstance(base_score, (int, float)) else 0.0
        weight = source_weights.get(source, 1.0)
        weighted.append((score * weight, row, weight))

    weighted.sort(key=lambda item: item[0], reverse=True)
    return weighted, source_weights


def _top_counts(rows, limit):
    counts = Counter()
    for row in rows[:limit]:
        job = row.get("job") or {}
        counts[_classify_role(job.get("title") or "")] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description="Source intent diagnostic")
    parser.add_argument("--config", default="config/applicant.yaml")
    parser.add_argument("--jobs", default="data/jobs/latest_jobs.json")
    parser.add_argument("--diagnostics", default="data/output/ranking_diagnostics_intent_on.json")
    parser.add_argument("--output", default="logs/source_intent_diagnostic.md")
    parser.add_argument("--cap", type=float, default=0.30)
    args = parser.parse_args()

    config = load_config(args.config)
    jobs = _load_json(args.jobs) if os.path.exists(args.jobs) else []
    diagnostics = _load_json(args.diagnostics) if os.path.exists(args.diagnostics) else {}
    results = diagnostics.get("results_preset") or []

    by_source = defaultdict(list)
    for job in jobs:
        key = _source_key(job)
        by_source[key].append(job)

    source_intent_rows = []
    for (source, company), rows in sorted(by_source.items()):
        dist = Counter()
        for row in rows:
            dist[_classify_role(row.get("title") or "")] += 1
        intent = _assign_source_intent(dist, len(rows))
        source_intent_rows.append((source, company, len(rows), dist, intent))

    lines = []
    lines.append("# Source Intent Diagnostic")
    lines.append("")
    lines.append("## Source Intent Classification")
    lines.append("| Source | Company | Jobs | Intent Label | Notes |")
    lines.append("| --- | --- | --- | --- | --- |")
    for source, company, count, dist, intent in source_intent_rows:
        pct = _format_dist(dist, count)
        notes = f"eng {pct['engineering']:.1f}% / strat {pct['strategy']:.1f}% / arch {pct['architecture']:.1f}% / lead {pct['leadership']:.1f}%"
        lines.append(f"| {source} | {company or '-'} | {count} | {intent} | {notes} |")

    lines.append("")
    lines.append("## Conditional Probabilities P(role_family | source)")
    for source, company, count, dist, _intent in source_intent_rows:
        lines.append(f"### {source} | {company or '-'}")
        for label in ROLE_FAMILIES:
            pct = _format_pct(dist.get(label, 0), count)
            lines.append(f"- {label}: {pct:.1f}%")

    global_dist = Counter()
    for job in jobs:
        global_dist[_classify_role(job.get("title") or "")] += 1
    lines.append("")
    lines.append("## Structurally Unlikely Families (Corpus)")
    unlikely = []
    for label in ROLE_FAMILIES:
        pct = _format_pct(global_dist.get(label, 0), len(jobs) if jobs else 1)
        if pct < 5:
            unlikely.append((label, pct))
    if unlikely:
        for label, pct in unlikely:
            lines.append(f"- {label}: {pct:.1f}% of corpus")
    else:
        lines.append("- None below 5% of corpus")

    weighted, source_weights = _reweight_sources(results, cap=args.cap)
    results_reweighted = [row for _score, row, _weight in weighted]

    top25_original = _top_counts(results, 25)
    top50_original = _top_counts(results, 50)
    top25_weighted = _top_counts(results_reweighted, 25)
    top50_weighted = _top_counts(results_reweighted, 50)

    lines.append("")
    lines.append("## Source Reweighting Simulation")
    lines.append(f"- cap per source: {args.cap:.0%}")
    lines.append("- source weights:")
    for source, weight in sorted(source_weights.items()):
        lines.append(f"  - {source}: {weight:.2f}")

    def dist_lines(label, counts, total):
        lines.append(f"### {label}")
        for fam in ROLE_FAMILIES:
            value = counts.get(fam, 0)
            pct = _format_pct(value, total)
            lines.append(f"- {fam}: {value} ({pct:.1f}%)")

    dist_lines("Top 25 (Original)", top25_original, 25)
    dist_lines("Top 25 (Reweighted)", top25_weighted, 25)
    dist_lines("Top 50 (Original)", top50_original, 50)
    dist_lines("Top 50 (Reweighted)", top50_weighted, 50)

    target_families = {"leadership", "architecture", "strategy"}
    original_target = sum(top25_original.get(f, 0) for f in target_families)
    reweighted_target = sum(top25_weighted.get(f, 0) for f in target_families)
    improvement = reweighted_target - original_target

    if improvement >= 2:
        impact = "Source diversity improves leadership/strategy presence in Top 25."
    elif improvement <= -2:
        impact = "Source reweighting reduces target-family presence in Top 25."
    else:
        impact = "Source reweighting does not materially change Top 25 composition."

    lines.append("")
    lines.append("## Impact Assessment")
    lines.append(f"- {impact}")

    if improvement >= 2 or any(pct < 5 for _label, pct in unlikely):
        recommendation = "A) Source intent layer REQUIRED"
    elif improvement == 0:
        recommendation = "B) Source intent layer OPTIONAL"
    else:
        recommendation = "C) Source intent layer UNNECESSARY"

    lines.append("")
    lines.append("## Recommendation")
    lines.append(f"- {recommendation}")
    lines.append("- Rationale:")
    rationale = []
    if any(pct < 5 for _label, pct in unlikely):
        rationale.append("Underrepresented role families suggest source bias in discovery.")
    if improvement >= 2:
        rationale.append("Reweighting shifts top ranks toward target families, indicating source influence.")
    if improvement == 0:
        rationale.append("Reweighting does not change top ranks, suggesting intent logic already dominates.")
    if not rationale:
        rationale.append("Observed source mix does not materially distort role-family visibility.")
    for item in rationale[:5]:
        lines.append(f"  - {item}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    conclusion_subject = "ATS/source mix" if any(pct < 5 for _label, pct in unlikely) else "role intent logic"
    conclusion_object = "role intent logic" if conclusion_subject == "ATS/source mix" else "source mix"
    print(f"Wrote report to {args.output}")
    print(f"Discovery breadth is currently limited primarily by {conclusion_subject}, not by {conclusion_object}.")


if __name__ == "__main__":
    main()
