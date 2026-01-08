import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from utils.io import load_config  # noqa: E402


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


def _normalize_title(title):
    text = (title or "").lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _format_distribution(counts, total):
    parts = []
    for label in ["leadership", "architecture", "strategy", "engineering", "data_science", "other"]:
        value = counts.get(label, 0)
        pct = (value / total * 100) if total else 0
        parts.append((label, value, pct))
    return parts


def _count_titles(rows):
    counts = Counter()
    for row in rows:
        title = (row.get("title") or row.get("job", {}).get("title") or "").strip()
        if not title:
            continue
        counts[_normalize_title(title)] += 1
    return counts


def _engineering_title_ratio(rows):
    if not rows:
        return 0.0
    tokens = ["engineer", "developer", "sre", "backend", "platform"]
    hit = 0
    for row in rows:
        title = (row.get("title") or row.get("job", {}).get("title") or "").lower()
        if any(token in title for token in tokens):
            hit += 1
    return hit / len(rows)


def _role_distribution(rows):
    counts = Counter()
    for row in rows:
        title = row.get("title") or (row.get("job") or {}).get("title") or ""
        counts[_classify_role(title)] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description="ATS coverage bias audit")
    parser.add_argument("--config", default="config/applicant.yaml")
    parser.add_argument("--jobs", default="data/jobs/latest_jobs.json")
    parser.add_argument("--diagnostics", default="data/output/ranking_diagnostics_intent_on.json")
    parser.add_argument("--output", default="logs/ats_bias_audit.md")
    args = parser.parse_args()

    config = load_config(args.config)
    jobs = _load_json(args.jobs) if os.path.exists(args.jobs) else []
    diagnostics = _load_json(args.diagnostics) if os.path.exists(args.diagnostics) else {}
    results_on = diagnostics.get("results_preset") or []

    total_jobs = len(jobs) if jobs else 1

    active_ats = []
    if (config.get("job_sources") or {}).get("use_ats", False):
        for entry in config.get("job_sources", {}).get("ats_companies", []) or []:
            provider = entry.get("provider") or ""
            company = entry.get("company") or entry.get("board") or ""
            if provider:
                active_ats.append((provider, company))
    adapters = config.get("adapters", {}) or {}
    for name, entry in adapters.items():
        if entry.get("enabled"):
            active_ats.append((name, entry.get("source_path") or ""))

    source_company = defaultdict(list)
    for job in jobs:
        source = (job.get("source") or "unknown").lower()
        company = job.get("company") or ""
        source_company[(source, company)].append(job)

    inventory_rows = []
    for source, company in sorted(source_company):
        rows = source_company[(source, company)]
        count = len(rows)
        pct = count / total_jobs * 100 if total_jobs else 0
        inventory_rows.append((source, company, count, pct))

    dist_rows = []
    for source, company, count, pct in inventory_rows:
        rows = source_company[(source, company)]
        counts = _role_distribution(rows)
        dist = _format_distribution(counts, count)
        dist_rows.append((source, company, count, dist))

    global_counts = _role_distribution(jobs)
    global_dist = _format_distribution(global_counts, len(jobs) if jobs else 1)

    top50 = results_on[:50]
    top50_counts = _role_distribution(top50)
    top50_dist = _format_distribution(top50_counts, len(top50) if top50 else 1)

    global_engineering = global_counts.get("engineering", 0) / (len(jobs) if jobs else 1)
    top50_engineering = top50_counts.get("engineering", 0) / (len(top50) if top50 else 1)

    bias_statement = ""
    if global_engineering > top50_engineering:
        bias_statement = "Engineering roles are more prevalent in the crawl corpus than in Top 50 results."
    elif global_engineering < top50_engineering:
        bias_statement = "Engineering roles are less prevalent in the crawl corpus than in Top 50 results."
    else:
        bias_statement = "Engineering role prevalence is similar between corpus and Top 50 results."

    target_families = {"leadership", "architecture", "strategy"}
    top50_target = sum(top50_counts.get(fam, 0) for fam in target_families)
    top50_target_pct = top50_target / (len(top50) if top50 else 1)
    top50_engineering_pct = top50_engineering

    if top50_target_pct >= 0.6 and top50_engineering_pct <= 0.2 and global_engineering > top50_engineering:
        verdict = "PASS"
    elif top50_target_pct >= 0.4 and top50_engineering_pct <= 0.35:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    intent_compensation = ""
    if global_engineering > top50_engineering:
        intent_compensation = "Intent calibration mitigates corpus bias by pulling non-engineering roles up in Top 50."
    else:
        intent_compensation = "Intent calibration does not appear to offset corpus composition." 

    underrepresented = []
    for label, value, pct in global_dist:
        if label in target_families and pct < 10:
            underrepresented.append((label, pct))

    bias_indicators = []
    title_skew = []
    for source, company, count, pct in inventory_rows:
        rows = source_company[(source, company)]
        ratio = _engineering_title_ratio(rows)
        top_titles = _count_titles(rows).most_common(15)
        title_skew.append((source, company, top_titles))
        if ratio > 0.5:
            bias_indicators.append((source, company, ratio))

    lines = []
    lines.append("# ATS Coverage Bias Audit")
    lines.append("")
    lines.append("## Active ATS Inventory (Observed)")
    lines.append("| ATS | Company | Jobs | % of Corpus |")
    lines.append("| --- | --- | --- | --- |")
    for source, company, count, pct in inventory_rows:
        lines.append(f"| {source} | {company or '-'} | {count} | {pct:.1f}% |")

    lines.append("")
    lines.append("## Role-Family Distribution per ATS")
    lines.append("| ATS | Company | Total | % Leadership | % Architecture | % Strategy | % Engineering | % Data Science | % Other |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for source, company, count, dist in dist_rows:
        dist_map = {label: pct for label, _value, pct in dist}
        lines.append(
            f"| {source} | {company or '-'} | {count} | "
            f"{dist_map.get('leadership', 0):.1f}% | {dist_map.get('architecture', 0):.1f}% | "
            f"{dist_map.get('strategy', 0):.1f}% | {dist_map.get('engineering', 0):.1f}% | "
            f"{dist_map.get('data_science', 0):.1f}% | {dist_map.get('other', 0):.1f}% |"
        )

    lines.append("")
    lines.append("## Cross-ATS Aggregation vs Top 50 (Intent ON)")
    lines.append("### Corpus Distribution")
    for label, value, pct in global_dist:
        lines.append(f"- {label}: {value} ({pct:.1f}%)")
    lines.append("### Top 50 Distribution (Intent ON)")
    for label, value, pct in top50_dist:
        lines.append(f"- {label}: {value} ({pct:.1f}%)")
    lines.append("")
    lines.append(f"- {bias_statement}")
    lines.append(f"- {intent_compensation}")

    lines.append("")
    lines.append("## Title-Level Skew (Top 15 Titles per ATS)")
    for source, company, titles in title_skew:
        lines.append(f"### {source} | {company or '-'}")
        for title, count in titles:
            lines.append(f"- {title} ({count})")

    lines.append("")
    if bias_indicators:
        lines.append("## Bias Indicators")
        for source, company, ratio in bias_indicators:
            lines.append(f"- {source} | {company or '-'}: {ratio:.0%} titles include engineering tokens")
    else:
        lines.append("## Bias Indicators")
        lines.append("- No ATS exceeds 50% engineering-token titles.")

    lines.append("")
    lines.append("## Coverage Gap Hypothesis")
    if underrepresented:
        labels = ", ".join([f"{label} ({pct:.1f}%)" for label, pct in underrepresented])
        lines.append(f"- Underrepresented families in corpus: {labels}.")
    else:
        lines.append("- Leadership/architecture/strategy families are not materially underrepresented in the corpus.")
    lines.append("- These roles are often posted outside engineering-focused ATSs (executive search, LinkedIn-native, consulting firm boards).")

    lines.append("")
    lines.append("## Verdict")
    lines.append(f"- {verdict}")
    lines.append("- PASS: ATS bias exists but intent calibration keeps Top 25/50 target-aligned.")
    lines.append("- WARN: ATS bias limits discovery breadth despite correct top ranks.")
    lines.append("- FAIL: ATS bias overwhelms intent logic.")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    conclusion = "sufficient" if verdict == "PASS" else "limiting" if verdict == "WARN" else "blocking"
    print(f"Wrote report to {args.output}")
    print(f"Current ATS coverage is {conclusion} for Applicant's role intent goals.")


if __name__ == "__main__":
    main()
