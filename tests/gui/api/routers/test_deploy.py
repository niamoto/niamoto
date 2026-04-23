"""Contract tests for deploy router endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


def test_list_platforms_returns_registered_platforms(monkeypatch):
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._get_supported_platforms",
        lambda: ["cloudflare", "vercel"],
    )

    client = TestClient(create_app())
    response = client.get("/api/deploy/platforms")

    assert response.status_code == 200
    assert response.json() == {"platforms": ["cloudflare", "vercel"]}


def test_save_credential_returns_500_when_keyring_write_fails(monkeypatch):
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._check_platform", lambda _: None
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.CredentialService.save",
        lambda platform, key, value: False,
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/deploy/credentials/cloudflare",
        json={"key": "api_token", "value": "secret"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to save credential to keyring"


def test_validate_exports_returns_errors_without_starting_deploy(monkeypatch, tmp_path):
    exports_dir = tmp_path / "exports" / "web"
    exports_dir.mkdir(parents=True)

    class FakeDeployer:
        def __init__(self):
            self.received_config = None

        def validate_exports(self, config):
            self.received_config = config
            return ["missing index.html"]

    fake_deployer = FakeDeployer()
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.get_working_directory",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._get_deployer",
        lambda platform: fake_deployer,
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/deploy/validate",
        json={"platform": "vercel", "project_name": "niamoto-site"},
    )

    assert response.status_code == 200
    assert response.json() == {"valid": False, "errors": ["missing index.html"]}
    assert fake_deployer.received_config is not None
    assert fake_deployer.received_config.platform == "vercel"
    assert fake_deployer.received_config.project_name == "niamoto-site"
    assert fake_deployer.received_config.exports_dir == exports_dir


def test_execute_returns_error_stream_for_preflight_failures(monkeypatch, tmp_path):
    exports_dir = tmp_path / "exports" / "web"
    exports_dir.mkdir(parents=True)

    class FakeDeployer:
        def validate_exports(self, config):
            return ["manifest.json missing", "index.html missing"]

    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.get_working_directory",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._get_deployer",
        lambda platform: FakeDeployer(),
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/deploy/execute",
        json={"platform": "netlify", "project_name": "niamoto-site"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data: ERROR: manifest.json missing" in response.text
    assert "data: ERROR: index.html missing" in response.text
    assert response.text.rstrip().endswith("data: DONE")


def test_unpublish_streams_deployer_output_without_working_directory(monkeypatch):
    class FakeDeployer:
        def __init__(self):
            self.received_config = None

        async def unpublish(self, config):
            self.received_config = config
            yield "data: removing deployment\n\n"
            yield "data: DONE\n\n"

    fake_deployer = FakeDeployer()
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.get_working_directory",
        lambda: None,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._get_deployer",
        lambda platform: fake_deployer,
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/deploy/unpublish",
        json={"platform": "render", "project_name": "niamoto-site"},
    )

    assert response.status_code == 200
    assert "data: removing deployment" in response.text
    assert fake_deployer.received_config is not None
    assert str(fake_deployer.received_config.exports_dir) == "."
