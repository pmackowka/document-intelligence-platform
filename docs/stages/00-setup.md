# Etap 0 — Setup środowiska

## Cel
Działające fundamenty: repozytorium git, środowisko Python, lokalny n8n, smoke test `claude -p`.

## Zakres / Definition of Done
- [x] `git init` + pierwszy commit (PRD, CLAUDE.md, struktura docs); prywatny remote na GitHubie
- [x] Struktura projektu (`config/`, `src/`, `data/{raw,pending,store,reports}`); drzewo i reguła prywatności ścieżek w CLAUDE.md
- [x] Środowisko Python (uv) — uv 0.11.29 (brew), Python 3.11.4, `uv sync` → `.venv/` + `uv.lock`, weryfikacja `uv run python` OK
- [x] `data/` w `.gitignore` — dokumenty medyczne nigdy nie trafiają do repo
- [x] n8n uruchomiony lokalnie (Docker Compose, v2.27.4) + dostęp Claude Code przez serwer MCP (scope local w `~/.claude.json`)
- [x] Pierwszy testowy workflow n8n (przez narzędzia n8n MCP) — `008 — Document Intelligence: pierwszy workflow testowy (MCP smoke test)`, Manual Trigger → Edit Fields; zbudowany, zwalidowany i uruchomiony (execution `success`)
- [x] Smoke test: wywołanie `claude -p "..."` z Pythona (subprocess), w tym `--model haiku` — `src/smoke_test_claude.py`, oba wywołania OK (model domyślny → `4`, Haiku → `cztery`)
- [x] (osobno, po MCP) upgrade n8n z 2.27.4 do najnowszej (2.30.7) — `docker compose pull && up -d`; migracje bazy czyste, klucz szyfrujący OK, 9 workflow całych, endpoint MCP ponownie Connected

## Notatki

### Git i repozytorium zdalne

**Decyzja:** git od pierwszego dnia, z prywatnym remote na GitHubie.

**Dlaczego:** metoda „PRD jako living document" wymaga commitów przy każdej zmianie zakresu; dokumentacja zawiera realne informacje zdrowotne właściciela → repo musi zostać prywatne (publiczna wersja portfolio = osobny, zredagowany wariant).

**Jak działa:** weryfikacja prywatności repo bez `gh`: `curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/<owner>/<repo>` — `404` bez autoryzacji oznacza repo prywatne (lub nieistniejące), `200` = publiczne.

**Pułapki:** `gh` CLI nie jest zainstalowane na tej maszynie — `brew install gh` przy domykaniu etapu.

### Struktura folderów i prywatność ścieżek

**Decyzja:** szkielet folderów utworzony z góry, przed kodem; `data/` ignorowane w `.gitignore` w całości (jeden wpis), nie per-plik.

**Dlaczego:** fizycznie istniejąca struktura egzekwuje regułę prywatności (`data/` = treść medyczna, poza gitem) lepiej niż sam zapis w CLAUDE.md — przyszła sesja nie wymyśli własnych ścieżek. Ignorowanie całego `data/` = „nowy artefakt medyczny automatycznie poza gitem" bez pamiętania o aktualizacji `.gitignore`. Pliki powstają dopiero w swoich etapach — bez stubów na zapas.

**Jak działa:** git nie śledzi pustych folderów → `.gitkeep` w `config/` i `src/`. Ścieżki ignorowane (`data/*`) nie istnieją w świeżym klonie w ogóle, więc kod pipeline'u musi tworzyć je przez `mkdir -p` przy starcie.

### Środowisko Python (uv)

**Decyzja:** `uv` zamiast `pip` + `venv` + `poetry`; instalacja przez Homebrew (nie skrypt curl). Zależności domenowe (Docling, Presidio, spaCy) **nie** instalowane teraz — dojdą w etapach 1 i 4.

