import streamlit as st
from typing import List, Optional
from src.models import (
    PromoCandidate,
    PromoEvaluation,
    Episode,
    Scene,
    ScreenplayEntry,
)
from src.parser import (
    extract_promo_screenplay_entries,
    get_scene_for_segment,
)
from src.storyboard_generator import get_storyboard_for_promo


def render_screenplay_entry(entry: ScreenplayEntry):
    """
    Renders an individual screenplay entry with distinct visual styling,
    timestamps, and partial overlap warnings where applicable.
    Preserves exact original wording without summarization.
    """
    badge_color_map = {
        "DIALOGUE": "#3182CE",     # Blue
        "CAMERA": "#805AD5",       # Purple
        "ACTION": "#38A169",       # Green
        "SOUND_FX": "#DD6B20",     # Amber / Orange
        "OTHER": "#718096",        # Slate Gray
    }
    badge_label_map = {
        "DIALOGUE": "💬 DIALOGUE",
        "CAMERA": "🎥 CAMERA",
        "ACTION": "🎬 ACTION",
        "SOUND_FX": "🔊 SOUND FX",
        "OTHER": "ℹ️ DIRECTION",
    }

    entry_type = entry.entry_type.upper()
    badge_bg = badge_color_map.get(entry_type, "#718096")
    badge_label = badge_label_map.get(entry_type, f"ℹ️ {entry_type}")

    # Build entry HTML/Markdown
    speaker_header = ""
    if entry.speaker:
        emotion_str = f" <i>({entry.emotion})</i>" if entry.emotion else ""
        speaker_header = f"<b>{entry.speaker}</b>{emotion_str}: "

    overlap_warning = ""
    if entry.is_partial_overlap:
        note_str = f" — {entry.overlap_note}" if entry.overlap_note else ""
        overlap_warning = (
            f"<div style='margin-top: 4px; padding: 3px 8px; background: rgba(221, 107, 32, 0.15); "
            f"border-left: 3px solid #DD6B20; font-size: 0.8rem; color: #DD6B20; border-radius: 2px;'>"
            f"⚠️ <b>Partial Overlap:</b> Original timestamps [{entry.start_time} - {entry.end_time}]{note_str}</div>"
        )

    # Style content by type
    if entry_type == "DIALOGUE":
        content_html = f"<div style='padding-left: 8px; font-size: 0.95rem; font-style: italic; color: inherit;'>“{entry.content}”</div>"
    elif entry_type == "CAMERA":
        content_html = f"<div style='padding-left: 8px; font-size: 0.9rem; color: #718096; font-family: monospace;'>{entry.content}</div>"
    elif entry_type == "ACTION":
        content_html = f"<div style='padding-left: 8px; font-size: 0.9rem; color: inherit;'>{entry.content}</div>"
    elif entry_type == "SOUND_FX":
        content_html = f"<div style='padding-left: 8px; font-size: 0.9rem; font-weight: 500; color: #DD6B20;'>🔊 {entry.content}</div>"
    else:
        content_html = f"<div style='padding-left: 8px; font-size: 0.9rem; color: inherit;'>{entry.content}</div>"

    card_html = (
        f"<div style='margin-bottom: 8px; padding: 6px 10px; background: rgba(255, 255, 255, 0.03); "
        f"border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px;'>"
        f"  <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;'>"
        f"    <div>"
        f"      <span style='background: {badge_bg}; color: white; padding: 2px 7px; border-radius: 4px; "
        f"font-size: 0.72rem; font-weight: bold; text-transform: uppercase;'>{badge_label}</span> "
        f"      <span style='font-size: 0.9rem;'>{speaker_header}</span>"
        f"    </div>"
        f"    <span style='font-size: 0.78rem; color: #718096; font-family: monospace;'>⏱️ {entry.start_time} - {entry.end_time}</span>"
        f"  </div>"
        f"  {content_html}"
        f"  {overlap_warning}"
        f"</div>"
    )

    st.markdown(card_html, unsafe_allow_html=True)


