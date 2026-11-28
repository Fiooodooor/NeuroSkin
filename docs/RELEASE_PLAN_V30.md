# NeuroSkin 3 — aktualna roadmapa

Stan aktualizowany na podstawie kodu linii 3 i testów. Dokument zastępuje historyczny dziennik kolejnych rewizji. Cel właściciela: ewoluować przycisk dotykowy/siłowy, wyeksportować parametryczny model bryłowy STEP, następnie opracować skórę robotyczną. Technologię wykonania wybierzemy później.

## Zaimplementowane funkcje

| Obszar | Implementacja | Weryfikacja |
| --- | --- | --- |
| Podgląd ustawień kontynuacji i audyt wzorca | Bieżące porównanie Loaded/Selected, liczba zgodnych/wykluczonych genotypów, PRNG, blokada niepoprawnego scope i ignorowanie opóźnionych odpowiedzi. Gwarantowany pierwszy audyt odziedziczonego wzorca w limicie Top-3 | Kontroler z niskim proxy i lepszym świeżym audytem, API bez uruchamiania ewolucji, uszkodzone archiwa i Chromium z odwróconą kolejnością odpowiedzi |
| Kontynuacja zapisanej sesji | Nowy run z wybranego snapshotu, numeracja G+1, edycja załadowanych kontrolek, świeże oceny, niezmienny rodzic i lineage. Checkpointy populacji/PRNG oraz atomowy snapshot postępu; fallback starszych archiwów do elit | Regresje źródeł, hasha/checksum, kontroli zasobów, rzeczywistego kontrolera, źródłowego runu i Chromium. Nie jest to dokładny replay QD/novelty/cache |
| Wyjaśnienia części i sensorów | Opisy funkcji w drzewie, przewodnik w GUI, spójna legenda. Hub koncepcyjny odróżniony od płyty sprzęgającej; sensory od kompletnej elektroniki | Generowane modele pojedyncze/hybrydowe i test przeglądarkowy |
| User bests | Trzecia kategoria Library: jeden końcowy audytowany champion na completed/stopped run przy niezaokrąglonym audit_score >90; trwały genotyp, audyt i provenance. Preview, eksport, Evaluate All i Multiscale | Regresje progu, braku wpisów iteracyjnych, najlepszego wcześniejszego championa, idempotencji, restartu, API i Chromium |
| GUI Basic / Advanced | `static/workspace.js`: Basic zwija, Advanced rozwija sekcje ustawień; ta sama konfiguracja i silnik | Test przeglądarkowy przełączania i niezmienności ustawień |
| Evolution presets | Cztery przykłady, dostosowanie do liczby CPU, własne zapisy, brak automatycznego startu | Testy Node oraz Chromium |
| Wysokość środkowych wykresów | Resize w pionie i ResizeObserver dopasowujący Plotly | Rzeczywiste przeciągnięcie narożnika w Chromium |
| Wizualizacje zakładek | Stan i wykresy przypisane do kandydata; ukryte widoki zwalniają wykresy | Testy kontekstu, raportów i Chromium |
| FEM 2×2 / 3D | Cztery standardowe przypadki ze wspólnymi skalami; dodatkowy inspektor | Regresje pól, sił i przeglądarki |
| Drzewo komponentów | Dokładne przedziały prymitywów, wybór i podświetlenie, człon/film | Python, Node, Chromium |
| Przepływ sił | Faktyczne siły węzłowe i reakcje; przybliżone przekroje trakcji podłoża | Bilans sił/momentów, testy pól i GUI; nie są to dokładne linie prądu naprężeń |
| Sygnały PVDF | Podpisany ładunek filmu, mapowanie member/film, przebiegi i schematy połączeń | Testy transdukcji, drzewa, fusion i GUI |
| Electronics-aware evolution | Cel electronics, moc/kanały/pasmo/headroom/SNR w screeningu i Pareto | `tests/test_electronics_evolution_v30.py` |
| Równoległy Evaluate All | Niezależne audyt/walidacja/orientacja, lokalny FEM, deterministyczne scalanie | Test prawdziwego spawn/serial oraz DAG |
| Podgląd zespołu skóry 3×3 / 5×5 / 7×7 | Geometria receptora rozmieszczona według obliczonego pitch i footprint; wybór wariantu, czujnika i widoczności warstw. Rozciągany podgląd 3D | Geometria, hash genotypu, API, Node i Chromium; geometria nominalna, nie deformacja ani kwalifikacja CAD |

## Rozwijane i weryfikowane

