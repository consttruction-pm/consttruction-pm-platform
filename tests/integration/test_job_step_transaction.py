from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pytest

from construction_pm.job_execution import (
    InMemoryJobExecutionRepository,
    InMemoryJobTransactionManager,
    JobIdempotencyConflict,
    JobState,
    JobStepFailure,
    JobStepTransactionExecutor,
)


def _executor():
    repository = InMemoryJobExecutionRepository()
    return repository, JobStepTransactionExecutor(repository, InMemoryJobTransactionManager(repository))


def _run(executor, *, key="job-key", revision=0, payload=None, steps=()):
    return executor.execute(
        tenant_id="tenant-1",
        project_id="project-1",
        job_id="job-1",
        expected_revision=revision,
        idempotency_key=key,
        payload=payload or {"input": "v1"},
        steps=steps,
    )


def test_job_executes_steps_in_order_and_commits_once():
    _, executor = _executor()
    events = []

    result = _run(
        executor,
        steps=[
            lambda: events.append("step-1"),
            lambda: events.append("step-2"),
            lambda: events.append("step-3"),
        ],
    )

    assert result.state is JobState.SUCCEEDED
    assert result.revision == 1
    assert events == ["step-1", "step-2", "step-3"]


def test_step_two_failure_rolls_back_and_retry_with_new_key_is_allowed():
    repository, executor = _executor()
    calls = []

    def step_one():
        calls.append("step-1")

    def step_two():
        calls.append("step-2")
        raise JobStepFailure("temporary failure", retryable=True)

    failed = _run(
        executor,
        key="attempt-1",
        steps=[step_one, step_two, lambda: calls.append("step-3")],
    )

    assert failed.state is JobState.RETRYABLE
    assert repository.get_current("tenant-1", "project-1", "job-1").state is JobState.ROLLED_BACK
    assert calls == ["step-1", "step-2"]

    retried = _run(
        executor,
        key="attempt-2",
        steps=[lambda: calls.append("retry-1"), lambda: calls.append("retry-2")],
    )

    assert retried.state is JobState.SUCCEEDED
    assert retried.revision == 1


def test_same_key_replays_without_reexecuting_steps():
    _, executor = _executor()
    calls = []

    first = _run(executor, steps=[lambda: calls.append("run")])
    replay = _run(executor, steps=[lambda: calls.append("unexpected")])

    assert first.state is JobState.SUCCEEDED
    assert replay.state is JobState.REPLAYED
    assert calls == ["run"]


def test_same_key_with_different_payload_is_a_conflict():
    _, executor = _executor()
    _run(executor, payload={"input": "v1"}, steps=[lambda: None])

    with pytest.raises(JobIdempotencyConflict, match="JOB_IDEMPOTENCY_KEY_REUSE"):
        _run(executor, payload={"input": "v2"}, steps=[lambda: None])


def test_optimistic_revision_mismatch_returns_conflict_without_steps():
    repository, executor = _executor()
    _run(executor, steps=[lambda: None])

    calls = []
    result = _run(
        executor,
        key="next-key",
        revision=0,
        steps=[lambda: calls.append("must-not-run")],
    )

    assert result.state is JobState.CONFLICT
    assert result.revision == 1
    assert calls == []
    assert repository.get_current("tenant-1", "project-1", "job-1").revision == 1


def test_non_retryable_failure_is_failed_and_replayable():
    repository, executor = _executor()

    result = _run(
        executor,
        key="terminal-attempt",
        steps=[lambda: (_ for _ in ()).throw(JobStepFailure("bad input", retryable=False))],
    )

    assert result.state is JobState.FAILED
    replay = _run(
        executor,
        key="terminal-attempt",
        steps=[lambda: pytest.fail("replay must not execute")],
    )
    assert replay.state is JobState.REPLAYED
    assert repository.get_current("tenant-1", "project-1", "job-1").state is JobState.ROLLED_BACK


def test_concurrent_same_key_executes_steps_once():
    repository, executor = _executor()
    call_lock = Lock()
    calls = []

    def step():
        with call_lock:
            calls.append("executed")

    def worker():
        return _run(executor, key="concurrent-key", steps=[step])

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(lambda _: worker(), range(2))

    assert {first.state, second.state} == {JobState.SUCCEEDED, JobState.REPLAYED}
    assert calls == ["executed"]


def test_all_required_job_states_are_versioned():
    assert [state.value for state in JobState] == [
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        "RETRYABLE",
        "ROLLED_BACK",
        "REPLAYED",
        "CONFLICT",
    ]
