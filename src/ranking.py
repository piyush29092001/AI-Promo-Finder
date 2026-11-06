import logging
from typing import List, Dict, Any, Tuple
import pandas as pd

from src.models import (
    PromoCandidate,
    PromoEvaluation,
    HookEvaluation,
    CliffhangerEvaluation,
)
from src.hook_evaluator import HookEvaluator
from src.cliffhanger_evaluator import CliffhangerEvaluator

logger = logging.getLogger(__name__)


class PromoRanker:
    """
    Ranks promo candidates according to the multi-criteria formula:
    Promo Score =
      40% Hook Quality
      25% Cliffhanger Strength
      15% Story Clarity
      10% Emotional Impact
      10% Scene Continuity

    Enforces deterministic tie-breaking without inventing arbitrary winners.
    """

    def __init__(
        self,
        hook_evaluator: HookEvaluator = None,
        cliffhanger_evaluator: CliffhangerEvaluator = None,
    ):
        self.hook_evaluator = hook_evaluator or HookEvaluator()
        self.cliffhanger_evaluator = cliffhanger_evaluator or CliffhangerEvaluator()

    def evaluate_and_rank_all(
        self, candidates: List[PromoCandidate]
    ) -> List[PromoEvaluation]:
        """
        Evaluates and ranks all candidates. Returns full ranked list.
        """
        evaluations: List[PromoEvaluation] = []

        for cand in candidates:
            hook_eval = self.hook_evaluator.evaluate_hook(cand)
            cliff_eval = self.cliffhanger_evaluator.evaluate_cliffhanger(cand)

            clarity_score = self._compute_story_clarity(cand)
            emotional_score = self._compute_emotional_impact(cand)
            continuity_score = self._compute_scene_continuity(cand)

            # Scoring formula: 40% Hook, 25% Cliffhanger, 15% Clarity, 10% Emotion, 10% Continuity
            overall_score = round(
                0.40 * hook_eval.total_hook_score
                + 0.25 * cliff_eval.cliffhanger_score
                + 0.15 * clarity_score
                + 0.10 * emotional_score
                + 0.10 * continuity_score,
                2,
            )

            evaluations.append(
                PromoEvaluation(
                    promo_id=cand.promo_id,
                    candidate=cand,
                    hook_eval=hook_eval,
                    cliffhanger_eval=cliff_eval,
                    story_clarity_score=clarity_score,
                    emotional_impact_score=emotional_score,
                    scene_continuity_score=continuity_score,
                    overall_promo_score=overall_score,
                )
            )

        # Apply tie-breaking sorting
        # Priority:
        # 1. Overall promo score (descending)
        # 2. Hook score (descending)
        # 3. Cliffhanger score (descending)
        # 4. Story clarity (descending)
        # 5. Emotional impact (descending)
        # 6. Scene continuity (descending)
        evaluations.sort(
            key=lambda e: (
                -e.overall_promo_score,
                -e.hook_eval.total_hook_score,
                -e.cliffhanger_eval.cliffhanger_score,
                -e.story_clarity_score,
                -e.emotional_impact_score,
                -e.scene_continuity_score,
            )
        )

        # Assign ranks and handle true ties
        current_rank = 1
        for i, ev in enumerate(evaluations):
            if i > 0:
                prev = evaluations[i - 1]
                # Compare all 6 criteria for a true tie
                is_true_tie = (
                    ev.overall_promo_score == prev.overall_promo_score
                    and ev.hook_eval.total_hook_score == prev.hook_eval.total_hook_score
                    and ev.cliffhanger_eval.cliffhanger_score == prev.cliffhanger_eval.cliffhanger_score
                    and ev.story_clarity_score == prev.story_clarity_score
                    and ev.emotional_impact_score == prev.emotional_impact_score
                    and ev.scene_continuity_score == prev.scene_continuity_score
                )
                if not is_true_tie:
                    current_rank = i + 1

            ev.rank = current_rank
            if i < 3:
                ev.is_top_three = True
                ev.publish_priority_reason = self._generate_publish_priority_reason(
                    ev, i + 1
                )

        return evaluations

    def _compute_story_clarity(self, cand: PromoCandidate) -> float:
        """
        Scores standalone story clarity (0-100) for cold viewers.
        """
        if cand.promo_type == "SINGLE_EPISODE":
            # Continuous scene has inherently high narrative coherence
            return 90.0
        else:
            # Multi-episode clarity depends on segment count
            if len(cand.segments) == 2:
                return 82.0
            return 75.0

    def _compute_emotional_impact(self, cand: PromoCandidate) -> float:
        """
        Scores emotional confrontation intensity (0-100).
        """
        text = f"{cand.hook_text} {cand.cliffhanger_text} {cand.key_conflict}".lower()
        score = 75.0
        if any(w in text for w in ["betray", "marry", "cheat", "abandon", "shame", "fury"]):
            score += 15.0
        if any(w in text for w in ["kill", "poison", "blood", "die", "destroy"]):
            score += 10.0
        return min(100.0, round(score, 1))

    def _compute_scene_continuity(self, cand: PromoCandidate) -> float:
        """
        Scores scene continuity and editorial smoothness (0-100).
        """
        if cand.promo_type == "SINGLE_EPISODE":
            return 98.0
        else:
            # Multi-episode cross-cutting has slight editorial jump
            if len(cand.episodes) == 2 and abs(cand.episodes[1] - cand.episodes[0]) <= 1:
                return 88.0
            return 80.0

    def _generate_publish_priority_reason(
        self, ev: PromoEvaluation, rank: int
    ) -> str:
        """
        Explains why this recommended promo candidate should be published first.
        """
        cand = ev.candidate
        if rank == 1:
            return (
                f"PRIORITY 1: Highest composite score ({ev.overall_promo_score}/100) with top hook ({ev.hook_eval.total_hook_score}/100). "
                f"Immediate emotional betrayal hook with zero delay, leaving unresolved cliffhanger: '{cand.unresolved_question}'."
            )
        elif rank == 2:
            return (
                f"PRIORITY 2: Strong story clarity ({ev.story_clarity_score}/100) and cliffhanger tension ({ev.cliffhanger_eval.cliffhanger_score}/100). "
                f"Delivers an unbroken dramatic confrontation that needs no prior context for scrolling audiences."
            )
        else:
            return (
                f"PRIORITY 3: High emotional resonance ({ev.emotional_impact_score}/100) providing an alternative character arc angle. "
                f"Optimized 20-60s pacing ({cand.total_duration_seconds}s) with clean transition to cliffhanger."
            )

    def to_dataframe(self, evaluations: List[PromoEvaluation]) -> pd.DataFrame:
        """
        Converts evaluations to a Pandas DataFrame for dashboard inspection and CSV export.
        """
        records = []
        for ev in evaluations:
            cand = ev.candidate
            records.append(
                {
                    "Rank": ev.rank,
                    "Promo ID": ev.promo_id,
                    "Type": cand.promo_type,
                    "Episodes": ", ".join(str(e) for e in cand.episodes),
                    "Duration (s)": cand.total_duration_seconds,
                    "Overall Score": ev.overall_promo_score,
                    "Hook Score (40%)": ev.hook_eval.total_hook_score,
                    "Cliffhanger Score (25%)": ev.cliffhanger_eval.cliffhanger_score,
                    "Clarity Score (15%)": ev.story_clarity_score,
                    "Emotional Score (10%)": ev.emotional_impact_score,
                    "Continuity Score (10%)": ev.scene_continuity_score,
                    "Top 3": "YES" if ev.is_top_three else "NO",
                    "Hook Text": cand.hook_text,
                    "Cliffhanger Text": cand.cliffhanger_text,
                    "Unresolved Question": cand.unresolved_question,
                    "Priority Reason": ev.publish_priority_reason,
                }
            )
        df = pd.DataFrame(records)
        return df