| Obszar | Co faktycznie jest w kodzie | Bramka dalszego rozwoju |
| --- | --- | --- |
| Równoległy matrix-free | Wspólna pula gather, rozłączne zapisy, partycje według incidencji, współbieżne RHS | Pomiar przyspieszenia całego audytu na docelowej stacji, nie sam procent CPU |
| Scheduler CPU/RAM/GPU | Atomowe estymowane rezerwacje CPU/RAM/VRAM, do czterech ręcznych analiz, jeden slot GPU, telemetria procesu | Twarde limity zasobów, odzyskiwanie zadań i zarządzanie między procesami pozostają otwarte |
| Multimaterial nonlinear FEM | TET4 Neo-Hookean z regionami materiałowymi, naprężenia Cauchy'ego, adaptacyjna kontynuacja kontaktu | Niezależna zbieżność siatki/kary, geometria CAD, realistyczne interfejsy i materiały |
| Fizyczne sprzężenia Skin Tile | Membrana Q1 i receptorowe sprężyny; wybrane modele z pełną podatnością liniowego podłoża 3D. Obsługa 7×7 także w solverach | Doświadczalna kalibracja i sprzężenie styczne/elektryczne; obecnie model T0 |
| Nieliniowa membrana i podatne podłoże 3D | Föppl–von Kármán u/v/w, relaksacja w płaszczyźnie, liniowy substrate TET4, bilans i pola | Podłoże nieliniowe, zmarszczki, zginanie i realistyczne warunki mocowania |
| Ewolucja wielopoziomowa | Dwustopniowe hybrydy i referencyjny transport wrench 1–3 stopni | Niezależne genotypy/materiały/geometrie stopni, pełne mapowanie i audyt; nie utożsamiać z samym wyborem hybrydy |
| Optymalizacja fragmentu skóry | Dyskretne porównanie bibliotek, siatek 3/5/7, pretension/depth przy stałym footprint; refinement i osobny holdout. Rekomendacja osobno dla siatki, w obrębie jednej wierności | Ciągła ewolucja układu i geometrii; najlepszy obliczony wariant nie jest globalnym optimum ani walidacją sprzętu |
| Kwalifikacja stabilnego 3.0 | Regresje numeryczne/API/Node/Chromium; wspólna tożsamość źródeł, naprawione archiwum i czas generacji | Pełny czysty przebieg Windows/Linux, opcjonalne kosztowne siatki, benchmarki i odtwarzalna instalacja. VERSION pozostaje rozwojowe |

## Otwarte etapy produktu — kolejność wykonania

1. **CAD przycisku / conforming CAD-to-FEM**: skończony parametryczny opis geometrii, pierwszy wspierany typ receptora, poprawne połączone bryły, nazwane ciała materiałowe, STEP, ponowny import i porównanie objętości/granic. Zachować genotyp i parametryczny opis; nie nazywać triangulowanego STL modelem parametrycznym. Dopiero potem tagowany mesh zgodny z CAD.
2. **Pełne PVDF–klej–elastomer**: zgodne interfejsy i materiały, mechanika warstw i przenoszenie odkształceń; pełne sprzężenie elektryczne pozostaje osobną bramką. Nie podnosić poziomu dowodów na podstawie obecnego embedded/shell postprocessingu.
3. **Niezależne instancje ewolucji**: jawny identyfikator instancji, osobny kontroler/PRNG/archive, wspólna atomowa rezerwacja, izolowane Start/Pause/Stop/cleanup, testy równoległych cykli. Dzisiejsze przypięte sesje inspekcji nie są instancjami ewolucji.
4. **Wieloskalowa ewolucja skóry**: wspólny footprint i scenariusze, niezależny optymalizator układu oraz receptorów, wymiana tylko jawnie porównywalnych wyników, statyczna i dynamiczna rekonstrukcja z właściwych kanałów.
5. **Full Robot Skin Engine**: powierzchnia robota/krzywizna, rozmieszczenie, kolizje i prześwity, mocowanie, połączenia elektryczne/bus, synchronizacja, kalibracja oraz eksport zespołu CAD. Obecny prostokątny tile nie realizuje tego silnika.
6. **Fabrication profile**: dopiero po wyborze procesu i materiałów ustalić minimalne cechy, tolerancje, klejenie, okablowanie i kwalifikację wykonania.

Dla każdego etapu: najpierw niezmienniki i kryteria akceptacji, potem minimalny adapter/implementacja, następnie regresje i raport dowodów. Nie obniżać progów fizycznych, nie nazywać diagnostyki kwalifikacją i nie przedstawiać niezaimplementowanych funkcji jako gotowych.

## Kryteria wydania

- Wszystkie wymagane testy Python i Node przechodzą; brak narzędzia jest jawnie nieudaną bramką.
- GUI Chromium pokrywa Basic/Advanced, presety, resize, Evolve/Pause/Stop, Evaluate All, przypięte konteksty, eksport, archive replay i obliczony podgląd skóry.
- Raport zawiera wersję środowiska, identyczność źródeł/protokołu/ustawień i statusy pominiętych testów.
- Eksperymenty są zachowane; wyniki o innej tożsamości nie są bezpośrednio porównywane.
- T3 z pomiarami jest opcjonalne dla wydania programu i ewolucji, ale wymagane dla twierdzeń o skalibrowanym działaniu sprzętu.

Szczegóły bieżącego wykonania: [VERIFICATION.md](VERIFICATION.md). Granice modeli: [VALIDATION.md](VALIDATION.md).
