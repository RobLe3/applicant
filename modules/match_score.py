import os
import re

from utils.io import load_config, read_json, write_json, log_message
from utils.db import db_enabled, init_db, upsert_job_state
from utils.vectorizer import jaccard_similarity, semantic_similarity, SemanticEmbedder, cluster_texts
from utils.feedback import load_feedback, build_tag_stats, build_feedback_tags, score_adjustment
from utils.translator import detect_language
from modules.extract_profile import (  # noqa: E402
    _extract_skills,
    _extract_skill_lists,
    _build_skill_weighting,
    _build_role_abstractions,
)


def _text_from_profile(profile):
    parts = []
    parts.extend(profile.get("hard_skills", []))
    parts.extend(profile.get("soft_skills", []))
    parts.extend([e.get("summary", "") for e in profile.get("experience", [])])
    parts.extend([p.get("summary", "") for p in profile.get("projects", [])])
    return " ".join([p for p in parts if p])


ROLE_INTENT_ORDER = [
    "executive_strategy",
    "principal_architecture",
    "consulting_leadership",
    "engineering_execution",
]
ROLE_INTENT_LEADERSHIP = {"executive_strategy", "principal_architecture", "consulting_leadership"}
SALES_GUARD_PATTERNS = [
    r"\baccount executive\b",
    r"\baccount manager\b",
    r"\bsales ops\b",
    r"\bsales operations\b",
    r"\bbusiness development\b",
    r"\bquota\b",
    r"\bsdr\b",
    r"\bbdr\b",
    r"\bsales(?!force)\b",
]


def _job_intent_tags(job):
    title = job.get("title", "") or ""
    description = job.get("description", "") or ""
    text = f"{title} {description}".lower()
    tags = set()
    if re.search(r"\bdirector\b|\bhead\b|\bvp\b|vice president|\bchief\b|\bexecutive\b|\bstrategy\b", text):
        tags.add("executive_strategy")
    if re.search(r"\barchitect\b|\barchitecture\b|solution architect|enterprise architect|platform architect", text):
        tags.add("principal_architecture")
    if re.search(r"\bconsultant\b|\bconsulting\b|\badvisory\b|\badvisor\b|pre-?sales|\bpartner\b|\bclient\b", text):
        tags.add("consulting_leadership")
    if re.search(
        r"\bengineer\b|\bdeveloper\b|\bscientist\b|data engineer|ml engineer|\bbackend\b|\bfrontend\b|full stack|\bswe\b|\bdevops\b|\bsre\b",
        text,
    ):
        tags.add("engineering_execution")
    return tags


def _primary_job_track(tags):
    for label in ROLE_INTENT_ORDER:
        if label in tags:
            return label
    return "unspecified"


def _sales_guard_hit(title):
    text = (title or "").lower()
    for pattern in SALES_GUARD_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _split_sentences(text):
    sentences = re.split(r"[.!?]+", text or "")
    return [s.strip() for s in sentences if s.strip()]


def _extract_pay_unit(text, start, end):
    window = (text or "")[end : end + 80].lower()
    if any(token in window for token in ["per year", "per annum", "/year", "/yr", "yearly"]):
        return " per year"
    if any(token in window for token in ["per hour", "/hour", "/hr", "hourly"]):
        return " per hour"
    if any(token in window for token in ["per day", "/day", "daily"]):
        return " per day"
    if any(token in window for token in ["per month", "/month", "monthly"]):
        return " per month"
    return ""


def _normalize_amount(raw):
    return (raw or "").strip()


def _extract_compensation(text):
    if not text:
        return ""
    currency = r"(?:USD|EUR|GBP|CHF|CAD|AUD|NZD|SGD|HKD|JPY|CNY|INR|SEK|NOK|DKK|PLN|CZK|BRL|MXN|\$|\u20ac|\u00a3)"
    amount = r"\d{2,3}(?:[.,]\d{3})*(?:\s?[kK])?"
    range_pattern = re.compile(
        rf"(?P<currency>{currency})\s*(?P<min>{amount})\s*(?:-|to|\u2013|\u2014)\s*(?P<currency2>{currency})?\s*(?P<max>{amount})",
        re.IGNORECASE,
    )
    match = range_pattern.search(text)
    if match:
        unit = _extract_pay_unit(text, match.start(), match.end())
        min_amt = _normalize_amount(match.group("min"))
        max_amt = _normalize_amount(match.group("max"))
        return f"{match.group('currency')} {min_amt} - {max_amt}{unit}".strip()

    single_pattern = re.compile(rf"(?P<currency>{currency})\s*(?P<amount>{amount})", re.IGNORECASE)
    match = single_pattern.search(text)
    if match:
        unit = _extract_pay_unit(text, match.start(), match.end())
        amt = _normalize_amount(match.group("amount"))
        return f"{match.group('currency')} {amt}{unit}".strip()
    return ""


