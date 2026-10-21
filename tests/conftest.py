"""Fixtures that run the statechart in an isolated copy of the project.

The capabilities find their mocks relative to their own location, so each
scenario copies ``fsm/`` and ``ontology/`` into a temporary project root and
controls the mocks there. The real repository files are never modified and
Claude Code is never called: a fake ``claude`` executable stands in for it.
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
ONTOLOGY_BASE: str = "https://github.com/EliasMPJunior/marketing-ai-guardrails/ontology/activities.ttl#"
MOCK_NAMES: Tuple[str, ...] = ("tasks.json", "step_scores.json", "subtasks.json")
FAKE_CLAUDE: str = """#!/usr/bin/env python3
import os, sys
mode = os.environ.get("FAKE_CLAUDE_MODE", "fail")
request = sys.argv[2]
if mode == "garbage":
    print("this is not json")
elif mode == "unknown_step" and request.startswith("Identify the tasks"):
    print('[{"id": 1, "task": "Select courses", "objective": "Shortlist"}]')
elif mode == "unknown_step":
    print('[{"id": 1, "steps": [{"uri": "urn:invented:Step", "score": 0.9}, '
          '{"uri": "urn:invented:Other", "score": 0.5}, {"uri": "urn:invented:Third", "score": 0.1}]}]')
else:
    sys.exit(1)
"""


@dataclass
class Run:
    """Outcome of one execution of the statechart."""

    folder: Path
    stdout: str
    returncode: int

    @property
    def path(self) -> Dict[str, Any]:
        return json.loads((self.folder / "path.json").read_text(encoding="utf-8"))

    @property
    def states(self) -> List[str]:
        """States entered, in order, starting with the initial one."""
        transitions: List[Dict[str, Any]] = self.path["transitions"]
        return [transitions[0]["source"]] + [item["target"] for item in transitions]

    def load(self, name: str) -> Any:
        return json.loads((self.folder / name).read_text(encoding="utf-8"))


def step_scores(task_id: Any, *scores: Tuple[str, float]) -> Dict[str, Any]:
    """Build the scores entry of one task from ontology step names."""
    return {
        "id": task_id,
        "steps": [{"uri": ONTOLOGY_BASE + name, "score": score} for name, score in scores],
    }


def repo_mock(name: str) -> Any:
    """Read one of the repository mocks."""
    return json.loads((REPO_ROOT / name).read_text(encoding="utf-8"))


@pytest.fixture
def run_fsm(tmp_path: Path):
    """Return a function that runs the statechart for a brief and a set of mocks."""

    def run(
        brief: str = (REPO_ROOT / "prompt.txt").read_text(encoding="utf-8"),
        mocks: Optional[Dict[str, Any]] = None,
        claude_mode: Optional[str] = None,
    ) -> Run:
        project: Path = tmp_path / "project"
        shutil.copytree(REPO_ROOT / "fsm", project / "fsm", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(REPO_ROOT / "ontology", project / "ontology")
        for name in MOCK_NAMES:
            shutil.copy(REPO_ROOT / name, project / name)
        for name, content in (mocks or {}).items():
            if content is None:
                (project / name).unlink()
            else:
                (project / name).write_text(json.dumps(content), encoding="utf-8")

        bin_dir: Path = tmp_path / "bin"
        bin_dir.mkdir()
        claude: Path = bin_dir / "claude"
        claude.write_text(FAKE_CLAUDE, encoding="utf-8")
        claude.chmod(0o755)
        if claude_mode == "absent":
            claude.unlink()
        environment: Dict[str, str] = {
            **os.environ,
            # With "absent" the PATH holds only the empty folder, so no claude exists.
            "PATH": str(bin_dir) if claude_mode == "absent" else f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_CLAUDE_MODE": claude_mode or "fail",
            "TERM": "dumb",
        }

        folder: Path = tmp_path / "trace"
        folder.mkdir()
        (folder / "brief.txt").write_text(brief, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(project / "fsm" / "main" / "executor.py"), "--etl-dir", str(folder)],
            capture_output=True, text=True, env=environment, stdin=subprocess.DEVNULL,
        )
        return Run(folder, completed.stdout, completed.returncode)

    return run
