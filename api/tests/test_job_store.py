from datetime import timedelta
from uuid import UUID

import pytest
from clock import Clock

from panther_api.jobs.models import JobStatus
from panther_api.jobs.refmap import RefmapInput
from panther_api.jobs.store import JobRecord, JobStore
from panther_api.jobs.tools import ToolsInput, ToolsResult
from panther_api.jobs.work import RefmapJobRequest, SerializedResult, ToolsJobRequest
from panther_api.problems import Problem
from panther_api.settings import MIB
from panther_api.versions import DataVersion, ToolVersion, Versions

EXPIRY = timedelta(hours=24)
REQUEST = ToolsJobRequest(service="tools", input=ToolsInput())
VERSIONS = Versions(
    api="1.0",
    engine="2.0",
    tools=[ToolVersion(name="blastp", version="2.17.0")],
    data=[DataVersion(service="csnp", panther="9")],
)
RESULT = ToolsResult(tools=[ToolVersion(name="blastp", version="2.17.0")])
ERROR = Problem(title="Internal Server Error", status=500, detail="It failed.")


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    clock = Clock()
    monkeypatch.setattr("panther_api.jobs.store.utcnow", clock)
    return clock


@pytest.fixture
def store(clock: Clock) -> JobStore:
    return JobStore(expiry=EXPIRY, results_budget=256 * MIB)


def test_a_new_job_is_queued(store: JobStore, clock: Clock) -> None:
    job = store.add(REQUEST, VERSIONS)

    assert job.status is JobStatus.QUEUED
    assert (job.service, job.summary) == ("tools", "")
    assert job.versions == VERSIONS
    assert job.created_at == clock.now
    assert (job.started_at, job.finished_at, job.result, job.error) == (None, None, None, None)


def test_ids_are_random_uuid4s(store: JobStore) -> None:
    ids = {store.add(REQUEST, VERSIONS).id for _ in range(3)}

    assert len(ids) == 3
    assert all(isinstance(job_id, UUID) and job_id.version == 4 for job_id in ids)


def test_a_job_is_found_by_its_id(store: JobStore) -> None:
    job = store.add(REQUEST, VERSIONS)

    assert store.get(str(job.id)) is job
    assert store.get(str(job.id).upper()) is job


@pytest.mark.parametrize("job_id", ["9b2f1d36-5a4e-4c3b-8f7a-2d1e0c9b8a76", "not-a-uuid", ""])
def test_an_unknown_id_is_not_found(store: JobStore, job_id: str) -> None:
    store.add(REQUEST, VERSIONS)

    assert store.get(job_id) is None


def test_the_lifecycle_sets_status_and_times(store: JobStore, clock: Clock) -> None:
    job = store.add(REQUEST, VERSIONS)
    created = clock.now

    clock.advance(timedelta(seconds=1))
    job.start()
    assert (job.status, job.started_at) == (JobStatus.RUNNING, created + timedelta(seconds=1))

    clock.advance(timedelta(seconds=1))
    job.succeed(RESULT)
    assert (job.status, job.finished_at) == (JobStatus.SUCCEEDED, created + timedelta(seconds=2))
    assert (job.result, job.error) == (RESULT, None)


def test_a_failed_job_has_an_error_and_no_result(store: JobStore, clock: Clock) -> None:
    job = store.add(REQUEST, VERSIONS)
    job.start()

    job.fail(ERROR)

    assert (job.status, job.finished_at) == (JobStatus.FAILED, clock.now)
    assert (job.result, job.error) == (None, ERROR)


def test_a_finished_job_is_kept_until_it_expires(store: JobStore, clock: Clock) -> None:
    job = store.add(REQUEST, VERSIONS)
    job.start()
    job.succeed(RESULT)

    clock.advance(EXPIRY - timedelta(seconds=1))
    assert store.get(str(job.id)) is job

    clock.advance(timedelta(seconds=1))
    assert store.get(str(job.id)) is None
    assert len(store) == 0


def test_an_unfinished_job_never_expires(store: JobStore, clock: Clock) -> None:
    queued = store.add(REQUEST, VERSIONS)
    running = store.add(REQUEST, VERSIONS)
    running.start()

    clock.advance(EXPIRY * 10)

    assert store.get(str(queued.id)) is queued
    assert store.get(str(running.id)) is running


