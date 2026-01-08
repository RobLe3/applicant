import json
import os
import io
import zipfile
import base64
import hashlib
from datetime import datetime
EXPORT_FORMAT = "applicant-export-v1"

DEFAULT_CONFIG = {
    "paths": {
        "sources_dir": "Sources",
        "jobs_dir": "data/jobs",
        "output_dir": "data/output",
        "prompts_dir": "prompts",
        "logs_dir": "data/logs",
    },
    "profile": {
        "name": "Rob Mumin",
        "location": "",
        "email": "",
        "source_exclude": ["Sources/ICAR", "ICAR_"],
        "committee": {"min_score": 2},
    },
    "web_profile": {
        "enabled": True,
        "urls": ["https://roblemumin.com"],
        "allowed_domains": ["roblemumin.com"],
        "follow_library": True,
        "follow_patterns": ["library"],
        "max_pages": 5,
    },
    "language": {"default": "en", "supported": ["en", "de"]},
    "discovery": {"source_policy": {"mode": "advisory"}},
    "meta": {"version": "0.5.0-beta", "maturity_label": "beta", "maturity_score": 6.4},
    "matching": {
        "weights": {
            "skills": 0.4,
            "title": 0.2,
            "location": 0.1,
            "language": 0.1,
            "experience": 0.1,
            "alignment": 0.1,
        },
        "similarity": {
            "enabled": True,
            "threshold": 0.85,
        },
        "semantic": {
            "mode": "semantic",
            "backend": "hash",
            "model_path": "",
            "cache_path": "",
        },
        "top_n": 5,
        "min_score": 0.1,
        "apply_threshold": 0.25,
        "consider_threshold": 0.15,
        "region_keywords": ["EU", "Europe", "UK", "United Kingdom", "Germany", "Deutschland", "DE", "DACH"],
        "committee": {"min_score": 2},
        "feedback": {
            "enabled": False,
            "path": "",
            "weight": 0.05,
            "tag_weight": 0.05,
            "company_weight": 0.07,
            "min_samples": 2,
            "max_adjustment": 0.1,
        },
        "role_intent": {
            "enabled": True,
            "mismatch_penalty": 0.08,
            "alignment_bonus": 0.06,
            "execution_bonus": 0.0,
        },
        "recommendation_guard": {"enabled": True},
    },
    "scoring": {
        "active_preset": "balanced",
        "presets": {
            "balanced": {
                "label": "Balanced",
                "weights": {
                    "skills": 0.4,
                    "title": 0.2,
                    "location": 0.1,
                    "language": 0.1,
                    "experience": 0.1,
                    "alignment": 0.1,
                },
                "thresholds": {"apply": 0.25, "consider": 0.15},
            },
            "growth": {
                "label": "Growth",
                "weights": {
                    "skills": 0.35,
                    "title": 0.2,
                    "location": 0.05,
                    "language": 0.05,
                    "experience": 0.15,
                    "alignment": 0.2,
                },
                "thresholds": {"apply": 0.23, "consider": 0.12},
            },
            "stability": {
                "label": "Stability",
                "weights": {
                    "skills": 0.4,
                    "title": 0.2,
                    "location": 0.15,
                    "language": 0.1,
                    "experience": 0.1,
                    "alignment": 0.05,
                },
                "thresholds": {"apply": 0.26, "consider": 0.16},
            },
            "remote_first": {
                "label": "Remote-first",
                "weights": {
                    "skills": 0.35,
                    "title": 0.2,
                    "location": 0.2,
                    "language": 0.05,
                    "experience": 0.1,
                    "alignment": 0.1,
                },
                "thresholds": {"apply": 0.24, "consider": 0.14},
            },
        },
    },
    "job_sources": {
        "use_manual_files": True,
        "use_ats": True,
        "use_job_pages": False,
        "ats_companies": [],
        "job_pages": [],
        "fetch_timeout_seconds": 10,
        "max_per_company": 0,
        "max_total": 0,
    },
    "adapters": {
        "stepstone": {"enabled": True, "source_path": "data/jobs/stepstone_jobs.json", "max_total": 0},
        "linkedin": {"enabled": False, "source_path": "data/jobs/linkedin_jobs.json", "max_total": 0},
        "rss": {
            "enabled": False,
            "feeds": [
                {
                    "source_id": "reliefweb_consulting",
                    "feed_url": "https://reliefweb.int/jobs/rss.xml?search=consultant",
                    "company": "ReliefWeb",
                    "intent_label": "consulting_advisory",
                    "location": "Global",
                    "max_total": 50,
                    "rationale": "Consulting and advisory roles in humanitarian/public sector contexts.",
                },
                {
                    "source_id": "epso_public",
                    "feed_url": "https://epso.europa.eu/rss.xml",
                    "company": "EPSO",
                    "intent_label": "public_sector_defense",
                    "location": "EU",
                    "max_total": 50,
                    "rationale": "EU public sector roles with leadership/strategy relevance.",
                },
            ],
        },
    },
    "schedule": {"daily": False, "hour": 9, "frequency": "24h"},
    "job_filters": {
        "derived_enabled": True,
        "derived_max_keywords": 40,
        "include_keywords": [
            "ai",
            "machine learning",
            "ml",
            "security",
            "cybersecurity",
            "zero trust",
            "network security",
            "cloud security",
            "governance",
            "compliance",
            "risk",
            "privacy",
            "architecture",
            "platform",
            "infrastructure",
            "strategy",
            "consulting",
            "product",
            "data",
            "automation",
        ],
        "exclude_keywords": ["oil", "drilling", "rig", "petroleum", "offshore"],
        "location_allow": ["Europe", "EU", "United Kingdom", "UK", "Germany", "Deutschland", "DACH", "Remote", "Hybrid"],
        "location_block": ["Hong Kong", "China", "Singapore"],
    },
    "review": {"use_votes": True},
    "drafting": {
        "require_review": True,
        "max_skills_in_letter": 3,
        "attachments": ["rob_cv.pdf"],
        "letter_date": "",
        "role_families": ["engineering", "data", "strategy"],
        "default_role_family": "",
    },
    "submission": {
        "enabled": False,
        "mode": "draft",
        "smtp": {
            "enabled": False,
            "host": "127.0.0.1",
            "port": 1025,
        },
    },
    "db": {
        "enabled": True,
        "driver": "sqlite",
        "env": "dev",
        "path": "db/applicant.db",
        "dev_path": "db/applicant_dev.db",
    },
    "skills_seed": {
        "hard": ["AI", "ML", "NLP", "Python", "Strategy", "Consulting", "Data Analysis", "Product", "Cloud", "Automation"],
        "soft": ["Leadership", "Communication", "Stakeholder Management", "Problem Solving", "Teamwork"],
    },
}


