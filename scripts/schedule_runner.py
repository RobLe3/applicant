import argparse
import os
import platform
import subprocess
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from utils.io import load_config  # noqa: E402


def _parse_frequency(value):
    if not value:
        return 86400
    text = str(value).strip().lower()
    if text.endswith("h"):
        return int(float(text[:-1]) * 3600)
    if text.endswith("m"):
        return int(float(text[:-1]) * 60)
    return int(float(text))


def _build_launchd_plist(python_path, script_path, schedule):
    label = "com.applicant.scheduler"
    hour = schedule.get("hour", 9)
    daily = bool(schedule.get("daily", False))
    frequency = schedule.get("frequency")
    start_interval = None
    if not daily:
        start_interval = _parse_frequency(frequency)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
        "<plist version=\"1.0\">",
        "<dict>",
        f"  <key>Label</key><string>{label}</string>",
        "  <key>ProgramArguments</key>",
        "  <array>",
        f"    <string>{python_path}</string>",
        f"    <string>{script_path}</string>",
        "  </array>",
        "  <key>RunAtLoad</key><true/>",
    ]
    if daily:
        lines.extend(
            [
                "  <key>StartCalendarInterval</key>",
                "  <dict>",
                f"    <key>Hour</key><integer>{hour}</integer>",
                "  </dict>",
            ]
        )
    else:
        lines.extend([f"  <key>StartInterval</key><integer>{start_interval}</integer>"])
    lines.extend(["</dict>", "</plist>"])
    return "\n".join(lines)


def _build_cron_line(python_path, script_path, schedule):
    hour = schedule.get("hour", 9)
    daily = bool(schedule.get("daily", False))
    frequency = schedule.get("frequency")
    if daily:
        return f"0 {hour} * * * {python_path} {script_path}"
    interval_hours = max(1, int(_parse_frequency(frequency) / 3600))
    return f"0 */{interval_hours} * * * {python_path} {script_path}"


def _write_file(path, content, dry_run):
    if dry_run:
        print(f"[dry-run] Would write {path}")
        print(content)
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _install_launchd(plist_path, dry_run):
    if dry_run:
        print(f"[dry-run] launchctl load {plist_path}")
        return
    subprocess.run(["launchctl", "load", plist_path], check=False)


def _install_cron(cron_path, dry_run):
    if dry_run:
        print(f"[dry-run] crontab {cron_path}")
        return
    subprocess.run(["crontab", cron_path], check=False)


def _run_now(python_path, script_path):
    print(f"Running pipeline now ({datetime.utcnow().isoformat()}Z)")
    subprocess.run([python_path, script_path], check=False)


def main():
    parser = argparse.ArgumentParser(description="Set up a local scheduler for the Applicant pipeline.")
    parser.add_argument("--config", default="config/applicant.yaml")
    parser.add_argument("--apply", action="store_true", help="Install schedule into launchd/cron")
    parser.add_argument("--dry-run", action="store_true", help="Show schedule without installing")
    parser.add_argument("--now", action="store_true", help="Run pipeline immediately")
    args = parser.parse_args()

    dry_run = args.dry_run or not args.apply
    config = load_config(args.config)
    schedule = config.get("schedule", {}) or {}

    python_path = sys.executable
    script_path = os.path.join(REPO_ROOT, "scripts", "run_pipeline.py")
    platform_name = platform.system().lower()

    if "darwin" in platform_name:
        plist = _build_launchd_plist(python_path, script_path, schedule)
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.applicant.scheduler.plist")
        _write_file(plist_path, plist, dry_run)
        if args.apply:
            _install_launchd(plist_path, dry_run)
    elif "linux" in platform_name:
        cron_line = _build_cron_line(python_path, script_path, schedule)
        cron_path = os.path.expanduser("~/.config/applicant/cron.job")
        _write_file(cron_path, cron_line + "\n", dry_run)
        if args.apply:
            _install_cron(cron_path, dry_run)
    else:
        print("Unsupported platform for scheduler setup.")
        return

    if args.now:
        _run_now(python_path, script_path)


if __name__ == "__main__":
    main()
