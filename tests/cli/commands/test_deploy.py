from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from niamoto.cli.commands.deploy import deploy_commands


class TestDeployCommand:
    def test_platforms_subcommand_lists_available_platforms(self) -> None:
        runner = CliRunner()

        with patch(
            "niamoto.cli.commands.deploy._get_available_platforms",
            return_value=["cloudflare", "github"],
        ):
            result = runner.invoke(deploy_commands, ["platforms"])

        assert result.exit_code == 0
        assert "Available deployment platforms" in result.output
        assert "cloudflare" in result.output
        assert "github" in result.output

    def test_default_deploy_uses_config_and_cli_overrides(self, tmp_path) -> None:
        runner = CliRunner()
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()
        (exports_dir / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")

        fake_config = MagicMock()
        fake_config.get_deploy_config = {
            "platform": "render",
            "project_name": "from-config",
            "branch": "preview",
            "extra": {
                "service_id": "svc-config",
                "region": "eu-central-1",
            },
        }
        fake_config.get_export_config = {"web": str(exports_dir)}

        fake_deployer = MagicMock()
        fake_deployer.validate_exports.return_value = []
        fake_run_deploy = AsyncMock(return_value=None)

        with patch("niamoto.cli.commands.deploy.Config", return_value=fake_config):
            with patch(
                "niamoto.cli.commands.deploy._get_deployer",
                return_value=fake_deployer,
            ):
                with patch("niamoto.cli.commands.deploy._run_deploy", fake_run_deploy):
                    result = runner.invoke(
                        deploy_commands,
                        [
                            "--project",
                            "from-cli",
                            "-e",
                            "service_id",
                            "svc-cli",
                        ],
                    )

        assert result.exit_code == 0
        fake_deployer.validate_exports.assert_called_once()
        fake_run_deploy.assert_called_once()

        deploy_config = fake_run_deploy.call_args.args[1]
        assert deploy_config.platform == "render"
        assert deploy_config.project_name == "from-cli"
        assert deploy_config.branch == "preview"
        assert deploy_config.extra == {
            "service_id": "svc-cli",
            "region": "eu-central-1",
        }
        assert "Deploying to render (project: from-cli)" in result.output

    def test_default_deploy_surfaces_preflight_validation_errors(
        self, tmp_path
    ) -> None:
        runner = CliRunner()
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()
        (exports_dir / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")

        fake_config = MagicMock()
        fake_config.get_deploy_config = {
            "platform": "cloudflare",
            "project_name": "niamoto-site",
            "extra": {},
        }
        fake_config.get_export_config = {"web": str(exports_dir)}

        fake_deployer = MagicMock()
        fake_deployer.validate_exports.return_value = [
            "No index.html found in export directory"
        ]

        with patch("niamoto.cli.commands.deploy.Config", return_value=fake_config):
            with patch(
                "niamoto.cli.commands.deploy._get_deployer",
                return_value=fake_deployer,
            ):
                result = runner.invoke(deploy_commands)

        assert result.exit_code != 0
        assert "No index.html found in export directory" in result.output
        assert "Pre-flight validation failed" in result.output
