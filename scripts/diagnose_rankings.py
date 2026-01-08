import argparse
import csv
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from modules.extract_profile import extract_profile  # noqa: E402
from modules.crawl_jobs import crawl_jobs  # noqa: E402
from modules.match_score import match_score  # noqa: E402
from utils.io import load_config, write_json, ensure_dir  # noqa: E402


def _normalize_id(job_id):
    if job_id is None:
        return ""
    return str(job_id)


def _rank_map(results):
    rank = {}
    for idx, row in enumerate(results):
        job_id = _normalize_id(row.get("id"))
        if not job_id:
            continue
        rank[job_id] = idx + 1
    return rank


def _top_jobs(results, limit=10):
    return [
        {
            "id": row.get("id"),
            "title": (row.get("job") or {}).get("title"),
            "company": (row.get("job") or {}).get("company"),
            "score": row.get("score"),
            "score_raw": row.get("score_raw"),
            "score_preset": row.get("score_preset"),
            "score_adjusted": row.get("score_adjusted"),
            "intent": (row.get("intent") or {}),
            "recommendation": row.get("recommendation"),
        }
        for row in results[:limit]
    ]


def _index_by_id(results):
    indexed = {}
    for row in results:
        job_id = _normalize_id(row.get("id"))
        if not job_id:
            continue
        indexed[job_id] = row
    return indexed


def _build_report(raw_results, preset_results, feedback_results):
    raw_rank = _rank_map(raw_results)
    preset_rank = _rank_map(preset_results)
    feedback_rank = _rank_map(feedback_results)
    preset_map = _index_by_id(preset_results)
    feedback_map = _index_by_id(feedback_results)
    all_ids = sorted(set(raw_rank) | set(preset_rank) | set(feedback_rank))
    rows = []
    for job_id in all_ids:
        raw_pos = raw_rank.get(job_id)
        preset_pos = preset_rank.get(job_id)
        feedback_pos = feedback_rank.get(job_id)
        delta_raw_preset = raw_pos - preset_pos if raw_pos and preset_pos else None
        delta_preset_feedback = preset_pos - feedback_pos if preset_pos and feedback_pos else None
        delta_raw_feedback = raw_pos - feedback_pos if raw_pos and feedback_pos else None
        shift = None
        if delta_raw_feedback is not None and abs(delta_raw_feedback) > 3:
            shift = "significant"
        meta = feedback_map.get(job_id) or preset_map.get(job_id) or {}
        intent = meta.get("intent") or {}
        rows.append(
            {
                "job_id": job_id,
                "raw_rank": raw_pos,
                "preset_rank": preset_pos,
                "feedback_rank": feedback_pos,
                "delta_raw_preset": delta_raw_preset,
                "delta_preset_feedback": delta_preset_feedback,
                "delta_raw_feedback": delta_raw_feedback,
                "shift": shift,
                "role_intent": intent.get("role_intent"),
                "job_track": intent.get("job_track"),
                "intent_alignment": intent.get("intent_alignment"),
                "intent_adjustment": intent.get("intent_adjustment"),
                "out_of_scope": intent.get("out_of_scope"),
            }
        )
    return rows


def _write_csv(rows, path):
    ensure_dir(os.path.dirname(path))
    fields = [
        "job_id",
        "raw_rank",
        "preset_rank",
        "feedback_rank",
        "delta_raw_preset",
        "delta_preset_feedback",
        "delta_raw_feedback",
        "shift",
        "role_intent",
        "job_track",
        "intent_alignment",
        "intent_adjustment",
        "out_of_scope",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(rows, path):
    ensure_dir(os.path.dirname(path))
    lines = [
        "| job_id | raw | preset | feedback | Δ raw→preset | Δ preset→feedback | Δ raw→feedback | shift | role_intent | job_track | intent | intent_adj | out_of_scope |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['job_id']} | {row['raw_rank']} | {row['preset_rank']} | {row['feedback_rank']} | "
            f"{row['delta_raw_preset']} | {row['delta_preset_feedback']} | {row['delta_raw_feedback']} | {row['shift'] or ''} | "
            f"{row.get('role_intent') or ''} | {row.get('job_track') or ''} | {row.get('intent_alignment') or ''} | "
            f"{row.get('intent_adjustment')} | {row.get('out_of_scope')} |"
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _parse_override_value(raw):
    text = raw.strip()
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if text.lower() in {"null", "none"}:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        if "." in text:
            return float(text)
        return int(text)
    except Exception:
        return text


def _apply_overrides(config, overrides):
    for override in overrides or []:
        if "=" not in override:
            continue
        key, raw_value = override.split("=", 1)
        path = [part for part in key.split(".") if part]
        if not path:
            continue
        current = config
        for part in path[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[path[-1]] = _parse_override_value(raw_value)
    return config


def diagnose_rankings(config_path, preset_name=None, output=None, fmt="json", overrides=None):
    config = load_config(config_path)
    config = _apply_overrides(config, overrides)
    run_config_path = config_path
    if overrides:
        output_dir = (config.get("paths", {}) or {}).get("output_dir") or "data/output"
        ensure_dir(output_dir)
        run_config_path = os.path.join(output_dir, "diagnose_config_override.json")
        write_json(config, run_config_path)

    extract_profile(run_config_path)
    crawl_jobs(run_config_path)
    preset_name = preset_name or (config.get("scoring", {}) or {}).get("active_preset")

    raw_results = match_score(run_config_path, write_outputs=False, feedback_enabled=False, preset_name="")
    preset_results = match_score(run_config_path, write_outputs=False, feedback_enabled=False, preset_name=preset_name)
    feedback_results = match_score(run_config_path, write_outputs=False, feedback_enabled=True, preset_name=preset_name)

    rows = _build_report(raw_results, preset_results, feedback_results)
    output_payload = {
        "preset": preset_name,
        "top_raw": _top_jobs(raw_results),
        "top_preset": _top_jobs(preset_results),
        "top_feedback": _top_jobs(feedback_results),
        "rank_deltas": rows,
    }
    if output and fmt == "json":
        output_payload["results_raw"] = raw_results
        output_payload["results_preset"] = preset_results
        output_payload["results_feedback"] = feedback_results

    if output:
        if fmt == "csv":
            _write_csv(rows, output)
        elif fmt == "md":
            _write_markdown(rows, output)
        else:
            ensure_dir(os.path.dirname(output))
            write_json(output_payload, output)
        print(f"Wrote diagnostics to {output}")
    else:
        print(json.dumps(output_payload, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Diagnose ranking deltas across scoring modes.")
    parser.add_argument("--config", default="tests/fixtures/config/applicant.yaml")
    parser.add_argument("--preset", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--format", choices=["json", "csv", "md"], default="json")
    parser.add_argument("--override", action="append", default=[], help="Override config values (key=value).")
    args = parser.parse_args()

    diagnose_rankings(
        args.config,
        preset_name=args.preset or None,
        output=args.output or None,
        fmt=args.format,
        overrides=args.override,
    )


if __name__ == "__main__":
    main()