def _detect_seniority(text):
    if not text:
        return ""
    rules = [
        ("c_level", ["chief", "c-level", "cto", "cio", "ciso", "ceo", "coo", "cpo"]),
        ("vp", ["vp", "vice president"]),
        ("director", ["director", "head of"]),
        ("principal", ["principal", "staff"]),
        ("lead", ["lead", "leader"]),
        ("senior", ["senior", "sr.", "sr "]),
        ("mid", ["mid", "mid-level", "mid level"]),
        ("junior", ["junior", "jr.", "jr "]),
        ("intern", ["intern", "internship"]),
    ]
    low = text.lower()
    for label, tokens in rules:
        if any(token in low for token in tokens):
            return label
    return ""


def _detect_contract_type(text):
    if not text:
        return ""
    rules = [
        ("full_time", ["full-time", "full time", "fulltime"]),
        ("part_time", ["part-time", "part time", "parttime"]),
        ("contract", ["contract", "contractor", "fixed-term", "fixed term"]),
        ("freelance", ["freelance"]),
        ("internship", ["intern", "internship"]),
        ("temporary", ["temporary", "temp"]),
    ]
    low = text.lower()
    for label, tokens in rules:
        if any(token in low for token in tokens):
            return label
    return ""


def _detect_benefits(text):
    if not text:
        return []
    rules = {
        "health": ["health insurance", "medical insurance", "healthcare", "medical plan"],
        "pension": ["pension", "retirement", "401k", "401(k)"],
        "equity": ["equity", "stock", "stock options", "esop", "rsu"],
        "bonus": ["bonus", "performance bonus", "annual bonus"],
        "relocation": ["relocation", "relocate"],
        "visa": ["visa sponsorship", "work visa", "sponsorship"],
        "training": ["training", "learning budget", "education budget", "conference"],
        "wellness": ["wellness", "gym", "fitness"],
        "pto": ["pto", "paid time off", "vacation", "holiday"],
    }
    low = text.lower()
    hits = []
    for label, tokens in rules.items():
        if any(token in low for token in tokens):
            hits.append(label)
    return hits


def _detect_work_mode(text, location_text):
    low = text.lower()
    loc = location_text.lower()
    if "hybrid" in low or "hybrid" in loc:
        return "hybrid"
    if "remote" in low or "remote" in loc or "telecommute" in low:
        return "remote"
    if any(token in low for token in ["on-site", "onsite", "in-office", "in office", "office-based"]):
        return "on_site"
    return ""


def _extract_job_facts(job):
    description = job.get("description", "") or ""
    title = job.get("title", "") or ""
    location = job.get("location", "") or ""
    text = f"{title}\\n{description}".lower()
    location_text = location.lower()

    work_mode = _detect_work_mode(text, location_text)
    workplace = (
        "Remote" if work_mode == "remote" else "Hybrid" if work_mode == "hybrid" else "On-site" if work_mode == "on_site" else ""
    )
    contract_type = _detect_contract_type(text)
    employment_type = (
        "Full-time"
        if contract_type == "full_time"
        else "Part-time"
        if contract_type == "part_time"
        else "Contract"
        if contract_type == "contract"
        else "Temporary"
        if contract_type == "temporary"
        else "Internship"
        if contract_type == "internship"
        else "Freelance"
        if contract_type == "freelance"
        else ""
    )

    compensation = _extract_compensation(description)
    seniority = _detect_seniority(title) or _detect_seniority(description)
    benefits = _detect_benefits(description)

    return {
        "location": location.strip(),
        "workplace": workplace,
        "work_mode": work_mode,
        "employment_type": employment_type,
        "contract_type": contract_type,
        "compensation": compensation,
        "seniority": seniority,
        "benefits": benefits,
    }


def _atomize_profile(profile):
    items = []
    evidence = profile.get("evidence", {})

    for skill in profile.get("hard_skills", []):
        items.append({"type": "skill", "label": skill, "text": evidence.get(skill, skill)})
    for skill in profile.get("soft_skills", []):
        items.append({"type": "skill", "label": skill, "text": evidence.get(skill, skill)})

    for entry in profile.get("experience", []):
        for sentence in _split_sentences(entry.get("summary", "")):
            items.append({"type": "experience", "label": "experience", "text": sentence})

    for entry in profile.get("projects", []):
        for sentence in _split_sentences(entry.get("summary", "")):
            items.append({"type": "project", "label": "project", "text": sentence})

    for entry in profile.get("education", []):
        for sentence in _split_sentences(entry.get("summary", "")):
            items.append({"type": "education", "label": "education", "text": sentence})

    return items


