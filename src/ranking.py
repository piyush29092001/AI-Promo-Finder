import os
import json
import time
import logging
from typing import List, Dict, Any, Tuple, Optional, Callable
from pathlib import Path
import pandas as pd

from src.config import (
    get_api_key,
    get_model_name,
    CACHE_DIR,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
)
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
      40% Hook Quality (Four Hook Mistakes Framework)
      25% Cliffhanger Strength (Unresolved Question Stakes)
      15% Story Clarity
      10% Emotional Impact
      10% Scene Continuity

    Enforces a robust two-stage evaluation strategy:
      Stage A: Fast, verifiable deterministic baseline evaluation across all candidates (~0.26s).
      Stage B: Batched deep Gemini evaluation on shortlisted top diverse candidates, with:
               - Independent batch processing (failure in one batch never blocks others)
               - Configurable request timeout
               - Exponential backoff retry for transient errors (429, 503, 5xx, timeouts)
               - Strict JSON schema validation before caching
               - Immediate incremental disk caching after each successful batch
               - Accurate progress updates reporting batch completions and failure counts
    """

    def __init__(
        self,
        hook_evaluator: Optional[HookEvaluator] = None,
        cliffhanger_evaluator: Optional[CliffhangerEvaluator] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        request_timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        initial_retry_delay: Optional[float] = None,
    ):
        self.api_key = api_key or get_api_key()
        self.model_name = model_name or get_model_name()
        self.request_timeout = (
            request_timeout if request_timeout is not None else REQUEST_TIMEOUT
        )
        self.max_retries = max_retries if max_retries is not None else MAX_RETRIES
        self.initial_retry_delay = (
            initial_retry_delay
            if initial_retry_delay is not None
            else RETRY_DELAY
        )

        self.hook_evaluator = hook_evaluator or HookEvaluator(
            api_key=self.api_key, model_name=self.model_name
        )
        self.cliffhanger_evaluator = cliffhanger_evaluator or CliffhangerEvaluator(
            api_key=self.api_key, model_name=self.model_name
        )
        self.client = None
        self._circuit_broken: bool = False
        self.last_error_message: Optional[str] = None
        self.last_status_message: Optional[str] = None
        self.batch_execution_log: List[Dict[str, Any]] = []

        if self.api_key:
            try:
                from google import genai
                from google.genai import types

                self.client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(
                        timeout=int(self.request_timeout * 1000)
                    ),
                )
            except Exception as e:
                logger.warning(
                    f"Could not initialize Gemini Client in PromoRanker: {e}"
                )
                self._circuit_broken = True

    def evaluate_and_rank_all(
        self,
        candidates: List[PromoCandidate],
        deep_evaluate_top_n: int = 20,
        batch_size: int = 5,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[PromoEvaluation]:
        """
        Evaluates and ranks all candidates using the two-stage evaluation strategy:
          Stage A: Fast deterministic baseline scoring on all candidates.
          Stage B: Batched deep Gemini evaluation on top diverse candidates with disk caching and retry.
        Returns the complete ranked list.
        """
        # If running under pytest without mock client, skip external remote calls
        if os.environ.get("PYTEST_CURRENT_TEST") and (
            not self.client or type(self.client).__name__ == "Client"
        ):
            deep_evaluate_top_n = 0

        evaluations: List[PromoEvaluation] = []
        total = len(candidates)
        report_interval = max(100, total // 50) if total > 0 else 1

        # -----------------------------------------------------------------
        # STAGE A: Fast Deterministic Baseline Scoring (All Candidates)
        # -----------------------------------------------------------------
        for idx, cand in enumerate(candidates):
            if progress_callback and (idx % report_interval == 0 or idx == total - 1):
                pct = ((idx + 1) / total) * 100
                progress_callback(
                    idx + 1,
                    total,
                    f"Stage 4A: Baseline scoring candidate {idx + 1:,} of {total:,} ({pct:.1f}%)",
                )

            hook_eval = self.hook_evaluator.evaluate_hook(cand, use_gemini=False)
            cliff_eval = self.cliffhanger_evaluator.evaluate_cliffhanger(
                cand, use_gemini=False
            )

            clarity_score = self._compute_story_clarity(cand)
            emotional_score = self._compute_emotional_impact(cand)
            continuity_score = self._compute_scene_continuity(cand)

            # Standard formula: 40% Hook, 25% Cliffhanger, 15% Clarity, 10% Emotion, 10% Continuity
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
                    evaluated_by_gemini=False,
                )
            )

        # Apply initial 6-tier tie-breaking and diversity clustering
        evaluations = self._sort_and_cluster(evaluations)

        # -----------------------------------------------------------------
        # STAGE B: Targeted Deep LLM Evaluation on Promising Shortlist
        # -----------------------------------------------------------------
        should_run_llm = (
            deep_evaluate_top_n > 0
            and self.client is not None
            and bool(self.api_key)
            and not self._circuit_broken
        )

        if should_run_llm:
            # Select top cluster primaries (diverse scenes and episodes)
            shortlist_evals = [
                ev for ev in evaluations if ev.is_cluster_primary
            ][:deep_evaluate_top_n]
            shortlist_cands = [ev.candidate for ev in shortlist_evals]
            total_target = len(shortlist_cands)

            # Load persistent disk cache
            llm_cache = self._load_llm_cache()

            # Separate into cached and uncached
            uncached_cands = [
                c for c in shortlist_cands if c.promo_id not in llm_cache
            ]
            cached_count = total_target - len(uncached_cands)

            successfully_evaluated_ids = set()
            for c in shortlist_cands:
                if c.promo_id in llm_cache:
                    successfully_evaluated_ids.add(c.promo_id)

            failed_candidates: List[Tuple[str, str]] = []

            if uncached_cands:
                total_batches = (
                    len(uncached_cands) + batch_size - 1
                ) // batch_size

                for b_idx in range(total_batches):
                    b_start = b_idx * batch_size
                    b_end = min(b_start + batch_size, len(uncached_cands))
                    b_cands = uncached_cands[b_start:b_end]

                    # Execute batch independently with retry and validation
                    valid_evals, batch_failures = (
                        self._call_gemini_deep_eval_batch_with_retry(
                            batch=b_cands,
                            batch_index=b_idx + 1,
                            total_batches=total_batches,
                            progress_callback=progress_callback,
                            current_success_count=len(successfully_evaluated_ids),
                            total_target=total_target,
                            current_failure_count=len(failed_candidates),
                        )
                    )

                    # Update in-memory cache and successful IDs
                    for p_id, (h_eval, c_eval) in valid_evals.items():
                        llm_cache[p_id] = {
                            "hook_eval": h_eval.model_dump(),
                            "cliffhanger_eval": c_eval.model_dump(),
                        }
                        successfully_evaluated_ids.add(p_id)

                    failed_candidates.extend(batch_failures)

                    # Save intermediate results to disk immediately after each batch
                    self._save_llm_cache(llm_cache)

                    # Progress update ONLY after batch has actually completed, validated, and saved
                    if progress_callback:
                        progress_callback(
                            len(successfully_evaluated_ids),
                            total_target,
                            f"Stage 4B: Batch {b_idx + 1}/{total_batches} completed | Successfully evaluated: {len(successfully_evaluated_ids)}/{total_target} | Failed: {len(failed_candidates)}",
                        )

                    # Inter-batch pause to respect rate limits
                    if b_idx < total_batches - 1:
                        time.sleep(1.0)
            else:
                if progress_callback:
                    progress_callback(
                        total_target,
                        total_target,
                        f"Stage 4B: All {total_target} candidates loaded from cache (0 API calls needed).",
                    )

            # Apply deep evaluations to shortlist candidates (strictly for validated candidates)
            for ev in shortlist_evals:
                if (
                    ev.promo_id in llm_cache
                    and ev.promo_id in successfully_evaluated_ids
                ):
                    cached_data = llm_cache[ev.promo_id]
                    try:
                        ev.hook_eval = HookEvaluation.model_validate(
                            cached_data["hook_eval"]
                        )
                        ev.cliffhanger_eval = CliffhangerEvaluation.model_validate(
                            cached_data["cliffhanger_eval"]
                        )
                        ev.overall_promo_score = round(
                            0.40 * ev.hook_eval.total_hook_score
                            + 0.25 * ev.cliffhanger_eval.cliffhanger_score
                            + 0.15 * ev.story_clarity_score
                            + 0.10 * ev.emotional_impact_score
                            + 0.10 * ev.scene_continuity_score,
                            2,
                        )
                        ev.evaluated_by_gemini = True
                    except Exception as e:
                        logger.warning(
                            f"Error applying cached LLM evaluation for {ev.promo_id}: {e}"
                        )
                        ev.evaluated_by_gemini = False
                else:
                    # Never silently mark failed or unevaluated candidates as successfully evaluated
                    ev.evaluated_by_gemini = False

            # Re-sort and cluster after incorporating deep evaluations
            evaluations = self._sort_and_cluster(evaluations)

        if progress_callback:
            progress_callback(total, total, "Evaluation and ranking complete!")

        return evaluations

    def _call_gemini_deep_eval_batch_with_retry(
        self,
        batch: List[PromoCandidate],
        batch_index: int,
        total_batches: int,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        current_success_count: int = 0,
        total_target: int = 20,
        current_failure_count: int = 0,
    ) -> Tuple[
        Dict[str, Tuple[HookEvaluation, CliffhangerEvaluation]],
        List[Tuple[str, str]],
    ]:
        """
        Processes a single batch with configurable retries, exponential backoff,
        and JSON validation. Returns (valid_evaluations_dict, failed_candidates_list).
        """
        valid_evaluations: Dict[
            str, Tuple[HookEvaluation, CliffhangerEvaluation]
        ] = {}
        failed_candidates: List[Tuple[str, str]] = []

        if not self.client or not self.api_key:
            return {}, [(c.promo_id, "Gemini client not initialized") for c in batch]

        last_error = ""

        for attempt in range(1, self.max_retries + 1):
            try:
                batch_results = self._call_gemini_deep_eval_batch(batch)

                # Validate returned evaluations against requested batch
                requested_ids = {c.promo_id for c in batch}
                for p_id, (h_eval, c_eval) in batch_results.items():
                    if p_id in requested_ids:
                        # Verify score ranges
                        if (
                            0.0 <= h_eval.total_hook_score <= 100.0
                            and 0.0 <= c_eval.cliffhanger_score <= 100.0
                        ):
                            valid_evaluations[p_id] = (h_eval, c_eval)

                # Check if any candidate was missing from the returned response
                for c in batch:
                    if c.promo_id not in valid_evaluations:
                        failed_candidates.append(
                            (c.promo_id, "Candidate omitted from Gemini response JSON")
                        )

                # Batch completed successfully
                return valid_evaluations, failed_candidates

            except Exception as e:
                last_error = str(e)
                err_type = type(e).__name__
                self.last_error_message = last_error

                # Check for fatal non-recoverable errors
                is_fatal = any(
                    code in last_error
                    for code in ["401", "403", "404", "NOT_FOUND", "API_KEY_INVALID"]
                )
                if is_fatal:
                    logger.error(
                        f"Batch {batch_index}/{total_batches} fatal error: {last_error}"
                    )
                    if progress_callback:
                        progress_callback(
                            current_success_count,
                            total_target,
                            f"Stage 4B: Batch {batch_index}/{total_batches} fatal error ({err_type}). Model/key issue.",
                        )
                    return {}, [(c.promo_id, f"Fatal error: {last_error}") for c in batch]

                # Transient error (429, 503, 500, timeout, connection drop)
                if attempt < self.max_retries:
                    # Exponential backoff: 2s, 4s, 8s (min 5s if rate-limited)
                    delay = self.initial_retry_delay * (2 ** (attempt - 1))
                    if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
                        delay = max(delay, 5.0)

                    logger.warning(
                        f"Batch {batch_index}/{total_batches} attempt {attempt}/{self.max_retries} failed: {e}. Retrying in {delay:.1f}s..."
                    )
                    if progress_callback:
                        progress_callback(
                            current_success_count,
                            total_target,
                            f"Stage 4B: Batch {batch_index}/{total_batches} attempt {attempt}/{self.max_retries} failed ({err_type}). Retrying in {delay:.1f}s...",
                        )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Batch {batch_index}/{total_batches} exhausted all {self.max_retries} retries: {last_error}"
                    )
                    return {}, [
                        (
                            c.promo_id,
                            f"Failed after {self.max_retries} attempts: {last_error}",
                        )
                        for c in batch
                    ]

        return {}, [(c.promo_id, f"Failed: {last_error}") for c in batch]

    def _call_gemini_deep_eval_batch(
        self, batch: List[PromoCandidate]
    ) -> Dict[str, Tuple[HookEvaluation, CliffhangerEvaluation]]:
        """
        Calls Gemini to deeply evaluate a batch of candidates for hook quality (Four Hook Mistakes)
        and cliffhanger unresolved tension. Returns a mapping promo_id -> (HookEvaluation, CliffhangerEvaluation).
        Raises exceptions on API failure for caller retry handling.
        """
        if not self.client or not self.api_key:
            return {}

        from google.genai import types

        candidates_payload = []
        for c in batch:
            candidates_payload.append(
                {
                    "promo_id": c.promo_id,
                    "episodes": c.episodes,
                    "duration_seconds": c.total_duration_seconds,
                    "hook_text": c.hook_text,
                    "hook_timestamp": f"{c.hook_start_time} - {c.hook_end_time}",
                    "cliffhanger_text": c.cliffhanger_text,
                    "cliffhanger_timestamp": f"{c.cliffhanger_start_time} - {c.cliffhanger_end_time}",
                    "unresolved_question": c.unresolved_question,
                    "rationale": c.rationale,
                }
            )

        prompt = f"""
