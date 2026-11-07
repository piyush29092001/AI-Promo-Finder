import json
import pytest
from unittest.mock import MagicMock
from src.models import PromoCandidate, PromoSegment
from src.ranking import PromoRanker


def create_mock_candidate(promo_id: str, episode_id: int = 1) -> PromoCandidate:
    return PromoCandidate(
        promo_id=promo_id,
        promo_type="SINGLE_EPISODE",
        episodes=[episode_id],
        segments=[
            PromoSegment(
                episode_id=episode_id,
                scene_id=f"EP{episode_id:02d}_SCENE_01",
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
        unresolved_question="Will Juliana fight back against Clarissa?",
        rationale="Confrontation",
    )


def make_mock_response(candidates_batch):
    evals = []
    for c in candidates_batch:
        evals.append(
            {
                "promo_id": c.promo_id,
                "hook_eval": {
                    "delay_score": 24.0,
                    "confusion_score": 23.0,
                    "irrelevance_score": 25.0,
                    "disinterest_score": 24.0,
                    "total_hook_score": 96.0,
                    "hook_dialogue": c.hook_text,
                    "hook_start_time": c.hook_start_time,
                    "hook_end_time": c.hook_end_time,
                    "supporting_evidence": "Dialogue line",
                    "weaknesses": [],
                    "explanation": "Valid LLM hook",
                },
                "cliffhanger_eval": {
                    "cliffhanger_score": 90.0,
                    "description": c.cliffhanger_text,
                    "supporting_evidence": "Ending line",
                    "source_timestamp": c.cliffhanger_end_time,
                    "unresolved_question": c.unresolved_question,
                    "explanation": "Valid LLM cliffhanger",
                    "weaknesses": [],
                },
            }
        )
    resp = MagicMock()
    resp.text = json.dumps({"evaluations": evals})
    return resp


def test_successful_four_batch_execution(tmp_path, monkeypatch):
    """
    Test 1: 20 candidates across 4 batches (5 candidates each) execute successfully.
    """
    from src.config import CACHE_DIR

    cache_file = CACHE_DIR / "llm_deep_evaluations.json"
    if cache_file.exists():
        cache_file.unlink()

    candidates = [create_mock_candidate(f"PROMO_TEST_{i:02d}", episode_id=i) for i in range(1, 21)]

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = lambda model, contents, config: make_mock_response(
        [c for c in candidates if c.promo_id in contents]
    )

    ranker = PromoRanker(api_key="mock_key", request_timeout=5.0, initial_retry_delay=0.01)
    ranker.client = mock_client
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    evals = ranker.evaluate_and_rank_all(candidates, deep_evaluate_top_n=20, batch_size=5)

    assert len(evals) == 20
    assert mock_client.models.generate_content.call_count == 4
    for ev in evals:
        assert ev.evaluated_by_gemini is True
        assert ev.hook_eval.total_hook_score == 96.0
        assert ev.cliffhanger_eval.cliffhanger_score == 90.0


def test_failure_in_batch_2_followed_by_successful_retry(monkeypatch):
    """
    Test 2: Batch 2 fails with 503 UNAVAILABLE on attempt 1, but succeeds on attempt 2.
    """
    from src.config import CACHE_DIR

    cache_file = CACHE_DIR / "llm_deep_evaluations.json"
    if cache_file.exists():
        cache_file.unlink()

    candidates = [create_mock_candidate(f"PROMO_TEST_{i:02d}", episode_id=i) for i in range(1, 21)]

    call_count = 0

    def mock_generate(model, contents, config):
        nonlocal call_count
        call_count += 1
        # Fail on call 2 (which is attempt 1 of batch 2)
        if call_count == 2:
            raise Exception("503 UNAVAILABLE: Model is experiencing high demand")
        return make_mock_response([c for c in candidates if c.promo_id in contents])

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = mock_generate

    ranker = PromoRanker(api_key="mock_key", request_timeout=5.0, initial_retry_delay=0.01)
    ranker.client = mock_client
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    evals = ranker.evaluate_and_rank_all(candidates, deep_evaluate_top_n=20, batch_size=5)

    assert len(evals) == 20
    # 4 batches with 1 retry on batch 2 = 5 total calls
    assert call_count == 5
    for ev in evals:
        assert ev.evaluated_by_gemini is True


def test_rate_limit_429_handling(monkeypatch):
    """
    Test 3: Rate limit 429 RESOURCE_EXHAUSTED is caught, backed off, and succeeds on retry.
    """
    from src.config import CACHE_DIR

    cache_file = CACHE_DIR / "llm_deep_evaluations.json"
    if cache_file.exists():
        cache_file.unlink()

    candidates = [create_mock_candidate(f"PROMO_429_{i:02d}", episode_id=i) for i in range(1, 6)]

    call_count = 0

    def mock_generate(model, contents, config):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("429 RESOURCE_EXHAUSTED: Rate limit exceeded")
        return make_mock_response(candidates)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = mock_generate

    ranker = PromoRanker(api_key="mock_key", request_timeout=5.0, initial_retry_delay=0.01)
    ranker.client = mock_client
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    evals = ranker.evaluate_and_rank_all(candidates, deep_evaluate_top_n=5, batch_size=5)

    assert len(evals) == 5
    assert call_count == 2
    for ev in evals:
        assert ev.evaluated_by_gemini is True


def test_invalid_json_response(monkeypatch):
    """
    Test 4: Invalid JSON response is caught gracefully and retried.
    """
    from src.config import CACHE_DIR

    cache_file = CACHE_DIR / "llm_deep_evaluations.json"
    if cache_file.exists():
        cache_file.unlink()

    candidates = [create_mock_candidate(f"PROMO_JSON_{i:02d}", episode_id=i) for i in range(1, 6)]

    call_count = 0

    def mock_generate(model, contents, config):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            bad_resp = MagicMock()
            bad_resp.text = "{invalid json string"
            return bad_resp
        return make_mock_response(candidates)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = mock_generate

    ranker = PromoRanker(api_key="mock_key", request_timeout=5.0, initial_retry_delay=0.01)
    ranker.client = mock_client
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    evals = ranker.evaluate_and_rank_all(candidates, deep_evaluate_top_n=5, batch_size=5)

    assert len(evals) == 5
    assert call_count == 2
    for ev in evals:
        assert ev.evaluated_by_gemini is True


def test_partial_batch_response(monkeypatch):
    """
    Test 5: When Gemini returns evaluations for only 3 of 5 candidates in a batch,
    the 3 valid ones succeed and the 2 omitted ones safely retain baseline.
    """
    from src.config import CACHE_DIR

    cache_file = CACHE_DIR / "llm_deep_evaluations.json"
    if cache_file.exists():
        cache_file.unlink()

    candidates = [create_mock_candidate(f"PROMO_PARTIAL_{i:02d}", episode_id=i) for i in range(1, 6)]

    # Return evaluations for only the first 3 candidates
    partial_resp = make_mock_response(candidates[:3])
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = partial_resp

    ranker = PromoRanker(api_key="mock_key", request_timeout=5.0, initial_retry_delay=0.01)
    ranker.client = mock_client
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    evals = ranker.evaluate_and_rank_all(candidates, deep_evaluate_top_n=5, batch_size=5)

    assert len(evals) == 5
    evaluated_ids = {e.promo_id for e in evals if e.evaluated_by_gemini}
    baseline_ids = {e.promo_id for e in evals if not e.evaluated_by_gemini}

    assert len(evaluated_ids) == 3
    assert len(baseline_ids) == 2
    assert "PROMO_PARTIAL_01" in evaluated_ids
    assert "PROMO_PARTIAL_02" in evaluated_ids
    assert "PROMO_PARTIAL_03" in evaluated_ids
    assert "PROMO_PARTIAL_04" in baseline_ids
    assert "PROMO_PARTIAL_05" in baseline_ids


def test_cache_resume_after_interruption(monkeypatch):
    """
    Test 6: Pre-cached Batch 1 is not requested again; only remaining batches run.
    """
    from src.config import CACHE_DIR

    cache_file = CACHE_DIR / "llm_deep_evaluations.json"

    candidates = [create_mock_candidate(f"PROMO_RESUME_{i:02d}", episode_id=i) for i in range(1, 21)]

    # Pre-populate cache with Batch 1 (first 5 candidates)
    initial_cache = {}
    for c in candidates[:5]:
        initial_cache[c.promo_id] = {
            "hook_eval": {
                "delay_score": 25.0,
                "confusion_score": 25.0,
                "irrelevance_score": 25.0,
                "disinterest_score": 25.0,
                "total_hook_score": 100.0,
                "hook_dialogue": c.hook_text,
                "hook_start_time": c.hook_start_time,
                "hook_end_time": c.hook_end_time,
                "supporting_evidence": "Pre-cached line",
                "weaknesses": [],
                "explanation": "Pre-cached hook",
            },
            "cliffhanger_eval": {
                "cliffhanger_score": 95.0,
                "description": c.cliffhanger_text,
                "supporting_evidence": "Pre-cached line",
                "source_timestamp": c.cliffhanger_end_time,
                "unresolved_question": c.unresolved_question,
                "explanation": "Pre-cached cliffhanger",
                "weaknesses": [],
            },
        }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(initial_cache, f)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = lambda model, contents, config: make_mock_response(
        [c for c in candidates[5:] if c.promo_id in contents]
    )

    ranker = PromoRanker(api_key="mock_key", request_timeout=5.0, initial_retry_delay=0.01)
    ranker.client = mock_client
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    evals = ranker.evaluate_and_rank_all(candidates, deep_evaluate_top_n=20, batch_size=5)

    assert len(evals) == 20
    # Because first 5 were already in cache, only 15 were requested (3 calls instead of 4)
    assert mock_client.models.generate_content.call_count == 3
    for ev in evals:
        assert ev.evaluated_by_gemini is True


def test_no_duplicate_evaluation_of_completed_candidates(monkeypatch):
    """
    Test 7: When all 20 candidates are already cached, 0 API calls are made.
    """
    from src.config import CACHE_DIR

    cache_file = CACHE_DIR / "llm_deep_evaluations.json"

    candidates = [create_mock_candidate(f"PROMO_ALLCACHED_{i:02d}", episode_id=i) for i in range(1, 21)]

    all_cached = {}
    for c in candidates:
        all_cached[c.promo_id] = {
            "hook_eval": {
                "delay_score": 25.0,
                "confusion_score": 25.0,
                "irrelevance_score": 25.0,
                "disinterest_score": 25.0,
                "total_hook_score": 100.0,
                "hook_dialogue": c.hook_text,
                "hook_start_time": c.hook_start_time,
                "hook_end_time": c.hook_end_time,
                "supporting_evidence": "Pre-cached line",
                "weaknesses": [],
                "explanation": "Pre-cached hook",
            },
            "cliffhanger_eval": {
                "cliffhanger_score": 95.0,
                "description": c.cliffhanger_text,
                "supporting_evidence": "Pre-cached line",
                "source_timestamp": c.cliffhanger_end_time,
                "unresolved_question": c.unresolved_question,
                "explanation": "Pre-cached cliffhanger",
                "weaknesses": [],
            },
        }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(all_cached, f)

    mock_client = MagicMock()
    ranker = PromoRanker(api_key="mock_key", request_timeout=5.0, initial_retry_delay=0.01)
    ranker.client = mock_client
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    evals = ranker.evaluate_and_rank_all(candidates, deep_evaluate_top_n=20, batch_size=5)

    assert len(evals) == 20
    # ZERO calls to generate_content
    assert mock_client.models.generate_content.call_count == 0
    for ev in evals:
        assert ev.evaluated_by_gemini is True

