import json
import logging
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.config import (
    ANALYZED_DIR,
    RAW_OUTPUTS_DIR,
    BATCH_SIZE,
    MAX_RETRIES,
    RETRY_DELAY,
    get_api_key,
    get_model_name,
)
from src.models import (
    Scene,
    Episode,
    SceneAnalysis,
    EpisodeAnalysis,
    HookMoment,
    CliffhangerMoment,
    seconds_to_timestamp,
)

logger = logging.getLogger(__name__)


class ScreenplayAnalyzer:
    """
    Analyzes microdrama screenplay scenes in batches using Google Gemini or high-fidelity rule-based heuristic fallback.
    Saves intermediate results and supports resumable processing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        batch_size: int = BATCH_SIZE,
        cache_dir: Path = ANALYZED_DIR,
    ):
        self.api_key = api_key or get_api_key()
        self.model_name = model_name or get_model_name()
        self.batch_size = batch_size
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self._circuit_broken = False

        if self.api_key:
            try:
                from google import genai

                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client: {e}")
                self._circuit_broken = True

    def analyze_episode(
        self, episode: Episode, force_refresh: bool = False
    ) -> EpisodeAnalysis:
        """
        Analyzes all scenes in an episode, with caching and resumability.
        """
        cache_file = self.cache_dir / f"episode_{episode.episode_id:03d}.json"
        if not force_refresh and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return EpisodeAnalysis.model_validate(data)
            except Exception as e:
                logger.warning(
                    f"Failed to read cache {cache_file}, re-analyzing: {e}"
                )

        scene_analyses: List[SceneAnalysis] = []

        # Process scenes in batches
        for i in range(0, len(episode.scenes), self.batch_size):
            batch = episode.scenes[i : i + self.batch_size]
            batch_results = self.analyze_scenes_batch(batch)
            scene_analyses.extend(batch_results)

        # Generate episode summary
        summary = self._generate_episode_summary(episode, scene_analyses)

        key_events = []
        for sa in scene_analyses:
            if sa.key_conflict:
                key_events.append(sa.key_conflict)

        ep_analysis = EpisodeAnalysis(
            episode_id=episode.episode_id,
            summary=summary,
            key_events=key_events,
            scene_analyses=scene_analyses,
        )

        # Save to cache
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(ep_analysis.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to write cache {cache_file}: {e}")

        return ep_analysis

    def analyze_scenes_batch(self, scenes: List[Scene]) -> List[SceneAnalysis]:
        """
        Processes a batch of scenes using Gemini API if key is present,
        otherwise uses heuristic analysis.
        """
        if not scenes:
            return []

        if self.client and self.api_key and not self._circuit_broken:
            try:
                return self._call_gemini_batch(scenes)
            except Exception as e:
                err_msg = str(e)
                if any(code in err_msg for code in ["404", "401", "403", "NOT_FOUND", "API_KEY_INVALID", "getaddrinfo", "ConnectError"]):
                    logger.warning(
                        f"Non-recoverable or network error calling Gemini API: {e}. Tripping circuit breaker."
                    )
                    self._circuit_broken = True
                else:
                    logger.error(
                        f"Gemini API call failed for batch: {e}. Falling back to heuristic analysis."
                    )
                return [self._heuristic_analyze_scene(s) for s in scenes]
        else:
            return [self._heuristic_analyze_scene(s) for s in scenes]

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_DELAY, min=2, max=10),
        reraise=True,
    )
    def _call_gemini_batch(self, scenes: List[Scene]) -> List[SceneAnalysis]:
        """
        Executes structured JSON generation with Gemini.
        """
        from google.genai import types

        prompt = self._build_batch_prompt(scenes)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        raw_text = response.text or "{}"

        # Save raw output for inspection and compliance
        raw_output_file = (
            RAW_OUTPUTS_DIR / f"gemini_batch_ep{scenes[0].episode_id}_{len(scenes)}scenes.json"
        )
        try:
            with open(raw_output_file, "w", encoding="utf-8") as f:
                f.write(raw_text)
        except Exception:
            pass

        parsed = json.loads(raw_text)
        if isinstance(parsed, dict) and "scenes" in parsed:
            parsed = parsed["scenes"]

        analyses = []
        for item in parsed:
            analyses.append(SceneAnalysis.model_validate(item))

        # Ensure all requested scenes are present
        found_ids = {a.scene_id for a in analyses}
        for s in scenes:
            if s.scene_id not in found_ids:
                analyses.append(self._heuristic_analyze_scene(s))

        return analyses

    def _build_batch_prompt(self, scenes: List[Scene]) -> str:
        scenes_data = []
        for s in scenes:
            scenes_data.append(
                {
                    "scene_id": s.scene_id,
                    "episode_id": s.episode_id,
                    "heading": s.heading,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "characters": s.characters,
                    "dialogues": [
                        {
                            "speaker": d.speaker,
                            "emotion": d.emotion,
                            "time": f"{d.start_time} - {d.end_time}",
                            "text": d.text,
                        }
                        for d in s.dialogues
                    ],
                    "actions": [
                        {
                            "type": a.type,
                            "time": f"{a.start_time} - {a.end_time}",
                            "desc": a.description,
                        }
                        for a in s.actions
                    ],
                }
            )

        schema_desc = """
