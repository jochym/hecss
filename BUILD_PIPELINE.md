# hecss Build Pipeline Documentation

**Version:** 1.0 (post-migration to Marimo)  
**Last Updated:** 2025  
**Canonical Commit:** `3578cce` (v0.5.29 on test.pypi.org)  
**Pipeline Script:** `scripts/build_lib.py` (generic, zero project-specific logic)

---

## Overview

The build pipeline transforms **literate marimo notebooks** into a clean Python package (`hecss/`) with zero project-specific logic in the build script. The pipeline is fully generic and driven by `#|` tags in marimo notebooks.

```
┌─────────────────┐     marimo convert      ┌──────────────┐
│  *.ipynb        │ ──────────────────────▶ │ notebooks/   │  (literate, all cells preserved)
│  (canonical)    │   (one-time, v0.24.0)   │ *.py         │
└─────────────────┘                           └──────┬───────┘
                                                     │
                                                     │  patches/01-notebooks.py (disposable)
                                                     ▼
                                            notebooks/*.py (patched)
                                                     │
                                                     │  marimo export script
                                                     ▼
                                            build/scripts/*.py (intermediate)
                                                     │
                              ┌──────────────────────┘
                              ▼
                    patches/02-scripts.py (AugAssign revert)
                                                     │
                                                     ▼
                                    build/scripts/*.py (patched)
                                                     │
                                                     ▼
                              scripts/build_lib.py (generic)
                                                     │
                                                     ▼
                                            hecss/*.py + __init__.py
```

---

## Pipeline Stages

### Stage 1: ipynb → marimo notebooks (one-time, manual)
```bash
marimo convert *.ipynb -o notebooks/
```
- **Tool:** `marimo convert` (v0.24.0 used for migration)
- **Input:** 19 canonical `.ipynb` files from commit `3578cce`
- **Output:** `notebooks/*.py` (20 files, 19 library + 1 legacy)
- **Preserves:** All markdown cells (`mo.md`), cell order, tags (`#| export`, `#| hide`, etc.), literate structure
- **One-time only** — committed to git, not re-run

### 2. Stage 1 Patches (`patches/01-notebooks.py`) — disposable
Run once after `marimo convert` to fix known conversion artifacts:

| Fix | Description |
|-----|-------------|
| `99_mh.py` | Remove `#| default_exp mh` → legacy marker (`#| hide` + comment) |
| `11_parwidth.py` | Async cell → sync wrapper (`asyncio.run(...)`) |
| All notebooks | Remove 19× `app._unparsable_cell` wrappers (nbdev boilerplate) |
| 8 lib notebooks | Restore `#| default_exp <module>` (stripped by unparsable removal) |
| `11_parwidth.py` | Async cell → sync wrapper (`asyncio.run(...)`) |

**Verification:** `python patches/01-notebooks.py` — asserts match counts.

---

### Stage 3: marimo export script (validation gate)
```bash
marimo export script notebooks/<nb>.py -o build/scripts/<nb>.py
```
- **Purpose:** Validates notebook wiring (catches cycles, undefined refs)
- **Output:** `build/scripts/*.py` (flat scripts, `# %%` separators, `#|` tags preserved)
- **Failures expected:** `11_core.py` (cycles) — handled gracefully in builder

---

### Stage 4: `patches/02-scripts.py` — disposable
Runs on `build/scripts/*.py` to revert `marimo export` reformatting:
| Transform | Regex | Count |
|-----------|-------|-------|
| `a = a + b` → `a += b` | `^(\s*)(\w+) = \2 ([+\-*/]) (.+)$` | 28 total |
| `a = a - b` → `a -= b` | similar | |
| `a = a * b` → `a *= b` | similar | |
| `a = a / b` → `a /= b` | similar | |

**Verification:** AST logic identical before/after (`ast.dump(StripDoc(...))` equal).  
**Disposable:** Removed after confidence in export stability.

---

### Stage 5: `scripts/build_lib.py` (permanent, generic)

**Entry point:** `python scripts/build_lib.py`

**Configuration** (via `pyproject.toml` `[tool.build_lib]`):
```toml
[tool.build_lib]
notebooks_dir = "notebooks"      # default
output_dir = "hecss"             # default
build_dir = "build"              # default
init_star_import = "core"        # for __init__.py
```

