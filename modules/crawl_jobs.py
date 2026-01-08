import difflib
import hashlib
import json
import os
import re
from datetime import datetime
from urllib.request import Request, urlopen

from utils.io import load_config, read_json, write_json, log_message, ensure_dir
from utils.sanitizer import sanitize_text, strip_html
from utils.translator import detect_language
from utils.web import fetch_url_text
from modules.adapters import get_enabled_adapters


def _slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "job"


def _strip_html(text):
    return strip_html(text)


def _sanitize_text(text):
    return sanitize_text(text)


def _build_job_id(source_id, external_id, url, title, location):
    source_id = (source_id or "unknown").strip().lower()
    external_id = (external_id or "").strip()
    url = (url or "").strip()
    title = (title or "").strip().lower()
    location = (location or "").strip().lower()
    anchor = external_id or url
    payload = f"{source_id}|{anchor}|{title}|{location}"
    payload = re.sub(r"\s+", " ", payload).strip()
    if not payload:
        return ""
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{source_id}:{digest[:12]}"


def _fetch_job_text(url, timeout, logs_dir=None, label=""):
    if not url:
        return ""
    text, status = fetch_url_text(url, timeout=timeout)
    if not text and logs_dir:
        target = label or url
        log_message(logs_dir, "crawl_jobs", f"Job page fetch failed for {target}: {status}")
    return text


def _truncate_text(text, limit=240):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _diff_preview(raw, sanitized, max_lines=8, max_chars=400):
    if raw == sanitized:
        return ""
    diff = list(difflib.unified_diff(raw.splitlines(), sanitized.splitlines(), lineterm=""))
    if not diff:
        return ""
    preview = "\n".join(diff[:max_lines])
    if len(preview) > max_chars:
        preview = preview[:max_chars].rstrip() + "..."
    return preview


def _log_sanitization_event(logs_dir, job_id, title, company, raw, sanitized, notes, index=0):
    if not logs_dir:
        return ""
    safe_job_id = str(job_id or f"job-{index}").strip() or f"job-{index}"
    record = {
        "job_id": safe_job_id,
        "title": title or "",
        "company": company or "",
        "raw_preview": _truncate_text(raw, 240),
        "sanitized_preview": _truncate_text(sanitized, 240),
        "diff_preview": _diff_preview(raw or "", sanitized or ""),
        "unsafe_patterns": notes or [],
        "has_changes": (raw or "") != (sanitized or ""),
        "raw_length": len(raw or ""),
        "sanitized_length": len(sanitized or ""),
        "logged_at": datetime.utcnow().isoformat() + "Z",
    }
    log_dir = os.path.join(logs_dir, "sanitization")
    ensure_dir(log_dir)
    timestamp = record["logged_at"].replace(":", "").replace(".", "")
    filename = f"{timestamp}_{_slugify(str(safe_job_id))}.json"
    path = os.path.join(log_dir, filename)
    write_json(record, path)
    return path


def _export_adapter_jobs(adapter_name, jobs, jobs_dir, logs_dir):
    if not jobs:
        return
    raw_path = os.path.join(jobs_dir, f"adapter_{adapter_name}_raw.json")
    write_json(jobs, raw_path)

    sanitized_jobs = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        description_raw = job.get("description", "")
        sanitized, notes = _sanitize_text(description_raw)
        item = dict(job)
        item["description_raw"] = description_raw
        item["description"] = sanitized
        item["sanitization_notes"] = notes
        sanitized_jobs.append(item)
    sanitized_path = os.path.join(jobs_dir, f"adapter_{adapter_name}_sanitized.json")
    write_json(sanitized_jobs, sanitized_path)
    if logs_dir:
        log_message(logs_dir, "crawl_jobs", f"Adapter {adapter_name}: exported {len(jobs)} jobs")