**Dlaczego:** jedno narzędzie (środowisko, zależności, lockfile, wersja Pythona), znacznie szybsze przy ciężkim stacku; `uv.lock` w repo → reprodukowalne środowisko z klona jedną komendą. Homebrew: aktualizacje przez `brew upgrade` razem z resztą narzędzi. Etap 0 stawia tylko fundament (reguła „bez stubów na zapas").

**Jak działa:** `uv sync` czyta `pyproject.toml`, tworzy `.venv/` i zapisuje dokładne wersje do `uv.lock`. `uv run <komenda>` sam aktywuje `.venv` — bez ręcznego `source .venv/bin/activate` jak przy klasycznym `venv`.

**Pułapki:** `.venv/` jest w `.gitignore` (odtwarzalne z locka, duże) — do repo idą `pyproject.toml` + `uv.lock`, nie samo środowisko.

### Konfiguracja n8n na MacBooku (Docker)

**Decyzja:** n8n uruchamiane jako kontener Docker przez Docker Compose; dane trwałe w zewnętrznym wolumenie Docker.

**Dlaczego:** izolacja od systemu i czysty upgrade (podmiana obrazu bez utraty danych). Wolumen `external` przeżywa `docker compose down` i podmianę wersji obrazu — workflow i credentiale nie giną przy aktualizacji.

**Jak działa:** katalog `/Users/p/Documents/dev/n8n` zawiera dwa pliki konfiguracyjne:
- `docker-compose.yml` — definicja usługi: obraz `docker.n8n.io/n8nio/n8n` (bez tagu = `latest`), port `5678:5678` (UI + API + endpoint MCP `/mcp-server/http`), env (`GENERIC_TIMEZONE`/`TZ` Europe/Warsaw, `N8N_RUNNERS_ENABLED`, `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS`), `restart: unless-stopped`.
- `.env` — kopia zapasowa sekretów (`N8N_ENCRYPTION_KEY`, `N8N_API_KEY`). Uwaga: compose jej NIE wstrzykuje (brak `${...}` w pliku) — to backup, nie aktywna konfiguracja.

Dane trwałe: wolumen Docker `n8n_data` (`external: true`), zamontowany na `/home/node/.n8n` w kontenerze, fizycznie w `/var/lib/docker/volumes/n8n_data/_data`. Zawiera: `config` (klucz szyfrujący `encryptionKey`), `database.sqlite` (workflow + zaszyfrowane credentiale), `nodes`, `storage`, logi zdarzeń.

**Pułapki:**
- Realny klucz szyfrujący żyje w wolumenie (`/home/node/.n8n/config`), nie w `.env`. Odczyt: `docker exec n8n sh -c 'cat /home/node/.n8n/config'`. Gdyby kiedyś wstrzykiwać klucz przez env, musi DOKŁADNIE zgadzać się z tym z wolumenu — inaczej „Mismatching encryption keys" i credentiale się nie odszyfrują.
- `.env` jest w `.gitignore` katalogu n8n (`.env`, `*.env`) — sekrety nigdy do repo.
- Wolumen jest `external` → utworzony poza compose; `docker compose down -v` go NIE usunie (bezpieczne), ale ręczne `docker volume rm n8n_data` skasuje wszystkie workflow i credentiale.

### Upgrade n8n (podmiana obrazu Docker)

**Decyzja:** upgrade przez `docker compose pull && up -d` (obraz bez tagu = `latest`), z backupem wolumenu tuż przed startem. Wykonany: 2.27.4 → 2.30.7.

**Jak działa:** `pull` ściąga nowy obraz, `up -d` odtwarza kontener z tego obrazu; wolumen `external` (`n8n_data`) zostaje ten sam, więc workflow, credentiale i klucz szyfrujący przeżywają podmianę. n8n przy starcie sam uruchamia migracje bazy — w logach widoczne jako pary `Starting migration ...` / `Finished migration ...`.

**Pułapki:** migracje bazy są **jednokierunkowe** — po majorze downgrade obrazu może się wysypać na schemacie, dlatego backup wolumenu przed upgradem: `docker run --rm -v n8n_data:/data:ro -v <cel>:/backup alpine tar czf /backup/n8n.tar.gz -C /data .`. Rollback wymaga przypięcia starego tagu w compose (`image: docker.n8n.io/n8nio/n8n:2.27.4`), bo `latest` sam z siebie nie pozwala wrócić. Weryfikacja po upgradzie: logi (migracje + brak „Mismatching encryption keys"), `claude mcp list` (Connected) oraz lista workflow przez MCP (potwierdza, że dane całe).

### Dostęp Claude Code do n8n (serwer MCP)

**Decyzja:** dostęp przez **wbudowany serwer MCP n8n** (nie zewnętrzny proces npx), zasięg **local** (per projekt), token reuse z projektu Learning-Plan (jeden token na oba projekty — świadoma decyzja właściciela).

**Dlaczego:** local zamiast global, bo to serwer HTTP — global oznaczałby próbę połączenia z `localhost:5678` w każdej sesji każdego projektu (szum, gdy n8n nie działa). Reuse tokenu: zweryfikowany, localhost, niskie ryzyko.

**Jak działa:** MCP typu `http`, endpoint `http://localhost:5678/mcp-server/http`, autoryzacja nagłówkiem `Bearer <JWT>`. Serwer („n8n MCP Server" v1.1.0) wystawia `tools` + `resources` do budowania workflow przez n8n Workflow SDK. Dodanie: `claude mcp add n8n-mcp --scope local --transport http <url> --header "Authorization: Bearer <token>"`. Serwery MCP ładują się przy starcie sesji — po dodaniu potrzebny restart, by narzędzia `mcp__n8n-mcp__*` były dostępne.

**Pułapki:** token to sekret — konfiguracja trafia do `~/.claude.json` (poza repo), **nigdy** do `.mcp.json` w repo (byłby JWT w gicie, sprzeczne z „zero sekretów"). Weryfikacja połączenia: `claude mcp list` → status Connected.

### Budowa workflow przez serwer MCP n8n

**Decyzja:** workflow budowany kodem SDK (`@n8n/workflow-sdk`), nie klikaniem w UI ani surowym JSON-em wysyłanym do REST API.

**Dlaczego:** serwer MCP wymusza ścieżkę „napisz kod → zwaliduj → utwórz", więc workflow powstaje deterministycznie i wersjonowalnie z opisu, a nie ręcznym układaniem węzłów. To ten sam model pracy, który docelowo obsłuży orkiestrację pipeline'u (n8n woła Python/`claude -p`).

**Jak działa:** obowiązkowa kolejność narzędzi MCP — `get_sdk_reference` (składnia SDK) → `get_workflow_best_practices` (wzorce dla techniki) → `search_nodes` (znalezienie węzłów + dyskryminatory resource/operation/mode) → `get_node_types` (dokładne nazwy parametrów) → `validate_workflow` → `create_workflow_from_code`. Pominięcie `get_node_types` = zgadywanie parametrów = niepoprawny workflow. Kod to `workflow(id, name).add(trigger).to(node)`; węzły definiowane osobno, każdy z przykładowym `output` (kolejne węzły budują na nim wyrażenia). Utworzony workflow wpada domyślnie do projektu osobistego; egzekucję testową sprawdza się `execute_workflow` (mode `manual`) → `get_execution` (status `success` + dane węzła).

**Pułapki:** numer prefiksu to sekwencja unikatowa — `007` był już zajęty (workflow ClickUp), więc „kolejny" = `008`, nie `007`; przed utworzeniem trzeba sprawdzić `search_workflows`, bo dwa razy ten sam prefiks to cichy duplikat. Wyrażenia zawsze w `expr('{{ ... }}')` z cudzysłowami prostymi, nigdy w backtickach ani ze zmiennymi poza `{{ }}`.

### Podział odpowiedzialności: Python vs. n8n

**Decyzja:** cała logika biznesowa (OCR, standaryzacja, anonimizacja, ekstrakcja) w wersjonowanych plikach `.py`; n8n wyłącznie orkiestruje — trigger, kolejność, retry. Node n8n nigdy nie trzyma logiki.

**Dlaczego:**

- **Git** — kod w plikach jest wersjonowany i review'owalny; logika w node'ach żyje w SQLite w wolumenie Dockera, poza gitem.
- **Testy** — funkcje Pythona mają unit testy i debugger; snippet w polu node'a nie ma nic.
- **Biblioteki** — Docling / Presidio / spaCy `pl_core_news_lg` wymagają natywnego venv (uv); sandbox runnera n8n ich nie uniesie.
- **Brak lock-in** — logika przeżyje zmianę orkiestratora (n8n → Airflow/cron); w node'ach byłaby uwięziona.
- **Prywatność** — twardą regułę „nic do API przed Presidio" audytujesz w jednym miejscu w kodzie, nie po rozproszonych node'ach.

**Pułapka:** reguła „zero logiki w n8n" jest odrobinę surowsza niż konieczne (drobny routing dałoby się w n8n) — świadomie, jako bariera przed *logic creep*: w n8n logika lubi rozłazić się po node'ach, aż nikt nie wie, gdzie co jest. To kanoniczny wzorzec: orkiestrator cienki, ciężka praca w wersjonowanym kodzie (tak samo Airflow: DAG wiąże taski, task woła kod).

### Tryb headless `claude -p` i model kosztowy (Pro vs. tokeny API)

**Decyzja:** wywołania LLM w pipeline idą przez `claude -p "<prompt>"` uruchamiane jako subprocess z Pythona, na zalogowanej subskrypcji **Pro** — nigdy przez SDK Anthropic z kluczem API rozliczanym per token. Smoke test (`src/smoke_test_claude.py`) potwierdza tę ścieżkę dla modelu domyślnego i dla `--model haiku`.

**Jak działa (tryb headless):** `claude -p` (od *print*) to Claude Code bez interaktywnego TTY — bierze prompt, wykonuje zadanie i wypisuje samą odpowiedź na stdout, po czym kończy proces. To czyni go wywoływalnym jak każdy program CLI:

```python
subprocess.run(["claude", "-p", "Wyekstrahuj ustalenia z: ...", "--model", "haiku"],
               capture_output=True, text=True, check=True).stdout
```

Uwierzytelnia się zalogowaną sesją Pro (keychain / `~/.claude`), nie kluczem API — dlatego działa też jako proces zagnieżdżony (odpalony z wnętrza tej sesji Claude Code). n8n woła to samo jako komenda shell → zero logiki w n8n, cała inteligencja w jednym mechanizmie.

**Dlaczego (koszt — ze sprostowaniem założenia):** Pro to koszt stały (~20 USD/mies., ~17 przy rocznym); API to koszt zmienny per token. Ale wbrew intuicji samo przetworzenie 390 dokumentów przez API byłoby **tanie**, nie drogie. Szacunek jednego pełnego przebiegu (założenia: ~273 dok. narracyjnych × ~2 000 tok wejścia + ~500 tok wyjścia na dokument; ~117 strukturalnych to garść weryfikacji aliasów na Haiku ≈ +0,35 USD):

| Model ekstrakcji narracyjnej | Cennik (wej./wyj. za 1 MTok) | Koszt 1 przebiegu 390 dok. |
| --- | --- | --- |
| Haiku 4.5 | $1 / $5 | ~1,6 USD |
| Sonnet 5 | $3 / $15 (intro $2/$10 do 2026-08-31) | ~4 USD (~2,5 USD w promo) |
| Opus 4.8 | $5 / $25 | ~6,5 USD |

Jednorazowa obróbka archiwum to kilka dolarów — API by tu nie zrujnowało budżetu. Realną przewagę Pro robią dwie inne rzeczy:

1. **Iteracja:** pipeline nie odpala się raz. Dziesiątki przebiegów przy strojeniu ekstrakcji i walidacji na przykładach → koszt × N.

2. **Agentic coding:** budowa pipeline'u w Claude Code (jak ta sesja) to miliony tokenów na sesję przy dużym kontekście i wielu tool-callach. Przy Opus $5/$25 kilka intensywnych dni programowania szybko przebija roczny koszt Pro. To tu metrowanie tokenów eksploduje, a płaska subskrypcja spłaszcza koszt do przewidywalnej kwoty.

**Pułapki:** Pro ma limity przepustowości (okna 5-godzinne + tygodniowe), API nie — 390 dokumentów w jednym zrywie mogłoby uderzyć w limit Pro; przy human-in-the-loop (partie zatwierdzane ręcznie) to nieistotne, ale masowy backfill trzeba rozłożyć w czasie. Druga: `claude -p` niesie narzut własnego promptu systemowego Claude Code, więc realne zużycie tokenów na wywołanie jest wyższe niż sam prompt + dokument (bez znaczenia przy Pro, istotne gdyby ktoś liczył wariant API).

### Dokumentacja i konwencje projektu

**Decyzja:** reguły przekrojowe (workflow etapów, Mermaid, ścieżki) w CLAUDE.md, szczegóły w docs.

**Dlaczego:** CLAUDE.md jest ładowany automatycznie do każdej sesji — to jedyne miejsce z gwarancją przeczytania.

**Jak działa:** CLAUDE.md vs docs = progressive disclosure — krótka reguła zawsze w kontekście, pełna instrukcja doczytywana na żądanie (ten sam mechanizm co skille w Claude Code).

**Pułapki:** deklaracja w czacie ≠ wykonanie — model raz napisał „git init odhaczony rzeczywistością", nie edytując pliku etapu; stąd obowiązkowy workflow (checkbox odhaczany od razu po akcji). Polskie cudzysłowy `„..."` w etykietach Mermaid łamią parser GitHuba (`got 'STR'`, incydent w diagramie V5) — etykiety w `["..."]`, zero `"` w treści.
