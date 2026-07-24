# Etap 0 — Setup środowiska

> **Uwaga (PRD v1.2):** n8n został później usunięty z zakresu V1 — lokalny kontener Docker (Linux) nie odpala Apple Vision (macOS). Checkboxy i notatki n8n poniżej to **rzetelny zapis wykonanej pracy** (instancja powstała i **nadal istnieje**, współdzielona z projektem Learning-Plan — `docs/n8n-backup-restore.md`), nie usuwamy ich. W V1 pipeline uruchamia operator z terminala; n8n jako kandydat na przyszłość — `docs/roadmap.md`.

## Cel
Działające fundamenty: repozytorium git, środowisko Python, lokalny n8n, smoke test `claude -p`.

Sedno: postawić i **zweryfikować** warstwę, na której stanie cała reszta — zanim napiszemy pierwszą linijkę logiki. Każdy element to prerekwizyt czegoś dalej:
- **git + prywatny remote** — PRD jako living document (commit przy każdej zmianie zakresu); treść medyczna nigdy w repo;
- **środowisko Python (uv)** — reprodukowalny stack pod Docling z jednego locka;
- **n8n lokalnie + MCP** — orkiestrator osiągalny z Claude Code, budowany kodem, nie klikaniem;
- **smoke test `claude -p`** — dowód, że headless na abonamencie Pro działa, zanim się na nim oprzemy.

„Done" = te fundamenty stoją i są sprawdzone, nie tylko zainstalowane.

## Zakres / Definition of Done
- [x] `git init` + pierwszy commit (PRD, CLAUDE.md, struktura docs); prywatny remote na GitHubie
- [x] Struktura projektu (`config/`, `src/`, `data/{raw,pending,store,reports}`); drzewo i reguła prywatności ścieżek w CLAUDE.md
- [x] Środowisko Python (uv) — uv 0.11.29 (brew), Python 3.11.4, `uv sync` → `.venv/` + `uv.lock`, weryfikacja OK
- [x] `data/` w `.gitignore` — dokumenty medyczne nigdy nie trafiają do repo
- [x] n8n uruchomiony lokalnie (Docker Compose, v2.27.4) + dostęp Claude Code przez serwer MCP (scope local w `~/.claude.json`)
- [x] Pierwszy testowy workflow n8n (przez MCP) — `008 — ... pierwszy workflow testowy`, Manual Trigger → Edit Fields; zbudowany, zwalidowany i uruchomiony (execution `success`)
- [x] Smoke test: `claude -p "..."` z Pythona (subprocess), w tym `--model haiku` — `src/smoke_test_claude.py`, oba wywołania OK
- [x] Upgrade n8n 2.27.4 → 2.30.7 — `docker compose pull && up -d`; migracje czyste, klucz szyfrujący OK, 9 workflow całych, MCP ponownie Connected
- [x] Backup środowiska n8n — procedura w `docs/n8n-backup-restore.md`; pierwszy backup wykonany i zweryfikowany (tar wolumenu + compose + `.env` na Google Drive, restart czysty, healthz 200)

## Notatki

### Git i repozytorium zdalne

**Decyzja:** git od pierwszego dnia, z prywatnym remote na GitHubie.

**Dlaczego:** „PRD jako living document" wymaga commitów przy każdej zmianie zakresu; dokumentacja zawiera realne dane zdrowotne → repo prywatne (publiczne portfolio = osobny, zredagowany wariant).

**Jak działa:** weryfikacja prywatności repo bez `gh`: `curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/<owner>/<repo>` — `404` bez autoryzacji = prywatne, `200` = publiczne.

### Struktura folderów i prywatność ścieżek

**Decyzja:** szkielet folderów z góry, przed kodem; `data/` ignorowane w `.gitignore` w całości (jeden wpis), nie per-plik.

**Dlaczego:** fizyczna struktura egzekwuje regułę prywatności lepiej niż sam zapis w CLAUDE.md — ignorowanie całego `data/` = „nowy artefakt medyczny automatycznie poza gitem" bez pamiętania o `.gitignore`.

