import pytest
from src.models import PromoCandidate, PromoSegment
from src.hook_evaluator import HookEvaluator
from src.cliffhanger_evaluator import CliffhangerEvaluator

@pytest.fixture
def sample_candidate():
    return PromoCandidate(
        promo_id="TEST_PROMO_01",
        promo_type="SINGLE_EPISODE",
        episodes=[1],
        segments=[
            PromoSegment(
                episode_id=1,
                scene_id="EP01_SCENE_01",
                start_time="00:33.80",
                end_time="01:05.60",
                start_seconds=33.8,
                end_seconds=65.6,
                duration_seconds=31.8,
                description="Confrontation at altar",
            )
        ],
        total_duration_seconds=31.8,
        hook_text='LADY JULIANA: "Why are you holding her hand?"',
        hook_start_time="00:33.80",
        hook_end_time="00:37.70",
        cliffhanger_text='THE FORMER GROOM: "I changed my mind."',
        cliffhanger_start_time="01:00.10",
        cliffhanger_end_time="01:05.60",
        unresolved_question="How will Juliana react to Gerald breaking their engagement publicly?",
        rationale="Uncompromising public betrayal in front of the cathedral guests.",
        key_conflict="Juliana abandoned at altar by Gerald",
    )


def test_hook_evaluator(sample_candidate):
    evaluator = HookEvaluator()
    hook_eval = evaluator.evaluate_hook(sample_candidate)

    assert 0.0 <= hook_eval.delay_score <= 25.0
    assert 0.0 <= hook_eval.confusion_score <= 25.0
    assert 0.0 <= hook_eval.irrelevance_score <= 25.0
    assert 0.0 <= hook_eval.disinterest_score <= 25.0
    assert 0.0 <= hook_eval.total_hook_score <= 100.0
    assert hook_eval.total_hook_score == round(
        hook_eval.delay_score
        + hook_eval.confusion_score
        + hook_eval.irrelevance_score
        + hook_eval.disinterest_score,
        1,
    )
    assert hook_eval.supporting_evidence != ""
    assert hook_eval.explanation != ""


def test_cliffhanger_evaluator(sample_candidate):
    evaluator = CliffhangerEvaluator()
    cliff_eval = evaluator.evaluate_cliffhanger(sample_candidate)

    assert 0.0 <= cliff_eval.cliffhanger_score <= 100.0
    assert cliff_eval.unresolved_question != ""
    assert cliff_eval.source_timestamp == sample_candidate.cliffhanger_end_time
    assert cliff_eval.explanation != ""

