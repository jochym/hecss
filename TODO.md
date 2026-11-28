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

## On request (deferred)

- [ ] Read the Docs support: `.readthedocs.yaml`, `mkdocs.configuration`, a
      version selector and tag triggers in `deploy.yaml`.

## Infrastructure (open)

- [ ] The GitHub `asap` job passes only by skipping: the PyPI `asap3` there has
      no OpenKIM models. Decide whether to add a conda/OpenKIM setup step for
      real integration coverage; local `uv` runs do exercise these tests.
- [ ] Refresh pinned GitHub Actions versions (Node 20 deprecation notices) and
      add `uv.lock` or `cache-dependency-glob` to `setup-uv`.
- [ ] Move the API compatibility probe into the repository as a maintained
      script so parity with 0.5.29 (minus the intentional `hecss.mh` removal)
      stays checkable after future changes.

## Decisions resolved (full review, 0.6.0)

- [x] Keep the `v0.6.0` tag at `ec2d520`, before the review fixes. Retagging is
      a release action for a later decision.
- [x] Keep docs deployment on `devel` only; no auto-publishing from branches
      or tags.
- [x] Keep the current ASAP CI skip behaviour.
- [x] Python metadata aligned: `requires-python = ">=3.9"` and classifiers
      3.9-3.12 (CI runs 3.11).

## Completed in 0.6

- [x] KaTeX vendored locally in `docs/assets/katex/` with auto-render and a
      Material initializer in `docs/javascripts/katex.js`; no unpkg dependency.
- [x] `kpath` default mismatch resolved: `build_bnd_lst` used `crast` since
      2020 while `run_alamode` and `monitor_phonons` used `cryst`. Corrected
      to `cryst` and covered by a signature regression test.
- [x] Unused imports removed and import blocks sorted; `ruff check --select
      F401,F811,I .` is clean, with `archive/` excluded by configuration.
- [x] Pre-existing CLI issues from the Seaglass review fixed: `--nodfset` no
      longer writes DFSET data, `--no-pbar` disables the progress bar, and
      `-n -s` still saves the amplitude-correction history via `xsl_writer`.
- [x] Bare `maxburn` in the width-search error message replaced with
      `self.maxburn`, with a regression test.

## Merge and release

- [x] PR #7 opened: `back-to-std` -> `devel`, after reviewer sign-off.
- [x] Docs-only build verified in a pristine `uv` environment with `.[docs]`:
      strict build succeeds and the local KaTeX assets are present.
- [ ] After merge: verify the `devel` docs deployment builds with the
      vendored KaTeX, static highlighting and no missing local assets.
- [ ] Agree the release version/tag (`v0.6.0` still points at `ec2d520`) and
      publish manually only after explicit review.

## Standing decisions

- Do not publish any artifact without a detailed review and explicit approval.
- `archive/` stays in the repository; notebooks and legacy code are kept there.
- `example/` data is not shipped in the wheel.
- VASP tests run only in a dedicated environment; ASAP/OpenKIM tests use the
  `asap` marker.