def _extract_requirements(description):
    if not description:
        return []
    lines = [line.strip(" -*\t") for line in description.splitlines() if line.strip()]
    keywords = [
        "must",
        "required",
        "requirements",
        "experience",
        "skills",
        "ability",
        "knowledge",
        "proficiency",
        "background",
        "familiarity",
        "responsibilities",
        "you will",
        "you'll",
    ]

    candidates = []
    for line in lines:
        low = line.lower()
        if any(k in low for k in keywords):
            candidates.append(line)

    if not candidates:
        candidates = _split_sentences(description)[:10]

    deduped = []
    seen = set()
    for item in candidates:
        norm = item.lower()
        if norm not in seen and len(item) > 4:
            seen.add(norm)
            deduped.append(item)
    return deduped[:10]


def _match_requirements(requirements, evidence_items):
    if not requirements:
        return [], 0.0, []

    requirement_rows = []
    matched_count = 0
    for req in requirements:
        matches = []
        for item in evidence_items:
            score = jaccard_similarity(req, item.get("text", ""))
            if score >= 0.1:
                matches.append(
                    {
                        "type": item.get("type"),
                        "label": item.get("label"),
                        "text": item.get("text"),
                        "score": round(score, 4),
                    }
                )
        matches.sort(key=lambda x: x["score"], reverse=True)
        top_matches = matches[:3]
        if top_matches:
            matched_count += 1
            status = "matched"
        else:
            status = "gap"
        requirement_rows.append(
            {
                "requirement": req,
                "status": status,
                "matches": top_matches,
            }
        )

    coverage = matched_count / len(requirements) if requirements else 0.0
    gaps = [row["requirement"] for row in requirement_rows if row["status"] == "gap"]
    return requirement_rows, coverage, gaps


def _location_score(location, region_keywords):
    if not location:
        return 0.0
    low = location.lower()
    for keyword in region_keywords:
        if keyword.lower() in low:
            return 1.0
    return 0.0


def _build_suggestions(results, top_n):
    suggestions = []
    for match in results[:top_n]:
        job = match.get("job", {})
        qualification = match.get("qualification", {})
        alignment = match.get("alignment", {})
        suggestions.append(
            {
                "id": match.get("id"),
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "url": job.get("url", ""),
                "score": match.get("score", 0.0),
                "alignment": alignment.get("alignment_score", 0.0),
                "recommendation": match.get("recommendation", ""),
                "coverage": qualification.get("coverage", 0.0),
                "top_gaps": (qualification.get("gaps") or [])[:3],
            }
        )
    return suggestions


def _summarize_skill_assessment(results, profile):
    gap_counts = {}
    coverage_values = []
    scores = []
    recommendation_counts = {"apply": 0, "consider": 0, "skip": 0}
    total_requirements = 0
    matched_requirements = 0

    for match in results:
        score = match.get("score")
        if isinstance(score, (int, float)):
            scores.append(score)
        recommendation = match.get("recommendation")
        if recommendation in recommendation_counts:
            recommendation_counts[recommendation] += 1

        qualification = match.get("qualification") or {}
        coverage = qualification.get("coverage")
        if isinstance(coverage, (int, float)):
            coverage_values.append(coverage)

        requirements = qualification.get("requirements") or []
        total_requirements += len(requirements)
        matched_requirements += sum(1 for row in requirements if row.get("status") == "matched")

        for gap in qualification.get("gaps") or []:
            gap_counts[gap] = gap_counts.get(gap, 0) + 1

    avg_score = sum(scores) / len(scores) if scores else 0.0
    avg_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
    req_coverage = matched_requirements / total_requirements if total_requirements else 0.0

    top_gaps = [
        {"gap": gap, "count": count} for gap, count in sorted(gap_counts.items(), key=lambda x: (-x[1], x[0]))
    ]

    summary = {
        "total_jobs": len(results),
        "avg_score": round(avg_score, 4),
        "avg_coverage": round(avg_coverage, 4),
        "requirements": {
            "total": total_requirements,
            "matched": matched_requirements,
            "coverage": round(req_coverage, 4),
        },
        "recommendations": recommendation_counts,
        "top_gaps": top_gaps[:10],
    }

    if profile:
        weighting = profile.get("skill_weighting", {})
        entries = weighting.get("entries", []) or []
        entries = [entry for entry in entries if entry.get("committee", {}).get("decision") == "accept"]
        if entries:
            summary["skill_weighting"] = {
                "major": [
                    {
                        "skill": entry.get("skill"),
                        "type": entry.get("type"),
                        "weight": entry.get("weight"),
                        "mentions": entry.get("mentions"),
                    }
                    for entry in entries
                    if entry.get("level") == "major"
                ][:8],
                "median": [
                    {
                        "skill": entry.get("skill"),
                        "type": entry.get("type"),
                        "weight": entry.get("weight"),
                        "mentions": entry.get("mentions"),
                    }
                    for entry in entries
                    if entry.get("level") == "median"
                ][:8],
                "minor": [
                    {
                        "skill": entry.get("skill"),
                        "type": entry.get("type"),
                        "weight": entry.get("weight"),
                        "mentions": entry.get("mentions"),
                    }
                    for entry in entries
                    if entry.get("level") == "minor"
                ][:8],
            }

        abstractions = profile.get("role_abstractions", {})
        capabilities = abstractions.get("capabilities", []) or []
        traits = abstractions.get("traits", []) or []
        if capabilities or traits:
            summary["role_abstractions"] = {
                "capabilities": [
                    {
                        "label": item.get("category"),
                        "level": item.get("level"),
                        "weight": item.get("weight"),
                        "skills": [s.get("skill") for s in (item.get("supporting_skills") or [])[:4]],
                    }
                    for item in capabilities
                ][:6],
                "traits": [
                    {
                        "label": item.get("trait"),
                        "level": item.get("level"),
                        "weight": item.get("weight"),
                        "skills": [s.get("skill") for s in (item.get("supporting_skills") or [])[:4]],
                    }
                    for item in traits
                ][:6],
            }

    return summary


