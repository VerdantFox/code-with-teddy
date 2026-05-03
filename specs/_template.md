# Spec XXXX: [Title]

**Status:** Draft | In Progress | Complete

---

## Overview

[One or two sentences describing the feature, fix, or change and the desired outcome.]

### Acceptance Criteria (Optional, overview might be enough)

- [Terse, testable statement of a required outcome.]
- [Add one bullet per distinct criterion.]

---

## Research

> **AI instructions:** Read all relevant parts of the codebase in depth before writing anything here. Understand how the affected systems work, their intricacies, and all their specificities. Do not skim — surface-level reading produces wrong plans. After researching, populate this section with detailed findings organized by subsection. Do not proceed to the Plan section until the developer has reviewed and approved this section. Delete these instructions after filling out this section.

### [Relevant Component or System]

[Findings, including how the component works, its conventions, and anything that could affect the implementation.]

### [Another relevant Component or System]

[Continue adding subsections as needed.]

---

## Plan

> **AI instructions:** Do not start this section until the "Research" section is reviewed and approved. Based on the research findings and the overview above, write a detailed implementation plan in this section. Include the file paths to be modified, code snippets showing the actual proposed changes, and any trade-offs or edge cases. If the plan involves new or changed Python functionality, include a testing approach. Do not implement anything yet. Wait for the developer to review and annotate this section. The developer will add inline notes prefixed with `COMMENT:` directly into this section. When the developer says "address all notes and update the plan", incorporate all annotations and update the plan accordingly — still without implementing. If you have questions, add them to the Open Questions section. Repeat until the developer approves. Delete these instructions after filling out this section.

### Approach

[High-level description of the implementation strategy and why it is the right approach.]

### Files to Modify

| File              | Change                 |
| ----------------- | ---------------------- |
| `path/to/file.py` | Description of change. |

### Implementation Details

[Detailed plan with code snippets showing the actual changes. Be specific about function signatures, data shapes, and integration points with existing systems.]

### Testing Approach

[If applicable: describe which tests to add or update, what scenarios to cover, and where the test files live. Omit this subsection if no Python code is changing.]

### Trade-offs and Considerations

[Known edge cases, alternative approaches considered and why they were rejected, and anything the developer should be aware of.]

---

## Open Questions

> **AI instructions:** If you have questions that must be answered before the plan can be finalized, list them here. The developer will answer each with an `ANSWER:` annotation. Do not begin implementation until all blocking questions are resolved. Delete these instructions after filling out this section. Delete this section entirely if there are no open questions.

[No open questions.]

---

## Tasks

> **AI instructions:** Do not start this step until the "Plan" is reviewed and approved. Populate this section with a granular, ordered task breakdown covering every step needed to complete the plan, including any test tasks. Use phases to group related work. Do not begin implementation until the developer approves. Once implementation begins, mark each task as completed (`[x]`) immediately after finishing it. Do not stop until all tasks are marked complete. Delete these instructions after filling out this section.

### Phase 1: [Phase Name]

- [ ] [Task description.]
- [ ] [Task description.]

### Phase 2: [Phase Name]

- [ ] [Task description.]
- [ ] [Task description.]

---

## Implementation

> **AI instructions:** Do not start implementation until the "Tasks" section is reviewed and approved. Implement all tasks from the checklist above. Follow these rules throughout:
>
> - Implement everything — do not cherry-pick tasks.
> - Mark each task `[x]` in the Tasks section immediately after completing it.
> - Do not stop until all tasks are marked complete.
> - After each logical change, run `pre-commit run --all-files` to catch lint and formatting issues before continuing.
> - Do not add unnecessary comments, docstrings, or type annotations to code you did not change.
> - Do not use `print` statements; use the `logging` module instead.
> - Do not change function signatures unless the plan explicitly requires it.
> - If a task surfaces a problem not covered by the plan, stop and note it here rather than making unplanned changes.
>
> Delete these instructions after filling out this section.

### Implementation Log

[AI: note any significant decisions, surprises, or deviations from the plan encountered during implementation.]
