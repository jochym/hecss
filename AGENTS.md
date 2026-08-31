# General behavioral rules

Observe rules described in @karpathy-guidelines.md and take into account @karpathy-examples.md in your work.
These are good guidelines to folow to keep the code simple and clean, and by extension correct.

# Interaction rules

Regardless of the language the user is using always write in English - both in the code and in the dialogs.

# Build Pipeline Reference

The complete build pipeline is documented in **BUILD_PIPELINE.md**.  
Key points for agents:

* **Pipeline:** `notebooks/*.py` → `marimo export script` → `patches/02-scripts.py` (AugAssign) → `scripts/build_lib.py` → `hecss/`
* **Configuration:** `pyproject.toml` `[tool.build_lib]` — paths, `init_star_import`
* **Tags:** `#| default_exp`, `#| export`, `#| exporti`, `#| exporti <mod>`, `#| hide` — nbdev semantics
* **Tag logic:** `export` → `__all__`, `exporti` → internal, `exporti <mod>` → cross-module, `hide` excluded
* **Cross-module:** `exporti <mod>` blocks appended to target module, imports merged
* **Disposable patches:** `patches/01-notebooks.py` (notebook fixes), `patches/02-scripts.py` (AugAssign revert) — remove after confidence
* **Canonical reference:** git tag `3578cce` (v0.5.29 on test.pypi.org)
* **Canonical module docstrings:** extracted from original `.ipynb` first markdown cell via `git show 3578cce:<module>.ipynb`

**Build command:** `python scripts/build_lib.py` (generic, config via `[tool.build_lib]` in `pyproject.toml`)

**Verification:** `python /tmp/verify_final.py` (AST logic parity, imports, __all__, docstrings, smoke test)