def _load_committee_votes(path):
    if os.path.exists(path):
        try:
            return read_json(path)
        except Exception:
            return {}
    return {}


def _normalize_skill_key(skill):
    return re.sub(r"\s+", " ", (skill or "").lower()).strip()


def _accepted_entries(weighting):
    return [entry for entry in (weighting.get("entries") or []) if entry.get("committee", {}).get("decision") == "accept"]


def _filter_weighting(weighting):
    entries = _accepted_entries(weighting)
    tiers = {"major": [], "median": [], "minor": []}
    for entry in entries:
        level = entry.get("level")
        if level in tiers:
            tiers[level].append(entry.get("skill"))
    return {
        "entries": entries,
        "tiers": tiers,
        "notes": weighting.get("notes"),
    }


def _filter_abstractions(abstractions):
    capabilities = [item for item in (abstractions.get("capabilities") or []) if item.get("decision") == "accept"]
    traits = [item for item in (abstractions.get("traits") or []) if item.get("decision") == "accept"]
    return {
        "capabilities": capabilities,
        "traits": traits,
        "notes": abstractions.get("notes"),
    }


def _collect_committee_review(skill_weighting, role_abstractions):
    held_skills = []
    for entry in skill_weighting.get("entries") or []:
        committee = entry.get("committee", {})
        if committee.get("decision") == "hold":
            held_skills.append(
                {
                    "skill": entry.get("skill"),
                    "type": entry.get("type"),
                    "mentions": entry.get("mentions"),
                    "weight": entry.get("weight"),
                    "committee": committee,
                }
            )

    held_abstractions = role_abstractions.get("held", []) or []
    if not held_skills and not held_abstractions:
        return {}
    return {
        "skills": held_skills,
        "abstractions": held_abstractions,
        "action": "agent_review",
        "notes": "Held items require agent review before use in scoring.",
    }


def _build_job_analysis(text, config, overrides=None):
    hard, soft = _extract_skill_lists(text, config)
    hard = list(dict.fromkeys(hard))
    soft = list(dict.fromkeys(soft))
    seed_hard, seed_soft, evidence = _extract_skills(text, config.get("skills_seed", {}))
    for skill in seed_hard:
        if skill not in hard:
            hard.append(skill)
    for skill in seed_soft:
        if skill not in soft:
            soft.append(skill)

    job_profile = {"hard_skills": hard, "soft_skills": soft, "evidence": evidence}
    committee_cfg = config.get("matching", {}).get("committee", {})
    weighting = _build_skill_weighting(job_profile, text, config, committee_cfg=committee_cfg, overrides=overrides)
    abstractions = _build_role_abstractions(weighting, overrides=overrides)
    committee_review = _collect_committee_review(weighting, abstractions)
    return {
        "skill_weighting": _filter_weighting(weighting),
        "role_abstractions": _filter_abstractions(abstractions),
        "committee_review": committee_review,
    }


