import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from thermal_validation.common_mode import run_common_mode, shift_rows


ROOT = Path(__file__).resolve().parents[1]


class CommonModeTests(unittest.TestCase):
    def test_shift_preserves_status_identity_and_input_rows(self):
        rows = [{"temperature_c": "", "reference_c": "60.00000", "status": "STALE", "timestamp_s": "245"},
                {"temperature_c": "60.02000", "reference_c": "60.00000", "status": "VALID", "timestamp_s": "246"}]
        before = copy.deepcopy(rows)
        shifted = shift_rows(rows, 1.0, 1.0)
        self.assertEqual(rows, before)
        self.assertEqual(shifted[0]["temperature_c"], "")
        self.assertEqual(shifted[1]["temperature_c"], "61.02000")
        for original, derived in zip(rows, shifted):
            self.assertEqual(original["status"], derived["status"])
            self.assertEqual(original["timestamp_s"], derived["timestamp_s"])

    def test_paired_shift_invariants_and_gate_decisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/synthetic").mkdir(parents=True)
            (root / "config").mkdir()
            shutil.copyfile(ROOT / "data/synthetic/baseline.csv", root / "data/synthetic/baseline.csv")
            shutil.copyfile(ROOT / "config/validation_policy.json", root / "config/validation_policy.json")
            records = run_common_mode(root)["cases"]
            baseline = records[0]["report"]
            self.assertEqual([record["report"]["passed"] for record in records], [True, False, False, True])
            self.assertEqual([record["average_mean_error_delta_c"] for record in records], [0.0, 1.0, -1.0, 0.0])
            for record in records:
                report = record["report"]
                self.assertEqual(report["p95_pairwise_spread_c"], baseline["p95_pairwise_spread_c"])
                for base, shifted in zip(baseline["channels"], report["channels"], strict=True):
                    self.assertEqual(base["valid_fraction"], shifted["valid_fraction"])
                    self.assertAlmostEqual(base["hold_drift_c_per_min"], shifted["hold_drift_c_per_min"], places=7)
                    self.assertAlmostEqual(base["hold_noise_rms_c"], shifted["hold_noise_rms_c"], places=7)
            output = root / "results/common_mode/comparison.json"
            first = output.read_bytes()
            run_common_mode(root)
            self.assertEqual(first, output.read_bytes())
