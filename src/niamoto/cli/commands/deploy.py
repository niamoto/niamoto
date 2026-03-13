"""
Commands for deploying generated content to various platforms.

Uses deployer plugins from the PluginRegistry. Configuration can come from:
- deploy.yml (project config, CI/CD friendly)
- CLI arguments (override deploy.yml values)
- OS keyring (credentials)
"""

import asyncio
import os

import click

from niamoto.common.config import Config
from niamoto.common.exceptions import CommandError
from niamoto.common.utils import error_handler
from ..utils.console import print_success, print_info, print_error, print_warning


def _ensure_deployer_plugins():
    """Import deployer plugin modules so they register via @register."""
    import niamoto.core.plugins.deployers.cloudflare  # noqa: F401
    import niamoto.core.plugins.deployers.github  # noqa: F401
    import niamoto.core.plugins.deployers.netlify  # noqa: F401
    import niamoto.core.plugins.deployers.vercel  # noqa: F401
    import niamoto.core.plugins.deployers.render  # noqa: F401
    import niamoto.core.plugins.deployers.ssh  # noqa: F401


def _get_available_platforms() -> list[str]:
    """Return list of registered deployer platform names."""
    _ensure_deployer_plugins()
    from niamoto.core.plugins.base import PluginType
    from niamoto.core.plugins.registry import PluginRegistry

    return list(PluginRegistry.get_plugins_by_type(PluginType.DEPLOYER).keys())


def _get_deployer(platform: str):
    """Get a deployer plugin instance by name."""
    _ensure_deployer_plugins()
    from niamoto.core.plugins.base import PluginType
    from niamoto.core.plugins.registry import PluginRegistry

    if not PluginRegistry.has_plugin(platform, PluginType.DEPLOYER):
        available = list(PluginRegistry.get_plugins_by_type(PluginType.DEPLOYER).keys())
        raise CommandError(
            command="deploy",
            message=f"Unknown platform: {platform}",
            details={"available": available},
        )
    deployer_class = PluginRegistry.get_plugin(platform, PluginType.DEPLOYER)
    return deployer_class()


@click.group(name="deploy", invoke_without_command=True)
@click.option(
    "--platform",
    "-p",
    type=str,
    help="Deployment platform (cloudflare, github, netlify, vercel, render, ssh).",
)
@click.option(
    "--project",
    type=str,
    help="Project name for the deployment.",
)
@click.option(
    "--branch",
    "-b",
    type=str,
    default=None,
    help="Branch name (optional, platform-specific behavior).",
)
@click.option(
    "--extra",
    "-e",
    type=(str, str),
    multiple=True,
    help="Extra platform-specific config as key=value pairs. E.g. -e repo user/repo",
)
@click.pass_context
@error_handler(log=True, raise_error=True)
def deploy_commands(ctx, platform, project, branch, extra):
    """Deploy generated content to hosting platforms.

    Reads defaults from deploy.yml if present. CLI arguments override config values.

    \b
    Examples:
      niamoto deploy                                    # uses deploy.yml
      niamoto deploy -p cloudflare --project my-site    # override platform
      niamoto deploy -p github -e repo user/repo        # with extra config
      niamoto deploy platforms                           # list available platforms
      niamoto deploy credentials cloudflare              # manage credentials
    """
    # If a subcommand is invoked, skip the default deploy action
    if ctx.invoked_subcommand is not None:
        return

    # --- Merge config: deploy.yml defaults + CLI overrides ---
    config = Config()
    deploy_config = config.get_deploy_config

    effective_platform = platform or deploy_config.get("platform")
    effective_project = project or deploy_config.get("project_name")
    effective_branch = branch or deploy_config.get("branch")
    effective_extra = dict(deploy_config.get("extra", {}))

    # CLI --extra pairs override yaml extra
    for key, value in extra:
        effective_extra[key] = value

    # --- Validate required fields ---
    if not effective_platform:
        available = _get_available_platforms()
        raise CommandError(
            command="deploy",
            message="No platform specified. Use --platform or set it in deploy.yml.",
            details={"available_platforms": available},
        )

    if not effective_project:
        raise CommandError(
            command="deploy",
            message="No project name specified. Use --project or set project_name in deploy.yml.",
        )

    # --- Resolve export directory ---
    output_dir = config.get_export_config.get("web")
    if not output_dir or not os.path.exists(output_dir):
        raise CommandError(
            command="deploy",
            message="Export directory not found. Run 'niamoto export' first.",
            details={"output_dir": output_dir},
        )

    # --- Get deployer and run ---
    deployer = _get_deployer(effective_platform)

    from niamoto.core.plugins.deployers.models import DeployConfig
    from pathlib import Path

    deploy_cfg = DeployConfig(
        platform=effective_platform,
        exports_dir=Path(output_dir),
        project_name=effective_project,
        branch=effective_branch,
        extra=effective_extra,
    )

    # Pre-flight validation
    errors = deployer.validate_exports(deploy_cfg)
    if errors:
        for err in errors:
            print_error(err)
        raise CommandError(
            command="deploy",
            message="Pre-flight validation failed",
            details={"errors": errors},
        )

    print_info(f"Deploying to {effective_platform} (project: {effective_project})...")

    # Run the async deploy and stream output to console
    asyncio.run(_run_deploy(deployer, deploy_cfg))


