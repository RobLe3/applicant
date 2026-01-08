import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from utils.io import load_config, write_json, read_json  # noqa: E402
from scripts.serve_web import _build_ui_snapshot  # noqa: E402


def _line_diff_count(a, b):
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    max_len = max(len(a_lines), len(b_lines))
    changes = 0
    for idx in range(max_len):
        left = a_lines[idx] if idx < len(a_lines) else ""
        right = b_lines[idx] if idx < len(b_lines) else ""
        if left != right:
            changes += 1
    return changes


def main():
    parser = argparse.ArgumentParser(description="Capture or compare UI snapshot output.")
    parser.add_argument("--config", default="config/applicant.yaml")
    parser.add_argument("--output", default="tests/ui_snapshots/ui_snapshot.json")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--baseline", default="tests/ui_snapshots/ui_snapshot.json")
    args = parser.parse_args()

    config = load_config(args.config)
    snapshot = _build_ui_snapshot(config)

    output_path = args.output
    if args.compare and os.path.abspath(output_path) == os.path.abspath(args.baseline):
        output_path = "tests/ui_snapshots/current_snapshot.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    write_json(snapshot, output_path)
    print(f"Wrote snapshot to {output_path}")

    if args.compare:
        if not os.path.exists(args.baseline):
            raise SystemExit(f"Baseline snapshot missing: {args.baseline}")
        baseline = read_json(args.baseline)
        current_text = json.dumps(snapshot, sort_keys=True, indent=2)
        baseline_text = json.dumps(baseline, sort_keys=True, indent=2)
        if current_text == baseline_text:
            print("UI snapshot comparison passed.")
            return
        diff_count = _line_diff_count(current_text, baseline_text)
        print(f"UI snapshot comparison failed: {diff_count} changed lines")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
