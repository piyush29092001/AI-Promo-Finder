import pytest
import glob
from pathlib import Path

from src.parser import (
    extract_text_from_txt,
    parse_screenplay,
    extract_promo_screenplay_entries,
    get_scene_for_segment,
)
from src.models import (
    PromoCandidate,
    PromoSegment,
    ScreenplayEntry,
    timestamp_to_seconds,
)


def test_top_3_screenplay_content_matches_source_verbatim():
    """
    Verifies that the extracted screenplay content for all Top 3 recommendations
    matches the original source text verbatim with 0 modifications.
    """
    top_3_configs = [
        {
            "promo_id": "PROMO_EP38_SC01_001600_004750_315",
            "episode_id": 38,
            "scene_id": "EP38_SCENE_01",
            "file": "input/episode-038-Episode 1681371.txt",
            "start": "00:16.00",
            "end": "00:47.50",
            "expected_hook": 'Why?',
            "expected_cliff": 'What if I die here?',
        },
        {
            "promo_id": "PROMO_EP01_SC01_011500_013820_232",
            "episode_id": 1,
            "scene_id": "EP01_SCENE_01",
            "file": "input/episode-001-Episode 1671703.txt",
            "start": "01:15.00",
            "end": "01:38.20",
            "expected_hook": 'Long enough to know he was never going to marry you.',
            "expected_cliff": 'Embarrassed you?',
        },
        {
            "promo_id": "PROMO_EP32_SC01_015690_022810_312",
            "episode_id": 32,
            "scene_id": "EP32_SCENE_01",
            "file": "input/episode-032-Episode 1681365.txt",
            "start": "01:56.90",
            "end": "02:28.10",
            "expected_hook": '...but you have never learned how to make anyone love you.',
            "expected_cliff": 'You think you can lecture me?!',
        },
    ]

    for cfg in top_3_configs:
        raw_text = extract_text_from_txt(cfg["file"])
        ep = parse_screenplay(raw_text, source_filename=cfg["file"])
        sc = next(s for s in ep.scenes if s.scene_id == cfg["scene_id"])

        s_sec = timestamp_to_seconds(cfg["start"])
        e_sec = timestamp_to_seconds(cfg["end"])
        entries = extract_promo_screenplay_entries(sc, s_sec, e_sec)

        assert len(entries) > 0, f"No entries extracted for {cfg['promo_id']}"

        # Every entry content must be verbatim inside the original source file
        for entry in entries:
            assert entry.content in raw_text, (
                f"Entry content '{entry.content}' for {cfg['promo_id']} not found in original text!"
            )
            assert entry.start_time in raw_text, (
                f"Timestamp '{entry.start_time}' not in source text!"
            )

        # Check dialogue content specifically includes hook and cliffhanger
        dialogue_texts = [e.content for e in entries if e.entry_type == "DIALOGUE"]
        assert any(cfg["expected_hook"] in d for d in dialogue_texts), (
            f"Expected hook '{cfg['expected_hook']}' missing in extracted entries for {cfg['promo_id']}"
        )
        assert any(cfg["expected_cliff"] in d for d in dialogue_texts), (
            f"Expected cliffhanger '{cfg['expected_cliff']}' missing in extracted entries for {cfg['promo_id']}"
        )


def test_chronological_ordering_preserved():
    """
    Verifies that extracted entries preserve strictly non-decreasing start times
    and retain the original script author's layout order on identical start timestamps.
    """
    raw_text = extract_text_from_txt("input/episode-038-Episode 1681371.txt")
    ep = parse_screenplay(raw_text)
    sc = ep.scenes[0]

    entries = extract_promo_screenplay_entries(sc, 16.0, 47.5)

    for i in range(len(entries) - 1):
        curr = entries[i]
        nxt = entries[i + 1]
        assert curr.start_seconds <= nxt.start_seconds, (
            f"Ordering violation: {curr.start_seconds} > {nxt.start_seconds}"
        )
        if curr.start_seconds == nxt.start_seconds:
            assert curr.order_index < nxt.order_index, (
                f"Source order violation on tie at {curr.start_seconds}s"
            )


def test_partial_overlap_detection():
    """
    Verifies that entries starting before promo start or extending after promo cut
    are accurately identified and flagged with descriptive notes.
    """
    raw_text = extract_text_from_txt("input/episode-038-Episode 1681371.txt")
    ep = parse_screenplay(raw_text)
    sc = ep.scenes[0]

    # Promo cut: 16.0s to 47.5s
    # Ep 38 has a CAMERA shot at 15.50s - 17.50s (starts before 16.0s)
    # and a CAMERA shot at 45.50s - 51.00s (extends past 47.5s)
    entries = extract_promo_screenplay_entries(sc, 16.0, 47.5)

    # First entry should be the partially overlapping camera shot
    first_entry = entries[0]
    assert first_entry.start_seconds == 15.5
    assert first_entry.is_partial_overlap is True
    assert "Starts at 00:15.50 before promo cut" in first_entry.overlap_note

    # Middle entry (e.g. Juliana "Why?" at 16.0 - 17.3) should NOT be partial overlap
    hook_entry = next(e for e in entries if e.speaker == "JULIANA" and e.content == "Why?")
    assert hook_entry.is_partial_overlap is False
    assert hook_entry.overlap_note is None

    # Entry extending past 47.5s (camera at 45.5 - 51.0)
    extending_entry = next(e for e in entries if e.end_seconds == 51.0)
    assert extending_entry.is_partial_overlap is True
    assert "Extends to 00:51.00 after promo cut" in extending_entry.overlap_note


