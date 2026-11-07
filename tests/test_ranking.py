import pytest
from src.models import PromoCandidate, PromoSegment
from src.ranking import PromoRanker

@pytest.fixture
def sample_candidates():
    c1 = PromoCandidate(
        promo_id="PROMO_A",
        promo_type="SINGLE_EPISODE",
        episodes=[1],
        segments=[
            PromoSegment(
                episode_id=1,
                scene_id="EP01_SCENE_01",
                start_time="00:10.00",
                end_time="00:45.00",
                start_seconds=10.0,
                end_seconds=45.0,
                duration_seconds=35.0,
            )
        ],
        total_duration_seconds=35.0,
        hook_text="You should turn around, Juliana.",
        hook_start_time="00:11.30",
        hook_end_time="00:14.30",
        cliffhanger_text="Because he is marrying me.",
        cliffhanger_start_time="00:39.10",
        cliffhanger_end_time="00:45.00",
        unresolved_question="Will Juliana fight back against Clarissa?",
        rationale="Stunning public wedding abandonment",
        key_conflict="Juliana betrayed at altar",
    )

    c2 = PromoCandidate(
        promo_id="PROMO_B",
        promo_type="MULTI_EPISODE",
        episodes=[1, 2],
        segments=[
            PromoSegment(
                episode_id=1,
                scene_id="EP01_SCENE_01",
                start_time="00:30.00",
                end_time="00:45.00",
                start_seconds=30.0,
                end_seconds=45.0,
                duration_seconds=15.0,
            ),
            PromoSegment(
                episode_id=2,
                scene_id="EP02_SCENE_01",
                start_time="00:10.00",
                end_time="00:30.00",
                start_seconds=10.0,
                end_seconds=30.0,
                duration_seconds=20.0,
            ),
        ],
        total_duration_seconds=35.0,
        hook_text="Why are you holding her hand?",
        hook_start_time="00:30.00",
        hook_end_time="00:33.00",
        cliffhanger_text="You are completely beneath the future I deserve.",
        cliffhanger_start_time="00:25.00",
        cliffhanger_end_time="00:30.00",
        unresolved_question="How will Juliana punish Gerald's arrogance?",
        rationale="Multi-episode escalation",
        key_conflict="Gerald attacks Juliana's worth",
    )

    return [c1, c2]


def test_ranking_scoring_formula(sample_candidates):
    ranker = PromoRanker()
    evaluations = ranker.evaluate_and_rank_all(sample_candidates)

    assert len(evaluations) == 2
    for ev in evaluations:
        expected = round(
            0.40 * ev.hook_eval.total_hook_score
            + 0.25 * ev.cliffhanger_eval.cliffhanger_score
            + 0.15 * ev.story_clarity_score
            + 0.10 * ev.emotional_impact_score
            + 0.10 * ev.scene_continuity_score,
            2,
        )
        assert abs(ev.overall_promo_score - expected) < 0.01
        assert ev.rank in [1, 2]
        assert ev.is_top_three is True
        assert ev.publish_priority_reason != ""


def test_tie_breaking():
    # Construct two identical candidates to test true tie handling
    c1 = PromoCandidate(
        promo_id="PROMO_TIE_1",
        promo_type="SINGLE_EPISODE",
        episodes=[1],
        segments=[
            PromoSegment(
                episode_id=1,
                scene_id="EP01_SCENE_01",
                start_time="00:00.00",
                end_time="00:30.00",
                start_seconds=0.0,
                end_seconds=30.0,
                duration_seconds=30.0,
            )
        ],
        total_duration_seconds=30.0,
        hook_text="Test dialogue hook",
        hook_start_time="00:00.00",
        hook_end_time="00:04.00",
        cliffhanger_text="Test cliffhanger line",
        cliffhanger_start_time="00:25.00",
        cliffhanger_end_time="00:30.00",
        unresolved_question="Unresolved question?",
        rationale="Test rationale",
    )
    c2 = c1.model_copy(update={"promo_id": "PROMO_TIE_2"})

    ranker = PromoRanker()
    evals = ranker.evaluate_and_rank_all([c1, c2])

    assert len(evals) == 2
    # Since all metrics are identical, ranks must be tied
    assert evals[0].rank == evals[1].rank
    assert evals[0].rank == 1


def test_dataframe_conversion(sample_candidates):
    ranker = PromoRanker()
    evals = ranker.evaluate_and_rank_all(sample_candidates)
    df = ranker.to_dataframe(evals)

    assert len(df) == 2
    assert "Overall Score" in df.columns
    assert "Hook Score (40%)" in df.columns
    assert "Cliffhanger Score (25%)" in df.columns
    assert "Rank" in df.columns


