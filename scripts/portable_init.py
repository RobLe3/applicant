import argparse
import os
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)


DEFAULT_DIRS = [
    "data/jobs",
    "data/output",
    "data/logs",
    "db",
    "Sources",
]


def _ensure_dirs(root, rel_dirs, dry_run=False):
    for rel in rel_dirs:
        path = os.path.join(root, rel)
        if dry_run:
            print(f"[dry-run] mkdir -p {path}")
            continue
        os.makedirs(path, exist_ok=True)


def _copy_config(template_path, dest_path, dry_run=False):
    if os.path.exists(dest_path):
        print(f"Config exists: {dest_path}")
        return
    if dry_run:
        print(f"[dry-run] copy {template_path} -> {dest_path}")
        return
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copy2(template_path, dest_path)
    print(f"Copied config to {dest_path}")


def _migrate_dir(src, dest, use_symlink=False, dry_run=False):
    if not os.path.exists(src):
        print(f"Skip missing: {src}")
        return
    if os.path.exists(dest):
        print(f"Destination exists, skipping: {dest}")
        return
    if dry_run:
        action = "symlink" if use_symlink else "copy"
        print(f"[dry-run] {action} {src} -> {dest}")
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if use_symlink:
        os.symlink(src, dest)
    else:
        shutil.copytree(src, dest)
    print(f"Migrated {src} -> {dest}")


def main():
    parser = argparse.ArgumentParser(description="Initialize a portable Applicant data layout.")
    parser.add_argument("--root", default=REPO_ROOT)
    parser.add_argument("--config-template", default=os.path.join(REPO_ROOT, "config", "applicant.yaml"))
    parser.add_argument("--config-dest", default=os.path.join(REPO_ROOT, "config", "applicant.yaml"))
    parser.add_argument("--migrate-from", default="")
    parser.add_argument("--symlink", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.root
    _ensure_dirs(root, DEFAULT_DIRS, dry_run=args.dry_run)
    _copy_config(args.config_template, args.config_dest, dry_run=args.dry_run)

    if args.migrate_from:
        for rel in DEFAULT_DIRS:
            src = os.path.join(args.migrate_from, rel)
            dest = os.path.join(root, rel)
            _migrate_dir(src, dest, use_symlink=args.symlink, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
