import pytest
from src.models import (
    PromoCandidate,
    PromoSegment,
    PromoEvaluation,
    HookEvaluation,
    CliffhangerEvaluation,
)
from src.exporter import Exporter

@pytest.fixture
def sample_evaluation():
    cand = PromoCandidate(
        promo_id="TEST_EX_01",
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
        hook_text="Hook dialogue",
        hook_start_time="00:10.00",
        hook_end_time="00:14.00",
        cliffhanger_text="Cliffhanger dialogue",
        cliffhanger_start_time="00:35.00",
        cliffhanger_end_time="00:40.00",
        unresolved_question="What happens next?",
        rationale="Dramatic confrontation",
    )
    return PromoEvaluation(
        promo_id="TEST_EX_01",
        candidate=cand,
        hook_eval=HookEvaluation(
            delay_score=24.0,
            confusion_score=23.0,
            irrelevance_score=24.0,
            disinterest_score=23.0,
            total_hook_score=94.0,
            hook_dialogue="Hook dialogue",
            hook_start_time="00:10.00",
            hook_end_time="00:14.00",
            supporting_evidence="text",
            explanation="Explanation",
        ),
        cliffhanger_eval=CliffhangerEvaluation(
            cliffhanger_score=90.0,
            description="Cliffhanger dialogue",
            supporting_evidence="text",
            source_timestamp="00:40.00",
            unresolved_question="What happens next?",
            explanation="Explanation",
        ),
        story_clarity_score=90.0,
        emotional_impact_score=95.0,
        scene_continuity_score=98.0,
        overall_promo_score=92.9,
        rank=1,
        is_top_three=True,
        publish_priority_reason="Top priority candidate.",
    )


def test_export_json_and_csv(sample_evaluation):
    json_out = Exporter.export_json([sample_evaluation])
    assert "TEST_EX_01" in json_out
    assert "overall_promo_score" in json_out

    csv_out = Exporter.export_csv([sample_evaluation])
    assert "TEST_EX_01" in csv_out
    assert "Overall Score" in csv_out


def test_export_pdf(sample_evaluation):
    pdf_bytes = Exporter.export_pdf([sample_evaluation])
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

