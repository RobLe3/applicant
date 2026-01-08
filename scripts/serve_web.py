import json
import os
import re
import sys
import zipfile
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from utils.io import load_config, read_json, write_json, ensure_dir, log_message  # noqa: E402
from utils.db import init_db, load_votes as db_load_votes, upsert_vote, db_enabled  # noqa: E402
from utils.feedback import load_feedback, record_outcome, latest_outcomes_by_job, build_feedback_tags  # noqa: E402
from modules.crawl_jobs import crawl_jobs, _derive_job_filters, _merge_filters  # noqa: E402
from modules.match_score import match_score  # noqa: E402
from modules.pipeline import run_pipeline  # noqa: E402
from modules.submission_agent import load_applications, submit_application  # noqa: E402


PIPELINE_OUTPUTS = (
    "rob_profile.json",
    "profile_comparison.json",
    "matched_jobs.json",
    "job_suggestions.json",
    "skill_assessment.json",
    "job_collection_summary.json",
    "derived_job_filters.json",
)


def _load_votes(config, path):
    if db_enabled(config):
        init_db(config)
        votes = db_load_votes(config)
    elif os.path.exists(path):
        votes = read_json(path)
    else:
        return {}
    if not isinstance(votes, dict):
        return {}
    normalized = {}
    for key, value in votes.items():
        normalized[str(key)] = value
    return normalized


def _load_optional_json(path, default):
    if os.path.exists(path):
        return read_json(path)
    return default


def _template_overrides_path(output_dir):
    return os.path.join(output_dir, "template_overrides.json")


def _load_template_overrides(output_dir):
    path = _template_overrides_path(output_dir)
    if os.path.exists(path):
        try:
            return read_json(path)
        except Exception:
            return {}
    return {}


def _save_template_overrides(output_dir, overrides):
    path = _template_overrides_path(output_dir)
    write_json(overrides, path)


