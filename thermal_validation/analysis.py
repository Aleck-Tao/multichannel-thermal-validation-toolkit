"""Status-aware validation of generic multichannel thermal experiments."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .models import ChannelMetrics, ValidationIssue, ValidationReport


REQUIRED_COLUMNS = {
    "timestamp_s",
    "run_id",
    "channel",
    "temperature_c",
    "reference_c",
    "status",
    "synthetic",
}


def load_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "version",
        "hold_start_s",
        "min_valid_fraction",
        "max_hold_mean_error_c",
        "max_hold_peak_abs_error_c",
        "max_hold_drift_c_per_min",
        "max_p95_pairwise_spread_c",
    }
    missing = required - policy.keys()
    if missing:
        raise ValueError(f"policy missing keys: {sorted(missing)}")
    return policy


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"dataset missing columns: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError("dataset contains no samples")
    if any(row["synthetic"].strip().lower() != "true" for row in rows):
        raise ValueError("public demonstration accepts only rows marked synthetic=true")
    return rows


def _channel_metrics(channel: str, rows: list[dict[str, str]], hold_start_s: float) -> ChannelMetrics:
    sample_count = len(rows)
    valid_rows = [
        row for row in rows if row["status"] == "VALID" and row["temperature_c"].strip()
    ]
    hold_rows = [row for row in valid_rows if float(row["timestamp_s"]) >= hold_start_s]
    if len(hold_rows) < 3:
        raise ValueError(f"{channel} has fewer than three valid hold samples")

    timestamps = np.array([float(row["timestamp_s"]) for row in hold_rows], dtype=float)
    temperatures = np.array([float(row["temperature_c"]) for row in hold_rows], dtype=float)
    references = np.array([float(row["reference_c"]) for row in hold_rows], dtype=float)
    errors = temperatures - references
    slope_c_per_second, intercept = np.polyfit(timestamps, errors, 1)
    residuals = errors - (slope_c_per_second * timestamps + intercept)

    return ChannelMetrics(
        channel=channel,
        samples=sample_count,
        valid_fraction=len(valid_rows) / sample_count,
        hold_mean_error_c=round(float(np.mean(errors)), 8),
        hold_peak_abs_error_c=round(float(np.max(np.abs(errors))), 8),
        hold_drift_c_per_min=round(float(slope_c_per_second * 60.0), 8),
        hold_noise_rms_c=round(float(np.sqrt(np.mean(residuals**2))), 8),
    )


def _spread(rows: list[dict[str, str]], hold_start_s: float) -> tuple[float, float]:
    grouped: dict[float, list[float]] = defaultdict(list)
    for row in rows:
        if (
            row["status"] == "VALID"
            and row["temperature_c"].strip()
            and float(row["timestamp_s"]) >= hold_start_s
        ):
            grouped[float(row["timestamp_s"])].append(float(row["temperature_c"]))
    spreads = np.array(
        [max(values) - min(values) for values in grouped.values() if len(values) >= 2],
        dtype=float,
    )
    if not spreads.size:
        raise ValueError("no timestamp has two valid hold samples")
    return round(float(np.percentile(spreads, 95)), 8), round(float(np.max(spreads)), 8)


def analyze_experiment(dataset_path: Path, policy_path: Path) -> ValidationReport:
    rows = _read_rows(dataset_path)
    policy = load_policy(policy_path)
    hold_start_s = float(policy["hold_start_s"])
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["channel"]].append(row)

    metrics = [
        _channel_metrics(channel, channel_rows, hold_start_s)
        for channel, channel_rows in sorted(grouped.items())
    ]
    p95_spread, max_spread = _spread(rows, hold_start_s)
    issues: list[ValidationIssue] = []

    def check(
        condition: bool,
        code: str,
        message: str,
        *,
        channel: str | None = None,
        observed: float | None = None,
        limit: float | None = None,
    ) -> None:
        if condition:
            issues.append(ValidationIssue(code, message, channel, observed, limit))

    for item in metrics:
        check(
            item.valid_fraction < float(policy["min_valid_fraction"]),
            "VALID_FRACTION_LOW",
            "valid sample fraction is below policy",
            channel=item.channel,
            observed=item.valid_fraction,
            limit=float(policy["min_valid_fraction"]),
        )
        check(
            abs(item.hold_mean_error_c) > float(policy["max_hold_mean_error_c"]),
            "MEAN_ERROR_HIGH",
            "absolute hold mean error exceeds policy",
            channel=item.channel,
            observed=abs(item.hold_mean_error_c),
            limit=float(policy["max_hold_mean_error_c"]),
        )
        check(
            item.hold_peak_abs_error_c > float(policy["max_hold_peak_abs_error_c"]),
            "PEAK_ERROR_HIGH",
            "hold peak absolute error exceeds policy",
            channel=item.channel,
            observed=item.hold_peak_abs_error_c,
            limit=float(policy["max_hold_peak_abs_error_c"]),
        )
        check(
            abs(item.hold_drift_c_per_min) > float(policy["max_hold_drift_c_per_min"]),
            "DRIFT_HIGH",
            "absolute hold drift exceeds policy",
            channel=item.channel,
            observed=abs(item.hold_drift_c_per_min),
            limit=float(policy["max_hold_drift_c_per_min"]),
        )

    check(
        p95_spread > float(policy["max_p95_pairwise_spread_c"]),
        "CHANNEL_SPREAD_HIGH",
        "95th percentile pairwise channel spread exceeds policy",
        observed=p95_spread,
        limit=float(policy["max_p95_pairwise_spread_c"]),
    )
    return ValidationReport(
        dataset=dataset_path.name,
        synthetic=True,
        policy_version=str(policy["version"]),
        passed=not issues,
        channels=metrics,
        issues=issues,
        p95_pairwise_spread_c=p95_spread,
        max_pairwise_spread_c=max_spread,
        hold_start_s=hold_start_s,
    )
