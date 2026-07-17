# Document Intelligence Platform
## Roadmap projektu AI Engineering

---

# Cel projektu

Zbudowanie własnej platformy do bezpiecznego przetwarzania dokumentów, która:

- działa lokalnie na MacBooku,
- wykorzystuje n8n jako orchestrator,
- wykorzystuje Python jako silnik przetwarzania,
- anonimizuje dane osobowe,
- przygotowuje dane do analizy przez Frontier Models,
- w przyszłości może zostać rozszerzona o RAG, MCP oraz architekturę agentową.

Projekt ma dwa cele.

1. Rozwiązuje realny problem (analiza własnych dokumentów).
2. Uczy technologii wykorzystywanych obecnie przez AI Engineerów.

---

# Docelowa architektura

```
                         ┌────────────────────┐
                         │      n8n           │
                         │ Workflow Engine    │
                         └─────────┬──────────┘
                                   │
                    upload / folder / webhook
                                   │
                                   ▼
                      Python Document Pipeline
                                   │
        ┌──────────────┬───────────────┬──────────────┐
        ▼              ▼               ▼
     Docling     Apple Vision      OCR Engine
                                   │
                                   ▼
                          Markdown + JSON
                                   │
                                   ▼
                          Microsoft Presidio
                                   │
                                   ▼
                           Pseudonimizacja
                                   │
                  ┌────────────────┴──────────────┐
                  ▼                               ▼
          Anonymous Markdown              Anonymous JSON
                  │                               │
                  └──────────────┬────────────────┘
                                 ▼
                     GPT / Claude / Gemini
                                 │
                                 ▼
                         Markdown Report
```

---

# Dlaczego n8n?

n8n NIE wykonuje OCR.

n8n NIE wykonuje analizy AI.

n8n odpowiada wyłącznie za orkiestrację.

Przykładowy workflow:

```
Nowy dokument

↓

Python

↓

OCR

↓

Standaryzacja

↓

Presidio

↓

LLM

↓

Zapis raportu

↓

Powiadomienie
```

Jest to odpowiednik Airflow dla świata AI Workflow.

---

# Dlaczego Python?

Python zawiera całą logikę biznesową.

Python odpowiada za:

- OCR
- przetwarzanie dokumentów
- standaryzację
- normalizację
- anonimizację
- zapis JSON
- zapis Markdown

n8n jedynie uruchamia kolejne moduły.

---

# Etap OCR

Preferowane narzędzia

## Docling

- IBM
- Open Source
- Markdown
- JSON
- analiza układu dokumentu
- obsługa tabel

To główny silnik projektu.

---

## Apple Vision Framework

Natywny OCR Apple.

Najlepiej działa na:

- HEIC
- JPG
- PNG

Docling potrafi wykorzystywać go jako backend OCR.

---

# Etap standaryzacji

To najważniejszy moduł całego projektu.

Nie polega na regexach.

Polega na normalizacji danych.

Cel:

```
Fe

Iron

Żelazo

Serum Iron

↓

iron
```

---

# Architektura standaryzacji

```
Markdown

↓

Dictionary Mapping

↓

Regex

↓

LLM Verification

↓

Canonical JSON
```

---

# Warstwa 1

## Dictionary Mapping

Najważniejszy element.

Powstaje plik

```
aliases.yml
```

Przykład

```yaml
iron:

  aliases:

    - Fe

    - Iron

    - Żelazo

    - Serum Iron

    - Fe Serum
```

Python wyszukuje alias.

Jeżeli znajdzie:

```
Fe

↓

iron
```

---

# Warstwa 2

Regex

Regex NIE służy do rozpoznawania badań.

Regex służy do wyciągania wartości.

Przykład

```
Hb: 13.2

↓

13.2
```

lub

```
CRP........0,18

↓

0.18
```

---

# Warstwa 3

LLM Verification

Jeżeli pojawia się nieznana nazwa:

```
Fe ICP-MS
```

Python wysyła ją do małego modelu.

Prompt:

```
Czy poniższa nazwa oznacza któreś z badań?

iron

ferritin

crp

hemoglobin
```

Model odpowiada

```
iron
```