def test_adding_a_job_sweeps_out_expired_ones(store: JobStore, clock: Clock) -> None:
    old = store.add(REQUEST, VERSIONS)
    old.start()
    old.fail(ERROR)
    unfinished = store.add(REQUEST, VERSIONS)

    clock.advance(EXPIRY)
    new = store.add(REQUEST, VERSIONS)

    # Swept without anyone asking for it again.
    assert len(store) == 2
    assert store.get(str(unfinished.id)) is unfinished
    assert store.get(str(new.id)) is new


def test_a_job_keeps_its_inputs_size_not_the_input(store: JobStore) -> None:
    ids = [f"U{index:05d}" for index in range(1000)]
    request = RefmapJobRequest(service="refmap", input=RefmapInput(organism="ENDPU", ids=ids))

    job = store.add(request, VERSIONS)

    assert (job.service, job.summary) == ("refmap", "ENDPU, 1000 IDs")
    assert "U00001" not in repr(job)


# The results budget (scoring-jobs: Jobs expire).


def finished(store: JobStore, clock: Clock, size: int) -> JobRecord:
    """A job that has succeeded, a second after the last, with a result of `size` bytes."""
    clock.advance(timedelta(seconds=1))
    job = store.add(REQUEST, VERSIONS)
    job.start()
    store.succeed(job, SerializedResult(b"x" * size))
    return job


def kept(store: JobStore, *jobs: JobRecord) -> list[bool]:
    return [store.get(str(job.id)) is job for job in jobs]


@pytest.fixture
def small_budget(clock: Clock) -> JobStore:
    return JobStore(expiry=EXPIRY, results_budget=10 * MIB)


def test_over_the_results_budget_the_oldest_finished_job_expires(
    small_budget: JobStore, clock: Clock
) -> None:
    first = finished(small_budget, clock, 4 * MIB)
    second = finished(small_budget, clock, 4 * MIB)
    assert small_budget.results_bytes == 8 * MIB

    third = finished(small_budget, clock, 4 * MIB)

    assert kept(small_budget, first, second, third) == [False, True, True]
    assert small_budget.results_bytes == 8 * MIB


def test_within_the_results_budget_every_job_is_kept(small_budget: JobStore, clock: Clock) -> None:
    jobs = [finished(small_budget, clock, 2 * MIB) for _ in range(5)]

    assert kept(small_budget, *jobs) == [True] * 5
    assert small_budget.results_bytes == 10 * MIB


def test_a_result_larger_than_the_budget_is_kept_alone(
    small_budget: JobStore, clock: Clock
) -> None:
    older = [finished(small_budget, clock, MIB) for _ in range(3)]
    unfinished = small_budget.add(REQUEST, VERSIONS)

    large = finished(small_budget, clock, 11 * MIB)

    assert kept(small_budget, *older, large) == [False, False, False, True]
    # Not finished, so not counted, and never expired.
    assert small_budget.get(str(unfinished.id)) is unfinished
    assert small_budget.results_bytes == 11 * MIB

    clock.advance(EXPIRY - timedelta(seconds=1))
    assert kept(small_budget, large) == [True]


def test_the_oldest_to_finish_expires_first_not_the_oldest_created(
    small_budget: JobStore, clock: Clock
) -> None:
    slow = small_budget.add(REQUEST, VERSIONS)
    slow.start()
    fast = finished(small_budget, clock, 4 * MIB)
    small_budget.succeed(slow, SerializedResult(b"x" * 4 * MIB))

    newest = finished(small_budget, clock, 4 * MIB)

    assert kept(small_budget, fast, slow, newest) == [False, True, True]


def test_a_failed_job_counts_nothing_against_the_budget(
    small_budget: JobStore, clock: Clock
) -> None:
    failed = small_budget.add(REQUEST, VERSIONS)
    failed.start()
    small_budget.fail(failed, ERROR)

    assert failed.status is JobStatus.FAILED
    assert small_budget.results_bytes == 0
    # Expiring it would free nothing, so it's kept even when a result doesn't fit.
    older = finished(small_budget, clock, 4 * MIB)
    finished(small_budget, clock, 11 * MIB)
    assert kept(small_budget, failed, older) == [True, False]


def test_a_models_result_is_counted_by_its_json(store: JobStore) -> None:
    job = store.add(REQUEST, VERSIONS)
    job.start()

    store.succeed(job, RESULT)

    assert job.result == RESULT
    assert store.results_bytes == len(RESULT.model_dump_json().encode())


def test_an_expired_job_frees_its_share_of_the_budget(small_budget: JobStore, clock: Clock) -> None:
    job = finished(small_budget, clock, 4 * MIB)

    clock.advance(EXPIRY)

    assert small_budget.get(str(job.id)) is None
    assert small_budget.results_bytes == 0