def test_diversity_clustering_near_duplicates():
    # Construct 3 candidates: 2 overlapping variants of Episode 1 scene, 1 from Episode 2
    c1 = PromoCandidate(
        promo_id="PROMO_EP01_VAR1",
        promo_type="SINGLE_EPISODE",
        episodes=[1],
        segments=[
            PromoSegment(
                episode_id=1,
                scene_id="EP01_SCENE_01",
                start_time="00:10.00",
                end_time="00:40.00",
                start_seconds=10.0,
                end_seconds=40.0,
                duration_seconds=30.0,
            )
        ],
        total_duration_seconds=30.0,
        hook_text="You should turn around, Juliana.",
        hook_start_time="00:10.00",
        hook_end_time="00:13.00",
        cliffhanger_text="Because he is marrying me.",
        cliffhanger_start_time="00:35.00",
        cliffhanger_end_time="00:40.00",
        unresolved_question="How will Juliana react?",
        rationale="Variant 1",
    )
    # Variant 2: same scene, same hook, 3 seconds longer
    c2 = PromoCandidate(
        promo_id="PROMO_EP01_VAR2",
        promo_type="SINGLE_EPISODE",
        episodes=[1],
        segments=[
            PromoSegment(
                episode_id=1,
                scene_id="EP01_SCENE_01",
                start_time="00:10.00",
                end_time="00:43.00",
                start_seconds=10.0,
                end_seconds=43.0,
                duration_seconds=33.0,
            )
        ],
        total_duration_seconds=33.0,
        hook_text="You should turn around, Juliana.",
        hook_start_time="00:10.00",
        hook_end_time="00:13.00",
        cliffhanger_text="No...",
        cliffhanger_start_time="00:40.00",
        cliffhanger_end_time="00:43.00",
        unresolved_question="How will Juliana react?",
        rationale="Variant 2",
    )
    # Candidate 3: distinct scene in Episode 2
    c3 = PromoCandidate(
        promo_id="PROMO_EP02_VAR1",
        promo_type="SINGLE_EPISODE",
        episodes=[2],
        segments=[
            PromoSegment(
                episode_id=2,
                scene_id="EP02_SCENE_01",
                start_time="00:05.00",
                end_time="00:35.00",
                start_seconds=5.0,
                end_seconds=35.0,
                duration_seconds=30.0,
            )
        ],
        total_duration_seconds=30.0,
        hook_text="I cannot marry you, Juliana.",
        hook_start_time="00:05.00",
        hook_end_time="00:08.00",
        cliffhanger_text="Gerald... Look at me.",
        cliffhanger_start_time="00:30.00",
        cliffhanger_end_time="00:35.00",
        unresolved_question="Will Gerald look at her?",
        rationale="Distinct episode",
    )

    ranker = PromoRanker()
    evals = ranker.evaluate_and_rank_all([c1, c2, c3])

    # c1 and c2 must share the same cluster_id
    var1 = next(e for e in evals if e.candidate.promo_id == "PROMO_EP01_VAR1")
    var2 = next(e for e in evals if e.candidate.promo_id == "PROMO_EP01_VAR2")
    assert var1.cluster_id == var2.cluster_id
    # Only one of c1 or c2 can be cluster primary
    ep1_evals = [e for e in evals if e.candidate.episodes[0] == 1]
    assert sum(1 for e in ep1_evals if e.is_cluster_primary) == 1
    # Both c1 and c2 remain preserved in the full list
    assert len(evals) == 3


def test_two_stage_evaluation_and_caching(tmp_path, sample_candidates, monkeypatch):
    """
    Verifies that Stage A performs fast deterministic baseline scoring,
    and Stage B loads cached LLM evaluations or safely falls back.
    """
    from src.config import CACHE_DIR
    import json

    ranker = PromoRanker()

    # Pre-populate disk cache with one candidate evaluation
    test_cache = {
        "PROMO_A": {
            "hook_eval": {
                "delay_score": 25.0,
                "confusion_score": 25.0,
                "irrelevance_score": 25.0,
                "disinterest_score": 25.0,
                "total_hook_score": 100.0,
                "hook_dialogue": sample_candidates[0].hook_text,
                "hook_start_time": sample_candidates[0].hook_start_time,
                "hook_end_time": sample_candidates[0].hook_end_time,
                "supporting_evidence": "Altar dialogue",
                "weaknesses": [],
                "explanation": "Perfect hook scored by LLM cache",
            },
            "cliffhanger_eval": {
                "cliffhanger_score": 95.0,
                "description": sample_candidates[0].cliffhanger_text,
                "supporting_evidence": "Altar line",
                "source_timestamp": sample_candidates[0].cliffhanger_end_time,
                "unresolved_question": sample_candidates[0].unresolved_question,
                "explanation": "High stakes cliffhanger",
                "weaknesses": [],
            },
        }
    }
    cache_file = CACHE_DIR / "llm_deep_evaluations.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(test_cache, f)

    # Mock client and api_key to allow Stage B execution
    ranker.api_key = "dummy_key"
    ranker.client = object()

    # Temporarily remove PYTEST_CURRENT_TEST to test Stage B path
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    evals = ranker.evaluate_and_rank_all(sample_candidates, deep_evaluate_top_n=2)

    # PROMO_A was in cache, so it should be marked as LLM evaluated
    promo_a_eval = next(e for e in evals if e.promo_id == "PROMO_A")
    assert promo_a_eval.evaluated_by_gemini is True
    assert promo_a_eval.hook_eval.total_hook_score == 100.0
    assert promo_a_eval.cliffhanger_eval.cliffhanger_score == 95.0

    # Ensure all original timestamps and segments are completely preserved
    assert promo_a_eval.candidate.segments[0].start_seconds == 10.0
    assert promo_a_eval.candidate.segments[0].end_seconds == 45.0



