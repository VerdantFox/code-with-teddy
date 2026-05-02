# Spec 0001: Update Ruff and Ty Rules for Maximum Strictness

## Overview

This spec describes planned changes to `ruff.toml` and `ty.toml` to increase linting and
type-checking strictness as much as practical. Rules that conflict with existing rules, are
purely for .pyi stub files, are domain-irrelevant (e.g., Airflow, Django, numpy/pandas), or
would produce excessive false positives are excluded or noted.

---

## Ruff Changes

### Currently Commented-Out Rule Groups Now Stable

Two rule groups were previously disabled because they were "In preview." Both now have large
sets of stable rules:

| Group          | Code   | Reason to Enable                                                                                               |
| -------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| refurb         | `FURB` | Many modernization rules are now stable (e.g., `FURB105`, `FURB136`, `FURB157`, `FURB161`, `FURB163`, etc.)    |
| flake8-logging | `LOG`  | Several rules are now stable: `LOG001`, `LOG002`, `LOG007`, `LOG009`. Prevents misuse of the `logging` module. |

**Action:** Uncomment `"FURB"` and `"LOG"` in `ruff.toml` `[lint] select`.

---

### New Rule Groups to Add

These groups are not currently selected and are stable and relevant to this FastAPI project:

| Group                                                    | Code   | Why Add                                                                                                  | Caveats                                                                                                                                               |
| -------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| FastAPI                                                  | `FAST` | Project is built on FastAPI. Rules catch FastAPI anti-patterns (e.g., non-annotated route dependencies). | Verify no false positives on existing routes.                                                                                                         |
| flake8-future-annotations                                | `FA`   | `FA100` / `FA102` enforce `from __future__ import annotations` where needed for forward references.      | Python 3.14 may make this less critical; verify impact.                                                                                               |
| flake8-slots                                             | `SLOT` | `SLOT000`–`SLOT002` enforce `__slots__` on subclasses of slotted base classes (`str`, `tuple`, etc.).    | Only flags issues when subclassing builtin slotted types; low noise.                                                                                  |
| flake8-type-checking COMMENT: let's not include this one | `TC`   | `TC001`–`TC003` move type-only imports into `TYPE_CHECKING` blocks, reducing runtime overhead.           | Must verify against SQLAlchemy/Pydantic patterns that need runtime imports; may require per-file ignores.                                             |
| flake8-todos                                             | `TD`   | `TD001`–`TD007` enforce a consistent TODO format.                                                        | Very strict; review existing TODO comments and pick which rules to keep. Consider ignoring `TD002` (author) and `TD003` (issue link) if not required. |
| flake8-fixme COMMENT: Let's not include this one         | `FIX`  | `FIX001`–`FIX004` flag FIXME/HACK/TODO/XXX comments so they're tracked.                                  | Potentially noisy. `FIX002` (line-contains-todo) overlaps heavily with `TD` rules. May omit.                                                          |

**Action:** Add `"FAST"`, `"FA"`, `"SLOT"`, `"TC"`, `"TD"` to `[lint] select`. Evaluate `"FIX"` separately.

---

### Rule Groups Intentionally Excluded

| Group            | Code  | Reason Excluded                                                  |
| ---------------- | ----- | ---------------------------------------------------------------- |
| Airflow          | `AIR` | Not an Airflow project.                                          |
| flake8-copyright | `CPY` | All rules remain in preview.                                     |
| flake8-django    | `DJ`  | Not a Django project; FastAPI is used instead.                   |
| flake8-gettext   | `INT` | No gettext/i18n in this project.                                 |
| flake8-pyi       | `PYI` | Only relevant for `.pyi` stub files; none exist in this project. |
| pandas-vet       | `PD`  | No pandas usage.                                                 |
| NumPy            | `NPY` | No numpy usage.                                                  |

---

### New Ignored Rules to Review

Some rules in newly added groups will likely need to be ignored:

| Rule     | Name                             | Reason to Ignore                                                      |
| -------- | -------------------------------- | --------------------------------------------------------------------- |
| `TD002`  | `missing-todo-author`            | Author in TODOs is not a project requirement.                         |
| `TD003`  | `missing-todo-link`              | Issue links are not required for all TODOs.                           |
| `FIX002` | `line-contains-todo`             | Redundant with `TD` rules if both are enabled.                        |
| `TC001`  | `typing-only-first-party-import` | SQLAlchemy mapped columns require runtime access; evaluate carefully. |

---

### Unfixable Rules to Review

The current `unfixable` list should remain as-is. No new entries needed for newly added groups.

---

### Preview Mode Consideration

The project currently uses only stable rules. Several useful rules remain in preview:

| Rule                 | Group | Description                                                          |
| -------------------- | ----- | -------------------------------------------------------------------- |
| `FURB` preview rules | FURB  | e.g., `FURB101`, `FURB140`, `FURB142`, etc.                          |
| `LOG004`             | LOG   | `log-exception-outside-except-handler`                               |
| `PLW1514`            | PLW   | `unspecified-encoding` for `open()` calls                            |
| `PLR0904`            | PLR   | `too-many-public-methods`                                            |
| `RUF029`             | RUF   | `unused-async` — flags async functions that don't use async features |