**Jak działa:** git nie śledzi pustych folderów → `.gitkeep` w `config/` i `src/`. Ścieżki `data/*` nie istnieją w świeżym klonie, więc kod tworzy je przez `mkdir -p` przy starcie.

### Środowisko Python (uv)

**Decyzja:** `uv` zamiast `pip` + `venv` + `poetry`, instalacja przez Homebrew. Docling dochodzi dopiero w etapie 1.

**Dlaczego:** jedno narzędzie (środowisko, zależności, lockfile, wersja Pythona), szybkie przy ciężkim stacku; `uv.lock` w repo → reprodukowalne środowisko z klona jedną komendą.

**Jak działa:** `uv sync` czyta `pyproject.toml`, tworzy `.venv/` i pisze wersje do `uv.lock`. `uv run <cmd>` sam aktywuje `.venv` — bez ręcznego `source`.

**Pułapki:** `.venv/` w `.gitignore` (odtwarzalne z locka) — do repo idą `pyproject.toml` + `uv.lock`, nie środowisko.

### Konfiguracja n8n (Docker)

**Decyzja:** n8n jako kontener Docker (Compose); dane trwałe w zewnętrznym wolumenie `n8n_data`.

**Dlaczego:** izolacja i czysty upgrade. Wolumen `external` przeżywa `docker compose down` i podmianę obrazu — workflow i credentiale nie giną.

**Jak działa:** `/Users/p/Documents/dev/n8n` ma `docker-compose.yml` (obraz `n8nio/n8n` bez tagu = `latest`, port `5678`, Europe/Warsaw) i `.env` (kopia sekretów — compose jej NIE wstrzykuje, to backup). Wolumen `n8n_data` na `/home/node/.n8n`: `config` (klucz szyfrujący), `database.sqlite` (workflow + zaszyfrowane credentiale).

**Pułapki:** realny klucz szyfrujący żyje w wolumenie, nie w `.env`. Gdyby wstrzykiwać klucz przez env, musi DOKŁADNIE zgadzać się z tym z wolumenu — inaczej „Mismatching encryption keys". `docker volume rm n8n_data` kasuje wszystko (backup: `docs/n8n-backup-restore.md`).

### Upgrade n8n (podmiana obrazu)

**Decyzja:** upgrade przez `docker compose pull && up -d`, z backupem wolumenu tuż przed. Wykonany: 2.27.4 → 2.30.7.

**Jak działa:** `pull` ściąga obraz, `up -d` odtwarza kontener; wolumen `external` zostaje, więc dane i klucz przeżywają. n8n przy starcie sam odpala migracje bazy.

