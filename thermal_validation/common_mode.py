"""Paired common-mode counterfactuals from one unchanged baseline dataset."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from .analysis import analyze_experiment
from .simulator import write_csv


CASES = {"baseline": (0.0, 0.0), "channels_plus_1": (1.0, 0.0),
         "reference_plus_1": (0.0, 1.0), "both_plus_1": (1.0, 1.0)}


def shift_rows(rows: list[dict[str, str]], channel_shift: float, reference_shift: float) -> list[dict[str, str]]:
    shifted = []
    for original in rows:
        row = dict(original)
        if row["temperature_c"]:
            row["temperature_c"] = f"{float(row['temperature_c']) + channel_shift:.5f}"
        row["reference_c"] = f"{float(row['reference_c']) + reference_shift:.5f}"
        shifted.append(row)
    return shifted


def run_common_mode(root: Path) -> dict:
    baseline_path = root / "data" / "synthetic" / "baseline.csv"
    policy_path = root / "config" / "validation_policy.json"
    with baseline_path.open(encoding="utf-8", newline="") as handle:
        baseline_rows = list(csv.DictReader(handle))
    output = root / "results" / "common_mode"
    output.mkdir(parents=True, exist_ok=True)
    records = []
    baseline_means = None
    for name, (channel_shift, reference_shift) in CASES.items():
        dataset = baseline_path if name == "baseline" else root / "data" / "synthetic" / "common_mode" / f"{name}.csv"
        if name != "baseline":
            write_csv(dataset, shift_rows(baseline_rows, channel_shift, reference_shift))
        report = analyze_experiment(dataset, policy_path)
        means = [channel.hold_mean_error_c for channel in report.channels]
        if baseline_means is None:
            baseline_means = means
        record = {
            "case": name,
            "channel_shift_c": channel_shift,
            "reference_shift_c": reference_shift,
            "dataset": dataset.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
            "average_channel_mean_error_c": round(sum(means) / len(means), 8),
            "average_mean_error_delta_c": round(sum(a - b for a, b in zip(means, baseline_means, strict=True)) / len(means), 8),
            "report": report.to_dict(),
        }
        records.append(record)
    summary = {
        "method": "Paired constant shifts of the same baseline rows; no resampled noise",
        "baseline_sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "cases": records,
    }
    (output / "comparison.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Common-mode and reference counterfactuals", "",
             "All four cases reuse the same ten-channel baseline rows. Constant offsets are added after generation; noise, timestamps and statuses remain identical.", "",
             "| Case | p95 spread (C) | Average channel error (C) | Error change (C) | Decision | Issues |",
             "|---|---:|---:|---:|---|---:|"]
    for record in records:
        report = record["report"]
        lines.append(f"| {record['case']} | {report['p95_pairwise_spread_c']:.4f} | {record['average_channel_mean_error_c']:+.4f} | {record['average_mean_error_delta_c']:+.4f} | {'PASS' if report['passed'] else 'FAIL'} | {len(report['issues'])} |")
    lines.extend(["", "A +1 C shift of all channels leaves their mutual spread unchanged but increases every reference error by 1 C. Shifting only the reference reverses that error. Shifting both cancels in both diagnostics; drift and detrended noise also remain unchanged.", "",
                  "The PASS for `both_plus_1` is an observability limit, not evidence of absolute accuracy. These relative measurements cannot identify a shared calibration bias without an independent reference. An error sign alone also cannot determine whether the reference or channels are wrong.", "",
                  "Reproduce with `python -m thermal_validation common-mode --root .` after `demo`. Full channel metrics, gate decisions, input hashes and shift parameters are in [comparison.json](comparison.json)."])
    (output / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return summary
