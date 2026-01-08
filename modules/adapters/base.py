import json
import os

from utils.io import log_message


class AdapterBase:
    name = ""

    def __init__(self, config, logs_dir=None):
        self.config = config or {}
        self.logs_dir = logs_dir

    def enabled(self):
        return bool(self.config.get("enabled", False))

    def fetch_jobs(self):
        return []

    def _load_json(self, path):
        if not path or not os.path.exists(path):
            if self.logs_dir:
                log_message(self.logs_dir, "crawl_jobs", f"Adapter {self.name}: missing source file {path}")
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            if self.logs_dir:
                log_message(self.logs_dir, "crawl_jobs", f"Adapter {self.name}: failed to read {path}: {exc}")
            return []
        if isinstance(data, dict):
            data = data.get("jobs") or data.get("items") or []
        if isinstance(data, list):
            return data
        return []

    def _normalize_job(self, job):
        if not isinstance(job, dict):
            return None
        normalized = {
            "id": job.get("id"),
            "title": job.get("title") or job.get("position") or "",
            "company": job.get("company") or job.get("employer") or "",
            "location": job.get("location") or job.get("city") or "",
            "description": job.get("description") or job.get("text") or "",
            "url": job.get("url") or job.get("link") or "",
            "contact_email": job.get("contact_email") or job.get("email") or "",
            "source": job.get("source") or self.name,
        }
        return normalized

    def normalize_jobs(self, jobs):
        normalized = []
        for job in jobs or []:
            item = self._normalize_job(job)
            if item:
                normalized.append(item)
        return self._limit_jobs(normalized)

    def _limit_jobs(self, jobs):
        max_total = self.config.get("max_total", 0)
        try:
            max_total = int(max_total)
        except (TypeError, ValueError):
            max_total = 0
        if max_total and len(jobs) > max_total:
            return jobs[:max_total]
        return jobs
