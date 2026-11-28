# Windows 11 / HP Z840 — instalacja i testy NeuroSkin 2.2

Otwórz **PowerShell** w wypakowanym katalogu `neuroskin_evolution_lab_v22`:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q tests/test_validation_v22.py tests/test_pipeline_v10.py tests/test_archive_api_v11.py
python server.py --cores auto --open --port 8765
```

Wybierz w bibliotece geometrię, naciśnij **Evaluate All** i sprawdź panel **Validation T0**. Następnie uruchom **Evolve**; każdy finalist Top-3 ma identyczną definicję protokołu i indywidualny wynik.

Test bez GUI:

```powershell
python validation_cli.py --family quadrant --genome EXAMPLE_GENOME_V22.json --out my_validation.json
python evolve_cli.py --cores 2 --seconds 6 --population 12 --no-fem --audit-grid 3 --out runs_my_smoke
```

`--no-fem` służy wyłącznie do szybkiego testu działania pipeline, nie do walidacji mechaniki. Domyślna ewolucja nadal korzysta z FEM HEX8. Na dwuprocesorowej Z840 rekomenduję rozpoczęcie od 16–20 workerów; CPU affinity/NUMA i liczba fizycznych rdzeni dostępnych procesowi zależą od Windows.

**Przy wysokiej rozdzielczości** obliczenia HEX8 mogą być czasochłonne i pamięciochłonne. GPU Quadro P1000 4 GB nie powinno być automatycznie wybierane do dużych FEM.

**Uwaga dotycząca `pip check`:** test jest wiarygodny w nowym, czystym `.venv`. Współdzielone środowiska z dodatkowymi pakietami (np. MoviePy/Pillow) mogą mieć niepowiązane konflikty.

**Zamknięcie:** w PowerShell `Ctrl+C` w procesie głównym. Alternatywny launcher `launch_windows.ps1` zachowano z v2.1.1. Windows signal handling wymaga sprawdzenia na Twojej fizycznej stacji.
