import json
from pathlib import Path

import requests


def load_sample_trace():
    trace_path = Path(__file__).parent.parent / "assets" / "sample_trace.json"
    with open(trace_path) as f:
        return json.load(f)


BASE_URL = "http://localhost:8000/api/v1"
REPO_URL = "https://github.com/NickKuts/capture_flow"


def test_store_traces_and_generate_mr():
    sample_trace_1 = load_sample_trace()
    sample_trace_2 = load_sample_trace()

    # Store
    response_1 = requests.post(
        f"{BASE_URL}/traces", params={"repository-url": REPO_URL}, json=sample_trace_1
    )
    assert response_1.status_code == 200
    assert response_1.json()["message"] == "Trace log saved successfully"

    # Store
    response_2 = requests.post(
        f"{BASE_URL}/traces", params={"repository-url": REPO_URL}, json=sample_trace_2
    )
    assert response_2.status_code == 200
    assert response_2.json()["message"] == "Trace log saved successfully"

    # Generate
    response_mr = requests.post(
        f"{BASE_URL}/merge-requests", params={"repository-url": REPO_URL}
    )
    assert response_mr.status_code == 200
    assert response_mr.json()["message"] == "MR generation process started successfully"


if __name__ == "__main__":
    test_store_traces_and_generate_mr()
