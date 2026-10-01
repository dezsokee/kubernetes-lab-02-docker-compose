"""API tests against a real PostgreSQL.

Point ``SNIPBOX_DATABASE_URL`` at a throwaway database, for example:

    docker run --rm -d --name snipbox-test-db -p 55432:5432 \
      -e POSTGRES_USER=snipbox -e POSTGRES_PASSWORD=snipbox postgres:18-alpine
    SNIPBOX_DATABASE_URL=postgresql://snipbox:snipbox@localhost:55432/snipbox pytest

Every test starts from an empty ``snippets`` table.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    "SNIPBOX_DATABASE_URL" not in os.environ,
    reason="SNIPBOX_DATABASE_URL is not set",
)


def fresh_app():
    for name in [m for m in sys.modules if m.startswith("app")]:
        del sys.modules[name]
    from app.main import app

    return app


@pytest.fixture
def client():
    with TestClient(fresh_app()) as test_client:
        from app import db

        with db.connect().connection() as conn:
            conn.execute("TRUNCATE snippets")
        yield test_client


def test_health_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["snippets"] == 0
    assert "snipbox:" not in response.json()["db"]  # no credentials leaked


def test_create_then_read_snippet(client):
    created = client.post("/snippets", json={"content": "print(1)", "language": "python"})
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "untitled"
    assert len(body["id"]) == 8

    fetched = client.get(f"/snippets/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_list_and_delete(client):
    ids = [
        client.post("/snippets", json={"content": f"snippet {i}"}).json()["id"]
        for i in range(3)
    ]
    listed = client.get("/snippets", params={"limit": 2})
    assert listed.status_code == 200
    assert listed.json()["total"] == 3
    assert len(listed.json()["items"]) == 2

    assert client.delete(f"/snippets/{ids[0]}").status_code == 204
    assert client.delete(f"/snippets/{ids[0]}").status_code == 404
    assert client.get(f"/snippets/{ids[0]}").status_code == 404


def test_empty_content_is_rejected(client):
    assert client.post("/snippets", json={"content": ""}).status_code == 422


def test_data_survives_a_restart(client):
    """A fresh app process, on the same database, still has the snippet."""
    snippet_id = client.post("/snippets", json={"content": "keep me"}).json()["id"]

    with TestClient(fresh_app()) as second:
        assert second.get(f"/snippets/{snippet_id}").json()["content"] == "keep me"
