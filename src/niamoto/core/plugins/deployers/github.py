"""GitHub Pages deployer plugin using Git Data API (no git binary required)."""

import asyncio
import base64
import logging
import os
from typing import AsyncIterator

import httpx

from niamoto.core.plugins.base import DeployerPlugin, register
from .models import DeployConfig
from niamoto.core.services.credential import CredentialService

logger = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"


@register("github")
class GitHubDeployer(DeployerPlugin):
    """Deploy static sites to GitHub Pages via the Git Data API."""

    platform = "github"

    async def deploy(self, config: DeployConfig) -> AsyncIterator[str]:
        """Deploy files to GitHub Pages.

        Flow:
        1. Authenticate and parse repo info
        2. Ensure branch exists (create orphan if needed)
        3. Upload all files as blobs (parallel, semaphore-limited)
        4. Create tree from blob SHAs
        5. Create commit pointing to tree
        6. Update branch ref to new commit
        """
        # --- Credentials ---
        token = CredentialService.get("github", "token")
        if not token:
            yield self.sse_error(
                "No GitHub token configured. Use credentials settings to add one."
            )
            yield self.sse_done()
            return

        # --- Parse config ---
        repo_slug = config.extra.get("repo")
        if not repo_slug or "/" not in repo_slug:
            yield self.sse_error(
                f"Invalid repo format: '{repo_slug}'. Expected 'owner/repo'."
            )
            yield self.sse_done()
            return

        owner, repo = repo_slug.split("/", 1)
        branch = config.extra.get("branch", "gh-pages")

        yield self.sse_log(f"Deploying to {owner}/{repo} (branch: {branch})")

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Niamoto-Deploy",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient(
            base_url=BASE_URL, headers=headers, timeout=60.0
        ) as client:
            # --- Ensure branch exists ---
            parent_sha, err = await self._ensure_branch(client, owner, repo, branch)
            if parent_sha is None:
                yield self.sse_error(err or f"Failed to initialise branch '{branch}'.")
                yield self.sse_done()
                return

            yield self.sse_log(f"Branch '{branch}' ready (tip: {parent_sha[:8]})")

            # --- Collect files ---
            exports_dir = config.exports_dir
            file_paths: list[tuple[str, str]] = []  # (relative_path, absolute_path)
            for root, _dirs, files in os.walk(exports_dir):
                for fname in files:
                    abs_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(abs_path, exports_dir)
                    file_paths.append((rel_path, abs_path))

            if not file_paths:
                yield self.sse_error("No files found in export directory.")
                yield self.sse_done()
                return

            total = len(file_paths)
            yield self.sse_log(f"Found {total} files to upload")

            # --- Upload blobs (parallel with semaphore) ---
            semaphore = asyncio.Semaphore(10)
            tree_entries: list[dict] = []
            uploaded = 0
            errors: list[str] = []
            lock = asyncio.Lock()

            async def upload_blob(rel_path: str, abs_path: str) -> None:
                nonlocal uploaded
                try:
                    with open(abs_path, "rb") as f:
                        content_b64 = base64.b64encode(f.read()).decode("ascii")

                    async with semaphore:
                        resp = await client.post(
                            f"/repos/{owner}/{repo}/git/blobs",
                            json={"content": content_b64, "encoding": "base64"},
                        )
                        resp.raise_for_status()
                        blob_sha = resp.json()["sha"]

                    # Use forward slashes for git paths
                    git_path = rel_path.replace("\\", "/")
                    async with lock:
                        tree_entries.append(
                            {
                                "path": git_path,
                                "mode": "100644",
                                "type": "blob",
                                "sha": blob_sha,
                            }
                        )
                        uploaded += 1
                except Exception as exc:
                    async with lock:
                        errors.append(f"{rel_path}: {exc}")

            # Launch all uploads
            tasks = [upload_blob(rel, abs_p) for rel, abs_p in file_paths]

            # Process in batches so we can yield progress
            batch_size = 20
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i : i + batch_size]
                await asyncio.gather(*batch)
                yield self.sse_log(f"Uploading files: {uploaded}/{total}")

            if errors:
                for err in errors[:5]:
                    yield self.sse_error(f"Upload failed: {err}")
                if len(errors) > 5:
                    yield self.sse_error(f"...and {len(errors) - 5} more errors")
                yield self.sse_done()
                return

            # --- Create tree ---
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

            # --- Create commit ---
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

            # --- Update ref ---
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

            url = f"https://{owner}.github.io/{repo}"
            yield self.sse_success(f"Deployed to GitHub Pages ({commit_sha[:8]})")
            yield self.sse_url(url)
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
        branch = config.extra.get("branch", "gh-pages")

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
    async def _ensure_branch(
        client: httpx.AsyncClient, owner: str, repo: str, branch: str
    ) -> tuple[str | None, str | None]:
        """Ensure the target branch exists.

        Returns (tip_commit_sha, None) on success, or (None, error_message) on failure.
        """
        # Check if repo exists first
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

        # Check if repo is empty (no commits yet)
        repo_data = repo_resp.json()
        if repo_data.get("size", 0) == 0:
            # Initialize the repo with a README via the Contents API
            # (Git Data API doesn't work on empty repos)
            try:
                import base64 as b64mod

                init_resp = await client.put(
                    f"/repos/{owner}/{repo}/contents/README.md",
                    json={
                        "message": "Initial commit",
                        "content": b64mod.b64encode(
                            f"# {repo}\n\nDeployed with Niamoto.\n".encode()
                        ).decode("ascii"),
                    },
                )
                init_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 422:  # 422 = file already exists
                    detail = exc.response.text[:300]
                    return None, f"Failed to initialize empty repo: {detail}"

        ref_url = f"/repos/{owner}/{repo}/git/refs/heads/{branch}"

        # Check if branch already exists
        resp = await client.get(ref_url)
        if resp.status_code == 200:
            return resp.json()["object"]["sha"], None

        # Branch does not exist — create orphan branch
        try:
            # Create a placeholder blob (.nojekyll) — GitHub rejects empty trees
            blob_resp = await client.post(
                f"/repos/{owner}/{repo}/git/blobs",
                json={"content": "", "encoding": "utf-8"},
            )
            blob_resp.raise_for_status()
            blob_sha = blob_resp.json()["sha"]

            # Create a tree with the placeholder file
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

            # Create an initial commit with no parents (orphan)
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

            # Create the ref
            create_ref_resp = await client.post(
                f"/repos/{owner}/{repo}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": initial_sha},
            )
            create_ref_resp.raise_for_status()

            return initial_sha, None
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300]
            logger.error("Failed to create orphan branch '%s': %s", branch, detail)
            return None, f"GitHub API error ({exc.response.status_code}): {detail}"
