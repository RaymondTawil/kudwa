import os
import json
import pathlib
import pytest

# Test mode: 'live' (default) or 'inproc' for different test environments
TEST_MODE = os.getenv("TEST_MODE", "live")  # live | inproc
# Base URL for API requests
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def test_data_dir() -> pathlib.Path:
    """
    Pytest fixture to provide the path to the test data directory.
    Raises an error if the directory or required files are missing.
    """
    p = pathlib.Path("test_data")
    if not p.exists():
        raise RuntimeError("Expected test_data/ with data_set_1.json and data_set_2.json")
    return p


@pytest.fixture(scope="session")
def ensure_ingested(test_data_dir):
    """
    Pytest fixture to ensure test data is ingested into the API before tests run.
    Posts QuickBooks and Rootfi datasets to the API and asserts success.
    Returns the API responses for both ingests.
    """
    import requests

    # Load test datasets
    qb_json = json.loads((test_data_dir / "data_set_1.json").read_text())
    rf_json = json.loads((test_data_dir / "data_set_2.json").read_text())

    def _post(path, payload):
        return requests.post(f"{BASE_URL}{path}", json={"payload": payload}, timeout=30)

    r1 = _post("/ingest/quickbooks", qb_json)
    assert r1.status_code == 200, r1.text
    r2 = _post("/ingest/rootfi", rf_json)
    assert r2.status_code == 200, r2.text
    return {"qb": r1.json(), "rf": r2.json()}