from modules.adapters.base import AdapterBase


class LinkedinAdapter(AdapterBase):
    name = "linkedin"

    def fetch_jobs(self):
        source_path = self.config.get("source_path", "")
        raw_jobs = self._load_json(source_path)
        return self.normalize_jobs(raw_jobs)