def _weighted_overlap(profile_map, job_map):
    overlap_keys = set(profile_map.keys()) & set(job_map.keys())
    profile_total = sum(profile_map.values()) if profile_map else 0.0
    job_total = sum(job_map.values()) if job_map else 0.0
    profile_overlap = sum(profile_map[key] for key in overlap_keys) if profile_total else 0.0
    job_overlap = sum(job_map[key] for key in overlap_keys) if job_total else 0.0
    profile_coverage = profile_overlap / profile_total if profile_total else 0.0
    job_coverage = job_overlap / job_total if job_total else 0.0
    return {
        "overlap": sorted(overlap_keys),
        "profile_coverage": round(profile_coverage, 4),
        "job_coverage": round(job_coverage, 4),
    }


def _compute_alignment(profile_weighting, job_weighting, profile_abstractions, job_abstractions):
    profile_entries = _accepted_entries(profile_weighting)
    job_entries = _accepted_entries(job_weighting)

    profile_map = {_normalize_skill_key(entry.get("skill")): entry.get("weight", 0.0) for entry in profile_entries}
    job_map = {_normalize_skill_key(entry.get("skill")): entry.get("weight", 0.0) for entry in job_entries}
    skill_overlap = _weighted_overlap(profile_map, job_map)

    profile_caps = {
        _normalize_skill_key(item.get("category")): item.get("weight", 0.0)
        for item in profile_abstractions.get("capabilities") or []
        if item.get("decision") == "accept"
    }
    job_caps = {
        _normalize_skill_key(item.get("category")): item.get("weight", 0.0)
        for item in job_abstractions.get("capabilities") or []
        if item.get("decision") == "accept"
    }
    capability_overlap = _weighted_overlap(profile_caps, job_caps)

    profile_traits = {
        _normalize_skill_key(item.get("trait")): item.get("weight", 0.0)
        for item in profile_abstractions.get("traits") or []
        if item.get("decision") == "accept"
    }
    job_traits = {
        _normalize_skill_key(item.get("trait")): item.get("weight", 0.0)
        for item in job_abstractions.get("traits") or []
        if item.get("decision") == "accept"
    }
    trait_overlap = _weighted_overlap(profile_traits, job_traits)

    components = [skill_overlap, capability_overlap, trait_overlap]
    scores = [component["profile_coverage"] for component in components if component["profile_coverage"]]
    scores += [component["job_coverage"] for component in components if component["job_coverage"]]
    alignment_score = round(sum(scores) / len(scores), 4) if scores else 0.0

    return {
        "skills": skill_overlap,
        "capabilities": capability_overlap,
        "traits": trait_overlap,
        "alignment_score": alignment_score,
    }

def _select_similarity(similarity_mode, embedder):
    if similarity_mode == "token":
        return lambda a, b: jaccard_similarity(a, b)
    return lambda a, b: semantic_similarity(a, b, embedder)


def _merge_weights(base, override):
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if value is None:
            continue
        merged[key] = value
    return merged


def _resolve_scoring_preset(config, preset_name=None):
    scoring_cfg = config.get("scoring", {}) or {}
    presets = scoring_cfg.get("presets", {}) or {}
    if preset_name is None:
        active_name = scoring_cfg.get("active_preset") or ""
    elif preset_name == "":
        active_name = ""
    else:
        active_name = preset_name
    preset = presets.get(active_name) if active_name else None
    base_weights = config.get("matching", {}).get("weights", {}) or {}
    base_apply = config.get("matching", {}).get("apply_threshold", 0.25)
    base_consider = config.get("matching", {}).get("consider_threshold", 0.15)
    if not preset:
        return {
            "name": "",
            "label": "",
            "weights": base_weights,
            "apply_threshold": base_apply,
            "consider_threshold": base_consider,
        }
    weights = _merge_weights(base_weights, preset.get("weights", {}) or {})
    thresholds = preset.get("thresholds", {}) or {}
    return {
        "name": active_name,
        "label": preset.get("label") or active_name,
        "weights": weights,
        "apply_threshold": thresholds.get("apply", base_apply),
        "consider_threshold": thresholds.get("consider", base_consider),
    }


