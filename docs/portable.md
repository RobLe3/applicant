# Portable Setup and Migration
Release: v0.5 beta (maturity score: 6.4/10)

This guide helps bootstrap a local data layout or migrate data into a new repository checkout.

## One-command setup
```
python scripts/portable_init.py
```

This creates the expected local folders:
- `data/jobs`
- `data/output`
- `data/logs`
- `db`
- `Sources`

It will also copy `config/applicant.yaml` if it does not exist.

## Migrate from an existing repo
```
python scripts/portable_init.py --migrate-from /path/to/old/repo
```

## Symlink instead of copy
```
python scripts/portable_init.py --migrate-from /path/to/old/repo --symlink
```

## Dry run
```
python scripts/portable_init.py --dry-run
```
