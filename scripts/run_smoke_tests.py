import argparse
import difflib
import hashlib
import json
import os
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from modules.extract_profile import extract_profile  # noqa: E402
from modules.crawl_jobs import crawl_jobs  # noqa: E402
from modules.match_score import match_score  # noqa: E402
from modules.generate_app import generate_app  # noqa: E402
from utils.io import read_json, write_json, ensure_dir  # noqa: E402


CONFIG_PATH = "tests/fixtures/config/applicant.yaml"
OUTPUT_DIR = "tests/fixtures/output"
LOGS_DIR = "tests/fixtures/logs"

REQUIRED_FILES = [
    "rob_profile.json",
    "profile_comparison.json",
    "source_inventory.json",
    "committee_review.json",
    "matched_jobs.json",
    "job_suggestions.json",
    "skill_assessment.json",
    "job_collection_summary.json",
    "derived_job_filters.json",
    "review_votes.json",
]

IGNORE_KEYS = {"generated_at", "updated_at"}
GOLDEN_DIR = "tests/golden_output"
GOLDEN_FILES = [
    "rob_profile.json",
    "profile_comparison.json",
    "source_inventory.json",
    "committee_review.json",
    "job_collection_summary.json",
    "derived_job_filters.json",
    "matched_jobs.json",
    "job_suggestions.json",
    "skill_assessment.json",
    "job_committee_review.json",
    "review_votes.json",
    "applications/application_1.json",
]
GOLDEN_BIN_HASHES = "binary_hashes.json"


def _reset_output_dirs():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    if os.path.exists(LOGS_DIR):
        shutil.rmtree(LOGS_DIR)
    ensure_dir(OUTPUT_DIR)
    ensure_dir(LOGS_DIR)


def _normalize(value):
    if isinstance(value, dict):
        return {key: _normalize(val) for key, val in value.items() if key not in IGNORE_KEYS}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _capture_snapshot():
    snapshot = {}
    for filename in REQUIRED_FILES:
        path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(path):
            raise AssertionError(f"Missing required output: {path}")
        snapshot[filename] = _normalize(read_json(path))
    app_path = os.path.join(OUTPUT_DIR, "applications", "application_1.json")
    if not os.path.exists(app_path):
        raise AssertionError(f"Missing application draft: {app_path}")
    snapshot["applications/application_1.json"] = _normalize(read_json(app_path))
    docx_path = os.path.join(OUTPUT_DIR, "applications", "application_1.docx")
    pdf_path = os.path.join(OUTPUT_DIR, "applications", "application_1.pdf")
    if not os.path.exists(docx_path):
        raise AssertionError(f"Missing application export: {docx_path}")
    if not os.path.exists(pdf_path):
        raise AssertionError(f"Missing application export: {pdf_path}")
    snapshot["applications/application_1.docx"] = _hash_file(docx_path)
    snapshot["applications/application_1.pdf"] = _hash_file(pdf_path)
    return snapshot


def _prepare_votes():
    matches_path = os.path.join(OUTPUT_DIR, "matched_jobs.json")
    matches = read_json(matches_path) if os.path.exists(matches_path) else []
    job_id = matches[0]["id"] if matches else "job-1"
    votes = {
        job_id: {
            "vote": "approve",
            "note": "smoke-test",
            "updated_at": "2020-01-01T00:00:00Z",
        }
    }
    write_json(votes, os.path.join(OUTPUT_DIR, "review_votes.json"))


def _hash_file(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _line_diff_count(a, b):
    diff = list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm=""))
    return sum(1 for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))), diff


def _compare_json(current_path, golden_path):
    current = _normalize(read_json(current_path))
    golden = _normalize(read_json(golden_path))
    current_text = json.dumps(current, sort_keys=True, indent=2)
    golden_text = json.dumps(golden, sort_keys=True, indent=2)
    if current_text == golden_text:
        return True, 0, []
    count, diff = _line_diff_count(current_text, golden_text)
    return False, count, diff


def _compare_to_golden():
    failures = []
    for filename in GOLDEN_FILES:
        current_path = os.path.join(OUTPUT_DIR, filename)
        golden_path = os.path.join(GOLDEN_DIR, filename)
        if not os.path.exists(golden_path):
            failures.append((filename, "missing golden"))
            continue
        if not os.path.exists(current_path):
            failures.append((filename, "missing current"))
            continue
        ok, count, _diff = _compare_json(current_path, golden_path)
        if not ok:
            failures.append((filename, f"{count} changed lines"))

    hashes_path = os.path.join(GOLDEN_DIR, GOLDEN_BIN_HASHES)
    if os.path.exists(hashes_path):
        hashes = read_json(hashes_path)
        for name, expected in hashes.items():
            current_path = os.path.join(OUTPUT_DIR, "applications", name)
            if not os.path.exists(current_path):
                failures.append((name, "missing current binary"))
                continue
            actual = _hash_file(current_path)
            if actual != expected:
                failures.append((name, "hash mismatch"))

    if failures:
        print("Golden comparison failed:")
        for filename, reason in failures:
            print(f"- {filename}: {reason}")
        return False
    print("Golden comparison passed.")
    return True


def _run_once():
    extract_profile(CONFIG_PATH)
    crawl_jobs(CONFIG_PATH)
    match_score(CONFIG_PATH)
    _prepare_votes()
    generate_app(CONFIG_PATH)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", action="store_true", help="Compare outputs to tests/golden_output")
    args = parser.parse_args()
    _reset_output_dirs()
    _run_once()
    snapshot_a = _capture_snapshot()
    _run_once()
    snapshot_b = _capture_snapshot()
    if json.dumps(snapshot_a, sort_keys=True) != json.dumps(snapshot_b, sort_keys=True):
        raise AssertionError("Smoke test failed: outputs are not deterministic.")
    if args.compare:
        if not _compare_to_golden():
            raise AssertionError("Smoke test failed: golden comparison mismatch.")
    print("Smoke tests passed.")


if __name__ == "__main__":
    main()
