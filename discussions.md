# Discussions

## Use Case

A hypothetical Black Friday campaign for courses was chosen as the example. The scenario assumes an established marketing infrastructure, including a course catalog, campaign management, and existing business rules.

## Marketing Plan

The workflow is represented in `ontology/activities.ttl` using the existing **P-Plan ontology**, rather than introducing new classes.

`:StandardMarketingWorkflow` is a `p-plan:Plan`: a description of an intended process. Its activities are `p-plan:Step` instances, linked to the plan through `p-plan:isStepOfPlan`. Their dependencies and expected inputs and outputs are also described in the ontology.

## Execution

The **finite state machine (FSM)** orchestrates execution of the plan's steps. Capabilities perform the operations, while state conditions and guards determine whether execution can advance, must be corrected, or requires human review.

The plan describes **what** should happen; the FSM controls **when** each step can proceed.
