# Runbook — backup i odtworzenie środowiska n8n

## Cel

Pełne zabezpieczenie i **odtworzenie lokalnej instancji n8n na innym MacBooku / komputerze**. Instancja jest **wspólna** dla projektów Learning Plan i Document Intelligence Platform — backupujesz jedno środowisko, nie per-projekt, więc jeden snapshot załatwia oba.

> To runbook operacyjny (uruchamiany na żądanie), nie etap implementacji — dlatego żyje poza `docs/stages/`. Mechanizm Dockera/wolumenu i klucza szyfrującego opisany w `docs/stages/00-setup.md` (notatki „Konfiguracja n8n na MacBooku" i „Upgrade n8n").

## Z czego składa się środowisko

Trzy kawałki o różnym traktowaniu:

| Element | Co zawiera | Lokalizacja | Do gita? |
|---|---|---|---|
| `docker-compose.yml` | definicja usługi (przepis, bezstanowy) | `/Users/p/Documents/dev/n8n/` | ✅ tak (brak sekretów) |
| `.env` | `N8N_ENCRYPTION_KEY` + `N8N_API_KEY` (kopia zapasowa kluczy) | `/Users/p/Documents/dev/n8n/` | ❌ nigdy — sekrety |
| wolumen `n8n_data` | workflows, zaszyfrowane credentiale, klucz szyfrujący, storage | wolumen Docker (`/var/lib/docker/volumes/n8n_data/_data`) | ❌ nie — wrażliwe + binarne |

**Zasada twarda:** do gita trafia wyłącznie `docker-compose.yml`. `.env` i tarball wolumenu zawierają sekrety (klucze API, zaszyfrowane credentiale) — **nigdy** do żadnego repozytorium. Backup przechowuj poza gitem (dysk zewnętrzny / prywatna, szyfrowana chmura).

Snapshot pełny = **tar wolumenu `n8n_data`** + **`docker-compose.yml`** + **kopia `.env`**. Tar niesie klucz szyfrujący w środku (plik `config`), więc sam wystarcza do odszyfrowania credentiali; `.env` to zapas na scenariusz częściowej utraty.

## Lokalizacja i rozmiar backupu

Backupy lądują na **Google Drive**: `/Users/p/Mój dysk/Colab Notebooks/n8n-backups/` (ścieżka ma spacje w środku — `Mój dysk`, `Colab Notebooks` — więc w komendach zawsze w cudzysłowach). Każdy backup dostaje **własny podfolder z datą**, a w nim trzy pliki:

```
/Users/p/Mój dysk/Colab Notebooks/n8n-backups/
└── 2026-07-18/
    ├── n8n_data.tar.gz       # cały wolumen spakowany — dane + klucz (~0,7 MB)
    ├── docker-compose.yml    # przepis (< 1 KB)
    └── n8n.env.backup        # kopia kluczy (< 1 KB)
```

Podfolder-per-data trzyma każdy snapshot samodzielnie: `docker-compose.yml` i `.env` mogą się z czasem zmieniać, więc ich kopia musi pasować do tara z tego samego dnia.

**Dlaczego Drive:** synchronizuje się do chmury, więc kopia jest automatycznie **poza maszyną** — ręczny krok „skopiuj na dysk zewnętrzny" znika, a awaria dysku Maca nie kasuje backupu.

**Dwie pułapki tej lokalizacji:**
- Docker **nie montuje niezawodnie** ścieżki Drive (to wirtualny FS przez `~/Library/CloudStorage`). Dlatego tarujemy do **lokalnego stagingu**, a na Drive kopiujemy zwykłym `cp` (kroki niżej).
- Snapshot to **sekrety w chmurze** (klucz szyfrujący + zaszyfrowane credentiale + `.env`). Akceptowalne na prywatnym koncie Google z 2FA; treści medycznych tu nie ma (te żyją lokalnie w `data/`). Świadoma decyzja właściciela.

Wolumen surowo waży ~7,5 MB (głównie `database.sqlite` + dziennik `-wal`), po kompresji `tar.gz` to ~0,7 MB. Miesięczny backup dokłada jeden datowany `.tar.gz` — po roku rząd kilku–kilkunastu MB. `stop` przed backupem scala `-wal` do głównej bazy → spójny (i mniejszy) snapshot.

## Backup — krok po kroku

Katalog n8n: `/Users/p/Documents/dev/n8n/`. Cel na Drive: `/Users/p/Mój dysk/Colab Notebooks/n8n-backups/`. Wykonuj w **jednej sesji terminala** (żeby zmienne przetrwały). Tarujemy lokalnie, potem kopiujemy na Drive (Docker nie montuje ścieżki Drive).

1. Ustal ścieżki (staging lokalny + cel z datą na Drive) i zatrzymaj kontener:
   ```bash
   STAGING="$HOME/.n8n-backup-staging"
   DEST="/Users/p/Mój dysk/Colab Notebooks/n8n-backups/$(date +%F)"
   mkdir -p "$STAGING" "$DEST"
   docker compose -f /Users/p/Documents/dev/n8n/docker-compose.yml stop
   ```
