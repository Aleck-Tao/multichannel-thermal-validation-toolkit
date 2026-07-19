# Architecture and assurance argument

## Layered design

The toolkit separates transport validity from measurement validity and experiment validity.

1. **Frame layer** — validates the start byte, version, message type, declared payload length, and CRC.
2. **Semantic layer** — maps status bits to a typed record and withholds the numeric value when any fault flag is present.
3. **Canonical-data layer** — records time, run, channel, reference, status, and the explicit `synthetic=true` provenance marker.
4. **Analysis layer** — computes only from valid hold-window observations.
5. **Policy layer** — compares metrics with versioned limits and returns coded issues.
6. **Evidence layer** — emits deterministic reports that CI regenerates and compares with the committed artifacts.

## Failure containment

| Failure | Containment behavior |
|---|---|
| Corrupted packet | CRC rejection; no record emitted |
| Truncated or inconsistent packet | Length rejection; no partial decode |
| Unsupported protocol revision | Explicit version rejection |
| Sensor-open/out-of-range/stale flag | Channel record retained for traceability; value withheld from statistics |
| Excess dropout | `VALID_FRACTION_LOW` issue |
| Channel bias or transient | Mean/peak error issue |
| Hold-period drift | `DRIFT_HIGH` issue |
| Loss of channel agreement | Experiment-level spread issue |

## Trust boundary

The public pipeline starts at a byte frame or the canonical synthetic CSV schema. It does not implement firmware, sensor excitation, analog front ends, closed-loop power control, factory information-system integration, or a proprietary calibration method.
