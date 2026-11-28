# NeuroSkin Evolution Lab 3

Otwarte środowisko badawcze do ewolucji geometrii przycisków sensorycznych dla skóry robotycznej. Aktualny identyfikator rozwojowy znajduje się w [VERSION](VERSION). Repozytorium zawiera jedną rozwijaną linię aplikacji.

Celem produktu jest przejście od wyewoluowanego receptora do parametrycznego modelu bryłowego i eksportu STEP, a następnie zespołów skóry robota. Obecny eksport STL jest konceptualny. Parametryczny CAD, conforming CAD-to-FEM oraz kompletny Robot Skin Engine pozostają zadaniami roadmapy; wynik symulacji nie jest potwierdzeniem parametrów sprzętu.

## Instalacja i uruchomienie

Wspierany pełny profil: Windows 11 x64, Python 3.14, obliczenia CPU; opcjonalnie CUDA 12/CuPy.

```powershell
python -m pip install -r requirements.txt
python -m pip check
python server.py --cores auto --open --port 8765
```

Alternatywnie: `./launch_windows.ps1`. Domyślny adres to `http://127.0.0.1:8765`. Uruchamiaj jeden proces aplikacji: kontroler ewolucji i rezerwacje zasobów są lokalne dla procesu.

## Praca w GUI

- **Basic**: zwinięte sekcje ustawień i uproszczony widok. **Advanced**: rozwinięte sekcje ustawień, inspektory i diagnostyka. Zmiana trybu nie uruchamia obliczeń ani nie zmienia konfiguracji genotypu.
- **Evolution presets**: cztery gotowe konfiguracje — Quick exploration, Balanced mechanics, Electronics co-design i Two-stage hybrids — oraz maksymalnie sześć własnych zapisanych lokalnie. Wczytanie presetu ustawia następny eksperyment; nie odtwarza ziarna ani nie zmienia trwającej ewolucji.
- **Overview / Results / FEM / Signals / Multiscale / Library / Runs / History**: wizualizacje i wyniki powiązane z wybranym kandydatem. W Advanced dostępne są cztery standardowe podglądy FEM w siatce 2×2, drzewo komponentów, wektory obciążeń/reakcji i sygnały PVDF.
- **Wysokość wykresów**: przeciągnij dolny prawy narożnik środkowego wykresu w dół. Plotly dopasowuje obszar rysowania do nowej wysokości. Działa również dla podglądów FEM, sygnałów i przypiętej geometrii.
- **Evaluate All**: niezależne etapy mogą działać równolegle w ramach estymowanego budżetu CPU/RAM i jawnego urządzenia. Ewolucja zachowuje wyłączność obliczeń ciężkich do końca sprzątania.

Budżet czasu ewolucji ogranicza rozpoczynanie kolejnych generacji. Dokończenie już uruchomionych audytów i eksportu może potrwać dłużej.

## Podgląd obliczonego fragmentu skóry

W **Multiscale → Tile optimization** wybierz porównywane siatki **3×3, 5×5 lub 7×7** i uruchom optymalizację. Pod wynikami znajduje się obracany podgląd 3D obliczonego zespołu: rzeczywista geometria receptora, podłoże, membrana i filmy PVDF. Możesz przełączać obliczone warianty, ukrywać warstwy, wybierać czujniki i zwiększać wysokość podglądu. Domyślny bok 160 mm pozwala sprawdzić większe siatki; warianty niedopasowane do geometrii są wykluczane.

Rekomendacja oznacza najlepszy z obliczonych wariantów danego rozmiaru. Wyniki po refinement mają pierwszeństwo; gdy ich brakuje, GUI jawnie pokazuje screening. Jest to nominalny zespół geometrii, a nie pole deformacji FEM ani kwalifikacja wykonania. Zapisywane raporty zachowują wyniki numeryczne bez dużych, odtwarzalnych siatek podglądu.

## Eksperymenty i eksport

**Kontynuacja wcześniejszej sesji:** w Runs otwórz zapisany eksperyment, wybierz generację lub wynik końcowy i kliknij **Load selected snapshot for evolution**. W Overview zmień załadowane ustawienia i użyj **Continue with these controls**. Powstaje osobny run z numeracją od wybranej generacji +1; źródłowy eksperyment pozostaje niezmienny. Nowe zapisy mają checkpoint populacji i PRNG, a starsze korzystają z zapisanych najlepszych geometrii i jawnych domyślnych wartości brakujących kontrolek. Dziedziczone geometrie otrzymują nowe oceny i audyty finalistów. [Szczegóły i ograniczenia kontynuacji](docs/CONTINUATION.md).

