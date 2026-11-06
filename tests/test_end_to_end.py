import pytest
import os
import glob
from pathlib import Path

from src.parser import extract_text_from_txt, parse_screenplay
from src.screenplay_analyzer import ScreenplayAnalyzer
from src.promo_discovery import PromoDiscoveryEngine
from src.ranking import PromoRanker
from src.quality_checker import QualityChecker
from src.exporter import Exporter
from src.config import FINAL_RESULTS_DIR, QUALITY_REPORTS_DIR


def test_round_1_two_episodes(tmp_path):
    """
    ROUND 1: Test with two screenplay files (Episode 1 & Episode 2).
    """
    files = ["input/episode-001-Episode 1671703.txt", "input/episode-002-Episode 1671704.txt"]
    episodes = []
    for f in files:
        assert os.path.exists(f)
        text = extract_text_from_txt(f)
        ep = parse_screenplay(text, source_filename=f)
        episodes.append(ep)

    assert len(episodes) == 2

    # Analyze
    analyzer = ScreenplayAnalyzer(cache_dir=tmp_path / "analyzed")
    analyses = [analyzer.analyze_episode(ep) for ep in episodes]
    assert len(analyses) == 2

    # Discover
    engine = PromoDiscoveryEngine()
    candidates = engine.discover_all_promos(episodes, analyses)
    assert len(candidates) >= 2

    # Rank
    ranker = PromoRanker()
    evaluations = ranker.evaluate_and_rank_all(candidates)
    assert len(evaluations) == len(candidates)
    top_3 = [ev for ev in evaluations if ev.is_top_three]
    assert len(top_3) <= 3 and len(top_3) >= 1

    # Quality check
    checker = QualityChecker()
    report = checker.run_full_quality_check(evaluations, episodes)
    assert report.total_promos_checked == len(candidates)
    assert report.rule_violations_count == 0  # No structural rule violations


def test_round_2_ten_episodes(tmp_path):
    """
    ROUND 2: Test with ten screenplay files (Episodes 1 to 10).
    """
    files = sorted(glob.glob("input/*.txt"))[:10]
    assert len(files) == 10

    episodes = []
    for f in files:
        text = extract_text_from_txt(f)
        ep = parse_screenplay(text, source_filename=f)
        episodes.append(ep)

    assert len(episodes) == 10

    # Analyze
    analyzer = ScreenplayAnalyzer(cache_dir=tmp_path / "analyzed")
    analyses = [analyzer.analyze_episode(ep) for ep in episodes]
    assert len(analyses) == 10

    # Discover
    engine = PromoDiscoveryEngine()
    candidates = engine.discover_all_promos(episodes, analyses)
    assert len(candidates) > 10

    # Verify both single and multi-episode promos exist
    has_single = any(c.promo_type == "SINGLE_EPISODE" for c in candidates)
    has_multi = any(c.promo_type == "MULTI_EPISODE" for c in candidates)
    assert has_single, "Should discover single-episode promos"
    assert has_multi, "Should discover multi-episode promos"

    # Rank
    ranker = PromoRanker()
    evaluations = ranker.evaluate_and_rank_all(candidates)
    top_3 = [ev for ev in evaluations if ev.is_top_three]
    assert len(top_3) == 3

    # Quality check
    checker = QualityChecker()
    report = checker.run_full_quality_check(evaluations, episodes)
    assert report.rule_violations_count == 0


def test_round_3_full_50_episodes(tmp_path):
    """
    ROUND 3: Full 50-episode pack execution and artifact generation.
    """
    files = sorted(glob.glob("input/*.txt"))
    assert len(files) == 50, f"Expected 50 files, got {len(files)}"

    episodes = []
    for f in files:
        text = extract_text_from_txt(f)
        ep = parse_screenplay(text, source_filename=f)
        episodes.append(ep)

    assert len(episodes) == 50
    total_scenes = sum(len(ep.scenes) for ep in episodes)
    assert total_scenes == 100

    # Analyze
    analyzer = ScreenplayAnalyzer(cache_dir=tmp_path / "analyzed")
    analyses = [analyzer.analyze_episode(ep) for ep in episodes]
    assert len(analyses) == 50

    # Discover
    engine = PromoDiscoveryEngine()
    candidates = engine.discover_all_promos(episodes, analyses)
    assert len(candidates) > 30

    # Rank
    ranker = PromoRanker()
    evaluations = ranker.evaluate_and_rank_all(candidates)
    assert len(evaluations) == len(candidates)

    top_3 = [ev for ev in evaluations if ev.is_top_three][:3]
    assert len(top_3) == 3

    # Verify ranking monotonicity
    scores = [ev.overall_promo_score for ev in evaluations]
    assert scores == sorted(scores, reverse=True)

    # Quality check
    checker = QualityChecker()
    report = checker.run_full_quality_check(evaluations, episodes)
    assert report.rule_violations_count == 0

    # Export final artifacts to data/final_results/
    json_path = FINAL_RESULTS_DIR / "complete_results.json"
    csv_path = FINAL_RESULTS_DIR / "ranked_promos.csv"
    pdf_path = FINAL_RESULTS_DIR / "executive_report.pdf"

    Exporter.export_json(evaluations, json_path)
    Exporter.export_csv(evaluations, csv_path)
    Exporter.export_pdf(evaluations, report, pdf_path)

    assert json_path.exists() and json_path.stat().st_size > 0
    assert csv_path.exists() and csv_path.stat().st_size > 0
    assert pdf_path.exists() and pdf_path.stat().st_size > 0