def _score_jobs(jobs, profile, config, similarity_mode=None, feedback_enabled=None, preset_name=None):
    logs_dir = config["paths"]["logs_dir"]
    output_dir = config["paths"]["output_dir"]
    matching_cfg = config.get("matching", {}) or {}
    semantic_cfg = matching_cfg.get("semantic", {}) or {}
    similarity_cfg = matching_cfg.get("similarity", {}) or {}
    mode = similarity_mode or semantic_cfg.get("mode", "semantic")
    backend = semantic_cfg.get("backend", "hash")
    model_path = semantic_cfg.get("model_path") or os.getenv("APPLICANT_SEMANTIC_MODEL")
    cache_path = semantic_cfg.get("cache_path")
    embedder = None
    if mode == "semantic":
        embedder = SemanticEmbedder(backend=backend, model_path=model_path, cache_path=cache_path)
        if not embedder.available:
            log_message(logs_dir, "match_score", f"Semantic embedder unavailable ({embedder.reason}); using token overlap.")
    similarity = _select_similarity(mode, embedder)

    profile_text = _text_from_profile(profile)
    evidence_items = _atomize_profile(profile)
    profile_weighting = profile.get("skill_weighting", {}) or {}
    profile_abstractions = profile.get("role_abstractions", {}) or {}
    committee_votes = _load_committee_votes(os.path.join(config["paths"]["output_dir"], "committee_votes.json"))
    region_keywords = config.get("matching", {}).get("region_keywords", [])
    feedback_cfg = config.get("matching", {}).get("feedback", {}) or {}
    feedback_path = feedback_cfg.get("path") or os.path.join(output_dir, "feedback.json")
    feedback_enabled = feedback_enabled if feedback_enabled is not None else feedback_cfg.get("enabled", False)
    feedback_stats = {}
    if feedback_enabled:
        feedback_data = load_feedback(feedback_path)
        feedback_stats = build_tag_stats(feedback_data.get("outcomes"), feedback_data.get("rollbacks"))
    base_weights = matching_cfg.get("weights", {})
    supported_langs = set(config.get("language", {}).get("supported", []))
    top_n = matching_cfg.get("top_n", 5)
    apply_threshold = matching_cfg.get("apply_threshold", 0.25)
    consider_threshold = matching_cfg.get("consider_threshold", 0.15)
    reco_guard_cfg = matching_cfg.get("recommendation_guard", {}) or {}
    reco_guard_enabled = reco_guard_cfg.get("enabled", True)
    preset_cfg = _resolve_scoring_preset(config, preset_name=preset_name)
    preset_weights = preset_cfg["weights"]
    preset_apply = preset_cfg["apply_threshold"]
    preset_consider = preset_cfg["consider_threshold"]
    intent_cfg = matching_cfg.get("role_intent", {}) or {}
    role_intent = (profile.get("role_intent") or "engineering_execution").lower()
    if role_intent not in ROLE_INTENT_ORDER:
        role_intent = "engineering_execution"
    try:
        mismatch_penalty = float(intent_cfg.get("mismatch_penalty", 0.08))
    except (TypeError, ValueError):
        mismatch_penalty = 0.08
    try:
        alignment_bonus = float(intent_cfg.get("alignment_bonus", 0.06))
    except (TypeError, ValueError):
        alignment_bonus = 0.06
    try:
        execution_bonus = float(intent_cfg.get("execution_bonus", 0.0))
    except (TypeError, ValueError):
        execution_bonus = 0.0
    intent_enabled = intent_cfg.get("enabled", True)

    results = []
    review_queue = []
    cluster_texts_list = []

    if db_enabled(config):
        init_db(config)

    for job in jobs:
        title = job.get("title", "")
        description = job.get("description", "") or ""
        location = job.get("location", "")
        text_missing = job.get("text_missing")
        if text_missing is None:
            text_missing = len(description) < 200
        job_text = f"{title}\n\n{description}".strip() if description else title
        job_facts = _extract_job_facts(job)
        job_overrides = {}
        if isinstance(committee_votes, dict):
            job_key = str(job.get("id", ""))
            job_overrides = (committee_votes.get("jobs", {}) or {}).get(job_key, {}) or {}
        job_analysis = _build_job_analysis(job_text, config, overrides=job_overrides)
        alignment = _compute_alignment(
            profile_weighting,
            job_analysis.get("skill_weighting", {}),
            profile_abstractions,
            job_analysis.get("role_abstractions", {}),
        )
        job_intent_tags = _job_intent_tags(job)
        job_track = _primary_job_track(job_intent_tags)
        intent_bonus = 0.0
        intent_penalty = 0.0
        if intent_enabled:
            if role_intent == "engineering_execution":
                if "engineering_execution" in job_intent_tags:
                    intent_bonus = execution_bonus
            else:
                if "engineering_execution" in job_intent_tags:
                    intent_penalty = mismatch_penalty
                if job_intent_tags & ROLE_INTENT_LEADERSHIP:
                    intent_bonus = alignment_bonus
        intent_adjustment = intent_bonus - intent_penalty
        if intent_bonus and intent_penalty:
            intent_alignment = "mixed"
        elif intent_bonus:
            intent_alignment = "bonus"
        elif intent_penalty:
            intent_alignment = "penalty"
        else:
            intent_alignment = "neutral"

        requirements = [] if text_missing else _extract_requirements(description)
        if text_missing:
            requirement_rows, coverage, gaps = [], 0.0, []
            coverage_reason = "missing_description"
        else:
            requirement_rows, coverage, gaps = _match_requirements(requirements, evidence_items)
            coverage_reason = ""

        similarity_text = description if not text_missing else title
        skills_semantic = similarity(profile_text, similarity_text)
        title_score = similarity(profile_text, title)
        experience_score = similarity(
            " ".join([e.get("summary", "") for e in profile.get("experience", [])]),
            similarity_text,
        )
        skills_signal = skills_semantic
        if coverage > 0:
            skills_signal = (skills_semantic + coverage) / 2
        language = job.get("language") or detect_language(description)
        language_score = 1.0 if language in supported_langs else 0.0
        location_score = _location_score(location, region_keywords)

        base_score = (
            skills_signal * base_weights.get("skills", 0.0)
            + title_score * base_weights.get("title", 0.0)
            + experience_score * base_weights.get("experience", 0.0)
            + language_score * base_weights.get("language", 0.0)
            + location_score * base_weights.get("location", 0.0)
            + alignment.get("alignment_score", 0.0) * base_weights.get("alignment", 0.0)
        )
        preset_score = (
            skills_signal * preset_weights.get("skills", 0.0)
            + title_score * preset_weights.get("title", 0.0)
            + experience_score * preset_weights.get("experience", 0.0)
            + language_score * preset_weights.get("language", 0.0)
            + location_score * preset_weights.get("location", 0.0)
            + alignment.get("alignment_score", 0.0) * preset_weights.get("alignment", 0.0)
        )

        feedback_tags = build_feedback_tags(job, job_facts)
        adjustment = 0.0
        adjustment_audit = []
        if feedback_enabled and feedback_tags:
            adjustment, adjustment_audit = score_adjustment(
                feedback_tags,
                feedback_stats,
                weight=feedback_cfg.get("weight", 0.05),
                tag_weight=feedback_cfg.get("tag_weight"),
                company_weight=feedback_cfg.get("company_weight"),
                min_samples=feedback_cfg.get("min_samples", 2),
                max_adjustment=feedback_cfg.get("max_adjustment", 0.1),
            )
        score_raw = round(base_score, 4)
        score_preset = round(preset_score, 4)
        score_intent_adjusted = round(max(0.0, min(1.0, preset_score + intent_adjustment)), 4)
        score_intent_adjustment = round(score_intent_adjusted - score_preset, 4)
        score_adjusted = round(max(0.0, min(1.0, score_intent_adjusted + adjustment)), 4)
        score_feedback_adjustment = round(score_adjusted - score_intent_adjusted, 4)
        score_final = score_adjusted if feedback_enabled else score_intent_adjusted
        adjusted_by = []
        if preset_cfg["name"]:
            adjusted_by.append(f"preset:{preset_cfg['name']}")
        if intent_alignment != "neutral":
            adjusted_by.append(f"intent:{intent_alignment}:{role_intent}")
        if adjustment_audit:
            adjusted_by.extend(adjustment_audit)
        adjusted_by_label = " + ".join(adjusted_by)

        threshold_apply = preset_apply if preset_cfg["name"] else apply_threshold
        threshold_consider = preset_consider if preset_cfg["name"] else consider_threshold

        if score_final >= threshold_apply:
            recommendation = "apply"
        elif score_final >= threshold_consider:
            recommendation = "consider"
        else:
            recommendation = "skip"
        reco_reason = ""
        if reco_guard_enabled and _sales_guard_hit(title):
            reco_reason = "role_family_out_of_scope:sales"
            if recommendation == "apply":
                recommendation = "consider"
        out_of_scope = False
        if (
            role_intent != "engineering_execution"
            and "engineering_execution" in job_intent_tags
            and recommendation == "consider"
        ):
            recommendation = "skip"
            out_of_scope = True

        job_with_facts = dict(job)
        job_with_facts["job_facts"] = job_facts
        cluster_texts_list.append(job_text)
        notes = []
        if reco_reason:
            notes.append(reco_reason)
        if out_of_scope:
            notes.append("out_of_scope:engineering_execution")

        results.append(
            {
                "id": job.get("id"),
                "score": score_final,
                "score_raw": score_raw,
                "score_preset": score_preset,
                "score_preset_adjustment": round(score_preset - score_raw, 4),
                "score_intent_adjusted": score_intent_adjusted,
                "score_intent_adjustment": score_intent_adjustment,
                "score_adjusted": score_adjusted,
                "score_adjustment": score_feedback_adjustment,
                "score_feedback_adjustment": score_feedback_adjustment,
                "feedback_applied": bool(feedback_enabled),
                "feedback_tags": feedback_tags,
                "adjusted_by": adjusted_by_label,
                "adjusted_by_parts": adjusted_by,
                "preset_name": preset_cfg["name"],
                "score_breakdown": {
                    "skills": round(skills_signal, 4),
                    "skills_semantic": round(skills_semantic, 4),
                    "coverage_signal": round(coverage, 4),
                    "title": round(title_score, 4),
                    "experience": round(experience_score, 4),
                    "language": round(language_score, 4),
                    "location": round(location_score, 4),
                    "alignment": alignment.get("alignment_score", 0.0),
                    "capability_depth": round(skills_semantic, 4),
                    "role_target_match": round(title_score, 4),
                },
                "intent": {
                    "role_intent": role_intent,
                    "job_track": job_track,
                    "job_intent_tags": sorted(job_intent_tags),
                    "intent_alignment": intent_alignment,
                    "intent_bonus": round(intent_bonus, 4),
                    "intent_penalty": round(intent_penalty, 4),
                    "intent_adjustment": round(intent_adjustment, 4),
                    "out_of_scope": out_of_scope,
                },
                "qualification": {
                    "coverage": round(coverage, 4),
                    "coverage_reason": coverage_reason,
                    "requirements": requirement_rows,
                    "gaps": gaps,
                },
                "job_analysis": job_analysis,
                "alignment": alignment,
                "job_facts": job_facts,
                "recommendation": recommendation,
                "recommendation_reason": reco_reason,
                "score_thresholds": {
                    "apply": threshold_apply,
                    "consider": threshold_consider,
                },
                "notes": notes,
                "job": job_with_facts,
            }
        )

        committee_review = job_analysis.get("committee_review") or {}
        if committee_review:
            review_queue.append(
                {
                    "job_id": job.get("id"),
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "url": job.get("url", ""),
                    "committee_review": committee_review,
                }
            )

        if db_enabled(config) and job.get("id"):
            upsert_job_state(config, job.get("id"), score_final, recommendation)

    if similarity_cfg.get("enabled", False) and results:
        try:
            cluster_threshold = float(similarity_cfg.get("threshold", 0.85))
        except (TypeError, ValueError):
            cluster_threshold = 0.85
        cluster_embedder = embedder if embedder and embedder.available else None
        cluster_ids, cluster_sizes = cluster_texts(cluster_texts_list, embedder=cluster_embedder, threshold=cluster_threshold)
        for idx, match in enumerate(results):
            cluster_id = cluster_ids[idx] if idx < len(cluster_ids) else None
            if cluster_id:
                match["cluster_id"] = f"cluster-{cluster_id}"
                match["cluster_size"] = cluster_sizes.get(cluster_id, 1)

    if embedder and embedder.cache:
        embedder.cache.save()

    results.sort(key=lambda x: x["score"], reverse=True)
    suggestions = _build_suggestions(results, top_n)
    assessment = _summarize_skill_assessment(results, profile)
    return results, suggestions, assessment, review_queue


