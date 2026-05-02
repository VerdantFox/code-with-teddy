# Spec 0002: Update GitHub Actions Pipeline

## Status: Complete

---

## 1. Background & Motivation

The current `run-full-ci.yml` workflow has become outdated in several ways:

- Action versions are significantly behind latest releases
- Python versions are wrong (test job uses 3.11, lint job uses 3.12; project requires ≥3.14)
- uv is installed via `pip install uv` rather than the official `astral-sh/setup-uv` action
- No uv package cache — each run reinstalls all packages from scratch
- Node.js version 20 is behind the current LTS (Node 22)
- No top-level `permissions` restriction (security best practice)
- Inconsistent virtual environment strategy between `lint` and `test` jobs
- No `concurrency` group to cancel redundant runs on the same branch

---

## 2. Research Findings

### 2.1 Action Version Inventory

| Action                 | Current | Latest     | Notes                                     |
| ---------------------- | ------- | ---------- | ----------------------------------------- |
| `actions/checkout`     | v4      | **v6.0.2** | v5 and v6 both released since v4          |
| `actions/setup-python` | v5      | **v6.2.0** | v6 is a breaking change (Node 24 runtime) |
| `actions/setup-node`   | v4      | **v6.4.0** | v5 and v6 both released since v4          |
| `pre-commit/action`    | v3.0.1  | **v3.0.1** | Already at latest                         |

### 2.2 Python Version Status (as of May 2026)

| Version  | Status              | Notes                                                                         |
| -------- | ------------------- | ----------------------------------------------------------------------------- |
| 3.15     | Pre-release         | Planned release October 2026                                                  |
| **3.14** | **Bugfix (active)** | Released October 7, 2025. Latest: 3.14.4 (April 7, 2026). **Project target.** |
| 3.13     | Bugfix              | Released October 7, 2024                                                      |
| 3.12     | Security-only       | Released October 2, 2023 — used in current lint job                           |
| 3.11     | Security-only       | Released October 24, 2022 — used in current test job                          |

The project's `pyproject.toml` declares `requires-python = ">=3.14"`, and `ty.toml` sets `python-version = "3.14"`. Both the `lint` and `test` jobs must use **Python 3.14**.

### 2.3 Node.js LTS Status

Node.js 20 (used in the lint job) is in "maintenance LTS" as of May 2026. Node.js **22** is the current active LTS. The workflow should target Node 22.

### 2.4 uv GitHub Actions Best Practices

The official Astral documentation recommends using the `astral-sh/setup-uv` action instead of manually running `pip install uv`. Benefits:

- Automatically adds uv to PATH
- Built-in uv package **cache** support (`enable-cache: true`) — avoids reinstalling packages on every run
- Cross-platform support
- Version pinning support
- Eliminates the need for `pip install uv` + manual venv creation steps
- Supports setting `UV_SYSTEM_PYTHON: 1` env var to install into the system Python (avoids needing to activate a venv in CI)

Example pattern (from uv docs):

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v8
  with:
    enable-cache: true
