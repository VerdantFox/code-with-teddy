# Spec 0002: Update GitHub Actions Pipeline

**Status:** Complete

---

## Overview

Update the project's GitHub Actions CI workflow (`run-full-ci.yml`) to use correct Python and Node.js versions, the latest action versions, the official `astral-sh/setup-uv` action with caching, and improved security via top-level permission restrictions, SHA pinning, and a concurrency group.

### Acceptance Criteria

- All three CI jobs (`lint`, `test`, `release`) pass successfully after the changes.
- Both the `lint` and `test` jobs use Python 3.14.
- The `lint` job uses Node.js 22.
- All actions are pinned to their full commit SHA with the version tag as an inline comment.
- `astral-sh/setup-uv` with `enable-cache: true` replaces all manual `pip install uv` steps.
- Workflow-level `permissions: read-all` is present.
- A `concurrency` group is configured to cancel in-progress runs on the same ref.

---

## Research

### Current Workflow State and Issues

The `run-full-ci.yml` workflow has several issues:

1. **Wrong Python versions**: lint uses 3.12, test uses 3.11; project requires ≥3.14.
2. **Outdated action versions**: `checkout@v4`, `setup-python@v5`, `setup-node@v4`.
3. **Manual uv install**: `pip install uv` with no cache — slow CI on every run.
4. **Inconsistent venv strategy**: lint job creates and activates a venv; test job uses `--system`.
5. **Old Node.js version**: Node 20 is maintenance LTS; Node 22 is the current active LTS.
6. **No workflow-level `permissions`**: all jobs have implicit broad permissions.
7. **No concurrency group**: redundant pushes waste CI minutes.

### Action Version Inventory

| Action                 | Current | Latest     | Notes                                      |
| ---------------------- | ------- | ---------- | ------------------------------------------ |
| `actions/checkout`     | v4      | **v6.0.2** | v5 and v6 both released since v4.          |
| `actions/setup-python` | v5      | **v6.2.0** | v6 is a breaking change (Node 24 runtime). |
| `actions/setup-node`   | v4      | **v6.4.0** | v5 and v6 both released since v4.          |
| `pre-commit/action`    | v3.0.1  | **v3.0.1** | Already at latest.                         |

### Python and Node.js Versions

Python 3.14 (released October 7, 2025; latest 3.14.4) is the project target per `pyproject.toml` (`requires-python = ">=3.14"`) and `ty.toml` (`python-version = "3.14"`). Both the `lint` and `test` jobs must use Python 3.14. Python 3.11 (test job) and 3.12 (lint job) are now security-only releases.

Node.js 22 is the current active LTS. Node.js 20 (used in the lint job) is in maintenance LTS as of May 2026.

### uv GitHub Actions Best Practices

The official Astral documentation recommends `astral-sh/setup-uv` (latest: v8.1.0) instead of `pip install uv`. It automatically adds uv to PATH, supports built-in package caching via `enable-cache: true`, and eliminates the need for manual venv creation.

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v8
  with:
    enable-cache: true
```

### GitHub Actions Security Best Practices

**Minimal permissions**: Add `permissions: read-all` at the workflow level to restrict `GITHUB_TOKEN` to read-only. The `release` job already has `permissions: contents: write` which continues to override this.

**SHA pinning**: Pin third-party actions to their full commit SHA to prevent supply chain attacks from mutable version tags. Keep the version tag as an inline comment for readability.

**Concurrency groups**: Cancel in-progress runs when a new push arrives on the same ref.

### SHA Reference

| Action                 | Target Version | Commit SHA                                 |
| ---------------------- | -------------- | ------------------------------------------ |
| `actions/checkout`     | v6.0.2         | `de0fac2e4500dabe0009e67214ff5f5447ce83dd` |
| `actions/setup-python` | v6.2.0         | `a309ff8b426b58ec0e2a45f0f869d46889d02405` |
| `actions/setup-node`   | v6.4.0         | `48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e` |
| `pre-commit/action`    | v3.0.1         | `2c7b3805fd2a0fd8c1884dcaebf91fc102a13ecd` |
| `astral-sh/setup-uv`   | v8.1.0         | `08807647e7069bb48b6ef5acd8ec9567f424441b` |

SHAs verified via the GitHub API (`/repos/{owner}/{repo}/git/ref/tags/{tag}`).

---

## Plan

### Approach

Update `.github/workflows/run-full-ci.yml` in place with all changes applied together: bump action versions, correct Python/Node versions, replace the manual uv install with `astral-sh/setup-uv`, add SHA pinning, add workflow-level `permissions: read-all`, and add a concurrency group.

### Files to Modify

| File                                | Change                   |
| ----------------------------------- | ------------------------ |
| `.github/workflows/run-full-ci.yml` | All CI pipeline changes. |

### Implementation Details

#### Workflow-level additions

```yaml
permissions: read-all

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

#### `lint` job

