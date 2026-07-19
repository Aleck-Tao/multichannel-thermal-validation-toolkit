import csv
import tempfile
import unittest
from pathlib import Path

from thermal_validation.analysis import analyze_experiment
from thermal_validation.simulator import SimulationConfig, simulate, write_csv


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "validation_policy.json"


class SimulationAndAnalysisTests(unittest.TestCase):
    def test_simulation_is_deterministic(self) -> None:
        config = SimulationConfig(channels=4, duration_s=20, seed=7)
        self.assertEqual(simulate(config), simulate(config))

    def test_baseline_passes_and_degraded_run_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_path = root / "baseline.csv"
            degraded_path = root / "degraded.csv"
            write_csv(baseline_path, simulate(SimulationConfig()))
            write_csv(degraded_path, simulate(SimulationConfig(degraded=True)))

            baseline = analyze_experiment(baseline_path, POLICY)
            degraded = analyze_experiment(degraded_path, POLICY)

        self.assertTrue(baseline.passed)
        self.assertFalse(baseline.issues)
        self.assertFalse(degraded.passed)
        self.assertGreaterEqual(
            {issue.code for issue in degraded.issues},
            {"MEAN_ERROR_HIGH", "PEAK_ERROR_HIGH", "DRIFT_HIGH", "CHANNEL_SPREAD_HIGH"},
        )

    def test_public_pipeline_rejects_unmarked_real_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not_public.csv"
            rows = simulate(SimulationConfig(channels=2, duration_s=5))
            rows[0]["synthetic"] = "false"
            write_csv(path, rows)
            with self.assertRaisesRegex(ValueError, "only rows marked synthetic"):
                analyze_experiment(path, POLICY)

    def test_invalid_samples_are_excluded_from_numeric_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "degraded.csv"
            write_csv(path, simulate(SimulationConfig(degraded=True)))
            report = analyze_experiment(path, POLICY)
        channel = next(item for item in report.channels if item.channel == "Channel-04")
        self.assertLess(channel.valid_fraction, 1.0)
        self.assertTrue(
            all(value == value for value in channel.to_dict().values() if isinstance(value, float))
        )

    def test_generated_csv_has_stable_public_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment.csv"
            write_csv(path, simulate(SimulationConfig(channels=3, duration_s=3)))
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
        self.assertEqual(
            reader.fieldnames,
            [
                "timestamp_s",
                "run_id",
                "channel",
                "temperature_c",
                "reference_c",
                "status",
                "synthetic",
            ],
        )
        self.assertEqual(len(rows), 12)
        self.assertEqual({row["synthetic"] for row in rows}, {"true"})


if __name__ == "__main__":
    unittest.main()
