"""Etap 4 — anonimizacja Presidio: polski NER (spaCy) + PESEL/telefon/e-mail -> spójne pseudonimy.

Reguła twarda z PRD: żaden tekst dokumentu nie trafia do zewnętrznego API przed anonimizacją
przez ten moduł. Skrypt (`main()`) liczy recall na złotym zbiorze z etapu 2, ale wypisuje
WYŁĄCZNIE zagregowane liczby — nigdy wartości PII ani dopasowane fragmenty tekstu.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import PhoneRecognizer

from ocr import ocr_markdown

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "narrative"
OCR_CACHE = ROOT / "data" / "interim" / "narrative-ocr"
ANON_OUT = ROOT / "data" / "interim" / "narrative-anon"

ENTITIES = ["PERSON", "LOCATION", "PHONE_NUMBER", "PL_PESEL", "EMAIL_ADDRESS"]

# Etykiety NER modelu pl_core_news_lg (korpus NKJP) -> standardowe encje Presidio.
# Model NIE używa PER/LOC/GPE z domyślnego mappingu Presidio — bez tego SpacyRecognizer
# zwraca zero trafień na nazwiskach/adresach mimo poprawnego działania samego NER-a.
_NER_MAPPING = {
    "persName": "PERSON",
    "placeName": "LOCATION",
    "geogName": "LOCATION",
    "orgName": "ORGANIZATION",
    "date": "DATE_TIME",
    "time": "DATE_TIME",
}

_TOKEN_PREFIX = {
    "PERSON": "PERSON",
    "LOCATION": "ADDRESS",
    "PHONE_NUMBER": "PHONE",
    "PL_PESEL": "PESEL",
    "EMAIL_ADDRESS": "EMAIL",
}


class PlAddressRecognizer(PatternRecognizer):
    """Adresy PL — spaCy NER (geogName/placeName) gubi numer domu i kod pocztowy całkowicie
    (znalezione empirycznie na złotym zbiorze etapu 2: recall LOCATION 24% bez tego).
    Generyczny wzorzec, zero PII w kodzie.
    """

    PATTERNS = [
        Pattern(
            "adres (ulica/aleja/plac + numer)",
            r"\b(?:ul\.|al\.|pl\.|os\.)\s*[A-ZŁŚŻŹĆŃÓĄĘ][\wąćęłńóśźż.-]*"
            r"(?:\s+[A-ZŁŚŻŹĆŃÓĄĘ][\wąćęłńóśźż.-]*)*\s+\d+[A-Za-z]?(?:/\d+)?\b",
            0.6,
        ),
        Pattern("kod pocztowy PL", r"\b\d{2}-\d{3}\b", 0.6),
    ]
    CONTEXT = ["adres", "zamieszkały", "zamieszkała", "kod pocztowy"]

    def __init__(self, supported_language: str = "pl", supported_entity: str = "LOCATION"):
        super().__init__(
            supported_entity=supported_entity,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


# V1 = jeden użytkownik: imię/adres/telefon pacjenta to STAŁE wartości powtarzające się w każdym
# dokumencie z tego samego źródła (LUX MED). NER samodzielnie ich nie łapie niezawodnie (empirycznie:
# PERSON 60%, LOCATION 44% recall na złotym zbiorze etapu 2) — deny-lista exact-match je domyka.
# Plik zawiera PII -> WYŁĄCZNIE lokalnie pod data/ (gitignored), wypełnia operator ręcznie (HITL),
# nigdy nie generowany/wypełniany automatycznie przez ten moduł.
DENYLIST_PATH = ROOT / "data" / "pending" / "known_pii_denylist.yml"


def _load_denylist_recognizers(path: Path) -> list[PatternRecognizer]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    recognizers = []
    for entity_type, values in data.items():
        patterns = [Pattern(f"denylist-{i}", re.escape(v), 0.95) for i, v in enumerate(values or []) if v]
        if patterns:
            recognizers.append(PatternRecognizer(
                supported_entity=entity_type, patterns=patterns, supported_language="pl",
            ))
    return recognizers


_ANALYZER: AnalyzerEngine | None = None


def _build_analyzer() -> AnalyzerEngine:
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "pl", "model_name": "pl_core_news_lg"}],
        "ner_model_configuration": {
            "model_to_presidio_entity_mapping": _NER_MAPPING,
            "low_confidence_score_multiplier": 0.4,
            "labels_to_ignore": ["ORGANIZATION", "DATE_TIME"],  # data badania (oś czasu) celowo zostaje
        },
    })
    nlp_engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["pl"])
    # PhoneRecognizer domyślnie nie zna regionu PL (DEFAULT_SUPPORTED_REGIONS bez "PL") -> zero trafień bez tego.
    analyzer.registry.add_recognizer(
        PhoneRecognizer(supported_language="pl", supported_regions=("PL",))
    )
    analyzer.registry.add_recognizer(PlAddressRecognizer())
    for rec in _load_denylist_recognizers(DENYLIST_PATH):
        analyzer.registry.add_recognizer(rec)
    return analyzer


def analyzer() -> AnalyzerEngine:
    global _ANALYZER
    if _ANALYZER is None:
        _ANALYZER = _build_analyzer()
    return _ANALYZER


def _resolve_overlaps(results):
    """Greedy: najwyższy score, potem najdłuższy span; odrzuca nachodzące (recognizery się dublują)."""
    ordered = sorted(results, key=lambda r: (-r.score, -(r.end - r.start)))
    accepted = []
    for r in ordered:
        if not any(r.start < a.end and a.start < r.end for a in accepted):
            accepted.append(r)
    return sorted(accepted, key=lambda r: r.start)


def anonymize_text(text: str) -> tuple[str, dict[str, str]]:
    """Zwraca (tekst_z_tokenami, mapping token->oryginał).

    Pseudonimizacja spójna: ta sama wartość (case-insensitive) w obrębie dokumentu
    zawsze dostaje ten sam token. `mapping` zawiera PII — traktować jak surowy dokument,
    nigdy nie drukować/logować jego zawartości.
    """
    results = analyzer().analyze(text=text, language="pl", entities=ENTITIES)
    spans = _resolve_overlaps(results)

    token_by_value: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}
    mapping: dict[str, str] = {}
    assigned = []
    for r in spans:
        original = text[r.start:r.end]
        key = (r.entity_type, original.strip().casefold())
        token = token_by_value.get(key)
        if token is None:
            prefix = _TOKEN_PREFIX.get(r.entity_type, r.entity_type)
            counters[prefix] = counters.get(prefix, 0) + 1
            token = f"{prefix}_{counters[prefix]:03d}"
            token_by_value[key] = token
            mapping[token] = original
        assigned.append((r.start, r.end, token))

    out = text
    for start, end, token in sorted(assigned, key=lambda t: t[0], reverse=True):
        out = out[:start] + token + out[end:]
    return out, mapping


# --- pomiar recall na złotym zbiorze (etap 4 DoD) ---

_WORD_OR_NUM = re.compile(r"[^\W\d_]{2,}|\d[\d-]*\d", re.UNICODE)


def _tokens(s: str) -> set[str]:
    """Rozbija wartość na jednostki >=2 znaki (słowa lub ciągi cyfr) — pojedyncza cyfra jest zbyt niejednoznaczna."""
    return {t.casefold() for t in _WORD_OR_NUM.findall(s)}


def _golden_category(key: str) -> str | None:
    k = key.upper()
    if k.startswith("PESEL"):
        return "PL_PESEL"
    if k.startswith("EMAIL"):
        return "EMAIL_ADDRESS"
    if k.startswith("PHONE"):
        return "PHONE_NUMBER"
    if "ADDRESS" in k:
        return "LOCATION"
    if (k.startswith("PERSON") or k.startswith("DOCTOR")) and not k.endswith(("_NPWZ", "_PWZ")):
        return "PERSON"
    return None  # poza zakresem DoD: DOB, nazwa placówki, NPWZ/REGON/NIP, nr badania


def score_document(raw_text: str, golden: dict[str, str]) -> dict[str, tuple[int, int]]:
    """Dla każdej kategorii encji: (zredagowane_jednostki, wszystkie_jednostki) po slowach/liczbach."""
    anon_text, _ = anonymize_text(raw_text)
    anon_norm = re.sub(r"\s+", " ", anon_text.casefold())

    totals: dict[str, list[int]] = {}
    for key, value in golden.items():
        if not value:
            continue
        category = _golden_category(key)
        if category is None:
            continue
        toks = _tokens(value)
        if not toks:
            continue
        redacted = sum(1 for t in toks if t not in anon_norm)
        bucket = totals.setdefault(category, [0, 0])
        bucket[0] += redacted
        bucket[1] += len(toks)
    return {k: (v[0], v[1]) for k, v in totals.items()}


def main() -> int:
    docs = sorted(p for p in RAW.iterdir() if p.is_file()) if RAW.exists() else []
    if not docs:
        print(f"Brak dokumentów w {RAW}", file=sys.stderr)
        return 1
    OCR_CACHE.mkdir(parents=True, exist_ok=True)
    ANON_OUT.mkdir(parents=True, exist_ok=True)

    grand_totals: dict[str, list[int]] = {}
    for doc in docs:
        raw_text = ocr_markdown(doc, OCR_CACHE)
        anon_text, _ = anonymize_text(raw_text)
        (ANON_OUT / (doc.stem + ".presidio.md")).write_text(anon_text, encoding="utf-8")

        golden_path = ANON_OUT / (doc.stem + ".golden.yml")
        if not golden_path.exists():
            print(f"{doc.name[:50]:50s} brak golden.yml — pomijam pomiar recall", flush=True)
            continue
        golden = yaml.safe_load(golden_path.read_text(encoding="utf-8")) or {}
        scores = score_document(raw_text, golden)

        parts = []
        for cat in ENTITIES:
            if cat in scores:
                red, tot = scores[cat]
                parts.append(f"{cat}={red}/{tot}")
        print(f"{doc.name[:50]:50s} " + " ".join(parts), flush=True)

        for cat, (red, tot) in scores.items():
            bucket = grand_totals.setdefault(cat, [0, 0])
            bucket[0] += red
            bucket[1] += tot

    print("\nRAZEM (zredagowane_jednostki / wszystkie_jednostki, per kategoria):")
    for cat in ENTITIES:
        if cat in grand_totals:
            red, tot = grand_totals[cat]
            pct = 100 * red / tot if tot else 0.0
            print(f"  {cat:15s} {red:3d}/{tot:3d}  ({pct:5.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
