import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from modules.extract_profile import extract_profile  # noqa: E402
from modules.crawl_jobs import crawl_jobs  # noqa: E402
from modules.match_score import match_score  # noqa: E402
from utils.io import ensure_dir, write_json  # noqa: E402


DEFAULT_CONFIG = "tests/fixtures/config/applicant.yaml"
OUTPUT_DIR = "tests/fixtures/output"


def _rank_map(results):
    return {row["id"]: idx + 1 for idx, row in enumerate(results)}


def _top_jobs(results, limit=10):
    return [
        {
            "id": row.get("id"),
            "title": (row.get("job") or {}).get("title"),
            "company": (row.get("job") or {}).get("company"),
            "score": row.get("score"),
            "alignment": (row.get("alignment") or {}).get("alignment_score"),
        }
        for row in results[:limit]
    ]


def compare_rankings(config_path=DEFAULT_CONFIG):
    ensure_dir(OUTPUT_DIR)
    extract_profile(config_path)
    crawl_jobs(config_path)

    token_results = match_score(config_path, similarity_mode="token", write_outputs=False)
    semantic_results = match_score(config_path, similarity_mode="semantic", write_outputs=False)

    token_rank = _rank_map(token_results)
    semantic_rank = _rank_map(semantic_results)
    all_ids = sorted(set(token_rank) | set(semantic_rank))

    deltas = []
    for job_id in all_ids:
        token_pos = token_rank.get(job_id)
        semantic_pos = semantic_rank.get(job_id)
        delta = None
        if token_pos and semantic_pos:
            delta = token_pos - semantic_pos
        deltas.append(
            {
                "job_id": job_id,
                "token_rank": token_pos,
                "semantic_rank": semantic_pos,
                "delta": delta,
            }
        )

    output = {
        "token_top_10": _top_jobs(token_results),
        "semantic_top_10": _top_jobs(semantic_results),
        "rank_deltas": deltas,
    }
    output_path = os.path.join(OUTPUT_DIR, "ranking_comparison.json")
    write_json(output, output_path)
    print(f"Wrote ranking comparison to {output_path}")


if __name__ == "__main__":
    compare_rankings()