Return a JSON array of objects, one for each scene, matching this exact schema:
[
  {
    "scene_id": "EP01_SCENE_01",
    "episode_id": 1,
    "key_conflict": "Brief description of the primary dramatic conflict",
    "betrayals": ["Identified betrayal event if any"],
    "secrets_or_revelations": ["Identified secret or sudden revelation"],
    "threats_or_danger": ["Identified threat or physical/social danger"],
    "emotional_intensity": 8, // Integer 1-10
    "suspense_level": 9, // Integer 1-10
    "narrative_summary": "Summary of the scene",
    "characters_involved": ["Juliana", "Gerald"],
    "hook_moments": [
      {
        "start_time": "00:11.30",
        "end_time": "00:14.30",
        "start_seconds": 11.3,
        "end_seconds": 14.3,
        "quote_or_action": "You should turn around, Juliana.",
        "hook_type": "CONFRONTATION",
        "curiosity_driver": "Why is the matriarch barring her from her own wedding?"
      }
    ],
    "cliffhanger_moments": [
      {
        "start_time": "02:11.30",
        "end_time": "02:17.00",
        "start_seconds": 131.3,
        "end_seconds": 137.0,
        "quote_or_action": "Juliana knuckles whitening with suppressed fury as strings swell.",
        "unresolved_question": "Will Juliana strike back against Gerald and Clarissa?",
        "intensity": 9
      }
    ]
  }
]
"""
        return (
            "You are an expert microdrama screenplay analyst specializing in promotional video hook and cliffhanger discovery.\n"
            "Analyze the following scenes accurately without inventing quotes or timestamps:\n\n"
            f"INPUT SCENES:\n{json.dumps(scenes_data, indent=2)}\n\n"
            f"OUTPUT FORMAT:\n{schema_desc}\n"
            "Only return valid JSON."
        )

    def _heuristic_analyze_scene(self, scene: Scene) -> SceneAnalysis:
        """
        High-precision deterministic analysis that extracts dramatic features,
        emotional peaks, hook moments, and cliffhanger moments from actual scene text.
        """
        dialogues = scene.dialogues
        actions = scene.actions

        betrayals: List[str] = []
        secrets: List[str] = []
        threats: List[str] = []
        hook_moments: List[HookMoment] = []
        cliffhanger_moments: List[CliffhangerMoment] = []

        betrayal_keywords = [
            "betray", "abandon", "cheat", "replaced", "changed my mind",
            "not marry", "fool", "disown", "scandal", "lie", "conspiracy",
            "poison", "illicit", "sham"
        ]
        threat_keywords = [
            "kill", "die", "poison", "strangle", "threat", "destroy",
            "ruin", "arrest", "guard", "knife", "sword", "weapon", "blood"
        ]
        secret_keywords = [
            "secret", "knew", "truth", "discover", "uncover", "confess",
            "witness", "father", "heir", "will", "arsenic", "antidote"
        ]

        # Scan dialogues
        for d in dialogues:
            lower_text = d.text.lower()
            lower_emotion = (d.emotion or "").lower()

            for kw in betrayal_keywords:
                if kw in lower_text or kw in lower_emotion:
                    betrayals.append(f"{d.speaker}: '{d.text}'")
                    break

            for kw in threat_keywords:
                if kw in lower_text or kw in lower_emotion:
                    threats.append(f"{d.speaker}: '{d.text}'")
                    break

            for kw in secret_keywords:
                if kw in lower_text:
                    secrets.append(f"{d.speaker}: '{d.text}'")
                    break

        # Discover Hook Moments (early high-impact dialogues or actions)
        # Look at the first 35 seconds of the scene
        early_dialogues = [d for d in dialogues if d.start_seconds - scene.start_seconds <= 35.0]
        if early_dialogues:
            for d in early_dialogues[:2]:
                hook_type = "CONFRONTATION"
                if any(w in d.text.lower() for w in ["why", "what", "how", "who"]):
                    hook_type = "MYSTERY_QUESTION"
                elif any(w in d.text.lower() for w in ["marry", "never", "changed", "stop", "leave"]):
                    hook_type = "SHOCKING_REVELATION"

                hook_moments.append(
                    HookMoment(
                        start_time=d.start_time,
                        end_time=d.end_time,
                        start_seconds=d.start_seconds,
                        end_seconds=d.end_seconds,
                        quote_or_action=f"{d.speaker}: \"{d.text}\"",
                        hook_type=hook_type,
                        curiosity_driver=f"Viewer immediately questions: {d.text}",
                    )
                )
        elif actions:
            first_act = actions[0]
            hook_moments.append(
                HookMoment(
                    start_time=first_act.start_time,
                    end_time=first_act.end_time,
                    start_seconds=first_act.start_seconds,
                    end_seconds=first_act.end_seconds,
                    quote_or_action=first_act.description,
                    hook_type="VISUAL_ACTION",
                    curiosity_driver="High visual tension establishes immediate dramatic stakes.",
                )
            )

        # Discover Cliffhanger Moments (late high-impact dialogues or actions)
        # Look at the last 30 seconds of the scene
        late_dialogues = [d for d in dialogues if scene.end_seconds - d.end_seconds <= 30.0]
        late_actions = [a for a in actions if scene.end_seconds - a.end_seconds <= 20.0]

        if late_dialogues:
            last_d = late_dialogues[-1]
            cliffhanger_moments.append(
                CliffhangerMoment(
                    start_time=last_d.start_time,
                    end_time=last_d.end_time,
                    start_seconds=last_d.start_seconds,
                    end_seconds=last_d.end_seconds,
                    quote_or_action=f"{last_d.speaker}: \"{last_d.text}\"",
                    unresolved_question=f"What will happen after {last_d.speaker} says: '{last_d.text}'?",
                    intensity=8 if (betrayals or threats) else 6,
                )
            )
        elif late_actions:
            last_act = late_actions[-1]
            cliffhanger_moments.append(
                CliffhangerMoment(
                    start_time=last_act.start_time,
                    end_time=last_act.end_time,
                    start_seconds=last_act.start_seconds,
                    end_seconds=last_act.end_seconds,
                    quote_or_action=last_act.description,
                    unresolved_question="How will the character respond to this critical turning point?",
                    intensity=7,
                )
            )
        else:
            cliffhanger_moments.append(
                CliffhangerMoment(
                    start_time=seconds_to_timestamp(max(0.0, scene.end_seconds - 5.0)),
                    end_time=scene.end_time,
                    start_seconds=max(0.0, scene.end_seconds - 5.0),
                    end_seconds=scene.end_seconds,
                    quote_or_action="Dramatic scene cut",
                    unresolved_question="What consequences follow this confrontation?",
                    intensity=6,
                )
            )

        # Score emotional intensity and suspense
        conflict_intensity = 5
        if betrayals:
            conflict_intensity += 3
        if threats:
            conflict_intensity += 2
        emotional_intensity = min(10, max(3, conflict_intensity))

        suspense_level = 5
        if secrets:
            suspense_level += 2
        if threats:
            suspense_level += 2
        suspense_level = min(10, max(3, suspense_level))

        # Key conflict
        key_conflict = "Dramatic confrontation"
        if betrayals:
            key_conflict = f"Betrayal conflict: {betrayals[0][:80]}"
        elif threats:
            key_conflict = f"Threat conflict: {threats[0][:80]}"
        elif dialogues:
            key_conflict = f"Confrontation between {dialogues[0].speaker} and others: {dialogues[0].text[:80]}"

        return SceneAnalysis(
            scene_id=scene.scene_id,
            episode_id=scene.episode_id,
            key_conflict=key_conflict,
            betrayals=betrayals[:3],
            secrets_or_revelations=secrets[:3],
            threats_or_danger=threats[:3],
            emotional_intensity=emotional_intensity,
            suspense_level=suspense_level,
            narrative_summary=f"Scene {scene.scene_id} at {scene.heading} involving {', '.join(scene.characters)}.",
            characters_involved=scene.characters,
            hook_moments=hook_moments,
            cliffhanger_moments=cliffhanger_moments,
        )

    def _generate_episode_summary(
        self, episode: Episode, scene_analyses: List[SceneAnalysis]
    ) -> str:
        """
        Generates a concise episode-level narrative summary.
        """
        if episode.logline:
            return episode.logline
        key_points = [sa.key_conflict for sa in scene_analyses if sa.key_conflict]
        return f"Episode {episode.episode_id} centers on {'; '.join(key_points[:3])}."