def render_promo_screenplay_section(
    candidate: PromoCandidate,
    episodes: Optional[List[Episode]] = None,
    expanded: bool = False,
):
    """
    Renders the expandable 'View Complete Promo Script' section.
    Displays all source entries in chronological order across all candidate segments.
    """
    with st.expander("📜 View Complete Promo Script (Original Screenplay)", expanded=expanded):
        for seg_idx, seg in enumerate(candidate.segments):
            if len(candidate.segments) > 1:
                st.markdown(
                    f"#### 🎬 Segment {seg_idx + 1}: Episode {seg.episode_id}, Scene {seg.scene_id} "
                    f"(`{seg.start_time}` – `{seg.end_time}`) — {seg.duration_seconds:.1f}s"
                )
            else:
                st.markdown(
                    f"#### 🎬 Source Screenplay: Episode {seg.episode_id}, Scene {seg.scene_id} "
                    f"(`{seg.start_time}` – `{seg.end_time}`) — {seg.duration_seconds:.1f}s"
                )

            scene = get_scene_for_segment(seg.episode_id, seg.scene_id, episodes)
            if not scene:
                st.warning(
                    f"⚠️ Original screenplay content for Episode {seg.episode_id}, Scene {seg.scene_id} "
                    f"could not be loaded from source files. Displaying verified candidate metadata only."
                )
                continue

            st.caption(f"📍 **Scene Heading:** `{scene.heading}` | **Scene Span:** `{scene.start_time}` – `{scene.end_time}`")

            entries = extract_promo_screenplay_entries(scene, seg.start_seconds, seg.end_seconds)
            if not entries:
                st.info(f"No screenplay entries found in the exact time range {seg.start_time} – {seg.end_time}.")
                continue

            # Summary count of items
            d_count = sum(1 for e in entries if e.entry_type == "DIALOGUE")
            c_count = sum(1 for e in entries if e.entry_type == "CAMERA")
            a_count = sum(1 for e in entries if e.entry_type == "ACTION")
            s_count = sum(1 for e in entries if e.entry_type == "SOUND_FX")
            st.caption(f"Chronological Timeline: {len(entries)} items ({d_count} dialogue, {c_count} camera, {a_count} action, {s_count} sound FX)")

            for entry in entries:
                render_screenplay_entry(entry)

            if seg_idx < len(candidate.segments) - 1:
                st.divider()