def _docx_to_text(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        text = re.sub(r"<[^>]+>", "", xml)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception:
        return ""


def _load_previous_application(path):
    base, ext = os.path.splitext(path)
    prev_path = f"{base}_prev{ext}"
    if not os.path.exists(prev_path):
        return {}
    try:
        return read_json(prev_path)
    except Exception:
        return {}


def _default_committee_votes():
    return {"profile": {"skills": {}, "abstractions": {}, "emails": {}}, "jobs": {}}


def _load_committee_votes(path):
    votes = _load_optional_json(path, _default_committee_votes())
    if not isinstance(votes, dict):
        return _default_committee_votes()
    votes.setdefault("profile", {})
    votes.setdefault("jobs", {})
    votes["profile"].setdefault("skills", {})
    votes["profile"].setdefault("abstractions", {})
    votes["profile"].setdefault("emails", {})
    return votes


def _pipeline_outputs_ready(output_dir):
    return all(os.path.exists(os.path.join(output_dir, name)) for name in PIPELINE_OUTPUTS)


def _ensure_pipeline_outputs(config, config_path):
    output_dir = config["paths"]["output_dir"]
    if _pipeline_outputs_ready(output_dir):
        return
    log_message(config["paths"]["logs_dir"], "serve_web", "Pipeline outputs missing; running pipeline.")
    run_pipeline(config_path)


def _feedback_path(config):
    cfg = config.get("matching", {}).get("feedback", {}) or {}
    path = cfg.get("path") or ""
    if path:
        return path
    return os.path.join(config["paths"]["output_dir"], "feedback.json")


def _summarize_application(app, output_dir):
    exports = app.get("exports") or {}
    docx_name = exports.get("docx") or ""
    docx_text = ""
    if docx_name:
        docx_path = os.path.join(output_dir, "applications", docx_name)
        docx_text = _docx_to_text(docx_path)

    previous = {}
    app_path = app.get("_path") or ""
    if app_path:
        previous = _load_previous_application(app_path)

    return {
        "job_id": app.get("job_id"),
        "to": app.get("to"),
        "subject": app.get("subject"),
        "body_draft": app.get("body_draft"),
        "docx_text": docx_text or app.get("body_draft") or "",
        "previous_body_draft": previous.get("body_draft", ""),
        "template": app.get("template") or {},
        "previous_template": previous.get("template") or {},
        "attachments": app.get("attachments") or [],
        "review_required": app.get("review_required", True),
        "exports": exports,
        "submitted": app.get("submitted", False),
        "submitted_at": app.get("submitted_at", ""),
        "draft_created": app.get("draft_created", False),
        "last_submission": app.get("last_submission", {}),
        "file": app.get("_file"),
    }


def _build_ui_snapshot(config):
    output_dir = config["paths"]["output_dir"]
    matches_path = os.path.join(output_dir, "matched_jobs.json")
    votes_path = os.path.join(output_dir, "review_votes.json")
    matches = _load_optional_json(matches_path, [])
    votes = _load_votes(config, votes_path)

    region_keywords = config.get("matching", {}).get("region_keywords", []) or []
    region_options = ["all"] + [item for item in region_keywords if item] + ["Remote", "Hybrid"]
    language_cfg = config.get("language", {}) or {}
    language_options = ["all"] + [lang.lower() for lang in (language_cfg.get("supported") or []) if lang]

    alignment_buckets = {"a90": 0, "a80": 0, "a70": 0, "rest": 0}
    vote_buckets = {"approve": 0, "hold": 0, "reject": 0, "none": 0}
    holding_ids = []

    for match in matches:
        job_id = match.get("id")
        vote = (votes.get(job_id, {}) or {}).get("vote", "none")
        if vote not in vote_buckets:
            vote = "none"
        vote_buckets[vote] += 1
        if vote == "none":
            holding_ids.append(job_id)

        alignment = (match.get("alignment") or {}).get("alignment_score", 0.0) or 0.0
        if alignment >= 0.9:
            alignment_buckets["a90"] += 1
        elif alignment >= 0.8:
            alignment_buckets["a80"] += 1
        elif alignment >= 0.7:
            alignment_buckets["a70"] += 1
        else:
            alignment_buckets["rest"] += 1

    return {
        "filters": {
            "region_options": region_options,
            "language_options": language_options,
            "alignment_default": 0.9,
            "group_default": "vote",
        },
        "grouping": {
            "alignment_buckets": alignment_buckets,
            "vote_buckets": vote_buckets,
        },
        "holding_queue": {
            "count": len(holding_ids),
            "sample_ids": holding_ids[:5],
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


class ReviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def _send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/matches":
            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            matches_path = os.path.join(output_dir, "matched_jobs.json")
            votes_path = os.path.join(output_dir, "review_votes.json")

            matches = read_json(matches_path) if os.path.exists(matches_path) else []
            votes = _load_votes(config, votes_path)

            for match in matches:
                match["decision"] = votes.get(str(match.get("id")), {})

            return self._send_json({"matches": matches})

        if parsed.path == "/api/insights":
            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            suggestions = _load_optional_json(os.path.join(output_dir, "job_suggestions.json"), [])
            assessment = _load_optional_json(os.path.join(output_dir, "skill_assessment.json"), {})
            collection = _load_optional_json(os.path.join(output_dir, "job_collection_summary.json"), {})
            job_committee = _load_optional_json(os.path.join(output_dir, "job_committee_review.json"), {})
            derived_filters = _load_optional_json(os.path.join(output_dir, "derived_job_filters.json"), {})
            return self._send_json(
                {
                    "suggestions": suggestions,
                    "assessment": assessment,
                    "collection": collection,
                    "job_committee_review": job_committee,
                    "derived_filters": derived_filters,
                }
            )

        if parsed.path == "/api/profile":
            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            profile = _load_optional_json(os.path.join(output_dir, "rob_profile.json"), {})
            comparison = _load_optional_json(os.path.join(output_dir, "profile_comparison.json"), {})
            committee_review = _load_optional_json(os.path.join(output_dir, "committee_review.json"), {})
            matching = config.get("matching", {})
            language_cfg = config.get("language", {})
            scoring_cfg = config.get("scoring", {}) or {}
            job_filters = config.get("job_filters", {}) or {}
            drafting_cfg = config.get("drafting", {}) or {}
            template_overrides = _load_template_overrides(output_dir)
            derived_filters = {}
            if profile and job_filters.get("derived_enabled", True):
                try:
                    derived = _derive_job_filters(profile, config)
                    derived_filters = {"derived": derived, "merged": _merge_filters(job_filters, derived)}
                except Exception:
                    derived_filters = {}
            return self._send_json(
                {
                    "profile": profile,
                    "comparison": comparison,
                    "committee_review": committee_review,
                    "matching": {
                        "weights": matching.get("weights", {}),
                        "apply_threshold": matching.get("apply_threshold"),
                        "consider_threshold": matching.get("consider_threshold"),
                        "min_score": matching.get("min_score"),
                        "top_n": matching.get("top_n"),
                        "region_keywords": matching.get("region_keywords", []),
                    },
                    "language": {
                        "default": language_cfg.get("default", "en"),
                        "supported": language_cfg.get("supported", []),
                    },
                    "job_sources": config.get("job_sources", {}),
                    "adapters": config.get("adapters", {}),
                    "job_filters": job_filters,
                    "drafting": {
                        "role_families": drafting_cfg.get("role_families", []) or [],
                        "default_role_family": drafting_cfg.get("default_role_family", ""),
                    },
                    "template_overrides": template_overrides,
                    "scoring": {
                        "active_preset": scoring_cfg.get("active_preset", ""),
                        "presets": scoring_cfg.get("presets", {}),
                    },
                    "derived_filters": derived_filters,
                }
            )

        if parsed.path == "/api/committee":
            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            votes = _load_committee_votes(os.path.join(output_dir, "committee_votes.json"))
            profile_review = _load_optional_json(os.path.join(output_dir, "committee_review.json"), {})
            job_review = _load_optional_json(os.path.join(output_dir, "job_committee_review.json"), {})
            return self._send_json(
                {
                    "votes": votes,
                    "profile_review": profile_review,
                    "job_review": job_review,
                }
            )

        if parsed.path == "/api/applications":
            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            submission_cfg = config.get("submission", {}) or {}
            apps = load_applications(output_dir)
            feedback = load_feedback(_feedback_path(config))
            feedback_map = latest_outcomes_by_job(feedback.get("outcomes"))
            summarized = []
            for app in apps:
                summary = _summarize_application(app, output_dir)
                job_id = summary.get("job_id")
                job_key = str(job_id) if job_id is not None else ""
                if job_key and job_key in feedback_map:
                    summary["feedback"] = feedback_map[job_key]
                summarized.append(summary)
            return self._send_json(
                {
                    "applications": summarized,
                    "submission": {
                        "enabled": bool(submission_cfg.get("enabled", False)),
                        "mode": submission_cfg.get("mode", "draft"),
                        "smtp": submission_cfg.get("smtp", {}) or {},
                    },
                }
            )

        if parsed.path == "/api/ui_snapshot":
            config = load_config("config/applicant.yaml")
            snapshot = _build_ui_snapshot(config)
            return self._send_json(snapshot)

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/crawl":
            crawl_jobs("config/applicant.yaml")
            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            summary = _load_optional_json(os.path.join(output_dir, "job_collection_summary.json"), {})
            return self._send_json({"ok": True, "summary": summary})

        if parsed.path == "/api/score":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            payload = {}
            if raw.strip():
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    return self._send_json({"error": "invalid json"}, status=400)
            feedback_enabled = payload.get("feedback_enabled")
            preset_name = payload.get("preset")
            match_score("config/applicant.yaml", feedback_enabled=feedback_enabled, preset_name=preset_name)
            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            suggestions = _load_optional_json(os.path.join(output_dir, "job_suggestions.json"), [])
            assessment = _load_optional_json(os.path.join(output_dir, "skill_assessment.json"), {})
            return self._send_json({"ok": True, "suggestions": suggestions, "assessment": assessment})

        if parsed.path == "/api/template":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, status=400)

            job_id = payload.get("job_id")
            if job_id is None:
                return self._send_json({"error": "job_id required"}, status=400)

            role_family = payload.get("role_family") or ""
            if role_family == "default":
                role_family = ""

            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            overrides = _load_template_overrides(output_dir)
            key = str(job_id)
            if role_family:
                overrides[key] = role_family
            else:
                overrides.pop(key, None)
            _save_template_overrides(output_dir, overrides)
            return self._send_json({"ok": True, "template_overrides": overrides})

        if parsed.path == "/api/submit":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, status=400)

            config = load_config("config/applicant.yaml")
            submission_cfg = config.get("submission", {}) or {}
            if not submission_cfg.get("enabled", False):
                return self._send_json({"error": "submission disabled"}, status=400)

            checklist = payload.get("checklist", {}) or {}
            if not checklist or not all(checklist.values()):
                return self._send_json({"error": "checklist incomplete"}, status=400)

            mode = payload.get("mode") or submission_cfg.get("mode", "draft")
            if mode not in {"draft", "smtp", "form"}:
                return self._send_json({"error": "invalid mode"}, status=400)
            if mode == "smtp":
                smtp_cfg = submission_cfg.get("smtp", {}) or {}
                if not smtp_cfg.get("enabled", False):
                    return self._send_json({"error": "smtp disabled"}, status=400)
                if not payload.get("dispatch", False):
                    return self._send_json({"error": "smtp dispatch not approved"}, status=400)

            output_dir = config["paths"]["output_dir"]
            job_id = payload.get("job_id")
            filename = payload.get("file")
            apps = load_applications(output_dir)
            app = None
            for item in apps:
                if filename and item.get("_file") == filename:
                    app = item
                    break
                if job_id and str(item.get("job_id")) == str(job_id):
                    app = item
                    break
            if not app:
                return self._send_json({"error": "application not found"}, status=404)
            if not app.get("review_required", True):
                return self._send_json({"error": "review gate not satisfied"}, status=400)

            votes_path = os.path.join(output_dir, "review_votes.json")
            votes = _load_votes(config, votes_path)
            job_key = str(app.get("job_id") or job_id)
            if votes.get(job_key, {}).get("vote") != "approve":
                return self._send_json({"error": "job not approved"}, status=400)

            overrides = {
                "to": payload.get("to"),
                "subject": payload.get("subject"),
                "body": payload.get("body"),
                "attachments": payload.get("attachments"),
                "from": payload.get("from"),
            }
            try:
                result = submit_application(
                    config,
                    job_id=app.get("job_id"),
                    filename=app.get("_file"),
                    mode=mode,
                    overrides=overrides,
                    dispatch=payload.get("dispatch", False),
                )
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=400)
            return self._send_json({"ok": True, "result": result})

        if parsed.path == "/api/feedback":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, status=400)

            job_id = payload.get("job_id")
            outcome = (payload.get("outcome") or "").lower()
            note = payload.get("note", "")
            if not job_id or outcome not in {"accepted", "rejected", "interview", "no_response"}:
                return self._send_json({"error": "invalid job_id or outcome"}, status=400)

            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            matches_path = os.path.join(output_dir, "matched_jobs.json")
            matches = read_json(matches_path) if os.path.exists(matches_path) else []
            match = next((row for row in matches if str(row.get("id")) == str(job_id)), None)
            if not match:
                return self._send_json({"error": "job not found"}, status=404)
            apps = load_applications(output_dir)
            if not any(str(app.get("job_id")) == str(job_id) for app in apps):
                return self._send_json({"error": "application not found"}, status=404)
            job = match.get("job") or {}
            job_facts = match.get("job_facts") or {}
            tags = build_feedback_tags(job, job_facts)
            feedback_path = _feedback_path(config)
            entry = record_outcome(
                feedback_path,
                str(job_id),
                outcome,
                tags,
                job_meta={
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                },
                note=note,
            )
            return self._send_json({"ok": True, "entry": entry})

        if parsed.path == "/api/vote":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, status=400)

            job_id = str(payload.get("job_id") or "")
            vote = payload.get("vote")
            note = payload.get("note", "")
            if not job_id or vote not in {"approve", "hold", "reject"}:
                return self._send_json({"error": "missing job_id or invalid vote"}, status=400)

            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            ensure_dir(output_dir)
            votes_path = os.path.join(output_dir, "review_votes.json")

            if db_enabled(config):
                updated_at = upsert_vote(config, job_id, vote, note)
                votes = _load_votes(config, votes_path)
                votes[job_id] = {"vote": vote, "note": note, "updated_at": updated_at}
                write_json(votes, votes_path)
            else:
                votes = _load_votes(config, votes_path)
                votes[job_id] = {
                    "vote": vote,
                    "note": note,
                    "updated_at": datetime.utcnow().isoformat() + "Z",
                }
                write_json(votes, votes_path)
            return self._send_json({"ok": True, "job_id": job_id})

        if parsed.path == "/api/committee":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, status=400)

            decision = (payload.get("decision") or "").lower()
            scope = (payload.get("scope") or "").lower()
            kind = (payload.get("kind") or "").lower()
            item_id = payload.get("id") or ""
            job_id = payload.get("job_id") or ""
            if decision not in {"accept", "reject"}:
                return self._send_json({"error": "invalid decision"}, status=400)
            if scope not in {"profile", "job"}:
                return self._send_json({"error": "invalid scope"}, status=400)
            if kind not in {"skills", "abstractions", "emails"}:
                return self._send_json({"error": "invalid kind"}, status=400)
            if not item_id:
                return self._send_json({"error": "missing id"}, status=400)
            if scope == "job" and not job_id:
                return self._send_json({"error": "missing job_id"}, status=400)

            config = load_config("config/applicant.yaml")
            output_dir = config["paths"]["output_dir"]
            votes_path = os.path.join(output_dir, "committee_votes.json")
            votes = _load_committee_votes(votes_path)

            if scope == "profile":
                votes["profile"].setdefault(kind, {})
                votes["profile"][kind][item_id] = decision
            else:
                job_key = str(job_id)
                votes["jobs"].setdefault(job_key, {})
                votes["jobs"][job_key].setdefault(kind, {})
                votes["jobs"][job_key][kind][item_id] = decision

            write_json(votes, votes_path)
            return self._send_json({"ok": True})

        return self._send_json({"error": "not found"}, status=404)


def main():
    config_path = "config/applicant.yaml"
    config = load_config(config_path)
    web_dir = os.path.join(os.getcwd(), "web")
    host = "127.0.0.1"
    port = 9000

    _ensure_pipeline_outputs(config, config_path)

    if db_enabled(config):
        init_db(config)

    handler = lambda *args, **kwargs: ReviewHandler(*args, directory=web_dir, **kwargs)
    server = HTTPServer((host, port), handler)
    print(f"Review UI running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