2. Zrzut wolumenu do stagingu (Docker pisze do lokalnej ścieżki):
   ```bash
   docker run --rm -v n8n_data:/data:ro -v "$STAGING":/backup alpine \
     tar czf /backup/n8n_data.tar.gz -C /data .
   ```
3. Wznów kontener (dalej pracujemy już na plikach, n8n może wrócić online):
   ```bash
   docker compose -f /Users/p/Documents/dev/n8n/docker-compose.yml start
   ```
4. Skopiuj trzy pliki na Drive i posprzątaj staging:
   ```bash
   cp "$STAGING/n8n_data.tar.gz" "$DEST/"
   cp /Users/p/Documents/dev/n8n/docker-compose.yml "$DEST/"
   cp /Users/p/Documents/dev/n8n/.env "$DEST/n8n.env.backup"
   rm "$STAGING/n8n_data.tar.gz"
   ```
5. Weryfikacja: `ls -lh "$DEST"` — `n8n_data.tar.gz` > 0 B, obecne `docker-compose.yml` i `n8n.env.backup`. Drive zsynchronizuje pliki do chmury (ikona sync w Finderze).

Kadencja: raz na miesiąc (lub przed każdą większą zmianą / upgradem n8n).

## Odtworzenie na nowym MacBooku — krok po kroku

1. Zainstaluj Docker Desktop.
2. Pobierz podfolder backupu z Google Drive (`.../Colab Notebooks/n8n-backups/RRRR-MM-DD/`) i odłóż jego pliki na nowej maszynie: `docker-compose.yml`, `n8n.env.backup` → zapisz jako `.env`, oraz `n8n_data.tar.gz`.
3. Utwórz wolumen (jest `external` — compose go nie stworzy):
   ```bash
   docker volume create n8n_data
   ```
4. Wgraj dane do wolumenu (`<podfolder>` = katalog backupu z wybranej daty, np. `.../n8n-backups/2026-07-18`):
   ```bash
   docker run --rm -v n8n_data:/data -v <podfolder>:/backup alpine \
     tar xzf /backup/n8n_data.tar.gz -C /data
   ```
5. Start:
   ```bash
   docker compose -f <katalog>/docker-compose.yml up -d
   ```
6. Zweryfikuj (sekcja niżej).

Klucz szyfrujący jedzie w tarballu → credentiale odszyfrują się same; `.env` nie jest do tego konieczny przy pełnym odtworzeniu wolumenu. `.env` używasz tylko, gdy odtwarzasz bazę **bez** pliku `config` — wtedy wstrzyknij `N8N_ENCRYPTION_KEY` przez env, żeby pasował do tego, czym zaszyfrowano dane (inaczej „Mismatching encryption keys" i credentiale się nie odszyfrują).

## Weryfikacja po odtworzeniu

- `docker exec n8n n8n --version` — wersja się pojawia.
- `curl -s -o /dev/null -w '%{http_code}' http://localhost:5678/healthz` → `200`.
- Lista workflow (MCP `search_workflows` albo UI `http://localhost:5678`) — wszystkie obecne.
- `docker logs n8n 2>&1 | grep -i "encryption"` — brak „Mismatching encryption keys" = klucz pasuje, credentiale odszyfrowane.

## Osobny projekt n8n (gdzie leży `.env`)

Konfiguracja n8n (compose + `.env`) **nie jest** częścią repo Document Intelligence Platform — żyje osobno w `/Users/p/Documents/dev/n8n/`. Właściciel ma do niej dostęp lokalnie; gdy przyszła sesja potrzebuje klucza szyfrującego lub API tokena, `.env` jest właśnie tam.

Repozytorium projektu n8n jest na GitHubie — **prywatne**, wersjonowany tylko `docker-compose.yml`, `.env` w `.gitignore` (zweryfikowane: sekrety nie trafiły do repo, śledzone są jedynie `.gitignore` i `docker-compose.yml`):

- Repo n8n (prywatne): `https://github.com/pmackowka/n8n.git`

To repo daje **przepis** (compose), nie dane ani sekrety. Do pełnego odtworzenia i tak potrzebny jest tarball wolumenu `n8n_data` + `.env` z bezpiecznego backupu (poza gitem).

## Instrukcja dla przyszłej sesji Claude

Gdy właściciel powie „zrób backup n8n":

1. Wykonaj sekcję **Backup — krok po kroku** w **jednej sesji terminala** (żeby zmienne `$STAGING`/`$DEST` przetrwały): tar `n8n_data` do lokalnego stagingu → start kontenera → `cp` trzech plików do podfolderu z datą na Drive (`/Users/p/Mój dysk/Colab Notebooks/n8n-backups/`).
2. Zweryfikuj rozmiar tara (> 0 B) i obecność wszystkich trzech elementów snapshotu.
3. Potwierdź, że Drive zsynchronizował pliki do chmury — off-machine backup jest wtedy automatyczny, osobne kopiowanie zbędne.
4. **Nigdy** nie commituj tara ani `.env` do żadnego repozytorium; nie wypisuj wartości kluczy do czatu.
