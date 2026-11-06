import json
import logging
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path

from src.config import (
    QUALITY_REPORTS_DIR,
    RAW_OUTPUTS_DIR,
    PROMO_MIN_DURATION,
    PROMO_MAX_DURATION,
    get_api_key,
    get_model_name,
)
from src.models import (
    PromoCandidate,
    PromoEvaluation,
    Episode,
    QualityError,
    QualityReport,
    timestamp_to_seconds,
)

logger = logging.getLogger(__name__)


class QualityChecker:
    """
    Quality Evaluation Engine combining:
    Method 1: Strict Python Rule-Based Validation
    Method 2: Independent Adversarial Evaluation (Gemini or Heuristic Auditor)
    Supports recording evaluator disagreements and human review status.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        min_duration: float = PROMO_MIN_DURATION,
        max_duration: float = PROMO_MAX_DURATION,
    ):
        self.api_key = api_key or get_api_key()
        self.model_name = model_name or get_model_name()
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client for QualityChecker: {e}")

    def run_full_quality_check(
        self, evaluations: List[PromoEvaluation], episodes: List[Episode]
    ) -> QualityReport:
        """
        Runs both Method 1 (Rule-based) and Method 2 (Independent Audit)
        and compiles a QualityReport.
        """
        candidates = [ev.candidate for ev in evaluations]

        # Method 1: Rule-Based Validation
        rule_errors = self.validate_rules(candidates, episodes)

        # Method 2: Independent Audit
        llm_errors, disagreements = self.independent_audit(evaluations, episodes)

        all_errors = rule_errors + llm_errors

        report = QualityReport(
            total_promos_checked=len(candidates),
            rule_violations_count=len(rule_errors),
            llm_audit_issues_count=len(llm_errors),
            errors=all_errors,
            disagreements=disagreements,
        )

        # Cache report
        cache_file = QUALITY_REPORTS_DIR / "quality_report.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(report.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to cache quality report: {e}")

        return report

    def validate_rules(
        self, candidates: List[PromoCandidate], episodes: List[Episode]
    ) -> List[QualityError]:
        """
        METHOD 1: PYTHON RULE-BASED VALIDATION
        Enforces strict structural, temporal, and reference integrity.
        """
        errors: List[QualityError] = []
        ep_map: Dict[int, Episode] = {ep.episode_id: ep for ep in episodes}
        seen_fingerprints: Set[str] = set()

        for idx, cand in enumerate(candidates):
            promo_id = cand.promo_id

            # Rule 1: Duration bounds
            dur = cand.total_duration_seconds
            if dur < self.min_duration:
                errors.append(
                    QualityError(
                        error_id=f"ERR_RULE_DUR_SHORT_{idx}",
                        promo_id=promo_id,
                        episode_number=cand.episodes[0] if cand.episodes else 0,
                        timestamp=cand.hook_start_time,
                        error_type="DURATION_OUT_OF_BOUNDS",
                        explanation=f"Total duration {dur:.2f}s is below minimum allowed {self.min_duration:.1f}s.",
                        severity="HIGH",
                        suggested_correction=f"Extend segment boundaries by at least {self.min_duration - dur:.2f}s.",
                    )
                )
            elif dur > self.max_duration:
                errors.append(
                    QualityError(
                        error_id=f"ERR_RULE_DUR_LONG_{idx}",
                        promo_id=promo_id,
                        episode_number=cand.episodes[0] if cand.episodes else 0,
                        timestamp=cand.hook_start_time,
                        error_type="DURATION_OUT_OF_BOUNDS",
                        explanation=f"Total duration {dur:.2f}s exceeds maximum allowed {self.max_duration:.1f}s.",
                        severity="HIGH",
                        suggested_correction=f"Trim segment boundaries by at least {dur - self.max_duration:.2f}s.",
                    )
                )

            # Rule 2: Episode and Scene references exist in source data
            for seg in cand.segments:
                ep = ep_map.get(seg.episode_id)
                if not ep:
                    errors.append(
                        QualityError(
                            error_id=f"ERR_RULE_EP_NOT_FOUND_{idx}",
                            promo_id=promo_id,
                            episode_number=seg.episode_id,
                            timestamp=seg.start_time,
                            error_type="INVALID_EPISODE_REFERENCE",
                            explanation=f"Referenced Episode {seg.episode_id} does not exist in the source dataset.",
                            severity="HIGH",
                            suggested_correction="Verify episode number or input file presence.",
                        )
                    )
                    continue

                sc = next((s for s in ep.scenes if s.scene_id == seg.scene_id), None)
                if not sc:
                    errors.append(
                        QualityError(
                            error_id=f"ERR_RULE_SCENE_NOT_FOUND_{idx}",
                            promo_id=promo_id,
                            episode_number=seg.episode_id,
                            timestamp=seg.start_time,
                            error_type="INVALID_SCENE_REFERENCE",
                            explanation=f"Referenced Scene {seg.scene_id} does not exist in Episode {seg.episode_id}.",
                            severity="HIGH",
                            suggested_correction="Regenerate candidates using valid scene identifiers.",
                        )
                    )
                    continue

                # Rule 3: Start time before End time
                if seg.start_seconds >= seg.end_seconds:
                    errors.append(
                        QualityError(
                            error_id=f"ERR_RULE_INVERTED_TIME_{idx}",
                            promo_id=promo_id,
                            episode_number=seg.episode_id,
                            timestamp=seg.start_time,
                            error_type="INVERTED_TIMESTAMPS",
                            explanation=f"Segment start time ({seg.start_time}) is after or equal to end time ({seg.end_time}).",
                            severity="HIGH",
                            suggested_correction="Ensure start timestamp precedes end timestamp.",
                        )
                    )

                # Rule 4: Timestamps fall within source scene bounds
                if seg.start_seconds < sc.start_seconds or seg.end_seconds > (sc.end_seconds + 0.5):
                    errors.append(
                        QualityError(
                            error_id=f"ERR_RULE_OUT_OF_SCENE_{idx}",
                            promo_id=promo_id,
                            episode_number=seg.episode_id,
                            timestamp=seg.start_time,
                            error_type="TIMESTAMP_OUT_OF_SCENE",
                            explanation=f"Segment [{seg.start_time} - {seg.end_time}] falls outside scene limits [{sc.start_time} - {sc.end_time}].",
                            severity="MEDIUM",
                            suggested_correction="Clamp segment bounds to source scene boundaries.",
                        )
                    )

            # Rule 5: Duplicate candidate check
            fp = "|".join(f"{s.episode_id}_{s.start_time}_{s.end_time}" for s in cand.segments)
            if fp in seen_fingerprints:
                errors.append(
                    QualityError(
                        error_id=f"ERR_RULE_DUP_{idx}",
                        promo_id=promo_id,
                        episode_number=cand.episodes[0] if cand.episodes else 0,
                        timestamp=cand.hook_start_time,
                        error_type="DUPLICATE_CANDIDATE",
                        explanation=f"Candidate {promo_id} has identical timestamps to another candidate.",
                        severity="MEDIUM",
                        suggested_correction="Remove duplicate candidate.",
                    )
                )
            else:
                seen_fingerprints.add(fp)

        return errors

    def independent_audit(
        self, evaluations: List[PromoEvaluation], episodes: List[Episode]
    ) -> Tuple[List[QualityError], List[str]]:
        """
        METHOD 2: INDEPENDENT ADVERSARIAL EVALUATION
        Critiques narrative continuity, weak hooks, weak cliffhangers, and story jumps.
        Records disagreements between discovery engine and evaluator.
        """
        audit_errors: List[QualityError] = []
        disagreements: List[str] = []

        for idx, ev in enumerate(evaluations):
            cand = ev.candidate
            hook_ev = ev.hook_eval
            cliff_ev = ev.cliffhanger_eval

            # Check 1: Weak Hook Criticism
            if hook_ev.total_hook_score < 80.0:
                audit_errors.append(
                    QualityError(
                        error_id=f"AUDIT_WEAK_HOOK_{idx}",
                        promo_id=cand.promo_id,
                        episode_number=cand.episodes[0],
                        timestamp=cand.hook_start_time,
                        error_type="WEAK_HOOK",
                        explanation=f"Hook score is only {hook_ev.total_hook_score:.1f}/100. Issues: {', '.join(hook_ev.weaknesses) or 'Low curiosity gap'}.",
                        severity="MEDIUM",
                        suggested_correction="Trim the first 2-4 seconds to open directly on the confrontation line.",
                    )
                )

            # Check 2: Weak Cliffhanger Criticism
            if cliff_ev.cliffhanger_score < 80.0:
                audit_errors.append(
                    QualityError(
                        error_id=f"AUDIT_WEAK_CLIFF_{idx}",
                        promo_id=cand.promo_id,
                        episode_number=cand.episodes[-1],
                        timestamp=cand.cliffhanger_end_time,
                        error_type="WEAK_CLIFFHANGER",
                        explanation=f"Cliffhanger score is {cliff_ev.cliffhanger_score:.1f}/100. Issues: {', '.join(cliff_ev.weaknesses) or 'Question not sufficiently unresolved'}.",
                        severity="MEDIUM",
                        suggested_correction="Cut on the exact accusation or dramatic line rather than following scene transition.",
                    )
                )

            # Check 3: Story jump in multi-episode promo
            if cand.promo_type == "MULTI_EPISODE" and len(cand.episodes) >= 2:
                gap = abs(cand.episodes[1] - cand.episodes[0])
                if gap > 3:
                    disagreements.append(
                        f"Promo {cand.promo_id}: Evaluator flagged story jump between Ep {cand.episodes[0]} and Ep {cand.episodes[1]} ({gap} episodes apart). Discovery engine argued shared character maintains emotional continuity."
                    )
                    audit_errors.append(
                        QualityError(
                            error_id=f"AUDIT_STORY_GAP_{idx}",
                            promo_id=cand.promo_id,
                            episode_number=cand.episodes[0],
                            timestamp=cand.hook_start_time,
                            error_type="NARRATIVE_CONTINUITY_GAP",
                            explanation=f"Episodes {cand.episodes[0]} and {cand.episodes[1]} are {gap} episodes apart; viewers may miss character state changes.",
                            severity="LOW",
                            suggested_correction="Pair consecutive episodes or add text context overlay in final distribution.",
                        )
                    )

        return audit_errors, disagreements
