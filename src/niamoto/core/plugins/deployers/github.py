"""GitHub Pages deployer with git transport and API fallback."""

import asyncio
import base64
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import quote

import httpx

from niamoto.core.plugins.base import DeployerPlugin, register
from niamoto.core.services.credential import CredentialService
from .models import DeployConfig

logger = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"
GITHUB_API_SAFE_FILE_LIMIT = 400
GITHUB_API_WRITE_DELAY_SECONDS = 1.0
DEFAULT_GIT_AUTHOR_NAME = "Niamoto Deploy"
DEFAULT_GIT_AUTHOR_EMAIL = "deploy@niamoto.local"


@register("github")
class GitHubDeployer(DeployerPlugin):
    """Deploy static sites to GitHub Pages.

    Prefer the local git transport when available because GitHub's content
    creation limits make the REST Git Data API unsuitable for large sites.
    """

    platform = "github"

    async def deploy(self, config: DeployConfig) -> AsyncIterator[str]:
        """Deploy files to GitHub Pages."""
        token = CredentialService.get("github", "token")
        if not token:
            yield self.sse_error(
                "No GitHub token configured. Use credentials settings to add one."
            )
            yield self.sse_done()
            return

        repo_slug = config.extra.get("repo")
        if not repo_slug or "/" not in repo_slug:
            yield self.sse_error(
                f"Invalid repo format: '{repo_slug}'. Expected 'owner/repo'."
            )
            yield self.sse_done()
            return

        owner, repo = repo_slug.split("/", 1)
        branch = str(config.branch or config.extra.get("branch") or "gh-pages")

        yield self.sse_log(f"Deploying to {owner}/{repo} (branch: {branch})")

        file_paths = self._collect_export_files(config.exports_dir)
        if not file_paths:
            yield self.sse_error("No files found in export directory.")
            yield self.sse_done()
            return

        total = len(file_paths)
        yield self.sse_log(f"Found {total} files to upload")

        git_binary = shutil.which("git")
        if git_binary:
            async for line in self._deploy_with_git(
                config=config,
                owner=owner,
                repo=repo,
                branch=branch,
                token=token,
                git_binary=git_binary,
            ):
                yield line
            return

        if total > GITHUB_API_SAFE_FILE_LIMIT:
            yield self.sse_error(
                "Git is not available on this system, and the GitHub API fallback "
                f"is limited to about {GITHUB_API_SAFE_FILE_LIMIT} files to avoid "
                "GitHub content-creation rate limits. Install Git or use another "
                "deployment platform for this site."
            )
            yield self.sse_done()
            return

        yield self.sse_log("Git not found; using the slower GitHub API fallback.")
        async for line in self._deploy_with_api(
            config=config,
            owner=owner,
            repo=repo,
            branch=branch,
            token=token,
            file_paths=file_paths,
        ):
            yield line

    async def _deploy_with_git(
        self,
        config: DeployConfig,
        owner: str,
        repo: str,
        branch: str,
        token: str,
        git_binary: str,
    ) -> AsyncIterator[str]:
        """Deploy by fetching the target branch, replacing exported files, and pushing."""
        yield self.sse_log("Using local git transport for GitHub Pages.")

        try:
            with tempfile.TemporaryDirectory(
                prefix="niamoto-github-pages-"
            ) as temp_dir:
                temp_root = Path(temp_dir)
                repo_dir = temp_root / "repo"
                credential_file = temp_root / "github-credentials"
                repo_dir.mkdir()

                yield self.sse_log("Preparing temporary deployment repository...")
                await self._run_git(git_binary, "init", cwd=repo_dir)
                await self._run_git(
                    git_binary,
                    "config",
                    "user.name",
                    self._get_git_author_name(config),
                    cwd=repo_dir,
                )
                await self._run_git(
                    git_binary,
                    "config",
                    "user.email",
                    self._get_git_author_email(config),
                    cwd=repo_dir,
                )
                await self._run_git(
                    git_binary,
                    "config",
                    "credential.helper",
                    f"store --file={credential_file}",
                    cwd=repo_dir,
                )
                await self._run_git(
                    git_binary,
                    "config",
                    "credential.useHttpPath",
                    "true",
                    cwd=repo_dir,
                )

                self._configure_git_credentials(credential_file, owner, repo, token)
                remote_url = self._get_git_remote_url(owner, repo)
                await self._run_git(
                    git_binary, "remote", "add", "origin", remote_url, cwd=repo_dir
                )

                branch_exists = await self._remote_branch_exists(
                    git_binary, repo_dir, branch
                )
                if branch_exists:
                    yield self.sse_log(f"Fetching existing branch '{branch}'...")
                    await self._run_git(
                        git_binary,
                        "fetch",
                        "--depth",
                        "1",
                        "origin",
                        branch,
                        cwd=repo_dir,
                    )
                    await self._run_git(
                        git_binary,
                        "checkout",
                        "-B",
                        branch,
                        "FETCH_HEAD",
                        cwd=repo_dir,
                    )
                    self._clear_worktree(repo_dir)
                else:
                    yield self.sse_log(f"Creating deployment branch '{branch}'...")
                    await self._run_git(
                        git_binary, "checkout", "--orphan", branch, cwd=repo_dir
                    )

                yield self.sse_log("Copying exported site files...")
                self._copy_exports(config.exports_dir, repo_dir)
                self._ensure_nojekyll(repo_dir)

                await self._run_git(git_binary, "add", "--all", cwd=repo_dir)
                if not await self._has_staged_changes(git_binary, repo_dir):
                    current_sha = await self._rev_parse_short(git_binary, repo_dir)
                    yield self.sse_success(
                        f"GitHub Pages already up to date ({current_sha})"
                    )
                    yield self.sse_url(self._get_pages_url(owner, repo))
                    yield self.sse_done()
                    return

                yield self.sse_log("Creating deployment commit...")
                await self._run_git(
                    git_binary,
                    "commit",
                    "-m",
                    f"Deploy {config.project_name}",
                    cwd=repo_dir,
                )
                commit_sha = await self._rev_parse_short(git_binary, repo_dir)

                yield self.sse_log(
                    f"Pushing branch '{branch}' to GitHub. This can take a moment..."
                )
                await self._run_git(
                    git_binary,
                    "push",
                    "--progress",
                    "origin",
                    f"HEAD:refs/heads/{branch}",
                    cwd=repo_dir,
                )

                yield self.sse_success(f"Deployed to GitHub Pages ({commit_sha})")
                yield self.sse_url(self._get_pages_url(owner, repo))
                yield self.sse_done()
        except RuntimeError as exc:
            yield self.sse_error(str(exc))
            yield self.sse_done()

    async def _deploy_with_api(
        self,
        config: DeployConfig,
        owner: str,
        repo: str,
        branch: str,
        token: str,
        file_paths: list[tuple[str, str]],
    ) -> AsyncIterator[str]:
        """Deploy via the GitHub Git Data API for smaller sites."""
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Niamoto-Deploy",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient(
            base_url=BASE_URL, headers=headers, timeout=60.0
        ) as client:
            parent_sha, err = await self._ensure_branch(client, owner, repo, branch)
            if parent_sha is None:
                yield self.sse_error(err or f"Failed to initialise branch '{branch}'.")
                yield self.sse_done()
                return

            yield self.sse_log(f"Branch '{branch}' ready (tip: {parent_sha[:8]})")

            tree_entries: list[dict] = []
            total = len(file_paths)

            for index, (rel_path, abs_path) in enumerate(file_paths, start=1):
                try:
                    with open(abs_path, "rb") as f:
                        content_b64 = base64.b64encode(f.read()).decode("ascii")

                    resp = await client.post(
                        f"/repos/{owner}/{repo}/git/blobs",
                        json={"content": content_b64, "encoding": "base64"},
                    )
                    resp.raise_for_status()
                    blob_sha = resp.json()["sha"]
                except httpx.HTTPStatusError as exc:
                    detail = exc.response.text[:200] or str(exc)
                    yield self.sse_error(f"Upload failed: {rel_path}: {detail}")
                    yield self.sse_done()
                    return
                except OSError as exc:
                    yield self.sse_error(f"Upload failed: {rel_path}: {exc}")
                    yield self.sse_done()
                    return

                tree_entries.append(
                    {
                        "path": rel_path.replace("\\", "/"),
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_sha,
                    }
                )

                if index % 20 == 0 or index == total:
                    yield self.sse_log(f"Uploading files: {index}/{total}")

                if index < total:
                    await asyncio.sleep(GITHUB_API_WRITE_DELAY_SECONDS)

            yield self.sse_log("Creating file tree...")
            try:
                tree_resp = await client.post(
                    f"/repos/{owner}/{repo}/git/trees",
                    json={"tree": tree_entries},
                )
                tree_resp.raise_for_status()
                tree_sha = tree_resp.json()["sha"]
            except httpx.HTTPStatusError as exc:
                yield self.sse_error(
                    f"Failed to create tree: {exc.response.text[:200]}"
                )
                yield self.sse_done()
                return

            yield self.sse_log("Creating commit...")
            try:
                commit_resp = await client.post(
                    f"/repos/{owner}/{repo}/git/commits",
                    json={
                        "message": f"Deploy {config.project_name}",
                        "tree": tree_sha,
                        "parents": [parent_sha],
                    },
                )
                commit_resp.raise_for_status()
                commit_sha = commit_resp.json()["sha"]
            except httpx.HTTPStatusError as exc:
                yield self.sse_error(
                    f"Failed to create commit: {exc.response.text[:200]}"
                )
                yield self.sse_done()
                return

            yield self.sse_log("Updating branch reference...")
            try:
                ref_resp = await client.patch(
                    f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
                    json={"sha": commit_sha},
                )
                ref_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                yield self.sse_error(f"Failed to update ref: {exc.response.text[:200]}")
                yield self.sse_done()
                return

            yield self.sse_success(f"Deployed to GitHub Pages ({commit_sha[:8]})")
            yield self.sse_url(self._get_pages_url(owner, repo))
            yield self.sse_done()

    async def unpublish(self, config: DeployConfig) -> AsyncIterator[str]:
        """Remove GitHub Pages by deleting the deployment branch."""
        token = CredentialService.get("github", "token")
        if not token:
            yield self.sse_error("No GitHub token configured.")
            yield self.sse_done()
            return

        repo_slug = config.extra.get("repo")
        if not repo_slug or "/" not in repo_slug:
            yield self.sse_error(f"Invalid repo format: '{repo_slug}'.")
            yield self.sse_done()
            return

        owner, repo = repo_slug.split("/", 1)
        branch = str(config.branch or config.extra.get("branch") or "gh-pages")

        yield self.sse_log(f"Deleting branch '{branch}' from {owner}/{repo}...")

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Niamoto-Deploy",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient(
            base_url=BASE_URL, headers=headers, timeout=30.0
        ) as client:
            resp = await client.delete(f"/repos/{owner}/{repo}/git/refs/heads/{branch}")

            if resp.status_code == 204:
                yield self.sse_success(
                    f"Branch '{branch}' deleted. GitHub Pages will be disabled."
                )
            elif resp.status_code == 404:
                yield self.sse_error(f"Branch '{branch}' not found.")
            else:
                yield self.sse_error(
                    f"Failed to delete branch: HTTP {resp.status_code} — {resp.text[:200]}"
                )

        yield self.sse_done()

    @staticmethod
    def _collect_export_files(exports_dir: Path) -> list[tuple[str, str]]:
        """Return export files as (relative_path, absolute_path) pairs."""
        file_paths: list[tuple[str, str]] = []
        for root, _dirs, files in os.walk(exports_dir):
            for fname in files:
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, exports_dir)
                file_paths.append((rel_path, abs_path))
        file_paths.sort()
        return file_paths

    @staticmethod
    def _get_git_author_name(config: DeployConfig) -> str:
        """Return the local git author name for deployment commits."""
        return str(config.extra.get("git_user_name") or DEFAULT_GIT_AUTHOR_NAME)

    @staticmethod
    def _get_git_author_email(config: DeployConfig) -> str:
        """Return the local git author email for deployment commits."""
        return str(config.extra.get("git_user_email") or DEFAULT_GIT_AUTHOR_EMAIL)

    @staticmethod
    def _get_git_remote_url(owner: str, repo: str) -> str:
        """Return the HTTPS remote URL for the target GitHub repository."""
        return f"https://github.com/{owner}/{repo}.git"

    @staticmethod
    def _configure_git_credentials(
        credential_file: Path, owner: str, repo: str, token: str
    ) -> None:
        """Write a temporary credential store entry for the deployment remote."""
        encoded_token = quote(token, safe="")
        credential_file.write_text(
            f"https://x-access-token:{encoded_token}@github.com/{owner}/{repo}.git\n",
            encoding="utf-8",
        )
        credential_file.chmod(0o600)

    @staticmethod
    def _clear_worktree(repo_dir: Path) -> None:
        """Delete all files except the git metadata directory."""
        for child in repo_dir.iterdir():
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    @staticmethod
    def _copy_exports(exports_dir: Path, repo_dir: Path) -> None:
        """Copy exported files into the temporary deployment repository."""
        for child in exports_dir.iterdir():
            destination = repo_dir / child.name
            if child.is_dir():
                shutil.copytree(child, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(child, destination)

    @staticmethod
    def _ensure_nojekyll(repo_dir: Path) -> None:
        """Ensure GitHub Pages serves files without Jekyll processing."""
        (repo_dir / ".nojekyll").touch()

    @staticmethod
    def _get_pages_url(owner: str, repo: str) -> str:
        """Return the GitHub Pages URL for the repository."""
        return f"https://{owner}.github.io/{repo}"

    async def _remote_branch_exists(
        self, git_binary: str, repo_dir: Path, branch: str
    ) -> bool:
        """Check whether the target branch already exists on the remote."""
        returncode, _stdout, stderr = await self._run_git(
            git_binary,
            "ls-remote",
            "--exit-code",
            "--heads",
            "origin",
            branch,
            cwd=repo_dir,
            check=False,
        )
        if returncode == 0:
            return True
        if returncode == 2:
            return False
        raise RuntimeError(stderr or f"Failed to inspect remote branch '{branch}'.")

    async def _has_staged_changes(self, git_binary: str, repo_dir: Path) -> bool:
        """Return whether the temporary repository contains staged changes."""
        returncode, _stdout, stderr = await self._run_git(
            git_binary,
            "diff",
            "--cached",
            "--quiet",
            "--exit-code",
            cwd=repo_dir,
            check=False,
        )
        if returncode == 0:
            return False
        if returncode == 1:
            return True
        raise RuntimeError(stderr or "Failed to inspect staged deployment changes.")

    async def _rev_parse_short(self, git_binary: str, repo_dir: Path) -> str:
        """Return the short SHA for the current HEAD."""
        _returncode, stdout, _stderr = await self._run_git(
            git_binary, "rev-parse", "--short", "HEAD", cwd=repo_dir
        )
        return stdout or "unknown"

    async def _run_git(
        self,
        git_binary: str,
        *args: str,
        cwd: Path,
        check: bool = True,
    ) -> tuple[int, str, str]:
        """Run a git command in the temporary deployment repository."""
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        try:
            process = await asyncio.create_subprocess_exec(
                git_binary,
                *args,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except OSError as exc:
            raise RuntimeError(f"Failed to start git: {exc}") from exc

        stdout_data, stderr_data = await process.communicate()
        stdout = stdout_data.decode("utf-8", errors="replace").strip()
        stderr = stderr_data.decode("utf-8", errors="replace").strip()

        if check and process.returncode != 0:
            detail = stderr or stdout or f"git {' '.join(args)} failed"
            raise RuntimeError(detail)

        return process.returncode, stdout, stderr

    @staticmethod
    async def _ensure_branch(
        client: httpx.AsyncClient, owner: str, repo: str, branch: str
    ) -> tuple[str | None, str | None]:
        """Ensure the target branch exists.

        Returns (tip_commit_sha, None) on success, or (None, error_message) on failure.
        """
        repo_resp = await client.get(f"/repos/{owner}/{repo}")
        if repo_resp.status_code == 404:
            return (
                None,
                f"Repository '{owner}/{repo}' not found (404). Create it first on GitHub.",
            )
        if repo_resp.status_code == 403:
            return None, f"Access denied to '{owner}/{repo}'. Check token permissions."
        if repo_resp.status_code != 200:
            return (
                None,
                f"Cannot access repo '{owner}/{repo}': HTTP {repo_resp.status_code}",
            )

        repo_data = repo_resp.json()
        if repo_data.get("size", 0) == 0:
            try:
                init_resp = await client.put(
                    f"/repos/{owner}/{repo}/contents/README.md",
                    json={
                        "message": "Initial commit",
                        "content": base64.b64encode(
                            f"# {repo}\n\nDeployed with Niamoto.\n".encode()
                        ).decode("ascii"),
                    },
                )
                init_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 422:
                    detail = exc.response.text[:300]
                    return None, f"Failed to initialize empty repo: {detail}"

        ref_url = f"/repos/{owner}/{repo}/git/refs/heads/{branch}"
        resp = await client.get(ref_url)
        if resp.status_code == 200:
            return resp.json()["object"]["sha"], None

        try:
            blob_resp = await client.post(
                f"/repos/{owner}/{repo}/git/blobs",
                json={"content": "", "encoding": "utf-8"},
            )
            blob_resp.raise_for_status()
            blob_sha = blob_resp.json()["sha"]

            tree_resp = await client.post(
                f"/repos/{owner}/{repo}/git/trees",
                json={
                    "tree": [
                        {
                            "path": ".nojekyll",
                            "mode": "100644",
                            "type": "blob",
                            "sha": blob_sha,
                        }
                    ]
                },
            )
            tree_resp.raise_for_status()
            init_tree_sha = tree_resp.json()["sha"]

            commit_resp = await client.post(
                f"/repos/{owner}/{repo}/git/commits",
                json={
                    "message": "Initial GitHub Pages commit",
                    "tree": init_tree_sha,
                    "parents": [],
                },
            )
            commit_resp.raise_for_status()
            initial_sha = commit_resp.json()["sha"]

            create_ref_resp = await client.post(
                f"/repos/{owner}/{repo}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": initial_sha},
            )
            create_ref_resp.raise_for_status()

            return initial_sha, None
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300]
            logger.error("Failed to create branch '%s': %s", branch, detail)
            return None, f"GitHub API error ({exc.response.status_code}): {detail}"
