# NeuroSkin Evolution Lab 3

Otwarte ?rodowisko badawcze do ewolucji geometrii przycisk?w sensorycznych dla sk?ry robotycznej. Aktualny identyfikator rozwojowy znajduje si? w [VERSION](VERSION). Repozytorium zawiera jedn? rozwijan? lini? aplikacji.

Celem produktu jest przej?cie od wyewoluowanego receptora do parametrycznego modelu bry?owego i eksportu STEP, a nast?pnie zespo??w sk?ry robota. Obecny eksport STL jest konceptualny. Parametryczny CAD, conforming CAD-to-FEM oraz kompletny Robot Skin Engine pozostaj? zadaniami roadmapy; wynik symulacji nie jest potwierdzeniem parametr?w sprz?tu.

## Instalacja i uruchomienie

Wspierany pe?ny profil: Windows 11 x64, Python 3.14, obliczenia CPU; opcjonalnie CUDA 12/CuPy.

```powershell
python -m pip install -r requirements.txt
python -m pip check
python server.py --cores auto --open --port 8765
```

Alternatywnie: `./launch_windows.ps1`. Domy?lny adres to `http://127.0.0.1:8765`. Uruchamiaj jeden proces aplikacji: kontroler ewolucji i rezerwacje zasob?w s? lokalne dla procesu.

## Praca w GUI

- **Basic**: zwini?te sekcje ustawie? i uproszczony widok. **Advanced**: rozwini?te sekcje ustawie?, inspektory i diagnostyka. Zmiana trybu nie uruchamia oblicze? ani nie zmienia konfiguracji genotypu.
- **Evolution presets**: cztery gotowe konfiguracje ? Quick exploration, Balanced mechanics, Electronics co-design i Two-stage hybrids ? oraz maksymalnie sze?? w?asnych zapisanych lokalnie. Wczytanie presetu ustawia nast?pny eksperyment; nie odtwarza ziarna ani nie zmienia trwaj?cej ewolucji.
- **Overview / Results / FEM / Signals / Multiscale / Library / Runs / History**: wizualizacje i wyniki powi?zane z wybranym kandydatem. W Advanced dost?pne s? cztery standardowe podgl?dy FEM w siatce 2?2, drzewo komponent?w, wektory obci??e?/reakcji i sygna?y PVDF.
- **Wysoko?? wykres?w**: przeci?gnij dolny prawy naro?nik ?rodkowego wykresu w d??. Plotly dopasowuje obszar rysowania do nowej wysoko?ci. Dzia?a r?wnie? dla podgl?d?w FEM, sygna??w i przypi?tej geometrii.
- **Evaluate All**: niezale?ne etapy mog? dzia?a? r?wnolegle w ramach estymowanego bud?etu CPU/RAM i jawnego urz?dzenia. Ewolucja zachowuje wy??czno?? oblicze? ci??kich do ko?ca sprz?tania.

Bud?et czasu ewolucji ogranicza rozpoczynanie kolejnych generacji. Doko?czenie ju? uruchomionych audyt?w i eksportu mo?e potrwa? d?u?ej.

## Eksperymenty i eksport

Wyniki GUI znajduj? si? w ignorowanym przez Git katalogu `runs/`. Dotychczasowe katalogi eksperyment?w zosta?y zachowane w tym miejscu. Widok Runs pozwala ponownie otworzy? eksperyment, wybra? generacj? i pobra? audyt lub archiwum ZIP.

```powershell
python evolve_cli.py --cores 4 --seconds 60 --population 48 --out runs
python smoke_test.py
python fem_cli.py --help
python measured_import.py measurement_template.csv --out artifacts/measured-report.json
```

`measurement_template.csv` jest wy??cznie nag??wkiem do wype?nienia pomiarami; pusty szablon zostanie odrzucony. Rzeczywiste dane pomiarowe s? opcjonalne dla wydania programu i ewolucji. Sam import CSV nie przyznaje kwalifikacji T3.

## Weryfikacja

```powershell
python -m pytest -q tests
python verify_release.py
```

Pe?na weryfikacja GUI wymaga Node.js oraz Playwright/Chromium:

```powershell
python -m pip install "playwright>=1.50,<2"
python -m playwright install chromium
python verify_release.py --browser
```

Runner uruchamia pytest, wszystkie testy Node i kontrole sk?adni JavaScript. Brak Node jest b??dem wymaganej kontroli. Bez `--browser` raport nie deklaruje gotowo?ci pe?nego wydania. Rzeczywisty kosztowny test siatki 8? wymaga `NEUROSKIN_SLOW_TESTS=1`.

## Dokumentacja

- [Aktualna roadmapa i status funkcji](docs/RELEASE_PLAN_V30.md)
- [Architektura aplikacji](docs/ARCHITECTURE.md)
- [Walidacja, poziomy dowod?w i ograniczenia](docs/VALIDATION.md)
- [Bie??ca weryfikacja zmian](docs/VERIFICATION.md)
- [?r?d?a koncepcji naukowych](docs/SCIENTIFIC_SOURCES.md)
- [Manifest zatwierdzonego porz?dkowania](docs/CLEANUP_MANIFEST.json)

Aktywne regresje zachowano i przemianowano wed?ug funkcji. Numery wersji w formatach JSON/protoko?ach oznaczaj? wersj? schematu, nie r?wnoleg?e wydanie aplikacji. Usuni?te materia?y i stan sprzed porz?dkowania s? odzyskiwalne z historii Git oraz lokalnej, ignorowanej kopii opisanej w manife?cie.

Licencja: [LICENSE](LICENSE).
