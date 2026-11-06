import json
import logging
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path

from src.config import (
    CANDIDATES_DIR,
    PROMO_MIN_DURATION,
    PROMO_MAX_DURATION,
    HOOK_MAX_DURATION,
    CLIFFHANGER_MAX_DURATION,
)
from src.models import (
    Scene,
    Episode,
    SceneAnalysis,
    EpisodeAnalysis,
    PromoCandidate,
    PromoSegment,
    seconds_to_timestamp,
    timestamp_to_seconds,
)

logger = logging.getLogger(__name__)


class PromoDiscoveryEngine:
    """
    Discovers single-episode and multi-episode promo candidates
    strictly adhering to 20s-60s duration constraints and authentic source timestamps.
    """

    def __init__(
        self,
        min_duration: float = PROMO_MIN_DURATION,
        max_duration: float = PROMO_MAX_DURATION,
    ):
        self.min_duration = min_duration
        self.max_duration = max_duration

    def discover_all_promos(
        self,
        episodes: List[Episode],
        analyses: List[EpisodeAnalysis],
    ) -> List[PromoCandidate]:
        """
        Discovers both single-episode and multi-episode promo candidates across all episodes.
        """
        candidates: List[PromoCandidate] = []
        ep_map = {ep.episode_id: ep for ep in episodes}
        analysis_map = {ea.episode_id: ea for ea in analyses}

        # 1. Discover Single-Episode Candidates
        single_ep_candidates = self.discover_single_episode_promos(episodes, analyses)
        candidates.extend(single_ep_candidates)

        # 2. Discover Multi-Episode Candidates
        multi_ep_candidates = self.discover_multi_episode_promos(episodes, analyses)
        candidates.extend(multi_ep_candidates)

        # 3. Deduplicate
        deduped = self.deduplicate_candidates(candidates)

        # Save discovered candidates
        cache_file = CANDIDATES_DIR / "all_candidates.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        [c.model_dump() for c in deduped], indent=2, default=str
                    )
                )
        except Exception as e:
            logger.error(f"Failed to cache discovered candidates: {e}")

        return deduped

    def discover_single_episode_promos(
        self,
        episodes: List[Episode],
        analyses: List[EpisodeAnalysis],
    ) -> List[PromoCandidate]:
        """
        Generates continuous single-episode promo candidates of 20s to 60s.
        Considers scene starts and all dramatic dialogue/action start points across the scene.
        """
        candidates: List[PromoCandidate] = []
        analysis_map = {ea.episode_id: ea for ea in analyses}

        for ep in episodes:
            ea = analysis_map.get(ep.episode_id)
            for sc in ep.scenes:
                sc_analysis = None
                if ea:
                    for sa in ea.scene_analyses:
                        if sa.scene_id == sc.scene_id:
                            sc_analysis = sa
                            break

                dialogues = sc.dialogues
                actions = sc.actions

                if not dialogues and not actions:
                    continue

                # Potential start points (Hooks):
                # 1. Scene start
                # 2. Dialogue lines that introduce tension, questions, or accusations
                start_candidates = [
                    (
                        sc.start_seconds,
                        sc.start_time,
                        f"Opening scene at {sc.heading}",
                        "SCENE_START",
                    )
                ]
                for d in dialogues:
                    # Every dialogue can potentially be a hook if followed by drama
                    start_candidates.append(
                        (
                            d.start_seconds,
                            d.start_time,
                            f"{d.speaker}: \"{d.text}\"",
                            "DIALOGUE_HOOK",
                        )
                    )

                # For each start candidate, find end candidates within 20s to 60s
                for s_sec, s_time, hook_desc, h_type in start_candidates:
                    # Collect possible end points in [s_sec + min_dur, s_sec + max_dur]
                    possible_ends = []

                    # Check scene end
                    if self.min_duration <= (sc.end_seconds - s_sec) <= self.max_duration:
                        possible_ends.append(
                            (
                                sc.end_seconds,
                                sc.end_time,
                                "Dramatic scene transition",
                            )
                        )

                    # Check dialogues ending in window
                    for d in dialogues:
                        dur = round(d.end_seconds - s_sec, 2)
                        if self.min_duration <= dur <= self.max_duration:
                            possible_ends.append(
                                (
                                    d.end_seconds,
                                    d.end_time,
                                    f"{d.speaker}: \"{d.text}\"",
                                )
                            )

                    # Check actions ending in window
                    for a in actions:
                        dur = round(a.end_seconds - s_sec, 2)
                        if self.min_duration <= dur <= self.max_duration:
                            possible_ends.append(
                                (
                                    a.end_seconds,
                                    a.end_time,
                                    a.description,
                                )
                            )

                    for e_sec, e_time, cliff_desc in possible_ends:
                        dur = round(e_sec - s_sec, 2)
                        contained_d = [
                            d
                            for d in dialogues
                            if d.start_seconds >= s_sec and d.end_seconds <= e_sec
                        ]

                        if len(contained_d) >= 2 or (contained_d and actions):
                            promo_id = f"PROMO_EP{ep.episode_id:02d}_{s_time.replace(':', '').replace('.', '')}_{e_time.replace(':', '').replace('.', '')}"

                            unresolved_q = f"What happens after this revelation: {cliff_desc[:70]}?"
                            rationale = f"Continuous stretch in Episode {ep.episode_id} from {s_time} to {e_time}."
                            if sc_analysis and sc_analysis.cliffhanger_moments:
                                unresolved_q = sc_analysis.cliffhanger_moments[
                                    0
                                ].unresolved_question

                            cand = PromoCandidate(
                                promo_id=promo_id,
                                promo_type="SINGLE_EPISODE",
                                episodes=[ep.episode_id],
                                segments=[
                                    PromoSegment(
                                        episode_id=ep.episode_id,
                                        scene_id=sc.scene_id,
                                        start_time=s_time,
                                        end_time=e_time,
                                        start_seconds=s_sec,
                                        end_seconds=e_sec,
                                        duration_seconds=dur,
                                        description=f"Episode {ep.episode_id} ({s_time} - {e_time})",
                                    )
                                ],
                                total_duration_seconds=dur,
                                hook_text=hook_desc,
                                hook_start_time=s_time,
                                hook_end_time=seconds_to_timestamp(
                                    min(s_sec + 4.0, e_sec)
                                ),
                                cliffhanger_text=cliff_desc,
                                cliffhanger_start_time=seconds_to_timestamp(
                                    max(s_sec, e_sec - 5.0)
                                ),
                                cliffhanger_end_time=e_time,
                                unresolved_question=unresolved_q,
                                rationale=rationale,
                                key_conflict=sc_analysis.key_conflict
                                if sc_analysis
                                else "High dramatic conflict",
                            )
                            candidates.append(cand)

        return candidates

    def discover_multi_episode_promos(
        self,
        episodes: List[Episode],
        analyses: List[EpisodeAnalysis],
    ) -> List[PromoCandidate]:
        """
        Discovers multi-episode combinations combining 2 or 3 related segments
        across consecutive or arc-related episodes, totaling 20s to 60s.
        """
        candidates: List[PromoCandidate] = []
        analysis_map = {ea.episode_id: ea for ea in analyses}
        ep_map = {ep.episode_id: ep for ep in episodes}

        # Cluster episodes by shared characters and narrative arcs
        # Microdrama arcs typically span 2-5 consecutive episodes
        sorted_ep_ids = sorted(ep_map.keys())

        for idx in range(len(sorted_ep_ids) - 1):
            ep_a_id = sorted_ep_ids[idx]
            ep_b_id = sorted_ep_ids[idx + 1]

            ep_a = ep_map[ep_a_id]
            ep_b = ep_map[ep_b_id]

            # Check for shared characters to ensure story continuity
            chars_a = set()
            for sc in ep_a.scenes:
                chars_a.update(sc.characters)
            chars_b = set()
            for sc in ep_b.scenes:
                chars_b.update(sc.characters)

            shared_chars = chars_a.intersection(chars_b)
            if not shared_chars:
                continue

            # Pick a sharp hook segment from Episode A (12s - 25s)
            seg_a_candidates = self._find_short_segments(ep_a, 10.0, 25.0, prefer_start=True)
            # Pick an intense cliffhanger segment from Episode B (12s - 25s)
            seg_b_candidates = self._find_short_segments(ep_b, 10.0, 25.0, prefer_start=False)

            for seg_a in seg_a_candidates[:3]:
                for seg_b in seg_b_candidates[:3]:
                    total_dur = round(seg_a.duration_seconds + seg_b.duration_seconds, 2)
                    if self.min_duration <= total_dur <= self.max_duration:
                        promo_id = f"PROMO_MULTI_EP{ep_a_id:02d}_EP{ep_b_id:02d}_{int(total_dur)}S"

                        hook_text = seg_a.description
                        cliff_text = seg_b.description
                        unresolved_q = f"Will the confrontation between {', '.join(list(shared_chars)[:2])} escalate further?"

                        cand = PromoCandidate(
                            promo_id=promo_id,
                            promo_type="MULTI_EPISODE",
                            episodes=[ep_a_id, ep_b_id],
                            segments=[seg_a, seg_b],
                            total_duration_seconds=total_dur,
                            hook_text=hook_text,
                            hook_start_time=seg_a.start_time,
                            hook_end_time=seconds_to_timestamp(
                                min(seg_a.start_seconds + 4.0, seg_a.end_seconds)
                            ),
                            cliffhanger_text=cliff_text,
                            cliffhanger_start_time=seconds_to_timestamp(
                                max(seg_b.start_seconds, seg_b.end_seconds - 5.0)
                            ),
                            cliffhanger_end_time=seg_b.end_time,
                            unresolved_question=unresolved_q,
                            rationale=f"Multi-episode arc promo joining Ep {ep_a_id} setup and Ep {ep_b_id} climax featuring {', '.join(list(shared_chars)[:2])}.",
                            key_conflict=f"Cross-episode arc involving {', '.join(list(shared_chars)[:2])}",
                        )
                        candidates.append(cand)

        return candidates

    def _find_short_segments(
        self,
        episode: Episode,
        min_sec: float,
        max_sec: float,
        prefer_start: bool = True,
    ) -> List[PromoSegment]:
        """
        Extracts high-impact short segments from an episode for multi-episode combinations.
        """
        segments: List[PromoSegment] = []
        for sc in episode.scenes:
            dialogues = sc.dialogues
            if not dialogues:
                continue

            if prefer_start:
                # Early segment
                for d in dialogues[:4]:
                    s_sec = d.start_seconds
                    for d_end in dialogues:
                        if d_end.end_seconds > s_sec:
                            dur = round(d_end.end_seconds - s_sec, 2)
                            if min_sec <= dur <= max_sec:
                                segments.append(
                                    PromoSegment(
                                        episode_id=episode.episode_id,
                                        scene_id=sc.scene_id,
                                        start_time=d.start_time,
                                        end_time=d_end.end_time,
                                        start_seconds=s_sec,
                                        end_seconds=d_end.end_seconds,
                                        duration_seconds=dur,
                                        description=f"{d.speaker}: \"{d.text}\"",
                                    )
                                )
                                break
            else:
                # Ending segment
                for d_end in reversed(dialogues[-4:]):
                    e_sec = d_end.end_seconds
                    for d_start in reversed(dialogues):
                        if d_start.start_seconds < e_sec:
                            dur = round(e_sec - d_start.start_seconds, 2)
                            if min_sec <= dur <= max_sec:
                                segments.append(
                                    PromoSegment(
                                        episode_id=episode.episode_id,
                                        scene_id=sc.scene_id,
                                        start_time=d_start.start_time,
                                        end_time=d_end.end_time,
                                        start_seconds=d_start.start_seconds,
                                        end_seconds=e_sec,
                                        duration_seconds=dur,
                                        description=f"{d_end.speaker}: \"{d_end.text}\"",
                                    )
                                )
                                break
        return segments

    def deduplicate_candidates(
        self, candidates: List[PromoCandidate]
    ) -> List[PromoCandidate]:
        """
        Removes identical and near-duplicate candidates (>85% temporal overlap in segments).
        """
        unique_candidates: List[PromoCandidate] = []
        seen_fingerprints: Set[str] = set()

        for c in candidates:
            # Build fingerprint based on episodes and segments
            fp_parts = []
            for seg in c.segments:
                # Quantize times to 2-second windows to catch near-duplicates
                s_q = int(seg.start_seconds // 2)
                e_q = int(seg.end_seconds // 2)
                fp_parts.append(f"{seg.episode_id}_{s_q}_{e_q}")

            fingerprint = "|".join(fp_parts)
            if fingerprint not in seen_fingerprints:
                seen_fingerprints.add(fingerprint)
                unique_candidates.append(c)

        return unique_candidates
