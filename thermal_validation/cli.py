"""Command line interface for simulation, validation, and frame inspection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import analyze_experiment
from .protocol_x import decode_sample
from .reporting import write_comparison, write_json, write_svg
from .simulator import SimulationConfig, simulate, write_csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _simulate(args: argparse.Namespace) -> int:
    config = SimulationConfig(
        channels=args.channels,
        duration_s=args.duration,
        seed=args.seed,
        degraded=args.degraded,
    )
    write_csv(args.output, simulate(config))
    print(f"wrote {args.output}")
    return 0


def _validate(args: argparse.Namespace) -> int:
    report = analyze_experiment(args.dataset, args.policy)
    if args.output:
        write_json(args.output, report)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 2


def _decode(args: argparse.Namespace) -> int:
    record = decode_sample(bytes.fromhex(args.hex_frame))
    print(
        json.dumps(
            {
                "sequence": record.sequence,
                "timestamp_ms": record.timestamp_ms,
                "channel": record.channel,
                "status": record.status.name,
                "usable": record.usable,
                "temperature_c": record.temperature_c,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _demo(args: argparse.Namespace) -> int:
    data_dir = args.root / "data" / "synthetic"
    results_dir = args.root / "results"
    policy = args.root / "config" / "validation_policy.json"
    baseline_path = data_dir / "baseline.csv"
    degraded_path = data_dir / "degraded.csv"
    write_csv(baseline_path, simulate(SimulationConfig()))
    write_csv(degraded_path, simulate(SimulationConfig(degraded=True)))
    baseline = analyze_experiment(baseline_path, policy)
    degraded = analyze_experiment(degraded_path, policy)
    write_json(results_dir / "baseline_report.json", baseline)
    write_json(results_dir / "degraded_report.json", degraded)
    write_comparison(results_dir / "comparison.md", [baseline, degraded])
    write_svg(baseline_path, results_dir / "baseline_profile.svg", title="Baseline multichannel thermal profile")
    write_svg(degraded_path, results_dir / "degraded_profile.svg", title="Degraded multichannel thermal profile")
    print(
        json.dumps(
            {
                "baseline": {"passed": baseline.passed, "issues": len(baseline.issues)},
                "degraded": {"passed": degraded.passed, "issues": len(degraded.issues)},
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if baseline.passed and not degraded.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate_parser = subparsers.add_parser("simulate", help="generate a synthetic experiment")
    simulate_parser.add_argument("--output", type=Path, required=True)
    simulate_parser.add_argument("--channels", type=int, default=10)
    simulate_parser.add_argument("--duration", type=int, default=300)
    simulate_parser.add_argument("--seed", type=int, default=20260719)
    simulate_parser.add_argument("--degraded", action="store_true")
    simulate_parser.set_defaults(handler=_simulate)

    validate_parser = subparsers.add_parser("validate", help="apply a versioned quality policy")
    validate_parser.add_argument("dataset", type=Path)
    validate_parser.add_argument("--policy", type=Path, default=PROJECT_ROOT / "config" / "validation_policy.json")
    validate_parser.add_argument("--output", type=Path)
    validate_parser.set_defaults(handler=_validate)

    decode_parser = subparsers.add_parser("decode-frame", help="decode one fictional Protocol-X frame")
    decode_parser.add_argument("hex_frame")
    decode_parser.set_defaults(handler=_decode)

    demo_parser = subparsers.add_parser("demo", help="regenerate all public datasets and reports")
    demo_parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    demo_parser.set_defaults(handler=_demo)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.handler(args))
