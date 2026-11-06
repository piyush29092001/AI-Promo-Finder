import os
import re
from typing import List, Optional, Tuple, Union
import pymupdf

from src.models import (
    DialogueLine,
    ActionItem,
    Scene,
    Episode,
    timestamp_to_seconds,
    seconds_to_timestamp,
)


def extract_text_from_pdf(pdf_source: Union[str, bytes]) -> str:
    """
    Extracts plain text from a PDF file path or raw bytes using PyMuPDF.
    """
    if isinstance(pdf_source, str):
        doc = pymupdf.open(pdf_source)
    else:
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")

    text_pages = []
    for page in doc:
        text_pages.append(page.get_text())
    doc.close()
    return "\n".join(text_pages)


def extract_text_from_txt(txt_source: Union[str, bytes]) -> str:
    """
    Extracts text from a TXT file path or raw bytes with utf-8 fallback handling.
    """
    if isinstance(txt_source, str):
        try:
            with open(txt_source, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(txt_source, "r", encoding="latin-1", errors="ignore") as f:
                return f.read()
    else:
        try:
            return txt_source.decode("utf-8")
        except UnicodeDecodeError:
            return txt_source.decode("latin-1", errors="ignore")


def detect_episode_id(content: str, filename: str = "") -> int:
    """
    Detects episode integer ID from text content or fallback filename.
    """
    # 1. Look for EPISODE NUMBER in content
    ep_match = re.search(r"EPISODE\s+NUMBER:\s*(?:Episode\s*)?(\d+)", content, re.IGNORECASE)
    if ep_match:
        return int(ep_match.group(1))

    # 2. Look in filename (e.g., episode-001-... or ep05)
    fn_match = re.search(r"(?:episode|ep)[-_]?\s*0*(\d+)", filename, re.IGNORECASE)
    if fn_match:
        return int(fn_match.group(1))

    # Fallback default
    return 1


def parse_screenplay(
    text: str, source_filename: str = "", episode_id: Optional[int] = None
) -> Episode:
    """
    Parses a single screenplay's text into a structured Episode model with validated Scenes.
    """
    if episode_id is None:
        episode_id = detect_episode_id(text, source_filename)

    # Extract logline
    logline_match = re.search(
        r"EPISODE\s+LOGLINE:\s*(.*?)(?=\n\s*(?:CONTINUITY|SCENE|---|\Z))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    logline = logline_match.group(1).strip() if logline_match else ""

    # Extract continuity notes
    continuity_match = re.search(
        r"CONTINUITY\s+NOTES:\s*(.*?)(?=\n\s*(?:SCENE|---|--- SCRIPT START|\Z))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    continuity_notes = (
        continuity_match.group(1).strip() if continuity_match else ""
    )

    # Find script content boundary
    script_content = text
    if "--- SCRIPT START ---" in text:
        script_content = text.split("--- SCRIPT START ---", 1)[1]
    if "--- SCRIPT END ---" in script_content:
        script_content = script_content.split("--- SCRIPT END ---", 1)[0]

    # Split into scenes
    scene_splits = re.split(r"\n(?=SCENE\s+\d+)", script_content, flags=re.IGNORECASE)
    scenes: List[Scene] = []

    for raw_scene_block in scene_splits:
        scene_block = raw_scene_block.strip()
        if not scene_block or not re.search(r"SCENE\s+\d+", scene_block, re.IGNORECASE):
            continue

        # Extract scene number
        sc_num_match = re.search(r"SCENE\s+(\d+)", scene_block, re.IGNORECASE)
        scene_num = int(sc_num_match.group(1)) if sc_num_match else len(scenes) + 1

        # Scene heading
        heading_match = re.search(
            r"Scene\s+heading:\s*(.*)", scene_block, re.IGNORECASE
        )
        heading = heading_match.group(1).strip() if heading_match else "UNKNOWN HEADING"

        # Scene start & end
        start_match = re.search(
            r"Scene\s+start:\s*([0-9:.]+)", scene_block, re.IGNORECASE
        )
        end_match = re.search(
            r"Scene\s+end:\s*([0-9:.]+)", scene_block, re.IGNORECASE
        )

        start_time_str = start_match.group(1).strip() if start_match else ""
        end_time_str = end_match.group(1).strip() if end_match else ""

        # Parse internal blocks (dialogues, actions, camera, sound fx)
        dialogues, actions, characters, block_start_secs, block_end_secs = _parse_scene_blocks(
            scene_block
        )

        # Handle missing or malformed scene timestamps
        timestamp_status = "VALID"
        if not start_time_str or not end_time_str:
            timestamp_status = "REVIEW_REQUIRED"
            if block_start_secs is not None:
                start_time_str = seconds_to_timestamp(block_start_secs)
            else:
                start_time_str = "00:00.00"

            if block_end_secs is not None:
                end_time_str = seconds_to_timestamp(block_end_secs)
            else:
                end_time_str = start_time_str

        start_secs = timestamp_to_seconds(start_time_str)
        end_secs = timestamp_to_seconds(end_time_str)

        if end_secs < start_secs:
            timestamp_status = "MALFORMED"

        duration = max(0.0, round(end_secs - start_secs, 2))
        scene_id = f"EP{episode_id:02d}_SCENE_{scene_num:02d}"

        scenes.append(
            Scene(
                episode_id=episode_id,
                scene_id=scene_id,
                scene_number=scene_num,
                heading=heading,
                start_time=start_time_str,
                end_time=end_time_str,
                start_seconds=start_secs,
                end_seconds=end_secs,
                duration_seconds=duration,
                dialogues=dialogues,
                characters=sorted(list(characters)),
                actions=actions,
                raw_text=scene_block,
                timestamp_status=timestamp_status,
            )
        )

    # Sort scenes by scene_number
    scenes.sort(key=lambda s: s.scene_number)

    total_duration = sum(s.duration_seconds for s in scenes)
    if scenes and scenes[-1].end_seconds > total_duration:
        total_duration = scenes[-1].end_seconds

    return Episode(
        episode_id=episode_id,
        title=f"Episode {episode_id}",
        logline=logline,
        continuity_notes=continuity_notes,
        scenes=scenes,
        source_filename=source_filename,
        total_duration_seconds=round(total_duration, 2),
    )


def _parse_scene_blocks(
    scene_text: str,
) -> Tuple[
    List[DialogueLine],
    List[ActionItem],
    set,
    Optional[float],
    Optional[float],
]:
    """
    Parses dialogues and action blocks within a scene text.
    Returns (dialogues, actions, character_names, earliest_start_sec, latest_end_sec).
    """
    dialogues: List[DialogueLine] = []
    actions: List[ActionItem] = []
    characters = set()

    # Regex matches: **TAG:** or **TAG**:
    block_header_regex = re.compile(r"\*\*([^*]+?)(?::\*\*|\*\*:)")
    time_regex = re.compile(
        r"Start:\s*\(?([0-9:.]+)\)?\s*\|\s*End:\s*\(?([0-9:.]+)\)?"
    )

    earliest_sec: Optional[float] = None
    latest_sec: Optional[float] = None

    matches = list(block_header_regex.finditer(scene_text))
    for i, match in enumerate(matches):
        raw_tag = match.group(1).strip()
        block_start_idx = match.end()
        block_end_idx = (
            matches[i + 1].start() if i + 1 < len(matches) else len(scene_text)
        )
        block_body = scene_text[block_start_idx:block_end_idx].strip()

        # Find timestamps
        time_m = time_regex.search(block_body)
        if not time_m:
            continue

        start_time_str = time_m.group(1)
        end_time_str = time_m.group(2)
        s_secs = timestamp_to_seconds(start_time_str)
        e_secs = timestamp_to_seconds(end_time_str)

        if earliest_sec is None or s_secs < earliest_sec:
            earliest_sec = s_secs
        if latest_sec is None or e_secs > latest_sec:
            latest_sec = e_secs

        # Text after the timestamp line
        content_after_time = block_body[time_m.end() :].strip()

        # Clean tag and emotion
        # e.g., 'MATRIARCH (Cold, Commanding)' or 'SOUND FX'
        emotion: Optional[str] = None
        tag_name = raw_tag
        if "(" in raw_tag and ")" in raw_tag:
            tag_name = raw_tag.split("(", 1)[0].strip()
            emotion = raw_tag.split("(", 1)[1].rstrip(")").strip()

        clean_tag_upper = tag_name.upper().strip()

        if clean_tag_upper in ("ACTION", "CAMERA", "SOUND FX"):
            actions.append(
                ActionItem(
                    type=clean_tag_upper,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    start_seconds=s_secs,
                    end_seconds=e_secs,
                    description=content_after_time,
                )
            )
        else:
            # Character dialogue
            clean_text = content_after_time.strip('"').strip()
            # If text had quotes inside or multiple lines
            if clean_text:
                characters.add(tag_name)
                dialogues.append(
                    DialogueLine(
                        speaker=tag_name,
                        emotion=emotion,
                        start_time=start_time_str,
                        end_time=end_time_str,
                        start_seconds=s_secs,
                        end_seconds=e_secs,
                        text=clean_text,
                    )
                )

    return dialogues, actions, characters, earliest_sec, latest_sec
