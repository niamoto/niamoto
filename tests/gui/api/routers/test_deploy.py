"""Contract tests for deploy router endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

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
    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
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
        headers={"x-niamoto-desktop-token": "desktop-secret"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to save credential to keyring"


def test_save_credential_rejects_missing_desktop_auth_configuration(monkeypatch):
    saved_calls = []

    monkeypatch.delenv("NIAMOTO_DESKTOP_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._check_platform", lambda _: None
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.CredentialService.save",
        lambda platform, key, value: saved_calls.append((platform, key, value)) or True,
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/deploy/credentials/cloudflare",
        json={"key": "api_token", "value": "secret"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Desktop auth token is not configured."
    assert saved_calls == []


def test_delete_credential_returns_500_when_keyring_delete_fails(monkeypatch):
    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._check_platform", lambda _: None
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.CredentialService.delete",
        lambda platform, key: False,
    )

    client = TestClient(create_app())
    response = client.delete(
        "/api/deploy/credentials/cloudflare/api_token",
        headers={"x-niamoto-desktop-token": "desktop-secret"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to delete credential from keyring"


def test_save_credential_requires_desktop_auth_when_configured(monkeypatch):
    saved_calls = []

    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._check_platform", lambda _: None
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.CredentialService.save",
        lambda platform, key, value: saved_calls.append((platform, key, value)),
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/deploy/credentials/cloudflare",
        json={"key": "api_token", "value": "secret"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid desktop auth token."
    assert saved_calls == []


def test_save_credential_accepts_desktop_auth_token(monkeypatch):
    saved_calls = []

    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._check_platform", lambda _: None
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.CredentialService.save",
        lambda platform, key, value: saved_calls.append((platform, key, value)) or True,
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/deploy/credentials/cloudflare",
        json={"key": "api_token", "value": "secret"},
        headers={"x-niamoto-desktop-token": "desktop-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"saved": True}
    assert saved_calls == [("cloudflare", "api_token", "secret")]


def test_delete_credential_requires_desktop_auth_when_configured(monkeypatch):
    delete_calls = []

    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._check_platform", lambda _: None
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.CredentialService.delete",
        lambda platform, key: delete_calls.append((platform, key)) or True,
    )

    client = TestClient(create_app())
    response = client.delete("/api/deploy/credentials/cloudflare/api_token")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid desktop auth token."
    assert delete_calls == []


def test_delete_credential_accepts_desktop_auth_token(monkeypatch):
    delete_calls = []

    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._check_platform", lambda _: None
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.CredentialService.delete",
        lambda platform, key: delete_calls.append((platform, key)) or True,
    )

    client = TestClient(create_app())
    response = client.delete(
        "/api/deploy/credentials/cloudflare/api_token",
        headers={"x-niamoto-desktop-token": "desktop-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
    assert delete_calls == [("cloudflare", "api_token")]


def test_check_credentials_requires_desktop_auth_when_configured(monkeypatch):
    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._check_platform", lambda _: None
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.CredentialService.has_credentials",
        lambda platform: True,
    )

    client = TestClient(create_app())
    response = client.get("/api/deploy/credentials/cloudflare/check")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid desktop auth token."


def test_validate_credentials_requires_desktop_auth_when_configured(monkeypatch):
    validate_calls = []

    async def fake_validate(platform):
        validate_calls.append(platform)
        return {"valid": True}

    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy._check_platform", lambda _: None
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.CredentialService.validate",
        fake_validate,
    )

    client = TestClient(create_app())
    response = client.post("/api/deploy/credentials/cloudflare/validate")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid desktop auth token."
    assert validate_calls == []


def test_execute_requires_desktop_auth_when_configured(monkeypatch, tmp_path):
    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.get_working_directory",
        lambda: tmp_path,
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/deploy/execute",
        json={"platform": "netlify", "project_name": "niamoto-site"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid desktop auth token."


def test_validate_exports_requires_desktop_auth_when_configured(monkeypatch, tmp_path):
    validate_calls = []

    class FakeDeployer:
        def validate_exports(self, config):
            validate_calls.append(config)
            return []

    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
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
        "/api/deploy/validate",
        json={"platform": "netlify", "project_name": "niamoto-site"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid desktop auth token."
    assert validate_calls == []


def test_unpublish_requires_desktop_auth_when_configured(monkeypatch):
    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")

    client = TestClient(create_app())
    response = client.post(
        "/api/deploy/unpublish",
        json={"platform": "render", "project_name": "niamoto-site"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid desktop auth token."


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
    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
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
        json={
            "platform": "vercel",
            "project_name": "niamoto-site",
            "extra": {"service_id": "svc-123"},
        },
        headers={"x-niamoto-desktop-token": "desktop-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"valid": False, "errors": ["missing index.html"]}
    assert fake_deployer.received_config is not None
    assert fake_deployer.received_config.platform == "vercel"
    assert fake_deployer.received_config.project_name == "niamoto-site"
    assert fake_deployer.received_config.exports_dir == exports_dir
    assert fake_deployer.received_config.extra == {"service_id": "svc-123"}


def test_execute_returns_error_stream_for_preflight_failures(monkeypatch, tmp_path):
    exports_dir = tmp_path / "exports" / "web"
    exports_dir.mkdir(parents=True)

    class FakeDeployer:
        def validate_exports(self, config):
            return ["manifest.json missing", "index.html missing"]

    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
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
        headers={"x-niamoto-desktop-token": "desktop-secret"},
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
    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
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
        headers={"x-niamoto-desktop-token": "desktop-secret"},
    )

    assert response.status_code == 200
    assert "data: removing deployment" in response.text
    assert fake_deployer.received_config is not None
    assert str(fake_deployer.received_config.exports_dir) == "."


def test_health_rejects_private_url_without_outbound_request(monkeypatch):
    class FailingAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            raise AssertionError("health check should reject before HTTP client use")

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.httpx.AsyncClient",
        FailingAsyncClient,
    )

    client = TestClient(create_app())
    response = client.get("/api/deploy/health", params={"url": "http://127.0.0.1"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Health check URL is not allowed."


def test_health_checks_public_url_with_mocked_client(monkeypatch):
    class FakeResponse:
        status_code = 200
        content = b"ok"
        text = "ok"
        headers = {}
        url = "https://example.com"

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(
        "niamoto.gui.api.url_security.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.httpx.AsyncClient",
        FakeAsyncClient,
    )

    client = TestClient(create_app())
    response = client.get("/api/deploy/health", params={"url": "https://example.com"})

    assert response.status_code == 200
    assert response.json()["status"] == "up"
    assert response.json()["statusCode"] == 200


def test_health_revalidates_url_immediately_before_request(monkeypatch):
    requested_urls = []
    resolved_ips = ["93.184.216.34", "127.0.0.1"]

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            requested_urls.append(url)
            raise AssertionError("private rebound URL should be rejected before GET")

    def fake_getaddrinfo(*args, **kwargs):
        return [(None, None, None, None, (resolved_ips.pop(0), 80))]

    monkeypatch.setattr(
        "niamoto.gui.api.url_security.socket.getaddrinfo",
        fake_getaddrinfo,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.httpx.AsyncClient",
        FakeAsyncClient,
    )

    response = TestClient(create_app()).get(
        "/api/deploy/health", params={"url": "http://example.com"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Health check URL is not allowed."
    assert requested_urls == []


def test_health_rejects_redirect_to_private_url(monkeypatch):
    class FakeResponse:
        status_code = 302
        content = b""
        text = ""
        headers = {"location": "http://127.0.0.1/admin"}
        url = "https://example.com"

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(
        "niamoto.gui.api.url_security.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.httpx.AsyncClient",
        FakeAsyncClient,
    )

    client = TestClient(create_app())
    response = client.get("/api/deploy/health", params={"url": "https://example.com"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Health check redirect URL is not allowed."


@pytest.mark.parametrize(
    "meta_tag",
    [
        '<meta content="0; url=/missing" http-equiv="refresh">',
        "<meta http-equiv='refresh' content='0; URL=\"/missing\"'>",
    ],
)
def test_health_follows_meta_refresh_variants(monkeypatch, meta_tag):
    class FakeResponse:
        def __init__(self, status_code, text, url):
            self.status_code = status_code
            self.text = text
            self.content = text.encode("utf-8")
            self.headers = {}
            self.url = url

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.calls = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            self.calls.append(url)
            if url == "https://example.com":
                return FakeResponse(200, meta_tag, url)
            return FakeResponse(404, "missing", url)

    monkeypatch.setattr(
        "niamoto.gui.api.url_security.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.deploy.httpx.AsyncClient",
        FakeAsyncClient,
    )

    response = TestClient(create_app()).get(
        "/api/deploy/health", params={"url": "https://example.com"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "down"
    assert response.json()["statusCode"] == 404
