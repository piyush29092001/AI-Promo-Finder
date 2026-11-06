import json
import logging
from typing import Optional, List

from src.config import get_api_key, get_model_name
from src.models import PromoCandidate, CliffhangerEvaluation

logger = logging.getLogger(__name__)


class CliffhangerEvaluator:
    """
    Evaluates promo cliffhangers on unresolved questions, emotional escalation,
    and narrative suspense (score out of 100).
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
                logger.warning(f"Could not initialize Gemini Client for CliffhangerEvaluator: {e}")

    def evaluate_cliffhanger(self, candidate: PromoCandidate) -> CliffhangerEvaluation:
        """
        Evaluates the cliffhanger of a PromoCandidate. Uses Gemini if available,
        otherwise uses deterministic rubric analysis.
        """
        if self.client and self.api_key:
            try:
                return self._call_gemini_cliffhanger_eval(candidate)
            except Exception as e:
                logger.error(f"Gemini cliffhanger evaluation failed: {e}. Using rubric fallback.")
                return self._heuristic_cliffhanger_eval(candidate)
        else:
            return self._heuristic_cliffhanger_eval(candidate)

    def _call_gemini_cliffhanger_eval(self, candidate: PromoCandidate) -> CliffhangerEvaluation:
        from google.genai import types

        prompt = f"""
You are an expert promotional video evaluator for microdramas.
Evaluate the ending cliffhanger of this candidate promo.
Note: A shocking event is NOT automatically a cliffhanger unless it leaves an important UNRESOLVED QUESTION that compels the viewer to watch the full episode.

PROMO CANDIDATE:
- Promo ID: {candidate.promo_id}
- Episodes: {candidate.episodes}
- Ending / Cliffhanger Text: {candidate.cliffhanger_text}
- Cliffhanger Timestamp: {candidate.cliffhanger_start_time} - {candidate.cliffhanger_end_time}
- Total Duration: {candidate.total_duration_seconds}s
- Current Unresolved Question: {candidate.unresolved_question}

Return valid JSON with:
{{
  "cliffhanger_score": 88.0, // Float 0-100
  "description": "{candidate.cliffhanger_text}",
  "supporting_evidence": "Exact dialogue or action line",
  "source_timestamp": "{candidate.cliffhanger_end_time}",
  "unresolved_question": "Precise unanswered question for the viewer",
  "explanation": "Why this cliffhanger succeeds or falls short",
  "weaknesses": ["Any weakness found"]
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
        return CliffhangerEvaluation.model_validate(data)

    def _heuristic_cliffhanger_eval(self, candidate: PromoCandidate) -> CliffhangerEvaluation:
        """
        Deterministic evaluation of cliffhanger strength.
        """
        cliff_text = candidate.cliffhanger_text
        lower_cliff = cliff_text.lower()
        weaknesses: List[str] = []

        base_score = 70.0

        # Factor 1: Unresolved Question Clarity (up to +15)
        if "?" in cliff_text or "unresolved" in candidate.unresolved_question.lower():
            base_score += 10.0
        if len(candidate.unresolved_question) > 20:
            base_score += 5.0

        # Factor 2: High Dramatic Stakes keywords (up to +15)
        high_drama_cues = [
            "never", "changed my mind", "marry", "choose", "daughter",
            "poison", "kill", "die", "betray", "shame", "fury",
            "blood", "weapon", "knuckles", "cut to black", "string drone"
        ]
        matched_cues = [w for w in high_drama_cues if w in lower_cliff]
        if matched_cues:
            base_score += min(15.0, len(matched_cues) * 5.0)

        # Factor 3: Penalty for resolved or scenic endings
        if "dramatic scene transition" in lower_cliff:
            base_score -= 8.0
            weaknesses.append("Ends on a scene transition rather than a stinging dialogue cut.")

        if len(cliff_text) < 15:
            base_score -= 5.0
            weaknesses.append("Ending dialogue/action line is very brief.")

        cliffhanger_score = max(20.0, min(100.0, round(base_score, 1)))

        explanation = (
            f"Cliffhanger delivers score {cliffhanger_score}/100. "
            f"Leaves unresolved question: '{candidate.unresolved_question}'. "
            f"Supported by ending element: '{cliff_text[:60]}'."
        )

        return CliffhangerEvaluation(
            cliffhanger_score=cliffhanger_score,
            description=cliff_text,
            supporting_evidence=cliff_text,
            source_timestamp=candidate.cliffhanger_end_time,
            unresolved_question=candidate.unresolved_question,
            explanation=explanation,
            weaknesses=weaknesses,
        )
