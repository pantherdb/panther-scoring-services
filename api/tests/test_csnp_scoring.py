"""`csnp` jobs end to end: the API, a real worker, the engine, `blastp` and the cSNP data sample.

Skipped without `blastp` or the sample, as natively on Windows and in CI's `api` job. Run them in
the API image (docs/testing/api.md, "Tests With the Tools and Data"). The expected scores are the
engine's goldens: the release sample's proteins and substitutions, scored as spec §7.3 gives them.
"""

import time
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from markers import REPO_ROOT, data_folder

from panther_api.jobs.work import run_job
from panther_api.main import create_app

pytestmark = [pytest.mark.tools("blastp"), pytest.mark.data("csnp")]

GOLDEN = REPO_ROOT / "engine" / "tests" / "golden" / "csnp"
# A search takes seconds; the first job also starts a worker.
POLL_TIMEOUT = 300.0


def sample_fasta() -> dict[str, str]:
    """The release's sample.fasta, as FASTA text with its header, by id."""
    proteins: dict[str, list[str]] = {}
    name = ""
    for line in (GOLDEN / "release" / "sample.fasta").read_text().splitlines():
        if line.startswith(">"):
            name = line[1:].strip()
            proteins[name] = [line]
        elif line.strip():
            proteins[name].append(line.strip())
    return {name: "\n".join(lines) for name, lines in proteins.items()}


def expected_scores() -> dict[str, list[dict[str, Any]]]:
    """Spec §7.3's rows by protein, in order, as the job's scores: the token as a website user
    types it, then the age, message and pDel."""
    inputs = (GOLDEN / "release" / "sample.input").read_text().splitlines()
    outputs = (GOLDEN / "spec" / "sample.out").read_text().splitlines()
    rows: dict[str, list[dict[str, Any]]] = {}
    for line, output in zip(inputs, outputs, strict=True):
        _, protein, position, residues = line.split("|")
        wild_type, mutant = residues.split(";")
        _, _, family, age, message, pdel = output.split(",")
        rows.setdefault(protein, []).append(
            {
                "family": family,
                "score": {
                    "substitution": f"{wild_type}{position}{mutant.strip()}",
                    "age": int(age),
                    "message": message,
                    "pdel": pdel,
                },
            }
        )
    return rows


PROTEINS = sample_fasta()
EXPECTED = expected_scores()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """An app whose workers run the real work, with the data folder the markers checked. The
    workers start with the first job, so they inherit `PANTHER_DATA_DIR` from here."""
    monkeypatch.setattr("panther_api.jobs.runner.run_job", run_job)
    monkeypatch.setenv("PANTHER_DATA_DIR", str(data_folder()))
    with TestClient(create_app()) as client:
        yield client


def run(
    client: TestClient, sequence: str, substitutions: list[str], species: str = "HUMAN"
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/jobs",
        json={
            "service": "csnp",
            "input": {"sequence": sequence, "substitutions": substitutions, "species": species},
        },
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    deadline = time.monotonic() + POLL_TIMEOUT
    while True:
        job: dict[str, Any] = client.get(f"/api/v1/jobs/{job_id}").json()
        if job["status"] in ("succeeded", "failed"):
            return job
        assert time.monotonic() < deadline, f"job still {job['status']}"
        time.sleep(0.2)


@pytest.mark.parametrize("protein", ["P26439", "Q9H2F3", "P78314"])
def test_a_sample_protein_gets_its_spec_7_3_scores(client: TestClient, protein: str) -> None:
    rows = EXPECTED[protein]

    job = run(client, PROTEINS[protein], [row["score"]["substitution"] for row in rows])

    assert job["status"] == "succeeded", job["error"]
    assert job["result"] == {
        "family": rows[0]["family"],
        "scores": [row["score"] for row in rows],
    }
    assert job["versions"]["data"] == [{"service": "csnp", "panther": "9"}]


def test_a_species_without_a_hit_succeeds_with_no_family(client: TestClient) -> None:
    job = run(client, PROTEINS["P26439"], ["A10E"], species="PLAF7")

    assert job["status"] == "succeeded"
    assert job["result"] == {
        "family": None,
        "scores": [
            {
                "substitution": "A10E",
                "age": None,
                "message": "Not scored: No PANTHER family for input sequence",
                "pdel": None,
            }
        ],
    }


def test_a_sequence_blast_cant_read_fails_the_job_with_a_422(client: TestClient) -> None:
    # Printable ASCII, so the API accepts it; blastp 2.17.0 can't read it (divergence 8).
    job = run(client, "1234567890", ["A10E"])

    assert job["status"] == "failed"
    assert job["result"] is None
    assert job["error"]["status"] == 422
    assert job["error"]["detail"].startswith("The sequence can't be read as a protein sequence.")
    assert "BLAST" not in job["error"]["detail"]
    assert "/" not in job["error"]["detail"]
