from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers.feedback import _normalize_worker_feedback_url


def test_normalize_worker_feedback_url_appends_submit_path(monkeypatch):
    monkeypatch.setattr(
        "niamoto.gui.api.url_security.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )

    assert (
        _normalize_worker_feedback_url("https://feedback.example.com/")
        == "https://feedback.example.com/feedback"
    )


def test_normalize_worker_feedback_url_rejects_invalid_values():
    try:
        _normalize_worker_feedback_url("notaurl")
    except Exception as exc:
        assert exc.status_code == 400
        assert exc.detail == "Invalid feedback endpoint URL."
    else:
        raise AssertionError("invalid feedback URL was accepted")


def test_normalize_worker_feedback_url_rejects_private_targets():
    for worker_url in (
        "http://127.0.0.1:8787",
        "http://localhost:8787",
        "http://169.254.169.254",
        "http://10.0.0.1",
    ):
        try:
            _normalize_worker_feedback_url(worker_url)
        except Exception as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError(f"private feedback URL was accepted: {worker_url}")


def test_submit_feedback_proxies_to_worker(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "niamoto.gui.api.url_security.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    monkeypatch.setenv("NIAMOTO_FEEDBACK_WORKER_URL", "https://feedback.example.com")
    monkeypatch.setenv("NIAMOTO_FEEDBACK_API_KEY", "secret")

    async def fake_forward_feedback(
        worker_feedback_url: str,
        api_key: str,
        payload: str,
        screenshot,
    ):
        captured["worker_feedback_url"] = worker_feedback_url
        captured["api_key"] = api_key
        captured["payload"] = payload
        captured["filename"] = None if screenshot is None else screenshot.filename
        return 201, {"success": True, "screenshot_uploaded": True}

    monkeypatch.setattr(
        "niamoto.gui.api.routers.feedback._forward_feedback",
        fake_forward_feedback,
    )

    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/feedback/submit",
        data={
            "payload": '{"type":"bug","title":"Broken widget"}',
            "worker_url": "http://127.0.0.1:8787",
            "api_key": "attacker-secret",
        },
        files={"screenshot": ("feedback.jpg", b"binary-image", "image/jpeg")},
    )

    assert response.status_code == 201
    assert response.json() == {"success": True, "screenshot_uploaded": True}
    assert captured == {
        "worker_feedback_url": "https://feedback.example.com/feedback",
        "api_key": "secret",
        "payload": '{"type":"bug","title":"Broken widget"}',
        "filename": "feedback.jpg",
    }


def test_submit_feedback_rejects_private_configured_worker(monkeypatch):
    forwarded = False
    monkeypatch.setenv("NIAMOTO_FEEDBACK_WORKER_URL", "http://127.0.0.1:8787")
    monkeypatch.setenv("NIAMOTO_FEEDBACK_API_KEY", "secret")

    async def fake_forward_feedback(*_args, **_kwargs):
        nonlocal forwarded
        forwarded = True
        return 201, {"success": True}

    monkeypatch.setattr(
        "niamoto.gui.api.routers.feedback._forward_feedback",
        fake_forward_feedback,
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/feedback/submit",
        data={"payload": '{"type":"bug","title":"Broken widget"}'},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Feedback endpoint URL is not allowed."
    assert forwarded is False
