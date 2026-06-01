"""Tests for the mobile integration doc endpoints."""
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def test_version_endpoint_no_auth_required():
    r = requests.get(f"{BASE_URL}/api/mobile/integration-doc/version", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) >= {"version", "sha256", "last_modified", "doc_url"}
    assert len(body["sha256"]) == 64
    assert len(body["version"]) == 12
    assert body["doc_url"] == "/api/mobile/integration-doc"


def test_json_endpoint_returns_full_body():
    r = requests.get(f"{BASE_URL}/api/mobile/integration-doc", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["content"].startswith("# TNWG Encampment Hub")
    assert body["content_length"] == len(body["content"])
    assert "Recent Backend Changes" in body["content"]


def test_markdown_endpoint_returns_raw_md_with_headers():
    r = requests.get(
        f"{BASE_URL}/api/mobile/integration-doc?format=markdown",
        timeout=10,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.headers["x-doc-version"]
    assert len(r.headers["x-doc-sha256"]) == 64
    assert r.text.startswith("# TNWG Encampment Hub")


def test_version_matches_full_doc_sha():
    v = requests.get(f"{BASE_URL}/api/mobile/integration-doc/version", timeout=10).json()
    f = requests.get(f"{BASE_URL}/api/mobile/integration-doc", timeout=10).json()
    assert v["sha256"] == f["sha256"]
    assert v["last_modified"] == f["last_modified"]