- `actions/checkout`: `@v4` → SHA-pinned `@v6.0.2`
- `actions/setup-python`: `@v5`, `python-version: "3.12"` → SHA-pinned `@v6.2.0`, `python-version: "3.14"`
- `actions/setup-node`: `@v4`, `node-version: 20` → SHA-pinned `@v6.4.0`, `node-version: 22`
- Replace manual `pip install uv` + `uv venv` + `source venv/bin/activate` with `astral-sh/setup-uv@v8.1.0` with `enable-cache: true`
- Install dependencies with `uv pip install -r requirements-dev.txt --system` (no venv needed)
- `pre-commit/action@v3.0.1`: no version change, but pin to SHA

#### `test` job

- `actions/checkout`: `@v4` → SHA-pinned `@v6.0.2`
- `actions/setup-python`: `@v5`, `python-version: "3.11"` → SHA-pinned `@v6.2.0`, `python-version: "3.14"`; update step name to "Set up Python 3.14"
- Replace `pip install uv` step with `astral-sh/setup-uv@v8.1.0` with `enable-cache: true`
- Keep `uv pip install -r requirements-dev.txt --system`

#### `release` job

- `actions/checkout`: `@v4` → SHA-pinned `@v6.0.2`
- No other changes needed

### Testing Approach

No Python code is changing. Post-implementation validation is manual: run `pre-commit run --all-files` locally to confirm the YAML is valid, then push to a branch and verify all three jobs (`lint`, `test`, `release`) pass in CI.

### Trade-offs and Considerations

| Change                         | Risk     | Notes                                                                                         |
| ------------------------------ | -------- | --------------------------------------------------------------------------------------------- |
| Python 3.11/3.12 → 3.14        | Medium   | Project already targets 3.14, but CI may expose previously hidden issues. Tests pass locally. |
| `actions/checkout` v4 → v6     | Low      | Breaking change in v6 is credentials storage location; doesn't affect this workflow.          |
| `actions/setup-python` v5 → v6 | Low      | v6 breaking change is Node 24 runtime upgrade — transparent to Python consumers.              |
| `actions/setup-node` v4 → v6   | Low      | v6 breaking change limits auto-caching to npm only — this workflow doesn't rely on it.        |
| `astral-sh/setup-uv` adoption  | Low      | Well-maintained official action from Astral. Simplifies setup.                                |
| `permissions: read-all`        | Very Low | Only affects `GITHUB_TOKEN` scope. Release job keeps its explicit `contents: write` override. |
| Concurrency group              | Very Low | Only cancels in-progress runs when a new push arrives. Does not affect final push results.    |
| Node 20 → 22                   | Low      | Used only for Tailwind CSS / npm tooling in pre-commit. No breaking changes expected.         |
| SHA pinning                    | Very Low | Increases security; no functional change.                                                     |

---

## Open Questions

[No open questions.]

---

## Tasks

### Phase 1 — Pre-work Verification

- [x] Review the current workflow file end-to-end to catch any additional issues
- [x] Verify Python 3.14 is available on `ubuntu-latest` GitHub-hosted runners
- [x] Verify `astral-sh/setup-uv@v8` is the correct latest major version
- [x] Confirm Node 22 is the current active LTS
- [x] Look up and record commit SHAs for all five actions

### Phase 2 — Workflow-Level Changes

- [x] Add top-level `permissions: read-all` block
- [x] Add `concurrency` block

### Phase 3 — `lint` Job

- [x] Update `actions/checkout` to SHA-pinned `@v6.0.2`
- [x] Update `actions/setup-python` to SHA-pinned `@v6.2.0` and `python-version: "3.14"`
- [x] Update `actions/setup-node` to SHA-pinned `@v6.4.0` and `node-version: 22`
- [x] Replace manual uv install steps with `astral-sh/setup-uv@v8.1.0` with `enable-cache: true`
- [x] Update dependency install to use `--system` (no venv)
- [x] Pin `pre-commit/action` to its SHA

### Phase 4 — `test` Job

- [x] Update `actions/checkout` to SHA-pinned `@v6.0.2`
- [x] Update `actions/setup-python` to SHA-pinned `@v6.2.0`, `python-version: "3.14"`, and step name
- [x] Replace `pip install uv` with `astral-sh/setup-uv@v8.1.0` with `enable-cache: true`

### Phase 5 — `release` Job

- [x] Update `actions/checkout` to SHA-pinned `@v6.0.2`

### Phase 6 — Post-work Validation

> **Note:** Remote validation steps are performed manually by the developer, not by the AI.

- [x] Run `pre-commit run --all-files` locally to confirm nothing broke
- [x] Commit and push to trigger CI
- [x] Verify all three jobs (`lint`, `test`, `release`) pass in CI
- [x] Confirm Python 3.14 appears in CI logs
- [x] Confirm uv cache hits on subsequent runs
- [x] Confirm concurrency group cancels in-progress runs when a new push arrives

---

## Implementation

### Implementation Log

All changes applied to `.github/workflows/run-full-ci.yml` in a single pass. No deviations from the plan. SHA values were verified against the GitHub API before pinning.
