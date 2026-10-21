"""End-to-end scenarios: the expected outcome is stated in advance for each one.

Every scenario runs the real statechart, guards and capabilities. Only the
sources of the AI output are controlled, through mocks or a fake ``claude``.
"""

from typing import Any, Dict, List

from conftest import Run, repo_mock, step_scores

SINGLE_STRONG = [("SelectProducts", 0.9), ("DiscoverProducts", 0.2), ("CreateOffers", 0.1)]


def all_single_strong() -> List[Dict[str, Any]]:
    """Scores in which every task of the tasks mock has exactly one strong step."""
    return [step_scores(task["id"], *SINGLE_STRONG) for task in repo_mock("tasks.json")]


def test_valid_demand_is_split_rescored_and_published(run_fsm):
    run: Run = run_fsm()

    assert run.returncode == 0
    assert run.states == [
        "brief_received", "brief_structured", "operation_scored", "operation_split",
        "tasks_replaced", "operation_scored", "operation_validated", "published",
    ]
    assert run.path["final"] is True and run.path["state"] == "published"
    # Tasks with several strong steps were replaced by their subtasks; the others are kept.
    assert [task["id"] for task in run.load("tasks.json")] == [1, "2.1", "2.2", "3.1", "3.2", "3.3", 4]
    nested = run.load("subtasks.json")
    assert [len(task["subtasks"]) for task in nested] == [0, 2, 3, 0]


def test_demand_with_one_strong_step_per_task_skips_the_split(run_fsm):
    run: Run = run_fsm(mocks={"step_scores.json": all_single_strong()})

    assert run.states == [
        "brief_received", "brief_structured", "operation_scored", "operation_validated", "published",
    ]
    assert [task["id"] for task in run.load("tasks.json")] == [1, 2, 3, 4]
    assert not (run.folder / "subtasks.json").exists()


def test_invalid_brief_is_rejected_before_anything_is_interpreted(run_fsm):
    run: Run = run_fsm(brief="   \n")

    assert run.states == ["brief_received", "rejected"]
    assert not (run.folder / "tasks.json").exists()
    assert not (run.folder / "step_scores.json").exists()


def test_task_without_strong_step_goes_to_people(run_fsm):
    scores = all_single_strong()
    scores[0] = step_scores(1, ("SelectProducts", 0.7), ("DiscoverProducts", 0.2), ("CreateOffers", 0.1))
    run: Run = run_fsm(mocks={"step_scores.json": scores})

    assert run.states == ["brief_received", "brief_structured", "operation_scored", "operation_unresolved"]
    assert "human tasks workflow" in run.stdout
    assert "task 1: 0 step(s)" in run.stdout
    assert not (run.folder / "subtasks.json").exists()


def test_split_that_does_not_resolve_the_ambiguity_stops_after_the_allowed_rounds(run_fsm):
    scores = repo_mock("step_scores.json")
    ambiguous = next(entry for entry in scores if entry["id"] == "2.1")
    ambiguous["steps"][1]["score"] = 0.9
    run: Run = run_fsm(mocks={"step_scores.json": scores})

    assert run.states[-1] == "operation_unresolved"
    assert run.states.count("operation_split") == 1
    assert "task 2.1: 2 step(s)" in run.stdout


def test_scores_for_a_step_missing_from_the_ontology_are_discarded(run_fsm):
    scores = all_single_strong()
    scores[0]["steps"][0]["uri"] = "urn:invented:Step"
    run: Run = run_fsm(mocks={"step_scores.json": scores})

    assert run.states == ["brief_received", "brief_structured", "operation_unresolved"]
    assert not (run.folder / "step_scores.json").exists()


def test_tasks_listing_that_breaks_the_contract_goes_to_people(run_fsm):
    run: Run = run_fsm(mocks={"tasks.json": [{"id": 1, "task": "No objective"}]})

    assert run.states == ["brief_received", "brief_structured", "operation_unresolved"]


def test_garbage_from_claude_does_not_advance_the_demand(run_fsm):
    run: Run = run_fsm(
        mocks={"tasks.json": None, "step_scores.json": None, "subtasks.json": None},
        claude_mode="garbage",
    )

    assert run.states == ["brief_received", "brief_structured", "operation_unresolved"]


def test_invented_steps_from_claude_are_not_trusted(run_fsm):
    run: Run = run_fsm(
        mocks={"tasks.json": None, "step_scores.json": None, "subtasks.json": None},
        claude_mode="unknown_step",
    )

    assert run.states == ["brief_received", "brief_structured", "operation_unresolved"]
    assert not (run.folder / "step_scores.json").exists()


def test_failing_claude_does_not_advance_the_demand(run_fsm):
    run: Run = run_fsm(mocks={"tasks.json": None, "step_scores.json": None, "subtasks.json": None})

    assert run.states == ["brief_received", "brief_structured", "operation_unresolved"]


def test_absent_claude_rejects_the_demand_without_interpretation(run_fsm):
    run: Run = run_fsm(
        mocks={"tasks.json": None, "step_scores.json": None, "subtasks.json": None},
        claude_mode="absent",
    )

    assert run.states == ["brief_received", "brief_structured", "rejected"]
    assert not (run.folder / "tasks.json").exists()


def test_path_is_a_connected_record_of_every_transition(run_fsm):
    run: Run = run_fsm()
    transitions = run.path["transitions"]

    for previous, current in zip(transitions, transitions[1:]):
        assert current["source"] == previous["target"]
    assert all(item["facts"] for item in transitions)
    assert transitions[-1]["facts"]["is_operation_validated"] is True
