# Project backlog

This file is the single maintained todo list for the project. Update it as
work is done. Items marked "on request" are deliberately deferred.

## 0.7 — API cleanup

- [ ] Merge the two `plot_virial_stat` implementations. `hecss.monitor` plots
      the dimensional virial/T ratio and returns nothing; `hecss.xscale`
      normalises by the sample mean, plots `1/sqrt(virial)` and returns an
      amplitude correction matrix. Consolidate both into
      `hecss.monitor.plot_virial_stat` with a switch selecting the normalised
      variant, leave a `DeprecationWarning` alias in `hecss.xscale` for one
      release, then remove it and update `docs/api/{monitor,xscale}.md`.

## On request

- [ ] Read the Docs support: `.readthedocs.yaml`, `mkdocs.configuration`, a
      version selector and tag triggers in `deploy.yaml`. Deferred in 0.6.
- [ ] Vendor KaTeX instead of loading it from unpkg, so the docs work offline.

## Infrastructure

- [ ] Refresh pinned GitHub Actions versions (Node 20 deprecation notices) and
      add `uv.lock` or `cache-dependency-glob` to `setup-uv`.
- [ ] Move the API compatibility probe into the repository as a maintained
      script so parity with 0.5.29 (minus the intentional `hecss.mh` removal)
      stays checkable after future changes.

## Standing decisions

- Do not publish any artifact without a detailed review and explicit approval.
- `archive/` stays in the repository; notebooks and legacy code are kept there.
- `example/` data is not shipped in the wheel.
- VASP tests run only in a dedicated environment; ASAP/OpenKIM tests use the
  `asap` marker.
