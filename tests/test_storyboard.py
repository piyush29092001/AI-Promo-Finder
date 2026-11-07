import os
from pathlib import Path
import pytest
from src.storyboard_generator import (
    TOP_PROMO_STORYBOARD_METADATA,
    get_storyboard_for_promo,
    STORYBOARDS_DIR,
)


def test_top_3_storyboards_exist():
    """
    Verifies that all Top 3 recommendations have storyboard metadata and image files.
    """
    assert len(TOP_PROMO_STORYBOARD_METADATA) == 3

    top_ids = [
        "PROMO_EP38_SC01_001600_004750_315",
        "PROMO_EP01_SC01_011500_013820_232",
        "PROMO_EP32_SC01_015690_022810_312",
    ]

    for rank, pid in enumerate(top_ids, 1):
        sb = get_storyboard_for_promo(pid, recommended_rank=rank)
        assert sb is not None
        assert sb["resolved_image_path"] is not None
        assert Path(sb["resolved_image_path"]).exists()
        assert Path(sb["resolved_image_path"]).stat().st_size > 50000  # Non-trivial image file


def test_storyboard_panel_sequence_and_cliffhanger():
    """
    Verifies that each storyboard has 6 sequential panels,
    with panel 1 as hook and panel 6 as cliffhanger.
    """
    for pid, meta in TOP_PROMO_STORYBOARD_METADATA.items():
        shots = meta["shots"]
        assert len(shots) == 6

        # Check chronological shot numbering 1 to 6
        for i, s in enumerate(shots, 1):
            assert s["shot_number"] == i
            assert s["timestamp"] != ""
            assert s["shot_type"] != ""
            assert s["dialogue_action"] != ""
            assert s["camera_source"] in [
                "Screenplay Source Instruction",
                "Creative Visualization",
            ]

        # First shot must represent Opening Hook
        assert "Hook" in shots[0]["notes"] or "hook" in shots[0]["notes"].lower()

        # Final shot must represent Closing Cliffhanger
        assert "Cliffhanger" in shots[-1]["notes"] or "cliffhanger" in shots[-1]["notes"].lower()


def test_storyboard_dialogue_accuracy():
    """
    Verifies that dialogue lines in the storyboards match verbatim quotes.
    """
    sb1 = TOP_PROMO_STORYBOARD_METADATA["PROMO_EP38_SC01_001600_004750_315"]
    assert 'JULIANA: "Why?"' in sb1["shots"][0]["dialogue_action"]
    assert 'JULIANA: "What if I die here?"' in sb1["shots"][5]["dialogue_action"]

    sb2 = TOP_PROMO_STORYBOARD_METADATA["PROMO_EP01_SC01_011500_013820_232"]
    assert 'LADY IN GOLD GOWN: "Long enough to know he was never going to marry you."' in sb2["shots"][0]["dialogue_action"]
    assert 'LADY JULIANA: "Embarrassed you?"' in sb2["shots"][5]["dialogue_action"]

    sb3 = TOP_PROMO_STORYBOARD_METADATA["PROMO_EP32_SC01_015690_022810_312"]
    assert 'JULIANA: "...but you have never learned how to make anyone love you."' in sb3["shots"][0]["dialogue_action"]
    assert 'CATHERINE: "You think you can lecture me?!"' in sb3["shots"][5]["dialogue_action"]

