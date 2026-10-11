# Changelog

## 0.1.0 — Unreleased

- Calculation and visualisation of statistical process control (SPC) charts and funnel plots.
- Static SVG plots, notebook display, and plot saving.
- Column mappings, record sequences, phases, and grouped SPC limits.
- Mixed Python dates and ISO date strings for SPC keys.
- Multi-indicator sigma charts with `misc()` and `misc_default_settings()`.
- Shared `ccCore` bundle replaces `ccD3`; MISC uses the native Funnel renderer.
- `funnel()` accepts `indicators` and `misc_settings`; `misc()` delegates to it.
- `misc()` takes the `funnel()` keyword arguments explicitly; inputs, settings,
  and results carry precise types.
- MISC settings now use Funnel options aligned with input rows. Removed
  `groupings`, `bar_settings`, and the result's `target` attribute; limits use
  `three_sigma` instead of `outlier` and omit `grouping`.