def load_config(path):
    if not os.path.exists(path):
        return DEFAULT_CONFIG

    if path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    try:
        import yaml  # type: ignore
    except Exception:
        return DEFAULT_CONFIG

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or DEFAULT_CONFIG


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(data, path):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_text(text, path):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def log_message(logs_dir, task, message):
    ensure_dir(logs_dir)
    timestamp = datetime.utcnow().isoformat() + "Z"
    line = f"[{timestamp}] {message}\n"
    with open(os.path.join(logs_dir, f"{task}.log"), "a", encoding="utf-8") as f:
        f.write(line)


def _hash_file(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _collect_export_files(root_dir, include_sources=True):
    paths = [
        "config/applicant.yaml",
        "data/jobs",
        "data/output",
        "data/logs",
        "db",
    ]
    if include_sources:
        paths.append("Sources")
    files = []
    for rel in paths:
        full = os.path.join(root_dir, rel)
        if os.path.isdir(full):
            for base, _, filenames in os.walk(full):
                for name in filenames:
                    files.append(os.path.join(base, name))
        elif os.path.isfile(full):
            files.append(full)
    return files


def _build_manifest(root_dir, files):
    manifest = {"format": EXPORT_FORMAT, "generated_at": datetime.utcnow().isoformat() + "Z", "files": {}}
    entries = []
    for path in sorted(files):
        rel = os.path.relpath(path, root_dir)
        digest = _hash_file(path)
        size = os.path.getsize(path)
        manifest["files"][rel] = {"sha256": digest, "size": size}
        entries.append(f"{rel}:{digest}")
    manifest["root_hash"] = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest() if entries else ""
    return manifest


def _xor_bytes(data, key):
    if not key:
        return data
    key_bytes = key.encode("utf-8")
    return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))


