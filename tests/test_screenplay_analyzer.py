import pytest
import os
import shutil
from pathlib import Path
from src.parser import parse_screenplay, extract_text_from_txt
from src.screenplay_analyzer import ScreenplayAnalyzer
from src.models import EpisodeAnalysis, SceneAnalysis

@pytest.fixture
def sample_episode():
    path = os.path.join("input", "episode-001-Episode 1671703.txt")
    text = extract_text_from_txt(path)
    return parse_screenplay(text, source_filename=path)


def test_screenplay_analyzer_basic(tmp_path, sample_episode):
    analyzer = ScreenplayAnalyzer(cache_dir=tmp_path, batch_size=2)
    ep_analysis = analyzer.analyze_episode(sample_episode)

    assert isinstance(ep_analysis, EpisodeAnalysis)
    assert ep_analysis.episode_id == 1
    assert len(ep_analysis.scene_analyses) == 1

    sa = ep_analysis.scene_analyses[0]
    assert sa.scene_id == "EP01_SCENE_01"
    assert sa.emotional_intensity >= 6
    assert len(sa.hook_moments) > 0
    assert len(sa.cliffhanger_moments) > 0
    assert len(sa.betrayals) > 0 or len(sa.key_conflict) > 0


def test_analyzer_caching(tmp_path, sample_episode):
    analyzer = ScreenplayAnalyzer(cache_dir=tmp_path, batch_size=2)

    # First run: creates cache
    analysis1 = analyzer.analyze_episode(sample_episode)
    cache_file = tmp_path / "episode_001.json"
    assert cache_file.exists()

    # Second run: reads from cache
    analysis2 = analyzer.analyze_episode(sample_episode)
    assert analysis2.episode_id == analysis1.episode_id
    assert len(analysis2.scene_analyses) == len(analysis1.scene_analyses)
    assert analysis2.scene_analyses[0].scene_id == analysis1.scene_analyses[0].scene_id


def test_analyzer_multiscene(tmp_path):
    path = os.path.join("input", "episode-003-Episode 1671705.txt")
    text = extract_text_from_txt(path)
    ep3 = parse_screenplay(text, source_filename=path)

    analyzer = ScreenplayAnalyzer(cache_dir=tmp_path, batch_size=2)
    ep_analysis = analyzer.analyze_episode(ep3)

    assert len(ep_analysis.scene_analyses) == 3
    for sa in ep_analysis.scene_analyses:
        assert isinstance(sa, SceneAnalysis)
        assert sa.episode_id == 3

