import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if it exists
load_dotenv(override=False)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
EXTRACTED_DIR = DATA_DIR / "extracted"
ANALYZED_DIR = DATA_DIR / "analyzed"
CANDIDATES_DIR = DATA_DIR / "candidates"
FINAL_RESULTS_DIR = DATA_DIR / "final_results"
QUALITY_REPORTS_DIR = DATA_DIR / "quality_reports"
RAW_OUTPUTS_DIR = DATA_DIR / "raw_outputs"

# Ensure all data directories exist
for directory in [
    DATA_DIR,
    INPUT_DIR,
    EXTRACTED_DIR,
    ANALYZED_DIR,
    CANDIDATES_DIR,
    FINAL_RESULTS_DIR,
    QUALITY_REPORTS_DIR,
    RAW_OUTPUTS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


def get_api_key() -> str:
    """
    Retrieves GEMINI_API_KEY from environment or Streamlit secrets if running in Streamlit.
    """
    # 1. Check environment variable
    key = os.getenv("GEMINI_API_KEY", "")
    if key:
        return key

    # 2. Check streamlit secrets if available
    try:
        import streamlit as st

        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    return ""


def get_model_name() -> str:
    """
    Retrieves GEMINI_MODEL name, defaulting to 'gemini-2.5-flash'.
    """
    try:
        import streamlit as st

        if hasattr(st, "secrets") and "GEMINI_MODEL" in st.secrets:
            return st.secrets["GEMINI_MODEL"]
    except Exception:
        pass
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "2.0"))

# Promo timing constraints (in seconds)
PROMO_MIN_DURATION = float(os.getenv("PROMO_MIN_DURATION", "20.0"))
PROMO_MAX_DURATION = float(os.getenv("PROMO_MAX_DURATION", "60.0"))
HOOK_MAX_DURATION = float(os.getenv("HOOK_MAX_DURATION", "5.0"))
CLIFFHANGER_MAX_DURATION = float(os.getenv("CLIFFHANGER_MAX_DURATION", "10.0"))
