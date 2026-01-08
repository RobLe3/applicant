import argparse
import json
import os
from collections import Counter


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _job_key(row):
    job_id = row.get("id")
    if job_id is not None:
        return f"id:{job_id}"
    job = row.get("job") or {}
    title = (job.get("title") or "").strip().lower()
    company = (job.get("company") or "").strip().lower()
    location = (job.get("location") or "").strip().lower()
    return f"key:{company}|{title}|{location}"


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


def _top_counts(results, n):
    counts = Counter()
    for row in results[:n]:
        title = (row.get("job") or {}).get("title") or ""
        counts[_classify_role(title)] += 1
    return counts


def _format_counts(counts, n):
    lines = []
    for label in ["leadership", "architecture", "strategy", "engineering", "data_science", "other"]:
        value = counts.get(label, 0)
        pct = (value / n * 100) if n else 0
        lines.append(f"- {label}: {value} ({pct:.1f}%)")
    return "\n".join(lines)


def _rank_map(results, limit=100):
    rank = {}
    for idx, row in enumerate(results[:limit]):
        rank[_job_key(row)] = idx + 1
    return rank


def _extract_mover_row(key, on_map, off_map):
    row_on = on_map.get(key)
    row_off = off_map.get(key)
    row = row_on or row_off or {}
    job = row.get("job") or {}
    intent = (row_on or row_off or {}).get("intent") or {}
    return {
        "row_on": row_on,
        "row_off": row_off,
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "intent": intent,
    }


def _build_movers(results_on, results_off, top_n=20, limit=100):
    on_rank = _rank_map(results_on, limit=limit)
    off_rank = _rank_map(results_off, limit=limit)
    on_map = {_job_key(row): row for row in results_on[:limit]}
    off_map = {_job_key(row): row for row in results_off[:limit]}
    keys = set(on_rank) | set(off_rank)
    deltas = []
    for key in keys:
        rank_on = on_rank.get(key, limit + 1)
        rank_off = off_rank.get(key, limit + 1)
        delta = rank_off - rank_on
        deltas.append((delta, key, rank_off, rank_on))
    deltas.sort(reverse=True)
    movers_up = deltas[:top_n]
    movers_down = sorted(deltas, key=lambda x: x[0])[:top_n]

    def format_movers(movers):
        lines = []
        for delta, key, rank_off, rank_on in movers:
            meta = _extract_mover_row(key, on_map, off_map)
            row_on = meta["row_on"] or {}
            row_off = meta["row_off"] or {}
            intent = meta["intent"]
            score_raw = row_on.get("score_raw") if row_on else row_off.get("score_raw")
            score_on = row_on.get("score") if row_on else None
            adjusted_by = row_on.get("adjusted_by") if row_on else row_off.get("adjusted_by")
            lines.append(
                "- "
                + f"{meta['title']} | {meta['company']} | {meta['location']} | "
                + f"{rank_off} -> {rank_on} | score_raw {score_raw} | score_on {score_on} | "
                + f"intent {intent.get('intent_alignment')} adj {intent.get('intent_adjustment')} "
                + f"out_of_scope {intent.get('out_of_scope')} | adjusted_by {adjusted_by}"
            )
        return "\n".join(lines)

    return format_movers(movers_up), format_movers(movers_down), deltas


def _coverage_check(results_on, top_n=50):
    zero_coverage = []
    for row in results_on[:top_n]:
        coverage = ((row.get("qualification") or {}).get("coverage"))
        coverage_value = coverage if isinstance(coverage, (int, float)) else 0.0
        if coverage_value <= 0.0:
            zero_coverage.append(row)
    examples = []
    for row in zero_coverage:
        job = row.get("job") or {}
        title = job.get("title", "")
        family = _classify_role(title)
        if family not in {"leadership", "architecture", "strategy"}:
            continue
        desc = job.get("description") or ""
        facts = row.get("job_facts") or {}
        examples.append(
            {
                "title": title,
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "length": len(desc),
                "seniority": facts.get("seniority"),
                "work_mode": facts.get("work_mode"),
                "contract_type": facts.get("contract_type"),
            }
        )
        if len(examples) >= 5:
            break
    return len(zero_coverage), examples


