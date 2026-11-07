# 🎬 AI Promo Finder & Ranking System

An AI-powered web application and discovery pipeline designed to analyze 50 microdrama episode screenplays, automatically identify high-engagement promotional video clips (20s to 60s), evaluate hooks using the **Four Hook Mistakes Framework**, evaluate cliffhangers and story coherence, rank all valid candidates with deterministic tie-breaking, and audit system quality.

Developed for **Kuku AI Generalist Assignment — Problem 1: Find the Promos (Ads)**.

---

## 🌟 Key Capabilities

1. **Full 50-Episode Ingestion & Segmentation**:
   - Supports both **PDF** (via PyMuPDF) and **TXT** screenplay formats.
   - Extracts exact timestamps, headings, dialogue speakers, emotional cues, actions, cameras, and sound FX without hallucinating timestamps or dialogue lines.
   - Validates all 100 scenes across 50 episodes with 100% temporal consistency.

2. **Dual-Type Promo Discovery (20s – 60s)**:
   - **Type 1: Single-Episode Promos**: Continuous unbroken dramatic confrontations within one episode.
   - **Type 2: Multi-Episode Promos**: Cross-episode arcs combining 2 to 3 related segments sharing characters and narrative continuity.
   - Discovers **11,961 valid candidate combinations** across 50 episodes with 100% unique collision-free promo IDs.

3. **Four Hook Mistakes Framework**:
   Evaluates every promo's opening 3 seconds across 4 distinct factors (25 pts each, total 100):
   - **Delay (0–25)**: Immediate in-media-res attention vs slow scenic exposition.
   - **Confusion (0–25)**: Instant situational clarity for cold scrolling viewers.
   - **Irrelevance (0–25)**: High-stakes emotional resonance (betrayal, heartbreak, injustice).
   - **Disinterest (0–25)**: Curiosity gaps, contrast, and unanswered questions.

4. **Segment-Level Cliffhanger & Story Coherence Engine**:
   - Derives unresolved questions dynamically from the promo segment's actual terminal dialogue line.
   - Penalizes flat or resolved endings as `"Weak / Resolved ending"`.
   - Distinguishes between shocking events and true cliffhangers that compel viewers to watch the full episode.

5. **Multi-Criteria Promo Ranking, Diversity Clustering & Tie-Breaking**:
   $$\text{Promo Score} = 0.40 \times \text{Hook} + 0.25 \times \text{Cliffhanger} + 0.15 \times \text{Clarity} + 0.10 \times \text{Emotion} + 0.10 \times \text{Continuity}$$
   - **Diversity Clustering**: Groups 11,961 candidates into **5,127 distinct narrative clusters** based on shared hook line and scene, flagging the top variant as `Cluster Primary` for diverse publishing recommendations.
   - **6-Level Tie-Breaking Hierarchy**: Resolves rank ties deterministically while preserving true ties.
   - **Primary Recommendations**: Recommends top cuts from distinct episodes and scenes for editorial publishing.

6. **Dual Quality Assurance Engine**:
   - **Method 1 (Rule-Based Validation)**: Validates episode/scene references, timestamp directionality ($start < end$), scene containment, and duration bounds $\in [20s, 60s]$ (**0 rule violations** across 11,961 candidates).
   - **Method 2 (Independent Adversarial Audit)**: Flags weak hooks, soft cliffhangers, and narrative jumps; records human review status (`PENDING`, `CONFIRMED`, `REJECTED`).

7. **Multi-Format Export Center**:
   - Complete JSON output with all timestamps and cluster metadata (`complete_results.json`).
   - Ranked Promos CSV (`ranked_promos.csv`).
   - 2-Page Executive PDF Report generated via ReportLab (`executive_report.pdf`).
   - Preserved raw candidate records in `data/raw_outputs/raw_discovered_candidates.json`.

8. **7-Page Streamlit Web Application**:
   - **Dashboard**: High-level KPIs and Top 3 publish-first recommendations.
   - **Upload Screenplays**: Ingest PDF and TXT files for up to 50 episodes.
   - **Analysis Engine**: Inspect scene conflicts, emotional intensity, and Gemini batch analyses.
   - **Promo Discovery**: Filter and inspect single- and multi-episode promo candidates.
   - **Promo Ranking**: Explore primary recommendations or full candidate pool with component scores.
   - **Quality Report**: Rule validation results, audit flags, and interactive review status toggle.
   - **Export Center**: One-click downloads for JSON, CSV, PDF, and quality reports.

