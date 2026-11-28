# Walidacja NeuroSkin 3

Oceniaj oddzielnie poprawność programu, poziom modelu numerycznego, poprawność geometrii CAD, wykonalność wykonania i parametry sprzętu. Sukces HTTP, wysoki fitness lub wyświetlenie pola 3D nie przyznaje żadnego z pozostałych statusów.

## Poziomy dowodów

- **T0**: syntetyczny screening i testy na zadeklarowanych modelach/noise; grupy pozycji pozostają rozdzielone między train/validation/test. Dobór dekodera i wzmocnienia nie używa zewnętrznego testu.
- **T1**: potrzebne są jawne dowody poprawnego continuum FEM i zbieżności siatki. Sam solve lub niskie residuum nie wystarcza.
- **T2**: dodatkowo odpowiednia nieliniowość/kontakt i niezależna weryfikacja numeryczna.
- **T3**: niezależne pomiary, kalibracja, szum i niepewność z jednoznacznym pochodzeniem. Sam import CSV nie przyznaje T3.

T3 jest opcjonalne dla wydania oprogramowania i ewolucji; bez danych fizycznych nie wolno deklarować skalibrowanych parametrów sensora. Numery wersji schematów JSON są zachowane dla zgodności formatu i nie oznaczają starych wydań aplikacji.

## Niezmienniki numeryczne

- Jednostki mechaniki: mm, N, MPa i N·mm; geometria, naprężenie i ładunek mają jawne jednostki.
- Bilans sił/momentów, dodatniość energii w zakresie modelu i zgodność serial/parallel sprawdzają testy.
- Siatka HEX8 może pogrubiać nierozdzielone cechy; jest to raportowane i nie może po cichu przyznawać kwalifikacji.
- Beam i HEX8 są różnymi modelami; nie są zamienne tylko dlatego, że mają tę samą długość elementu.
- Regiony multimaterial TET4 nie zastępują zgodnej z CAD geometrii, pełnych interfejsów ani niezależnego badania zbieżności.
- PVDF i klej są nadal przybliżane. Znak ładunku przed wiring oraz układ kanałów nie są pomiarem napięcia rzeczywistego toru elektronicznego.
- Model nonlinear tile może łączyć nieliniową membranę z liniowym podłożem 3D; nie jest to nieliniowa cała skóra robota.

## Podgląd zespołu skóry i rekomendacja

Podgląd 3×3 / 5×5 / 7×7 przedstawia nominalne rozmieszczenie rzeczywistej geometrii genotypu przy pitch obliczonego wariantu. Hash geometrii musi odpowiadać receptorowi użytemu w obliczeniu, a obwiednia musi mieścić się w komórce. Limit szczegółowości może zastąpić powierzchnie oznaczonymi osiami strukturalnymi. Membrana i podłoże w tym widoku są nominalnymi warstwami, bez pola deformacji.

Rekomendacja oznacza najlepszy obliczony wariant danego rozmiaru: dostępny wynik refinement ma pierwszeństwo, potem oceniana jest wykonalność i koszt w obrębie tej samej wierności. Wynik screening nie jest porównywany liczbowo z refinement i nie staje się wynikiem refined przez samo wyświetlenie. Wynik nie jest dowodem globalnego optimum, poprawności CAD ani możliwości wykonania.

## Powtarzalność i porównanie

Archiwa zachowują oryginalne genotypy i wyniki. Porównanie wymaga znanych zgodnych tożsamości źródeł, solvera, protokołu, seeda, noise, ustawień ewaluacji, poziomu dowodów i zbieżności oraz celu/grid/backendu/pitch FEM. Brakujące dane nie są traktowane jako zgodne. Poprawki fizyki/geometrii wymagają ponownej ewaluacji, nie przepisywania starych ocen.

## Procedura weryfikacji programu

```powershell
python -m pip check
python -m pytest -q tests --junitxml=artifacts/pytest.xml
python verify_release.py --browser
```

Raport runnera odróżnia `software_checks_pass`, włączone testy przeglądarki i `release_ready`. Wymagana kontrola Node nie jest pomijana jako sukces. CI obejmuje Windows/Python 3.14 i osobną próbę instalacji oraz kontraktów CPU dla Linux; lokalny wynik Windows nie dowodzi przejścia Linux.

Test kosztownej siatki 8× uruchamia się przez `NEUROSKIN_SLOW_TESTS=1`. GPU wymaga oddzielnego smoke testu i benchmarku obejmującego setup, solve, pełne pole i zużycie pamięci. Rezerwacje RAM/VRAM są estymatami, nie twardymi limitami systemu.

Aktualne wyniki wykonania i znane luki: [VERIFICATION.md](VERIFICATION.md). Kryteria kolejnych funkcji: [roadmapa](RELEASE_PLAN_V30.md).
