import pytest
import os
import pymupdf
from src.models import timestamp_to_seconds, seconds_to_timestamp, Episode, Scene
from src.parser import (
    extract_text_from_txt,
    extract_text_from_pdf,
    parse_screenplay,
    detect_episode_id,
)

def test_timestamp_conversions():
    assert timestamp_to_seconds("00:00.00") == 0.0
    assert timestamp_to_seconds("01:30.00") == 90.0
    assert timestamp_to_seconds("02:18.50") == 138.5
    assert timestamp_to_seconds("(00:15.50)") == 15.5
    assert timestamp_to_seconds("01:02:03") == 3723.0
    assert timestamp_to_seconds("") == 0.0

    assert seconds_to_timestamp(0.0) == "00:00.00"
    assert seconds_to_timestamp(90.0) == "01:30.00"
    assert seconds_to_timestamp(138.5) == "02:18.50"


def test_detect_episode_id():
    content = "EPISODE NUMBER: Episode 5\nEPISODE LOGLINE: ..."
    assert detect_episode_id(content, "random_name.txt") == 5

    assert detect_episode_id("No episode line", "episode-012-Episode.txt") == 12
    assert detect_episode_id("No episode line", "ep42.txt") == 42


def test_parse_episode_001():
    path = os.path.join("input", "episode-001-Episode 1671703.txt")
    if not os.path.exists(path):
        pytest.skip("Episode 1 file not found")

    text = extract_text_from_txt(path)
    ep = parse_screenplay(text, source_filename=path)

    assert ep.episode_id == 1
    assert "Juliana" in ep.logline
    assert len(ep.scenes) == 1
    sc = ep.scenes[0]
    assert sc.scene_id == "EP01_SCENE_01"
    assert sc.heading == "INT. CATHEDRAL – DAY"
    assert sc.start_time == "00:00.00"
    assert sc.end_time == "02:18.00"
    assert sc.duration_seconds == 138.0
    assert len(sc.dialogues) > 0
    assert len(sc.actions) > 0
    assert "LADY JULIANA" in sc.characters
    assert sc.timestamp_status == "VALID"


def test_parse_episode_003_multiscene():
    path = os.path.join("input", "episode-003-Episode 1671705.txt")
    if not os.path.exists(path):
        pytest.skip("Episode 3 file not found")

    text = extract_text_from_txt(path)
    ep = parse_screenplay(text, source_filename=path)

    assert ep.episode_id == 3
    assert len(ep.scenes) == 3
    assert ep.scenes[0].scene_id == "EP03_SCENE_01"
    assert ep.scenes[1].scene_id == "EP03_SCENE_02"
    assert ep.scenes[2].scene_id == "EP03_SCENE_03"


def test_parse_episode_006_case_insensitivity():
    path = os.path.join("input", "episode-006-Episode 1671708.txt")
    if not os.path.exists(path):
        pytest.skip("Episode 6 file not found")

    text = extract_text_from_txt(path)
    ep = parse_screenplay(text, source_filename=path)

    assert ep.episode_id == 6
    assert len(ep.scenes) == 2
    assert ep.scenes[0].timestamp_status == "VALID"
    assert ep.scenes[0].heading == "EXT. WOODLAND PATH – NIGHT"


def test_pdf_extraction_roundtrip(tmp_path):
    sample_text = (
        "EPISODE NUMBER: Episode 99\n"
        "EPISODE LOGLINE: A dramatic test logline.\n"
        "--- SCRIPT START ---\n\n"
        "SCENE 01\n"
        "Scene heading: INT. ROOM - NIGHT\n"
        "Scene start: 00:00.00\n"
        "Scene end: 00:30.00\n\n"
        "**ALICE:**\n"
        "Start: (00:05.00) | End: (00:10.00)\n"
        "\"This is a PDF test!\"\n"
        "--- SCRIPT END ---"
    )

    pdf_path = str(tmp_path / "test_ep.pdf")
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), sample_text)
    doc.save(pdf_path)
    doc.close()

    extracted = extract_text_from_pdf(pdf_path)
    assert "EPISODE NUMBER: Episode 99" in extracted
    assert "This is a PDF test!" in extracted

    ep = parse_screenplay(extracted, source_filename=pdf_path)
    assert ep.episode_id == 99
    assert len(ep.scenes) == 1
    assert ep.scenes[0].heading == "INT. ROOM - NIGHT"
    assert ep.scenes[0].dialogues[0].speaker == "ALICE"
    assert ep.scenes[0].dialogues[0].text == "This is a PDF test!"


def test_malformed_timestamp_flagging():
    malformed_text = (
        "EPISODE NUMBER: Episode 100\n"
        "--- SCRIPT START ---\n"
        "SCENE 01\n"
        "Scene heading: INT. MYSTERY ROOM\n"
        "Scene start: 01:00.00\n"
        "Scene end: 00:30.00\n"  # end before start!
        "--- SCRIPT END ---"
    )
    ep = parse_screenplay(malformed_text, "test.txt")
    assert ep.scenes[0].timestamp_status == "MALFORMED"


def test_parse_all_50_episodes():
    import glob
    files = sorted(glob.glob("input/*.txt"))
    assert len(files) == 50, f"Expected 50 files, got {len(files)}"

    total_scenes = 0
    total_dialogues = 0
    episodes = []

    for f in files:
        txt = extract_text_from_txt(f)
        ep = parse_screenplay(txt, source_filename=f)
        assert ep.episode_id >= 1 and ep.episode_id <= 50
        assert len(ep.scenes) >= 1
        for sc in ep.scenes:
            assert sc.timestamp_status == "VALID"
            assert sc.duration_seconds > 0
            assert len(sc.heading) > 0
            total_scenes += 1
            total_dialogues += len(sc.dialogues)
        episodes.append(ep)

    assert len(episodes) == 50
    assert total_scenes == 100
    assert total_dialogues > 500

