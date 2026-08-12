import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QSizePolicy

from ui.analysis_visualization_widget import AnalysisVisualizationWidget
from ui.bundle_data_analysis_widget import BundleDataAnalysisWidget


class AnalysisVisualizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _result():
        summary = pd.DataFrame(
            [
                {
                    "DUT": "Hornbill",
                    "Test": "VOLTAGE",
                    "Channel": 1,
                    "Set Voltage (V)": 5.0,
                    "Set Current (A)": 1.0,
                    "Metric": "Programming Error",
                    "Samples": 4,
                    "Pass Rate (%)": 100.0,
                    "Mean Error": 0.1,
                    "Maximum Limit Usage (%)": 20.0,
                    "Maximum Absolute Error": 0.2,
                    "Compliance Conclusion": (
                        "PASS - compliant and statistically stable"
                    ),
                    "95% CI Lower": 0.0,
                    "95% CI Upper": 0.2,
                    "Lower Limit": -1.0,
                    "Upper Limit": 1.0,
                },
                {
                    "DUT": "Hornbill",
                    "Test": "VOLTAGE",
                    "Channel": 2,
                    "Set Voltage (V)": 10.0,
                    "Set Current (A)": 2.0,
                    "Metric": "Programming Error",
                    "Samples": 2,
                    "Pass Rate (%)": 50.0,
                    "Mean Error": 0.8,
                    "Maximum Limit Usage (%)": 120.0,
                    "Maximum Absolute Error": 1.2,
                    "Compliance Conclusion": (
                        "FAIL - observed point exceeded limit"
                    ),
                    "95% CI Lower": 0.3,
                    "95% CI Upper": 1.3,
                    "Lower Limit": -1.0,
                    "Upper Limit": 1.0,
                },
            ]
        )
        loop_performance = pd.DataFrame(
            [
                {
                    "DUT": "Hornbill",
                    "Test": "VOLTAGE",
                    "Channel": 1,
                    "Set Voltage (V)": 5.0,
                    "Set Current (A)": 1.0,
                    "Metric": "Programming Error",
                    "Loop": 1,
                    "Mean Error": 0.05,
                },
                {
                    "DUT": "Hornbill",
                    "Test": "VOLTAGE",
                    "Channel": 1,
                    "Set Voltage (V)": 5.0,
                    "Set Current (A)": 1.0,
                    "Metric": "Programming Error",
                    "Loop": 2,
                    "Mean Error": 0.15,
                },
                {
                    "DUT": "Hornbill",
                    "Test": "VOLTAGE",
                    "Channel": 2,
                    "Set Voltage (V)": 5.0,
                    "Set Current (A)": 1.0,
                    "Metric": "Programming Error",
                    "Loop": 1,
                    "Mean Error": 0.25,
                },
                {
                    "DUT": "Hornbill",
                    "Test": "VOLTAGE",
                    "Channel": 2,
                    "Set Voltage (V)": 5.0,
                    "Set Current (A)": 1.0,
                    "Metric": "Programming Error",
                    "Loop": 2,
                    "Mean Error": 0.35,
                },
                {
                    "DUT": "Hornbill",
                    "Test": "VOLTAGE",
                    "Channel": 2,
                    "Set Voltage (V)": 10.0,
                    "Set Current (A)": 2.0,
                    "Metric": "Programming Error",
                    "Loop": 1,
                    "Mean Error": 0.8,
                },
            ]
        )
        return SimpleNamespace(
            summary=summary,
            loop_performance=loop_performance,
            channel_comparison=pd.DataFrame(
                [
                    {
                        "DUT": "Hornbill",
                        "Test": "VOLTAGE",
                        "Metric": "Programming Error",
                        "Channel A": 1,
                        "Channel B": 2,
                        "Set Voltage (V)": 5.0,
                        "Set Current (A)": 1.0,
                        "Mean Difference (A-B)": -0.2,
                        "Difference Limit Usage (%)": 20.0,
                        "Practical Threshold (%)": 10.0,
                        "Difference Detected": "Yes",
                        "Evidence Strength": "Preliminary",
                        "Conclusion": (
                            "Preliminary statistically and practically "
                            "meaningful channel offset"
                        ),
                    }
                ]
            ),
        )

    def test_dashboard_populates_cards_and_three_plots(self):
        widget = AnalysisVisualizationWidget()
        widget.set_result(self._result())
        self.app.processEvents()

        self.assertEqual(widget.card_values["records"].text(), "6")
        self.assertEqual(widget.card_values["pass_rate"].text(), "83.33%")
        self.assertEqual(widget.card_values["limit_usage"].text(), "120.00%")
        self.assertEqual(widget.card_values["conclusion"].text(), "1 P / 0 M / 1 F")
        self.assertTrue(widget.heatmap.listDataItems())
        self.assertTrue(widget.confidence_plot.listDataItems())
        self.assertTrue(widget.channel_difference_plot.listDataItems())
        self.assertTrue(widget.loop_plot.listDataItems())
        self.assertTrue(widget.comparison_trend_plot.listDataItems())
        self.assertIn(
            "2 loops detected",
            widget.loop_plot.getPlotItem().titleLabel.text,
        )
        plotted_loop_sequences = [
            item.getData()[0].tolist()
            for item in widget.loop_plot.listDataItems()
        ]
        self.assertIn([1.0, 2.0], plotted_loop_sequences)
        widget.close()

    def test_dashboard_uses_full_size_graph_tabs(self):
        widget = AnalysisVisualizationWidget()

        self.assertEqual(
            [
                widget.plot_tabs.tabText(index)
                for index in range(widget.plot_tabs.count())
            ],
            [
                "Compliance Heatmap",
                "Confidence Intervals",
                "Channel Comparison",
                "Individual Trend",
                "Comparison Trend",
            ],
        )
        self.assertEqual(
            widget.plot_tabs.sizePolicy().verticalPolicy(),
            QSizePolicy.Expanding,
        )
        self.assertGreaterEqual(widget.heatmap.minimumHeight(), 300)
        widget.close()

    def test_reset_filters_returns_dashboard_to_all_data(self):
        widget = AnalysisVisualizationWidget()
        widget.set_result(self._result())
        channel_combo = widget.filter_combos["Channel"]
        channel_combo.setCurrentIndex(channel_combo.findData(1))

        widget.reset_filters()
        self.app.processEvents()

        self.assertTrue(
            all(
                combo.currentIndex() == 0
                for combo in widget.filter_combos.values()
            )
        )
        self.assertEqual(widget.card_values["records"].text(), "6")
        widget.close()

    def test_channel_filter_updates_dashboard(self):
        widget = AnalysisVisualizationWidget()
        widget.set_result(self._result())
        channel_combo = widget.filter_combos["Channel"]
        channel_combo.setCurrentIndex(channel_combo.findData(1))
        self.app.processEvents()

        self.assertEqual(widget.card_values["records"].text(), "4")
        self.assertEqual(widget.card_values["pass_rate"].text(), "100.00%")
        self.assertEqual(widget.card_values["conclusion"].text(), "1 P / 0 M / 0 F")
        widget.close()

    def test_data_analysis_tab_exposes_visual_dashboard_first(self):
        widget = BundleDataAnalysisWidget()

        self.assertEqual(widget.analysis_workspace.orientation(), Qt.Horizontal)
        self.assertIs(
            widget.analysis_workspace.widget(0),
            widget.analysis_setup_group,
        )
        self.assertIs(
            widget.analysis_workspace.widget(1),
            widget.analysis_output_group,
        )
        self.assertEqual(
            widget.analysis_tabs.tabText(0),
            "Visual Dashboard",
        )
        self.assertIs(
            widget.analysis_tabs.widget(0),
            widget.visualization_scroll,
        )
        self.assertIs(
            widget.visualization_scroll.widget(),
            widget.visualization_widget,
        )
        self.assertTrue(widget.visualization_scroll.widgetResizable())
        self.assertGreaterEqual(widget.visualization_widget.minimumHeight(), 720)
        self.assertEqual(
            widget.analysis_tabs.tabText(1),
            "Text Analysis",
        )
        self.assertEqual(
            widget.text_detail_tabs.tabText(0),
            "Individual Run Trends",
        )
        self.assertEqual(
            widget.text_detail_tabs.tabText(1),
            "Run / Channel Comparison",
        )
        self.assertEqual(
            widget.analysis_tabs.tabText(2),
            "Condition Compliance",
        )
        self.assertEqual(
            widget.analysis_tabs.tabText(4),
            "Stability Detection",
        )
        self.assertEqual(
            widget.analysis_tabs.tabText(6),
            "Statistical Assessments",
        )
        widget.close()

    def test_analysis_type_selector_switches_workflows(self):
        widget = BundleDataAnalysisWidget()

        self.assertEqual(
            [
                widget.analysis_mode_combo.itemText(index)
                for index in range(widget.analysis_mode_combo.count())
            ],
            ["Analyze Existing Results", "Compare Two Runs"],
        )
        self.assertEqual(widget.analysis_mode_stack.currentIndex(), 0)
        widget.analysis_mode_combo.setCurrentIndex(1)
        self.app.processEvents()
        self.assertEqual(widget.analysis_mode_stack.currentIndex(), 1)
        widget.close()

    def test_single_results_location_starts_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            widget = BundleDataAnalysisWidget()
            widget.refresh = Mock(return_value="single-result")
            widget.single_root_input.setText(str(root))

            result = widget.analyze_selected_root()

        self.assertEqual(result, "single-result")
        widget.refresh.assert_called_once_with(root)
        widget.close()

    def test_single_results_location_rejects_empty_input(self):
        widget = BundleDataAnalysisWidget()
        widget.refresh = Mock()

        self.assertIsNone(widget.analyze_selected_root())
        self.assertIn("valid results location", widget.status_label.text())
        widget.refresh.assert_not_called()
        widget.close()

    def test_two_independent_run_inputs_start_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root_a = Path(directory) / "channel-a"
            root_b = Path(directory) / "another-location" / "channel-b"
            root_a.mkdir()
            root_b.mkdir(parents=True)
            widget = BundleDataAnalysisWidget()
            widget.refresh = Mock(return_value="combined-result")
            widget.comparison_root_a.setText(str(root_a))
            widget.comparison_root_b.setText(str(root_b))

            result = widget.compare_selected_roots()

        self.assertEqual(result, "combined-result")
        selected_roots = widget.refresh.call_args.args[0]
        self.assertEqual(selected_roots, [root_a, root_b])
        widget.close()

    def test_comparison_button_analysis_runs_in_background_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            root_a = Path(directory) / "run-a"
            root_b = Path(directory) / "run-b"
            root_a.mkdir()
            root_b.mkdir()
            widget = BundleDataAnalysisWidget()
            widget.comparison_root_a.setText(str(root_a))
            widget.comparison_root_b.setText(str(root_b))

            thread = widget.start_comparison_analysis()

            self.assertIsNotNone(thread)
            self.assertIn("background", widget.status_label.text())
            self.assertFalse(widget.refresh_button.isEnabled())
            self.assertTrue(thread.wait(10000))
            self.app.processEvents()
            self.assertIsNotNone(widget.last_result)
            self.assertTrue(widget.refresh_button.isEnabled())
            widget.close()

    def test_comparison_rejects_missing_or_duplicate_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            widget = BundleDataAnalysisWidget()
            widget.refresh = Mock()
            widget.comparison_root_a.setText(str(root))
            widget.comparison_root_b.setText(str(root / "missing"))

            self.assertIsNone(widget.compare_selected_roots())
            self.assertIn("Run B", widget.status_label.text())
            widget.comparison_root_b.setText(str(root))
            self.assertIsNone(widget.compare_selected_roots())
            self.assertIn("must be different", widget.status_label.text())
            widget.refresh.assert_not_called()
            widget.close()

    def test_exports_comparison_csv_graphs_manifest_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_a = root / "run-a"
            run_b = root / "run-b"
            run_a.mkdir()
            run_b.mkdir()
            result = self._result()
            result.empty = False
            result.observations = pd.DataFrame(
                {
                    "Channel": [1, 2],
                    "Loop": [1, 1],
                    "Source": ["Realtime CSV", "Excel report fallback"],
                }
            )
            result.insights = ("All supplied points passed.",)

            def export_csv(destination):
                Path(destination, "analysis_summary.csv").write_text(
                    "summary\n",
                    encoding="utf-8",
                )

            result.export_csv = export_csv
            widget = BundleDataAnalysisWidget()
            widget.last_result = result
            widget.output_roots = [run_a, run_b]
            widget.practical_threshold_spin.setValue(15.0)
            widget.visualization_widget.set_result(result)
            self.app.processEvents()

            export_directory = widget.export_analysis_results(root)

            self.assertIsNotNone(export_directory)
            self.assertTrue(
                (export_directory / "analysis_summary.csv").is_file()
            )
            for filename in (
                "compliance_heatmap.png",
                "confidence_intervals.png",
                "channel_difference_heatmap.png",
                "loop_stability.png",
                "comparison_trend.png",
                "analysis_manifest.json",
                "analysis_summary.txt",
            ):
                self.assertTrue((export_directory / filename).is_file())
            manifest = json.loads(
                (export_directory / "analysis_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                manifest["analysis_roots"],
                [str(run_a), str(run_b)],
            )
            self.assertEqual(
                manifest["practical_difference_threshold_percent"],
                15.0,
            )
            self.assertEqual(manifest["trend_series"], 0)
            self.assertEqual(
                manifest["trend_series_with_sudden_jumps"],
                0,
            )
            self.assertEqual(
                manifest["matched_comparison_conditions"],
                1,
            )
            self.assertEqual(
                manifest["statistical_comparison_differences"],
                1,
            )
            widget.close()


if __name__ == "__main__":
    unittest.main()