**Pułapki:** migracje są **jednokierunkowe** — downgrade po majorze może się wysypać na schemacie; stąd backup przed upgradem. Rollback = przypięcie starego tagu w compose. Weryfikacja: logi (brak „Mismatching encryption keys"), `claude mcp list` (Connected).

### Dostęp Claude Code do n8n (serwer MCP)

**Decyzja:** wbudowany serwer MCP n8n (nie proces npx), zasięg **local** (per projekt), token z projektu Learning-Plan.

**Dlaczego:** local, bo to serwer HTTP — global próbowałby się łączyć z `localhost:5678` w każdej sesji każdego projektu (szum, gdy n8n nie działa).

**Jak działa:** MCP typu `http`, endpoint `http://localhost:5678/mcp-server/http`, autoryzacja `Bearer <JWT>`. Dodanie: `claude mcp add n8n-mcp --scope local --transport http <url> --header "Authorization: Bearer <token>"`. Serwery MCP ładują się przy starcie sesji — po dodaniu potrzebny restart.

**Pułapki:** token to sekret — konfiguracja idzie do `~/.claude.json` (poza repo), **nigdy** do `.mcp.json` w repo.

### Budowa workflow przez serwer MCP n8n

**Decyzja:** workflow budowany kodem SDK (`@n8n/workflow-sdk`), nie klikaniem w UI ani surowym JSON-em.

**Dlaczego:** serwer MCP wymusza ścieżkę „napisz kod → zwaliduj → utwórz" — workflow powstaje deterministycznie i wersjonowalnie z opisu. Ten sam model pracy obsłuży docelowo orkiestrację pipeline'u.

**Jak działa:** obowiązkowa kolejność narzędzi MCP: `get_sdk_reference` → `get_workflow_best_practices` → `search_nodes` → `get_node_types` → `validate_workflow` → `create_workflow_from_code`. Pominięcie `get_node_types` = zgadywanie parametrów = niepoprawny workflow. Egzekucję testową sprawdza `execute_workflow` (mode `manual`) → `get_execution`.

**Pułapki:** prefiks to sekwencja unikatowa — przed utworzeniem sprawdź `search_workflows` (dwa razy ten sam numer to cichy duplikat; `007` był zajęty → `008`). Wyrażenia zawsze w `expr('{{ ... }}')`, cudzysłowy proste.

### Podział odpowiedzialności: Python vs. n8n

**Decyzja:** cała logika biznesowa (OCR, standaryzacja) w wersjonowanych `.py`; n8n tylko orkiestruje (trigger, kolejność, retry). Node nigdy nie trzyma logiki.

**Dlaczego:** kod w plikach jest wersjonowany, testowalny i przenośny (przeżyje zmianę n8n → Airflow/cron); logika w node'ach żyje w SQLite poza gitem, bez testów. Ciężka biblioteka (Docling) wymaga natywnego venv, którego sandbox runnera n8n nie uniesie. Regułę „do API idzie wyłącznie nazwa markera" audytujesz w jednym miejscu w kodzie.

**Pułapki:** „zero logiki w n8n" jest surowsze niż konieczne — świadomie, jako bariera przed *logic creep*. Kanoniczny wzorzec: orkiestrator cienki, ciężka praca w wersjonowanym kodzie (tak samo Airflow: DAG wiąże taski, task woła kod).

### Tryb headless `claude -p`

**Decyzja:** wywołania LLM w pipeline idą przez `claude -p "<prompt>"` jako subprocess z Pythona, na subskrypcji **Pro** — nigdy przez SDK Anthropic z kluczem API. Smoke test: `src/smoke_test_claude.py`.

**Jak działa:** `claude -p` (od *print*) to Claude Code bez interaktywnego TTY — bierze prompt, wykonuje, wypisuje na stdout, kończy proces. Wywoływalny jak każdy program CLI:

```python
subprocess.run(["claude", "-p", "Wyekstrahuj ...", "--model", "haiku"],
               capture_output=True, text=True, check=True).stdout
```

Uwierzytelnia się zalogowaną sesją Pro (keychain / `~/.claude`), nie kluczem API — działa też zagnieżdżony. n8n woła to samo jako komenda shell → cała inteligencja w jednym mechanizmie.

**Dlaczego Pro, nie tokeny API:** Pro to koszt stały; API rośnie z wolumenem. Wolumen eksploduje nie na jednorazowej obróbce 390 dokumentów (kilka dolarów), lecz na iteracji pipeline'u i samym agentic codingu — miliony tokenów na sesję. Płaska subskrypcja spłaszcza to do przewidywalnej kwoty.

**Pułapki:** Pro ma limity przepustowości (okna 5-godzinne + tygodniowe), API nie — masowy backfill trzeba rozłożyć w czasie (przy HITL nieistotne).

### Dokumentacja i konwencje projektu

**Decyzja:** reguły przekrojowe (workflow etapów, Mermaid, ścieżki) w CLAUDE.md, szczegóły w docs.

**Dlaczego:** CLAUDE.md jest ładowany automatycznie do każdej sesji — jedyne miejsce z gwarancją przeczytania (progressive disclosure: krótka reguła zawsze w kontekście, pełna instrukcja na żądanie).

**Pułapki:** deklaracja w czacie ≠ wykonanie — checkbox odhaczany od razu po akcji. Polskie cudzysłowy `„..."` w etykietach Mermaid łamią parser GitHuba — etykiety w `["..."]`, zero `"` w treści.
