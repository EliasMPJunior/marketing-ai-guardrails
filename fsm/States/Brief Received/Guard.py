"""Objective input checks for the ``brief_received`` state.

These checks validate the prompt as a readable text input. They do not decide
whether the marketing request is truthful, complete, or commercially valid.
"""

from pathlib import Path
import unicodedata


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROMPT_PATH = PROJECT_ROOT / "prompt.txt"
MAX_PROMPT_BYTES = 1024 * 1024


def validate_text(prompt: object) -> list[str]:
    """Report structural problems in a user-provided marketing prompt."""
    if not isinstance(prompt, str):
        return ["Prompt must be text."]

    if not prompt.strip():
        return ["Prompt is empty or contains only whitespace."]

    errors: list[str] = []
    if not any(character.isalnum() for character in prompt):
        errors.append("Prompt has no letters or digits (no meaningful textual input).")

    forbidden = {
        character
        for character in prompt
        if unicodedata.category(character) in {"Cc", "Cs"}
        and character not in "\t\n\r"
    }
    if forbidden:
        errors.append("Prompt contains invalid control or surrogate characters.")

    return errors


def validate_file(
    prompt_path: str | Path = DEFAULT_PROMPT_PATH,
    *,
    max_bytes: int = MAX_PROMPT_BYTES,
) -> list[str]:
    """Check existence, file type, size, UTF-8 decoding, and useful content."""
    path = Path(prompt_path)
    try:
        if not path.is_file():
            return [f"Prompt file does not exist or is not a regular file: {path}"]
        size = path.stat().st_size
        if size == 0:
            return ["Prompt file is empty."]
        if size > max_bytes:
            return [f"Prompt file exceeds the configured {max_bytes}-byte limit."]
        text = path.read_bytes().decode("utf-8-sig", errors="strict")
    except (OSError, ValueError, UnicodeError) as error:
        return [f"Prompt file cannot be read as UTF-8: {error}"]

    return validate_text(text)


def guard(prompt_path: str | Path = DEFAULT_PROMPT_PATH) -> bool:
    """Boolean predicate for use by an FSM transition guard."""
    return not validate_file(prompt_path)


if __name__ == "__main__":
    import sys

    issues = validate_file(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT_PATH)
    if issues:
        for issue in issues:
            print(f"FAIL: {issue}")
        raise SystemExit(1)
    print("PASS: Prompt is a readable, non-empty UTF-8 text file.")
