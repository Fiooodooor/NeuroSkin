# Weryfikacja bieżącej iteracji NeuroSkin 3

Data: 2026-11-28. Zmiany porządkowe i poprzednia regresja są zapisane w `cb7bef5` na `develop/v3`. Implementacja obliczonego podglądu zespołów skóry i testy tej iteracji: `16591c2`.

## Zakres porządkowania i wcześniejszych poprawek

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
- **Końcowy pełny runner: 320 passed, 1 skipped, 106 subtests passed; wszystkie 17 kontroli przeszło.** Obejmuje pięć rzeczywistych scenariuszy Chromium, pięć zestawów Node, deformację oraz składnię skryptów zewnętrznych i inline. Pytest trwał 511,57 s. Wynik: `artifacts/skin-release-verification.json`; `software_checks_pass=true`, `browser_checks_enabled=true`, `release_ready=true`. Pominięto wyłącznie opcjonalną kosztowną siatkę 8×; istniejąca deprecjacja TestClient/HTTPX pozostała ostrzeżeniem.
- AST wszystkich 145 aktywnych plików Python oraz `git diff --check`: bez błędów. Lokalne linki dokumentacji: bez brakujących celów.
- Ponowny skan 182 niepustych aktywnych plików z pominięciem `.git`, `.tools`, `runs`, `artifacts` i cache: brak identycznych plików. Dowód lokalny: `artifacts/skin-repository-check.json`.

## Dowody lokalne i CI

Artefakty lokalne są celowo ignorowane w Git: `artifacts/skin-release-verification.json`, powiązany JUnit XML, logi testów skupionych i `artifacts/skin-patch-7x7.png`. Zachowano również `artifacts/v3-final-verification.json`, `artifacts/repository-check.json` i `artifacts/workspace-v3.png`. CI publikuje artefakty Windows i Linux także przy porażce. Pełny job Windows korzysta z tego samego runnera; Linux sprawdza instalację i kontrakty CPU.

W tej sesji doinstalowano lokalne, ignorowane narzędzia testowe: Node z oficjalnego archiwum ze sprawdzoną sumą SHA-256 oraz Playwright/Chromium. Zależności numeryczne aplikacji nie były aktualizowane. Kopia sprzed zatwierdzonego porządkowania: `.tools/backups/v3-cleanup.zip`, 362 sprawdzone pliki; jej hash jest w manifeście.

`release_ready` w raporcie runnera opisuje wymagane kontrole oprogramowania tej konfiguracji. Nie przyznaje stabilnej kwalifikacji całej roadmapy, przejścia nieuruchomionego tutaj Linux, kwalifikacji CAD, wykonania ani sprzętu. Pominięta siatka 8× jest kontrolą opt-in; osobny benchmark GPU również pozostaje opcjonalny. Istniejące ostrzeżenie o deprecjacji TestClient/HTTPX nie oznacza błędu solvera.

Podgląd skóry przedstawia nominalną geometrię. Nie zaimplementowano w tej iteracji kompletnego CAD/STEP, pełnego sprzężenia warstw, niezależnych instancji ewolucji ani Full Robot Skin Engine. Ich bramki i kolejność są zapisane w [aktualnej roadmapie](RELEASE_PLAN_V30.md).

Po wymianie kodu należy ponownie uruchomić wcześniej działający serwer, aby załadować aktualny backend i katalog `runs/`.

## Narzędzia pomocnicze

Generatory zapisują podglądy do `artifacts/previews/`, benchmark do `artifacts/refinement-benchmark.json`, a CLI domyślnie używa `runs/`. W poprzedniej iteracji sprawdzono składnię narzędzi, pomoc CLI, generowanie aktualnego katalogu geometrii i rzeczywistego podglądu laminate-shell. `pip check` i kontrola lokalnych linków przeszły.
