"""Typed outputs shared by the analysis and reporting layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChannelMetrics:
    channel: str
    samples: int
    valid_fraction: float
    hold_mean_error_c: float
    hold_peak_abs_error_c: float
    hold_drift_c_per_min: float
    hold_noise_rms_c: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    channel: str | None = None
    observed: float | None = None
    limit: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    dataset: str
    synthetic: bool
    policy_version: str
    passed: bool
    channels: list[ChannelMetrics]
    issues: list[ValidationIssue] = field(default_factory=list)
    p95_pairwise_spread_c: float = 0.0
    max_pairwise_spread_c: float = 0.0
    hold_start_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "synthetic": self.synthetic,
            "policy_version": self.policy_version,
            "passed": self.passed,
            "hold_start_s": self.hold_start_s,
            "p95_pairwise_spread_c": self.p95_pairwise_spread_c,
            "max_pairwise_spread_c": self.max_pairwise_spread_c,
            "channels": [channel.to_dict() for channel in self.channels],
            "issues": [issue.to_dict() for issue in self.issues],
        }
