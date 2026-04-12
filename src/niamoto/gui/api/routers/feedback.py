"""Feedback proxy endpoints for the GUI."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter()

_FORWARD_TIMEOUT = 30.0


def _normalize_worker_feedback_url(worker_url: str) -> str:
    normalized = worker_url.strip().rstrip("/")
    if not normalized:
        raise HTTPException(
            status_code=400, detail="Feedback endpoint not configured in this build."
        )

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid feedback endpoint URL.")

    return f"{normalized}/feedback"


async def _forward_feedback(
    worker_feedback_url: str,
    api_key: str,
    payload: str,
    screenshot: UploadFile | None,
) -> tuple[int, dict[str, Any]]:
    files: list[tuple[str, tuple[str | None, Any, str | None]]] = [
        ("payload", (None, payload, None))
    ]

    if screenshot is not None:
        content = await screenshot.read()
        files.append(
            (
                "screenshot",
                (
                    screenshot.filename or "feedback.jpg",
                    content,
                    screenshot.content_type or "application/octet-stream",
                ),
            )
        )

    try:
        async with httpx.AsyncClient(timeout=_FORWARD_TIMEOUT) as client:
            response = await client.post(
                worker_feedback_url,
                headers={"X-Feedback-Key": api_key},
                files=files,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Feedback relay failed: {exc}",
        ) from exc

    try:
        body = response.json()
    except json.JSONDecodeError:
        body = {"error": response.text or "unknown"}

    if not isinstance(body, dict):
        body = {"data": body}

    return response.status_code, body


@router.post("/submit")
async def submit_feedback(
    payload: str = Form(...),
    worker_url: str = Form(...),
    api_key: str = Form(...),
    screenshot: UploadFile | None = File(None),
):
    if not api_key.strip():
        raise HTTPException(
            status_code=400, detail="Feedback API key not configured in this build."
        )

    worker_feedback_url = _normalize_worker_feedback_url(worker_url)
    status_code, body = await _forward_feedback(
        worker_feedback_url=worker_feedback_url,
        api_key=api_key.strip(),
        payload=payload,
        screenshot=screenshot,
    )
    return JSONResponse(status_code=status_code, content=body)
