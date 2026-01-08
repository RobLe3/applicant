import os
import re
from datetime import datetime

from utils.io import read_json, write_json, ensure_dir

POSITIVE_OUTCOMES = {"accepted", "interview"}
NEGATIVE_OUTCOMES = {"rejected", "no_response"}
ALL_OUTCOMES = POSITIVE_OUTCOMES | NEGATIVE_OUTCOMES


def _slug(value):
    if not value:
        return ""
    text = re.sub(r"[^a-z0-9]+", "_", str(value).lower())
    return text.strip("_")


def load_feedback(path):
    if os.path.exists(path):
        data = read_json(path)
        if isinstance(data, dict) and isinstance(data.get("outcomes"), list):
            data.setdefault("adjustment_history", [])
            data.setdefault("rollbacks", [])
            return data
    return {"outcomes": [], "adjustment_history": [], "rollbacks": []}


def write_feedback(path, data):
    ensure_dir(os.path.dirname(path))
    write_json(data, path)


def build_feedback_tags(job, job_facts):
    tags = []
    company = _slug(job.get("company"))
    if company:
        tags.append(f"company:{company}")
    seniority = job_facts.get("seniority")
    if seniority:
        tags.append(f"seniority:{seniority}")
    contract_type = job_facts.get("contract_type")
    if contract_type:
        tags.append(f"contract:{contract_type}")
    work_mode = job_facts.get("work_mode")
    if work_mode:
        tags.append(f"work_mode:{work_mode}")
    language = job.get("language")
    if language:
        tags.append(f"language:{_slug(language)}")
    return list(dict.fromkeys(tags))


def record_outcome(path, job_id, outcome, tags, job_meta=None, note=None):
    if outcome not in ALL_OUTCOMES:
        raise ValueError("Invalid outcome")
    data = load_feedback(path)
    outcome_id = f"{_slug(job_id) or 'job'}-{len(data.get('outcomes', [])) + 1}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    entry = {
        "outcome_id": outcome_id,
        "job_id": job_id,
        "outcome": outcome,
        "tags": tags or [],
        "note": note or "",
        "job": job_meta or {},
        "recorded_at": datetime.utcnow().isoformat() + "Z",
    }
    data["outcomes"].append(entry)
    history = data.get("adjustment_history") or []
    history.append(
        {
            "outcome_id": outcome_id,
            "job_id": job_id,
            "tags": tags or [],
            "recorded_at": entry["recorded_at"],
            "active": True,
        }
    )
    data["adjustment_history"] = history
    write_feedback(path, data)
    return entry


def record_adjustment_rollback(path, outcome_id, reason=""):
    data = load_feedback(path)
    rollbacks = data.get("rollbacks") or []
    rollbacks.append(
        {
            "outcome_id": outcome_id,
            "reason": reason,
            "rolled_back_at": datetime.utcnow().isoformat() + "Z",
        }
    )
    data["rollbacks"] = rollbacks
    history = data.get("adjustment_history") or []
    for entry in history:
        if entry.get("outcome_id") == outcome_id:
            entry["active"] = False
            entry["rolled_back_at"] = datetime.utcnow().isoformat() + "Z"
    data["adjustment_history"] = history
    write_feedback(path, data)
    return rollbacks[-1]


def build_tag_stats(outcomes, rollbacks=None):
    stats = {}
    rolled_back = {item.get("outcome_id") for item in (rollbacks or []) if item.get("outcome_id")}
    for entry in outcomes or []:
        if entry.get("outcome_id") in rolled_back:
            continue
        outcome = entry.get("outcome")
        tags = entry.get("tags") or []
        for tag in tags:
            stat = stats.setdefault(tag, {"positive": 0, "negative": 0, "total": 0})
            if outcome in POSITIVE_OUTCOMES:
                stat["positive"] += 1
            elif outcome in NEGATIVE_OUTCOMES:
                stat["negative"] += 1
            stat["total"] += 1
    return stats


def score_adjustment(tags, stats, weight=0.05, min_samples=2, max_adjustment=0.1, tag_weight=None, company_weight=None):
    if not tags or not stats:
        return 0.0, []
    tag_weight = weight if tag_weight is None else tag_weight
    company_weight = weight if company_weight is None else company_weight

    def compute_adjustment(tag_list, weight_value, prefix):
        signals = []
        used_tags = []
        for tag in tag_list:
            stat = stats.get(tag)
            if not stat or stat.get("total", 0) < min_samples:
                continue
            total = stat.get("total", 0)
            signal = (stat.get("positive", 0) - stat.get("negative", 0)) / total if total else 0.0
            signals.append(signal)
            used_tags.append(tag)
        if not signals:
            return 0.0, []
        adjustment = (sum(signals) / len(signals)) * weight_value
        audit = []
        for tag in used_tags:
            if prefix == "company" and tag.startswith("company:"):
                audit.append(f"feedback:{prefix}:{tag.split('company:', 1)[1]}")
            else:
                audit.append(f"feedback:{prefix}:{tag}")
        return adjustment, audit

    company_tags = [tag for tag in tags if tag.startswith("company:")]
    other_tags = [tag for tag in tags if not tag.startswith("company:")]

    company_adjust, company_audit = compute_adjustment(company_tags, company_weight, "company")
    tag_adjust, tag_audit = compute_adjustment(other_tags, tag_weight, "tag")
    total_adjust = company_adjust + tag_adjust
    total_adjust = max(-max_adjustment, min(max_adjustment, total_adjust))
    return total_adjust, company_audit + tag_audit


def latest_outcomes_by_job(outcomes):
    latest = {}
    for entry in outcomes or []:
        job_id = entry.get("job_id")
        if not job_id:
            continue
        current = latest.get(job_id)
        if not current or entry.get("recorded_at", "") > current.get("recorded_at", ""):
            latest[job_id] = entry
    return latest
