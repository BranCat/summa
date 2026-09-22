# SUMMA objective function: C wrapper, Python, SPOTPY

Calls SUMMA (with mizuRoute routing in the same process) from Python as `J(params) -> float`,
so any Python optimizer can drive it.

| File | Purpose |
|---|---|
| `../build/source/driver/summa_c_api.f90` | C-callable `summa_evaluate(param_values, n, objective, err)` |
| `../test_summa_c_api.c` | minimal C program calling the wrapper |
| `summa_python_interface.py` | ctypes wrapper exposing `J(params)` |
| `spotpy_setup.py`, `calibrate_summa.py` | SPOTPY example |
| `results_analysis.py` | routed flow at one segment vs observations (KGE, NSE, PBIAS + plot) |

## Build
```bash
cd build
make            # summa.exe
make libsumma   # libsumma.dylib (macOS); Linux needs -shared / .so
```
`calibration/libsumma.dylib` is a symlink to the built library.

## Tests (test case CAN_05BB001, included in `test_coupled/`)
1. C call: `./test_summa_c_api` → objective **-10.2181321285**
2. Python: `python calibration/summa_python_interface.py` → **-10.218132128510868**
3. SPOTPY: `python calibration/calibrate_summa.py` → 5 iterations, ≈ -10.23 to -10.25

## Running a calibrated domain (no overrides)
```bash
./bin/summa.exe -m <fileManager.txt> -c <config.toml> -s <suffix>
SUMMA_DOMAIN=/path/to/my_domain python calibration/results_analysis.py
```

## Known limitations
- `make libsumma` is macOS-only (`-dynamiclib`, `.dylib`).
- `J()` always overrides its parameters, by design.
- The `--param` CLI path is untested.
- `seg_outlet = -9999` falls back to the largest-drainage-area reach.
- SPOTPY bounds and the sign convention are placeholders.
