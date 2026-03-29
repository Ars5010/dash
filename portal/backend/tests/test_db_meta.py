from __future__ import annotations


def test_meta_status(client):
    r = client.get("/api/v1/meta/status")
    assert r.status_code == 200
    body = r.json()
    assert "bootstrapped" in body
