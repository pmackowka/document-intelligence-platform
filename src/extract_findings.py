"""Etap 2 — walidacja ekstrakcji narracyjnej.

Dla każdego zanonimizowanego opisu (`data/interim/narrative-anon/*.md`) woła
`claude -p` (model domyślny abonamentu Pro), prosząc o wyodrębnienie ustaleń do
schematu. Wynik zapisuje jako `<nazwa>.findings.json` obok źródła.

Zasada: wejściem są WYŁĄCZNIE pliki .md (tokeny zamiast PII) — nigdy .golden.yml.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANON = ROOT / "data" / "interim" / "narrative-anon"

# Prompt ekstrakcyjny — "extract, don't infer". Pola zgodne z PRD.
PROMPT = """\
Zadanie: ekstrakcja ustaleń (findings) z opisu badania medycznego do JSON.
NIE diagnozuj, NIE interpretuj, NIE dopowiadaj — wyodrębnij wyłącznie to, co napisano w opisie.

Zwróć TABLICĘ obiektów JSON. Każdy obiekt = jedno ustalenie, pola:
- "finding": krótki opis ustalenia (co stwierdzono), string
- "location": lokalizacja anatomiczna, string lub null
- "measurement_value": wartość liczbowa pomiaru, number lub null
- "measurement_unit": jednostka pomiaru (np. "mm", "ml", "%"), string lub null
- "status": jeden z: "obecny" (patologia stwierdzona) | "prawidłowy" (opisane jako w normie/bez zmian) | "nieobecny" (wykluczone)
- "exam_type": typ badania z nagłówka dokumentu, string
- "exam_date": data WYKONANIA badania w formacie YYYY-MM-DD, string

Zasady:
- Jedno ustalenie = jeden obiekt. Rozbij złożone zdania na osobne ustalenia.
- Negacje i normy ("bez zmian", "prawidłowy", "nie stwierdzono", "niepowiększona") zapisz jako osobne ustalenia ze statusem "prawidłowy" lub "nieobecny" — NIE pomijaj ich.
- Pomiary: jeśli podano wymiary (np. "22x23x37 mm") lub objętość (np. "V=9,6 ml"), zapisz measurement_value + measurement_unit. Wartości z przecinkiem dziesiętnym zamień na kropkę.
- Tokeny PERSON_001, DOCTOR_001, FACILITY_001, ADDRESS_001, PESEL_001 itd. to zanonimizowane PII — IGNORUJ je, nie są ustaleniami.
- exam_type i exam_date bierz z nagłówka dokumentu.
- Zwróć WYŁĄCZNIE poprawny JSON (tablica), bez komentarza, bez ```-fence.

OPIS BADANIA:
---
"""


def run_claude(prompt: str, timeout: int = 180) -> str:
    """Woła headless Claude Code; zwraca stdout. Model domyślny (abonament Pro)."""
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True, text=True, timeout=timeout, check=True,
    )
    return result.stdout.strip()


def strip_fence(s: str) -> str:
    """Usuwa opakowanie ```json ... ``` jeśli model je dodał (LLM często je dokłada mimo instrukcji)."""
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


def main() -> int:
    files = sorted(ANON.glob("*.md"))
    if not files:
        print("Brak plików .md w narrative-anon/", file=sys.stderr)
        return 1

    for f in files:
        doc = f.read_text(encoding="utf-8")
        raw = run_claude(PROMPT + doc + "\n---\n")
        out = ANON / (f.stem + ".findings.json")
        # spróbuj sparsować; zapisz surowo, żeby ocenić nawet gdy JSON jest niepełny
        try:
            parsed = json.loads(strip_fence(raw))
            out.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            n = len(parsed) if isinstance(parsed, list) else "?"
            print(f"[OK   ] {f.name[:48]:48s} → {n} ustaleń", flush=True)
        except json.JSONDecodeError as e:
            out.write_text(raw, encoding="utf-8")
            print(f"[JSON?] {f.name[:48]:48s} → niepoprawny JSON ({e}); zapisano surowo", flush=True)

    print(f"\nGotowe → {ANON}/*.findings.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