Python zapisuje wynik.

Operator jedynie zatwierdza.

---

# Projekt uczy się sam

Po pierwszych dokumentach

```
Fe

↓

iron
```

Po kolejnych

```
Fe Serum

↓

iron
```

Po miesiącu

```
Iron (ICP-MS)

↓

iron
```

Lista aliasów stale rośnie.

Kod praktycznie się nie zmienia.

---

# Standaryzacja jednostek

Analogicznie.

```
ug/dL

↓

ug/dL
```

```
µmol/L

↓

ug/dL
```

Python dokonuje konwersji.

---

# Zakres referencyjny

Różne laboratoria zapisują go różnie.

```
15-150

15 – 150

15 do 150
```

Po normalizacji

```json
{
    "reference_low":15,
    "reference_high":150
}
```

---

# Dlaczego YAML zamiast kodu?

Cała wiedza domenowa trafia do plików.

```
medical_schema/

aliases.yml

units.yml

reference_ranges.yml

laboratories.yml
```

Python pozostaje uniwersalnym silnikiem.

Dodanie nowego laboratorium nie wymaga zmiany kodu.

---

# Wyjście

Projekt tworzy dwa formaty.

## Markdown

Do LLM.

## JSON

Do

- SQL
- Python
- wykresów
- statystyk

---

# Presidio

Microsoft Presidio wykrywa:

- nazwiska
- adresy
- telefony
- PESEL
- e-mail

Przykład

```
Jan Kowalski

↓

PERSON_001
```

---

# Pierwsza wersja projektu

## Version 1

✅ n8n

✅ Python

✅ Docling

✅ Apple Vision

✅ Markdown

✅ JSON

✅ Presidio

✅ GPT / Claude

Efekt:

Bezpieczna analiza dokumentów.

---

# Version 2

Dodajemy RAG.

Nowe elementy

```
Chunking

↓

Embedding

↓

Vector Database

↓

Retriever

↓

LLM
```

Możliwe bazy

- Qdrant
- ChromaDB

Kompetencje

- Embedding
- Semantic Search
- RAG

---

# Version 3

Przeniesienie do chmury.

Dodajemy

- FastAPI
- Docker
- Cloud Run

n8n wywołuje endpoint HTTP.

---

# Version 4

Dodajemy MCP.

Projekt staje się serwerem MCP.

Może udostępniać dokumenty:

- Claude Code
- ChatGPT
- Codex
- Cursor
- inne klienty MCP

---

# Version 5

Dodajemy architekturę agentową.

Do wyboru:

- LangGraph
- OpenAI Agents SDK

Agent potrafi:

- wyszukiwać dokumenty,
- analizować historię,
- wykonywać wieloetapowe zadania,
- planować kolejne kroki.

---

# Rozszerzenia domenowe

Ta sama platforma może obsługiwać:

## Medical

wyniki badań

---

## Legal

umowy

NDA

pisma

---

## Finance

faktury

raporty

---

## HR

CV

oceny

umowy

---

## Technical

instrukcje

manuale

PDF

---

# Kompetencje zdobywane podczas projektu

| Etap | Kompetencja |
|------|-------------|
| n8n | Workflow Automation |
| Python | Data Engineering |
| Docling | Document AI |
| OCR | Computer Vision |
| Markdown | Knowledge Representation |
| JSON | Structured Data |
| YAML | Configuration-driven Design |
| Presidio | Privacy Engineering |
| GPT/Claude | Prompt Engineering |
| RAG | Retrieval-Augmented Generation |
| FastAPI | API Development |
| Cloud Run | Cloud Deployment |
| MCP | AI Integration |
| LangGraph / Agents SDK | Agentic AI |

---

# Dlaczego taka kolejność?

Każda wersja kończy się działającym produktem.

Version 1 daje wartość użytkową.

Version 2 dodaje inteligentne wyszukiwanie.

Version 3 umożliwia wdrożenie produkcyjne.

Version 4 otwiera platformę na ekosystem AI.

Version 5 wprowadza pełnoprawnych agentów AI.

Dzięki temu projekt rozwija się ewolucyjnie, bez konieczności przepisywania wcześniejszych modułów.
