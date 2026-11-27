# Archived nbdev project tree

This directory preserves the pre-migration project layout so that the old
sources remain at hand without cluttering the modern project tree. Nothing
here is used to build, test or document the package any more.

- `nbdev/notebooks/` — the original notebooks: library sources, tutorials and analysis notebooks.
- `nbdev/config/` — nbdev, Quarto, packaging and legacy CI configuration.
- `nbdev/ci/` — the GitLab CI configuration and the custom Quarto deploy action.

The library source now lives directly in `hecss/`, tests in `tests/`, and
documentation sources in `docs/`. The notebook assertions were migrated to
pytest, including the `asap` and `vasp` marker groups.
