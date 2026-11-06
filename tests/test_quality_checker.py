import pytest
from src.models import (
    PromoCandidate,
    PromoSegment,
    Episode,
    Scene,
    PromoEvaluation,
    HookEvaluation,
    CliffhangerEvaluation,
)
from src.quality_checker import QualityChecker

@pytest.fixture
def dummy_episode():
    return Episode(
        episode_id=1,
        title="Episode 1",
        scenes=[
            Scene(
                episode_id=1,
                scene_id="EP01_SCENE_01",
                scene_number=1,
                heading="INT. CATHEDRAL",
                start_time="00:00.00",
                end_time="02:00.00",
                start_seconds=0.0,
                end_seconds=120.0,
                duration_seconds=120.0,
            )
        ],
    )


def test_rule_based_validation_valid(dummy_episode):
    checker = QualityChecker()
    cand = PromoCandidate(
        promo_id="VALID_01",
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
        hook_text="Valid hook text",
        hook_start_time="00:10.00",
        hook_end_time="00:14.00",
        cliffhanger_text="Valid cliffhanger text",
        cliffhanger_start_time="00:35.00",
        cliffhanger_end_time="00:40.00",
        unresolved_question="Valid question?",
        rationale="Valid rationale",
    )

    errors = checker.validate_rules([cand], [dummy_episode])
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"


def test_rule_based_validation_invalid_duration(dummy_episode):
    checker = QualityChecker()
    short_cand = PromoCandidate(
        promo_id="SHORT_01",
        promo_type="SINGLE_EPISODE",
        episodes=[1],
        segments=[
            PromoSegment(
                episode_id=1,
                scene_id="EP01_SCENE_01",
                start_time="00:10.00",
                end_time="00:20.00",
                start_seconds=10.0,
                end_seconds=20.0,
                duration_seconds=10.0,  # 10s is < 20s
            )
        ],
        total_duration_seconds=10.0,
        hook_text="Short hook",
        hook_start_time="00:10.00",
        hook_end_time="00:13.00",
        cliffhanger_text="Short cliff",
        cliffhanger_start_time="00:17.00",
        cliffhanger_end_time="00:20.00",
        unresolved_question="Short?",
        rationale="Too short",
    )

    errors = checker.validate_rules([short_cand], [dummy_episode])
    assert any(e.error_type == "DURATION_OUT_OF_BOUNDS" for e in errors)


def test_rule_based_validation_invalid_reference(dummy_episode):
    checker = QualityChecker()
    invalid_ep_cand = PromoCandidate(
        promo_id="INVALID_EP_01",
        promo_type="SINGLE_EPISODE",
        episodes=[999],  # does not exist
        segments=[
            PromoSegment(
                episode_id=999,
                scene_id="EP999_SCENE_01",
                start_time="00:10.00",
                end_time="00:40.00",
                start_seconds=10.0,
                end_seconds=40.0,
                duration_seconds=30.0,
            )
        ],
        total_duration_seconds=30.0,
        hook_text="Hook",
        hook_start_time="00:10.00",
        hook_end_time="00:14.00",
        cliffhanger_text="Cliff",
        cliffhanger_start_time="00:35.00",
        cliffhanger_end_time="00:40.00",
        unresolved_question="?",
        rationale="r",
    )

    errors = checker.validate_rules([invalid_ep_cand], [dummy_episode])
    assert any(e.error_type == "INVALID_EPISODE_REFERENCE" for e in errors)


def test_full_quality_report(dummy_episode):
    checker = QualityChecker()
    cand = PromoCandidate(
        promo_id="VALID_01",
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
        hook_text="Valid hook text",
        hook_start_time="00:10.00",
        hook_end_time="00:14.00",
        cliffhanger_text="Valid cliffhanger text",
        cliffhanger_start_time="00:35.00",
        cliffhanger_end_time="00:40.00",
        unresolved_question="Valid question?",
        rationale="Valid rationale",
    )

    ev = PromoEvaluation(
        promo_id="VALID_01",
        candidate=cand,
        hook_eval=HookEvaluation(
            delay_score=23.0,
            confusion_score=22.0,
            irrelevance_score=22.0,
            disinterest_score=22.0,
            total_hook_score=89.0,
            hook_dialogue="Valid hook",
            hook_start_time="00:10.00",
            hook_end_time="00:14.00",
            supporting_evidence="text",
            explanation="Good hook",
        ),
        cliffhanger_eval=CliffhangerEvaluation(
            cliffhanger_score=85.0,
            description="Good cliff",
            supporting_evidence="text",
            source_timestamp="00:40.00",
            unresolved_question="What happens?",
            explanation="Solid",
        ),
        story_clarity_score=90.0,
        emotional_impact_score=85.0,
        scene_continuity_score=95.0,
        overall_promo_score=88.5,
        rank=1,
        is_top_three=True,
    )

    report = checker.run_full_quality_check([ev], [dummy_episode])
    assert report.total_promos_checked == 1
    assert report.rule_violations_count == 0
