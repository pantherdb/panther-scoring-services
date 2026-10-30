from datetime import timedelta
from uuid import UUID

import pytest
from clock import Clock

from panther_api.jobs.models import JobStatus
from panther_api.jobs.store import JobStore
from panther_api.jobs.tools import ToolsInput, ToolsResult
from panther_api.jobs.work import ToolsJobRequest
from panther_api.problems import Problem
from panther_api.versions import ToolVersion, Versions

EXPIRY = timedelta(hours=24)
REQUEST = ToolsJobRequest(service="tools", input=ToolsInput())
VERSIONS = Versions(api="1.0", engine="2.0", tools=[ToolVersion(name="blastp", version="2.17.0")])
RESULT = ToolsResult(tools=[ToolVersion(name="blastp", version="2.17.0")])
ERROR = Problem(title="Internal Server Error", status=500, detail="It failed.")


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    clock = Clock()
    monkeypatch.setattr("panther_api.jobs.store.utcnow", clock)
    return clock


@pytest.fixture
def store(clock: Clock) -> JobStore:
    return JobStore(expiry=EXPIRY)


def test_a_new_job_is_queued(store: JobStore, clock: Clock) -> None:
    job = store.add(REQUEST, VERSIONS)

    assert job.status is JobStatus.QUEUED
    assert job.service == "tools"
    assert job.request == REQUEST
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
