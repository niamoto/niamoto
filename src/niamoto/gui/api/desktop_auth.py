"""Desktop API authentication helpers."""

import os

from fastapi import HTTPException, Request

DESKTOP_TOKEN_HEADER = "x-niamoto-desktop-token"
DESKTOP_AUTH_TOKEN_ENV = "NIAMOTO_DESKTOP_AUTH_TOKEN"


def require_desktop_mutation_auth(request: Request) -> None:
    """Require the desktop token when the GUI API runs behind a desktop shell."""
    expected_token = os.environ.get(DESKTOP_AUTH_TOKEN_ENV)
    if not expected_token:
        return

    provided_token = request.headers.get(DESKTOP_TOKEN_HEADER)
    if provided_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid desktop auth token.")
