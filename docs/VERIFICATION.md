# Weryfikacja bieżącej iteracji NeuroSkin 3

## Kontynuacja sesji i semantyka części

Dodano jawny workflow Runs → wybrany snapshot → Load selected snapshot for evolution → edycja kontrolek → Continue with these controls. Nowy run zachowuje rodzica, wybraną generację, źródłowy digest i zmiany ustawień, ale nie przejmuje historycznych ocen. Numery nowych kandydatów i zapisanych etapów są zgodne: G+1 względem snapshotu, nie względem wieku championa.

Nowe checkpointy przechowują następną populację, PRNG, komplet kontrolek, provenance i checksum. Atomowy snapshot postępu umożliwia odkrycie ostatniej ukończonej granicy po awarii procesu. Stare archiwa używają zapisanych elit i wskazują brakujące kontrolki; QD/novelty/audit cache nie są odtwarzane. Nie deklarujemy dokładnego replay procesu. User bests nadal zapisuje wyłącznie końcowego championa i zachowuje lineage dziecka.

Skupione regresje: **25 passed** — starsze archiwa i checkpointy, zgodność scope, odrzucenie uszkodzonego checkpointu, realny kontroler z generacji 40 do 41 przy champione urodzonym w 12, ponowne oceny, zachowanie rodzica, odkrywalny snapshot postępu, API/digest/admission, User bests i semantyka komponentów. Kontrolowane audyty w teście lifecycle nie stanowią nowych dowodów fizycznych.

Chromium: **1 passed** — wybór wcześniejszego etapu, załadowanie kontrolek, zmiana celu na electronics i exploration na 0.75, rzeczywiste uruchomienie kolejnej generacji, zachowanie źródła oraz ponowne otwarcie nowego checkpointu. Sprawdzono też wyjaśnienie huba w drzewie i przewodnik kanałów sensorowych. Lokalny zrzut: `artifacts/continuation-workspace.png`.

Kontrola istniejących lokalnych archiwów, bez ich modyfikacji: z 17 zapisów 16 zawierało zgodne genotypy i dało się przygotować do kontynuacji; jeden pusty zapis bez geometrii został prawidłowo odrzucony. Dowód: `artifacts/continuation-existing-archives.json`.

Data: 2026-11-28. Aktualna implementacja kontynuacji i semantyki komponentow: `8edab0d` na `develop/v3`. Poprzednie funkcje User bests i podgladu skory pozostaja objete pelna regresja.

## User bests — automatyczna biblioteka końcowych championów

Dodano trzecią kategorię Library, trwałe pliki `runs/user_bests/{run_id}.json` i selekcję `user_best` we wspólnych ścieżkach inspekcji. Po atomowym zapisie terminalnego completed/stopped runu do biblioteki trafia wyłącznie jego końcowy audytowany champion z niezaokrąglonym audit_score >90. Zapis generacji, finalizing, paused/running oraz failed nie dodaje wpisów. Powtarzane zapisy tego samego runu są idempotentne. Oryginalne audyty i provenance pozostają zachowane; nie importowano wstecz dawnych archiwów.

Skupiona regresja: **16 passed** — próg 90 i wartości niepoprawne, dwa cykle kontrolera po dwie generacje (completed i stopped), lepszy champion z wcześniejszej generacji, brak zapisów iteracyjnych, restart, niezmienność wpisów, odrzucanie uszkodzonej geometrii i ścieżek, rzeczywiste API Preview/Evaluate All/eksport bez źródłowego archiwum. Testy lifecycle używają kontrolowanych wyników audytu, aby sprawdzić mechanizm zapisu; nie są dowodem osiągnięcia wyniku >90 przez konkretny model fizyczny.

Chromium: **1 passed** — trzecia kategoria, automatyczne odświeżenie po zakończeniu runu, Preview, zachowanie wyboru po zmianie live runu oraz prawdziwe obliczenie Skin tile w Multiscale dla selekcji user_best. Kontrola AST 147 aktywnych plików Python, składnia inline JavaScript i linki dokumentacji: bez błędów.

Końcowa kontrola obu testów lifecycle po zastąpieniu czasu rzeczywistego deterministycznym zegarem kontrolera: **2 passed**. Pełny runner dla tej iteracji: `artifacts/user-bests-release-verification.json`; szczegóły poniżej.

## Zakres wcześniejszego porządkowania

- Wykonano zatwierdzony [manifest porządkowania](CLEANUP_MANIFEST.json): 203 pliki usunięte, 21 ścieżek przemianowanych. Lista obejmuje historyczne dokumenty, zduplikowane obrazy, wygenerowane dawne katalogi oraz poprzedni audyt i plany.
- Testy aktywnych funkcji zachowano pod nazwami odpowiadającymi funkcjom. Z `engine.py` usunięto nieużywany starszy kontroler i dwa testy wyłącznie tego kontrolera; bieżące cykle ewolucji pokrywają `test_advanced.py`, `test_pipeline.py`, `test_search.py`, `test_spatial.py`, `test_shutdown.py` i test wygaśnięcia budżetu.
- Wszystkie dotychczasowe eksperymenty zachowano w `runs/`. Dodatkowy eksperyment ukończony podczas migracji scalono bez nadpisywania plików, zachowując komplet jedenastu etapów. W katalogu jest dziesięć wyników końcowych.
- Cztery przykładowe presety nie ustawiają seeda i nie uruchamiają eksperymentu. Basic zwija sekcje, Advanced je rozwija. Native resize i ResizeObserver utrzymują zgodną wysokość Plotly.
- Naprawiono nominowanie nowej generacji po wygaśnięciu czasu, niespójne porównanie archiwów, brak pobierania audytu final/stage, oczekiwane błędy eksportu, odczyt spoza katalogu archiwum, buforowanie ZIP w RAM i aktywny HTML w galerii.
- Tożsamość źródeł numerycznych jest wspólna dla ewolucji i walidacji. Wzorce pojedynczego stopnia nie dziedziczą losowych hybryd.