def _fetch_json(url, timeout=10, logs_dir=None, label=""):
    try:
        req = Request(url, headers={"User-Agent": "ApplicantMVP/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        return json.loads(raw)
    except Exception as exc:
        if logs_dir:
            target = label or url
            log_message(logs_dir, "crawl_jobs", f"Failed to fetch {target}: {exc}")
        return None


def _fetch_html(url, timeout=10, logs_dir=None, label=""):
    try:
        req = Request(url, headers={"User-Agent": "ApplicantMVP/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        if logs_dir:
            target = label or url
            log_message(logs_dir, "crawl_jobs", f"Failed to fetch {target}: {exc}")
        return ""


def _extract_json_ld_jobs(raw_html, logs_dir=None, label=""):
    if not raw_html:
        return []
    blocks = re.findall(
        r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    postings = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        try:
            data = json.loads(block)
        except Exception as exc:
            if logs_dir:
                target = label or "job page"
                log_message(logs_dir, "crawl_jobs", f"Failed to parse JSON-LD from {target}: {exc}")
            continue
        postings.extend(_find_job_postings(data))
    return postings


def _find_job_postings(data):
    postings = []
    if isinstance(data, list):
        for item in data:
            postings.extend(_find_job_postings(item))
        return postings
    if not isinstance(data, dict):
        return postings

    if data.get("@type") == "JobPosting":
        postings.append(data)
        return postings

    graph = data.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            postings.extend(_find_job_postings(item))
        return postings

    if data.get("@type") == "ItemList":
        elements = data.get("itemListElement") or []
        for element in elements:
            postings.extend(_find_job_postings(element))
        return postings

    return postings


def _job_location_from_posting(posting):
    location = ""
    job_location = posting.get("jobLocation")
    if isinstance(job_location, list):
        for item in job_location:
            location = _job_location_from_posting({"jobLocation": item})
            if location:
                return location
    if isinstance(job_location, dict):
        place = job_location.get("address") or job_location.get("name") or ""
        if isinstance(place, dict):
            parts = [
                place.get("addressLocality"),
                place.get("addressRegion"),
                place.get("addressCountry"),
            ]
            location = ", ".join([part for part in parts if part])
        elif isinstance(place, str):
            location = place
    if not location and posting.get("jobLocationType"):
        if "telecommute" in str(posting.get("jobLocationType")).lower():
            location = "Remote"
    if not location and posting.get("applicantLocationRequirements"):
        req = posting.get("applicantLocationRequirements")
        if isinstance(req, dict):
            location = req.get("name", "") or req.get("address", "") or ""
        elif isinstance(req, str):
            location = req
    return location.strip()


def _job_id_from_posting(posting):
    identifier = posting.get("identifier")
    if isinstance(identifier, dict):
        identifier = identifier.get("value") or identifier.get("name") or identifier.get("propertyID")
    if identifier:
        return str(identifier)
    return ""


def _normalize_job_posting(posting, fallback_company="", fallback_url=""):
    title = posting.get("title", "") or ""
    company = fallback_company
    hiring = posting.get("hiringOrganization") or {}
    if isinstance(hiring, dict):
        company = hiring.get("name") or company
    elif isinstance(hiring, str):
        company = hiring
    description = _strip_html(posting.get("description") or "")
    location = _job_location_from_posting(posting)
    url = posting.get("url") or posting.get("applyUrl") or fallback_url
    job_id = _job_id_from_posting(posting)
    if not job_id:
        job_id = _slugify(f"{company}-{title}")
    return {
        "id": job_id,
        "title": title.strip(),
        "company": company.strip(),
        "location": location,
        "description": description,
        "source": "job_page",
        "source_type": "job_page",
        "url": url,
    }


def _load_job_pages(job_pages, timeout, logs_dir):
    jobs = []
    for entry in job_pages:
        if isinstance(entry, dict):
            url = entry.get("url", "")
            company = entry.get("company", "")
        else:
            url = entry
            company = ""
        if not url:
            continue
        html = _fetch_html(url, timeout=timeout, logs_dir=logs_dir, label=f"job_page:{url}")
        postings = _extract_json_ld_jobs(html, logs_dir=logs_dir, label=url)
        for posting in postings:
            normalized = _normalize_job_posting(posting, fallback_company=company, fallback_url=url)
            if normalized.get("title") and normalized.get("company"):
                jobs.append(normalized)
    return jobs


def _fetch_greenhouse(board, company_name, timeout, logs_dir):
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    data = _fetch_json(url, timeout=timeout, logs_dir=logs_dir, label=f"greenhouse:{board}")
    if not data:
        return []
    jobs = []
    source_id = f"greenhouse:{board}"
    for job in data.get("jobs", []):
        content = job.get("content") or ""
        if not content and job.get("id"):
            detail_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job.get('id')}"
            detail = _fetch_json(detail_url, timeout=timeout, logs_dir=logs_dir, label=f"greenhouse:{board}:{job.get('id')}")
            if detail:
                content = detail.get("content") or detail.get("content_text") or detail.get("description") or ""
        jobs.append(
            {
                "id": job.get("id"),
                "title": job.get("title", ""),
                "company": company_name,
                "location": (job.get("location") or {}).get("name", ""),
                "description": _strip_html(content),
                "source": source_id,
                "source_type": "ats",
                "source_id": source_id,
                "url": job.get("absolute_url", ""),
            }
        )
    return jobs


def _fetch_lever(company_slug, company_name, timeout, logs_dir):
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    data = _fetch_json(url, timeout=timeout, logs_dir=logs_dir, label=f"lever:{company_slug}")
    if not data:
        return []
    jobs = []
    source_id = f"lever:{company_slug}"
    for job in data:
        categories = job.get("categories") or {}
        description = job.get("descriptionPlain") or job.get("description") or job.get("text") or ""
        jobs.append(
            {
                "id": job.get("id"),
                "title": job.get("text", ""),
                "company": company_name,
                "location": categories.get("location", ""),
                "description": _strip_html(description),
                "source": source_id,
                "source_type": "ats",
                "source_id": source_id,
                "url": job.get("hostedUrl", ""),
            }
        )
    return jobs


def _fetch_ashby(company_slug, company_name, timeout, logs_dir):
    url = f"https://jobs.ashbyhq.com/{company_slug}.json"
    data = _fetch_json(url, timeout=timeout, logs_dir=logs_dir, label=f"ashby:{company_slug}")
    if not data:
        return []
    jobs = []
    source_id = f"ashby:{company_slug}"
    for job in data.get("jobs", []):
        location = ""
        job_location = job.get("location") or {}
        if isinstance(job_location, dict):
            location = job_location.get("location", "") or job_location.get("name", "")
        elif isinstance(job_location, str):
            location = job_location
        description = job.get("descriptionPlain") or job.get("description") or ""
        jobs.append(
            {
                "id": job.get("id"),
                "title": job.get("title", ""),
                "company": company_name,
                "location": location,
                "description": _strip_html(description),
                "source": source_id,
                "source_type": "ats",
                "source_id": source_id,
                "url": job.get("jobUrl", "") or job.get("absoluteUrl", "") or job.get("url", ""),
            }
        )
    return jobs


def _load_job_files(jobs_dir):
    jobs = []
    for filename in os.listdir(jobs_dir):
        if not filename.endswith(".json"):
            continue
        if filename == "latest_jobs.json":
            continue
        path = os.path.join(jobs_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                if not item.get("source"):
                    item["source"] = "manual"
                item.setdefault("source_type", "manual")
                item.setdefault("source_id", item.get("source"))
                jobs.append(item)
    return jobs


def _limit_list(items, limit):
    if not limit or limit <= 0:
        return items
    return items[:limit]


def _load_ats_jobs(ats_companies, timeout, max_per_company, logs_dir):
    jobs = []
    for entry in ats_companies:
        provider = (entry.get("provider") or "").lower()
        company_name = entry.get("company") or entry.get("name") or entry.get("board") or entry.get("slug") or ""
        board = entry.get("board") or entry.get("slug") or entry.get("company") or ""
        if not provider or not board:
            continue

        fetched = []
        if provider == "greenhouse":
            fetched = _fetch_greenhouse(board, company_name, timeout, logs_dir)
        elif provider == "lever":
            fetched = _fetch_lever(board, company_name, timeout, logs_dir)
        elif provider == "ashby":
            fetched = _fetch_ashby(board, company_name, timeout, logs_dir)
        jobs.extend(_limit_list(fetched, max_per_company))
    return jobs


def _matches_filters(job, filters):
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    include = [k.lower() for k in filters.get("include_keywords", [])]
    exclude = [k.lower() for k in filters.get("exclude_keywords", [])]
    location_allow = [k.lower() for k in filters.get("location_allow", [])]
    location_block = [k.lower() for k in filters.get("location_block", [])]
    location = (job.get("location") or "").lower()
    description = (job.get("description") or "").lower()

    if include and not any(k in text for k in include):
        return False
    if exclude and any(k in text for k in exclude):
        return False
    if location_allow:
        allow_hit = location and any(k in location for k in location_allow)
        if not allow_hit:
            remote_keys = [k for k in location_allow if k in {"remote", "hybrid", "distributed"}]
            if remote_keys and any(key in description for key in remote_keys):
                allow_hit = True
        if not allow_hit:
            return False
    if location_block:
        haystack = location or description
        if any(k in haystack for k in location_block):
            return False
    return True


def _dedupe_list(items):
    seen = set()
    deduped = []
    for item in items:
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_keyword(term):
    term = re.sub(r"\s+", " ", (term or "").strip())
    term = term.strip(" -–—•.;:,")
    if not term or len(term) < 2 or len(term) > 60:
        return ""
    if re.match(r"^[\\W_]+$", term):
        return ""
    return term


def _derive_job_filters(profile, config):
    derived = {"include_keywords": [], "location_allow": [], "location_block": []}
    if not profile:
        return derived

    weighting = profile.get("skill_weighting", {}) or {}
    entries = [entry for entry in (weighting.get("entries") or []) if entry.get("committee", {}).get("decision") == "accept"]
    entries.sort(key=lambda x: (-x.get("weight", 0), x.get("skill", "").lower()))
    max_keywords = config.get("job_filters", {}).get("derived_max_keywords", 40)
    try:
        max_keywords = int(max_keywords)
    except (TypeError, ValueError):
        max_keywords = 40

    for entry in entries[:max_keywords]:
        keyword = _normalize_keyword(entry.get("skill"))
        if keyword:
            derived["include_keywords"].append(keyword)

    abstractions = profile.get("role_abstractions", {}) or {}
    for cap in abstractions.get("capabilities", []) or []:
        if cap.get("decision") != "accept":
            continue
        keyword = _normalize_keyword(cap.get("category"))
        if keyword:
            derived["include_keywords"].append(keyword)
    for trait in abstractions.get("traits", []) or []:
        if trait.get("decision") != "accept":
            continue
        keyword = _normalize_keyword(trait.get("trait"))
        if keyword:
            derived["include_keywords"].append(keyword)

    identity = profile.get("identity", {}) or {}
    location = identity.get("location") or ""
    if location:
        derived["location_allow"].append(location)
        for part in re.split(r"[,/]|\\s{2,}", location):
            part = _normalize_keyword(part)
            if part:
                derived["location_allow"].append(part)

    region_keywords = config.get("matching", {}).get("region_keywords", []) or []
    profile_text_parts = []
    for entry in profile.get("experience", []) or []:
        profile_text_parts.append(entry.get("summary", ""))
    for entry in profile.get("projects", []) or []:
        profile_text_parts.append(entry.get("summary", ""))
    for entry in profile.get("education", []) or []:
        profile_text_parts.append(entry.get("summary", ""))
    profile_text = " ".join([part for part in profile_text_parts if part]).lower()

    for keyword in region_keywords:
        if keyword and keyword.lower() in profile_text:
            derived["location_allow"].append(keyword)

    if "remote" in profile_text:
        derived["location_allow"].append("Remote")
    if "hybrid" in profile_text:
        derived["location_allow"].append("Hybrid")

    derived["include_keywords"] = _dedupe_list(derived["include_keywords"])
    derived["location_allow"] = _dedupe_list(derived["location_allow"])
    derived["location_block"] = _dedupe_list(derived["location_block"])
    return derived


def _merge_filters(base, derived):
    merged = {
        "include_keywords": _dedupe_list((base.get("include_keywords") or []) + (derived.get("include_keywords") or [])),
        "exclude_keywords": _dedupe_list((base.get("exclude_keywords") or []) + (derived.get("exclude_keywords") or [])),
        "location_allow": _dedupe_list((base.get("location_allow") or []) + (derived.get("location_allow") or [])),
        "location_block": _dedupe_list((base.get("location_block") or []) + (derived.get("location_block") or [])),
    }
    return merged


def crawl_jobs(config_path="config/applicant.yaml"):
    config = load_config(config_path)
    jobs_dir = config["paths"]["jobs_dir"]
    output_dir = config["paths"]["output_dir"]
    logs_dir = config["paths"]["logs_dir"]
    ensure_dir(jobs_dir)
    ensure_dir(output_dir)

    job_sources = config.get("job_sources", {})
    job_filters = config.get("job_filters", {})
    derived_filters = {}
    derived_enabled = job_filters.get("derived_enabled", True)
    profile_path = os.path.join(output_dir, "rob_profile.json")
    if derived_enabled and os.path.exists(profile_path):
        try:
            profile = read_json(profile_path)
            derived_filters = _derive_job_filters(profile, config)
            job_filters = _merge_filters(job_filters, derived_filters)
            write_json(
                {"derived": derived_filters, "merged": job_filters},
                os.path.join(output_dir, "derived_job_filters.json"),
            )
        except Exception as exc:
            log_message(logs_dir, "crawl_jobs", f"Failed to derive job filters: {exc}")

    fetch_timeout = job_sources.get("fetch_timeout_seconds", 10)
    max_per_company = job_sources.get("max_per_company", 0)
    max_total = job_sources.get("max_total", 0)
    try:
        fetch_timeout = int(fetch_timeout)
    except (TypeError, ValueError):
        fetch_timeout = 10
    try:
        max_per_company = int(max_per_company)
    except (TypeError, ValueError):
        max_per_company = 0
    try:
        max_total = int(max_total)
    except (TypeError, ValueError):
        max_total = 0

    jobs = []
    manual_jobs = []
    ats_jobs = []
    page_jobs = []
    if job_sources.get("use_manual_files", True):
        manual_jobs = _load_job_files(jobs_dir)
        jobs.extend(manual_jobs)
    if job_sources.get("use_ats", False):
        ats_jobs = _load_ats_jobs(job_sources.get("ats_companies", []), fetch_timeout, max_per_company, logs_dir)
        jobs.extend(ats_jobs)
    adapter_jobs = []
    adapters = get_enabled_adapters(config, logs_dir=logs_dir)
    for adapter in adapters:
        fetched = adapter.fetch_jobs()
        if fetched:
            adapter_jobs.extend(fetched)
            _export_adapter_jobs(adapter.name, fetched, jobs_dir, logs_dir)
    if adapter_jobs:
        jobs.extend(adapter_jobs)
    job_pages = job_sources.get("job_pages", []) or []
    use_job_pages = job_sources.get("use_job_pages", bool(job_pages))
    if use_job_pages and job_pages:
        page_jobs = _load_job_pages(job_pages, fetch_timeout, logs_dir)
        jobs.extend(page_jobs)

    log_message(
        logs_dir,
        "crawl_jobs",
        (
            f"Loaded {len(jobs)} raw jobs (manual={len(manual_jobs)}, ats={len(ats_jobs)}, "
            f"pages={len(page_jobs)}, adapters={len(adapter_jobs)})"
        ),
    )
    normalized = []
    filtered_out = 0
    seen_ids = {}
    duplicates = 0

    for idx, job in enumerate(jobs, start=1):
        if not isinstance(job, dict):
            continue
        title = job.get("title", "").strip()
        company = job.get("company", "").strip()
        location = job.get("location", "").strip()
        source_id = (job.get("source_id") or job.get("source") or "").strip()
        source_type = (job.get("source_type") or "").strip()
        url = job.get("url", "").strip()
        external_id = job.get("id")

        description_raw = job.get("description", "") or ""
        if "<" in description_raw or "&lt;" in description_raw:
            description_raw = _strip_html(description_raw)
        if source_type == "rss" and len(description_raw.strip()) < 200 and url:
            fetched_text = _fetch_job_text(url, fetch_timeout, logs_dir=logs_dir, label=title)
            if fetched_text:
                description_raw = fetched_text

        sanitized, notes = _sanitize_text(description_raw)
        description = sanitized
        job_id = _build_job_id(source_id, str(external_id or ""), url, title, location)
        if not job_id:
            job_id = _slugify(f"{source_id}-{title}-{location}-{idx}")
        _log_sanitization_event(logs_dir, job_id, title, company, description_raw, description, notes, index=idx)

        if not title or not company:
            continue
        language = job.get("language") or detect_language(description)
        text_missing = len(description) < 200

        normalized_job = {
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "language": language,
            "description": description,
            "description_raw": description_raw,
            "sanitization_notes": notes,
            "source": source_id,
            "source_intent": job.get("source_intent", ""),
            "source_type": source_type,
            "external_id": external_id,
            "text_missing": text_missing,
            "url": url,
            "contact_email": job.get("contact_email", ""),
        }

        if notes and logs_dir:
            log_message(
                logs_dir,
                "crawl_jobs",
                f"Sanitized job description for {company} - {title}: {', '.join(notes)}",
            )

        if _matches_filters(normalized_job, job_filters):
            existing = seen_ids.get(job_id)
            if existing:
                duplicates += 1
                if len(description) > len(existing.get("description", "")):
                    seen_ids[job_id] = normalized_job
            else:
                seen_ids[job_id] = normalized_job
        else:
            filtered_out += 1

    normalized = list(seen_ids.values())
    if duplicates and logs_dir:
        log_message(logs_dir, "crawl_jobs", f"Dropped {duplicates} duplicate jobs by job_id.")

    limited = _limit_list(normalized, max_total)
    truncated = len(normalized) - len(limited)
    normalized = limited

    source_counts = {}
    for job in normalized:
        source_key = job.get("source") or "unknown"
        source_type = job.get("source_type") or "unknown"
        key = (source_key, source_type)
        source_counts[key] = source_counts.get(key, 0) + 1
    source_inventory = []
    for (source_key, source_type), count in sorted(source_counts.items(), key=lambda item: (-item[1], item[0][0])):
        source_inventory.append(
            {
                "source_id": source_key,
                "source_type": source_type,
                "count": count,
            }
        )

    text_missing_count = sum(1 for job in normalized if job.get("text_missing"))
    summary = {
        "raw_total": len(jobs),
        "manual_total": len(manual_jobs),
        "ats_total": len(ats_jobs),
        "job_page_total": len(page_jobs),
        "normalized_total": len(normalized),
        "filtered_out": filtered_out,
        "deduped": duplicates,
        "text_missing": text_missing_count,
        "truncated": truncated,
        "sources": source_inventory,
        "derived_filters": {
            "enabled": bool(derived_filters),
            "include_keywords": len(derived_filters.get("include_keywords", [])),
            "location_allow": len(derived_filters.get("location_allow", [])),
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    write_json(summary, os.path.join(output_dir, "job_collection_summary.json"))

    output_path = os.path.join(jobs_dir, "latest_jobs.json")
    write_json(normalized, output_path)
    log_message(logs_dir, "crawl_jobs", f"Collected {len(normalized)} jobs from {jobs_dir}")
    return normalized


if __name__ == "__main__":
    crawl_jobs()
