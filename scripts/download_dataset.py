"""Download the Olist Kaggle dataset into data/raw/.

Self-contained: reads KAGGLE_USERNAME / KAGGLE_KEY from the environment (set by
`source config/credentials.env`, or by scripts/setup_local_env.sh), no kaggle.json needed.

Usage:
    source config/credentials.env
    python scripts/download_dataset.py
"""
import shutil
import sys
from pathlib import Path

import kagglehub

REPO_ROOT = Path(__file__).parents[1]
DEST_DIR = REPO_ROOT / "data" / "raw"


def main() -> None:
    src = Path(kagglehub.dataset_download("olistbr/brazilian-ecommerce"))
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    for csv_file in src.glob("*.csv"):
        shutil.copy(csv_file, DEST_DIR / csv_file.name)
    print(f"Copied {len(list(DEST_DIR.glob('*.csv')))} CSVs into {DEST_DIR}")


if __name__ == "__main__":
    sys.exit(main())