## Podgląd obliczonych zespołów skóry

Dodano podgląd 3D siatek 3×3, 5×5 i 7×7 z odpowiedzi optymalizatora. Geometria jest związana hashem z obliczonym genotypem i kopiowana zgodnie z rzeczywistym pitch; kontrolowane są prześwity i dopasowanie do footprint. Duże modele mają jawnie oznaczony podgląd osi strukturalnych. Rekomendacje porównują wykonalność i istniejący koszt utility wyłącznie w obrębie jednej wierności modelu; pierwszeństwo mają dostępne wyniki refinement. Układy bez refinement są opisane jako screening.

Dodano obsługę 7×7 do modeli scalar, Q1 i nieliniowej membrany z podatnym podłożem 3D. Zachowano zgodność API dla 8×8. Raporty zapisywane przez GUI zachowują wyniki numeryczne bez dużych, odtwarzalnych siatek podglądu. Naprawiono również uszkodzone polskie znaki w README i dokumentach architektury, walidacji, roadmapy oraz weryfikacji.

## Wykonane kontrole

- Skupione testy siatki i istniejących modeli tile/membrany: **18 passed**.
- Testy rzeczywistej geometrii, n² pozycji, hasha, prześwitów, wyboru wierności, API oraz rezerwacji zasobów: **16 passed**. Nie obniżono progów fizycznych; niepowodzenie refinement pozostaje widoczne w wyniku, a podgląd jawnie korzysta wtedy ze screeningu.
- Node: geometria 3×3 / 5×5 / 7×7, indeksy złączonych mesh, warstwy, wybór czujnika, odrzucenie niezgodnego hasha i zapis raportu bez dużych siatek przeszły.
- Chromium: rzeczywiste obliczenie, przełączanie trzech rozmiarów bez kolejnych żądań optymalizacji, 49 czujników, geometria flexure, warstwy, wybór czujnika i zwalnianie wykresów po zmianie zakładki: **1 passed**.
- **Końcowy pełny runner: 345 passed, 1 skipped, 106 subtests passed; wszystkie 18 kontroli przeszło.** Obejmuje siedem rzeczywistych scenariuszy Chromium, pięć zestawów Node, deformację oraz składnię skryptów zewnętrznych i inline. Pytest trwał 553,24 s. Wynik: `artifacts/continuation-release-verification.json`; `software_checks_pass=true`, `browser_checks_enabled=true`, `release_ready=true`. Pominięto wyłącznie opcjonalną kosztowną siatkę 8×; istniejąca deprecjacja TestClient/HTTPX pozostała ostrzeżeniem.
- AST wszystkich 149 aktywnych plików Python oraz `git diff --check`: bez błędów. Lokalne linki dokumentacji: bez brakujących celów.
- Ponowny skan 189 niepustych aktywnych plików z pominięciem `.git`, `.tools`, `runs`, `artifacts` i cache: brak identycznych plików. Dowód lokalny: `artifacts/continuation-repository-check.json`.

## Dowody lokalne i CI

Artefakty lokalne są celowo ignorowane w Git: `artifacts/continuation-release-verification.json`, powiązany JUnit XML, `artifacts/continuation-workspace.png`, kontrola istniejących archiwów i logi skupionych regresji. Zachowano również wcześniejsze raporty i zrzuty User bests, podglądu skóry oraz porządkowania. CI publikuje artefakty Windows i Linux także przy porażce. Pełny job Windows korzysta z tego samego runnera; Linux sprawdza instalację i kontrakty CPU.

W tej sesji doinstalowano lokalne, ignorowane narzędzia testowe: Node z oficjalnego archiwum ze sprawdzoną sumą SHA-256 oraz Playwright/Chromium. Zależności numeryczne aplikacji nie były aktualizowane. Kopia sprzed zatwierdzonego porządkowania: `.tools/backups/v3-cleanup.zip`, 362 sprawdzone pliki; jej hash jest w manifeście.

`release_ready` w raporcie runnera opisuje wymagane kontrole oprogramowania tej konfiguracji. Nie przyznaje stabilnej kwalifikacji całej roadmapy, przejścia nieuruchomionego tutaj Linux, kwalifikacji CAD, wykonania ani sprzętu. Pominięta siatka 8× jest kontrolą opt-in; osobny benchmark GPU również pozostaje opcjonalny. Istniejące ostrzeżenie o deprecjacji TestClient/HTTPX nie oznacza błędu solvera.

Podgląd skóry przedstawia nominalną geometrię. Nie zaimplementowano w tej iteracji kompletnego CAD/STEP, pełnego sprzężenia warstw, niezależnych instancji ewolucji ani Full Robot Skin Engine. Ich bramki i kolejność są zapisane w [aktualnej roadmapie](RELEASE_PLAN_V30.md).

Po wymianie kodu należy ponownie uruchomić wcześniej działający serwer, aby załadować aktualny backend i katalog `runs/`.

## Narzędzia pomocnicze

Generatory zapisują podglądy do `artifacts/previews/`, benchmark do `artifacts/refinement-benchmark.json`, a CLI domyślnie używa `runs/`. W poprzedniej iteracji sprawdzono składnię narzędzi, pomoc CLI, generowanie aktualnego katalogu geometrii i rzeczywistego podglądu laminate-shell. `pip check` i kontrola lokalnych linków przeszły.