**Pipeline:**
1. **Phase 1:** Export all tagged notebooks → `build/scripts/` (validation gate)
2. **Phase 2:** Apply `patches/02-scripts.py` (AugAssign revert)
3. **Phase 3:** Parse `build/scripts/*.py` → tagged blocks (`parse_script`)
   - Falls back to `parse_notebook_blocks()` if export failed (cycles)
4. **Assembly:**
   - Group blocks by `#| default_exp <module>` → `targets[module]`
   - Cross-module `exporti <mod>` → `cross[target].extend(blocks)`
   - `build_module()` → `hecss/<module>.py`
     - Module docstring from canonical ipynb first markdown cell (extracted via `git show 3578cce:<ipynb>`)
     - `split_imports()` → dedup + sort (stdlib → third-party → local)
     - `__all__` from `export` blocks only
   - Cross-module `exporti <target>` → appended via `merge_into_module()`
4. `__init__.py` generated with version + `from .core import *`

**Key generic features:**
- Zero hardcoded module names (discovered via `#| default_exp`)
- Tag semantics: `export` → `__all__`, `exporti` → internal, `exporti <mod>` → cross-module, `hide` → skip
- Last-tag-wins for multiple tags on one cell
- `hide`/`asap`/`eval`/etc. → preserved in notebooks, excluded from library
- Cross-module: `exporti <target>` blocks appended to target module, imports merged

---

## Native marimo cells vs. nbdev tags

marimo exposes three "special" cell kinds beyond the regular `@app.cell`. They
are **not** used as library gates — the `#|` tags above remain the single
source of truth for what lands in `hecss/`. None of the current notebooks use
`app.setup`; `@app.function` appears in `16_util.py` / `99_mh.py`.

| marimo cell | Purpose | Maps to nbdev tag? | Role in this pipeline |
|-------------|---------|--------------------|-----------------------|
| `@app.cell` | Regular reactive cell | `#\| export` / `#\| exporti` / `#\| hide` | **Primary.** Tags gate inclusion |
| `@app.function` | Pure, top-level importable function | partial — it is a cell like any other; tags still govern inclusion | Authoring convenience; `marimo export script` flattens it to a plain `def` and keeps `#\|` tags |
| `@app.class_definition` | Pure, top-level importable class | partial — same as function | Authoring convenience; flattened like `def` on export |
| `app.setup` (`with app.setup:`) | Shared imports for top-level funcs/classes | **does not map** — imports are stripped by `marimo export script` | Currently **not usable** for cross-cell import hoisting |

### Why tags stay the gate, not these cells
- **`export` vs `exporti` (public vs internal) has no marimo equivalent.** A
  `@app.function` cell is importable by *any* notebook, but `hecss` needs to
  distinguish `__all__` members from internal helpers. `#\| export` / `#\| exporti`
  carry that distinction; the cell decorator does not.
- **`exporti <mod>` (cross-module) is purely a build-time concept.** marimo has
  no notion of routing a cell into another module. Only the tag does this.
- **`app.setup` is lost on export.** `marimo export script` drops `with app.setup:`
  bodies entirely (verified 0.24.0), so it cannot feed the library build. The
  conventional `import` blocks inside `#\| exporti`/`#\| export` cells are what
  `split_imports()` collects and merges.
- **Byte parity with canonical `3578cce` was the goal.** Reworking gates onto
  marimo cells would change code shape and risk drifting from nbdev semantics.
- `asap`/`vasp`/`slow`/`eval` remain doc/run flags (`#\|` comments), never gates.

#### Where the setup cell drops out of the pipeline
The drop happens in **Stage 3 (`marimo export script`)** — not in the notebook
files and not in `build_lib.py`. Specifically, marimo's
`_convert/script.py:convert_from_ir_to_script` emits only regular cells:

```python
codes = ["# %%\n" + graph.cells[cid].code
         for cid in topological_sort(graph, graph.cells.keys())]
```

`graph.cells` holds `@app.cell` / `@app.function` / `@app.class_definition`
only. The setup cell is stored separately on the app (`app._setup`, a
`_SetupContext`), **outside** `graph.cells`, so this loop never sees it. It is
preserved in the notebook's own canonical serialization (`InternalApp.to_py()`)
but stripped by the flat-script exporter. The notebook-direct fallback
(`parse_notebook_blocks`) would also miss it, because it keys off
`@app.cell` markers. To feed a future `app.setup` into the library, the build
would need to read the `with app.setup:` block directly from the notebook file
and merge its `stmt*` imports like any other import block — no `marimo export
script` change required. Not done now: no current notebook uses it.

