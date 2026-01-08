import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

from modules.pipeline import run_pipeline  # noqa: E402


if __name__ == "__main__":
    run_pipeline()