def match_score(
    config_path="config/applicant.yaml", similarity_mode=None, write_outputs=True, feedback_enabled=None, preset_name=None
):
    config = load_config(config_path)
    output_dir = config["paths"]["output_dir"]
    jobs_dir = config["paths"]["jobs_dir"]
    logs_dir = config["paths"]["logs_dir"]

    profile = read_json(os.path.join(output_dir, "rob_profile.json"))
    jobs = read_json(os.path.join(jobs_dir, "latest_jobs.json"))

    results, suggestions, assessment, review_queue = _score_jobs(
        jobs,
        profile,
        config,
        similarity_mode=similarity_mode,
        feedback_enabled=feedback_enabled,
        preset_name=preset_name,
    )

    if not write_outputs:
        return results

    output_path = os.path.join(output_dir, "matched_jobs.json")
    write_json(results, output_path)
    write_json(suggestions, os.path.join(output_dir, "job_suggestions.json"))
    write_json(assessment, os.path.join(output_dir, "skill_assessment.json"))
    if review_queue:
        write_json(
            {
                "action": "agent_review",
                "jobs": review_queue,
                "notes": "Held job skills/abstractions require agent review before use in scoring.",
            },
            os.path.join(output_dir, "job_committee_review.json"),
        )
    log_message(logs_dir, "match_score", f"Ranked {len(results)} jobs")
    log_message(logs_dir, "match_score", f"Wrote {len(suggestions)} job suggestions")
    log_message(logs_dir, "match_score", "Wrote skill assessment summary")
    if review_queue:
        log_message(logs_dir, "match_score", "Job committee review queued; see job_committee_review.json")
    return results


if __name__ == "__main__":
    match_score()
