# Spec 0001: Update Ruff and Ty Rules for Maximum Strictness

**Status:** Complete

---

## Overview

Increase linting and type-checking strictness by enabling additional stable rule groups in `ruff.toml` and upgrading warn-level rules to errors in `ty.toml`, excluding rules that are domain-irrelevant, conflict with existing configuration, or produce excessive false positives.

### Acceptance Criteria

- `ruff.toml` enables `FAST`, `FA`, `FURB`, `LOG`, `SLOT`, `TD`, and `RUF029`.
- `ty.toml` upgrades all targeted `warn`-level rules to `error` and enables `unsupported-dynamic-base`, `unused-awaitable`, and `call-abstract-method`.
- `pre-commit run --all-files` passes with no violations.
- Full test suite passes with no regressions.

---

## Research

### Current ruff.toml State

Two rule groups (`FURB`, `LOG`) were previously commented out because they were in preview. Both now have large sets of stable rules ready to enable.

The following stable groups are not yet selected but are potentially relevant to this FastAPI project:

| Group                     | Code   | Notes                                                                      |
| ------------------------- | ------ | -------------------------------------------------------------------------- |
| FastAPI                   | `FAST` | Catches FastAPI anti-patterns (e.g., non-annotated route dependencies).    |
| flake8-future-annotations | `FA`   | `FA100`/`FA102` enforce `from __future__ import annotations` where needed. |
| flake8-slots              | `SLOT` | `SLOT000`–`SLOT002` enforce `__slots__` on subclasses of slotted builtins. |
| flake8-type-checking      | `TC`   | `TC001`–`TC003` move type-only imports into `TYPE_CHECKING` blocks.        |
| flake8-todos              | `TD`   | `TD001`–`TD007` enforce a consistent TODO format.                          |
| flake8-fixme              | `FIX`  | `FIX001`–`FIX004` flag FIXME/HACK/TODO/XXX comments.                       |

The following groups are intentionally out of scope (domain-irrelevant or preview-only):

| Group            | Code  | Reason Excluded                                                  |
| ---------------- | ----- | ---------------------------------------------------------------- |
| Airflow          | `AIR` | Not an Airflow project.                                          |
| flake8-copyright | `CPY` | All rules remain in preview.                                     |
| flake8-django    | `DJ`  | Not a Django project; FastAPI is used instead.                   |
| flake8-gettext   | `INT` | No gettext/i18n in this project.                                 |
| flake8-pyi       | `PYI` | Only relevant for `.pyi` stub files; none exist in this project. |
| pandas-vet       | `PD`  | No pandas usage.                                                 |
| NumPy            | `NPY` | No numpy usage.                                                  |

The project currently uses only stable rules. Several useful rules remain in preview and can be added explicitly to `select` without enabling global preview mode:

| Rule                 | Group | Description                                                          |
| -------------------- | ----- | -------------------------------------------------------------------- |
| `FURB` preview rules | FURB  | e.g., `FURB101`, `FURB140`, `FURB142`, etc.                          |
| `LOG004`             | LOG   | `log-exception-outside-except-handler`                               |
| `PLW1514`            | PLW   | `unspecified-encoding` for `open()` calls                            |
| `PLR0904`            | PLR   | `too-many-public-methods`                                            |
| `RUF029`             | RUF   | `unused-async` — flags async functions that don't use async features |

### Current ty.toml State

The following rules currently default to `warn` and are candidates for upgrade to `error`: `ambiguous-protocol-member`, `deprecated`, `ignore-comment-unknown-rule`, `ineffective-final`, `invalid-enum-member-annotation`, `invalid-legacy-positional-parameter`, `mismatched-type-name`, `possibly-missing-submodule`, `unused-type-ignore-comment`, `useless-overload-body`.

The `unsupported-dynamic-base` rule defaults to `ignore` but is worth enabling at `warn` since `type()` is rarely used in this codebase.

Two high-value preview rules are available: `unused-awaitable` (critical for async correctness; preview since 0.0.21) and `call-abstract-method` (preview since 0.0.16).

A stale comment referencing `unknown-rule` (a rule removed from ty) exists in `ty.toml` and should be removed.

---

## Plan

### Approach

Apply changes in phases — ty first (foundational), then ruff stable groups, then ruff todo/preview rules. Run `pre-commit run --all-files` and the full test suite after each phase before proceeding. This staged approach makes it easy to attribute any new violations to the specific rule group that introduced them.

`TC` (flake8-type-checking) is excluded because SQLAlchemy mapped columns require runtime imports — moving them into `TYPE_CHECKING` blocks would break the ORM. `FIX` (flake8-fixme) is excluded because `FIX002` (`line-contains-todo`) is redundant with the `TD` rules.

### Files to Modify

| File                           | Change                                                                                                                     |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `ty.toml`                      | Upgrade warn-level rules to error, enable `unsupported-dynamic-base` and preview rules, remove stale comment.              |
| `ruff.toml`                    | Uncomment `FURB` and `LOG`, add `FAST`/`FA`/`SLOT`/`TD` to select, add `TD002`/`TD003` to ignore, add `RUF029` explicitly. |
| `app/**/*.py`, `tests/**/*.py` | Fix any violations introduced by the new rules.                                                                            |

### Implementation Details

#### ruff.toml changes

