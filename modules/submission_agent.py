import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

from utils.io import read_json, write_json, ensure_dir, log_message


def _application_dir(output_dir):
    return os.path.join(output_dir, "applications")


def load_applications(output_dir):
    app_dir = _application_dir(output_dir)
    if not os.path.exists(app_dir):
        return []
    apps = []
    for name in sorted(os.listdir(app_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(app_dir, name)
        try:
            data = read_json(path)
            data["_file"] = name
            data["_path"] = path
            apps.append(data)
        except Exception:
            continue
    return apps


def _find_application(output_dir, job_id=None, filename=None):
    apps = load_applications(output_dir)
    if filename:
        for app in apps:
            if app.get("_file") == filename:
                return app
    if job_id:
        for app in apps:
            if str(app.get("job_id")) == str(job_id):
                return app
    return None


def _compose_email(app, config, overrides=None):
    overrides = overrides or {}
    to_addr = overrides.get("to") or app.get("to") or ""
    subject = overrides.get("subject") or app.get("subject") or "Application"
    body = overrides.get("body") or app.get("body_draft") or ""
    attachments = overrides.get("attachments") or app.get("attachments") or []

    profile = config.get("profile", {}) or {}
    from_addr = overrides.get("from") or profile.get("email") or ""

    message = EmailMessage()
    message["To"] = to_addr
    if from_addr:
        message["From"] = from_addr
    message["Subject"] = subject

    attachment_note = ""
    if attachments:
        attachment_lines = "\n".join([f"- {item}" for item in attachments])
        attachment_note = f"\n\nAttachments to include manually:\n{attachment_lines}\n"

    message.set_content(f"{body}{attachment_note}".strip())
    return message


def _draft_path(app, output_dir):
    filename = os.path.splitext(app.get("_file", "application"))[0]
    return os.path.join(_application_dir(output_dir), f"{filename}.eml")


def create_email_draft(app, config, overrides=None):
    output_dir = config["paths"]["output_dir"]
    message = _compose_email(app, config, overrides=overrides)
    draft_path = _draft_path(app, output_dir)
    ensure_dir(os.path.dirname(draft_path))
    with open(draft_path, "wb") as f:
        f.write(message.as_bytes())
    return draft_path


def send_email(app, config, overrides=None):
    smtp_cfg = (config.get("submission", {}) or {}).get("smtp", {}) or {}
    host = smtp_cfg.get("host", "127.0.0.1")
    port = int(smtp_cfg.get("port", 1025))
    message = _compose_email(app, config, overrides=overrides)
    with smtplib.SMTP(host, port) as smtp:
        smtp.send_message(message)
    return {"host": host, "port": port}


def build_form_assist(app, config, overrides=None):
    overrides = overrides or {}
    return {
        "to": overrides.get("to") or app.get("to") or "",
        "subject": overrides.get("subject") or app.get("subject") or "",
        "body": overrides.get("body") or app.get("body_draft") or "",
        "attachments": overrides.get("attachments") or app.get("attachments") or [],
        "notes": "Manual form assist only. No auto-submission performed.",
    }


def record_submission(app, config, record, submitted=False, draft_created=False):
    output_dir = config["paths"]["output_dir"]
    logs_dir = config["paths"]["logs_dir"]
    record = dict(record)
    record.setdefault("recorded_at", datetime.utcnow().isoformat() + "Z")
    record.setdefault("job_id", app.get("job_id"))
    record.setdefault("application_file", app.get("_file"))

    log_dir = os.path.join(logs_dir, "submissions")
    ensure_dir(log_dir)
    log_name = f"{record['recorded_at'].replace(':', '')}_{record.get('job_id', 'job')}.json"
    log_path = os.path.join(log_dir, log_name)
    write_json(record, log_path)

    app_path = app.get("_path")
    if app_path and os.path.exists(app_path):
        current = read_json(app_path)
        history = current.get("submission_history") or []
        history.append(record)
        current["submission_history"] = history
        current["last_submission"] = record
        if draft_created:
            current["draft_created"] = True
        if submitted:
            current["submitted"] = True
            current["submitted_at"] = record["recorded_at"]
        write_json(current, app_path)

    log_message(logs_dir, "submission_agent", f"Recorded submission for job {record.get('job_id')}")
    return log_path


def submit_application(config, job_id=None, filename=None, mode="draft", overrides=None, dispatch=False):
    output_dir = config["paths"]["output_dir"]
    app = _find_application(output_dir, job_id=job_id, filename=filename)
    if not app:
        raise FileNotFoundError("Application package not found.")

    overrides = overrides or {}
    record = {
        "mode": mode,
        "dispatch": bool(dispatch),
        "to": overrides.get("to") or app.get("to"),
        "subject": overrides.get("subject") or app.get("subject"),
        "attachments": overrides.get("attachments") or app.get("attachments") or [],
    }
    body_text = overrides.get("body") or app.get("body_draft") or ""
    if body_text:
        record["body_preview"] = body_text[:240]
    if mode == "draft":
        draft_path = create_email_draft(app, config, overrides=overrides)
        record.update({"status": "draft_created", "draft_path": draft_path})
        record_submission(app, config, record, submitted=False, draft_created=True)
        return {"status": "draft_created", "draft_path": draft_path}

    if mode == "smtp":
        if not dispatch:
            raise ValueError("SMTP dispatch requires explicit approval.")
        smtp_meta = send_email(app, config, overrides=overrides)
        record.update({"status": "sent", "smtp": smtp_meta})
        record_submission(app, config, record, submitted=True, draft_created=False)
        return {"status": "sent", "smtp": smtp_meta}

    if mode == "form":
        assist = build_form_assist(app, config, overrides=overrides)
        record.update({"status": "form_assist"})
        record_submission(app, config, record, submitted=False, draft_created=False)
        return {"status": "form_assist", "form": assist}

    raise ValueError("Unsupported submission mode.")
