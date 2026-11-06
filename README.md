# 🎬 AI Promo Finder & Ranking System

An AI-powered web application and discovery pipeline designed to analyze 50 microdrama episode screenplays, automatically identify high-engagement promotional video clips (20s to 60s), evaluate hooks using the **Four Hook Mistakes Framework**, evaluate cliffhangers and story coherence, rank all valid candidates with deterministic tie-breaking, and audit system quality.

Developed for **Kuku AI Generalist Assignment — Problem 1: Find the Promos (Ads)**.

---

## 🌟 Key Capabilities

1. **Full 50-Episode Ingestion & Segmentation**:
   - Supports both **PDF** (via PyMuPDF) and **TXT** screenplay formats.
   - Extracts exact timestamps, headings, dialogue speakers, emotional cues, actions, cameras, and sound FX without hallucinating timestamps or lines.
   - Validates all 100 scenes across 50 episodes with 100% temporal consistency.

2. **Dual-Type Promo Discovery (20s – 60s)**:
   - **Type 1: Single-Episode Promos**: Continuous unbroken dramatic confrontations within one episode.
   - **Type 2: Multi-Episode Promos**: Cross-episode arcs combining 2 to 3 related segments sharing characters and narrative continuity.
   - Discovers **11,000+ candidate combinations** across 50 episodes while eliminating duplicate and near-duplicate windows (>85% temporal overlap).

3. **Four Hook Mistakes Framework**:
   Evaluates every promo's opening 3 seconds across 4 distinct factors (25 pts each, total 100):
   - **Delay (0–25)**: Immediate in-media-res attention vs slow scenic exposition.
   - **Confusion (0–25)**: Instant situational clarity for cold scrolling viewers.
   - **Irrelevance (0–25)**: High-stakes emotional resonance (betrayal, heartbreak, injustice).
   - **Disinterest (0–25)**: Curiosity gaps, contrast, and unanswered questions.

4. **Cliffhanger & Story Coherence Engine**:
   - Evaluates unresolved questions, tension escalation, and dramatic cliffhanger cuts (scored 0–100).
   - Distinguishes between shocking events and true cliffhangers that compel viewers to watch the full episode.

5. **Multi-Criteria Promo Ranking & Tie-Breaking**:
   $$\text{Promo Score} = 0.40 \times \text{Hook} + 0.25 \times \text{Cliffhanger} + 0.15 \times \text{Clarity} + 0.10 \times \text{Emotion} + 0.10 \times \text{Continuity}$$
   - Strict 6-level tie-breaking hierarchy.
   - Preserves true ties without inventing arbitrary winners.
   - Generates tailored publishing rationales for the Top 3 recommendations.

6. **Dual Quality Assurance Engine**:
   - **Method 1 (Rule-Based Validation)**: Validates episode/scene references, timestamp directionality, scene containment, and duration bounds.
   - **Method 2 (Independent Adversarial Audit)**: Flags weak hooks, soft cliffhangers, and narrative jumps; records disagreements and allows human review.

7. **Multi-Format Export Center**:
   - Complete JSON output with all timestamps.
   - Ranked Promos CSV.
   - Executive PDF Report generated via ReportLab.
   - Quality audit report & unedited raw LLM outputs.

8. **7-Page Streamlit Dashboard**:
   - Dashboard, Screenplay Upload, Analysis Engine, Promo Discovery, Promo Ranking, Quality Report, and Export Center.

---

## 🛠️ Technology Stack

- **Language**: Python 3.11+
- **Web Interface**: Streamlit
- **LLM Engine**: Google Gemini API via official `google-genai` SDK (configurable model: `gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`)
- **PDF Extraction**: PyMuPDF (`pymupdf`)
- **Schema Validation**: Pydantic v2
- **Data Processing & Ranking**: Pandas
- **Export Engine**: ReportLab (PDF), JSON, CSV
- **Retry & Reliability**: Tenacity (exponential backoff)
- **Testing**: Pytest (27 automated tests across 3 rounds)
- **Deployment**: Streamlit Community Cloud

---