def main():
    parser = argparse.ArgumentParser(description="Verify intent shift effects.")
    parser.add_argument(
        "--intent-on",
        default="data/output/ranking_diagnostics_intent_on.json",
        help="Diagnostics output with intent enabled.",
    )
    parser.add_argument(
        "--intent-off",
        default="data/output/ranking_diagnostics_intent_off.json",
        help="Diagnostics output with intent disabled.",
    )
    parser.add_argument(
        "--profile",
        default="data/output/rob_profile.json",
        help="Profile path to read role intent.",
    )
    parser.add_argument(
        "--output",
        default="logs/phase10_verification.md",
        help="Report output path.",
    )
    parser.add_argument("--top", type=int, default=50)
    args = parser.parse_args()

    data_on = _load_json(args.intent_on)
    data_off = _load_json(args.intent_off)
    results_on = data_on.get("results_preset") or []
    results_off = data_off.get("results_preset") or []

    profile = _load_json(args.profile) if os.path.exists(args.profile) else {}
    role_intent = profile.get("role_intent", "unknown")

    top25_on = _top_counts(results_on, 25)
    top25_off = _top_counts(results_off, 25)
    top50_on = _top_counts(results_on, 50)
    top50_off = _top_counts(results_off, 50)

    delta25 = Counter({key: top25_on.get(key, 0) - top25_off.get(key, 0) for key in set(top25_on) | set(top25_off)})
    delta50 = Counter({key: top50_on.get(key, 0) - top50_off.get(key, 0) for key in set(top50_on) | set(top50_off)})

    movers_up, movers_down, deltas = _build_movers(results_on, results_off, top_n=20, limit=100)
    intent_evidence = [item for item in deltas if item[0] != 0]

    zero_count, examples = _coverage_check(results_on, top_n=50)

    target_families = ["leadership", "architecture", "strategy"]
    target_count = sum(top25_on.get(fam, 0) for fam in target_families)
    engineering_count = top25_on.get("engineering", 0)
    target_pct = target_count / 25 if 25 else 0
    engineering_pct = engineering_count / 25 if 25 else 0
    intent_evidence_count = sum(1 for row in results_on[:25] if (row.get("intent") or {}).get("intent_adjustment"))

    passed = target_pct >= 0.6 and engineering_pct <= 0.2 and intent_evidence_count >= 5
    status = "PASS" if passed else "FAIL"

    lines = [
        "# Phase 10 Verification",
        "",
        "## Commands Executed",
        "- python scripts/run_pipeline.py --config config/applicant.yaml",
        "- python scripts/diagnose_rankings.py --config config/applicant.yaml --output data/output/ranking_diagnostics_intent_on.json",
        "- python scripts/diagnose_rankings.py --config config/applicant.yaml --override matching.role_intent.alignment_bonus=0 ",
        "  --override matching.role_intent.mismatch_penalty=0 --override matching.role_intent.execution_bonus=0 ",
        "  --output data/output/ranking_diagnostics_intent_off.json",
        "- python scripts/verify_intent_shift.py --intent-on data/output/ranking_diagnostics_intent_on.json ",
        "  --intent-off data/output/ranking_diagnostics_intent_off.json",
        "",
        f"Profile role_intent: {role_intent}",
        "",
        "## Top 25 Distribution (Intent ON)",
        _format_counts(top25_on, 25),
        "",
        "## Top 25 Distribution (Intent OFF)",
        _format_counts(top25_off, 25),
        "",
        "## Top 25 Delta (ON - OFF)",
        _format_counts(delta25, 25),
        "",
        "## Top 50 Distribution (Intent ON)",
        _format_counts(top50_on, 50),
        "",
        "## Top 50 Distribution (Intent OFF)",
        _format_counts(top50_off, 50),
        "",
        "## Top 50 Delta (ON - OFF)",
        _format_counts(delta50, 50),
        "",
        "## Biggest Upward Movers (Top 100)",
        movers_up or "- None",
        "",
        "## Biggest Downward Movers (Top 100)",
        movers_down or "- None",
        "",
        "## Coverage Sanity Check (Top 50, Intent ON)",
        f"- coverage==0 count: {zero_count}",
    ]

    if examples:
        lines.append("- Examples (leadership/architecture/strategy with coverage==0):")
        for ex in examples:
            lines.append(
                f"  - {ex['title']} | {ex['company']} | {ex['location']} | "
                f"len {ex['length']} | seniority {ex['seniority']} | work_mode {ex['work_mode']} | contract {ex['contract_type']}"
            )
    else:
        lines.append("- No coverage==0 examples in leadership/architecture/strategy roles.")

    lines.extend(
        [
            "",
            "## Conclusion",
            f"- target families (leadership+architecture+strategy) in Top25: {target_count}/25 ({target_pct:.2%})",
            f"- engineering in Top25: {engineering_count}/25 ({engineering_pct:.2%})",
            f"- intent adjustment evidence in Top25: {intent_evidence_count} entries",
            f"- Result: {status}",
        ]
    )

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote report to {args.output}")
    print(f"Result: {status}")


if __name__ == "__main__":
    main()
