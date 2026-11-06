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