## 🚀 Quick Start Guide

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/your-username/ai-promo-finder.git
cd ai-promo-finder

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your Google Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
BATCH_SIZE=5
MAX_RETRIES=3
```
*(Note: If no API key is supplied, the application automatically runs in verified deterministic heuristic mode, ensuring 100% functionality even offline or without API credits).*

### 4. Run the Streamlit Dashboard

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

---

## 🧪 Testing & Verification

The test suite validates every module across 3 progressive rounds:

```bash
# Run all 27 unit and end-to-end integration tests
pytest -v
```

### Test Coverage Highlights:
- **`tests/test_parser.py`**: Timestamp parsing (`MM:SS.SS`), case-insensitivity (`Scene start:` vs `SCENE START:`), PDF roundtrip extraction, malformed timestamp detection, and validation of all 50 screenplay files.
- **`tests/test_screenplay_analyzer.py`**: Batch processing, caching, resume capability, and conflict extraction.
- **`tests/test_promo_discovery.py`**: Single-episode (20s–60s), multi-episode combinations, and candidate deduplication.
- **`tests/test_evaluators.py`**: Four Hook Mistakes Framework scoring and cliffhanger evaluation.
- **`tests/test_ranking.py`**: Mathematical weighted formula validation and 6-level tie-breaking.
- **`tests/test_quality_checker.py`**: Rule-based error traps (duration bounds, missing episode IDs, inverted times).
- **`tests/test_exporter.py`**: JSON, CSV, and ReportLab PDF binary export validation.
- **`tests/test_end_to_end.py`**:
  - **Round 1**: 2 episodes.
  - **Round 2**: 10 episodes.
  - **Round 3**: Full 50-episode pack processing (11,961 candidates discovered, 0 rule violations).

---

## 📁 Project Structure

```
AI-Promo-Finder/
├── app.py                     # Streamlit 7-page Web Application
├── requirements.txt           # Python package dependencies
├── pytest.ini                 # Pytest configuration
├── .env.example               # Template environment configuration
├── .gitignore                 # Excludes .env, .venv, and confidential screenplays
├── SOLUTION_DOCUMENT.md       # Comprehensive 2-page Assignment Solution Doc
├── src/
│   ├── __init__.py
│   ├── config.py              # Centralized environment, paths & timing config
│   ├── models.py              # Pydantic schemas (Scene, Promo, HookEval, etc.)
│   ├── parser.py              # PyMuPDF and TXT extraction & scene segmenter
│   ├── screenplay_analyzer.py # Gemini batch scene analysis & resumable caching
│   ├── promo_discovery.py     # Single & Multi-episode candidate generator (20-60s)
│   ├── hook_evaluator.py      # Four Hook Mistakes Framework (100 pts)
│   ├── cliffhanger_evaluator.py # Unresolved question & tension evaluator (100 pts)
│   ├── ranking.py             # Weighted scoring & 6-level tie-breaking
│   ├── quality_checker.py     # Rule-based validation + independent audit
│   └── exporter.py            # JSON, CSV, and ReportLab PDF generator
├── tests/
│   ├── conftest.py
│   ├── test_parser.py
│   ├── test_screenplay_analyzer.py
│   ├── test_promo_discovery.py
│   ├── test_evaluators.py
│   ├── test_ranking.py
│   ├── test_quality_checker.py
│   ├── test_exporter.py
│   └── test_end_to_end.py
└── data/                      # Local data artifacts
    ├── input/                 # Ingested screenplays
    ├── extracted/             # Parsed scene data
    ├── analyzed/              # Cached scene analyses
    ├── candidates/            # Discovered promo candidates
    ├── final_results/         # Final ranked outputs (JSON, CSV, PDF)
    ├── quality_reports/       # Quality audit reports
    └── raw_outputs/           # Unedited raw LLM generations
```

---

## ☁️ Streamlit Community Cloud Deployment

1. **Push to GitHub**:
   Ensure confidential screenplays (`input/*.txt`, `data/*`) and `.env` are ignored by `.gitignore`.
2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io).
   - Select your repository and branch (`main`).
   - Main file path: `app.py`.
3. **Configure Secrets**:
   Under **App Settings > Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key"
   GEMINI_MODEL = "gemini-2.5-flash"
   ```
4. Click **Deploy**.

---

## 🔒 Confidentiality & Security

- **Screenplay Confidentiality**: All confidential screenplay text files are protected by `.gitignore` and never committed to GitHub.
- **API Key Protection**: API keys are loaded via environment variables or Streamlit Secrets and never displayed in UI, logs, or exports.
- **Local Isolation**: All parsing and duration calculations run on the local Python runtime.
