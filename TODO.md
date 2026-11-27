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
- [x] KaTeX vendored locally in `docs/assets/katex/`, with the auto-render
      extension and a Material initializer in `docs/javascripts/katex.js`;
      the docs no longer depend on unpkg for equation rendering.

## Decisions needed (full review, 0.6.0)

- [ ] `v0.6.0` points at `ec2d520`, before the review-driven fixes. Decide
      whether to move/recreate the tag at the current HEAD; this needs a
      force-push and is a release action requiring approval.
- [ ] `deploy.yaml` triggers only on `devel`. Decide whether to add
      `back-to-std` or tag triggers; that would auto-publish docs and needs
      approval.
- [x] Python metadata aligned: `requires-python = ">=3.9"` and classifiers
      updated to 3.9-3.12 (CI runs 3.11). User decision from full review.
- [x] Release decisions recorded: keep `v0.6.0` tag where it is, keep docs
      deploy on `devel` only, keep the current ASAP CI skip behaviour.

## Infrastructure

- [ ] The GitHub `asap` job passes only by skipping: the PyPI `asap3` there has
      no OpenKIM models. Decide whether to add a conda/OpenKIM setup step for
      real integration coverage; local `uv` runs do exercise these tests.
- [ ] Clean unused imports in `hecss/xscale.py` (non-blocking lint noise).
- [ ] Refresh pinned GitHub Actions versions (Node 20 deprecation notices) and
      add `uv.lock` or `cache-dependency-glob` to `setup-uv`.
- [ ] Move the API compatibility probe into the repository as a maintained
      script so parity with 0.5.29 (minus the intentional `hecss.mh` removal)
      stays checkable after future changes.
- [x] `kpath` default mismatch resolved: `build_bnd_lst` used `crast` since
      2020 while `run_alamode` and `monitor_phonons` used `cryst`. Corrected
      to `cryst` and covered by a signature regression test.

## Standing decisions

- Do not publish any artifact without a detailed review and explicit approval.
- `archive/` stays in the repository; notebooks and legacy code are kept there.
- `example/` data is not shipped in the wheel.
- VASP tests run only in a dedicated environment; ASAP/OpenKIM tests use the
  `asap` marker.
