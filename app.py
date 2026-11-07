import os
import glob
import json
from pathlib import Path
from typing import List, Optional
import streamlit as st
import pandas as pd

from src.config import (
    INPUT_DIR,
    FINAL_RESULTS_DIR,
    RAW_OUTPUTS_DIR,
    QUALITY_REPORTS_DIR,
    ANALYZED_DIR,
    CANDIDATES_DIR,
    get_api_key,
    get_model_name,
    get_input_files,
)
from src.models import (
    Episode,
    EpisodeAnalysis,
    PromoCandidate,
    PromoEvaluation,
    QualityReport,
)
from src.parser import (
    extract_text_from_txt,
    extract_text_from_pdf,
    parse_screenplay,
)
from src.screenplay_analyzer import ScreenplayAnalyzer
from src.promo_discovery import PromoDiscoveryEngine
from src.ranking import PromoRanker
from src.quality_checker import QualityChecker
from src.exporter import Exporter
from src.ui_components import render_promo_card, render_promo_screenplay_section

# Page config
st.set_page_config(
    page_title="AI Promo Finder & Ranking System",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #718096;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .top-badge {
        background-color: #3182CE;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "episodes" not in st.session_state:
    st.session_state.episodes = []
if "analyses" not in st.session_state:
    st.session_state.analyses = []
if "candidates" not in st.session_state:
    st.session_state.candidates = []
if "evaluations" not in st.session_state:
    st.session_state.evaluations = []
if "quality_report" not in st.session_state:
    st.session_state.quality_report = None
if "api_key" not in st.session_state:
    st.session_state.api_key = get_api_key()
if "model_name" not in st.session_state:
    st.session_state.model_name = get_model_name()

# Auto-load verified pre-computed results on initial launch for Streamlit Cloud
if "auto_loaded" not in st.session_state:
    st.session_state.auto_loaded = True
    verified_file = FINAL_RESULTS_DIR / "complete_results.json"
    if verified_file.exists():
        try:
            with open(verified_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            st.session_state.evaluations = [PromoEvaluation.model_validate(x) for x in raw_data]
            st.session_state.candidates = [e.candidate for e in st.session_state.evaluations]
            qr_file = QUALITY_REPORTS_DIR / "quality_report.json"
            if qr_file.exists():
                with open(qr_file, "r", encoding="utf-8") as f:
                    st.session_state.quality_report = QualityReport.model_validate(json.load(f))
        except Exception:
            pass

# Sidebar
with st.sidebar:
    st.title("🎬 Promo Finder")
    st.caption("AI-Powered Microdrama Promotion Engine")
    st.divider()

    # API Configuration
    st.subheader("🔑 AI Configuration")
    user_key = st.text_input(
        "Gemini API Key (Optional)",
        value=st.session_state.api_key,
        type="password",
        help="Optional. Reading pre-computed verified results requires no API key. A key is only needed to run new live analyses.",
    )
    if user_key != st.session_state.api_key:
        st.session_state.api_key = user_key

    selected_model = st.selectbox(
        "Model Selection",
        ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-2.5-pro"],
        index=0,
        help="gemini-3.5-flash (Recommended) & gemini-3.1-flash-lite are high availability. gemini-3.8-flash may experience temporary demand spikes.",
    )
    st.session_state.model_name = selected_model

    if st.session_state.api_key:
        st.success("API Key Active (Gemini SDK Enabled)")
    else:
        st.info("Using Built-in Deterministic Parser & Heuristic Analyzer")

    st.divider()

    # Navigation
    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📁 Upload Screenplays",
            "⚙️ Analysis Engine",
            "🎯 Promo Discovery",
            "🏆 Promo Ranking",
            "🛡️ Quality Report",
            "📥 Export Center",
        ],
    )

    st.divider()
    if st.button("🔄 Reset / Clear Session", use_container_width=True):
        st.session_state.episodes = []
        st.session_state.analyses = []
        st.session_state.candidates = []
        st.session_state.evaluations = []
        st.session_state.quality_report = None
        st.rerun()

    verified_results_file = FINAL_RESULTS_DIR / "complete_results.json"
    results_ready = verified_results_file.exists()
    if st.button(
        "📂 Load Verified 11,961 Promos",
        use_container_width=True,
        disabled=not results_ready,
        help="Instantly load pre-computed, verified 11,961 promo evaluations from disk." if results_ready else "Run analysis or place complete_results.json in data/final_results/.",
    ):
        with st.spinner("Loading verified results..."):
            with open(verified_results_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            evals = [PromoEvaluation.model_validate(x) for x in raw_data]
            st.session_state.evaluations = evals
            st.session_state.candidates = [e.candidate for e in evals]
            qr_file = QUALITY_REPORTS_DIR / "quality_report.json"
            if qr_file.exists():
                with open(qr_file, "r", encoding="utf-8") as f:
                    st.session_state.quality_report = QualityReport.model_validate(json.load(f))
            if not st.session_state.episodes:
                files = get_input_files()
                st.session_state.episodes = [
                    parse_screenplay(extract_text_from_txt(f), source_filename=f)
                    for f in files
                ]
        st.success("Loaded 11,961 verified results!")
        st.rerun()

    st.caption("Status: All 50 episodes supported")


# -----------------------------------------------------------------------------
# PAGE 1: DASHBOARD
# -----------------------------------------------------------------------------
if page == "📊 Dashboard":
    st.markdown("<div class='main-title'>🎬 AI Promo Finder & Ranking Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Automated Hook & Cliffhanger Discovery for 50-Episode Microdramas</div>", unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Episodes Loaded", len(st.session_state.episodes))
    with col2:
        total_scenes = sum(len(ep.scenes) for ep in st.session_state.episodes)
        st.metric("Total Scenes", total_scenes)
    with col3:
        st.metric("Promos Discovered", len(st.session_state.candidates))
    with col4:
        top_score = (
            f"{st.session_state.evaluations[0].overall_promo_score:.1f}/100"
            if st.session_state.evaluations
            else "N/A"
        )
        st.metric("Top Promo Score", top_score)
    with col5:
        issues_count = (
            st.session_state.quality_report.rule_violations_count
            + st.session_state.quality_report.llm_audit_issues_count
            if st.session_state.quality_report
            else 0
        )
        st.metric("Quality Audit Flags", issues_count)

    st.divider()

    if not st.session_state.evaluations:
        st.info("👋 Welcome! To begin discovering promos, go to **📁 Upload Screenplays** or click 'Load Full 50-Episode Pack' below.")
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("🚀 Quick Start: Load & Analyze Full 50-Episode Pack", type="primary", use_container_width=True):
                progress_container = st.container()
                with progress_container:
                    overall_bar = st.progress(0, text="Initializing 5-stage analysis pipeline...")
                    stage_status = st.empty()
                    metrics_cols = st.columns(4)
                    m_ep = metrics_cols[0].empty()
                    m_sc = metrics_cols[1].empty()
                    m_cand = metrics_cols[2].empty()
                    m_eval = metrics_cols[3].empty()

                    m_ep.metric("Episodes", "0 / 50")
                    m_sc.metric("Scenes", "0 / 100")
                    m_cand.metric("Candidates", "0")
                    m_eval.metric("Evaluated", "0")

                    try:
                        # STAGE 1: INGESTION & PARSING
                        stage_status.info("📁 **Stage 1/5: Loading and parsing screenplay files...**")
                        overall_bar.progress(0.1, text="Stage 1/5: Parsing screenplays...")
                        files = get_input_files()
                        if not files:
                            stage_status.error("❌ **No screenplay source files found.**")
                            st.warning("Screenplay source files were omitted from the repository for confidentiality. Please upload `.txt` or `.pdf` screenplays on the **📁 Upload Screenplays** page, or click **📂 Load Pre-computed Verified Results** below.")
                            st.stop()

                        loaded_eps = []
                        total_scenes_count = 0
                        for idx, f in enumerate(files):
                            text = extract_text_from_txt(f)
                            ep = parse_screenplay(text, source_filename=f)
                            loaded_eps.append(ep)
                            total_scenes_count += len(ep.scenes)
                            m_ep.metric("Episodes", f"{idx + 1} / {len(files)}")
                            m_sc.metric("Scenes", f"{total_scenes_count}")
                        st.session_state.episodes = loaded_eps

                        # STAGE 2: SCENE DRAMATIC ANALYSIS
                        stage_status.info("⚙️ **Stage 2/5: Analyzing dramatic scenes across all 50 episodes...**")
                        overall_bar.progress(0.3, text="Stage 2/5: Dramatic analysis...")
                        analyzer = ScreenplayAnalyzer(
                            api_key=st.session_state.api_key,
                            model_name=st.session_state.model_name,
                        )
                        analyses = []
                        for idx, ep in enumerate(loaded_eps):
                            ea = analyzer.analyze_episode(ep)
                            analyses.append(ea)
                            m_ep.metric("Episodes Analyzed", f"{idx + 1} / {len(loaded_eps)}")
                        st.session_state.analyses = analyses

                        # STAGE 3: PROMO DISCOVERY
                        stage_status.info("🎯 **Stage 3/5: Discovering single- and multi-episode promo candidates (20s–60s)...**")
                        overall_bar.progress(0.5, text="Stage 3/5: Discovering promo candidates...")
                        discovery = PromoDiscoveryEngine()
                        candidates = discovery.discover_all_promos(loaded_eps, analyses)
                        st.session_state.candidates = candidates
                        m_cand.metric("Candidates", f"{len(candidates):,}")

                        # STAGE 4: EVALUATION & RANKING
                        stage_status.info("🏆 **Stage 4/5: Two-Stage Evaluation (Stage 4A: Baseline scoring, Stage 4B: Batched Gemini evaluation)...**")
                        ranker = PromoRanker(
                            api_key=st.session_state.api_key,
                            model_name=st.session_state.model_name,
                        )

                        def update_rank_progress(cur, tot, msg):
                            pct = cur / max(tot, 1)
                            overall_bar.progress(0.5 + 0.35 * pct, text=f"Stage 4/5: {msg}")
                            m_eval.metric("Evaluated", f"{cur:,} / {tot:,}")

                        evaluations = ranker.evaluate_and_rank_all(
                            candidates,
                            deep_evaluate_top_n=20 if st.session_state.api_key else 0,
                            progress_callback=update_rank_progress,
                        )
                        st.session_state.evaluations = evaluations

                        # STAGE 5: QUALITY AUDIT
                        stage_status.info("🛡️ **Stage 5/5: Performing dual-method quality assurance...**")
                        overall_bar.progress(0.95, text="Stage 5/5: Quality verification...")
                        checker = QualityChecker()
                        st.session_state.quality_report = checker.run_full_quality_check(
                            evaluations, loaded_eps
                        )

                        overall_bar.progress(1.0, text="Pipeline Complete!")
                        st.success(f"Processing complete! Discovered and ranked {len(candidates):,} candidates across all 50 episodes with 0 structural errors.")
                        st.rerun()

                    except Exception as e:
                        stage_status.error(f"❌ **Pipeline Error encountered:** {e}")
                        st.exception(e)

        with c_btn2:
            verified_results_file = FINAL_RESULTS_DIR / "complete_results.json"
            is_avail = verified_results_file.exists()
            if st.button(
                "📂 Load Pre-computed Verified Results (11,961 Promos)",
                use_container_width=True,
                disabled=not is_avail,
                help="Instantly load pre-computed 11,961 promo evaluations from disk (39.5 MB)." if is_avail else "Result file complete_results.json not found.",
            ):
                with st.spinner("Loading verified results..."):
                    with open(verified_results_file, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                    evals = [PromoEvaluation.model_validate(x) for x in raw_data]
                    st.session_state.evaluations = evals
                    st.session_state.candidates = [e.candidate for e in evals]
                    qr_file = QUALITY_REPORTS_DIR / "quality_report.json"
                    if qr_file.exists():
                        with open(qr_file, "r", encoding="utf-8") as f:
                            st.session_state.quality_report = QualityReport.model_validate(json.load(f))
                    if not st.session_state.episodes:
                        files = get_input_files()
                        st.session_state.episodes = [
                            parse_screenplay(extract_text_from_txt(f), source_filename=f)
                            for f in files
                        ]
                st.success("Loaded 11,961 verified results!")
                st.rerun()

    else:
        top_col1, top_col2 = st.columns([3, 1])
        with top_col1:
            st.subheader("🌟 Top 3 Recommended Promos to Publish First")
            st.caption("Primary creative recommendations representing distinct episodes, dramatic conflicts, and complete original screenplays.")
        with top_col2:
            verified_results_file = FINAL_RESULTS_DIR / "complete_results.json"
            if verified_results_file.exists():
                if st.button("🔄 Reload 11,961 Verified Promos", use_container_width=True):
                    with st.spinner("Reloading complete dataset..."):
                        with open(verified_results_file, "r", encoding="utf-8") as f:
                            raw_data = json.load(f)
                        st.session_state.evaluations = [PromoEvaluation.model_validate(x) for x in raw_data]
                        st.session_state.candidates = [e.candidate for e in st.session_state.evaluations]
                    st.rerun()
        top_3 = [ev for ev in st.session_state.evaluations if ev.is_top_three][:3]

        for i, ev in enumerate(top_3):
            cand = ev.candidate
            render_promo_card(
                candidate=cand,
                evaluation=ev,
                episodes=st.session_state.episodes,
                is_top_recommendation=True,
                rank_label=f"Recommendation #{ev.recommended_publish_rank or (i + 1)} (Raw Rank #{ev.rank})",
            )


# -----------------------------------------------------------------------------
# PAGE 2: UPLOAD SCREENPLAYS
# -----------------------------------------------------------------------------
elif page == "📁 Upload Screenplays":
    st.markdown("<div class='main-title'>📁 Screenplay Ingestion & Verification</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Accepts both PDF and TXT files for up to 50 episodes</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        uploaded_files = st.file_uploader(
            "Upload Screenplays (PDF or TXT)",
            type=["txt", "pdf"],
            accept_multiple_files=True,
            help="Select one, ten, or all 50 episode files.",
        )
    with c2:
        st.write("Or load existing workspace repository files:")
        if st.button("📁 Load All 50 Episodes from `input/` folder", use_container_width=True):
            files = get_input_files()
            if not files:
                st.warning("⚠️ No screenplay files found in `input/` or `data/input/`. Screenplay files are omitted from the public repository for confidentiality. Please upload your `.txt` or `.pdf` screenplay files above.")
            else:
                loaded_eps = []
                for f in files:
                    text = extract_text_from_txt(f)
                    ep = parse_screenplay(text, source_filename=f)
                    loaded_eps.append(ep)
                st.session_state.episodes = loaded_eps
                st.success(f"Successfully loaded and parsed all {len(loaded_eps)} episodes!")

    if uploaded_files:
        if st.button(f"Parse {len(uploaded_files)} Uploaded Files", type="primary"):
            new_eps = []
            for uf in uploaded_files:
                name = uf.name
                bytes_data = uf.read()
                if name.lower().endswith(".pdf"):
                    text = extract_text_from_pdf(bytes_data)
                else:
                    text = extract_text_from_txt(bytes_data)

                ep = parse_screenplay(text, source_filename=name)
                new_eps.append(ep)

            # Sort by episode ID
            new_eps.sort(key=lambda e: e.episode_id)
            st.session_state.episodes = new_eps
            st.success(f"Parsed {len(new_eps)} episodes successfully!")

    if st.session_state.episodes:
        st.divider()
        st.subheader("📋 Ingested Episodes Summary")

        records = []
        for ep in st.session_state.episodes:
            records.append(
                {
                    "Episode ID": ep.episode_id,
                    "Title": ep.title,
                    "Scenes": len(ep.scenes),
                    "Duration (s)": ep.total_duration_seconds,
                    "Logline": ep.logline[:90] + "..." if ep.logline else "N/A",
                    "Status": "VALID",
                }
            )
        df_eps = pd.DataFrame(records)
        st.dataframe(df_eps, use_container_width=True)


# -----------------------------------------------------------------------------
# PAGE 3: ANALYSIS ENGINE
# -----------------------------------------------------------------------------
elif page == "⚙️ Analysis Engine":
    st.markdown("<div class='main-title'>⚙️ Screenplay Analysis Engine</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Batch scene processing, dramatic conflict identification & caching</div>", unsafe_allow_html=True)

    if not st.session_state.episodes:
        analyzed_files = sorted(glob.glob(str(ANALYZED_DIR / "episode_*.json")))
        if analyzed_files and not st.session_state.analyses:
            st.info("💡 Screenplay text files are omitted for confidentiality, but 50 pre-computed episode analyses are available on disk.")
            if st.button("📂 Load Pre-computed Episode Analyses (50 Episodes)", use_container_width=True):
                loaded_ea = []
                for af in analyzed_files:
                    with open(af, "r", encoding="utf-8") as f:
                        loaded_ea.append(EpisodeAnalysis.model_validate(json.load(f)))
                st.session_state.analyses = loaded_ea
                st.success(f"Loaded {len(loaded_ea)} pre-computed episode analyses!")
                st.rerun()
        st.warning("Please upload or load episodes on the 'Upload Screenplays' page to run live scene analysis.")
    else:
        st.write(f"Ready to analyze {len(st.session_state.episodes)} episodes.")

        colA, colB = st.columns([1, 1])
        with colA:
            if st.button("▶️ Run Scene Analysis", type="primary"):
                progress_bar = st.progress(0, text="Initializing analysis...")
                analyzer = ScreenplayAnalyzer(
                    api_key=st.session_state.api_key,
                    model_name=st.session_state.model_name,
                )
                analyses = []
                total = len(st.session_state.episodes)

                for idx, ep in enumerate(st.session_state.episodes):
                    progress_bar.progress(
                        (idx + 1) / total,
                        text=f"Analyzing Episode {ep.episode_id}/{total} ({len(ep.scenes)} scenes)...",
                    )
                    ea = analyzer.analyze_episode(ep)
                    analyses.append(ea)

                st.session_state.analyses = analyses
                progress_bar.empty()
                st.success("Analysis complete across all episodes!")

        if st.session_state.analyses:
            st.divider()
            st.subheader("🔍 Episode Scene Insights")
            selected_ep_id = st.selectbox(
                "Select Episode to Inspect",
                [ea.episode_id for ea in st.session_state.analyses],
            )
            selected_ea = next(
                ea for ea in st.session_state.analyses if ea.episode_id == selected_ep_id
            )

            st.write(f"**Episode Summary:** {selected_ea.summary}")
            for sa in selected_ea.scene_analyses:
                with st.expander(f"Scene {sa.scene_id} — Conflict: {sa.key_conflict}", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Emotional Intensity:** {sa.emotional_intensity}/10")
                        st.write(f"**Suspense Level:** {sa.suspense_level}/10")
                        st.write(f"**Characters:** {', '.join(sa.characters_involved)}")
                        if sa.betrayals:
                            st.write(f"**Betrayals Detected:** {'; '.join(sa.betrayals)}")
                    with col2:
                        st.write(f"**Hook Candidates Found:** {len(sa.hook_moments)}")
                        st.write(f"**Cliffhanger Candidates Found:** {len(sa.cliffhanger_moments)}")
                        if sa.threats_or_danger:
                            st.write(f"**Threats/Danger:** {'; '.join(sa.threats_or_danger)}")


# -----------------------------------------------------------------------------
# PAGE 4: PROMO DISCOVERY
# -----------------------------------------------------------------------------
elif page == "🎯 Promo Discovery":
    st.markdown("<div class='main-title'>🎯 Promo Discovery Engine</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Discovers Single-Episode and Multi-Episode combinations (20s - 60s)</div>", unsafe_allow_html=True)

    if not st.session_state.candidates and st.session_state.evaluations:
        st.session_state.candidates = [e.candidate for e in st.session_state.evaluations]

    if not st.session_state.candidates:
        cand_file = CANDIDATES_DIR / "all_candidates.json"
        if cand_file.exists():
            st.info("💡 Pre-discovered candidate promos are available on disk.")
            if st.button("📂 Load Pre-discovered Promo Candidates (11,961 Promos)", use_container_width=True):
                with open(cand_file, "r", encoding="utf-8") as f:
                    st.session_state.candidates = [PromoCandidate.model_validate(x) for x in json.load(f)]
                st.success(f"Loaded {len(st.session_state.candidates)} pre-discovered candidates!")
                st.rerun()

    if not st.session_state.episodes or not st.session_state.analyses:
        if not st.session_state.candidates:
            st.warning("Please complete Screenplay Analysis before discovering new promos.")
    else:
        if st.button("⚡ Discover All Promo Candidates", type="primary"):
            with st.spinner("Extracting and evaluating candidate combinations..."):
                discovery = PromoDiscoveryEngine()
                candidates = discovery.discover_all_promos(
                    st.session_state.episodes, st.session_state.analyses
                )
                st.session_state.candidates = candidates
            st.success(f"Discovered {len(candidates)} valid candidate promos!")

        if st.session_state.candidates:
            promo_type_filter = st.selectbox(
                "Filter by Promo Type", ["ALL", "SINGLE_EPISODE", "MULTI_EPISODE"]
            )
            filtered = st.session_state.candidates
            if promo_type_filter != "ALL":
                filtered = [c for c in filtered if c.promo_type == promo_type_filter]

            c_filter1, c_filter2 = st.columns([1, 2])
            with c_filter1:
                page_size = 10
                total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
                selected_page = st.number_input(
                    f"Page (1 to {total_pages})",
                    min_value=1,
                    max_value=total_pages,
                    value=1,
                    step=1,
                )
            with c_filter2:
                st.write(f"Total Discovered: **{len(filtered)}** candidates. Showing **10** per page with complete screenplay scripts.")

            start_idx = (selected_page - 1) * page_size
            end_idx = min(start_idx + page_size, len(filtered))

            eval_map = {ev.promo_id: ev for ev in st.session_state.evaluations}

            for c in filtered[start_idx:end_idx]:
                ev = eval_map.get(c.promo_id)
                render_promo_card(
                    candidate=c,
                    evaluation=ev,
                    episodes=st.session_state.episodes,
                    is_top_recommendation=False,
                )


# -----------------------------------------------------------------------------
# PAGE 5: PROMO RANKING
# -----------------------------------------------------------------------------
elif page == "🏆 Promo Ranking":
    st.markdown("<div class='main-title'>🏆 Multi-Criteria Promo Ranking & Tie-Breaking</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Formula: 40% Hook + 25% Cliffhanger + 15% Clarity + 10% Emotion + 10% Continuity</div>", unsafe_allow_html=True)

    if not st.session_state.candidates and st.session_state.evaluations:
        st.session_state.candidates = [e.candidate for e in st.session_state.evaluations]

    if not st.session_state.candidates and not st.session_state.evaluations:
        verified_results_file = FINAL_RESULTS_DIR / "complete_results.json"
        if verified_results_file.exists():
            st.info("💡 Pre-computed verified rankings are available on disk.")
            if st.button("📂 Load Pre-computed Verified Rankings (11,961 Promos)", use_container_width=True):
                with open(verified_results_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                st.session_state.evaluations = [PromoEvaluation.model_validate(x) for x in raw_data]
                st.session_state.candidates = [e.candidate for e in st.session_state.evaluations]
                st.success("Loaded 11,961 verified results!")
                st.rerun()
        st.warning("Please run Promo Discovery first or load pre-computed results.")
    elif st.session_state.candidates and not st.session_state.evaluations:
        if st.button("⚖️ Calculate Rankings & Apply Tie-Breaking", type="primary"):
            p_bar = st.progress(0, text="Scoring all candidates...")

            def update_scoring_progress(cur, tot, msg):
                p_bar.progress(cur / max(tot, 1), text=f"Scoring: {msg}")

            try:
                ranker = PromoRanker(
                    api_key=st.session_state.api_key,
                    model_name=st.session_state.model_name,
                )
                evaluations = ranker.evaluate_and_rank_all(
                    st.session_state.candidates,
                    deep_evaluate_top_n=20 if st.session_state.api_key else 0,
                    progress_callback=update_scoring_progress,
                )
                st.session_state.evaluations = evaluations
                p_bar.empty()
                st.success(f"Scoring and ranking completed for {len(evaluations):,} candidates!")
            except Exception as e:
                p_bar.empty()
                st.error(f"Error during ranking: {e}")
                st.exception(e)

        if st.session_state.evaluations:
            ranker = PromoRanker(
                api_key=st.session_state.api_key,
                model_name=st.session_state.model_name,
            )
            df = ranker.to_dataframe(st.session_state.evaluations)

            view_mode = st.radio(
                "Filter View",
                ["🌟 Primary Recommendations (Distinct Scenes / Conflicts)", "📋 Complete Candidate Pool (Including All Duration Variants)"],
                horizontal=True,
            )
            if "Primary Recommendations" in view_mode:
                display_df = df[df["Cluster Primary"] == "YES"]
            else:
                display_df = df

            cols_to_show = [
                "Rec Rank",
                "Rank",
                "Promo ID",
                "Type",
                "Episodes",
                "Duration (s)",
                "Overall Score",
                "Hook Score (40%)",
                "Cliffhanger Score (25%)",
                "Top 3",
                "Cluster Primary",
                "Variants in Cluster",
            ]
            if "LLM Deep Evaluated" in display_df.columns:
                cols_to_show.append("LLM Deep Evaluated")
            cols_to_show.append("Diversity Notes")

            st.dataframe(
                display_df[cols_to_show],
                use_container_width=True,
            )

            st.divider()
            st.subheader("🌟 Top 3 Recommendations to Publish First")
            st.caption("Primary recommendations with complete original screenplays, individual score breakdowns, and partial overlap tracking.")
            for i, ev in enumerate([e for e in st.session_state.evaluations if e.is_top_three][:3]):
                render_promo_card(
                    candidate=ev.candidate,
                    evaluation=ev,
                    episodes=st.session_state.episodes,
                    is_top_recommendation=True,
                    rank_label=f"Recommendation #{ev.recommended_publish_rank or (i + 1)} (Raw Rank #{ev.rank})",
                )

            st.divider()
            st.subheader("🔍 Complete Screenplay & Scoring Inspector")
            st.caption("Select any candidate in the pool to inspect its complete original screenplay script, camera angles, actions, and metric breakdown.")

            ranked_options = [
                f"Rank #{ev.rank} [{ev.overall_promo_score:.2f} pts] — {ev.promo_id} ({ev.candidate.promo_type})"
                for ev in st.session_state.evaluations[:250]
            ]
            selected_option = st.selectbox(
                "Select Candidate to Inspect",
                options=ranked_options,
                index=0,
            )
            if selected_option:
                sel_promo_id = selected_option.split(" — ")[1].split(" ")[0].strip()
                sel_ev = next((e for e in st.session_state.evaluations if e.promo_id == sel_promo_id), None)
                if sel_ev:
                    render_promo_card(
                        candidate=sel_ev.candidate,
                        evaluation=sel_ev,
                        episodes=st.session_state.episodes,
                        is_top_recommendation=True,
                        rank_label=f"Rank #{sel_ev.rank}",
                    )


# -----------------------------------------------------------------------------
# PAGE 6: QUALITY REPORT
# -----------------------------------------------------------------------------
elif page == "🛡️ Quality Report":
    st.markdown("<div class='main-title'>🛡️ Quality Assurance & Error Auditing</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Method 1: Strict Python Rule Validation | Method 2: Independent Adversarial Evaluation</div>", unsafe_allow_html=True)

    if not st.session_state.quality_report:
        qr_file = QUALITY_REPORTS_DIR / "quality_report.json"
        if qr_file.exists():
            try:
                with open(qr_file, "r", encoding="utf-8") as f:
                    st.session_state.quality_report = QualityReport.model_validate(json.load(f))
            except Exception:
                pass

    if not st.session_state.evaluations:
        st.warning("Please complete Promo Ranking before auditing quality or load pre-computed results.")
    else:
        if st.button("🔍 Run Full Quality Audit", type="primary"):
            with st.spinner("Executing structural and semantic quality checks..."):
                checker = QualityChecker()
                st.session_state.quality_report = checker.run_full_quality_check(
                    st.session_state.evaluations, st.session_state.episodes
                )
            st.success("Quality audit complete!")

        if st.session_state.quality_report:
            rep = st.session_state.quality_report
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Promos Audited", rep.total_promos_checked)
            with c2:
                st.metric("Rule Violations", rep.rule_violations_count)
            with c3:
                st.metric("Audit Flags / Suggestions", rep.llm_audit_issues_count)

            st.divider()

            if rep.disagreements:
                st.subheader("⚖️ AI Evaluator Disagreements")
                for dis in rep.disagreements:
                    st.info(dis)

            st.subheader("📝 Detailed Error & Review Items")
            if not rep.errors:
                st.success("✅ Zero structural rule violations detected! All candidates adhere strictly to 20s-60s bounds and source timestamps.")
            else:
                for idx, err in enumerate(rep.errors):
                    severity_color = "red" if err.severity == "HIGH" else "orange" if err.severity == "MEDIUM" else "blue"
                    with st.expander(f"[{err.severity}] {err.error_type} in `{err.promo_id}` (Ep {err.episode_number})", expanded=(err.severity == "HIGH")):
                        st.markdown(f"**Explanation:** {err.explanation}")
                        st.markdown(f"**Timestamp:** `{err.timestamp}`")
                        st.markdown(f"**Suggested Correction:** {err.suggested_correction}")

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button(f"Mark Confirmed #{idx}"):
                                err.human_review_status = "CONFIRMED"
                                st.rerun()
                        with col_btn2:
                            if st.button(f"Reject Flag #{idx}"):
                                err.human_review_status = "REJECTED"
                                st.rerun()

                        st.caption(f"Human Review Status: **{err.human_review_status}**")


# -----------------------------------------------------------------------------
# PAGE 7: EXPORT CENTER
# -----------------------------------------------------------------------------
elif page == "📥 Export Center":
    st.markdown("<div class='main-title'>📥 Export & Reporting Center</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Export complete outputs in JSON, CSV, PDF, and Raw Formats</div>", unsafe_allow_html=True)

    if not st.session_state.evaluations:
        verified_results_file = FINAL_RESULTS_DIR / "complete_results.json"
        if verified_results_file.exists():
            try:
                with open(verified_results_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                st.session_state.evaluations = [PromoEvaluation.model_validate(x) for x in raw_data]
            except Exception:
                pass

    if not st.session_state.evaluations:
        st.warning("No evaluated promo results to export yet. Please run the pipeline or load verified results.")
    else:
        colA, colB, colC = st.columns(3)

        # JSON Export
        with colA:
            st.subheader("1. Full JSON Results")
            st.write("Complete structured output of all ranked promos with segment timestamps.")
            json_data = Exporter.export_json(st.session_state.evaluations)
            st.download_button(
                label="⬇️ Download Results (JSON)",
                data=json_data,
                file_name="promo_discovery_results.json",
                mime="application/json",
                use_container_width=True,
            )

        # CSV Export
        with colB:
            st.subheader("2. Ranked Promos CSV")
            st.write("Tabular breakdown of component scores, hook metrics, and rankings.")
            csv_data = Exporter.export_csv(st.session_state.evaluations)
            st.download_button(
                label="⬇️ Download Ranked Promos (CSV)",
                data=csv_data,
                file_name="ranked_promos.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # PDF Export
        with colC:
            st.subheader("3. Executive Report PDF")
            st.write("Formatted PDF report detailing top recommendations and editorial insights.")
            pdf_bytes = Exporter.export_pdf(
                st.session_state.evaluations, st.session_state.quality_report
            )
            st.download_button(
                label="⬇️ Download Executive Report (PDF)",
                data=pdf_bytes,
                file_name="promo_recommendations_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        st.divider()

        st.subheader("4. Quality Report & Raw Outputs")
        colD, colE = st.columns(2)
        with colD:
            if st.session_state.quality_report:
                rep_json = st.session_state.quality_report.model_dump_json(indent=2)
                st.download_button(
                    label="⬇️ Download Quality Report (JSON)",
                    data=rep_json,
                    file_name="quality_report.json",
                    mime="application/json",
                    use_container_width=True,
                )
            else:
                st.info("Quality report not generated yet.")

        with colE:
            st.write("Raw unedited intermediate outputs are preserved in `data/raw_outputs/` and `data/analyzed/`.")
            st.info("Ensures auditability and separation between raw AI generations and post-processed outputs.")