---

## 🏆 Corrected Top 3 Recommendations to Publish First

| Publish Rank | Promo ID | Episode & Location | Timestamps | Duration | Overall Score | Opening Hook | Closing Cliffhanger |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **#1** | `PROMO_EP38_SC01_001600_004750_315` | Ep 38 (Dungeon Cell) | 00:16.00 – 00:47.50 | 31.5s | **94.60** | `JULIANA: "Why?"` | `JULIANA: "What if I die here?"` |
| **#2** | `PROMO_EP01_SC01_011500_013820_232` | Ep 1 (Cathedral Wedding) | 01:15.00 – 01:38.20 | 23.2s | **93.55** | `LADY: "Long enough to know he was never going to marry you."` | `LADY JULIANA: "Embarrassed you?"` |
| **#3** | `PROMO_EP32_SC01_015690_022810_312` | Ep 32 (Manor Drawing Room) | 01:56.90 – 02:28.10 | 31.2s | **93.55** | `JULIANA: "...but you have never learned how to make anyone love you."` | `CATHERINE: "You think you can lecture me?!"` |

---

## 🛠️ Technology Stack

- **Language**: Python 3.11+
- **Web Interface**: Streamlit
- **LLM Engine**: Google Gemini API via official `google-genai` SDK (`gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`)
- **PDF Extraction**: PyMuPDF (`pymupdf`)
- **Schema Validation**: Pydantic v2
- **Data Processing & Ranking**: Pandas
- **Export Engine**: ReportLab (PDF), JSON, CSV
- **Retry & Reliability**: Tenacity (exponential backoff)
- **Testing**: Pytest (31 automated unit and regression tests)
- **Deployment**: Streamlit Community Cloud

---

## 🚀 Quick Start Guide

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/your-username/ai-promo-finder.git
cd ai-promo-finder

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
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
*(Note: If no API key is supplied, the application automatically runs in verified deterministic heuristic mode, ensuring 100% functionality offline).*

### 4. Run the Streamlit Dashboard

```bash
streamlit run app.py
```

The Streamlit entrypoint is `app.py`. Open your browser at `http://localhost:8501`. The dashboard automatically loads the verified pre-computed dataset (11,961 candidates across all 50 episodes), visual storyboards, and quality metrics out of the box with zero API calls.

---

## 🧪 Testing & Verification

The test suite validates every module across **49 automated tests**:

```bash
pytest tests/ -v
```

### Test Suite Highlights:
- **`tests/test_storyboard.py` (3 tests)**: Verifies that Top 3 storyboards exist, conform to 6-panel chronological layout with opening hook and closing cliffhanger, and match verbatim screenplay dialogue.
- **`tests/test_screenplay_display.py` (7 tests)**: Verifies verbatim original screenplay matching against source text files, chronological ordering, partial overlap flagging (`is_partial_overlap`), boundary clamping, entry type categorization (`DIALOGUE`, `CAMERA`, `ACTION`, `SOUND_FX`), missing content warnings, and multi-episode segment extraction.
- **`tests/test_batch_evaluation.py` (7 tests)**: Tests batched Gemini evaluation across multiple batches, retry on 429 rate limits, invalid JSON resilience, partial responses, cache resumption, and duplicate avoidance.
- **`tests/test_parser.py` (8 tests)**: Timestamp parsing (`MM:SS.SS`), case-insensitivity (`Scene start:` vs `SCENE START:`), PDF roundtrip extraction, malformed timestamp detection, and validation of all 50 screenplay files.
- **`tests/test_screenplay_analyzer.py` (3 tests)**: Batch processing, caching, resume capability, and conflict extraction.
- **`tests/test_promo_discovery.py` (5 tests)**: Single-episode (20s–60s), multi-episode combinations, deduplication, promo ID uniqueness (0 collisions across 11,961 candidates), segment-level unresolved question accuracy, and weak ending marking.
- **`tests/test_evaluators.py` (2 tests)**: Four Hook Mistakes Framework scoring and cliffhanger evaluation.
- **`tests/test_ranking.py` (5 tests)**: Mathematical weighted formula validation, 6-level tie-breaking, dataframe conversion, and diversity clustering.
- **`tests/test_quality_checker.py` (4 tests)**: Rule-based error traps (duration bounds, missing episode IDs, inverted times, scene containment) and comprehensive audit report.
- **`tests/test_exporter.py` (2 tests)**: JSON, CSV, and ReportLab PDF binary export validation.
- **`tests/test_end_to_end.py` (3 tests)**:
  - **Round 1**: 2 episodes.
  - **Round 2**: 10 episodes.
  - **Round 3**: Full 50-episode pack processing (11,961 candidates discovered, 0 rule violations).

