# NeuroSkin — zatwierdzony plan zadań i kryteria akceptacji

**Zasada jakości:** projekt nie nadaje etykiety "hardware verified" na podstawie symulacji. Każda wersja musi zachować archiwalną odtwarzalność, przejść testy regresji oraz publikować niewykonane zadania wprost.

## P0 — fundament walidacji (NeuroSkin 2.2)

- [x] **P0.1** Wersjonowany `validation_protocol_v30.json` + walidacja Pydantic. **Akceptacja:** błędne zakresy i niepełny protokół są odrzucane.
- [x] **P0.2** Testy jawne `pass/fail/not_run/unsupported`, zakaz cichej promocji T1/T2/T3. **Akceptacja:** brak wymaganego testu lub dowodu uniemożliwia `pass`.
- [x] **P0.3** Metadane: SHA-256 protokołu, genotypu, kodu solvera, materiałów, Python/numerics, seed, źródło szumu. **Akceptacja:** powtórzenie przy tych samych warunkach daje ten sam raport T0.
- [x] **P0.4** Wspólny merger FEM/PVDF/odciążenia dla Top-3 i Evaluate All. **Akceptacja:** ręczna siła podglądu nie zmienia referencyjnej punktacji.
- [x] **P0.5** Fail-closed pojedynczej walidacji, bez ukrywania błędów. **Akceptacja:** osobnik ze złą geometrią nie jest promowany.
- [x] **P0.6** GUI i API z osobnymi wynikami oraz archiwalnymi hashami protokołu. **Akceptacja:** nieporównywalne archiwa nie dostają delty fitness.
- [x] **P0.7** Zachowanie trybu Windows/CPU, archiwum, 10 hybryd i zatrzymywania z Ctrl+C. **Akceptacja:** regresja kluczowych modułów.

## P1 — mierzalna informacja dotykowa (NeuroSkin 2.2–2.4)

- [x] **P1.1** Grupowy holdout wg punktu kontaktu, ridge z normalizacją wyłącznie na treningu. **Akceptacja:** zero wspólnych pozycji train/test; raport błędów Fx/Fy/Fz i X/Y.
- [x] **P1.2** Jacobian, wartości osobliwe i warunkowanie z jawną założoną kowariancją szumu. **Akceptacja:** brak przypisywania przyjętych sigma danym pomiarowym.
- [x] **P1.3** Monte Carlo niepewności materiału, szczeliny, kleju i szumu. **Akceptacja:** seed, rozkład i percentyle w raporcie.
- [x] **P1.4** Front Pareto finalistów Top-3 (błąd siły, pozycji, SNR p10). **Akceptacja:** dostępny w decyzji etapu obok punktacji scalonej.
- [ ] **P1.5** Porównanie decoderów: fizycznie ograniczony Jacobian, ridge, mała sieć nieliniowa. **Akceptacja:** rozłączne sesje i indywidualne protokoły holdout, porównanie metryk z przedziałami ufności.
- [ ] **P1.6** Walidacja odporności na nowe kształty wgłębników i niezależne sesje; bieżący model nie rozróżnia ich fizycznie. **Akceptacja:** pomiar lub rozwiązanie kontaktu z rzeczywistą geometrią wgłębnika.

## P2 — dokładniejsza fizyka (od NeuroSkin 2.5)

- [x] **P2.1** Utrzymanie obecnego liniowego HEX8 i laminate postprocess w obecnym pipeline; brak podnoszenia wyniku do T1 bez dowodu zbieżności.
- [ ] **P2.2** Zgodny z geometrią mesher tetra z oddzielnymi regionami elastomer/PVDF/klej. **Akceptacja:** zamknięta siatka, testy jakości, benchmark zbieżności.
- [ ] **P2.3** Duże deformacje, hipersprężystość, nieliniowy kontakt i cykl load/unload. **Akceptacja:** benchmark analityczny + reakcje + zgodność z eksperymentami na próbkach.
- [ ] **P2.4** Oddzielne limity jednoczesnych kosztownych solverów i budget pamięci dla Z840. **Akceptacja:** brak oversubscription podczas 8× finer mesh.

## P3 — elektronika i energetyka (NeuroSkin 2.2–2.6)

- [x] **P3.1** Przybliżony budżet kanałów, latencji, transmisji, energii i mocy z jawnymi założeniami. **Akceptacja:** parametry wyliczane dla liczby folii w genotypie; bez fikcyjnej ceny BOM.
- [ ] **P3.2** Charakterystyki prawdziwego CDC/AFE, pasożyty, pasmo, dryft, szum i przełączanie stanów. **Akceptacja:** pomiary układu prototypowego lub dostatecznie sprawdzona karta katalogowa.
- [ ] **P3.3** Układ obwodów dla 4/8 PVDF, opcje różnicowe, PCB, BOM. **Akceptacja:** weryfikowalne elementy, projekt elektryczny i test EMC.

## P4 — pętla z fizycznym prototypem (NeuroSkin 2.2–3.0)

- [x] **P4.1** Lokalny importer CSV ze schematem, limitami, SHA-256 i holdoutem pozycyjnym. **Akceptacja:** nie awansuje automatycznie do T3, nie udostępnia prywatnych plików przez API.
- [ ] **P4.2** Stanowisko kalibracyjne (czujnik siły referencyjnej, pozycjoner, wgłębniki, temperatura, oscyloskop/CDC).
- [ ] **P4.3** Rzeczywiste pomiary siła–ugięcie, spektrum szumu, powrót/creep, cykle zmęczeniowe.
- [ ] **P4.4** Fit parametrów materiałów i elektroniki na kalibracji oraz niezależny test sprzętowy.
- [ ] **P4.5** Kwalifikacja T3 z udokumentowaną niepewnością i laboratoryjnymi danymi.

## Zależności i kolejność

1. P0 musi być stabilny przed P1/P2.
2. Do rzeczywistego T1 wymagane jest P2.2 + zbieżność siatki; sama równowaga HEX8 nie wystarcza.
3. Pełne P2.3/P3.2/P4.4 wymagają pomiarów fizycznych parametrów materiału i elektroniki.
4. Kolejna wersja kodu nie może tracić znanych funkcji, ale *nie da się udowodnić*, że żadna nieobserwowana regresja nie istnieje. Testy i benchmarki są jawne.
5. Wszystkie punktacje syntetyczne oznaczamy T0 i nie traktujemy ich jako skuteczności rzeczywistego receptora.
