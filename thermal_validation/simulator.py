"""Deterministic synthetic experiments for regression testing and tutorials."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .protocol_x import Status


@dataclass(frozen=True)
class SimulationConfig:
    channels: int = 10
    duration_s: int = 300
    sample_period_s: float = 1.0
    seed: int = 20260719
    degraded: bool = False


def reference_temperature(timestamp_s: float) -> float:
    """A generic ramp-and-hold profile, unrelated to any proprietary test recipe."""
    if timestamp_s <= 30:
        return 24.0
    if timestamp_s <= 180:
        return 24.0 + (timestamp_s - 30.0) * (36.0 / 150.0)
    return 60.0


def simulate(config: SimulationConfig) -> list[dict[str, object]]:
    rng = np.random.default_rng(config.seed)
    timestamps = np.arange(0.0, config.duration_s + config.sample_period_s, config.sample_period_s)
    states = np.full(config.channels, 24.0, dtype=float)
    offsets = np.linspace(-0.12, 0.12, config.channels)
    time_constants = np.linspace(10.5, 14.0, config.channels)
    rows: list[dict[str, object]] = []

    for sample_index, timestamp in enumerate(timestamps):
        target = reference_temperature(float(timestamp))
        for channel_index in range(config.channels):
            states[channel_index] += (
                config.sample_period_s
                / time_constants[channel_index]
                * (target - states[channel_index])
            )
            noise = rng.normal(0.0, 0.025)
            temperature = states[channel_index] + offsets[channel_index] + noise
            status = Status.VALID

            if config.degraded and channel_index == 3:
                temperature += 1.05
                if sample_index > 205 and sample_index % 9 == 0:
                    status = Status.SENSOR_OPEN
            if config.degraded and channel_index == 7 and timestamp >= 195:
                temperature += 0.0065 * (timestamp - 195.0)
            if config.degraded and channel_index == 8 and 235 <= timestamp <= 245:
                status = Status.STALE

            rows.append(
                {
                    "timestamp_s": f"{timestamp:.3f}",
                    "run_id": "SYNTH-DEGRADED" if config.degraded else "SYNTH-BASELINE",
                    "channel": f"Channel-{channel_index + 1:02d}",
                    "temperature_c": "" if status != Status.VALID else f"{temperature:.5f}",
                    "reference_c": f"{target:.5f}",
                    "status": status.name,
                    "synthetic": "true",
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "timestamp_s",
        "run_id",
        "channel",
        "temperature_c",
        "reference_c",
        "status",
        "synthetic",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
