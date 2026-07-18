"""Smoke test wywołań Claude Code w trybie headless (`claude -p`) z Pythona.

Sprawdza ścieżkę, której użyje pipeline: Python (a przez niego n8n) woła
`claude -p` jako komendę shell (subprocess), korzystając z zalogowanej
subskrypcji Pro — bez klucza API Anthropic i bez zakupu tokenów. Testuje
model domyślny oraz jawny `--model haiku` (tani model do weryfikacji aliasów).
"""
from __future__ import annotations

import subprocess


def run_claude(prompt: str, model: str | None = None, timeout: int = 120) -> str:
    """Wywołuje `claude -p <prompt>` i zwraca odpowiedź modelu (stdout).

    `model` (np. "haiku") mapuje na flagę `--model`. `check=True` sprawia, że
    kod wyjścia != 0 podnosi wyjątek — smoke test ma paść głośno, nie po cichu.
    """
    cmd = ["claude", "-p", prompt]
    if model:
        cmd += ["--model", model]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return result.stdout.strip()


def main() -> int:
    # Prompt trywialny i deterministyczny — potwierdza realną odpowiedź modelu
    # przy minimalnym zużyciu limitu Pro.
    prompt = "Odpowiedz jednym słowem, bez interpunkcji: ile to jest 2+2?"
    cases: list[tuple[str, str | None]] = [
        ("model domyślny", None),
        ("Haiku (--model haiku)", "haiku"),
    ]
    for label, model in cases:
        try:
            answer = run_claude(prompt, model=model)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"[FAIL] {label}: {exc}")
            return 1
        print(f"[OK]   {label}: {answer!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