```

The latest version of `astral-sh/setup-uv` is **v8** (as of the uv 0.11.8 documentation).

### 2.5 GitHub Actions Security Best Practices

**Minimal permissions principle**: GitHub recommends setting a top-level `permissions: read-all` (or `permissions: {}`) to restrict the default `GITHUB_TOKEN` to read-only, then explicitly grant write permissions only to the specific jobs that need them. Currently only the `release` job has an explicit `permissions` block; the `lint` and `test` jobs implicitly have broad write permissions.

**Action pinning**: GitHub's security guidance recommends pinning actions to full commit SHAs (most secure) or at minimum to a specific major version tag. Using floating tags like `@v4` risks supply chain attacks if a tag is moved. Version tags from trusted/verified publishers (e.g., GitHub's own `actions/` org) are low-risk, but SHA pinning is the gold standard for high-security environments.

**Dependabot for actions**: GitHub recommends enabling Dependabot version updates for GitHub Actions to automatically keep action versions current via PRs.

**Concurrency groups**: Best practice is to add a `concurrency` block to cancel in-progress runs when a new push arrives on the same branch/ref, reducing wasted CI minutes.

### 2.6 Current Workflow Issues Summary

1. **Wrong Python versions**: lint uses 3.12, test uses 3.11; project requires ≥3.14
2. **Outdated action versions**: checkout@v4, setup-python@v5, setup-node@v4
3. **Manual uv install**: `pip install uv` is the old way; no cache means slow CI
4. **Inconsistent venv strategy**: lint job creates and activates a venv; test job uses `--system`. Both should use the same approach.
5. **Old Node.js version**: Node 20 is maintenance LTS; Node 22 is current LTS
6. **No workflow-level `permissions`**: All jobs have implicit broad permissions
7. **No concurrency group**: Redundant pushes waste CI minutes
8. **No uv cache**: Package installation time is not amortized across runs

---

## 3. Update Plan

### Goal

Bring the CI pipeline up to date with current best practices: correct Python/Node versions, latest action versions, proper uv integration with caching, and improved security posture via permission restrictions and a concurrency group.

### Jobs to Update

#### 3.1 `lint` Job

- Update `actions/checkout` from `v4` → `v6`
- Update `actions/setup-python` from `v5` → `v6`, change `python-version` from `"3.12"` → `"3.14"`
- Update `actions/setup-node` from `v4` → `v6`, change `node-version` from `20` → `22`
- Replace the manual `pip install uv` + `uv venv venv` + `source venv/bin/activate` + `uv pip install` pattern with `astral-sh/setup-uv@v8` with `enable-cache: true`
- Use `uv pip install -r requirements-dev.txt --system` (consistent with test job, no venv activation needed)
- `pre-commit/action@v3.0.1` stays as-is (already latest)

#### 3.2 `test` Job

- Update `actions/checkout` (implicit from `pre-commit/action`) — the test job itself doesn't use checkout directly, but add it for clarity and consistency
- Actually: the test job _does_ use `actions/checkout@v4` (via the `uses: actions/checkout@v4` step) — update to `v6`
- Update `actions/setup-python` from `v5` → `v6`, change `python-version` from `"3.11"` → `"3.14"`
- Fix the job name label comment (currently says "Set up Python 3.11" — update to "3.14")
- Replace `pip install uv` + `uv pip install --system` with `astral-sh/setup-uv@v8` + `uv pip install --system` (with cache enabled)

#### 3.3 `release` Job

- Update `actions/checkout` from `v4` → `v6`
- No other changes needed (no Python/Node needed here)

### 3.4 Workflow-Level Changes

- Add `permissions: read-all` at the top of the workflow (before `jobs:`) to restrict the default `GITHUB_TOKEN` to read-only across all jobs. The `release` job already has its own `permissions: contents: write` block which continues to override this.

  ```yaml
  permissions: read-all
  ```

- Add a `concurrency` block to cancel in-progress runs when a new push arrives on the same ref, reducing wasted CI minutes:

  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true
  ```

### 3.5 Action SHA Pinning

GitHub's security guidance recommends pinning third-party actions to their full commit SHA rather than a mutable version tag. This prevents supply chain attacks where a tag is silently moved to malicious code.

For each action used, look up the commit SHA corresponding to the target version tag and pin to it, keeping the version tag as an inline comment for readability:

```yaml
# Example pattern
uses: actions/checkout@<full-commit-sha> # v6.0.2
```

All five actions used in this workflow require SHA pinning:

| Action                 | Target Version | Commit SHA                                 |
| ---------------------- | -------------- | ------------------------------------------ |
| `actions/checkout`     | v6.0.2         | `de0fac2e4500dabe0009e67214ff5f5447ce83dd` |
| `actions/setup-python` | v6.2.0         | `a309ff8b426b58ec0e2a45f0f869d46889d02405` |
| `actions/setup-node`   | v6.4.0         | `48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e` |
| `pre-commit/action`    | v3.0.1         | `2c7b3805fd2a0fd8c1884dcaebf91fc102a13ecd` |
| `astral-sh/setup-uv`   | v8.1.0         | `08807647e7069bb48b6ef5acd8ec9567f424441b` |

SHAs were verified via the GitHub API (`/repos/{owner}/{repo}/git/ref/tags/{tag}`).

---

## 4. Reference: Action Latest Versions

| Action                 | Latest Version | URL                                                |
| ---------------------- | -------------- | -------------------------------------------------- |
| `actions/checkout`     | v6.0.2         | <https://github.com/actions/checkout/releases>     |
| `actions/setup-python` | v6.2.0         | <https://github.com/actions/setup-python/releases> |
| `actions/setup-node`   | v6.4.0         | <https://github.com/actions/setup-node/releases>   |
| `pre-commit/action`    | v3.0.1         | <https://github.com/pre-commit/action/releases>    |
| `astral-sh/setup-uv`   | v8 (v8.1.0)    | <https://github.com/astral-sh/setup-uv/releases>   |

---

## 5. Risk Assessment

