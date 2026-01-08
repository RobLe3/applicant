import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from utils.io import load_config, read_json  # noqa: E402


def _load_json(path):
    try:
        return read_json(path), None
    except Exception as exc:
        return None, str(exc)


def _validate_submission_logs(log_dir):
    errors = []
    entries = []
    if not os.path.exists(log_dir):
        return errors, entries
    for name in sorted(os.listdir(log_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(log_dir, name)
        payload, err = _load_json(path)
        if err or not isinstance(payload, dict):
            errors.append(f"{path}: invalid json ({err or 'not a dict'})")
            continue
        for key in ["recorded_at", "job_id", "status"]:
            if not payload.get(key):
                errors.append(f"{path}: missing {key}")
        entries.append(payload)
    return errors, entries


def _validate_feedback(feedback_path):
    errors = []
    outcomes = []
    if not os.path.exists(feedback_path):
        return errors, outcomes
    payload, err = _load_json(feedback_path)
    if err or not isinstance(payload, dict):
        errors.append(f"{feedback_path}: invalid json ({err or 'not a dict'})")
        return errors, outcomes
    outcomes = payload.get("outcomes")
    if not isinstance(outcomes, list):
        errors.append(f"{feedback_path}: outcomes must be a list")
        return errors, []
    for idx, entry in enumerate(outcomes):
        if not isinstance(entry, dict):
            errors.append(f"{feedback_path}: outcome[{idx}] not an object")
            continue
        for key in ["recorded_at", "job_id", "outcome"]:
            if not entry.get(key):
                errors.append(f"{feedback_path}: outcome[{idx}] missing {key}")
    return errors, outcomes


def _emit_feedback_deltas(output_dir, outcomes):
    if not outcomes:
        return
    matched_path = os.path.join(output_dir, "matched_jobs.json")
    if not os.path.exists(matched_path):
        return
    matched, err = _load_json(matched_path)
    if err or not isinstance(matched, list):
        return
    score_map = {}
    for row in matched:
        job_id = row.get("id")
        adjustment = row.get("score_feedback_adjustment", row.get("score_adjustment"))
        if job_id is not None and isinstance(adjustment, (int, float)):
            score_map[str(job_id)] = adjustment
    tag_adjustments = {}
    for entry in outcomes:
        job_id = str(entry.get("job_id"))
        tags = entry.get("tags") or []
        adjustment = score_map.get(job_id)
        if adjustment is None:
            continue
        for tag in tags:
            tag_adjustments.setdefault(tag, []).append(adjustment)
    if not tag_adjustments:
        return
    print("Feedback tag adjustments:")
    for tag, values in sorted(tag_adjustments.items()):
        avg = sum(values) / len(values) if values else 0.0
        print(f"- {tag}: avg {avg:.4f} (n={len(values)})")


def main():
    parser = argparse.ArgumentParser(description="Validate submission and feedback logs.")
    parser.add_argument("--config", default="config/applicant.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    logs_dir = config["paths"]["logs_dir"]
    output_dir = config["paths"]["output_dir"]
    feedback_path = config.get("matching", {}).get("feedback", {}).get("path") or os.path.join(
        output_dir, "feedback.json"
    )

    submission_dir = os.path.join(logs_dir, "submissions")
    errors = []

    submission_errors, submission_entries = _validate_submission_logs(submission_dir)
    errors.extend(submission_errors)

    feedback_errors, outcomes = _validate_feedback(feedback_path)
    errors.extend(feedback_errors)

    if errors:
        print("Log validation failed:")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)

    print("Log validation passed.")
    print(f"Submission logs: {len(submission_entries)}")
    print(f"Feedback outcomes: {len(outcomes)}")
    _emit_feedback_deltas(output_dir, outcomes)


if __name__ == "__main__":
    main()
