import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_parse_txt(client, tmp_path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("Hello world. This is a test.", encoding="utf-8")
    with path.open("rb") as handle:
        response = client.post("/api/v1/documents/parse", files={"file": ("note.txt", handle, "text/plain")})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["filename"] == "note.txt"
    assert payload["sentence_count"] >= 1


def test_unsupported_file_type(client, tmp_path) -> None:
    path = tmp_path / "image.png"
    path.write_bytes(b"png")
    with path.open("rb") as handle:
        response = client.post("/api/v1/documents/parse", files={"file": ("image.png", handle, "image/png")})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "UNSUPPORTED_FILE_TYPE"
    assert "PDF" in body["message"]


def test_comparison_not_found(client) -> None:
    response = client.get("/api/v1/comparisons/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"] == "COMPARISON_NOT_FOUND"


def test_comparison_history_contract(client) -> None:
    response = client.get("/api/v1/comparisons?limit=5&offset=0")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["limit"] == 5
    assert payload["offset"] == 0
    assert isinstance(payload["items"], list)
    if payload["items"]:
        item = payload["items"][0]
        assert {"comparison_id", "created_at", "old_document", "new_document", "summary"} <= item.keys()


def test_upload_fetch_and_explore_comparison(client) -> None:
    old_text = b"Revenue was $10 million. The deadline is March 15, 2026."
    new_text = b"Revenue was $15 million. The deadline is April 30, 2026."
    response = client.post(
        "/api/v1/comparisons",
        files={
            "old_file": ("report_v1.txt", old_text, "text/plain"),
            "new_file": ("report_v2.txt", new_text, "text/plain"),
        },
    )
    assert response.status_code == 200, response.text
    created = response.json()
    comparison_id = created["comparison_id"]
    assert created["summary"]["numerical_changes"] == 1
    assert created["summary"]["temporal_changes"] == 1

    detail = client.get(f"/api/v1/comparisons/{comparison_id}")
    changes = client.get(f"/api/v1/comparisons/{comparison_id}/changes")
    summary = client.get(f"/api/v1/comparisons/{comparison_id}/summary")
    history = client.get("/api/v1/comparisons?limit=20&offset=0")
    assert detail.status_code == changes.status_code == summary.status_code == history.status_code == 200
    assert detail.json()["comparison_id"] == comparison_id
    assert len(changes.json()) == summary.json()["total_changes"]
    assert any(item["comparison_id"] == comparison_id for item in history.json()["items"])
