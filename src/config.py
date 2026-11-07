import os
import glob
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env file from project root if it exists
load_dotenv(override=False)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
ROOT_INPUT_DIR = PROJECT_ROOT / "input"
DATA_INPUT_DIR = DATA_DIR / "input"
INPUT_DIR = ROOT_INPUT_DIR if ROOT_INPUT_DIR.exists() else DATA_INPUT_DIR
EXTRACTED_DIR = DATA_DIR / "extracted"
ANALYZED_DIR = DATA_DIR / "analyzed"
CANDIDATES_DIR = DATA_DIR / "candidates"
FINAL_RESULTS_DIR = DATA_DIR / "final_results"
QUALITY_REPORTS_DIR = DATA_DIR / "quality_reports"
RAW_OUTPUTS_DIR = DATA_DIR / "raw_outputs"
CACHE_DIR = DATA_DIR / "cache"
STORYBOARDS_DIR = DATA_DIR / "storyboards"

# Ensure all data directories exist
for directory in [
    DATA_DIR,
    ROOT_INPUT_DIR,
    DATA_INPUT_DIR,
    EXTRACTED_DIR,
    ANALYZED_DIR,
    CANDIDATES_DIR,
    FINAL_RESULTS_DIR,
    QUALITY_REPORTS_DIR,
    RAW_OUTPUTS_DIR,
    CACHE_DIR,
    STORYBOARDS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


def get_input_files() -> List[str]:
    """
    Returns sorted list of available screenplay txt files from input directories.
    Portable across Windows, Linux, and macOS.
    """
    candidates = []
    for pattern in ["input/*.txt", "data/input/*.txt"]:
        for f in glob.glob(str(PROJECT_ROOT / pattern)):
            candidates.append(str(Path(f).resolve()))
    # Deduplicate by filename
    seen = set()
    unique = []
    for c in candidates:
        name = Path(c).name
        if name not in seen:
            seen.add(name)
            unique.append(c)
    return sorted(unique)


def get_api_key() -> str:
    """
    Retrieves GEMINI_API_KEY or GOOGLE_API_KEY from environment or Streamlit secrets.
    Portable across local environments and Streamlit Community Cloud.
    """
    # 1. Check environment variables
    for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        key = os.getenv(var, "")
        if key:
            return key

    # 2. Check streamlit secrets if available
    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
                if var in st.secrets:
                    return str(st.secrets[var])
    except Exception:
        pass

    return ""


def get_model_name() -> str:
    """
    Retrieves GEMINI_MODEL name, defaulting to 'gemini-3.5-flash'.
    """
    try:
        import streamlit as st

        if hasattr(st, "secrets") and "GEMINI_MODEL" in st.secrets:
            return str(st.secrets["GEMINI_MODEL"])
    except Exception:
        pass
    return os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "2.0"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))

# Promo timing constraints (in seconds)
PROMO_MIN_DURATION = float(os.getenv("PROMO_MIN_DURATION", "20.0"))
PROMO_MAX_DURATION = float(os.getenv("PROMO_MAX_DURATION", "60.0"))
HOOK_MAX_DURATION = float(os.getenv("HOOK_MAX_DURATION", "5.0"))
CLIFFHANGER_MAX_DURATION = float(os.getenv("CLIFFHANGER_MAX_DURATION", "10.0"))
