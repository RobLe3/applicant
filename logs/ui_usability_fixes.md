# UI Usability Fixes

## Root causes
- Crawl tab enumerated only ATS companies; RSS adapters and manual sources were not included or counted.
- HTML entities were preserved in descriptions because text was sanitized without decoding entities or preserving paragraph breaks.
- Recommendations were based solely on score thresholds, so sales/GTM titles could surface as `apply` despite intent goals.

## Files changed
- `modules/crawl_jobs.py`: ATS source IDs now include provider+board, source_type set, HTML is stripped early, and per-source counts emitted.
- `utils/sanitizer.py`: HTML entity decoding + paragraph-preserving text normalization.
- `utils/web.py`: HTML-to-text conversion preserves paragraphs and decodes entities.
- `modules/match_score.py`: recommendation guard for sales roles (cap at consider) + reason tagging.
- `config/applicant.yaml`, `utils/io.py`: added `matching.recommendation_guard.enabled`.
- `web/app.js`: unified source list with counts, recommendation reason badge, collapsible description preview, and insight-triggered crawl refresh.
- `web/styles.css`: preserve line breaks in description preview.
- `tests/test_sanitization_logs.py`: assert HTML entity stripping.

## How to test
1) `python scripts/run_pipeline.py --config config/applicant.yaml`
2) `python scripts/serve_web.py`
3) Crawl tab:
   - Sources show ATS + RSS + manual with `source_id`, `source_type`, and `count`.
4) Review tab:
   - Descriptions render as plain text (no `&lt;` sequences).
   - Sales roles show `Reco consider` and a badge `role_family_out_of_scope:sales`.
   - Description previews expand/collapse per job.

## Example job IDs
- `greenhouse:mongodb:558d328adc58` (ATS board source_id)
- `epso_public:6b3ab2d10fd5` (RSS source_id)
- `sample:9837c3d64583` (manual source_id)