def export_data(path, encrypted=True, include_sources=True):
    root_dir = os.getcwd()
    files = _collect_export_files(root_dir, include_sources=include_sources)
    manifest = _build_manifest(root_dir, files)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for file_path in files:
            rel = os.path.relpath(file_path, root_dir)
            zipf.write(file_path, rel)
    payload = buffer.getvalue()

    key = os.getenv("APPLICANT_EXPORT_KEY", "")
    if encrypted and key:
        encoded = base64.b64encode(_xor_bytes(payload, key)).decode("utf-8")
        wrapper = {
            "format": EXPORT_FORMAT,
            "encrypted": True,
            "encryption": "xor",
            "root_hash": manifest.get("root_hash"),
            "files": manifest.get("files"),
            "payload": encoded,
        }
        write_json(wrapper, path)
        return path

    with open(path, "wb") as f:
        f.write(payload)
    return path


def import_data(path, require_confirm=True):
    if require_confirm and os.getenv("APPLICANT_IMPORT_CONFIRM", "").lower() not in {"1", "true", "yes"}:
        raise ValueError("Import requires confirmation. Set APPLICANT_IMPORT_CONFIRM=true.")

    root_dir = os.getcwd()
    data = None
    if path.endswith(".json"):
        try:
            data = read_json(path)
        except Exception:
            data = None

    if isinstance(data, dict) and data.get("format") == EXPORT_FORMAT:
        if data.get("encrypted"):
            key = os.getenv("APPLICANT_EXPORT_KEY", "")
            if not key:
                raise ValueError("Missing APPLICANT_EXPORT_KEY for encrypted import.")
            payload = base64.b64decode(data.get("payload", ""))
            payload = _xor_bytes(payload, key)
        else:
            payload = base64.b64decode(data.get("payload", ""))
        buffer = io.BytesIO(payload)
        manifest = {"files": data.get("files", {}), "root_hash": data.get("root_hash", "")}
    else:
        with open(path, "rb") as f:
            payload = f.read()
        buffer = io.BytesIO(payload)
        manifest = None

    with zipfile.ZipFile(buffer, "r") as zipf:
        if manifest is None:
            manifest_data = json.loads(zipf.read("manifest.json").decode("utf-8"))
            manifest = manifest_data
        files = manifest.get("files") or {}
        entries = []
        for rel, info in files.items():
            payload = zipf.read(rel)
            digest = hashlib.sha256(payload).hexdigest()
            if digest != info.get("sha256"):
                raise ValueError(f"Hash mismatch for {rel}")
            entries.append(f"{rel}:{digest}")
        root_hash = hashlib.sha256("\n".join(sorted(entries)).encode("utf-8")).hexdigest() if entries else ""
        if manifest.get("root_hash") and root_hash != manifest.get("root_hash"):
            raise ValueError("Root hash mismatch")

        for rel in files:
            target = os.path.join(root_dir, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if os.path.exists(target) and os.getenv("APPLICANT_IMPORT_OVERWRITE", "").lower() not in {"1", "true", "yes"}:
                continue
            with open(target, "wb") as f:
                f.write(zipf.read(rel))
    return True