async def _run_deploy(deployer, config):
    """Run deployer and print SSE lines to console."""
    async for line in deployer.deploy(config):
        # Parse SSE format: "data: MESSAGE\n\n"
        text = line.strip()
        if not text.startswith("data: "):
            continue
        message = text[6:]  # Strip "data: "

        if message == "DONE":
            break
        elif message.startswith("ERROR: "):
            print_error(message[7:])
        elif message.startswith("SUCCESS: "):
            print_success(message[9:])
        elif message.startswith("URL: "):
            print_success(f"URL: {message[5:]}")
        else:
            print_info(message)


# --- Subcommands ---


@deploy_commands.command(name="platforms")
def list_platforms():
    """List available deployment platforms."""
    platforms = _get_available_platforms()
    print_info("Available deployment platforms:")
    for p in platforms:
        print_info(f"  - {p}")


@deploy_commands.group(name="credentials")
def credentials_group():
    """Manage deployment credentials stored in OS keyring."""
    pass


@credentials_group.command(name="set")
@click.argument("platform")
@click.argument("key")
@click.argument("value")
@error_handler(log=True, raise_error=True)
def credentials_set(platform: str, key: str, value: str):
    """Save a credential to the OS keyring.

    \b
    Examples:
      niamoto deploy credentials set cloudflare api-token sk-xxx
      niamoto deploy credentials set cloudflare account-id abc123
      niamoto deploy credentials set github token ghp_xxx
    """
    from niamoto.core.services.credential import CredentialService

    success = CredentialService.save(platform, key, value)
    if success:
        print_success(f"Saved {platform}/{key} to keyring")
    else:
        print_error(f"Failed to save {platform}/{key}")


@credentials_group.command(name="check")
@click.argument("platform")
@error_handler(log=True, raise_error=True)
def credentials_check(platform: str):
    """Check configured credentials for a platform.

    \b
    Examples:
      niamoto deploy credentials check cloudflare
      niamoto deploy credentials check github
    """
    from niamoto.core.services.credential import CredentialService

    has_creds = CredentialService.has_credentials(platform)
    masked = CredentialService.get_all_for_platform(platform)

    if has_creds:
        print_success(f"{platform}: credentials configured")
        for key, val in masked.items():
            print_info(f"  {key}: {val}")
    else:
        print_warning(f"{platform}: missing credentials")
        for key, val in masked.items():
            status = val if val else "NOT SET"
            print_info(f"  {key}: {status}")


@credentials_group.command(name="validate")
@click.argument("platform")
@error_handler(log=True, raise_error=True)
def credentials_validate(platform: str):
    """Validate credentials by making a test API call.

    \b
    Examples:
      niamoto deploy credentials validate cloudflare
      niamoto deploy credentials validate github
    """
    from niamoto.core.services.credential import CredentialService

    result = asyncio.run(CredentialService.validate(platform))
    if result.get("valid"):
        user = result.get("user", "")
        print_success(f"{platform}: token valid ({user})")
    else:
        error = result.get("error", "Unknown error")
        print_error(f"{platform}: {error}")


@credentials_group.command(name="delete")
@click.argument("platform")
@click.argument("key")
@error_handler(log=True, raise_error=True)
def credentials_delete(platform: str, key: str):
    """Delete a credential from the OS keyring.

    \b
    Examples:
      niamoto deploy credentials delete cloudflare api-token
    """
    from niamoto.core.services.credential import CredentialService

    success = CredentialService.delete(platform, key)
    if success:
        print_success(f"Deleted {platform}/{key} from keyring")
    else:
        print_warning(f"Credential {platform}/{key} not found or already deleted")
