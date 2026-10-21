#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
REQUIREMENTS="${ROOT_DIR}/requirements.txt"

if [[ ! -f "${REQUIREMENTS}" ]]; then
  printf '\033[31m[error]\033[0m Missing requirements.txt in %s\n' "${ROOT_DIR}" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf '\033[31m[error]\033[0m Python 3 is required.\n' >&2
  exit 1
fi

printf '\033[36m\n  ◆ Marketing AI Guardrails\033[0m\n'
printf '\033[2m  Preparing isolated Python environment...\033[0m\n\n'

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

PYTHON="${VENV_DIR}/bin/python"

# Textual is installed first so it can display the remaining installation steps.
"${PYTHON}" -m pip install --disable-pip-version-check --quiet 'textual>=0.80'

"${PYTHON}" - "${REQUIREMENTS}" "${ROOT_DIR}/prompt.txt" <<'PY'
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, LoadingIndicator, RichLog, Static

requirements = Path(sys.argv[1])
prompt_path = Path(sys.argv[2])


def load_prompt() -> str:
    content = prompt_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Prompt file is empty: {prompt_path}")
    return content


command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
           "--no-input", "--progress-bar", "off", "-r", str(requirements)]
console = Console()


class Installer(App):
    TITLE = "Marketing AI Guardrails"
    SUB_TITLE = "Setup and challenge"
    BINDINGS = [("q", "close_prompt", "Close"), ("enter", "close_prompt", "Continue")]
    prompt_ready = False
    CSS = """
    Screen { background: #0d1727; color: #e6f1ff; }
    #banner { height: 3; content-align: center middle; background: #13344b;
              color: #53e9d6; text-style: bold; }
    #message { height: 3; padding: 1 2; color: #d5e4f5; }
    #spinner { height: 3; color: #53e9d6; }
    #details { height: 1fr; margin: 1 2; border: round #238eaa;
               background: #101f31; padding: 0 1; }
    #challenge {
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

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("◆  MARKETING AI GUARDRAILS  ◆", id="banner")
        yield Static("[1/2] Installing project dependencies...", id="message")
        yield LoadingIndicator(id="spinner")
        yield RichLog(id="details", highlight=False, wrap=True, auto_scroll=True)
        yield Static("", id="challenge")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.install(), exclusive=True)

    def action_close_prompt(self) -> None:
        if self.prompt_ready:
            self.exit(return_code=0)

    async def install(self) -> None:
        details = self.query_one("#details", RichLog)
        message = self.query_one("#message", Static)
        details.write(Text("→ Resolving packages from requirements.txt", style="bold cyan"))
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert process.stdout is not None
            async for raw_line in process.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
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
            prompt_text = load_prompt()
        except (OSError, ValueError) as error:
            message.update("✗ Could not load prompt.txt.")
            details.write(Text(str(error), style="bold red"))
            await asyncio.sleep(1.2)
            self.exit(return_code=1)
            return

        details.display = False
        challenge = self.query_one("#challenge", Static)
        # Use native Textual styling instead of nesting a Rich Panel in a
        # previously hidden Static widget (which could display as an empty box).
        challenge.display = True
        challenge.update(
            Text(
                "◆  THE CHALLENGE  ◆\n\n" + prompt_text,
                style="bold bright_white",
                justify="center",
            )
        )
        message.update("✓ Setup complete. Challenge from prompt.txt (Enter or Q to close).")
        self.prompt_ready = True
        self.refresh(layout=True)


def run_without_tui() -> int:
    console.print(Panel.fit(
        "[bold cyan]Marketing AI Guardrails[/]\n"
        "[dim]Installing dependencies from requirements.txt[/]",
        border_style="cyan", title="Setup"))
    code = subprocess.call(command)
    return code


CLAUDE_INSTRUCTION = (
    "Identify the tasks with clear objectives in the text below and deliver them "
    "as a JSON listing. Answer with JSON only: an array of objects with the keys "
    '"id", "task" and "objective". No prose and no code fences.'
)


def ask_claude(prompt_text: str) -> int:
    claude = shutil.which("claude")
    if claude is None:
        console.print(Panel.fit(
            "[bold red]✗ Claude Code executable not found in PATH.[/]",
            border_style="red", title="Error"))
        return 1
    console.print(Panel.fit(
        "[bold cyan]Marketing AI Guardrails[/]\n"
        "[dim]Asking Claude Code for the tasks with clear objectives[/]",
        border_style="cyan", title="Claude Code"))
    return subprocess.call([claude, "-p", f"{CLAUDE_INSTRUCTION}\n\n{prompt_text}"])


interactive = (
    sys.stdin.isatty()
    and sys.stdout.isatty()
    and os.environ.get("TERM") not in (None, "dumb")
)
if interactive:
    app = Installer()
    app.run(inline=True)
    exit_code = app.return_code or 0
else:
    exit_code = run_without_tui()

if exit_code == 0:
    # Show the prompt in the terminal after the TUI closes, too. This makes
    # the actual challenge readable in VS Code's scrollback in all modes.
    try:
        prompt_text = load_prompt()
    except (OSError, ValueError) as error:
        console.print(f"[bold red]✗ Unable to read prompt.txt: {error}[/]")
        sys.exit(1)
    console.print(Panel(
        Text(prompt_text, style="bold bright_white", justify="center"),
        border_style="bright_cyan",
        title="[bold bright_cyan]◆  THE CHALLENGE  ◆[/]",
        subtitle="prompt.txt",
        padding=(1, 3),
    ))
    console.print(Panel.fit(
        "[bold green]✓ Python dependencies installed successfully[/]\n"
        "[dim]Virtual environment:[/] [cyan].venv[/]\n"
        "[dim]To activate:[/] [white]source .venv/bin/activate[/]",
        border_style="green", title="Ready"))
    exit_code = ask_claude(prompt_text)
else:
    console.print(Panel.fit(
        f"[bold red]✗ Installation failed (exit code {exit_code}).[/]",
        border_style="red", title="Error"))
sys.exit(exit_code)
PY
