# Discussions

## Use Case

A hypothetical Black Friday campaign for courses was chosen as the example. The scenario assumes an established marketing infrastructure, including a course catalog, campaign management, and existing business rules.

## Marketing Plan

The workflow is represented in `ontology/activities.ttl` using the existing **P-Plan ontology**, rather than introducing new classes.

`:StandardMarketingWorkflow` is a `p-plan:Plan`: a description of an intended process. Its activities are `p-plan:Step` instances, linked to the plan through `p-plan:isStepOfPlan`. Their dependencies and expected inputs and outputs are also described in the ontology.

## Execution

The **finite state machine (FSM)** orchestrates execution of the plan's steps. Capabilities perform the operations, while state conditions and guards determine whether execution can advance, must be corrected, or requires human review.

The plan describes **what** should happen; the FSM controls **when** each step can proceed.

The machine never advances because a capability reported success. A state means a condition that was verified independently: `brief_structured` means a task listing exists that honors its JSON contract, `operation_scored` means a scores file exists that covers every task with steps that belong to the ontology, `operation_validated` means every task is tied to exactly one strong step. Capabilities are interchangeable and their return value proves nothing on its own.

## Scores

The AI does not decide anything. It proposes, and the decision comes from a score.

Each task is tied to the **three closest `p-plan:Step` instances** of the plan, with a score from 0 to 1, and only answers that cover every task, name distinct steps that exist in the ontology and stay within range are accepted. Counting, per task, how many steps reach `MIN_SCORE` (0.8) gives three deterministic outcomes:

- **exactly one strong step** — the task maps to a single activity; the operation is validated;
- **several strong steps** — the task is ambiguous, and the ambiguity is not hand-waved: the task is split into subtasks, one per strong step, the listing is replaced and the new listing is **scored again**;
- **no strong step** — the task matches nothing in the plan, and the demand is escalated to people.

The correction loop is closed on purpose: a split that does not resolve the ambiguity is detected because the new listing is rescored, and `max_split_rounds` (1) bounds it, since every round calls an AI and costs tokens.

## AI usage confined to small tasks

The core design choice is to **never ask the model to produce the campaign**. The work is cut into small, bounded tasks — interpret the brief into a listing, score how close a task is to a plan step, split one ambiguous task into subtasks — and each answer passes a deterministic check before it is used. Small scoped questions with a verifiable answer is what keeps hallucination from reaching the output: the narrower the task, the less room the model has to invent courses, prices, steps or audiences. A wrong answer costs a rejection or an escalation, in a workflow whose progress depends on verified conditions, not on the model's confidence.

## What building it exposed

The main defect found during development was the reliance on Sismic **contracts as if they were routes**. The result of a capability was recorded by the `action` of a transition and then required by the `before` assertion of the target state, with no failure branch: when the capability returned `False` (missing mock, `claude` unavailable, invalid answer), the interpreter raised `PreconditionError` and aborted the run instead of routing somewhere. The fix applied to every affected state followed the same pattern: the capability runs in the `on entry` of the state, the resulting fact is recorded there, the transitions are guarded by that fact, and the failure becomes an explicit branch — `rejected` when nothing was interpreted, `operation_unresolved` when scoring, splitting or replacement failed. A contract is an assertion, not a route; a failure that must be handled has to be a transition.

Every run left a trace folder with the inputs, the artifacts and `path.json` (each transition with the facts holding after it). Scenarios were exercised with and without mocks — valid demand reaching `published`, invalid brief rejected, scoring failure and split failure escalated — matching the expected outcome in each case, and the suite in `tests/` states those expectations in advance.

## Scope reduction

Only the first part of the request runs end to end: understanding the request, breaking it into tasks, and tying each task to the activity of the plan that performs it. The business checks of the request — offers against pricing and discount policy, claims against course descriptions, recipients against consent — the execution of the plan after validation, and the human hand-off beyond the on-screen alert are described as future steps and were left out to keep the deliverable inside the time available.

Two pieces of that reduction deserve to be named, because they are where the determinism of the solution would go next:

- **SHACL** — expressing the shapes of products, offers and audiences as constraints and validating them with pySHACL, would move the rules out of the code and give a **more deterministic** reading of the data than a prompt, validating against the **database** of the existing infrastructure instead of against the model's answer. It stayed in future implementations.
- **Neural networks to find the necessary information** — locating the courses, offers and audiences that feed the checks, instead of expecting the model to recall them. Also left for later, and it is exactly the part that the reduced tasks above are meant to make verifiable once the data source exists.
