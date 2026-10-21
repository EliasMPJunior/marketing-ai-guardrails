# Marketing AI Guardrails

An exercise in designing a validation loop for an AI-assisted marketing workflow, with an emphasis on failure modes, deterministic checks, and human oversight.

## Challenge

This repository will document an exercise developed in response to the following challenge:

> Please design the validation loop for a marketing use case, explain its failure modes, and identify where human oversight is required.

## Problem Statement

Since no use case was specified in the challenge, this exercise assumes an AI-assisted marketing campaign workflow focused on personalized email campaigns.

A marketing team supplies a natural-language brief describing a product, a target audience, campaign objectives, and commercial conditions. An AI system interprets the brief and proposes audience segments, offers, promotional claims, and customer-facing messages.

The problem is not simply generating the campaign. It is determining **whether each proposed action and statement can be trusted and authorized before publication**.

For example, the system must avoid:
- Targeting customers who are not eligible or have not provided the required consent.
- Inventing product capabilities, performance figures, or supporting evidence.
- Offering discounts or terms that conflict with approved commercial policies.
- Publishing contradictory, misleading, inappropriate, or noncompliant content.
- Treating ambiguous or incomplete information as a verified fact.

The exercise will explore a validation loop that separates probabilistic AI interpretation and content generation from explicit, independently verifiable constraints. Validation outcomes should distinguish between **pass**, **fail**, and **human review**, with traceable reasons for each decision.

## Exercise Objectives

The planned exercise will address three aspects of the challenge:

1. **Validation loop:** Define how an initial brief, structured campaign proposal, generated content, and publication decision are checked, corrected, or escalated.
2. **Failure modes:** Identify what can go wrong during interpretation, factual grounding, audience selection, policy enforcement, content generation, and subsequent operation.
3. **Human oversight:** Specify where people approve requirements, adjudicate ambiguous or high-risk cases, authorize publication, and review changes to rules.

## Proposed Direction

The design will examine a layered workflow:

1. Interpret a marketing brief into structured data.
2. Validate its structure, business rules, sources, and applicable permissions.
3. Generate campaign content from approved inputs.
4. Revalidate generated claims and offers against authoritative evidence and policies.
5. Route unresolved or high-risk cases to human reviewers.
6. Publish only when the required checks and approvals have been satisfied, retaining an audit trail.

Semantic representations, rules, and deterministic validation may be used where appropriate. Passing a structural or logical check, however, does **not** by itself establish factual truth, legal compliance, or marketing effectiveness.

## Methodology

