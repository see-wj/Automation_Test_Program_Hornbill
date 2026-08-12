import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analysis.bundle_data_analysis import analyze_bundle_runs
from configuration.test_configuration import ParameterSnapshot
from execution.run_context import RunContext


class BundleDataAnalysisTests(unittest.TestCase):
    @staticmethod
    def _measurement_values(
        error, readback_error, set_voltage=5.0, set_current=1.0
    ):
        return (
            set_voltage,
            set_current,
            set_voltage + error,
            set_voltage + readback_error,
            set_current,
            error,
            readback_error,
            error * 100.0,
            readback_error * 100.0,
            1.0,
            -1.0,
            1.0,
            -1.0,
            100.0,
            -100.0,
        )

    def _write_run(self, directory, run_id, channel, errors):
        parameters = ParameterSnapshot(savelocation=directory)
        configuration = {
            "DUT": "Hornbill",
            "unit": "VOLTAGE",
            "PSU_Channel": channel,
            "noofloop": len(errors),
        }
        context = RunContext.create(
            run_id,
            directory,
            "Hornbill",
            configuration,
            parameters,
            {"VoltageAccuracy": True},
        )
        context.open_realtime_csv(run_id)
        for loop_index, loop_errors in enumerate(errors, start=1):
            context.set_measurement_context(loop_index, channel)
            for error in loop_errors:
                context.write_realtime_row(
                    self._measurement_values(error, error / 2.0)
                )
        context.close()
        return context

    def test_summarizes_loops_channels_extremes_and_relationships(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self._write_run(
                directory, "channel-1", 1, ((-0.1, 0.1), (-0.2, 0.2))
            )
            self._write_run(
                directory, "channel-2", 2, ((0.3, 0.4), (0.5, 0.6))
            )

            result = analyze_bundle_runs(directory)
            channel_one = result.summary.loc[
                (result.summary["Channel"] == 1)
                & (result.summary["Metric"] == "Programming Error")
            ].iloc[0]

            self.assertFalse(result.empty)
            self.assertEqual(channel_one["Samples"], 4)
            self.assertEqual(channel_one["Loops"], 2)
            self.assertAlmostEqual(channel_one["Mean Error"], 0.0)
            self.assertEqual(channel_one["Minimum Error"], -0.2)
            self.assertEqual(channel_one["Maximum Error"], 0.2)
            self.assertEqual(channel_one["Set Voltage (V)"], 5.0)
            self.assertEqual(channel_one["Set Current (A)"], 1.0)
            self.assertAlmostEqual(
                channel_one["Maximum Limit Usage (%)"],
                20.0,
            )
            self.assertEqual(
                channel_one["Mean Equivalent to Limits"],
                "Yes",
            )
            self.assertEqual(
                channel_one["Bias Detected (95% CI)"],
                "No",
            )
            self.assertTrue(
                channel_one["Compliance Conclusion"].startswith("PASS")
            )
            self.assertEqual(len(result.loop_performance), 8)
            self.assertNotIn("Loops", result.loop_performance.columns)
            self.assertIn("Total Loops", result.stability_summary.columns)
            self.assertIn("Narrative", result.trend_summary.columns)
            self.assertIn("Status", result.trend_summary.columns)
            self.assertIn("Finding", result.trend_summary.columns)
            self.assertIn("Magnitude", result.trend_summary.columns)
            self.assertIn("Confidence", result.trend_summary.columns)
            self.assertIn(
                "Recommended Action",
                result.trend_summary.columns,
            )
            self.assertTrue(result.comparison_report)
            self.assertEqual(len(result.extremes), 12)
            self.assertIn(
                "Mean Difference (A-B)",
                result.channel_comparison.columns,
            )
            self.assertIn(
                "Difference Detected",
                result.channel_comparison.columns,
            )
            self.assertIn("Status", result.channel_comparison.columns)
            self.assertIn(
                "Recommended Action",
                result.channel_comparison.columns,
            )
            self.assertEqual(len(result.hypothesis_tests), 8)
            self.assertEqual(
                set(result.hypothesis_tests["Assessment"]),
                {
                    "Bias assessment",
                    "Mean equivalence (TOST via 90% CI)",
                },
            )
            methodology = "".join(result.methodology)
            self.assertIn("e_prog = V_ref - V_set", methodology)
            self.assertIn(
                "s = sqrt(sum((x_i - x_bar)^2) / (n - 1))",
                methodology,
            )
            self.assertIn("CI90_lower", methodology)
            self.assertIn("Practical difference threshold", methodology)
            self.assertIn("not a universal statistical significance", methodology)

            result.export_csv(first.storage.raw)
            self.assertTrue(
                (first.storage.raw / "analysis_summary.csv").is_file()
            )
            self.assertTrue(
                (
                    first.storage.raw
                    / "analysis_hypothesis_tests.csv"
                ).is_file()
            )
            self.assertTrue(
                (
                    first.storage.raw
                    / "analysis_stability_summary.csv"
                ).is_file()
            )
            self.assertTrue(
                (
                    first.storage.raw
                    / "analysis_trend_summary.csv"
                ).is_file()
            )
            self.assertTrue(
                (
                    first.storage.raw
                    / "analysis_trend_report.txt"
                ).is_file()
            )
            self.assertTrue(
                (
                    first.storage.raw
                    / "analysis_comparison_report.txt"
                ).is_file()
            )

    def test_detects_earliest_stable_loop_and_confirmation_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_run(
                directory,
                "settling-run",
                1,
                (
                    (0.30,),
                    (0.20,),
                    (0.100,),
                    (0.101,),
                    (0.099,),
                    (0.100,),
                    (0.101,),
                ),
            )

            result = analyze_bundle_runs(directory)
            stability = result.stability_summary.loc[
                result.stability_summary["Metric"] == "Programming Error"
            ].iloc[0]

            self.assertEqual(stability["Total Loops"], 7)
            self.assertEqual(stability["Stability Reached"], "Yes")
            self.assertEqual(stability["Stable From Loop"], 3)
            self.assertEqual(stability["Confirmed At Loop"], 4)
            self.assertEqual(
                stability["Required Confirmation Loops"],
                2,
            )
            self.assertLessEqual(stability["Span Limit Usage (%)"], 10.0)
            self.assertLessEqual(
                stability["Drift Limit Usage (%/loop)"],
                1.0,
            )
            trend = result.trend_summary.loc[
                result.trend_summary["Metric"] == "Programming Error"
            ].iloc[0]
            self.assertEqual(trend["Trend Direction"], "Decreasing")
            self.assertEqual(
                trend["Movement Relative to Zero"],
                "Moving toward zero",
            )
            self.assertIn("signed error trend is decreasing", trend["Narrative"])
            self.assertIn(
                "error magnitude is moving toward zero",
                trend["Narrative"],
            )

    def test_reports_when_loop_series_does_not_reach_stability(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_run(
                directory,
                "drifting-run",
                1,
                (
                    (0.00,),
                    (0.05,),
                    (0.10,),
                    (0.15,),
                    (0.20,),
                    (0.25,),
                    (0.30,),
                ),
            )

            result = analyze_bundle_runs(directory)
            stability = result.stability_summary.loc[
                result.stability_summary["Metric"] == "Programming Error"
            ].iloc[0]

            self.assertEqual(stability["Stability Reached"], "No")
            self.assertTrue(pd.isna(stability["Stable From Loop"]))
            self.assertIn("Not stable", stability["Conclusion"])
            trend = result.trend_summary.loc[
                result.trend_summary["Metric"] == "Programming Error"
            ].iloc[0]
            self.assertEqual(trend["Trend Direction"], "Increasing")
            self.assertEqual(
                trend["Movement Relative to Zero"],
                "Moving away from zero",
            )
            self.assertTrue(
                any(
                    "Overall DUT stability was not reached" in insight
                    for insight in result.insights
                )
            )

    def test_trend_analysis_detects_jumps_and_robust_outlier_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_run(
                directory,
                "jump-run",
                1,
                (
                    (0.001,),
                    (-0.001,),
                    (0.002,),
                    (0.000,),
                    (0.300,),
                    (0.001,),
                ),
            )

            result = analyze_bundle_runs(directory)
            trend = result.trend_summary.loc[
                result.trend_summary["Metric"] == "Programming Error"
            ].iloc[0]

            self.assertGreaterEqual(trend["Sudden Jump Count"], 2)
            self.assertGreaterEqual(trend["Robust Outlier Count"], 1)
            self.assertIn("5", trend["Robust Outlier Loops"])
            self.assertIn("sudden jump", trend["Narrative"])

    def test_does_not_mix_different_voltage_or_current_conditions(self):
        with tempfile.TemporaryDirectory() as directory:
            parameters = ParameterSnapshot(savelocation=directory)
            configuration = {
                "DUT": "Hornbill",
                "unit": "VOLTAGE",
                "PSU_Channel": 1,
                "noofloop": 2,
            }
            context = RunContext.create(
                "conditions",
                directory,
                "Hornbill",
                configuration,
                parameters,
                {"VoltageAccuracy": True},
            )
            context.open_realtime_csv("conditions")
            for loop_index in (1, 2):
                context.set_measurement_context(loop_index, 1)
                context.write_realtime_row(
                    self._measurement_values(0.1, 0.05, 5.0, 1.0)
                )
                context.write_realtime_row(
                    self._measurement_values(0.4, 0.2, 10.0, 2.0)
                )
            context.close()

            result = analyze_bundle_runs(directory)
            programming = result.summary.loc[
                result.summary["Metric"] == "Programming Error"
            ]

        self.assertEqual(len(programming), 2)
        low_condition = programming.loc[
            (programming["Set Voltage (V)"] == 5.0)
            & (programming["Set Current (A)"] == 1.0)
        ].iloc[0]
        high_condition = programming.loc[
            (programming["Set Voltage (V)"] == 10.0)
            & (programming["Set Current (A)"] == 2.0)
        ].iloc[0]
        self.assertAlmostEqual(low_condition["Mean Error"], 0.1)
        self.assertAlmostEqual(high_condition["Mean Error"], 0.4)

    def test_failed_point_overrides_statistical_mean_conclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_run(
                directory,
                "failed-condition",
                1,
                ((0.0, 1.2), (0.0, 0.0)),
            )

            result = analyze_bundle_runs(directory)
            programming = result.summary.loc[
                result.summary["Metric"] == "Programming Error"
            ].iloc[0]

        self.assertEqual(programming["Pass Rate (%)"], 75.0)
        self.assertAlmostEqual(
            programming["Maximum Limit Usage (%)"],
            120.0,
        )
        self.assertTrue(
            programming["Compliance Conclusion"].startswith("FAIL")
        )

    def test_detects_consistent_matched_channel_offset(self):
        with tempfile.TemporaryDirectory() as directory:
            self._write_run(
                directory,
                "matched-channel-1",
                1,
                ((0.0,), (0.1,), (0.0,), (0.1,), (0.0,)),
            )
            self._write_run(
                directory,
                "matched-channel-2",
                2,
                ((0.5,), (0.6,), (0.5,), (0.6,), (0.5,)),
            )

            result = analyze_bundle_runs(directory)
            programming = result.channel_comparison.loc[
                result.channel_comparison["Metric"]
                == "Programming Error"
            ].iloc[0]
            stricter_result = analyze_bundle_runs(
                directory,
                practical_difference_threshold_percent=60.0,
            )
            stricter_programming = stricter_result.channel_comparison.loc[
                stricter_result.channel_comparison["Metric"]
                == "Programming Error"
            ].iloc[0]

        self.assertEqual(programming["Matched Loops"], 5)
        self.assertAlmostEqual(
            programming["Mean Difference (A-B)"],
            -0.5,
        )
        self.assertEqual(programming["Difference Detected"], "Yes")
        self.assertEqual(programming["Evidence Strength"], "Supported")
        self.assertEqual(programming["Practically Meaningful"], "Yes")
        self.assertIn(
            "Channel 1 minus Channel 2",
            programming["Comparison Narrative"],
        )
        self.assertIn(
            "Highest-priority comparison findings:",
            result.comparison_report,
        )
        self.assertAlmostEqual(
            programming["Difference Limit Usage (%)"],
            50.0,
        )
        self.assertIn(
            "practically meaningful channel offset",
            programming["Conclusion"],
        )
        self.assertEqual(
            stricter_result.practical_difference_threshold_percent,
            60.0,
        )
        self.assertEqual(
            stricter_programming["Difference Detected"],
            "Yes",
        )
        self.assertEqual(
            stricter_programming["Practically Meaningful"],
            "No",
        )
        self.assertIn(
            "below the practical threshold",
            stricter_programming["Conclusion"],
        )

    def test_combines_separate_result_roots_without_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            first_root = Path(directory) / "first-root"
            second_root = Path(directory) / "second-root"
            self._write_run(
                first_root,
                "first-channel",
                1,
                ((0.1,), (0.2,), (0.15,)),
            )
            self._write_run(
                second_root,
                "second-channel",
                2,
                ((0.2,), (0.3,), (0.25,)),
            )

            result = analyze_bundle_runs([first_root, second_root])

        self.assertEqual(set(result.observations["Channel"]), {1, 2})
        self.assertEqual(len(result.channel_comparison), 2)
        self.assertEqual(
            set(result.channel_comparison["Evidence Strength"]),
            {"Preliminary"},
        )

    def test_compares_separate_runs_with_the_same_channel_number(self):
        with tempfile.TemporaryDirectory() as directory:
            first_root = Path(directory) / "run-a-root"
            second_root = Path(directory) / "run-b-root"
            self._write_run(
                first_root,
                "run-a",
                1,
                ((0.1,),),
            )
            self._write_run(
                second_root,
                "run-b",
                1,
                ((0.2,),),
            )

            result = analyze_bundle_runs([first_root, second_root])

        self.assertEqual(len(result.channel_comparison), 2)
        self.assertEqual(
            set(result.channel_comparison["Comparison Basis"]),
            {"Run"},
        )
        comparison_subjects = (
            set(result.channel_comparison["Channel A"])
            | set(result.channel_comparison["Channel B"])
        )
        self.assertEqual(comparison_subjects, set(result.observations["Run"]))
        self.assertEqual(set(result.channel_comparison["DUT Channel A"]), {"1"})
        self.assertEqual(set(result.channel_comparison["DUT Channel B"]), {"1"})

    def test_infers_loop_and_channel_for_legacy_realtime_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "legacy-run" / "raw"
            raw.mkdir(parents=True)
            (raw / "parameters.json").write_text(
                json.dumps(
                    {
                        "DUT": "Hornbill",
                        "unit": "VOLTAGE",
                        "PSU_Channel": 3,
                        "noofloop": 2,
                    }
                ),
                encoding="utf-8",
            )
            rows = [self._measurement_values(error, error) for error in (0.1, 0.2, 0.3, 0.4)]
            columns = (
                "Set_Voltage",
                "Set_Current",
                "Programming_Voltage",
                "Readback_Voltage",
                "Readback_Current",
                "Programming_Voltage_Error",
                "Readback_Voltage_Error",
                "Programming_Voltage_Percentage_Error",
                "Readback_Voltage_Percentage_Error",
                "Programming_Upper_Limit_Boundary",
                "Programming_Lower_Limit_Boundary",
                "Readback_Upper_Limit_Boundary",
                "Readback_lower_Limit_Boundary",
                "Percentage_Upper_Limit_Boundary",
                "Percentage_Lower_Limit_Boundary",
            )
            frame = pd.DataFrame(rows, columns=columns)
            frame.insert(0, "Index", range(1, len(frame) + 1))
            frame.to_csv(raw / "realtime_voltage_data_legacy.csv", index=False)

            result = analyze_bundle_runs(directory)

        self.assertEqual(set(result.observations["Loop"]), {1, 2})
        self.assertEqual(set(result.observations["Channel"]), {3})

    def test_loads_excel_report_when_raw_data_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = (
                Path(directory)
                / "Channel_2"
                / "Single_3_loop"
                / "report-only-run"
                / "reports"
            )
            reports.mkdir(parents=True)
            rows = []
            for error in (0.1, 0.2, 0.15, 0.25, 0.2, 0.3):
                rows.append(
                    (
                        5.0,
                        1.0,
                        5.0 + error / 2.0,
                        1.0,
                        5.0 + error,
                        error,
                        error * 100.0,
                        error / 2.0,
                        error * 50.0,
                        5.0,
                        0.0,
                        1.0,
                        -1.0,
                        "PASS",
                        1.0,
                        -1.0,
                        "PASS",
                    )
                )
            frame = pd.DataFrame(
                rows,
                columns=[f"Report Column {index}" for index in range(17)],
            )
            report_path = reports / "VOLTAGE_report_only.xlsx"
            with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
                frame.to_excel(
                    writer,
                    sheet_name="Data",
                    index=False,
                    startrow=7,
                    startcol=3,
                )

            result = analyze_bundle_runs(directory)

        self.assertFalse(result.empty)
        self.assertEqual(len(result.observations), 6)
        self.assertEqual(set(result.observations["Loop"]), {1, 2, 3})
        self.assertEqual(set(result.observations["Channel"]), {2})
        self.assertEqual(
            set(result.observations["Source"]),
            {"Excel report fallback"},
        )


if __name__ == "__main__":
    unittest.main()
