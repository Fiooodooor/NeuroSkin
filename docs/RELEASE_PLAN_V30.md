# NeuroSkin 3 ? aktualna roadmapa

Stan aktualizowany na podstawie kodu linii 3 i test?w. Dokument zast?puje historyczny dziennik kolejnych rewizji. Cel w?a?ciciela: ewoluowa? przycisk dotykowy/si?owy, wyeksportowa? parametryczny model bry?owy STEP, nast?pnie opracowa? sk?r? robotyczn?. Technologi? wykonania wybierzemy p??niej.

## Zaimplementowane funkcje

| Obszar | Implementacja | Weryfikacja |
| --- | --- | --- |
| GUI Basic / Advanced | `static/workspace.js`: Basic zwija, Advanced rozwija sekcje ustawie?; ta sama konfiguracja i silnik | Test przegl?darkowy prze??czania i niezmienno?ci ustawie? |
| Evolution presets | Cztery przyk?ady, dostosowanie do liczby CPU, w?asne zapisy, brak automatycznego startu | Testy Node oraz Chromium |
| Wysoko?? ?rodkowych wykres?w | Resize w pionie i ResizeObserver dopasowuj?cy Plotly | Rzeczywiste przeci?gni?cie naro?nika w Chromium |
| Wizualizacje zak?adek | Stan i wykresy przypisane do kandydata; ukryte widoki zwalniaj? wykresy | Testy kontekstu, raport?w i Chromium |
| FEM 2?2 / 3D | Cztery standardowe przypadki z wsp?lnymi skalami; dodatkowy inspektor | Regresje p?l, si? i przegl?darki |
| Drzewo komponent?w | Dok?adne przedzia?y prymityw?w, wyb?r i pod?wietlenie, cz?on/film | Python, Node, Chromium |
| Przep?yw si? | Faktyczne si?y w?z?owe i reakcje; przybli?one przekroje trakcji pod?o?a | Bilans si?/moment?w, testy p?l i GUI; nie s? to dok?adne linie pr?du napr??e? |
| Sygna?y PVDF | Podpisany ?adunek filmu, mapowanie member/film, przebiegi i schematy po??cze? | Testy transdukcji, drzewa, fusion i GUI |
| Electronics-aware evolution | Cel electronics, moc/kana?y/pasmo/headroom/SNR w screeningu i Pareto | `tests/test_electronics_evolution_v30.py` |
| R?wnoleg?y Evaluate All | Niezale?ne audyt/walidacja/orientacja, lokalny FEM, deterministyczne scalanie | Test prawdziwego spawn/serial oraz DAG |

## Rozwijane i weryfikowane

| Obszar | Co faktycznie jest w kodzie | Bramka dalszego rozwoju |
| --- | --- | --- |
| R?wnoleg?y matrix-free | Wsp?lna pula gather, roz??czne zapisy, partycje wed?ug incidencji, wsp??bie?ne RHS | Pomiar przyspieszenia ca?ego audytu na docelowej stacji, nie sam procent CPU |
| Scheduler CPU/RAM/GPU | Atomowe estymowane rezerwacje CPU/RAM/VRAM, do czterech r?cznych analiz, jeden slot GPU, telemetria procesu | Twarde limity zasob?w, odzyskiwanie zada? i zarz?dzanie mi?dzy procesami pozostaj? otwarte |
| Multimaterial nonlinear FEM | TET4 Neo-Hookean z regionami materia?owymi, napr??enia Cauchy'ego, adaptacyjna kontynuacja kontaktu | Niezale?na zbie?no?? siatki/kary, geometria CAD, realistyczne interfejsy i materia?y |
| Fizyczne sprz??enia Skin Tile | Membrana Q1 i receptorowe spr??yny; wybrane modele z pe?n? podatno?ci? liniowego pod?o?a 3D | Do?wiadczalna kalibracja i sprz??enie styczne/elektryczne; obecnie model T0 |
| Nieliniowa membrana i podatne pod?o?e 3D | F?ppl?von K?rm?n u/v/w, relaksacja w p?aszczy?nie, liniowy substrate TET4, bilans i pola | Pod?o?e nieliniowe, zmarszczki, zginanie i realistyczne warunki mocowania |
| Ewolucja wielopoziomowa | Dwustopniowe hybrydy i referencyjny transport wrench 1?3 stopni | Niezale?ne genotypy/materia?y/geometrie stopni, pe?ne mapowanie i audyt; nie uto?samia? z samym wyborem hybrydy |
| Optymalizacja fragmentu sk?ry | Dyskretne por?wnanie bibliotek, rozmiar?w siatki, pretension/depth przy sta?ym footprint; refinement i osobny holdout | Ci?g?a ewolucja uk?adu i geometrii; obecne wyniki nie promuj? receptora i nie stanowi? walidacji sprz?tu |
| Kwalifikacja stabilnego 3.0 | Regresje numeryczne/API/Node/Chromium; wsp?lna to?samo?? ?r?de?, naprawione archiwum i czas generacji | Pe?ny czysty przebieg Windows/Linux, opcjonalne kosztowne siatki, benchmarki i odtwarzalna instalacja. VERSION pozostaje rozwojowe |

