import pytest
import os
from src.parser import parse_screenplay, extract_text_from_txt
from src.screenplay_analyzer import ScreenplayAnalyzer
from src.promo_discovery import PromoDiscoveryEngine
from src.models import PromoCandidate

@pytest.fixture
def parsed_episodes(tmp_path):
    eps = []
    for f in ["episode-001-Episode 1671703.txt", "episode-002-Episode 1671704.txt"]:
        path = os.path.join("input", f)
        text = extract_text_from_txt(path)
        eps.append(parse_screenplay(text, source_filename=path))
    return eps

@pytest.fixture
def analyzed_episodes(tmp_path, parsed_episodes):
    analyzer = ScreenplayAnalyzer(cache_dir=tmp_path)
    return [analyzer.analyze_episode(ep) for ep in parsed_episodes]


def test_promo_discovery_single_and_multi(parsed_episodes, analyzed_episodes):
    engine = PromoDiscoveryEngine(min_duration=20.0, max_duration=60.0)
    candidates = engine.discover_all_promos(parsed_episodes, analyzed_episodes)

    assert len(candidates) > 0

    single_eps = [c for c in candidates if c.promo_type == "SINGLE_EPISODE"]
    multi_eps = [c for c in candidates if c.promo_type == "MULTI_EPISODE"]

    assert len(single_eps) > 0, "Should discover single-episode promos"
    assert len(multi_eps) > 0, "Should discover multi-episode promos"

    for c in candidates:
        assert isinstance(c, PromoCandidate)
        assert 20.0 <= c.total_duration_seconds <= 60.0
        assert len(c.segments) >= 1
        assert c.hook_text != ""
        assert c.cliffhanger_text != ""
        assert c.unresolved_question != ""

        # Check segment validity
        for seg in c.segments:
            assert seg.start_seconds < seg.end_seconds
            assert seg.duration_seconds > 0


def test_promo_deduplication(parsed_episodes, analyzed_episodes):
    engine = PromoDiscoveryEngine()
    candidates = engine.discover_all_promos(parsed_episodes, analyzed_episodes)

    # Duplicating the list
    doubled = candidates + candidates
    deduped = engine.deduplicate_candidates(doubled)

    assert len(deduped) == len(candidates)


def test_unique_promo_ids_no_collisions(parsed_episodes, analyzed_episodes):
    engine = PromoDiscoveryEngine()
    candidates = engine.discover_all_promos(parsed_episodes, analyzed_episodes)
    ids = [c.promo_id for c in candidates]
    assert len(ids) == len(set(ids)), "All promo candidate IDs must be strictly unique"


def test_unresolved_question_matches_actual_ending(parsed_episodes, analyzed_episodes):
    engine = PromoDiscoveryEngine()
    candidates = engine.discover_all_promos(parsed_episodes, analyzed_episodes)
    
    # Filter candidates in Episode 1 that end mid-scene at "Embarrassed you?"
    cand = next(
        (c for c in candidates if "Embarrassed you?" in c.cliffhanger_text),
        None,
    )
    assert cand is not None
    # Must NOT contain the final scene line about Clarissa being the jewel of the county
    assert "Clarissa is the true jewel" not in cand.unresolved_question
    assert "Embarrassed you?" in cand.unresolved_question


def test_weak_ending_marking(parsed_episodes, analyzed_episodes):
    engine = PromoDiscoveryEngine()
    candidates = engine.discover_all_promos(parsed_episodes, analyzed_episodes)
    
    # Find any candidate that ends on a scenic transition
    neutral_cands = [c for c in candidates if "dramatic scene transition" in c.cliffhanger_text.lower()]
    for nc in neutral_cands:
        # If it cut before the end of the scene, it must be marked as weak/resolved
        if nc.segments[0].end_seconds < 100.0:
            assert "Weak / Resolved ending" in nc.unresolved_question or "transition" in nc.unresolved_question.lower()


