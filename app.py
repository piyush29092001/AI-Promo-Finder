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
    get_api_key,
    get_model_name,
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

# Sidebar
with st.sidebar:
    st.title("🎬 Promo Finder")
    st.caption("AI-Powered Microdrama Promotion Engine")
    st.divider()

    # API Configuration
    st.subheader("🔑 AI Configuration")
    user_key = st.text_input(
        "Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        help="Reads from .env by default. Enter a key or leave empty to use the verified offline rule/heuristic engine.",
    )
    if user_key != st.session_state.api_key:
        st.session_state.api_key = user_key

    selected_model = st.selectbox(
        "Model Selection",
        ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        index=0,
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
        if st.button("🚀 Quick Start: Load & Analyze Full 50-Episode Input Pack", type="primary"):
            with st.spinner("Loading and parsing all 50 screenplay files..."):
                files = sorted(glob.glob("input/*.txt"))
                loaded_eps = []
                for f in files:
                    text = extract_text_from_txt(f)
                    ep = parse_screenplay(text, source_filename=f)
                    loaded_eps.append(ep)
                st.session_state.episodes = loaded_eps

            with st.spinner("Analyzing scenes across all 50 episodes..."):
                analyzer = ScreenplayAnalyzer(
                    api_key=st.session_state.api_key,
                    model_name=st.session_state.model_name,
                )
                analyses = [analyzer.analyze_episode(ep) for ep in loaded_eps]
                st.session_state.analyses = analyses

            with st.spinner("Discovering single and multi-episode promos (20s - 60s)..."):
                discovery = PromoDiscoveryEngine()
                candidates = discovery.discover_all_promos(loaded_eps, analyses)
                st.session_state.candidates = candidates

            with st.spinner("Evaluating hooks (Four Hook Mistakes) and ranking..."):
                ranker = PromoRanker()
                evaluations = ranker.evaluate_and_rank_all(candidates)
                st.session_state.evaluations = evaluations

            with st.spinner("Performing dual-method quality verification..."):
                checker = QualityChecker()
                st.session_state.quality_report = checker.run_full_quality_check(
                    evaluations, loaded_eps
                )

            st.success(f"Processing complete! Discovered {len(candidates)} promo candidates across 50 episodes.")
            st.rerun()

    else:
        st.subheader("🌟 Top 3 Recommended Promos to Publish First")
        top_3 = [ev for ev in st.session_state.evaluations if ev.is_top_three][:3]

        cols = st.columns(3)
        for i, ev in enumerate(top_3):
            cand = ev.candidate
            with cols[i]:
                st.markdown(f"### Rank #{ev.rank}")
                st.caption(f"**ID:** `{ev.promo_id}` | **Type:** {cand.promo_type}")
                st.write(f"⏱️ **Duration:** {cand.total_duration_seconds:.1f}s")
                st.progress(ev.overall_promo_score / 100.0, text=f"Composite Score: {ev.overall_promo_score:.1f}/100")

                with st.expander("🎣 Hook Analysis", expanded=True):
                    st.write(f"**Dialogue:** *\"{cand.hook_text}\"*")
                    st.caption(f"Time: {cand.hook_start_time} - {cand.hook_end_time} | Score: {ev.hook_eval.total_hook_score:.1f}/100")
                    st.caption(f"Delay: {ev.hook_eval.delay_score}/25 | Confusion: {ev.hook_eval.confusion_score}/25 | Irrelevance: {ev.hook_eval.irrelevance_score}/25 | Disinterest: {ev.hook_eval.disinterest_score}/25")

                with st.expander("⚡ Cliffhanger Analysis", expanded=True):
                    st.write(f"**Ending:** *\"{cand.cliffhanger_text}\"*")
                    st.caption(f"Time: {cand.cliffhanger_start_time} - {cand.cliffhanger_end_time} | Score: {ev.cliffhanger_eval.cliffhanger_score:.1f}/100")
                    st.write(f"❓ **Unresolved Question:** {cand.unresolved_question}")

                st.info(f"💡 **Why Publish First:** {ev.publish_priority_reason}")


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
            files = sorted(glob.glob("input/*.txt"))
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
        st.warning("Please upload or load episodes on the 'Upload Screenplays' page first.")
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

    if not st.session_state.episodes or not st.session_state.analyses:
        st.warning("Please complete Screenplay Analysis before discovering promos.")
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

            st.write(f"Showing **{len(filtered)}** candidates:")

            for c in filtered[:25]:
                with st.container():
                    st.markdown(f"#### `{c.promo_id}` ({c.promo_type}) — Duration: {c.total_duration_seconds:.1f}s")
                    st.write(f"**Episodes:** {c.episodes} | **Conflict:** {c.key_conflict}")
                    st.write(f"**Segments:** " + "; ".join(f"Ep {s.episode_id}: {s.start_time}-{s.end_time}" for s in c.segments))
                    c1, c2 = st.columns(2)
                    with c1:
                        st.info(f"**Opening Hook:**\n*\"{c.hook_text}\"* ({c.hook_start_time} - {c.hook_end_time})")
                    with c2:
                        st.warning(f"**Ending Cliffhanger:**\n*\"{c.cliffhanger_text}\"* ({c.cliffhanger_start_time} - {c.cliffhanger_end_time})\n\n❓ *{c.unresolved_question}*")
                    st.divider()


# -----------------------------------------------------------------------------
# PAGE 5: PROMO RANKING
# -----------------------------------------------------------------------------
elif page == "🏆 Promo Ranking":
    st.markdown("<div class='main-title'>🏆 Multi-Criteria Promo Ranking & Tie-Breaking</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Formula: 40% Hook + 25% Cliffhanger + 15% Clarity + 10% Emotion + 10% Continuity</div>", unsafe_allow_html=True)

    if not st.session_state.candidates:
        st.warning("Please run Promo Discovery first.")
    else:
        if st.button("⚖️ Calculate Rankings & Apply Tie-Breaking", type="primary"):
            with st.spinner("Scoring all candidates..."):
                ranker = PromoRanker()
                evaluations = ranker.evaluate_and_rank_all(st.session_state.candidates)
                st.session_state.evaluations = evaluations
            st.success("Scoring and ranking completed!")

        if st.session_state.evaluations:
            ranker = PromoRanker()
            df = ranker.to_dataframe(st.session_state.evaluations)

            st.dataframe(
                df[
                    [
                        "Rank",
                        "Promo ID",
                        "Type",
                        "Episodes",
                        "Duration (s)",
                        "Overall Score",
                        "Hook Score (40%)",
                        "Cliffhanger Score (25%)",
                        "Clarity Score (15%)",
                        "Emotional Score (10%)",
                        "Continuity Score (10%)",
                        "Top 3",
                    ]
                ],
                use_container_width=True,
            )

            st.divider()
            st.subheader("💡 Top 3 Recommendation Rationales")
            for ev in [e for e in st.session_state.evaluations if e.is_top_three][:3]:
                st.markdown(f"**Rank #{ev.rank} (`{ev.promo_id}`):** {ev.publish_priority_reason}")


# -----------------------------------------------------------------------------
# PAGE 6: QUALITY REPORT
# -----------------------------------------------------------------------------
elif page == "🛡️ Quality Report":
    st.markdown("<div class='main-title'>🛡️ Quality Assurance & Error Auditing</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Method 1: Strict Python Rule Validation | Method 2: Independent Adversarial Evaluation</div>", unsafe_allow_html=True)

    if not st.session_state.evaluations:
        st.warning("Please complete Promo Ranking before auditing quality.")
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
        st.warning("No evaluated promo results to export yet. Please run the pipeline first.")
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