## Otwarte etapy produktu ? kolejno?? wykonania

1. **CAD przycisku / conforming CAD-to-FEM**: sko?czony parametryczny opis geometrii, pierwszy wspierany typ receptora, poprawne po??czone bry?y, nazwane cia?a materia?owe, STEP, ponowny import i por?wnanie obj?to?ci/granic. Zachowa? genotyp i parametryczny opis; nie nazywa? triangulowanego STL modelem parametrycznym. Dopiero potem tagowany mesh zgodny z CAD.
2. **Pe?ne PVDF?klej?elastomer**: zgodne interfejsy i materia?y, mechanika warstw i przenoszenie odkszta?ce?; pe?ne sprz??enie elektryczne pozostaje osobn? bramk?. Nie podnosi? poziomu dowod?w na podstawie obecnego embedded/shell postprocessingu.
3. **Niezale?ne instancje ewolucji**: jawny identyfikator instancji, osobny kontroler/PRNG/archive, wsp?lna atomowa rezerwacja, izolowane Start/Pause/Stop/cleanup, testy r?wnoleg?ych cykli. Dzisiejsze przypi?te sesje inspekcji nie s? instancjami ewolucji.
4. **Wieloskalowa ewolucja sk?ry**: wsp?lny footprint i scenariusze, niezale?ny optymalizator uk?adu oraz receptor?w, wymiana tylko jawnie por?wnywalnych wynik?w, statyczna i dynamiczna rekonstrukcja z w?a?ciwych kana??w.
5. **Full Robot Skin Engine**: powierzchnia robota/krzywizna, rozmieszczenie, kolizje i prze?wity, mocowanie, po??czenia elektryczne/bus, synchronizacja, kalibracja oraz eksport zespo?u CAD. Obecny prostok?tny tile nie realizuje tego silnika.
6. **Fabrication profile**: dopiero po wyborze procesu i materia??w ustali? minimalne cechy, tolerancje, klejenie, okablowanie i kwalifikacj? wykonania.

Dla ka?dego etapu: najpierw niezmienniki i kryteria akceptacji, potem minimalny adapter/implementacja, nast?pnie regresje i raport dowod?w. Nie obni?a? prog?w fizycznych, nie nazywa? diagnostyki kwalifikacj? i nie przedstawia? niezaimplementowanych funkcji jako gotowych.

## Kryteria wydania

- Wszystkie wymagane testy Python i Node przechodz?; brak narz?dzia jest jawnie nieudan? bramk?.
- GUI Chromium pokrywa Basic/Advanced, presety, resize, Evolve/Pause/Stop, Evaluate All, przypi?te konteksty, eksport i archive replay.
- Raport zawiera wersj? ?rodowiska, identyczno?? ?r?de?/protoko?u/ustawie? i statusy pomini?tych test?w.
- Eksperymenty s? zachowane; wyniki o innej to?samo?ci nie s? bezpo?rednio por?wnywane.
- T3 z pomiarami jest opcjonalne dla wydania programu i ewolucji, ale wymagane dla twierdze? o skalibrowanym dzia?aniu sprz?tu.

Szczeg??y bie??cego wykonania: [VERIFICATION.md](VERIFICATION.md). Granice modeli: [VALIDATION.md](VALIDATION.md).