W podglądzie 3D rozwiń **How this button senses touch** lub wybierz część w drzewie. Opisy rozróżniają rzeczywiste role mechaniczne, placeholdery sensorów i koncepcyjny hub. Kolory legendy odpowiadają geometrii. [Jak działają części i kanały pomiarowe](docs/SENSING_MODEL.md).

**Library → User bests** jest trzecią kategorią biblioteki. Po ukończeniu lub ręcznym zatrzymaniu eksperymentu aplikacja automatycznie zachowuje jego końcowego audytowanego championa, jeżeli oryginalny, niezaokrąglony `audit_score` jest **ściśle większy niż 90/100**. Nie zapisuje kolejnych iteracji, ocen proxy ani ocen eksperckich bibliotek. Wybór championa zachowuje bieżącą politykę promocji; może to być geometria z wcześniejszej generacji.

Każdy run ma jeden trwały wpis w `runs/user_bests/{run_id}.json`. Powtórne zapisanie zakończonego runu nie powiela ani nie nadpisuje wpisu. Biblioteka zachowuje dokładny genotyp, pełny oryginalny audyt, hash geometrii, seed, ustawienia i pochodzenie źródeł; jest dostępna po restarcie i nie wymaga zachowania katalogu źródłowego eksperymentu. Preview umożliwia dalszą inspekcję, Evaluate All, eksport geometrii i analizy Multiscale. Ponowna ewaluacja nie zmienia oryginalnej oceny we wpisie. Wpisy są wyświetlane od najnowszych; oceny z różnych protokołów nie tworzą wspólnego rankingu. Istniejące archiwa nie są automatycznie importowane wstecz.

Wyniki GUI znajdują się w ignorowanym przez Git katalogu `runs/`. Dotychczasowe katalogi eksperymentów zostały zachowane w tym miejscu. Widok Runs pozwala ponownie otworzyć eksperyment, wybrać generację i pobrać audyt lub archiwum ZIP.

```powershell
python evolve_cli.py --cores 4 --seconds 60 --population 48 --out runs
python smoke_test.py
python fem_cli.py --help
python measured_import.py measurement_template.csv --out artifacts/measured-report.json
```

`measurement_template.csv` jest wyłącznie nagłówkiem do wypełnienia pomiarami; pusty szablon zostanie odrzucony. Rzeczywiste dane pomiarowe są opcjonalne dla wydania programu i ewolucji. Sam import CSV nie przyznaje kwalifikacji T3.

## Weryfikacja

```powershell
python -m pytest -q tests
python verify_release.py
```

Pełna weryfikacja GUI wymaga Node.js oraz Playwright/Chromium:

```powershell
python -m pip install "playwright>=1.50,<2"
python -m playwright install chromium
python verify_release.py --browser
```

Runner uruchamia pytest, wszystkie testy Node i kontrole składni JavaScript. Brak Node jest błędem wymaganej kontroli. Bez `--browser` raport nie deklaruje gotowości pełnego wydania. Rzeczywisty kosztowny test siatki 8× wymaga `NEUROSKIN_SLOW_TESTS=1`.

## Dokumentacja

- [Aktualna roadmapa i status funkcji](docs/RELEASE_PLAN_V30.md)
- [Architektura aplikacji](docs/ARCHITECTURE.md)
- [Walidacja, poziomy dowodów i ograniczenia](docs/VALIDATION.md)
- [Bieżąca weryfikacja zmian](docs/VERIFICATION.md)
- [Źródła koncepcji naukowych](docs/SCIENTIFIC_SOURCES.md)
- [Manifest zatwierdzonego porządkowania](docs/CLEANUP_MANIFEST.json)

Aktywne regresje zachowano i przemianowano według funkcji. Numery wersji w formatach JSON/protokołach oznaczają wersję schematu, nie równoległe wydanie aplikacji. Usunięte materiały i stan sprzed porządkowania są odzyskiwalne z historii Git oraz lokalnej, ignorowanej kopii opisanej w manifeście.

Licencja: [LICENSE](LICENSE).