**Conclusion:** `@app.function` / `@app.class_definition` are kept for authoring
ergonomics; `app.setup` is documented-but-unused. Library membership stays
100% tag-driven. If marimo later gains a native "export to module" / "exclude
from module" cell property, that could replace `#\| export`/`hide` — worth
revisiting then, not now.

---

## Configuration Files

### `pyproject.toml` (project root)
```toml
[tool.build_lib]
init_star_import = "core"   # module to re-export in hecss/__init__.py
notebooks_dir = "notebooks" # optional
output_dir = "hecss"        # default
build_dir = "build"         # default
```

### `scripts/build_lib.py` (permanent)
- **No hardcoded module names** — discovered via `#| default_exp`
- Tag parsing: `resolve_tags()` → `{'export': set(), 'exporti': {'core'}, 'hide': ...}`
- Tag resolution: last-tag-wins, `hide` ⊃ `export` for library exclusion
- Imports: `split_imports()` dedup + sort (stdlib → 3rd-party → local)
- Docstrings: extracted from canonical ipynb first markdown cell (git show 3578cce)

### `patches/01-notebooks.py` (disposable)
Run once after `marimo convert`:
- Removes 19 `_unparsable_cell` (unwraps 5 real cells, drops 19 nbdev imports)
- Restores `default_exp` for 8 lib modules
- Fixes `11_parwidth.py` async → sync
- De-targets `99_mh.py` (legacy)

### `patches/02-scripts.py` (disposable)
AugAssign revert on `build/scripts/*.py`:
```python
pattern = r'^([ \t]*)(\w+) = \2 ([+\-*/]) ([^\n]+)$'
repl = r'\1\1 \2= \4'
```

---

## Verification Gates

| Gate | Command | Pass Criteria |
|------|---------|---------------|
| **Unit** | `uv run python scripts/build_lib.py` | 8 modules built, 0 real diffs |
| **Import** | `python -c "import hecss"` | 9/9 modules load |
| **Parity** | `verify_battery.py` | 0 real diffs, 8/8 docstrings, 9/9 imports |
| **Byte diff** | `diff -u <(git show 3578cce:hecss/X.py) hecss/X.py` | ≤ AugAssign + ws |

---

## Maintenance

### Adding a new module
1. Create `notebooks/<name>.py` with `#| default_exp <name>`
2. Tag cells `#| export` / `#| exporti` / `#| exporti other_mod`
3. Run `python scripts/build_lib.py` → auto-discovers module

### Updating `marimo` version
1. `uv pip install marimo@<new_version>`
2. `marimo convert *.ipynb -o notebooks/` (re-run stage 1)
3. Re-run `patches/01-notebooks.py` (fixes new conversions)
3. Rebuild: `python scripts/build_lib.py`

### Cleaning disposable patches
```bash
git rm patches/01-notebooks.py patches/02-scripts.py
git commit -m "cleanup: drop disposable migration patches"
```

---

## Key Files Reference

| File | Role | Status |
|------|------|--------|
| `scripts/build_lib.py` | Permanent builder | **Keep** |
| `patches/01-notebooks.py` | Notebook fixes (one-time) | Delete after confidence |
| `patches/02-scripts.py` | AugAssign revert | Delete after confidence |
| `build/scripts/*.py` | Intermediate (gitignored) | Ephemeral |
| `notebooks/*.py` | Source of truth (literate) | **Keep** |
| `hecss/*.py` | Build output | Generated |
| `patches/` | Disposable migration scripts | Delete post-merge |

---

## Quick Reference Commands

```bash
# Full rebuild from notebooks
python scripts/build_lib.py

# Clean rebuild
rm -rf hecss build
python scripts/build_lib.py

# Verify parity with canonical
python /tmp/verify_final.py  # (kept in /tmp for ad-hoc)

# Update from new ipynb
marimo convert new_feature.ipynb -o notebooks/
python patches/01-notebooks.py  # if needed
python scripts/build_lib.py
```

---

## References
- Migration commits: `6f63f4e` → `f82201f` → `4c753db` → `6cc35f7` → `17fb020` → `6cc35f7` → `27429c0`
- Canonical tag: `3578cce` (v0.5.29 on test.pypi.org)
- marimo version at migration: 0.23.16 → 0.24.0