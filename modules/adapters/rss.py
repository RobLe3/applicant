import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

from modules.adapters.base import AdapterBase
from utils.sanitizer import strip_html
from utils.io import log_message


class RssAdapter(AdapterBase):
    name = "rss"

    def fetch_jobs(self):
        feeds = self.config.get("feeds", []) or []
        jobs = []
        for feed in feeds:
            jobs.extend(self._fetch_feed(feed))
        return jobs

    def _fetch_feed(self, feed_cfg):
        feed_url = feed_cfg.get("feed_url") or ""
        if not feed_url:
            return []

        headers = {"User-Agent": "ApplicantRSS/1.0"}
        timeout = feed_cfg.get("timeout", 10)
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            timeout = 10

        try:
            request = Request(feed_url, headers=headers)
            with urlopen(request, timeout=timeout) as resp:
                payload = resp.read()
        except Exception as exc:
            if self.logs_dir:
                log_message(self.logs_dir, "crawl_jobs", f"RSS adapter failed for {feed_url}: {exc}")
            return []

        try:
            root = ET.fromstring(payload)
        except Exception as exc:
            if self.logs_dir:
                log_message(self.logs_dir, "crawl_jobs", f"RSS adapter parse failed for {feed_url}: {exc}")
            return []

        items = root.findall(".//item")
        results = []
        source_id = feed_cfg.get("source_id") or feed_cfg.get("source") or self.name
        intent_label = feed_cfg.get("intent_label") or ""
        company = feed_cfg.get("company") or feed_cfg.get("publisher") or source_id
        default_location = feed_cfg.get("location") or ""
        max_total = feed_cfg.get("max_total", 0)
        try:
            max_total = int(max_total)
        except (TypeError, ValueError):
            max_total = 0

        for item in items:
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            description = item.findtext("description") or ""
            content = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
            raw_description = content or description
            clean_description = strip_html(raw_description)
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or "").strip()

            results.append(
                {
                    "id": guid or link or title,
                    "title": title,
                    "company": company,
                    "location": default_location,
                    "description": clean_description,
                    "url": link,
                    "source": source_id,
                    "source_type": "rss",
                    "source_intent": intent_label,
                }
            )
            if max_total and len(results) >= max_total:
                break

        return results