---

## 📁 Project Structure

```
AI-Promo-Finder/
├── app.py                     # Streamlit Application Entrypoint
├── requirements.txt           # Python package dependencies
├── pytest.ini                 # Pytest configuration
├── .env.example               # Template environment configuration (no secrets)
├── .gitignore                 # Excludes .env, .venv, logs, and confidential screenplays
├── SOLUTION_DOCUMENT.md       # Concise Assignment Solution Doc
├── .streamlit/
│   └── config.toml            # Headless server & CORS configuration
├── src/
│   ├── __init__.py
│   ├── config.py              # Centralized environment, paths & timing config (portable paths)
│   ├── models.py              # Pydantic schemas (Scene, ScreenplayEntry, Promo, HookEval, etc.)
│   ├── parser.py              # PyMuPDF and TXT extraction & scene segmenter
│   ├── screenplay_analyzer.py # Scene analysis & resumable caching
│   ├── promo_discovery.py     # Single & Multi-episode candidate generator (20s-60s)
│   ├── hook_evaluator.py      # Four Hook Mistakes Framework (100 pts)
│   ├── cliffhanger_evaluator.py # Segment unresolved question & tension evaluator (100 pts)
│   ├── ranking.py             # Weighted scoring, diversity clustering & tie-breaking
│   ├── quality_checker.py     # Rule-based validation + independent audit
│   ├── exporter.py            # JSON, CSV, and ReportLab PDF generator
│   ├── storyboard_generator.py # 6-panel composite visual storyboard resolver
│   └── ui_components.py       # Visual storyboard viewer, promo cards & screenplay timeline
├── tests/                     # 49 automated unit and regression tests
└── data/                      # Tracked verified output artifacts & cache
    ├── candidates/            # Candidate pool metadata (all_candidates.json)
    ├── analyzed/              # Pre-computed dramatic scene analyses (episode_001 to 050.json)
    ├── final_results/         # Verified outputs (complete_results.json, ranked_promos.csv, PDF)
    ├── quality_reports/       # Quality audit reports (quality_report.json)
    ├── cache/                 # LLM deep evaluation cache (llm_deep_evaluations.json)
    └── storyboards/           # 6-panel composite storyboard sheets (JPEG format)
```

---

## ☁️ Streamlit Community Cloud Deployment

Follow these exact steps to deploy to Streamlit Community Cloud:

### Step 1: Initialize & Push to GitHub

```bash
# Verify git status to ensure .env and input/ are excluded
git status

# Stage all project files (output data, tests, source code, app.py)
git add .

# Commit changes
git commit -m "feat: prepare AI Promo Finder for Streamlit Community Cloud deployment"

# Link to your GitHub repository and push
git remote add origin https://github.com/<your-github-username>/AI-Promo-Finder.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit Community Cloud

1. Navigate to [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
2. Click **New app**.
3. Fill in the deployment form:
   - **Repository**: `<your-github-username>/AI-Promo-Finder`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Click **Advanced settings** (or **App settings > Secrets**):
   ```toml
   GEMINI_API_KEY = "your-actual-gemini-api-key"
   GEMINI_MODEL = "gemini-3.5-flash"
   ```
   *(Note: The app runs 100% functional out of the box using pre-computed verified results even without an API key).*
5. Click **Deploy!**

The app will boot in seconds on Streamlit Community Cloud.

---

## 🔒 Confidentiality & Security

- **Confidential Screenplays Protected**: All raw screenplay files (`input/*.txt`, `data/input/`, `data/extracted/`) and assignment PDFs (`docs/*.pdf`) are strictly excluded via `.gitignore` and never committed to GitHub.
- **Zero Exposed Secrets**: API keys are loaded via environment variables or Streamlit Secrets and never hardcoded, printed to logs, or displayed in the UI.
- **Zero-Dependency Browsing**: The deployed app ships with verified candidate evaluations, rankings, storyboards, and metrics, allowing visitors and evaluators to explore all 11,961 candidates without requiring new Gemini API calls.