```toml
# In [lint] select, uncomment/add these:
"FAST",   # FastAPI-specific rules
"FA",     # flake8-future-annotations
"FURB",   # Refurb (was "In preview", now has stable rules)
"LOG",    # flake8-logging (was "In preview", now has stable rules)
"SLOT",   # flake8-slots
"TD",     # flake8-todos
"RUF029", # unused-async (preview, added explicitly)

# In [lint] ignore, add:
"TD002",  # Missing author in TODO — not a project requirement
"TD003",  # Missing issue link for TODO — not required
```

#### ty.toml changes

```toml
[rules]
# Upgrade warn → error:
ambiguous-protocol-member = "error"
deprecated = "error"
ignore-comment-unknown-rule = "error"
ineffective-final = "error"
invalid-enum-member-annotation = "error"
invalid-legacy-positional-parameter = "error"
mismatched-type-name = "error"
possibly-missing-submodule = "error"
unused-type-ignore-comment = "error"
useless-overload-body = "error"

# Enable from ignore:
unsupported-dynamic-base = "warn"

# Preview rules (explicitly enabled):
unused-awaitable = "error"
call-abstract-method = "error"
```

### Testing Approach

No new test files are needed. The full test suite (`pytest`) should be run after each phase to confirm no regressions. `pre-commit run --all-files` acts as the primary per-phase validation (it runs ruff, ty, and other validators).

### Trade-offs and Considerations

- `TC` is excluded: SQLAlchemy/Pydantic runtime import patterns conflict with moving imports into `TYPE_CHECKING` blocks.
- `FIX` is excluded: `FIX002` is redundant with `TD` rules.
- Preview mode is not enabled globally — individual preview rules are added explicitly to avoid pulling in unstable rules.
- Conflicts with existing ignore rules: none identified. The new groups don't overlap with currently ignored rules (`A003`, `ANN401`, `COM812`, `D105`, `D107`, `D203`, `D213`, `ISC001`).
- The `tests/*` per-file ignores are unlikely to need changes for any of these new rule groups.

---

## Open Questions

[No open questions.]

---

## Tasks

### Phase 1 — ty Strictness

- [x] Add `ambiguous-protocol-member = "error"` to `ty.toml` `[rules]`
- [x] Add `deprecated = "error"` to `ty.toml` `[rules]`
- [x] Add `ignore-comment-unknown-rule = "error"` to `ty.toml` `[rules]`
- [x] Add `ineffective-final = "error"` to `ty.toml` `[rules]`
- [x] Add `invalid-enum-member-annotation = "error"` to `ty.toml` `[rules]`
- [x] Add `invalid-legacy-positional-parameter = "error"` to `ty.toml` `[rules]`
- [x] Add `mismatched-type-name = "error"` to `ty.toml` `[rules]`
- [x] Add `possibly-missing-submodule = "error"` to `ty.toml` `[rules]`
- [x] Add `unused-type-ignore-comment = "error"` to `ty.toml` `[rules]`
- [x] Add `useless-overload-body = "error"` to `ty.toml` `[rules]`
- [x] Add `unsupported-dynamic-base = "warn"` to `ty.toml` `[rules]`
- [x] Add `unused-awaitable = "error"` to `ty.toml` `[rules]` (preview)
- [x] Add `call-abstract-method = "error"` to `ty.toml` `[rules]` (preview)
- [x] Remove the stale comment `# unknown-rule is no longer a valid rule name in current ty versions` from `ty.toml`
- [x] Run `pre-commit run --all-files` and fix all new violations
- [x] Run full test suite to confirm no regressions

### Phase 2 — Ruff: Uncomment Previously-Preview Groups

- [x] Uncomment `"FURB"` in `ruff.toml` `[lint] select`
- [x] Uncomment `"LOG"` in `ruff.toml` `[lint] select`
- [x] Run `pre-commit run --all-files` and fix all new violations
- [x] Run full test suite to confirm no regressions

### Phase 3 — Ruff: Add New Stable Groups

- [x] Add `"FAST"` to `ruff.toml` `[lint] select`
- [x] Run `pre-commit run --all-files`, fix or suppress any false positives specific to FastAPI patterns
- [x] Add `"FA"` to `ruff.toml` `[lint] select`
- [x] Run `pre-commit run --all-files` and fix all new violations (add `from __future__ import annotations` where needed)
- [x] Add `"SLOT"` to `ruff.toml` `[lint] select`
- [x] Run `pre-commit run --all-files` and fix all new violations
- [x] Run full test suite to confirm no regressions

### Phase 4 — Ruff: Todos and Preview Rules

- [x] Add `"TD"` to `ruff.toml` `[lint] select`
- [x] Add `"TD002"` to `ruff.toml` `[lint] ignore` (missing TODO author — not required)
- [x] Add `"TD003"` to `ruff.toml` `[lint] ignore` (missing TODO issue link — not required)
- [x] Run `pre-commit run --all-files` and fix all remaining `TD` violations (standardise TODO format)
- [x] Add `"RUF029"` to `ruff.toml` `[lint] select` (unused-async, preview rule)
- [x] Run `pre-commit run --all-files` and fix all `RUF029` violations (convert or annotate non-async `async def` functions)
- [x] Run full test suite to confirm no regressions

### Phase 5 — Final Verification

- [x] Run `pre-commit run --all-files` (full clean pass with all new rules)
- [x] Run full test suite (`pytest`)
- [x] Commit all changes

---

## Implementation

### Implementation Log

No significant deviations from the plan. All phases completed in order. `TC` and `FIX` were excluded as decided during planning. `RUF029` required converting or annotating several non-async `async def` functions.
