import os
import re
from fnmatch import fnmatch
from io import BytesIO
import zipfile

from utils.io import load_config, read_json, write_json, log_message, ensure_dir
from utils.parser import load_documents, build_inventory, Document
from utils.web import fetch_url_html, fetch_binary, extract_links, html_to_text, allowed_url

SECTION_HEADERS = {
    "skills": ["skills", "technical skills", "core skills"],
    "experience": ["experience", "work history", "professional experience"],
    "education": ["education", "academic"],
    "projects": ["projects", "project experience"],
}

SKILL_CATEGORY_IGNORE = {
    "email",
    "phone",
    "website",
    "podcast",
    "library",
    "faq",
    "name",
    "nationality",
    "current place of residence",
}

SKILL_CATEGORY_HINTS = {
    "skill",
    "competenc",
    "expertise",
    "technology",
    "ai",
    "data",
    "cloud",
    "infrastructure",
    "security",
    "protocol",
    "architecture",
    "ml",
    "machine",
    "devops",
    "leadership",
    "strategy",
}

HARD_SKILL_HINTS = {
    "ai",
    "ml",
    "model",
    "framework",
    "protocol",
    "cloud",
    "infrastructure",
    "architecture",
    "security",
    "kubernetes",
    "docker",
    "terraform",
    "ansible",
    "python",
    "java",
    "golang",
    "database",
    "devops",
    "network",
}

SOFT_SKILL_HINTS = {
    "leadership",
    "communication",
    "stakeholder",
    "team",
    "management",
    "collaboration",
    "negotiation",
    "presentation",
    "people",
    "strategy",
}

SKILL_STOP_PHRASES = {
    "curriculum vitae",
    "cv -",
    "page",
    "overview",
    "contact",
    "library",
    "podcast",
    "website",
    "faq",
    "profile",
    "focus areas",
    "strategic overview",
    "experience level",
    "qualification",
    "certification",
    "skill / competency",
    "whitepapers",
    "project references",
    "questions regarding my work",
}

SKILL_STOP_WORDS = {
    "documents",
    "approach",
    "overview",
    "profile",
    "focus",
    "areas",
    "models",
}

CAPABILITY_TAXONOMY = [
    {
        "category": "AI Strategy & Transformation",
        "keywords": [
            "ai",
            "ml",
            "machine learning",
            "gpt",
            "llm",
            "prompt",
            "mlops",
            "model",
            "ai platform",
            "ai infrastructure",
            "transfer learning",
            "vision transformer",
            "federated learning",
        ],
        "summary": "Evidence-backed AI strategy and transformation capability.",
    },
    {
        "category": "Cloud & DevOps",
        "keywords": [
            "cloud",
            "aws",
            "azure",
            "gcp",
            "kubernetes",
            "docker",
            "terraform",
            "ansible",
            "ci/cd",
            "devops",
            "infrastructure as code",
            "container",
        ],
        "summary": "Cloud, platform, and DevOps infrastructure delivery.",
    },
    {
        "category": "Security & Governance",
        "keywords": [
            "security",
            "zero-trust",
            "gdpr",
            "hipaa",
            "pci",
            "compliance",
            "threat",
            "siem",
            "iso 27001",
            "itil",
            "risk",
        ],
        "summary": "Security architecture, governance, and compliance leadership.",
    },
    {
        "category": "Distributed Systems & Architecture",
        "keywords": [
            "distributed",
            "microservices",
            "architecture",
            "system design",
            "high availability",
            "scalable",
            "protocol",
            "mesh",
        ],
        "summary": "Distributed systems architecture and scaling expertise.",
    },
    {
        "category": "Data Platforms & Analytics",
        "keywords": [
            "data",
            "analytics",
            "database",
            "postgres",
            "mysql",
            "mongo",
            "redis",
            "big data",
        ],
        "summary": "Data platform strategy and analytics execution.",
    },
    {
        "category": "Product & Business Strategy",
        "keywords": [
            "product",
            "saas",
            "go-to-market",
            "white-label",
            "partner",
            "business model",
            "consulting",
        ],
        "summary": "Product strategy and business model execution.",
    },
    {
        "category": "Leadership & Org Design",
        "keywords": [
            "leadership",
            "team",
            "stakeholder",
            "management",
            "people",
            "c-level",
        ],
        "summary": "Leadership, org design, and stakeholder management.",
    },
]

TRAIT_TAXONOMY = [
    {
        "trait": "Leadership & People",
        "keywords": ["leadership", "team", "people", "management", "mentor", "building"],
    },
    {
        "trait": "Stakeholder & Communication",
        "keywords": ["stakeholder", "communication", "presentation", "negotiation"],
    },
    {
        "trait": "Strategic Thinking",
        "keywords": ["strategy", "consulting", "vision", "roadmap"],
    },
    {
        "trait": "Execution & Delivery",
        "keywords": ["delivery", "operations", "program", "project", "release"],
    },
]


def _normalize_lines(text):
    text = text.replace("\r", "\n")
    return [line.strip() for line in text.split("\n") if line.strip()]


def _find_section(lines, keywords):
    start = None
    for idx, line in enumerate(lines):
        low = line.lower()
        if any(k in low for k in keywords):
            start = idx + 1
            break
    if start is None:
        return []
    end = len(lines)
    for idx in range(start, len(lines)):
        low = lines[idx].lower()
        if any(k in low for k in SECTION_HEADERS["skills"] + SECTION_HEADERS["experience"] + SECTION_HEADERS["education"] + SECTION_HEADERS["projects"]):
            end = idx
            break
    return lines[start:end]