**Decision:** Do not enable preview mode globally. Individual preview rules can be enabled by
adding them explicitly to `select` using their specific codes (e.g., `"RUF029"`, `"LOG004"`).

**Action:** Consider adding `"RUF029"` (unused-async) explicitly — it's a good fit for an async
FastAPI codebase to prevent accidentally non-async route handlers.
COMMENT: Let's try RUF029

---

### Summary of `ruff.toml` Changes

```toml
# In [lint] select, uncomment/add these:
"FAST",  # FastAPI-specific rules
"FA",    # flake8-future-annotations
"FURB",  # Refurb (was "In preview", now has stable rules)
"LOG",   # flake8-logging (was "In preview", now has stable rules)
"SLOT",  # flake8-slots
"TC",    # flake8-type-checking
"TD",    # flake8-todos
"RUF029", # unused-async (preview, added explicitly)

# In [lint] ignore, add:
"TD002", # Missing author in TODO
"TD003", # Missing issue link for TODO
```

---

## Ty Changes

### Rules Currently "warn" → Upgrade to "error"

The following rules default to `warn`. Setting them to `"error"` increases strictness:

| Rule                                  | Default | Proposed | Description                                                                              |
| ------------------------------------- | ------- | -------- | ---------------------------------------------------------------------------------------- |
| `ambiguous-protocol-member`           | warn    | error    | Protocol with undeclared members leads to ambiguous interfaces.                          |
| `deprecated`                          | warn    | error    | Uses of items marked `@deprecated` should be treated as errors.                          |
| `ignore-comment-unknown-rule`         | warn    | error    | Unknown rule codes in `ty: ignore[...]` comments are likely typos.                       |
| `ineffective-final`                   | warn    | error    | Calling `final()` directly (not as decorator) has no type-checker effect.                |
| `invalid-enum-member-annotation`      | warn    | error    | Explicit type annotations on enum members are misleading per the typing spec.            |
| `invalid-legacy-positional-parameter` | warn    | error    | Incorrect use of the legacy positional-only parameter convention.                        |
| `mismatched-type-name`                | warn    | error    | TypeVar/NewType/TypedDict variable name doesn't match the name argument (likely a typo). |
| `possibly-missing-submodule`          | warn    | error    | Accessing submodules that may not have been imported.                                    |
| `unused-type-ignore-comment`          | warn    | error    | `type: ignore` comments that suppress no errors should be removed.                       |
| `useless-overload-body`               | warn    | error    | `@overload`-decorated functions should have stub-like bodies only.                       |

### Rules Currently "ignore" → Enable

| Rule                       | Default | Proposed | Description                                          | Risk                                            |
| -------------------------- | ------- | -------- | ---------------------------------------------------- | ----------------------------------------------- |
| `unsupported-dynamic-base` | ignore  | warn     | Classes created via `type()` with unsupported bases. | Low — `type()` is rarely used in this codebase. |

### Preview Rules to Enable

These rules are in preview but are high-value for this async FastAPI codebase:

| Rule                   | Level        | Description                                                                | Notes                                                 |
| ---------------------- | ------------ | -------------------------------------------------------------------------- | ----------------------------------------------------- |
| `unused-awaitable`     | warn → error | Coroutines/awaitables used as expression statements without being awaited. | Critical for async correctness. Preview since 0.0.21. |
| `call-abstract-method` | error        | Calls to abstract `@classmethod`/`@staticmethod` with trivial bodies.      | Preview since 0.0.16.                                 |

### Rules to Remove the Stale Comment About

The current `ty.toml` has a comment:

```toml
# unknown-rule is no longer a valid rule name in current ty versions
```

This comment refers to a rule that was removed. The comment itself should be removed since
it no longer serves a purpose.

### Summary of `ty.toml` Changes

```toml
[rules]
# Existing rules (keep as-is):
invalid-ignore-comment = "error"
possibly-missing-attribute = "error"
possibly-missing-import = "error"
redundant-cast = "error"
undefined-reveal = "error"
unresolved-global = "error"
unsupported-base = "error"
division-by-zero = "error"
possibly-unresolved-reference = "error"
unused-ignore-comment = "error"

# New rules (upgrade warn → error):
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

# New rules (enable from ignore):
unsupported-dynamic-base = "warn"

# Preview rules (explicitly enabled):
unused-awaitable = "error"
call-abstract-method = "error"
```

---

## Implementation Order

1. **ty changes first** — type-checking errors are foundational. Run `pre-commit run --all-files` and fix all
   new violations before moving to linting.
2. **Ruff stable group additions** — add `FURB`, `LOG`, `FAST`, `FA`, `SLOT` first (lower
   churn expected).
3. **Ruff TD and preview** — requires cleaning up TODO comments and adding `RUF029`. Apply last.
4. **Run full test suite** after each stage to catch regressions.

---

## Notes

- All rule additions are for stable rules unless explicitly marked as preview.
- Conflicts with existing ignore rules: none identified — the new groups don't overlap with
  currently ignored rules (`A003`, `ANN401`, `COM812`, `D105`, `D107`, `D203`, `D213`,
  `ISC001`).
- The `tests/*` per-file ignores are unlikely to need changes for any of these new rule groups.

---

## Todo List

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
- [ ] Commit all changes