This exercise presents a **simplified version of my own methodology, developed and published in [OntoBDC](https://github.com/EliasMPJunior/ontobdc-wip)**.

The simplification is intentional: it is meant for **presentation and easier understanding of the methodology's underlying principles**, rather than reproducing the full OntoBDC runtime or all of its features.

The approach is organized around a few key elements: **finite state machines**, **independent capabilities**, **state and transition constraints**, and an **explicit validation loop**. The goal is not to turn a probabilistic AI model into a deterministic model, but to place its outputs inside an observable workflow whose progress is governed by verifiable conditions.

## Concepts

### Finite State Machine (FSM)

A **Finite State Machine** represents a process as a defined set of states and transitions. A transition is allowed only when its corresponding conditions are met.

In this exercise, states represent **verifiable stages of the marketing workflow**, such as an interpreted brief, a validated audience, an approved offer, or content ready for human review. They are not merely labels for functions that have run.

A possible sequence is:

```text
Brief received → Brief structured → Campaign validated → Content generated
                       ↑                   |                      |
                       └──── correction ───┘                      |
                                                                  ↓
                                      Human review ← Content validated
                                            |              |
                                            └── approval → Publication
```

If a required condition is not satisfied, the process must not advance as if the state had been achieved. The machine can follow an explicitly defined correction, rejection, or escalation path.

#### Sismic

The implementation will use [Sismic](https://sismic.readthedocs.io/), a Python library for defining and executing **statecharts**, which extend finite state machines with features such as hierarchical states, events, guarded transitions, and executable contracts.

Sismic coordinates **which state is active**, **which transitions are possible**, and **which conditions must hold**. The statechart expresses the workflow; it does not need to embed the implementation of every operation.

### Capabilities

A **capability** is a bounded, independently executable unit of work. It might interpret a marketing brief, resolve customer eligibility, check consent, verify a product claim, or generate campaign copy.

Capabilities are **not states**:

- A **state** describes a condition the system can verify.
- A **capability** performs work intended to establish or modify that condition.
- A **transition** describes when the machine may move from one state to another.

A state can be reached through different capabilities or implementation strategies, provided the **same required conditions** are satisfied. Similarly, a capability returning without an error does not prove that the expected state has been reached.

This separation allows the implementation of a capability to change without redefining the workflow's acceptance criteria.

### Guards, Contracts, and Constraints

Sismic provides complementary ways to control execution:

- **Guards** are boolean conditions associated with transitions. They determine whether a transition is eligible to occur.
- **`before` contracts** express preconditions that must hold before entering a state or executing a transition.
- **`after` contracts** express postconditions verified after leaving a state or completing a transition.
- **`always` contracts** express invariants that must remain true while the applicable state or transition is active.

These contracts are particularly important to the methodology: **validation belongs to the state or transition contract, not exclusively to the capability that performed the work**.

For example, a capability may generate a promotional offer, but the relevant postcondition still requires the resulting offer to comply with the approved discount policy. A different capability might attempt the same task; the acceptance criterion remains unchanged.

Domain-specific checks, such as semantic constraints, consent rules, evidence requirements, or commercial limits, can be exposed to the state machine through dedicated validation operations. Sismic enforces the contracts expressed in the statechart; it does not automatically establish the truth of external business data.

### How the Validation Loop Works

1. The state machine identifies the current state and an intended next state.
2. A capability performs the operation needed to establish the intended conditions.
3. Independent checks evaluate the resulting data or artifacts.
4. Guards and contracts determine whether the required state or transition conditions are satisfied.
5. The configured workflow either **advances**, **attempts correction and revalidation**, **rejects the operation**, or **escalates it for human review**.

The loop is therefore driven by **verified conditions rather than by the identity, confidence, or success message of the capability**. Retries and escalation are explicit paths in the statechart, not automatic behavior supplied by Sismic.

Human oversight remains necessary when the conditions themselves require judgment, reliable evidence is unavailable, or publication approval is required.

## Expected Results

The expected outcome is a **small, demonstrable validation workflow** that makes the proposed methodology understandable and testable in the selected marketing use case, without reproducing the entire OntoBDC platform.

The exercise should demonstrate:

1. **An explicit state-driven process:** A Sismic statechart describing the campaign lifecycle, valid transitions, correction paths, rejection, and escalation to human review.
2. **Capability-independent validation:** Interchangeable capabilities can propose or modify campaign artifacts, but progression depends on the same guards, checks, and state/transition contracts, regardless of which capability produced the result.
3. **A working validation loop:** A valid campaign can progress, while an invalid or incomplete campaign is stopped and either corrected and revalidated, rejected, or referred for human judgment.
4. **Observable failure modes:** Representative scenarios, including unsupported advertising claims, excessive discounts, missing consent, or ambiguous instructions, produce explicit outcomes instead of silent acceptance.
5. **Defined human oversight:** Review and approval points are visible in the workflow, including cases that cannot be resolved through formal rules alone and final authorization before publication.
6. **Traceable, reproducible decisions:** Each demonstration records the relevant inputs, state transitions, validation outcomes, reasons for rejection or escalation, and human decisions where applicable.

A minimal set of test cases should include **one valid campaign, one policy violation, one unsupported claim, and one case requiring human review**. Their expected outcomes should be stated in advance and checked against actual execution.

**Success does not mean proving that AI-generated marketing content is always correct.** It means showing that probabilistic outputs can be handled by a controlled process in which defined constraints are checked independently, failures are visible, and unresolved decisions are not silently automated.

## Status


This text was originally crafted by a human (me), subsequently expanded and developed with ChatGPT, and finally reviewed by me.

This repository is the starting point for the exercise. Design decisions, examples, implementation, test cases, and observed limitations will be documented as the work progresses.
