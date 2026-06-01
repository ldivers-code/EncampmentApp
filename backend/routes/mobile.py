"""Mobile integration endpoints.

Exposes the markdown source of `MOBILE_BACKEND_INTEGRATION.md` so the
mobile team can fetch the latest spec programmatically (e.g. from CI) and
detect changes via the `version` hash without needing to clone the repo.

The doc is loaded from disk on every request — the file is small (<60 KB)
so we don't bother caching. A future revision can add an in-memory cache
keyed on the file's mtime if traffic grows.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Response

from database import api_router, ROOT_DIR


# Resolve once at import time. ROOT_DIR is `/app/backend`; the doc lives
# at the repo root `/app/MOBILE_BACKEND_INTEGRATION.md`.
_DOC_PATH = Path(ROOT_DIR).parent / "MOBILE_BACKEND_INTEGRATION.md"


def _read_doc() -> tuple[str, str, str]:
    """Return (markdown_body, sha256_hex, iso_last_modified)."""
    if not _DOC_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Mobile integration doc is not available on this server.",
        )
    body = _DOC_PATH.read_text(encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    mtime = datetime.fromtimestamp(
        _DOC_PATH.stat().st_mtime, tz=timezone.utc
    ).isoformat()
    return body, digest, mtime


@api_router.get("/mobile/integration-doc/version")
def mobile_integration_doc_version():
    """Lightweight polling endpoint: returns just the hash + mtime so the
    mobile team's CI can cheaply check for changes without downloading
    the full markdown body.

    Public (no auth) — the document only describes the public API surface
    and contains no secrets.
    """
    _, digest, mtime = _read_doc()
    return {
        "version": digest[:12],   # short, human-readable
        "sha256": digest,
        "last_modified": mtime,
        "doc_url": "/api/mobile/integration-doc",
    }


@api_router.get("/mobile/integration-doc")
def mobile_integration_doc(format: Optional[str] = "json"):
    """Returns the mobile integration spec.

    Query params:
      - `format=json` (default): returns `{version, sha256, last_modified, content}`.
      - `format=markdown`: returns the raw markdown body with
        `Content-Type: text/markdown` — convenient for piping into editors
        or CI diff tools (`curl ... > spec.md`).

    Public (no auth).
    """
    body, digest, mtime = _read_doc()

    if (format or "").lower() in ("md", "markdown", "text"):
        return Response(
            content=body,
            media_type="text/markdown; charset=utf-8",
            headers={
                "X-Doc-Version": digest[:12],
                "X-Doc-SHA256": digest,
                "X-Doc-Last-Modified": mtime,
                # Mobile CI may cache aggressively; let them control freshness.
                "Cache-Control": "public, max-age=300",
            },
        )

    return {
        "version": digest[:12],
        "sha256": digest,
        "last_modified": mtime,
        "content": body,
        "content_length": len(body),
        "format": "markdown",
    }
