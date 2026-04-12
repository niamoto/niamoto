from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers.feedback import _normalize_worker_feedback_url


def test_normalize_worker_feedback_url_appends_submit_path():
    assert (
        _normalize_worker_feedback_url("https://feedback.example.com/")
        == "https://feedback.example.com/feedback"
    )


def test_normalize_worker_feedback_url_rejects_invalid_values():
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/feedback/submit",
        data={
            "payload": "{}",
            "worker_url": "notaurl",
            "api_key": "secret",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid feedback endpoint URL."


def test_submit_feedback_proxies_to_worker(monkeypatch):
    captured = {}

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
            "worker_url": "https://feedback.example.com",
            "api_key": "secret",
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
