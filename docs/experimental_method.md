# Synthetic experiment method

## Profile

The default experiment contains ten independent channels and a 301-second shared reference:

- 0–30 s: 24 °C baseline;
- 30–180 s: linear ramp to 60 °C;
- 180–300 s: 60 °C hold;
- 240–300 s: validation window.

Each channel is a first-order response with a small deterministic offset, a channel-specific time constant, and seeded Gaussian observation noise. This is a regression fixture, not a physical thermal model.

## Controlled degraded run

The degraded scenario adds three public fault classes:

- Channel-04: fixed offset plus periodic sensor-open status;
- Channel-08: additional hold-period drift;
- Channel-09: a short stale-data interval.

The values are chosen to exercise the policy and do not reproduce product tolerances, customer data, or calibration coefficients.

## Metrics

For valid observations in the hold window, the pipeline computes:

- mean and peak absolute error from the shared reference;
- linear error drift in °C/min;
- RMS residual noise after removing the fitted drift;
- per-channel valid fraction across the complete run;
- the 95th percentile and maximum pairwise spread across valid channels.

Every failed gate is emitted as a stable issue code with channel, observed value, and limit where applicable.
