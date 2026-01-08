from utils.io import load_config, ensure_dir, log_message
from utils.db import init_db, db_enabled
from modules.extract_profile import extract_profile
from modules.crawl_jobs import crawl_jobs
from modules.match_score import match_score
from modules.generate_app import generate_app


def run_pipeline(config_path="config/applicant.yaml"):
    config = load_config(config_path)
    output_dir = config["paths"]["output_dir"]
    logs_dir = config["paths"]["logs_dir"]
    ensure_dir(output_dir)
    ensure_dir(logs_dir)
    if db_enabled(config):
        init_db(config)

    log_message(logs_dir, "pipeline", "Starting pipeline")
    extract_profile(config_path)
    crawl_jobs(config_path)
    match_score(config_path)
    generate_app(config_path)
    log_message(logs_dir, "pipeline", "Pipeline complete")


if __name__ == "__main__":
    run_pipeline()
