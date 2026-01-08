import os

from utils.io import load_config, read_json, write_json, log_message
from utils.db import db_enabled, init_db, load_votes as db_load_votes
from utils.translator import detect_language
from utils.exporter import build_cover_letter_text, export_docx, export_pdf


def _load_prompt(prompts_dir, filename):
    path = os.path.join(prompts_dir, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def _choose_skills(profile, max_count):
    skills = profile.get("hard_skills", []) + profile.get("soft_skills", [])
    return skills[:max_count]


def _load_template(prompts_dir, lang, role_family=None):
    candidates = []
    if role_family:
        candidates.append(f"cover_letter_{lang}_{role_family}.txt")
        candidates.append(f"cover_letter_{role_family}.txt")
    candidates.append("cover_letter_de.txt" if lang == "de" else "cover_letter_en.txt")
    candidates.append("cover_letter_en.txt")
    for filename in candidates:
        template = _load_prompt(prompts_dir, filename)
        if template:
            return template, filename
    return "", ""


def _cover_letter_context(job, profile, config, max_skills, lang):
    identity = profile.get("identity", {}) or {}
    name = identity.get("name") or config.get("profile", {}).get("name") or "Applicant"
    email = identity.get("email") or config.get("profile", {}).get("email") or ""
    skills = _choose_skills(profile, max_skills)
    skills_str = ", ".join(skills) if skills else ("relevant experience" if lang != "de" else "relevanter Erfahrung")
    letter_date = config.get("drafting", {}).get("letter_date", "")
    return {
        "date": letter_date,
        "name": name,
        "email": email,
        "title": job.get("title", "Role"),
        "company": job.get("company", "Company"),
        "skills": skills_str,
    }


def create_cover_letter(job, profile, config, lang, max_skills, role_family=None):
    template, filename = _load_template(config["paths"]["prompts_dir"], lang, role_family=role_family)
    if not template:
        template, filename = _load_template(config["paths"]["prompts_dir"], "en", role_family=role_family)
    context = _cover_letter_context(job, profile, config, max_skills, lang)
    return build_cover_letter_text(template, context), filename


def _load_template_overrides(output_dir):
    path = os.path.join(output_dir, "template_overrides.json")
    if os.path.exists(path):
        try:
            return read_json(path)
        except Exception:
            return {}
    return {}


def _copy_previous_package(path):
    if not os.path.exists(path):
        return ""
    base, ext = os.path.splitext(path)
    prev_path = f"{base}_prev{ext}"
    try:
        current = read_json(path)
        write_json(current, prev_path)
        return prev_path
    except Exception:
        return ""


def generate_app(config_path="config/applicant.yaml"):
    config = load_config(config_path)
    output_dir = config["paths"]["output_dir"]
    prompts_dir = config["paths"]["prompts_dir"]
    logs_dir = config["paths"]["logs_dir"]

    profile = read_json(os.path.join(output_dir, "rob_profile.json"))
    matches = read_json(os.path.join(output_dir, "matched_jobs.json"))

    top_n = config.get("matching", {}).get("top_n", 5)
    min_score = config.get("matching", {}).get("min_score", 0.0)
    max_skills = config.get("drafting", {}).get("max_skills_in_letter", 3)
    require_review = config.get("drafting", {}).get("require_review", True)
    attachments = config.get("drafting", {}).get("attachments", [])
    use_votes = config.get("review", {}).get("use_votes", True)
    drafting_cfg = config.get("drafting", {}) or {}
    default_role_family = drafting_cfg.get("default_role_family", "")
    template_overrides = _load_template_overrides(output_dir)

    cover_prompt = _load_prompt(prompts_dir, "icar_cover_letter_detail.txt")
    umbrella_prompt = _load_prompt(prompts_dir, "icar_umbrella.txt")
    reference_prompt = _load_prompt(prompts_dir, "icar_reference_letter_detail.txt")

    output_app_dir = os.path.join(output_dir, "applications")
    os.makedirs(output_app_dir, exist_ok=True)

    filtered = [m for m in matches if m.get("score", 0.0) >= min_score][:top_n]

    if not use_votes:
        log_message(logs_dir, "generate_app", "Review votes disabled in config; review gate still enforced.")
    if not require_review:
        log_message(logs_dir, "generate_app", "Drafting require_review disabled in config; forcing review_required true.")

    votes = {}
    votes_path = os.path.join(output_dir, "review_votes.json")
    if db_enabled(config):
        init_db(config)
        votes = db_load_votes(config)
    elif os.path.exists(votes_path):
        votes = read_json(votes_path)
    else:
        log_message(logs_dir, "generate_app", "No review_votes.json found; skipping draft generation")
        return []

    filtered = [m for m in filtered if votes.get(m.get("id"), {}).get("vote") == "approve"]

    for idx, match in enumerate(filtered, start=1):
        job = dict(match.get("job", {}) or {})
        lang = job.get("language") or detect_language(job.get("description", ""))
        job_id = job.get("id")
        role_family = template_overrides.get(str(job_id), default_role_family) if job_id else default_role_family
        letter, template_file = create_cover_letter(job, profile, config, lang, max_skills, role_family=role_family)

        email = job.get("contact_email")
        if not email:
            domain = job.get("company", "company").lower().replace(" ", "")
            email = f"hr@{domain}.com"

        job["template_family"] = role_family
        job["template_file"] = template_file

        package = {
            "job_id": job.get("id"),
            "to": email,
            "subject": f"Application for {job.get('title', 'Role')}",
            "body_draft": letter,
            "attachments": attachments,
            "review_required": True,
            "notes": ["Review required before any external use."],
            "template": {"family": role_family, "file": template_file},
            "exports": {
                "docx": f"application_{idx}.docx",
                "pdf": f"application_{idx}.pdf",
            },
            "prompt_bundle": {
                "icar_umbrella": umbrella_prompt,
                "icar_cover_letter_detail": cover_prompt,
                "icar_reference_letter_detail": reference_prompt,
                "profile": profile,
                "job": job,
                "match": match,
            },
        }

        output_path = os.path.join(output_app_dir, f"application_{idx}.json")
        _copy_previous_package(output_path)
        write_json(package, output_path)

        docx_path = os.path.join(output_app_dir, f"application_{idx}.docx")
        pdf_path = os.path.join(output_app_dir, f"application_{idx}.pdf")
        export_docx(letter, docx_path)
        export_pdf(letter, pdf_path)

    log_message(logs_dir, "generate_app", f"Generated {len(filtered)} application drafts")
    return filtered


if __name__ == "__main__":
    generate_app()
