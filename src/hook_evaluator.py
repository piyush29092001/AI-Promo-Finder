import json
import logging
import re
from typing import Optional, List, Dict, Any

from src.config import get_api_key, get_model_name, RAW_OUTPUTS_DIR
from src.models import PromoCandidate, HookEvaluation, timestamp_to_seconds

logger = logging.getLogger(__name__)


class HookEvaluator:
    """
    Evaluates promo opening hooks using the Four Hook Mistakes Framework:
    1. Delay (0-25)
    2. Confusion (0-25)
    3. Irrelevance (0-25)
    4. Disinterest (0-25)
    Total Hook Score: 0-100.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.model_name = model_name or get_model_name()
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client for HookEvaluator: {e}")

    def evaluate_hook(self, candidate: PromoCandidate) -> HookEvaluation:
        """
        Evaluates the hook of a PromoCandidate. Uses Gemini if available,
        otherwise uses deterministic rubric analysis.
        """
        if self.client and self.api_key:
            try:
                return self._call_gemini_hook_eval(candidate)
            except Exception as e:
                logger.error(f"Gemini hook evaluation failed: {e}. Using rubric fallback.")
                return self._heuristic_hook_eval(candidate)
        else:
            return self._heuristic_hook_eval(candidate)

    def _call_gemini_hook_eval(self, candidate: PromoCandidate) -> HookEvaluation:
        from google.genai import types

        prompt = f"""
You are an expert promotional video evaluator for vertical microdramas.
Evaluate the opening hook of this candidate promo using the Four Hook Mistakes Framework:

FACTOR 1: DELAY (0 to 25 pts)
Does it grab attention immediately within the first 0-3 seconds? Does it avoid slow exposition or unnecessary buildup?

FACTOR 2: CONFUSION (0 to 25 pts)
Can a new viewer who has NEVER seen the show understand the basic situation and relationship dynamic immediately?

FACTOR 3: IRRELEVANCE (0 to 25 pts)
Does it create relatable emotional stakes (betrayal, heartbreak, injustice, danger) that make a viewer care?

FACTOR 4: DISINTEREST (0 to 25 pts)
Does it provoke intense curiosity, contrast, or unanswered questions?

PROMO CANDIDATE:
- Promo ID: {candidate.promo_id}
- Promo Type: {candidate.promo_type}
- Episodes: {candidate.episodes}
- Hook Text: {candidate.hook_text}
- Hook Start: {candidate.hook_start_time}
- Hook End: {candidate.hook_end_time}
- Total Duration: {candidate.total_duration_seconds}s
- Rationale: {candidate.rationale}

Return valid JSON with:
{{
  "delay_score": 23.0,
  "confusion_score": 22.0,
  "irrelevance_score": 24.0,
  "disinterest_score": 23.5,
  "total_hook_score": 92.5,
  "hook_dialogue": "{candidate.hook_text}",
  "hook_start_time": "{candidate.hook_start_time}",
  "hook_end_time": "{candidate.hook_end_time}",
  "supporting_evidence": "Verifiable quote/action from the text",
  "weaknesses": ["Any minor issue found"],
  "explanation": "Detailed rationale"
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
        data = json.loads(response.text)
        return HookEvaluation.model_validate(data)

    def _heuristic_hook_eval(self, candidate: PromoCandidate) -> HookEvaluation:
        """
        Deterministic, transparent evaluation using the Four Hook Mistakes Framework.
        """
        hook_text = candidate.hook_text
        lower_hook = hook_text.lower()
        weaknesses: List[str] = []

        # 1. DELAY (Max 25)
        # Check start timestamp: promos that start immediately on dialogue get highest score
        delay_score = 25.0
        start_sec = timestamp_to_seconds(candidate.hook_start_time)
        first_seg = candidate.segments[0]
        lead_in = start_sec - first_seg.start_seconds

        if "opening scene at" in lower_hook:
            delay_score -= 5.0
            weaknesses.append("Begins on a scenic establishing shot rather than in-media-res dialogue.")

        if lead_in > 4.0:
            delay_score -= 4.0
            weaknesses.append("Slightly slow buildup before the main conflict begins.")

        delay_score = max(5.0, min(25.0, delay_score))

        # 2. CONFUSION (Max 25)
        confusion_score = 25.0
        # Check clarity of dialogue
        has_clear_subject = any(
            w in lower_hook for w in ["marry", "husband", "wife", "father", "sister", "family", "kill", "love", "mine", "never", "why", "stop"]
        )
        if not has_clear_subject:
            confusion_score -= 4.0
            weaknesses.append("May lack immediate context for first-time viewers unfamiliar with character names.")

        if len(hook_text) < 15:
            confusion_score -= 3.0
            weaknesses.append("Very brief hook text provides limited initial narrative context.")

        confusion_score = max(8.0, min(25.0, confusion_score))

        # 3. IRRELEVANCE (Max 25)
        irrelevance_score = 22.0
        high_stakes_keywords = [
            "marry", "betray", "cheat", "abandon", "shame", "kill", "die", "poison",
            "daughter", "choose", "value", "love", "heart", "swore", "disown"
        ]
        if any(w in lower_hook for w in high_stakes_keywords):
            irrelevance_score = 25.0
        elif any(w in lower_hook for w in ["why", "what", "look", "listen", "enough"]):
            irrelevance_score = 22.0
        else:
            irrelevance_score = 18.0
            weaknesses.append("Emotional stakes could be more explicit in the opening seconds.")

        # 4. DISINTEREST (Max 25)
        disinterest_score = 22.0
        curiosity_triggers = ["why", "not anymore", "changed my mind", "never", "no...", "who", "look", "mistake"]
        if any(w in lower_hook for w in curiosity_triggers):
            disinterest_score = 25.0
        elif "?" in hook_text or "!" in hook_text:
            disinterest_score = 23.5
        else:
            disinterest_score = 19.0
            weaknesses.append("Hook could push stronger curiosity gap or unexpected revelation.")

        total_score = round(delay_score + confusion_score + irrelevance_score + disinterest_score, 1)

        explanation = (
            f"Evaluated via Four Hook Mistakes Framework: "
            f"Delay={delay_score}/25, Confusion={confusion_score}/25, "
            f"Irrelevance={irrelevance_score}/25, Disinterest={disinterest_score}/25. "
            f"Total Hook Score={total_score}/100."
        )

        return HookEvaluation(
            delay_score=delay_score,
            confusion_score=confusion_score,
            irrelevance_score=irrelevance_score,
            disinterest_score=disinterest_score,
            total_hook_score=total_score,
            hook_dialogue=candidate.hook_text,
            hook_start_time=candidate.hook_start_time,
            hook_end_time=candidate.hook_end_time,
            supporting_evidence=candidate.hook_text,
            weaknesses=weaknesses,
            explanation=explanation,
        )