def _extract_emails(text):
    return list({m.group(0) for m in re.finditer(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+", text)})


def _name_tokens(name):
    if not name:
        return []
    tokens = re.split(r"[^a-z]+", name.lower())
    return [token for token in tokens if token]


def _score_email_candidate(email, name_tokens, allowed_domains):
    votes = []
    score = 0
    if not email or "@" not in email:
        return 0, ["invalid email"]

    local, domain = email.lower().split("@", 1)
    if allowed_domains:
        for allowed in allowed_domains:
            allowed = allowed.lower()
            if domain == allowed or domain.endswith("." + allowed):
                score += 2
                votes.append("allowed domain")
                break

    if name_tokens:
        if len(name_tokens) > 1 and name_tokens[-1] in local:
            score += 2
            votes.append("last name in local part")
        if name_tokens and name_tokens[0] in local:
            score += 1
            votes.append("first name in local part")

    if local in {"info", "contact", "jobs", "hr", "careers", "support", "team", "hello", "noreply"}:
        score -= 2
        votes.append("generic mailbox")

    if score <= 0 and name_tokens and not any(token in local for token in name_tokens):
        score -= 1
        votes.append("no name match")

    return score, votes


def _select_profile_email(emails, profile, config, overrides=None):
    if not emails:
        return "", []

    name_tokens = _name_tokens((profile.get("identity") or {}).get("name", ""))
    allowed_domains = set(config.get("web_profile", {}).get("allowed_domains", []) or [])
    allowed_domains.update(config.get("profile", {}).get("email_domains", []) or [])
    override_decisions = {key.lower(): value for key, value in (overrides or {}).items()}

    candidates = []
    for email in sorted(set(emails), key=str.lower):
        score, votes = _score_email_candidate(email, name_tokens, allowed_domains)
        decision = ""
        override = override_decisions.get(email.lower())
        if override in {"accept", "reject"}:
            decision = override
            votes.append("override")
        candidates.append({"email": email, "score": score, "votes": votes, "decision": decision})

    candidates.sort(key=lambda item: (-item["score"], item["email"].lower()))
    for item in candidates:
        if item.get("decision") == "accept":
            return item["email"], candidates

    best = None
    for item in candidates:
        if item.get("decision") == "reject":
            continue
        best = item
        break
    if best and best["score"] >= 2:
        best["decision"] = "selected"
        for item in candidates:
            if item is best:
                continue
            if not item.get("decision"):
                item["decision"] = "rejected"
        return best["email"], candidates

    for item in candidates:
        if not item.get("decision"):
            item["decision"] = "rejected"
    return "", candidates


def _load_committee_votes(path):
    if os.path.exists(path):
        try:
            return read_json(path)
        except Exception:
            return {}
    return {}


def _extract_skills(text, skills_seed):
    hard = []
    soft = []
    evidence = {}
    for skill in skills_seed.get("hard", []):
        pattern = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            hard.append(skill)
            evidence[skill] = _snippet(text, match.start())
    for skill in skills_seed.get("soft", []):
        pattern = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            soft.append(skill)
            evidence[skill] = _snippet(text, match.start())
    return sorted(set(hard)), sorted(set(soft)), evidence


def _snippet(text, idx, window=120):
    start = max(0, idx - window)
    end = min(len(text), idx + window)
    snippet = text[start:end].replace("\n", " ").strip()
    return snippet


def _docx_bytes_to_text(data):
    if not data:
        return ""
    try:
        with zipfile.ZipFile(BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception:
        return ""
    xml = re.sub(r"</w:p>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _pdf_bytes_to_text(data):
    if not data:
        return ""
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
    except Exception:
        pass

    temp_path = None
    try:
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            temp_path = tmp.name
        result = subprocess.run(
            ["pdftotext", temp_path, "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        if result.stdout:
            return result.stdout.strip()
    except Exception:
        return ""
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    return ""


def _match_patterns(path, patterns):
    if not patterns:
        return False
    for pattern in patterns:
        if not pattern:
            continue
        if any(ch in pattern for ch in "*?[]"):
            if fnmatch(path, pattern):
                return True
        elif pattern in path:
            return True
    return False


def _select_profile_docs(docs, exclude_patterns):
    used = []
    excluded = []
    for doc in docs:
        if not doc.content:
            excluded.append({"path": doc.path, "reason": "empty content"})
            continue
        if _match_patterns(doc.path, exclude_patterns):
            excluded.append({"path": doc.path, "reason": "excluded by profile settings"})
            continue
        used.append(doc)
    return used, excluded


def _section_entries(lines):
    entries = []
    for line in lines:
        if len(line) < 3:
            continue
        entries.append({"summary": line, "evidence": [line]})
    return entries


def _classify_skill(item):
    low = item.lower()
    if any(hint in low for hint in HARD_SKILL_HINTS):
        return "hard"
    if any(hint in low for hint in SOFT_SKILL_HINTS):
        return "soft"
    return "hard"


def _extract_skill_lists(text, config):
    if not text:
        return [], []
    lines = _normalize_lines(text)
    hard, soft, _ = _extract_skills(text, config.get("skills_seed", {}))

    skills_lines = _find_section(lines, SECTION_HEADERS["skills"])
    if skills_lines:
        raw_skills = []
        for line in skills_lines:
            if ":" in line:
                _, right = line.split(":", 1)
                raw_skills.extend(_split_skill_items(right))
            else:
                raw_skills.extend(_split_skill_items(line))
        for skill in raw_skills:
            if skill not in hard and skill not in soft:
                hard.append(skill)

    categories = _extract_skill_categories(lines)
    for _, items in categories.items():
        for item in items:
            if item in hard or item in soft:
                continue
            bucket = _classify_skill(item)
            if bucket == "soft":
                soft.append(item)
            else:
                hard.append(item)

    hard = list(dict.fromkeys(hard))
    soft = list(dict.fromkeys(soft))
    return hard, soft


def _find_skill_evidence(text, skill, max_hits=1):
    if not text or not skill:
        return []
    matches = []
    pattern = re.compile(re.escape(skill), re.IGNORECASE)
    for match in pattern.finditer(text):
        snippet = _snippet(text, match.start())
        if snippet and snippet not in matches:
            matches.append(snippet)
        if len(matches) >= max_hits:
            break
    return matches


def _capability_confidence(support_count, evidence_count):
    if support_count >= 4 and evidence_count >= 2:
        return "high"
    if support_count >= 2:
        return "medium"
    return "low"


def _skill_match_pattern(skill):
    if not skill:
        return None
    if re.match(r"^[A-Za-z0-9]+$", skill):
        return re.compile(rf"\\b{re.escape(skill)}\\b", re.IGNORECASE)
    return re.compile(re.escape(skill), re.IGNORECASE)


def _count_skill_mentions(text, skill):
    if not text or not skill:
        return 0
    pattern = _skill_match_pattern(skill)
    if not pattern:
        return 0
    return len(pattern.findall(text))


def _assign_levels(items, major_frac=0.2, median_frac=0.5, key="signal", name_key="skill"):
    if not items:
        return
    items.sort(key=lambda x: (-x.get(key, 0), str(x.get(name_key, "")).lower()))
    total = len(items)
    major_cut = max(1, int(round(total * major_frac)))
    if total == 1:
        median_cut = major_cut
    else:
        median_cut = max(major_cut + 1, int(round(total * median_frac)))
    for idx, item in enumerate(items):
        if idx < major_cut:
            item["level"] = "major"
        elif idx < median_cut:
            item["level"] = "median"
        else:
            item["level"] = "minor"


def _skill_committee_vote(skill, combined_text, skills_section, seeded_skills, evidence_hits):
    votes = []
    score = 0

    mentions = _count_skill_mentions(combined_text, skill)
    if mentions >= 2:
        votes.append({"source": "mentions", "weight": 1})
        score += 1

    if evidence_hits:
        votes.append({"source": "evidence", "weight": 1})
        score += 1

    if skills_section:
        pattern = _skill_match_pattern(skill)
        if pattern and pattern.search(skills_section):
            votes.append({"source": "skills section", "weight": 1})
            score += 1

    if seeded_skills and skill.lower() in seeded_skills:
        votes.append({"source": "seeded skill", "weight": 1})
        score += 1

    low = skill.lower()
    taxonomy_keywords = set()
    for cap in CAPABILITY_TAXONOMY:
        taxonomy_keywords.update(cap.get("keywords") or [])
    for trait in TRAIT_TAXONOMY:
        taxonomy_keywords.update(trait.get("keywords") or [])
    if any(keyword in low for keyword in taxonomy_keywords):
        votes.append({"source": "taxonomy match", "weight": 1})
        score += 1

    if "http" in low or "www" in low:
        votes.append({"source": "url artifact", "weight": -2})
        score -= 2

    return {"score": score, "votes": votes}


def _normalize_committee_decision(value):
    if not value:
        return ""
    value = str(value).strip().lower()
    if value in {"accept", "approve", "approved"}:
        return "accept"
    if value in {"reject", "rejected", "deny"}:
        return "reject"
    if value in {"hold", "defer"}:
        return "hold"
    return ""


def _build_skill_weighting(profile, combined_text, config, committee_cfg=None, overrides=None):
    entries = []
    lines = _normalize_lines(combined_text)
    skills_lines = _find_section(lines, SECTION_HEADERS["skills"])
    skills_section = " ".join(skills_lines) if skills_lines else ""
    skills_seed = config.get("skills_seed", {})
    hard_seed = set([s.lower() for s in skills_seed.get("hard", [])])
    soft_seed = set([s.lower() for s in skills_seed.get("soft", [])])
    committee_cfg = committee_cfg if committee_cfg is not None else config.get("profile", {}).get("committee", {})
    min_score = committee_cfg.get("min_score", 2)
    try:
        min_score = int(min_score)
    except (TypeError, ValueError):
        min_score = 2
    overrides = overrides or {}
    override_skills = {key.lower(): _normalize_committee_decision(val) for key, val in (overrides.get("skills") or {}).items()}
    evidence_map = profile.get("evidence", {})
    for skill in profile.get("hard_skills", []):
        mentions = _count_skill_mentions(combined_text, skill)
        evidence_hits = 1 if skill in evidence_map else 0
        signal = mentions + (2 if evidence_hits else 0)
        committee = _skill_committee_vote(
            skill,
            combined_text,
            skills_section,
            hard_seed | soft_seed,
            evidence_hits,
        )
        committee["decision"] = "accept" if committee["score"] >= min_score else "hold"
        override = override_skills.get(skill.lower())
        if override in {"accept", "reject", "hold"}:
            committee["decision"] = override
            committee["override"] = override
        entries.append(
            {
                "skill": skill,
                "type": "hard",
                "mentions": mentions,
                "evidence_hits": evidence_hits,
                "signal": signal,
                "committee": committee,
            }
        )
    for skill in profile.get("soft_skills", []):
        mentions = _count_skill_mentions(combined_text, skill)
        evidence_hits = 1 if skill in evidence_map else 0
        signal = mentions + (2 if evidence_hits else 0)
        committee = _skill_committee_vote(
            skill,
            combined_text,
            skills_section,
            hard_seed | soft_seed,
            evidence_hits,
        )
        committee["decision"] = "accept" if committee["score"] >= min_score else "hold"
        override = override_skills.get(skill.lower())
        if override in {"accept", "reject", "hold"}:
            committee["decision"] = override
            committee["override"] = override
        entries.append(
            {
                "skill": skill,
                "type": "soft",
                "mentions": mentions,
                "evidence_hits": evidence_hits,
                "signal": signal,
                "committee": committee,
            }
        )

    if not entries:
        return {"entries": [], "tiers": {"major": [], "median": [], "minor": []}}

    _assign_levels(entries, major_frac=0.2, median_frac=0.5, key="signal", name_key="skill")
    max_signal = max(1, max(entry["signal"] for entry in entries))
    for entry in entries:
        entry["weight"] = round(entry["signal"] / max_signal, 4)

    tiers = {"major": [], "median": [], "minor": []}
    for entry in sorted(entries, key=lambda x: (-x["signal"], x["skill"].lower())):
        tiers[entry["level"]].append(entry["skill"])

    return {
        "entries": sorted(entries, key=lambda x: (-x["signal"], x["skill"].lower())),
        "tiers": tiers,
        "committee": {
            "min_score": min_score,
            "held": sum(1 for entry in entries if entry.get("committee", {}).get("decision") == "hold"),
            "rejected": sum(1 for entry in entries if entry.get("committee", {}).get("decision") == "reject"),
        },
        "notes": "Weights derived from source mentions and evidence hits.",
    }


def _abstraction_committee_vote(support, total_signal, matched_keywords=None):
    votes = []
    score = 0
    support_count = len(support)

    if support_count >= 2:
        votes.append({"source": "support count", "weight": 1})
        score += 1

    if any(item.get("level") in {"major", "median"} for item in support):
        votes.append({"source": "major or median support", "weight": 1})
        score += 1

    if total_signal >= 3:
        votes.append({"source": "signal strength", "weight": 1})
        score += 1

    if matched_keywords is not None and len(matched_keywords) >= 2:
        votes.append({"source": "keyword coverage", "weight": 1})
        score += 1

    return {"score": score, "votes": votes}


def _build_role_abstractions(skill_weighting, overrides=None):
    entries = list(skill_weighting.get("entries", []))
    accepted = [entry for entry in entries if entry.get("committee", {}).get("decision") == "accept"]
    fallback_used = False
    if accepted:
        entries = accepted
    elif entries:
        fallback_used = True
    if not entries:
        return {"capabilities": [], "traits": [], "held": [], "notes": "No skills available for abstraction."}

    overrides = overrides or {}
    override_map = {key.lower(): _normalize_committee_decision(val) for key, val in (overrides.get("abstractions") or {}).items()}

    capabilities = []
    held = []
    for cap in CAPABILITY_TAXONOMY:
        support = []
        matched_keywords = set()
        total_signal = 0
        for entry in entries:
            low = entry["skill"].lower()
            if any(keyword in low for keyword in cap["keywords"]):
                support.append(entry)
                total_signal += entry["signal"]
                for keyword in cap["keywords"]:
                    if keyword in low:
                        matched_keywords.add(keyword)
        if not support:
            continue
        support_sorted = sorted(support, key=lambda x: (-x["signal"], x["skill"].lower()))
        committee = _abstraction_committee_vote(support_sorted, total_signal, matched_keywords)
        decision = "accept" if committee["score"] >= 2 else "hold"
        if fallback_used:
            decision = "hold"
        override = override_map.get(f"capability:{cap['category'].lower()}") or override_map.get(cap["category"].lower())
        if override in {"accept", "reject", "hold"}:
            decision = override
            committee["override"] = override
        payload = {
            "category": cap["category"],
            "summary": cap["summary"],
            "supporting_skills": [
                {"skill": item["skill"], "level": item["level"], "weight": item["weight"]} for item in support_sorted
            ],
            "matched_keywords": sorted(matched_keywords),
            "total_signal": total_signal,
            "committee": committee,
            "decision": decision,
        }
        if decision == "accept":
            capabilities.append(payload)
        elif decision == "hold":
            held.append({"kind": "capability", **payload})

    traits = []
    for trait in TRAIT_TAXONOMY:
        support = []
        total_signal = 0
        for entry in entries:
            if entry.get("type") != "soft":
                continue
            low = entry["skill"].lower()
            if any(keyword in low for keyword in trait["keywords"]):
                support.append(entry)
                total_signal += entry["signal"]
        if not support:
            continue
        support_sorted = sorted(support, key=lambda x: (-x["signal"], x["skill"].lower()))
        committee = _abstraction_committee_vote(support_sorted, total_signal)
        decision = "accept" if committee["score"] >= 2 else "hold"
        if fallback_used:
            decision = "hold"
        override = override_map.get(f"trait:{trait['trait'].lower()}") or override_map.get(trait["trait"].lower())
        if override in {"accept", "reject", "hold"}:
            decision = override
            committee["override"] = override
        payload = {
            "trait": trait["trait"],
            "supporting_skills": [
                {"skill": item["skill"], "level": item["level"], "weight": item["weight"]} for item in support_sorted
            ],
            "total_signal": total_signal,
            "committee": committee,
            "decision": decision,
        }
        if decision == "accept":
            traits.append(payload)
        elif decision == "hold":
            held.append({"kind": "trait", **payload})

    _assign_levels(capabilities, major_frac=0.25, median_frac=0.6, key="total_signal", name_key="category")
    _assign_levels(traits, major_frac=0.25, median_frac=0.6, key="total_signal", name_key="trait")

    max_cap_signal = max([c["total_signal"] for c in capabilities], default=0) or 1
    for cap in capabilities:
        cap["weight"] = round(cap["total_signal"] / max_cap_signal, 4)

    max_trait_signal = max([t["total_signal"] for t in traits], default=0) or 1
    for trait in traits:
        trait["weight"] = round(trait["total_signal"] / max_trait_signal, 4)

    return {
        "capabilities": sorted(capabilities, key=lambda x: (-x["total_signal"], x["category"].lower())),
        "traits": sorted(traits, key=lambda x: (-x["total_signal"], x["trait"].lower())),
        "held": held,
        "notes": "Abstracted from weighted skills to align with job description language.",
    }


def _build_capability_baseline(profile, combined_text, config):
    skills = profile.get("hard_skills", []) + profile.get("soft_skills", [])
    evidence_map = dict(profile.get("evidence", {}))
    for skill in skills:
        if skill not in evidence_map:
            snippets = _find_skill_evidence(combined_text, skill, max_hits=1)
            if snippets:
                evidence_map[skill] = snippets[0]

    min_support = config.get("profile", {}).get("capability_min_support", 2)
    try:
        min_support = int(min_support)
    except (TypeError, ValueError):
        min_support = 2

    capabilities = []
    used_skills = set()
    for cap in CAPABILITY_TAXONOMY:
        support = []
        evidence = []
        matched_keywords = set()
        for skill in skills:
            low = skill.lower()
            if any(keyword in low for keyword in cap["keywords"]):
                support.append(skill)
                used_skills.add(skill)
                for keyword in cap["keywords"]:
                    if keyword in low:
                        matched_keywords.add(keyword)
                snippet = evidence_map.get(skill)
                if snippet:
                    evidence.append(snippet)
        support = list(dict.fromkeys(support))
        evidence = list(dict.fromkeys(evidence))
        if len(support) < min_support:
            continue
        capabilities.append(
            {
                "category": cap["category"],
                "summary": cap["summary"],
                "supporting_skills": support,
                "matched_keywords": sorted(matched_keywords),
                "evidence": evidence[:3],
                "support_count": len(support),
                "confidence": _capability_confidence(len(support), len(evidence)),
            }
        )

    traits = []
    used_traits = set()
    soft_skills = profile.get("soft_skills", [])
    for trait in TRAIT_TAXONOMY:
        support = []
        evidence = []
        for skill in soft_skills:
            low = skill.lower()
            if any(keyword in low for keyword in trait["keywords"]):
                support.append(skill)
                used_traits.add(skill)
                snippet = evidence_map.get(skill)
                if snippet:
                    evidence.append(snippet)
        support = list(dict.fromkeys(support))
        evidence = list(dict.fromkeys(evidence))
        if not support:
            continue
        traits.append(
            {
                "trait": trait["trait"],
                "supporting_skills": support,
                "evidence": evidence[:3],
                "support_count": len(support),
            }
        )

    unmapped_skills = [skill for skill in skills if skill not in used_skills]
    unmapped_traits = [skill for skill in soft_skills if skill not in used_traits]

    identity = profile.get("identity", {})
    perks = {}
    if identity.get("location"):
        perks["location"] = identity.get("location")
    if identity.get("email"):
        perks["contact_email"] = identity.get("email")

    baseline = {
        "capabilities": capabilities,
        "traits": traits,
        "perks": perks,
        "unmapped_skills": sorted(unmapped_skills),
        "unmapped_traits": sorted(unmapped_traits),
        "guardrails": {
            "min_support": min_support,
            "sources_used": len(profile.get("source_files_used", [])),
            "sources_excluded": len(profile.get("source_files_excluded", [])),
            "notes": "Capabilities derived only from extracted skills and source text.",
        },
    }
    return baseline


def _extract_section_text(text, start_keywords, end_keywords):
    low = text.lower()
    starts = [low.find(k) for k in start_keywords if k in low]
    if not starts:
        return ""
    start_idx = min(starts)
    end_idx = len(text)
    for end_kw in end_keywords:
        idx = low.find(end_kw, start_idx + 1)
        if idx != -1:
            end_idx = min(end_idx, idx)
    return text[start_idx:end_idx].strip()


def _looks_like_role_header(fragment):
    if not fragment or len(fragment) > 220:
        return False
    if re.search(r"\b(19|20)\d{2}\b", fragment) is None:
        return False
    if re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", fragment.lower()):
        return True
    if " - " in fragment or " – " in fragment:
        return True
    return False


def _clean_fragment(fragment):
    cleaned = re.sub(r"CV\s*-\s*[^\n]+", " ", fragment, flags=re.IGNORECASE)
    cleaned = re.sub(r"CV\s+\w+\s+\d{4}\s+Page\s+\d+/\d+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"CV[^\n]{0,80}Page\s+\d+/\d+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", " ", cleaned)
    cleaned = re.sub(r"\+\d[\d\s-]{6,}", " ", cleaned)
    cleaned = re.sub(r"\bcom\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _split_on_date_marker(part):
    pattern = re.compile(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\s*[–-]\s*(?:[a-z]+\s*)?\d{4}\b",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(part))
    if not matches:
        return [part]
    split_positions = []
    for match in matches:
        if match.start() == 0:
            continue
        split_at = part.rfind(".", 0, match.start())
        if split_at != -1:
            split_positions.append(split_at + 1)
    if not split_positions and len(matches) > 1:
        split_positions.append(matches[1].start())
    if not split_positions:
        return [part]
    segments = []
    last = 0
    for pos in sorted(set(split_positions)):
        segment = part[last:pos].strip()
        if segment:
            segments.append(segment)
        last = pos
    tail = part[last:].strip()
    if tail:
        segments.append(tail)
    return segments


def _extract_experience_entries(text):
    section = _extract_section_text(
        text,
        ["professional experience", "work history", "experience highlights"],
        ["projects - roble", "skills - roble", "skills & competencies"],
    )
    if not section:
        return []
    section = section.replace("Professional Experience", "").strip()
    raw_parts = [p.strip() for p in section.split("•") if p.strip()]
    parts = []
    for part in raw_parts:
        for segment in _split_on_date_marker(part):
            cleaned = _clean_fragment(segment)
            if cleaned:
                parts.append(cleaned)
    entries = []
    current = None
    for part in parts:
        if _looks_like_role_header(part):
            if current:
                entries.append(current)
            current = {"summary": part, "evidence": [part]}
        else:
            if current is None:
                current = {"summary": part, "evidence": [part]}
            else:
                current["evidence"].append(part)
    if current:
        entries.append(current)
    for entry in entries:
        if len(entry["evidence"]) > 1:
            entry["summary"] = f"{entry['evidence'][0]} — {entry['evidence'][1]}"
    return entries


def _extract_simple_section(text, start_keywords, end_keywords):
    section = _extract_section_text(text, start_keywords, end_keywords)
    if not section:
        return []
    parts = [p.strip() for p in section.split("•") if p.strip()]
    return _section_entries(parts[:40])


def _count_pattern_hits(text, patterns):
    if not text:
        return 0
    hits = 0
    for pattern in patterns:
        if re.search(pattern, text):
            hits += 1
    return hits


def _infer_role_intent(profile, combined_text):
    leadership_patterns = [
        r"\bdirector\b",
        r"\bhead\b",
        r"\bvp\b",
        r"vice president",
        r"\bchief\b",
        r"\bexecutive\b",
        r"\bmanager\b",
        r"\blead\b",
        r"\bprincipal\b",
    ]
    strategy_patterns = [
        r"\bstrategy\b",
        r"\bstrategic\b",
        r"\bgovernance\b",
        r"\broadmap\b",
        r"\bportfolio\b",
        r"\btransformation\b",
        r"\boversaw\b",
        r"\bled\b",
        r"\bmanaged\b",
        r"\bowned\b",
        r"\bdefined\b",
        r"\bsteered\b",
        r"\bstakeholder\b",
    ]
    architecture_patterns = [
        r"\barchitect\b",
        r"\barchitecture\b",
        r"solution architect",
        r"enterprise architect",
        r"platform architect",
        r"systems architect",
    ]
    consulting_patterns = [
        r"\bconsultant\b",
        r"\bconsulting\b",
        r"\badvisory\b",
        r"\badvisor\b",
        r"pre-?sales",
        r"\bclient\b",
        r"\bpartner\b",
        r"\bengagement\b",
        r"\bpractice\b",
    ]
    execution_patterns = [
        r"\bengineer\b",
        r"\bdeveloper\b",
        r"\bscientist\b",
        r"data engineer",
        r"ml engineer",
        r"\bbackend\b",
        r"\bfrontend\b",
        r"full stack",
        r"\bswe\b",
        r"\bdevops\b",
        r"\bsre\b",
        r"site reliability",
    ]

    experience = profile.get("experience", []) or []
    entry_texts = []
    for entry in experience:
        parts = []
        summary = entry.get("summary", "")
        if summary:
            parts.append(summary)
        evidence = entry.get("evidence") or []
        parts.extend([item for item in evidence if item])
        if parts:
            entry_texts.append(" ".join(parts))

    if not entry_texts and combined_text:
        entry_texts = [combined_text]

    scores = {
        "executive_strategy": 0,
        "principal_architecture": 0,
        "consulting_leadership": 0,
        "engineering_execution": 0,
    }
    leadership_entries = 0
    execution_entries = 0

    for text in entry_texts:
        low = (text or "").lower()
        leadership_hits = _count_pattern_hits(low, leadership_patterns)
        strategy_hits = _count_pattern_hits(low, strategy_patterns)
        architecture_hits = _count_pattern_hits(low, architecture_patterns)
        consulting_hits = _count_pattern_hits(low, consulting_patterns)
        execution_hits = _count_pattern_hits(low, execution_patterns)

        if leadership_hits or strategy_hits or architecture_hits or consulting_hits:
            leadership_entries += 1
        if execution_hits:
            execution_entries += 1

        scores["executive_strategy"] += leadership_hits + strategy_hits
        scores["principal_architecture"] += architecture_hits + (1 if leadership_hits else 0)
        scores["consulting_leadership"] += consulting_hits + (1 if strategy_hits else 0)
        scores["engineering_execution"] += execution_hits

    total_entries = max(len(entry_texts), 1)
    leadership_ratio = leadership_entries / total_entries

    leader_scores = {k: v for k, v in scores.items() if k != "engineering_execution"}
    top_leader = max(leader_scores.items(), key=lambda item: (item[1], item[0])) if leader_scores else ("", 0)
    top_all = max(scores.items(), key=lambda item: (item[1], item[0])) if scores else ("engineering_execution", 0)

    if leadership_ratio >= 0.4 and top_leader[1] > 0:
        role_intent = top_leader[0]
    else:
        role_intent = top_all[0] if top_all[1] > 0 else "engineering_execution"

    signals = {
        "scores": scores,
        "leadership_entries": leadership_entries,
        "execution_entries": execution_entries,
        "leadership_ratio": round(leadership_ratio, 3),
    }
    return role_intent, signals


def _split_skill_items(text):
    raw_items = re.split(r"[•;]|\s{2,}|,(?!\d)", text)
    items = []
    for item in raw_items:
        clean = item.strip(" \t-–—•.;:")
        clean = re.sub(r"^(and|or)\s+", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s+", " ", clean)
        if _is_skill_candidate(clean):
            items.append(clean)
    return items


def _normalize_label(label):
    label = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
    return label


def _is_skill_candidate(text):
    if not text or len(text) < 2:
        return False
    if len(text) > 60:
        return False
    if "@" in text:
        return False
    words = text.split()
    if len(words) > 8:
        return False
    if re.match(r"^\d[\d,]*\+?\s+\S+", text) and len(words) > 2:
        return False
    low = text.lower()
    if any(phrase in low for phrase in SKILL_STOP_PHRASES):
        return False
    if low in SKILL_STOP_WORDS:
        return False
    if re.match(r"^[\\W_]+$", text):
        return False
    return True


def _extract_skill_categories(lines):
    categories = {}
    label_pattern = re.compile(r"([A-Za-z/& ]{2,40}):")
    for line in lines:
        matches = list(label_pattern.finditer(line))
        if not matches:
            continue
        for idx, match in enumerate(matches):
            label = match.group(1).strip()
            label_norm = _normalize_label(label)
            if not label or label_norm in SKILL_CATEGORY_IGNORE:
                continue
            if len(label_norm.split()) > 6:
                continue
            if not any(hint in label_norm for hint in SKILL_CATEGORY_HINTS):
                continue
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(line)
            right = line[start:end]
            if len(right) < 8 or ("," not in right and "•" not in right):
                continue
            items = _split_skill_items(right)
            if items:
                categories[label] = items
    return categories


def _fetch_web_document(url):
    clean_url = url.split("?", 1)[0].split("#", 1)[0].lower()
    if clean_url.endswith(".pdf"):
        data, content_type, status = fetch_binary(url)
        text = _pdf_bytes_to_text(data) if data else ""
        notes = content_type or status
        doc_status = "ok" if text else "error"
        return Document(path=f"web:{url}", content=text, file_type="pdf", status=doc_status, notes=notes), ""
    if clean_url.endswith(".docx"):
        data, content_type, status = fetch_binary(url)
        text = _docx_bytes_to_text(data) if data else ""
        notes = content_type or status
        doc_status = "ok" if text else "error"
        return Document(path=f"web:{url}", content=text, file_type="docx", status=doc_status, notes=notes), ""

    html, status = fetch_url_html(url)
    text = html_to_text(html) if html else ""
    doc_status = "ok" if text else "error"
    return Document(path=f"web:{url}", content=text, file_type="html", status=doc_status, notes=status), html


def _load_web_documents(config, output_text_dir):
    web_cfg = config.get("web_profile", {})
    if not web_cfg.get("enabled"):
        return []

    urls = web_cfg.get("urls", [])
    allowed_domains = web_cfg.get("allowed_domains", [])
    follow_enabled = bool(web_cfg.get("follow_library", False) or web_cfg.get("follow_patterns"))
    follow_patterns = web_cfg.get("follow_patterns", []) or []
    max_pages = web_cfg.get("max_pages", 0)
    try:
        max_pages = int(max_pages)
    except (TypeError, ValueError):
        max_pages = 0

    documents = []
    seen = set()
    follow_queue = []

    for idx, url in enumerate(urls, start=1):
        if allowed_domains and not allowed_url(url, allowed_domains):
            documents.append(
                Document(
                    path=f"web:{url}",
                    content="",
                    file_type="html",
                    status="blocked",
                    notes="domain not in allowed_domains",
                )
            )
            continue

        document, html = _fetch_web_document(url)
        documents.append(document)
        seen.add(url)

        if output_text_dir and document.content:
            os.makedirs(output_text_dir, exist_ok=True)
            out_path = os.path.join(output_text_dir, f"web_{idx}.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(document.content)

        if follow_enabled and html:
            links = extract_links(html, url)
            for link in links:
                if max_pages and len(follow_queue) >= max_pages:
                    break
                if link in seen:
                    continue
                if allowed_domains and not allowed_url(link, allowed_domains):
                    continue
                if follow_patterns and not any(pat in link for pat in follow_patterns):
                    continue
                follow_queue.append(link)
                seen.add(link)

    for idx, url in enumerate(follow_queue, start=len(urls) + 1):
        document, _ = _fetch_web_document(url)
        documents.append(document)

        if output_text_dir and document.content:
            os.makedirs(output_text_dir, exist_ok=True)
            out_path = os.path.join(output_text_dir, f"web_{idx}.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(document.content)

    return documents


def extract_profile(config_path="config/applicant.yaml"):
    config = load_config(config_path)
    sources_dir = config["paths"]["sources_dir"]
    output_dir = config["paths"]["output_dir"]
    logs_dir = config["paths"]["logs_dir"]
    ensure_dir(output_dir)
    committee_votes = _load_committee_votes(os.path.join(output_dir, "committee_votes.json"))
    profile_overrides = committee_votes.get("profile", {}) if isinstance(committee_votes, dict) else {}

    output_text_dir = os.path.join(output_dir, "source_texts")
    docs = load_documents(sources_dir, output_text_dir=output_text_dir)
    docs.extend(_load_web_documents(config, output_text_dir))
    inventory = build_inventory(docs)
    write_json(inventory, os.path.join(output_dir, "source_inventory.json"))

    profile_cfg = config.get("profile", {})
    exclude_patterns = profile_cfg.get("source_exclude", [])
    if not exclude_patterns:
        exclude_patterns = ["Sources/ICAR", "ICAR_"]

    used_docs, excluded_docs = _select_profile_docs(docs, exclude_patterns)
    combined_text = "\n\n".join([doc.content for doc in used_docs if doc.content])
    lines = _normalize_lines(combined_text)

    profile = {
        "identity": {
            "name": config.get("profile", {}).get("name", ""),
            "location": config.get("profile", {}).get("location", ""),
            "email": config.get("profile", {}).get("email", ""),
        },
        "hard_skills": [],
        "soft_skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "evidence": {},
        "notes": [],
        "source_files": [doc.path for doc in docs],
        "source_files_used": [doc.path for doc in used_docs],
        "source_files_excluded": excluded_docs,
    }

    emails = _extract_emails(combined_text)
    if emails and not profile["identity"]["email"]:
        selected_email, candidates = _select_profile_email(emails, profile, config, profile_overrides.get("emails", {}))
        if selected_email:
            profile["identity"]["email"] = selected_email
        else:
            profile["notes"].append("Email candidates rejected as low confidence; set profile.email in config.")
        if candidates:
            profile["identity"]["email_candidates"] = candidates

    hard, soft, evidence = _extract_skills(combined_text, config.get("skills_seed", {}))
    profile["hard_skills"] = hard
    profile["soft_skills"] = soft
    profile["evidence"].update(evidence)

    skills_lines = _find_section(lines, SECTION_HEADERS["skills"])
    if skills_lines:
        raw_skills = []
        for line in skills_lines:
            if ":" in line:
                _, right = line.split(":", 1)
                raw_skills.extend(_split_skill_items(right))
            else:
                raw_skills.extend(_split_skill_items(line))
        for skill in raw_skills:
            if skill not in profile["hard_skills"] and skill not in profile["soft_skills"]:
                profile["hard_skills"].append(skill)

    categories = _extract_skill_categories(lines)
    for label, items in categories.items():
        for item in items:
            if item in profile["hard_skills"] or item in profile["soft_skills"]:
                continue
            bucket = _classify_skill(item)
            if bucket == "soft":
                profile["soft_skills"].append(item)
            else:
                profile["hard_skills"].append(item)
        profile["evidence"].setdefault(label, ", ".join(items[:5]))

    exp_entries = _extract_experience_entries(combined_text)
    edu_entries = _extract_simple_section(
        combined_text,
        ["academic background", "education:", "education -"],
        ["skills - roble", "skills & competencies", "projects", "project experience"],
    )
    proj_entries = _extract_simple_section(
        combined_text,
        ["projects - roble", "projects december", "project experience", "academic research", "research project"],
        ["skills - roble", "skills & competencies", "education:", "education -"],
    )

    if not exp_entries:
        exp_lines = _find_section(lines, SECTION_HEADERS["experience"])
        exp_entries = _section_entries(exp_lines)

    if not edu_entries:
        edu_lines = _find_section(lines, SECTION_HEADERS["education"])
        edu_entries = _section_entries(edu_lines)

    if not proj_entries:
        proj_lines = _find_section(lines, SECTION_HEADERS["projects"])
        proj_entries = _section_entries(proj_lines)

    profile["experience"] = exp_entries
    profile["education"] = edu_entries
    profile["projects"] = proj_entries

    if not profile["experience"]:
        profile["notes"].append("Experience section not detected; add or verify manually.")
    if not profile["hard_skills"] and not profile["soft_skills"]:
        profile["notes"].append("No skills detected; update skills_seed in config.")
    if excluded_docs:
        profile["notes"].append("Some sources were excluded from profile extraction; see source_files_excluded.")

    profile["hard_skills"] = list(dict.fromkeys(profile["hard_skills"]))
    profile["soft_skills"] = list(dict.fromkeys(profile["soft_skills"]))
    profile["skill_weighting"] = _build_skill_weighting(
        profile,
        combined_text,
        config,
        committee_cfg=config.get("profile", {}).get("committee", {}),
        overrides=profile_overrides,
    )
    profile["role_abstractions"] = _build_role_abstractions(profile["skill_weighting"], overrides=profile_overrides)
    profile["capability_baseline"] = _build_capability_baseline(profile, combined_text, config)
    role_intent, intent_signals = _infer_role_intent(profile, combined_text)
    profile["role_intent"] = role_intent
    profile["role_intent_signals"] = intent_signals

    held_skills = []
    for entry in profile.get("skill_weighting", {}).get("entries", []):
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

    held_abstractions = profile.get("role_abstractions", {}).get("held", []) or []
    held_emails = []
    email_candidates = (profile.get("identity") or {}).get("email_candidates") or []
    if email_candidates and not (profile.get("identity") or {}).get("email"):
        held_emails = email_candidates

    committee_review = {
        "skills": held_skills,
        "abstractions": held_abstractions,
        "emails": held_emails,
        "action": "agent_review",
        "notes": "Held items require agent review before use in assessment or abstraction.",
    }
    profile["committee_review"] = committee_review

    local_docs = [doc for doc in used_docs if not doc.path.startswith("web:")]
    web_docs = [doc for doc in used_docs if doc.path.startswith("web:")]
    local_text = "\n\n".join([doc.content for doc in local_docs if doc.content])
    web_text = "\n\n".join([doc.content for doc in web_docs if doc.content])

    local_hard, local_soft = _extract_skill_lists(local_text, config)
    web_hard, web_soft = _extract_skill_lists(web_text, config)

    local_set = set(local_hard + local_soft)
    web_set = set(web_hard + web_soft)
    comparison = {
        "local": {
            "hard_skills": sorted(local_hard),
            "soft_skills": sorted(local_soft),
            "total": len(local_set),
        },
        "web": {
            "hard_skills": sorted(web_hard),
            "soft_skills": sorted(web_soft),
            "total": len(web_set),
        },
        "overlap": sorted(local_set & web_set),
        "local_only": sorted(local_set - web_set),
        "web_only": sorted(web_set - local_set),
    }
    write_json(comparison, os.path.join(output_dir, "profile_comparison.json"))

    write_json(committee_review, os.path.join(output_dir, "committee_review.json"))
    write_json(profile, os.path.join(output_dir, "rob_profile.json"))
    log_message(logs_dir, "extract_profile", f"Extracted profile from {len(docs)} documents")
    if held_skills or held_abstractions or held_emails:
        log_message(logs_dir, "extract_profile", "Committee review queued; see committee_review.json")
    return profile


if __name__ == "__main__":
    extract_profile()