def test_exact_boundary_filtering():
    """
    Verifies that entries completely outside the [promo_start, promo_end] window
    are strictly excluded.
    """
    raw_text = extract_text_from_txt("input/episode-001-Episode 1671703.txt")
    ep = parse_screenplay(raw_text)
    sc = ep.scenes[0]

    # Range: 01:15.00 (75.0s) to 01:38.20 (98.2s)
    entries = extract_promo_screenplay_entries(sc, 75.0, 98.2)

    for e in entries:
        # Must not end before promo starts
        assert e.end_seconds > 75.0, f"Entry {e} ends before promo start"
        # Must not start after promo ends
        assert e.start_seconds < 98.2, f"Entry {e} starts after promo end"

    # Entries from scene start (00:00 - 00:10) must NOT be present
    assert not any(e.start_seconds < 70.0 for e in entries)


def test_screenplay_entry_types_distinguished():
    """
    Verifies that all screenplay entry types (DIALOGUE, CAMERA, ACTION, SOUND_FX)
    are recognized and categorized cleanly.
    """
    raw_text = extract_text_from_txt("input/episode-038-Episode 1681371.txt")
    ep = parse_screenplay(raw_text)
    sc = ep.scenes[0]

    # Look across the whole scene
    all_entries = extract_promo_screenplay_entries(sc, 0.0, 90.0)

    types_found = {e.entry_type for e in all_entries}
    assert "DIALOGUE" in types_found
    assert "CAMERA" in types_found
    assert "ACTION" in types_found
    assert "SOUND_FX" in types_found

    # Check that dialogues have valid speakers and actions have descriptions
    for e in all_entries:
        if e.entry_type == "DIALOGUE":
            assert e.speaker is not None and len(e.speaker) > 0
            assert len(e.content) > 0
        elif e.entry_type in ("CAMERA", "ACTION", "SOUND_FX"):
            assert len(e.content) > 0


def test_missing_screenplay_handling():
    """
    Verifies that attempting to look up non-existent episodes or scenes returns None
    so the system can display a clean warning without fabricating content.
    """
    missing_scene = get_scene_for_segment(999, "EP999_SCENE_99", episodes=[])
    assert missing_scene is None

    # Missing episode on disk
    missing_disk = get_scene_for_segment(888, "EP888_SCENE_01", episodes=None)
    assert missing_disk is None


def test_multi_episode_segment_extraction():
    """
    Verifies that multi-episode promos extract screenplay entries for each segment separately.
    """
    multi_cand = PromoCandidate(
        promo_id="PROMO_MULTI_EP01_EP02_TEST",
        promo_type="MULTI_EPISODE",
        episodes=[1, 2],
        segments=[
            PromoSegment(
                episode_id=1,
                scene_id="EP01_SCENE_01",
                start_time="01:15.00",
                end_time="01:30.00",
                start_seconds=75.0,
                end_seconds=90.0,
                duration_seconds=15.0,
            ),
            PromoSegment(
                episode_id=2,
                scene_id="EP02_SCENE_01",
                start_time="00:10.00",
                end_time="00:25.00",
                start_seconds=10.0,
                end_seconds=25.0,
                duration_seconds=15.0,
            ),
        ],
        total_duration_seconds=30.0,
        hook_text="Test Hook",
        hook_start_time="01:15.00",
        hook_end_time="01:19.00",
        cliffhanger_text="Test Cliffhanger",
        cliffhanger_start_time="00:20.00",
        cliffhanger_end_time="00:25.00",
        unresolved_question="Test Question?",
        rationale="Multi-episode test",
        key_conflict="Conflict test",
    )

    for seg in multi_cand.segments:
        sc = get_scene_for_segment(seg.episode_id, seg.scene_id)
        assert sc is not None, f"Could not find scene for Ep {seg.episode_id} {seg.scene_id}"
        entries = extract_promo_screenplay_entries(sc, seg.start_seconds, seg.end_seconds)
        assert len(entries) > 0, f"No entries for Ep {seg.episode_id}"
        for e in entries:
            assert e.end_seconds > seg.start_seconds
            assert e.start_seconds < seg.end_seconds

