# Common-mode and reference counterfactuals

All four cases reuse the same ten-channel baseline rows. Constant offsets are added after generation; noise, timestamps and statuses remain identical.

| Case | p95 spread (C) | Average channel error (C) | Error change (C) | Decision | Issues |
|---|---:|---:|---:|---|---:|
| baseline | 0.3026 | -0.0042 | +0.0000 | PASS | 0 |
| channels_plus_1 | 0.3026 | +0.9958 | +1.0000 | FAIL | 20 |
| reference_plus_1 | 0.3026 | -1.0042 | -1.0000 | FAIL | 20 |
| both_plus_1 | 0.3026 | -0.0042 | +0.0000 | PASS | 0 |

A +1 C shift of all channels leaves their mutual spread unchanged but increases every reference error by 1 C. Shifting only the reference reverses that error. Shifting both cancels in both diagnostics; drift and detrended noise also remain unchanged.

The PASS for `both_plus_1` is an observability limit, not evidence of absolute accuracy. These relative measurements cannot identify a shared calibration bias without an independent reference. An error sign alone also cannot determine whether the reference or channels are wrong.

Reproduce with `python -m thermal_validation common-mode --root .` after `demo`. Full channel metrics, gate decisions, input hashes and shift parameters are in [comparison.json](comparison.json).
