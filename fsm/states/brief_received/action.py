"""Capability invoked when ``brief_received`` accepts the prompt.

The capability produces the tasks listing for the accepted brief and writes it
to the run folder. It calls the Claude Code executable; while ``tasks.json``
exists at the project root, that file is used as a mock to avoid spending tokens
during development and tests. Deciding whether the prompt is valid remains the
job of the state's guard.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.panel import Panel

MOCK_TASKS_PATH: Path = Path(__file__).resolve().parents[3] / "tasks.json"
TASKS_FILE_NAME: str = "tasks.json"
CLAUDE_INSTRUCTION = (
    "Identify the tasks with clear objectives in the text below and deliver them "
    "as a JSON listing. Answer with JSON only: an array of objects with the keys "
    '"id", "task" and "objective". No prose and no code fences.'
)

console = Console()


def action(brief_path: Union[str, Path]) -> bool:
    """Write the tasks listing for the accepted brief into the run folder."""
    brief_file: Path = Path(brief_path)
    tasks_text: str
    if MOCK_TASKS_PATH.is_file():
        tasks_text = MOCK_TASKS_PATH.read_text(encoding="utf-8")
    else:
        claude: Optional[str] = shutil.which("claude")
        if claude is None:
            console.print(Panel.fit(
                "[bold red]✗ Claude Code executable not found in PATH.[/]",
                border_style="red", title="Error"))
            return False
        console.print(Panel.fit(
            "[bold cyan]Marketing AI Guardrails[/]\n"
            "[dim]Asking Claude Code for the tasks with clear objectives[/]",
            border_style="cyan", title="Claude Code"))
        prompt_text: str = brief_file.read_text(encoding="utf-8-sig")
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            [claude, "-p", f"{CLAUDE_INSTRUCTION}\n\n{prompt_text}"],
            capture_output=True,
            text=True,
        )
        tasks_text = completed.stdout

    (brief_file.parent / TASKS_FILE_NAME).write_text(tasks_text, encoding="utf-8")

    return True
