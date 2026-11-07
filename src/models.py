from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import re

def timestamp_to_seconds(ts: str) -> float:
    """
    Converts timestamp string like '00:15.50' or '01:23' or '(00:15.50)' to seconds float.
    """
    if not ts:
        return 0.0
    clean = ts.strip("() \t\n\r")
    parts = clean.split(":")
    if len(parts) == 2:
        minutes = float(parts[0])
        seconds = float(parts[1])
        return round(minutes * 60.0 + seconds, 2)
    elif len(parts) == 3:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return round(hours * 3600.0 + minutes * 60.0 + seconds, 2)
    else:
        try:
            return round(float(clean), 2)
        except ValueError:
            return 0.0

def seconds_to_timestamp(seconds: float) -> str:
    """
    Converts seconds float to 'MM:SS.SS' format.
    """
    if seconds < 0:
        seconds = 0.0
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:05.2f}"


class DialogueLine(BaseModel):
    speaker: str
    emotion: Optional[str] = None
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    text: str


class ActionItem(BaseModel):
    type: str  # ACTION, CAMERA, SOUND FX
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    description: str


class ScreenplayEntry(BaseModel):
    """
    Unified chronological screenplay item preserving exact wording, timestamps,
    and type (DIALOGUE, CAMERA, ACTION, SOUND_FX, OTHER).
    Includes partial overlap indicators when evaluated against a promo window.
    """
    entry_type: str  # DIALOGUE, ACTION, CAMERA, SOUND_FX, OTHER
    speaker: Optional[str] = None
    emotion: Optional[str] = None
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    content: str
    order_index: int = 0
    is_partial_overlap: bool = False
    overlap_note: Optional[str] = None


class Scene(BaseModel):
    episode_id: int
    scene_id: str
    scene_number: int
    heading: str
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    dialogues: List[DialogueLine] = Field(default_factory=list)
    characters: List[str] = Field(default_factory=list)
    actions: List[ActionItem] = Field(default_factory=list)
    entries: List[ScreenplayEntry] = Field(default_factory=list)
    raw_text: str = ""
    timestamp_status: str = "VALID"  # VALID, MALFORMED, REVIEW_REQUIRED


class Episode(BaseModel):
    episode_id: int
    title: str
    logline: str = ""
    continuity_notes: str = ""
    scenes: List[Scene] = Field(default_factory=list)
    source_filename: str = ""
    total_duration_seconds: float = 0.0


# -------------------------------------------------------------
# Module C: Screenplay Analysis Models
# -------------------------------------------------------------

class HookMoment(BaseModel):
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    quote_or_action: str
    hook_type: str  # e.g., SLAP, SHOCKING_REVELATION, BETRAYAL, CONFRONTATION, ACCUSATION
    curiosity_driver: str


class CliffhangerMoment(BaseModel):
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    quote_or_action: str
    unresolved_question: str
    intensity: int = Field(ge=1, le=10, default=7)


class SceneAnalysis(BaseModel):
    scene_id: str
    episode_id: int
    key_conflict: str
    betrayals: List[str] = Field(default_factory=list)
    secrets_or_revelations: List[str] = Field(default_factory=list)
    threats_or_danger: List[str] = Field(default_factory=list)
    emotional_intensity: int = Field(ge=1, le=10, default=5)
    suspense_level: int = Field(ge=1, le=10, default=5)
    narrative_summary: str = ""
    characters_involved: List[str] = Field(default_factory=list)
    hook_moments: List[HookMoment] = Field(default_factory=list)
    cliffhanger_moments: List[CliffhangerMoment] = Field(default_factory=list)


class EpisodeAnalysis(BaseModel):
    episode_id: int
    summary: str
    key_events: List[str] = Field(default_factory=list)
    scene_analyses: List[SceneAnalysis] = Field(default_factory=list)


# -------------------------------------------------------------
# Module D: Promo Discovery Models
# -------------------------------------------------------------

class PromoSegment(BaseModel):
    episode_id: int
    scene_id: str
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    description: str = ""


class PromoCandidate(BaseModel):
    promo_id: str
    promo_type: str  # SINGLE_EPISODE, MULTI_EPISODE
    episodes: List[int]
    segments: List[PromoSegment]
    total_duration_seconds: float
    hook_text: str
    hook_start_time: str
    hook_end_time: str
    cliffhanger_text: str
    cliffhanger_start_time: str
    cliffhanger_end_time: str
    unresolved_question: str
    rationale: str
    key_conflict: str = ""


# -------------------------------------------------------------
# Module E & F: Hook & Cliffhanger Evaluation Models
# -------------------------------------------------------------

class HookEvaluation(BaseModel):
    delay_score: float = Field(ge=0, le=25)
    confusion_score: float = Field(ge=0, le=25)
    irrelevance_score: float = Field(ge=0, le=25)
    disinterest_score: float = Field(ge=0, le=25)
    total_hook_score: float = Field(ge=0, le=100)
    hook_dialogue: str
    hook_start_time: str
    hook_end_time: str
    supporting_evidence: str
    weaknesses: List[str] = Field(default_factory=list)
    explanation: str


class CliffhangerEvaluation(BaseModel):
    cliffhanger_score: float = Field(ge=0, le=100)
    description: str
    supporting_evidence: str
    source_timestamp: str
    unresolved_question: str
    explanation: str
    weaknesses: List[str] = Field(default_factory=list)


# -------------------------------------------------------------
# Module G: Ranking & Evaluation Models
# -------------------------------------------------------------

class PromoEvaluation(BaseModel):
    promo_id: str
    candidate: PromoCandidate
    hook_eval: HookEvaluation
    cliffhanger_eval: CliffhangerEvaluation
    story_clarity_score: float = Field(ge=0, le=100)
    emotional_impact_score: float = Field(ge=0, le=100)
    scene_continuity_score: float = Field(ge=0, le=100)
    overall_promo_score: float = Field(ge=0, le=100)
    rank: int = 0
    is_top_three: bool = False
    publish_priority_reason: str = ""
    cluster_id: str = ""
    is_cluster_primary: bool = True
    cluster_variant_count: int = 1
    diversity_notes: str = ""
    recommended_publish_rank: Optional[int] = None
    evaluated_by_gemini: bool = False


# -------------------------------------------------------------
# Module H: Quality Checking Models
# -------------------------------------------------------------

class QualityError(BaseModel):
    error_id: str
    promo_id: str
    episode_number: int
    timestamp: str
    error_type: str  # TIMESTAMP_INVALID, DURATION_OUT_OF_BOUNDS, WEAK_HOOK, etc.
    explanation: str
    severity: str  # HIGH, MEDIUM, LOW
    suggested_correction: str
    human_review_status: str = "PENDING"  # PENDING, CONFIRMED, REJECTED


class QualityReport(BaseModel):
    total_promos_checked: int
    rule_violations_count: int
    llm_audit_issues_count: int
    errors: List[QualityError] = Field(default_factory=list)
    disagreements: List[str] = Field(default_factory=list)
