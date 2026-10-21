"""Unit tests for the objective checks, loaded from their state folders."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

STATES: Path = Path(__file__).resolve().parents[1] / "fsm" / "states"


def load(state: str, module: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"{state}_{module}", STATES / state / f"{module}.py")
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


scores = load("operation_scored", "guard")
brief = load("brief_received", "guard")


def write_scores(folder: Path, content: Any) -> Path:
    (folder / "step_scores.json").write_text(json.dumps(content), encoding="utf-8")
    return folder / "brief.txt"


def entry(task_id: int, *values: float) -> dict:
    return {"id": task_id, "steps": [{"uri": f"urn:s{i}", "score": value} for i, value in enumerate(values)]}


def test_the_threshold_is_inclusive():
    assert scores.MIN_SCORE == 0.8
    assert scores.count_strong_steps(entry(1, 0.8, 0.79, 0.81)) == 2


def test_every_task_needs_at_least_one_strong_step(tmp_path):
    assert scores.every_task_has_strong_step(write_scores(tmp_path, [entry(1, 0.9, 0.9, 0.1), entry(2, 0.8, 0.1, 0.1)]))
    assert not scores.every_task_has_strong_step(write_scores(tmp_path, [entry(1, 0.9, 0.1, 0.1), entry(2, 0.7, 0.1, 0.1)]))


def test_every_task_needs_exactly_one_strong_step(tmp_path):
    assert scores.every_task_has_single_strong_step(write_scores(tmp_path, [entry(1, 0.9, 0.1, 0.1), entry(2, 0.8, 0.1, 0.1)]))
    assert not scores.every_task_has_single_strong_step(write_scores(tmp_path, [entry(1, 0.9, 0.9, 0.1)]))
    assert not scores.every_task_has_single_strong_step(write_scores(tmp_path, [entry(1, 0.1, 0.1, 0.1)]))


@pytest.mark.parametrize("content", [[], {"id": 1}, [{"id": 1}], [{"id": 1, "steps": [{"uri": "x"}]}]])
def test_unusable_scores_never_pass(tmp_path, content):
    path = write_scores(tmp_path, content)
    assert not scores.every_task_has_strong_step(path)
    assert not scores.every_task_has_single_strong_step(path)


def test_missing_scores_never_pass(tmp_path):
    assert not scores.every_task_has_strong_step(tmp_path / "brief.txt")


@pytest.mark.parametrize("text", ["", "   \n\t", "!!! ???", "bad\x00control"])
def test_prompt_guard_rejects_unusable_text(text):
    assert brief.validate_text(text)


def test_prompt_guard_accepts_the_project_prompt():
    prompt = Path(__file__).resolve().parents[1] / "prompt.txt"
    assert brief.guard(prompt)


def test_prompt_guard_rejects_missing_oversized_and_non_utf8_files(tmp_path):
    assert not brief.guard(tmp_path / "missing.txt")
    big = tmp_path / "big.txt"
    big.write_text("a" * 20, encoding="utf-8")
    assert brief.validate_file(big, max_bytes=10)
    binary = tmp_path / "binary.txt"
    binary.write_bytes(b"\xff\xfe\x00bad")
    assert not brief.guard(binary)
