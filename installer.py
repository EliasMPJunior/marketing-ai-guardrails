"""Provision the isolated environment, present the marketing brief, and hand it to Claude Code."""

import asyncio
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, LoadingIndicator, RichLog, Static

CLAUDE_INSTRUCTION = (
    "Identify the tasks with clear objectives in the text below and deliver them "
    "as a JSON listing. Answer with JSON only: an array of objects with the keys "
    '"id", "task" and "objective". No prose and no code fences.'
)

console = Console()


def load_prompt(prompt_path: Path) -> str:
    content: str = prompt_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Prompt file is empty: {prompt_path}")
    return content


def install_command(requirements_path: Path) -> List[str]:
    return [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--progress-bar",
        "off",
        "-r",
        str(requirements_path),
    ]


class Installer(App):
    TITLE = "Marketing AI Guardrails"
    SUB_TITLE = "Setup and marketing brief"
    BINDINGS = [("q", "close_prompt", "Close"), ("enter", "close_prompt", "Continue")]
    CSS = """
    Screen { background: #0d1727; color: #e6f1ff; }
    #banner { height: 3; content-align: center middle; background: #13344b;
              color: #53e9d6; text-style: bold; }
    #message { height: 3; padding: 1 2; color: #d5e4f5; }
    #spinner { height: 3; color: #53e9d6; }
    #details { height: 1fr; margin: 1 2; border: round #238eaa;
               background: #101f31; padding: 0 1; }
    #user_prompt {
        display: none;
        height: auto;
        min-height: 9;
        margin: 1 2;
        padding: 2 3;
        border: round #53e9d6;
        background: #112d3b;
        color: #ffffff;
        text-style: bold;
        content-align: center middle;
    }
    Footer { background: #13344b; }
    """

    def __init__(self, requirements_path: Path, prompt_path: Path) -> None:
        super().__init__()
        self._requirements_path: Path = requirements_path
        self._prompt_path: Path = prompt_path
        self._prompt_ready: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("◆  MARKETING AI GUARDRAILS  ◆", id="banner")
        yield Static("[1/2] Installing project dependencies...", id="message")
        yield LoadingIndicator(id="spinner")
        yield RichLog(id="details", highlight=False, wrap=True, auto_scroll=True)
        yield Static("", id="user_prompt")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.install(), exclusive=True)

    def action_close_prompt(self) -> None:
        if self._prompt_ready:
            self.exit(return_code=0)

    async def install(self) -> None:
        details: RichLog = self.query_one("#details", RichLog)
        message: Static = self.query_one("#message", Static)
        details.write(Text("→ Resolving packages from requirements.txt", style="bold cyan"))
        code: int
        try:
            process = await asyncio.create_subprocess_exec(
                *install_command(self._requirements_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert process.stdout is not None
            async for raw_line in process.stdout:
                line: str = raw_line.decode("utf-8", errors="replace").rstrip()
                if line:
                    details.write(Text(line, style="bright_black"))
            code = await process.wait()
        except OSError as error:
            details.write(Text(str(error), style="bold red"))
            code = 1

        self.query_one("#spinner", LoadingIndicator).display = False
        if code != 0:
            message.update("✗ Dependency installation failed. Review the log above.")
            details.write(Text(f"✗ pip exited with status {code}", style="bold red"))
            await asyncio.sleep(1.2)
            self.exit(return_code=code)
            return

        try:
            prompt_text: str = load_prompt(self._prompt_path)
        except (OSError, ValueError) as error:
            message.update("✗ Could not load prompt.txt.")
            details.write(Text(str(error), style="bold red"))
            await asyncio.sleep(1.2)
            self.exit(return_code=1)
            return

        details.display = False
        prompt_widget: Static = self.query_one("#user_prompt", Static)
        # Use native Textual styling instead of nesting a Rich Panel in a
        # previously hidden Static widget (which could display as an empty box).
        prompt_widget.display = True
        prompt_widget.update(
            Text(
                "◆  MARKETING USER PROMPT  ◆\n\n" + prompt_text,
                style="bold bright_white",
                justify="center",
            )
        )
        message.update("✓ Setup complete. Marketing brief from prompt.txt (Enter or Q to close).")
        self._prompt_ready = True
        self.refresh(layout=True)


def run_without_tui(requirements_path: Path) -> int:
    console.print(Panel.fit(
        "[bold cyan]Marketing AI Guardrails[/]\n"
        "[dim]Installing dependencies from requirements.txt[/]",
        border_style="cyan", title="Setup"))
    code: int = subprocess.call(install_command(requirements_path))
    return code


def ask_claude(prompt_text: str) -> int:
    claude: Optional[str] = shutil.which("claude")
    if claude is None:
        console.print(Panel.fit(
            "[bold red]✗ Claude Code executable not found in PATH.[/]",
            border_style="red", title="Error"))
        return 1
    console.print(Panel.fit(
        "[bold cyan]Marketing AI Guardrails[/]\n"
        "[dim]Asking Claude Code for the tasks with clear objectives[/]",
        border_style="cyan", title="Claude Code"))

    TASKS_PATH: Path = Path(__file__).with_name("tasks.json")
    tasks: List[Dict[str, Any]] = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    print(json.dumps(tasks, indent=2, ensure_ascii=False))

    # return subprocess.call([claude, "-p", f"{CLAUDE_INSTRUCTION}\n\n{prompt_text}"])
    return 0


def run_fsm(prompt_text: str) -> int:
    console.print(Panel.fit(
        "[bold cyan]Marketing AI Guardrails[/]\n"
        "[dim]Running the marketing operation statechart[/]",
        border_style="cyan", title="FSM"))
    executor_path: Path = Path(__file__).parent / "fsm" / "main" / "executor.py"
    return subprocess.call([sys.executable, str(executor_path)])


def main() -> int:
    requirements_path: Path = Path(sys.argv[1])
    prompt_path: Path = Path(sys.argv[2])

    interactive: bool = (
        sys.stdin.isatty()
        and sys.stdout.isatty()
        and os.environ.get("TERM") not in (None, "dumb")
    )
    exit_code: int
    if interactive:
        app = Installer(requirements_path, prompt_path)
        app.run(inline=True)
        exit_code = app.return_code or 0
    else:
        exit_code = run_without_tui(requirements_path)

    if exit_code != 0:
        console.print(Panel.fit(
            f"[bold red]✗ Installation failed (exit code {exit_code}).[/]",
            border_style="red", title="Error"))
        return exit_code

    # Show the prompt in the terminal after the TUI closes, too. This makes
    # the marketing brief readable in VS Code's scrollback in all modes.
    try:
        prompt_text: str = load_prompt(prompt_path)
    except (OSError, ValueError) as error:
        console.print(f"[bold red]✗ Unable to read prompt.txt: {error}[/]")
        return 1
    console.print(Panel(
        Text(prompt_text, style="bold bright_white", justify="center"),
        border_style="bright_cyan",
        title="[bold bright_cyan]◆  MARKETING USER PROMPT  ◆[/]",
        subtitle="prompt.txt",
        padding=(1, 3),
    ))
    console.print(Panel.fit(
        "[bold green]✓ Python dependencies installed successfully[/]\n"
        "[dim]Virtual environment:[/] [cyan].venv[/]\n"
        "[dim]To activate:[/] [white]source .venv/bin/activate[/]",
        border_style="green", title="Ready"))
    claude_code: int = ask_claude(prompt_text)
    if claude_code != 0:
        return claude_code
    return run_fsm(prompt_text)


if __name__ == "__main__":
    sys.exit(main())