def render_promo_card(
    candidate: PromoCandidate,
    evaluation: Optional[PromoEvaluation] = None,
    episodes: Optional[List[Episode]] = None,
    is_top_recommendation: bool = False,
    rank_label: Optional[str] = None,
):
    """
    Renders a complete promo card containing:
    1. Header metadata (Episode, Scene, Start, End, Duration, Promo ID)
    2. Hook Analysis with 4 Hook Mistakes breakdown
    3. Cliffhanger Analysis with unresolved question
    4. Scoring Breakdown (if evaluated)
    5. Expandable complete screenplay script view
    """
    container = st.container()
    with container:
        # Header Row
        title_prefix = f"### {rank_label} — " if rank_label else "#### "
        st.markdown(f"{title_prefix}`{candidate.promo_id}` ({candidate.promo_type})")

        # Metadata bar
        seg_summary = "; ".join(
            f"Ep {s.episode_id} ({s.scene_id}): {s.start_time} - {s.end_time} [{s.duration_seconds:.1f}s]"
            for s in candidate.segments
        )
        st.caption(f"⏱️ **Total Duration:** {candidate.total_duration_seconds:.1f}s | **Segments:** {seg_summary}")

        if evaluation:
            st.progress(
                evaluation.overall_promo_score / 100.0,
                text=f"Composite Score: {evaluation.overall_promo_score:.2f}/100",
            )

        # Hook & Cliffhanger Columns
        col_hook, col_cliff = st.columns(2)
        with col_hook:
            with st.container():
                st.markdown("##### 🎣 Opening Hook")
                st.write(f"*\"{candidate.hook_text}\"*")
                st.caption(f"Timestamps: `{candidate.hook_start_time}` – `{candidate.hook_end_time}`")
                if evaluation and evaluation.hook_eval:
                    h = evaluation.hook_eval
                    st.caption(f"**Hook Score:** {h.total_hook_score:.1f}/100")
                    st.caption(
                        f"Delay: {h.delay_score}/25 | Confusion: {h.confusion_score}/25 | "
                        f"Irrelevance: {h.irrelevance_score}/25 | Disinterest: {h.disinterest_score}/25"
                    )
                    if h.explanation:
                        st.caption(f"_{h.explanation}_")

        with col_cliff:
            with st.container():
                st.markdown("##### ⚡ Closing Cliffhanger")
                st.write(f"*\"{candidate.cliffhanger_text}\"*")
                st.caption(f"Timestamps: `{candidate.cliffhanger_start_time}` – `{candidate.cliffhanger_end_time}`")
                if evaluation and evaluation.cliffhanger_eval:
                    c = evaluation.cliffhanger_eval
                    st.caption(f"**Cliffhanger Score:** {c.cliffhanger_score:.1f}/100")
                    if c.explanation:
                        st.caption(f"_{c.explanation}_")
                st.info(f"❓ **Unresolved Question:** {candidate.unresolved_question}")

        if evaluation:
            # Component Score breakdown
            with st.expander("📊 View Complete Multi-Criteria Scoring Breakdown", expanded=False):
                colA, colB, colC, colD, colE = st.columns(5)
                with colA:
                    st.metric("Hook (40%)", f"{evaluation.hook_eval.total_hook_score:.1f}/100")
                with colB:
                    st.metric("Cliffhanger (25%)", f"{evaluation.cliffhanger_eval.cliffhanger_score:.1f}/100")
                with colC:
                    st.metric("Clarity (15%)", f"{evaluation.story_clarity_score:.1f}/100")
                with colD:
                    st.metric("Emotion (10%)", f"{evaluation.emotional_impact_score:.1f}/100")
                with colE:
                    st.metric("Continuity (10%)", f"{evaluation.scene_continuity_score:.1f}/100")

                if evaluation.publish_priority_reason:
                    st.info(f"💡 **Publishing Priority Rationale:** {evaluation.publish_priority_reason}")
                if evaluation.diversity_notes:
                    st.caption(f"🌐 **Diversity Clustering:** {evaluation.diversity_notes}")

        # Visual Storyboard & Screenplay Presentation
        storyboard = get_storyboard_for_promo(
            candidate.promo_id,
            evaluation.recommended_publish_rank if evaluation else None,
        )

        if is_top_recommendation and storyboard and storyboard.get("resolved_image_path"):
            st.markdown("#### 🎨 Complete Visual Storyboard (Cinematic Comic-Strip Format)")
            st.caption(
                f"Professional black-and-white cinematic storyboard sheet ({storyboard['duration']}) illustrating the complete sequence "
                f"from Opening Hook to Closing Cliffhanger with consistent character styling, room layouts, camera angles, and original dialogue."
            )

            # Display the single composite storyboard image
            st.image(
                storyboard["resolved_image_path"],
                use_container_width=True,
                caption=f"Cinematic Storyboard Sheet — {storyboard['title']}",
            )

            # Shot-by-shot sequential reference table
            with st.expander("🎬 Storyboard Panel Sequence & Screenplay Mapping", expanded=False):
                st.caption("Detailed breakdown of each panel in the composite storyboard sheet above:")
                cols_header = st.columns([1, 2, 2, 4, 3])
                cols_header[0].markdown("**Shot**")
                cols_header[1].markdown("**Est. Time**")
                cols_header[2].markdown("**Perspective**")
                cols_header[3].markdown("**Action / Dialogue (Verbatim)**")
                cols_header[4].markdown("**Notes**")
                st.divider()

                for s in storyboard["shots"]:
                    cols = st.columns([1, 2, 2, 4, 3])
                    cols[0].write(f"**Shot {s['shot_number']}**")
                    cols[1].code(s["timestamp"])
                    cols[2].write(f"`{s['shot_type']}`\n\n<small style='color:gray;'>{s['camera_source']}</small>", unsafe_allow_html=True)
                    cols[3].write(f"**{s['dialogue_action']}**\n\n_{s['visual_description']}_")
                    cols[4].caption(s["notes"])

            # Collapsible raw chronological screenplay entries
            with st.expander("📜 View Raw Screenplay Entry Chronology (Optional Reference)", expanded=False):
                render_promo_screenplay_section(
                    candidate=candidate,
                    episodes=episodes,
                    expanded=True,
                )
        else:
            # Complete Screenplay Script Section for general candidate pool
            render_promo_screenplay_section(
                candidate=candidate,
                episodes=episodes,
                expanded=is_top_recommendation,
            )

        st.divider()

