# Spec-Driven Development

This directory contains specs for planned and in-progress features, fixes, and improvements. Specs follow the workflow described in [How I Use Claude Code](https://boristane.com/blog/how-i-use-claude-code/).

The core principle: **never let an AI write code until you have reviewed and approved a written plan.** Separating thinking from typing prevents wasted effort, keeps you in control of architecture decisions, and produces significantly better results.

---

## Directory Structure

```txt
specs/
├── README.md              # This file.
├── _template.md           # Spec template — copy this for every new spec.
├── spec_0001_*.md         # Individual spec files, numbered sequentially.
└── spec_0002_*.md
```

Name spec files as `spec_XXXX_short_description.md` using a zero-padded four-digit number.

---

## The Workflow

The workflow has five phases, all captured in a **single spec file**.

### Phase 0: Overview and Acceptance Criteria

Before any research, fill in the **Overview** section with one or two sentences describing the feature, fix, or change and the desired outcome. Then, optionally, add a bulleted **Acceptance Criteria** subsection listing the terse, testable conditions that must all be true for the work to be considered complete. These criteria anchor the rest of the spec and give the AI a clear definition of done.

### Phase 1: Research

Copy `_template.md`, fill in the title and overview, then ask the AI to research the relevant parts of the codebase and populate the Research section.

Key prompt guidance:

- Explicitly demand depth: ask the AI to understand the system "in depth", "in great detail", and to cover "all its intricacies". Without this language, the AI will skim.
- Require the findings to be written into the Research section before any planning begins.

**Review the Research section yourself.** If the AI misunderstood the system, the plan will be wrong, and the implementation will be wrong. Correct any misunderstandings now. This is the highest-leverage step in the entire workflow.

### Phase 2: Plan

Once you approve the research, ask the AI to write the implementation plan into the Plan section. A good plan includes:

- The overall approach and why it is correct for the existing system.
- A table of files to be modified.
- Code snippets showing the actual proposed changes (not pseudocode).
- A testing approach for any new or changed Python functionality.
- Trade-offs and edge cases.

Useful prompt to get started:

> I want to build the feature/bug outlined in the spec overview. Write a detailed plan in the Plan section of the spec. Read source files before suggesting changes — base the plan on the actual codebase. Do not implement yet.

**If you have a reference implementation** (e.g., a pattern already used elsewhere in the codebase, or a well-designed open-source example), share it with the AI. Reference implementations dramatically improve plan quality.

### Phase 3: Annotate

This is where you add the most value. Open the spec file in your editor and add inline notes directly into the Plan section. Prefix every annotation with `COMMENT:` so the AI can identify your notes at a glance. If the AI has questions in the Open Questions section, answer them with `ANSWER:` annotations.

Annotations can:

- Correct a wrong assumption (e.g., `COMMENT: No — this should be a PATCH, not a PUT.`)
- Reject a proposed approach (e.g., `COMMENT: Remove this section — we do not need caching here.`)
- Add a constraint (e.g., `COMMENT: This function signature must not change.`)
- Inject domain knowledge the AI does not have.
- Answer an AI question (e.g., `ANSWER: Use the existing UserService, do not create a new one.`)

Then send the AI back to the document:

> I added `COMMENT:` notes to the plan and `ANSWER:` responses to any open questions. Address all notes and update the plan accordingly. Do not implement yet.

Repeat this cycle until the plan is exactly right. **Always include "do not implement yet."** Without it, the AI will start writing code the moment it thinks the plan is good enough.

Once the plan is approved, ask the AI to populate the Tasks section with a granular, ordered checklist of every step needed to complete the plan.

### Phase 4: Implementation

When the plan and tasks are finalized, issue the implementation command:

> Implement all tasks. Mark each task as completed in the spec as you finish it. Run `pre-commit run --all-files` after each logical change. Do not stop until all tasks are marked complete. Do not add unnecessary comments or docstrings to code you did not change.

The key phrases encoded in this prompt:

- **"Implement all tasks"** — do everything in the plan; do not cherry-pick.
- **"Mark each task as completed"** — the spec is the source of truth for progress.
- **"Run `pre-commit run --all-files`"** — catch lint and formatting issues early, not at the end. This also validates documentation and configuration files.
- **"Do not stop until all tasks are marked complete"** — do not pause mid-flow for confirmation.
- **"Do not add unnecessary comments or docstrings"** — keep the code clean.

During implementation, your prompts should be short and terse — the AI has the full plan context. A correction like "You didn't implement the `parse_token` function" is enough.

**If something goes badly wrong,** revert with `git checkout` and narrow scope rather than trying to patch a bad approach:

> I reverted everything. Now I only want [narrow change] — nothing else.

---

## Tips for Best Results

- **Run research and implementation in a single session.** By the time you say "implement it all," the AI has built deep understanding of the codebase through the research and annotation phases. A single session produces better results than splitting across multiple.
- **Be precise in annotations.** Two words (`COMMENT: Not optional.`) can be enough. A paragraph is fine when domain knowledge is needed.
- **Include tests in the plan.** For any spec that changes Python code, the plan should have a Testing Approach subsection and the Tasks list should include test tasks.
- **Trim scope actively.** Remove nice-to-haves from the plan before implementation starts. Preventing scope creep is your job, not the AI's.
- **Reference existing patterns.** Point to similar code already in the project ("this should follow the same pattern as `services/users/`"). The AI reads the reference and applies all the implicit conventions without you having to enumerate them.
- **Check the `pre-commit` output after implementation.** The pre-commit hooks run ruff (linting and formatting), type-checking, and other validators. A clean pre-commit run is a required exit criterion for every spec.

---

## Spec Status

Update the status field at the top of each spec as work progresses:

| Status        | Meaning                                             |
| ------------- | --------------------------------------------------- |
| `Draft`       | Overview written; research not yet started.         |
| `In Progress` | Actively being researched, planned, or implemented. |
| `Complete`    | All tasks done; pre-commit and tests pass.          |
