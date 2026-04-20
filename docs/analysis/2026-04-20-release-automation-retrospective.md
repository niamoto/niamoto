# Release Automation Retrospective

## Summary

The `v0.15.5` release exposed a mismatch between the documented release flow,
the `niamoto-release` skill, and the GitHub Actions pipeline that actually ran
in production.

The most important conclusion is simple:

- the skill was not fundamentally wrong about the desired release flow
- the repository drifted away from that flow
- the drift concentrated the failure modes in the worst possible place:
  right at publish time

This document records the concrete problems, their causes, and the new release
contract that should keep future releases boring.

## Problems Encountered

### 1. Release fan-out did not trigger reliably

The repository had moved to a model where `build-binaries.yml` created the
GitHub Release from inside Actions with `softprops/action-gh-release`.

That meant the release-triggered workflows (`publish-pypi.yml` and
`build-tauri.yml`) depended on a release object created by another workflow,
not by the local release operator. In practice, the expected downstream
fan-out did not happen consistently during `v0.15.5`.

The symptom was confusing:

- the tag existed
- a release eventually existed
- but the workflows that were supposed to run on `release: published` did not
  all behave like a locally published release

### 2. The skill had drifted from the repo

The original release plan expected a local `gh release create` step.
The current skill had later been edited to assume that `build-binaries.yml`
would create the release automatically after tag push.

That drift made the skill internally coherent but externally wrong:

- it waited for a tag-driven release to appear
- it told the operator not to create the release manually
- it no longer matched the intended architecture from the original plan

The skill also still referenced `scripts/build/publish.sh`, which no longer
exists in the repository. That is a second, independent drift signal.

### 3. macOS signing secrets were wrong

The first macOS failures were not build failures. They were Apple signing
configuration failures:

- wrong `APPLE_CERTIFICATE_PASSWORD`
- wrong certificate identity at one point
- then a `.p12` export format that `security import` did not accept in CI

This was painful because each fix attempt required a full macOS runner roundtrip
before the next real failure became visible.

### 4. The macOS bundle structure was not release-safe

Once certificate import worked, the next failures came from the packaged Python
runtime inside the Tauri app:

- sidecar Mach-O binaries were not all signed
- `Python.framework` needed explicit handling
- the final bundled layout flattened framework symlinks in a way that broke
  strict verification and notarization

The durable fix was not “more retries” or “more secrets”, but a post-build
repair/finalization step that understands the real bundle layout.

### 5. The release finalizer contract was incomplete

After the macOS finalizer existed, the release workflow still failed because
the contract between CI and the finalizer was incomplete:

- the downloaded `.app` path was not resolved robustly
- the updater signer did not receive an explicit private key path
- the updater signer did not receive an explicit password

Those were not conceptual release problems. They were contract bugs between the
workflow and the finalization script.

## Root Causes

### Primary root cause

The primary root cause was **release orchestration drift**:

- the intended source of truth was a local release cut followed by CI fan-out
- the actual source of truth became a tag push plus a release created from CI
- the skill and the docs were not updated consistently when that changed

### Secondary root cause

The secondary root cause was **insufficiently codified macOS finalization**:

- signing and notarization logic lived across workflow steps and ad hoc fixes
- the final bundle layout assumptions were not encoded as a reusable script soon
  enough

## New Release Contract

The release flow is now intentionally explicit:

1. A local operator or release skill runs `scripts/build/niamoto_release.py`
2. That script:
   - inspects Git state
   - proposes or accepts a version
   - runs preflight checks
   - updates `CHANGELOG.md`
   - bumps all version files
   - commits and tags the release
   - pushes `main`
   - pushes the tag
   - creates the GitHub Release with `gh release create`
3. GitHub Actions reacts to that published release:
   - `publish-pypi.yml` publishes PyPI
   - `build-tauri.yml` publishes desktop artifacts
   - `build-binaries.yml` uploads CLI archives to the already-existing release

This contract removes the ambiguous handoff where CI was both consumer and
creator of the release object.

## Hardening Added

The release path is now supported by dedicated scripts:

- `scripts/build/niamoto_release.py`
- `scripts/dev/verify_macos_distribution.sh`
- `scripts/build/finalize_macos_release.sh`

This matters because the fragile parts are now:

- versioned
- reviewable
- locally runnable
- testable

instead of being spread across skill prose and workflow folklore.

## Remaining Risks

The release process is materially better, but not completely risk-free.

The main remaining operational dependencies are:

- valid Apple signing secrets
- valid Tauri updater signing secrets
- GitHub CLI authentication for the local operator
- PyPI Trusted Publisher configuration

These are external prerequisites, not release logic bugs, and should fail much
earlier and more legibly than before.

## Recommendation

Treat `scripts/build/niamoto_release.py` as the durable entrypoint and keep the
skill thin.

The skill should:

- inspect state when no version is provided
- surface the suggested version
- run the script with `--yes` once confirmed

The skill should not re-encode the full release pipeline inline unless the
script is unavailable.