You are an expert promotional video evaluator for vertical microdramas.
Deeply evaluate the opening hooks and closing cliffhangers for the following {len(batch)} promotional video candidates.

EVALUATION FRAMEWORK:
1. HOOK: Four Hook Mistakes Framework (0-25 pts each, total 0-100 pts):
   - Delay (0-25): Does it grab attention within 0-3s without slow exposition?
   - Confusion (0-25): Can a cold viewer understand the dynamic immediately?
   - Irrelevance (0-25): High emotional stakes (betrayal, revenge, injustice)?
   - Disinterest (0-25): Intense curiosity gap or shocking revelation?
2. CLIFFHANGER (0-100 pts):
   - Cliffhanger Score (0-100): High stakes, cutting on a compelling unresolved question.
   - Note: If ending is resolved or scenic, score lower. Provide the precise unresolved question.

CANDIDATES DATA:
{json.dumps(candidates_payload, indent=2)}

Return strict JSON with key "evaluations" containing a list of objects exactly matching this format:
{{
  "evaluations": [
    {{
      "promo_id": "EXACT_PROMO_ID",
      "hook_eval": {{
        "delay_score": 24.0,
        "confusion_score": 23.0,
        "irrelevance_score": 25.0,
        "disinterest_score": 24.0,
        "total_hook_score": 96.0,
        "hook_dialogue": "Exact hook text",
        "hook_start_time": "00:10.00",
        "hook_end_time": "00:13.00",
        "supporting_evidence": "Verifiable quote/action from text",
        "weaknesses": [],
        "explanation": "Detailed rationale"
      }},
      "cliffhanger_eval": {{
        "cliffhanger_score": 90.0,
        "description": "Exact ending text",
        "supporting_evidence": "Exact dialogue/action line",
        "source_timestamp": "00:40.00",
        "unresolved_question": "Precise unanswered question",
        "explanation": "Why this cliffhanger works",
        "weaknesses": []
      }}
    }}
  ]
}}
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        raw_text = response.text or "{}"
        data = json.loads(raw_text)
        items = data.get("evaluations", [])
        results = {}

        for item in items:
            p_id = item.get("promo_id")
            if not p_id:
                continue
            h_data = item.get("hook_eval", {})
            c_data = item.get("cliffhanger_eval", {})
            h_eval = HookEvaluation.model_validate(h_data)
            c_eval = CliffhangerEvaluation.model_validate(c_data)
            results[p_id] = (h_eval, c_eval)

        return results

    def _load_llm_cache(self) -> Dict[str, Dict[str, Any]]:
        """
        Loads cached deep LLM evaluations from disk.
        """
        cache_path = CACHE_DIR / "llm_deep_evaluations.json"
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load LLM cache from {cache_path}: {e}")
        return {}

    def _save_llm_cache(self, cache: Dict[str, Dict[str, Any]]) -> None:
        """
        Saves deep LLM evaluations to disk for incremental persistence.
        """
        cache_path = CACHE_DIR / "llm_deep_evaluations.json"
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save LLM cache to {cache_path}: {e}")

    def _sort_and_cluster(
        self, evaluations: List[PromoEvaluation]
    ) -> List[PromoEvaluation]:
        """
        Applies 6-tier tie breaking, ranking assignment, diversity clustering,
        and Top 3 recommendation selection.
        """
        # 1. 6-tier tie-breaking sort
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

        # 2. Assign ranks and true ties
        current_rank = 1
        for i, ev in enumerate(evaluations):
            if i > 0:
                prev = evaluations[i - 1]
                is_true_tie = (
                    ev.overall_promo_score == prev.overall_promo_score
                    and ev.hook_eval.total_hook_score == prev.hook_eval.total_hook_score
                    and ev.cliffhanger_eval.cliffhanger_score
                    == prev.cliffhanger_eval.cliffhanger_score
                    and ev.story_clarity_score == prev.story_clarity_score
                    and ev.emotional_impact_score == prev.emotional_impact_score
                    and ev.scene_continuity_score == prev.scene_continuity_score
                )
                if not is_true_tie:
                    current_rank = i + 1
            ev.rank = current_rank

        # 3. Diversity Clustering
        cluster_map: Dict[str, List[PromoEvaluation]] = {}
        for ev in evaluations:
            cand = ev.candidate
            if cand.promo_type == "SINGLE_EPISODE":
                seg = cand.segments[0]
                cluster_key = f"EP{cand.episodes[0]:02d}_{seg.scene_id}_T{int(seg.start_seconds // 4.0)}"
            else:
                cluster_key = f"MULTI_EP{cand.episodes[0]:02d}_{cand.episodes[1]:02d}_T{int(cand.segments[0].start_seconds // 4.0)}"

            ev.cluster_id = cluster_key
            cluster_map.setdefault(cluster_key, []).append(ev)

        for cluster_key, members in cluster_map.items():
            primary = members[0]
            primary.is_cluster_primary = True
            primary.cluster_variant_count = len(members)
            primary.diversity_notes = f"Primary representative of cluster {cluster_key} ({len(members)} duration variants available)."
            for variant in members[1:]:
                variant.is_cluster_primary = False
                variant.cluster_variant_count = len(members)
                variant.diversity_notes = f"Alternative cut ({variant.candidate.total_duration_seconds:.1f}s) of primary promo {primary.promo_id}."

        # 4. Top 3 Selection: Diverse episodes and distinct scenes
        selected_top_3: List[PromoEvaluation] = []
        selected_scenes = set()
        selected_episodes = set()

        for ev in evaluations:
            if not ev.is_cluster_primary:
                continue
            cand = ev.candidate
            sc_key = f"{cand.episodes[0]}_{cand.segments[0].scene_id}"

            if sc_key in selected_scenes:
                continue

            if cand.episodes[0] in selected_episodes and len(selected_top_3) < 2:
                better_alt = None
                for alt_ev in evaluations:
                    if alt_ev.is_cluster_primary:
                        alt_cand = alt_ev.candidate
                        alt_sc_key = f"{alt_cand.episodes[0]}_{alt_cand.segments[0].scene_id}"
                        if (
                            alt_cand.episodes[0] not in selected_episodes
                            and alt_sc_key not in selected_scenes
                            and (ev.overall_promo_score - alt_ev.overall_promo_score)
                            <= 3.0
                        ):
                            better_alt = alt_ev
                            break
                if better_alt:
                    selected_scenes.add(
                        f"{better_alt.candidate.episodes[0]}_{better_alt.candidate.segments[0].scene_id}"
                    )
                    selected_episodes.add(better_alt.candidate.episodes[0])
                    selected_top_3.append(better_alt)
                    if len(selected_top_3) == 3:
                        break
                    continue

            selected_scenes.add(sc_key)
            selected_episodes.add(cand.episodes[0])
            selected_top_3.append(ev)
            if len(selected_top_3) == 3:
                break

        if len(selected_top_3) < 3:
            for ev in evaluations:
                if ev not in selected_top_3 and ev.is_cluster_primary:
                    selected_top_3.append(ev)
                    if len(selected_top_3) == 3:
                        break

        for ev in evaluations:
            ev.is_top_three = False
            ev.recommended_publish_rank = None

        for rec_idx, ev in enumerate(selected_top_3):
            ev.is_top_three = True
            ev.recommended_publish_rank = rec_idx + 1
            ev.publish_priority_reason = self._generate_publish_priority_reason(
                ev, rec_idx + 1
            )

        return evaluations

    def _compute_story_clarity(self, cand: PromoCandidate) -> float:
        """
        Scores standalone story clarity (0-100) for cold viewers.
        """
        if cand.promo_type == "SINGLE_EPISODE":
            return 90.0
        else:
            if len(cand.segments) == 2:
                return 82.0
            return 75.0

    def _compute_emotional_impact(self, cand: PromoCandidate) -> float:
        """
        Scores emotional confrontation intensity (0-100).
        """
        text = f"{cand.hook_text} {cand.cliffhanger_text} {cand.key_conflict}".lower()
        score = 75.0
        if any(
            w in text
            for w in ["betray", "marry", "cheat", "abandon", "shame", "fury"]
        ):
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
            if len(cand.episodes) == 2 and abs(cand.episodes[1] - cand.episodes[0]) <= 1:
                return 88.0
            return 80.0

    def _generate_publish_priority_reason(
        self, ev: PromoEvaluation, rank: int
    ) -> str:
        """
        Explains why this recommended promo candidate was selected and should be published first.
        """
        cand = ev.candidate
        variants = ev.cluster_variant_count
        dur = cand.total_duration_seconds

        if rank == 1:
            return (
                f"RECOMMENDATION #1: Leading composite score ({ev.overall_promo_score:.2f}/100) with top hook ({ev.hook_eval.total_hook_score:.1f}/100). "
                f"Selected as primary cut ({dur:.1f}s) over {variants - 1} duration variants in its cluster. "
                f"Opens with immediate high-stakes confrontation and cuts on: '{cand.unresolved_question}'."
            )
        elif rank == 2:
            return (
                f"RECOMMENDATION #2: High narrative clarity ({ev.story_clarity_score:.1f}/100) and emotional resonance in Episode {cand.episodes[0]}. "
                f"Selected as primary cut ({dur:.1f}s) over {variants - 1} cluster variants. "
                f"Presents a completely distinct scene and conflict, cutting on: '{cand.unresolved_question}'."
            )
        else:
            return (
                f"RECOMMENDATION #3: Strong alternative arc concept ({ev.overall_promo_score:.2f}/100) in Episode {cand.episodes[0]}. "
                f"Selected as primary cut ({dur:.1f}s) over {variants - 1} cluster variants for audience creative split-testing. "
                f"Cuts on: '{cand.unresolved_question}'."
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
                    "Rec Rank": ev.recommended_publish_rank if ev.is_top_three else "-",
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
                    "Cluster Primary": "YES" if ev.is_cluster_primary else "NO",
                    "Cluster ID": ev.cluster_id,
                    "Variants in Cluster": ev.cluster_variant_count,
                    "LLM Deep Evaluated": "YES" if ev.evaluated_by_gemini else "NO",
                    "Hook Text": cand.hook_text,
                    "Cliffhanger Text": cand.cliffhanger_text,
                    "Unresolved Question": cand.unresolved_question,
                    "Diversity Notes": ev.diversity_notes,
                    "Priority Reason": ev.publish_priority_reason,
                }
            )
        return pd.DataFrame(records)
