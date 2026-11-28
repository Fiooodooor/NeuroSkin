# Walidacja NeuroSkin 3

Oceniaj oddzielnie poprawno?? programu, poziom modelu numerycznego, poprawno?? geometrii CAD, wykonalno?? wykonania i parametry sprz?tu. Sukces HTTP, wysoki fitness lub wy?wietlenie pola 3D nie przyznaje ?adnego z pozosta?ych status?w.

## Poziomy dowod?w

- **T0**: syntetyczny screening i testy na zadeklarowanych modelach/noise; grupy pozycji pozostaj? rozdzielone mi?dzy train/validation/test. Dob?r dekodera i wzmocnienia nie u?ywa zewn?trznego testu.
- **T1**: potrzebne s? jawne dowody poprawnego continuum FEM i zbie?no?ci siatki. Sam solve lub niskie residuum nie wystarcza.
- **T2**: dodatkowo odpowiednia nieliniowo??/kontakt i niezale?na weryfikacja numeryczna.
- **T3**: niezale?ne pomiary, kalibracja, szum i niepewno?? z jednoznacznym pochodzeniem. Sam import CSV nie przyznaje T3.

T3 jest opcjonalne dla wydania oprogramowania i ewolucji; bez danych fizycznych nie wolno deklarowa? skalibrowanych parametr?w sensora. Numery wersji schemat?w JSON s? zachowane dla zgodno?ci formatu i nie oznaczaj? starych wyda? aplikacji.

## Niezmienniki numeryczne

- Jednostki mechaniki: mm, N, MPa i N?mm; geometria, napr??enie i ?adunek maj? jawne jednostki.
- Bilans si?/moment?w, dodatnio?? energii w zakresie modelu i zgodno?? serial/parallel sprawdzaj? testy.
- Siatka HEX8 mo?e pogrubia? nierozdzielone cechy; jest to raportowane i nie mo?e po cichu przyznawa? kwalifikacji.
- Beam i HEX8 s? r??nymi modelami; nie s? zamienne tylko dlatego, ?e maj? t? sam? d?ugo?? elementu.
- Regiony multimaterial TET4 nie zast?puj? zgodnej z CAD geometrii, pe?nych interfejs?w ani niezale?nego badania zbie?no?ci.
- PVDF i klej s? nadal przybli?ane. Znak ?adunku przed wiring oraz uk?ad kana??w nie s? pomiarem napi?cia rzeczywistego toru elektronicznego.
- Model nonlinear tile mo?e ??czy? nieliniow? membran? z liniowym pod?o?em 3D; nie jest to nieliniowa ca?a sk?ra robota.

## Powtarzalno?? i por?wnanie

Archiwa zachowuj? oryginalne genotypy i wyniki. Por?wnanie wymaga znanych zgodnych to?samo?ci ?r?de?, solvera, protoko?u, seeda, noise, ustawie? ewaluacji, poziomu dowod?w i zbie?no?ci oraz celu/grid/backendu/pitch FEM. Brakuj?ce dane nie s? traktowane jako zgodne. Poprawki fizyki/geometrii wymagaj? ponownej ewaluacji, nie przepisywania starych ocen.

## Procedura weryfikacji programu

```powershell
python -m pip check
python -m pytest -q tests --junitxml=artifacts/pytest.xml
python verify_release.py --browser
```

Raport runnera odr??nia `software_checks_pass`, w??czone testy przegl?darki i `release_ready`. Wymagana kontrola Node nie jest pomijana jako sukces. CI obejmuje Windows/Python 3.14 i osobn? pr?b? instalacji oraz kontrakt?w CPU dla Linux; lokalny wynik Windows nie dowodzi przej?cia Linux.

Test kosztownej siatki 8? uruchamia si? przez `NEUROSKIN_SLOW_TESTS=1`. GPU wymaga oddzielnego smoke testu i benchmarku obejmuj?cego setup, solve, pe?ne pole i zu?ycie pami?ci. Rezerwacje RAM/VRAM s? estymatami, nie twardymi limitami systemu.

Aktualne wyniki wykonania i znane luki: [VERIFICATION.md](VERIFICATION.md). Kryteria kolejnych funkcji: [roadmapa](RELEASE_PLAN_V30.md).