| Change                         | Risk Level | Notes                                                                                                                  |
| ------------------------------ | ---------- | ---------------------------------------------------------------------------------------------------------------------- |
| Python 3.11 → 3.14             | Medium     | Project already targets 3.14, but CI may expose previously hidden 3.14-specific issues. Tests pass locally.            |
| `actions/checkout` v4 → v6     | Low        | Breaking change in v6 is credentials storage location; doesn't affect this workflow's use case.                        |
| `actions/setup-python` v5 → v6 | Low        | v6 breaking change is Node 24 runtime upgrade — transparent to Python consumers.                                       |
| `actions/setup-node` v4 → v6   | Low        | v6 breaking change limits automatic caching to npm only — our workflow doesn't rely on automatic caching.              |
| `astral-sh/setup-uv` adoption  | Low        | Well-maintained official action from Astral. Simplifies setup; `--system` flag usage unchanged.                        |
| `permissions: read-all`        | Very Low   | Only affects `GITHUB_TOKEN` scope; this workflow doesn't use it in lint/test. Release job keeps its explicit override. |
| Concurrency group              | Very Low   | Only cancels in-progress runs when a new push arrives. Does not affect final push results.                             |
| Node 20 → 22                   | Low        | Used only for Tailwind CSS / npm tooling in pre-commit. No breaking changes expected.                                  |
| SHA pinning all actions        | Very Low   | Increases security; no functional change. SHAs must be verified against the correct release tags.                      |

---

## 6. Detailed Implementation Checklist

### Pre-work

- [x] Review the current workflow file end-to-end to catch any additional issues not covered in this spec
- [x] Verify that Python 3.14 is available on `ubuntu-latest` GitHub-hosted runners (it is — GitHub Actions runners include Python 3.14 via `actions/setup-python@v6`)
- [x] Verify that `astral-sh/setup-uv@v8` is the correct latest major version (confirmed from uv docs showing `v8.1.0` as latest)
- [x] Confirm Node 22 is the current LTS (verified — Node 22 became LTS in October 2024)

### Workflow-Level Changes

- [x] Add top-level `permissions: read-all` block (before `jobs:`) to restrict default `GITHUB_TOKEN` scope
- [x] Add `concurrency` block to cancel in-progress runs for the same `github.ref`

### `lint` Job

- [x] Update `actions/checkout` from `@v4` → `@v6`
- [x] Update `actions/setup-python` from `@v5` → `@v6`
- [x] Change `python-version` in setup-python from `"3.12"` → `"3.14"`
- [x] Update `actions/setup-node` from `@v4` → `@v6`
- [x] Change `node-version` in setup-node from `20` → `22`
- [x] Replace the "Install python dependencies" step with `astral-sh/setup-uv@v8` with `enable-cache: true`
- [x] Remove manual `pip install uv`, `uv venv venv`, and `source venv/bin/activate` commands
- [x] Install python dependencies using `uv pip install -r requirements-dev.txt --system` (no venv needed)
- [x] Verify `pre-commit/action@v3.0.1` remains unchanged (already latest)

### `test` Job

- [x] Update `actions/checkout` from `@v4` → `@v6`
- [x] Update `actions/setup-python` step name label from `"Set up Python 3.11"` → `"Set up Python 3.14"` (cosmetic, but accurate)
- [x] Update `actions/setup-python` from `@v5` → `@v6`
- [x] Change `python-version` in setup-python from `"3.11"` → `"3.14"`
- [x] Replace the "Install dependencies" step: swap `pip install uv` for `astral-sh/setup-uv@v8` with `enable-cache: true`
- [x] Keep `uv pip install -r requirements-dev.txt --system` (the `--system` flag remains correct here)

### `release` Job

- [x] Update `actions/checkout` from `@v4` → `@v6`
- [x] Verify `permissions: contents: write` is still present (it is — this overrides the new top-level `read-all`)
- [x] No other changes needed

### SHA Pinning

- [x] Look up the commit SHA for `actions/checkout@v6.0.2` on GitHub and pin
- [x] Look up the commit SHA for `actions/setup-python@v6.2.0` on GitHub and pin
- [x] Look up the commit SHA for `actions/setup-node@v6.4.0` on GitHub and pin
- [x] Look up the commit SHA for `pre-commit/action@v3.0.1` on GitHub and pin
- [x] Confirm the SHA for `astral-sh/setup-uv@v8.1.0` (documented in uv docs as `08807647e7069bb48b6ef5acd8ec9567f424441b`) and pin
- [x] Add the version tag as an inline comment on each pinned line, e.g. `@<sha> # v6.0.2`

### Post-work Validation

> **Note**: All git and remote-push validation steps are to be performed manually by the developer after implementation. No mutating git actions are performed by the agent.

- [ ] Run `pre-commit run --all-files` locally to confirm nothing broke
- [ ] Commit and push to a non-main branch to trigger the CI pipeline
- [ ] Verify all three jobs (`lint`, `test`, `release`) pass successfully
- [ ] Confirm the correct Python version (3.14) is reported in CI logs
- [ ] Confirm uv cache is populated and subsequent runs show cache hits
- [ ] Confirm the `concurrency` group works by pushing two commits in quick succession
