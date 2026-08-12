"""Bundle Test post-run analysis user interface."""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyqtgraph.exporters
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from analysis.bundle_data_analysis import (
    PRACTICAL_DIFFERENCE_THRESHOLD_PERCENT,
    analyze_bundle_runs,
)
from ui.analysis_visualization_widget import AnalysisVisualizationWidget


MAX_DISPLAY_TABLE_ROWS = 500


class AnalysisThread(QThread):
    """Calculate data analysis without blocking the Qt event loop."""

    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, roots, practical_threshold, parent=None):
        super().__init__(parent)
        self.roots = list(roots)
        self.practical_threshold = float(practical_threshold)

    def run(self):
        try:
            result = analyze_bundle_runs(
                self.roots,
                practical_difference_threshold_percent=(
                    self.practical_threshold
                ),
            )
        except Exception as exception:
            self.failed.emit(f"{type(exception).__name__}: {exception}")
            return
        self.completed.emit(result)


class BundleDataAnalysisWidget(QWidget):
    """Display statistical summaries across loops, runs, and channels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.output_root = None
        self.output_roots = []
        self.last_result = None
        self.analysis_thread = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Bundle Test Data Analysis")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        description = QLabel(
            "Evaluates point compliance first, then quantifies bias, "
            "repeatability, mean equivalence, and matched channel differences. "
            "Every result remains separated by set voltage and load current."
        )
        description.setWordWrap(True)

        mode_controls = QHBoxLayout()
        mode_label = QLabel("Analysis type:")
        self.analysis_mode_combo = QComboBox()
        self.analysis_mode_combo.addItem(
            "Analyze Existing Results",
            "single",
        )
        self.analysis_mode_combo.addItem(
            "Compare Two Runs",
            "compare",
        )
        self.analysis_mode_combo.setToolTip(
            "Choose whether to analyze one results location or compare "
            "two independently selected runs."
        )
        self.refresh_button = QPushButton("Refresh Analysis")
        self.refresh_button.clicked.connect(self.refresh)
        self.export_button = QPushButton("Export Analysis Results")
        self.export_button.setEnabled(False)
        self.export_button.setToolTip(
            "Export full analysis CSV files, dashboard graphs, selected "
            "source paths, settings, and conclusions."
        )
        self.export_button.clicked.connect(
            lambda: self.export_analysis_results()
        )
        mode_controls.addWidget(mode_label)
        mode_controls.addWidget(self.analysis_mode_combo)
        mode_controls.addStretch()
        mode_controls.addWidget(self.refresh_button)
        mode_controls.addWidget(self.export_button)

        self.analysis_mode_stack = QStackedWidget()

        single_group = QGroupBox("Analyze Existing Results")
        single_layout = QGridLayout(single_group)
        single_description = QLabel(
            "Analyze one completed run or a parent folder containing "
            "multiple related runs."
        )
        single_description.setWordWrap(True)
        self.single_root_input = QLineEdit()
        self.single_root_input.setPlaceholderText(
            "Select or paste a run folder or parent results folder"
        )
        browse_single = QPushButton("Browse Results Location")
        browse_single.clicked.connect(self._browse_single_root)
        analyze_single = QPushButton("Analyze Selected Results")
        analyze_single.setToolTip(
            "Recursively analyze supported result files beneath the "
            "selected location."
        )
        analyze_single.clicked.connect(self.start_selected_root_analysis)
        single_layout.addWidget(single_description, 0, 0, 1, 3)
        single_layout.addWidget(QLabel("Results location:"), 1, 0)
        single_layout.addWidget(self.single_root_input, 1, 1)
        single_layout.addWidget(browse_single, 1, 2)
        single_layout.addWidget(analyze_single, 2, 1, 1, 2)
        self.analysis_mode_stack.addWidget(single_group)

        comparison_group = QGroupBox("Compare Two Runs")
        comparison_layout = QGridLayout(comparison_group)
        comparison_description = QLabel(
            "Compare two run folders even when they are stored in "
            "different locations."
        )
        comparison_description.setWordWrap(True)
        self.source_label = QLabel("Results folder: not selected")
        self.source_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.comparison_root_a = QLineEdit()
        self.comparison_root_a.setPlaceholderText(
            "Select or paste the first run folder"
        )
        self.comparison_root_b = QLineEdit()
        self.comparison_root_b.setPlaceholderText(
            "Select or paste the second run folder"
        )
        browse_a = QPushButton("Browse Run A")
        browse_a.clicked.connect(
            lambda: self._browse_comparison_root(
                self.comparison_root_a,
                "Select Run A Results Folder",
            )
        )
        browse_b = QPushButton("Browse Run B")
        browse_b.clicked.connect(
            lambda: self._browse_comparison_root(
                self.comparison_root_b,
                "Select Run B Results Folder",
            )
        )
        compare_button = QPushButton("Compare Run A and Run B")
        compare_button.setToolTip(
            "Analyze the two independently selected folders together. "
            "Files remain in their original locations."
        )
        compare_button.clicked.connect(self.start_comparison_analysis)
        self.practical_threshold_spin = QDoubleSpinBox()
        self.practical_threshold_spin.setRange(0.1, 100.0)
        self.practical_threshold_spin.setDecimals(1)
        self.practical_threshold_spin.setSingleStep(1.0)
        self.practical_threshold_spin.setValue(
            PRACTICAL_DIFFERENCE_THRESHOLD_PERCENT
        )
        self.practical_threshold_spin.setSuffix(" % of limit")
        self.practical_threshold_spin.setToolTip(
            "A matched channel difference at or above this percentage of "
            "the engineering error limit is practically meaningful."
        )
        self.practical_threshold_spin.valueChanged.connect(
            self._practical_threshold_changed
        )
        comparison_layout.addWidget(comparison_description, 0, 0, 1, 3)
        comparison_layout.addWidget(QLabel("Run A:"), 1, 0)
        comparison_layout.addWidget(self.comparison_root_a, 1, 1)
        comparison_layout.addWidget(browse_a, 1, 2)
        comparison_layout.addWidget(QLabel("Run B:"), 2, 0)
        comparison_layout.addWidget(self.comparison_root_b, 2, 1)
        comparison_layout.addWidget(browse_b, 2, 2)
        comparison_layout.addWidget(
            QLabel("Practical difference threshold:"),
            3,
            0,
        )
        comparison_layout.addWidget(
            self.practical_threshold_spin,
            3,
            1,
            1,
            2,
        )
        comparison_layout.addWidget(compare_button, 4, 1, 1, 2)
        self.analysis_mode_stack.addWidget(comparison_group)
        self.analysis_mode_combo.currentIndexChanged.connect(
            self.analysis_mode_stack.setCurrentIndex
        )

        self.status_label = QLabel(
            "Analysis will appear after a test completes."
        )
        self.status_label.setStyleSheet(
            "padding: 6px; background: #eef3f8; font-weight: bold;"
        )
        self.insights = QTextBrowser()
        self.insights.setMinimumHeight(165)

        self.analysis_setup_group = QGroupBox("Analysis Setup")
        setup_layout = QVBoxLayout(self.analysis_setup_group)
        setup_layout.addLayout(mode_controls)
        setup_layout.addWidget(self.analysis_mode_stack)

        self.analysis_output_group = QGroupBox("Analysis Output")
        output_layout = QVBoxLayout(self.analysis_output_group)
        output_layout.addWidget(self.source_label)
        output_layout.addWidget(self.status_label)
        output_layout.addWidget(self.insights, stretch=1)

        self.analysis_workspace = QSplitter(Qt.Horizontal)
        self.analysis_workspace.setObjectName("analysisWorkspace")
        self.analysis_workspace.addWidget(self.analysis_setup_group)
        self.analysis_workspace.addWidget(self.analysis_output_group)
        self.analysis_workspace.setStretchFactor(0, 3)
        self.analysis_workspace.setStretchFactor(1, 2)
        self.analysis_workspace.setSizes((680, 470))
        self.analysis_workspace.setMinimumHeight(250)
        self.analysis_workspace.setMaximumHeight(340)
        self.analysis_workspace.setStyleSheet(
            "QSplitter#analysisWorkspace::handle { background: #cbd5e1; "
            "width: 6px; margin: 5px 2px; border-radius: 3px; }"
        )

        self.analysis_tabs = QTabWidget()
        self.visualization_widget = AnalysisVisualizationWidget()
        self.visualization_widget.setMinimumHeight(720)
        self.visualization_scroll = QScrollArea()
        self.visualization_scroll.setObjectName("visualDashboardScroll")
        self.visualization_scroll.setWidgetResizable(True)
        self.visualization_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )
        self.visualization_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )
        self.visualization_scroll.setWidget(self.visualization_widget)
        self.trend_page = QWidget()
        trend_layout = QVBoxLayout(self.trend_page)
        self.trend_browser = QTextBrowser()
        self.trend_browser.setMaximumHeight(250)
        self.trend_table = self._create_table()
        self.comparison_text_table = self._create_table()
        self.text_detail_tabs = QTabWidget()
        self.text_detail_tabs.addTab(
            self.trend_table,
            "Individual Run Trends",
        )
        self.text_detail_tabs.addTab(
            self.comparison_text_table,
            "Run / Channel Comparison",
        )
        trend_layout.addWidget(self.trend_browser)
        trend_layout.addWidget(self.text_detail_tabs, stretch=1)
        self.summary_table = self._create_table()
        self.loop_table = self._create_table()
        self.stability_table = self._create_table()
        self.channel_table = self._create_table()
        self.hypothesis_table = self._create_table()
        self.extremes_table = self._create_table()
        self.methodology_browser = QTextBrowser()
        self.methodology_browser.setOpenExternalLinks(False)
        self.analysis_tabs.addTab(
            self.visualization_scroll,
            "Visual Dashboard",
        )
        self.analysis_tabs.addTab(
            self.trend_page,
            "Text Analysis",
        )
        self.analysis_tabs.addTab(
            self.summary_table,
            "Condition Compliance",
        )
        self.analysis_tabs.addTab(
            self.loop_table,
            "Loop Repeatability",
        )
        self.analysis_tabs.addTab(
            self.stability_table,
            "Stability Detection",
        )
        self.analysis_tabs.addTab(
            self.channel_table,
            "Matched Channels",
        )
        self.analysis_tabs.addTab(
            self.hypothesis_table,
            "Statistical Assessments",
        )
        self.analysis_tabs.addTab(
            self.extremes_table,
            "Maximum / Minimum",
        )
        self.analysis_tabs.addTab(
            self.methodology_browser,
            "Methodology",
        )
        self.summary_table.itemSelectionChanged.connect(
            self._sync_dashboard_from_summary_selection
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.analysis_workspace)
        layout.addWidget(self.analysis_tabs, stretch=1)

    @staticmethod
    def _create_table():
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    @staticmethod
    def _sort_table_data(dataframe, column):
        if dataframe.empty or column not in dataframe.columns:
            return dataframe
        return dataframe.sort_values(column, ascending=False)

    def choose_output_root(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Bundle Test Results Folder"
        )
        if directory:
            self.single_root_input.setText(directory)
            return self.refresh(directory)
        return None

    def _browse_single_root(self):
        current = self.single_root_input.text().strip()
        start_directory = current if Path(current).is_dir() else ""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Results Location",
            start_directory,
        )
        if directory:
            self.single_root_input.setText(directory)

    def analyze_selected_root(self):
        root_text = self.single_root_input.text().strip()
        root = Path(root_text) if root_text else None
        if root is None or not root.is_dir():
            self.status_label.setText(
                "Select a valid results location before analyzing."
            )
            return None
        return self._refresh_with_feedback(
            root,
            "Analyzing selected results. Large reports may take a moment...",
        )

    def start_selected_root_analysis(self):
        root_text = self.single_root_input.text().strip()
        root = Path(root_text) if root_text else None
        if root is None or not root.is_dir():
            self.status_label.setText(
                "Select a valid results location before analyzing."
            )
            return None
        return self._start_async_analysis(
            [root],
            "Analyzing selected results in the background...",
        )

    def _browse_comparison_root(self, target, title):
        current = target.text().strip()
        start_directory = current if Path(current).is_dir() else ""
        directory = QFileDialog.getExistingDirectory(
            self,
            title,
            start_directory,
        )
        if directory:
            target.setText(directory)

    def compare_selected_roots(self):
        roots = self._validated_comparison_roots()
        if roots is None:
            return None
        return self._refresh_with_feedback(
            roots,
            "Comparing Run A and Run B. Loading and matching report data...",
        )

    def start_comparison_analysis(self):
        roots = self._validated_comparison_roots()
        if roots is None:
            return None
        return self._start_async_analysis(
            roots,
            "Comparing Run A and Run B in the background. "
            "The window remains responsive...",
        )

    def _validated_comparison_roots(self):
        root_a_text = self.comparison_root_a.text().strip()
        root_b_text = self.comparison_root_b.text().strip()
        root_a = Path(root_a_text) if root_a_text else None
        root_b = Path(root_b_text) if root_b_text else None
        missing = []
        if root_a is None or not root_a.is_dir():
            missing.append("Run A")
        if root_b is None or not root_b.is_dir():
            missing.append("Run B")
        if missing:
            self.status_label.setText(
                "Select a valid folder for " + " and ".join(missing) + "."
            )
            return None
        if root_a.resolve() == root_b.resolve():
            self.status_label.setText(
                "Run A and Run B must be different folders."
            )
            return None
        return [root_a, root_b]

    def _start_async_analysis(self, roots, message):
        if self.analysis_thread is not None:
            self.status_label.setText(
                "An analysis is already running. Please wait for it to finish."
            )
            return None
        self._set_output_roots(roots)
        self.status_label.setText(message)
        self.refresh_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.analysis_thread = AnalysisThread(
            self.output_roots,
            self.practical_threshold_spin.value(),
            parent=self,
        )
        self.analysis_thread.completed.connect(
            self._async_analysis_completed
        )
        self.analysis_thread.failed.connect(self._async_analysis_failed)
        self.analysis_thread.finished.connect(self._async_analysis_finished)
        self.analysis_thread.start()
        return self.analysis_thread

    def _async_analysis_completed(self, result):
        self._apply_analysis_result(result)

    def _async_analysis_failed(self, message):
        self.status_label.setText(f"Analysis failed: {message}")

    def _async_analysis_finished(self):
        thread = self.analysis_thread
        self.analysis_thread = None
        self.refresh_button.setEnabled(True)
        if thread is not None:
            thread.deleteLater()

    def _refresh_with_feedback(self, roots, message):
        self.status_label.setText(message)
        self.refresh_button.setEnabled(False)
        self.export_button.setEnabled(False)
        application = QApplication.instance()
        if application is not None:
            application.setOverrideCursor(Qt.WaitCursor)
            application.processEvents()
        try:
            return self.refresh(roots)
        finally:
            self.refresh_button.setEnabled(True)
            if application is not None:
                application.restoreOverrideCursor()
                application.processEvents()

    def _practical_threshold_changed(self, value):
        if self.last_result is None:
            return
        self.status_label.setText(
            f"Practical threshold changed to {value:.1f}%. "
            "Refresh or compare again to recalculate conclusions."
        )

    @staticmethod
    def _export_plot(plot_widget, path):
        exporter = pyqtgraph.exporters.ImageExporter(
            plot_widget.getPlotItem()
        )
        exporter.parameters()["width"] = 1600
        exporter.export(str(path))

    def export_analysis_results(self, destination=None):
        result = self.last_result
        if result is None or result.empty:
            self.status_label.setText(
                "Run or load an analysis before exporting."
            )
            return None
        if destination is None:
            destination = QFileDialog.getExistingDirectory(
                self,
                "Select Analysis Export Destination",
            )
            if not destination:
                return None
        destination = Path(destination)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        prefix = (
            "analysis_comparison"
            if len(self.output_roots) > 1
            else "analysis_export"
        )
        export_directory = destination / f"{prefix}_{timestamp}"
        export_directory.mkdir(parents=True, exist_ok=False)
        try:
            result.export_csv(export_directory)
            plots = {
                "compliance_heatmap.png": (
                    self.visualization_widget.heatmap
                ),
                "confidence_intervals.png": (
                    self.visualization_widget.confidence_plot
                ),
                "channel_difference_heatmap.png": (
                    self.visualization_widget.channel_difference_plot
                ),
                "loop_stability.png": (
                    self.visualization_widget.loop_plot
                ),
                "comparison_trend.png": (
                    self.visualization_widget.comparison_trend_plot
                ),
            }
            for filename, plot_widget in plots.items():
                self._export_plot(
                    plot_widget,
                    export_directory / filename,
                )

            observations = result.observations
            channels = (
                [str(value) for value in observations["Channel"].unique()]
                if "Channel" in observations.columns
                else []
            )
            loops = (
                sorted(
                    {
                        int(float(value))
                        for value in observations["Loop"].dropna()
                    }
                )
                if "Loop" in observations.columns
                else []
            )
            sources = (
                {
                    str(key): int(value)
                    for key, value in observations["Source"]
                    .value_counts()
                    .items()
                }
                if "Source" in observations.columns
                else {}
            )
            trend_summary = getattr(
                result,
                "trend_summary",
                pd.DataFrame(),
            )
            comparison_summary = getattr(
                result,
                "channel_comparison",
                pd.DataFrame(),
            )
            manifest = {
                "generated_at": datetime.now().isoformat(),
                "analysis_roots": [
                    str(path) for path in self.output_roots
                ],
                "measurement_rows": int(len(observations)),
                "condition_metric_conclusions": int(len(result.summary)),
                "channels": channels,
                "loops": loops,
                "data_sources": sources,
                "practical_difference_threshold_percent": (
                    getattr(
                        result,
                        "practical_difference_threshold_percent",
                        self.practical_threshold_spin.value(),
                    )
                ),
                "minimum_inference_loops": 5,
                "trend_series": int(len(trend_summary)),
                "trend_series_moving_away_from_zero": int(
                    (
                        trend_summary.get(
                            "Movement Relative to Zero",
                            pd.Series(dtype="object"),
                        )
                        == "Moving away from zero"
                    ).sum()
                ),
                "trend_series_with_sudden_jumps": int(
                    (
                        trend_summary.get(
                            "Sudden Jump Count",
                            pd.Series(dtype="float64"),
                        )
                        > 0
                    ).sum()
                ),
                "trend_series_with_robust_outliers": int(
                    (
                        trend_summary.get(
                            "Robust Outlier Count",
                            pd.Series(dtype="float64"),
                        )
                        > 0
                    ).sum()
                ),
                "matched_comparison_conditions": int(
                    len(comparison_summary)
                ),
                "statistical_comparison_differences": int(
                    (
                        comparison_summary.get(
                            "Difference Detected",
                            pd.Series(dtype="object"),
                        )
                        == "Yes"
                    ).sum()
                ),
                "practical_comparison_differences": int(
                    (
                        comparison_summary.get(
                            "Practically Meaningful",
                            pd.Series(dtype="object"),
                        )
                        == "Yes"
                    ).sum()
                ),
                "display_table_row_limit": MAX_DISPLAY_TABLE_ROWS,
                "exported_graphs": list(plots),
            }
            (export_directory / "analysis_manifest.json").write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8",
            )
            summary_lines = [
                "Hornbill Bundle Test Data Analysis",
                f"Generated: {manifest['generated_at']}",
                "",
                "Analysis roots:",
                *(
                    f"- {path}"
                    for path in manifest["analysis_roots"]
                ),
                "",
                "Conclusions:",
                *(f"- {line}" for line in result.insights),
                "",
                "Trend overview:",
                *(f"- {line}" for line in getattr(result, "trend_report", ())[:6]),
                "",
                "Comparison overview:",
                *(
                    f"- {line}"
                    for line in getattr(result, "comparison_report", ())[:4]
                ),
            ]
            (export_directory / "analysis_summary.txt").write_text(
                "\n".join(summary_lines) + "\n",
                encoding="utf-8",
            )
        except Exception as exception:
            self.status_label.setText(
                f"Analysis export failed: {exception}"
            )
            return None

        self.status_label.setText(
            f"Analysis exported to: {export_directory}"
        )
        return export_directory

    @staticmethod
    def _normalize_output_roots(output_root):
        if isinstance(output_root, (str, Path)):
            candidates = (output_root,)
        else:
            candidates = tuple(output_root or ())
        roots = []
        seen = set()
        for candidate in candidates:
            path = Path(candidate)
            identity = path.resolve()
            if identity in seen:
                continue
            seen.add(identity)
            roots.append(path)
        return roots

    @staticmethod
    def _format_value(value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "N/A"
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)

    @staticmethod
    def _cell_color(column, value):
        text = str(value)
        if column == "Status":
            return {
                "Pass": QColor("#c6efce"),
                "Warning": QColor("#ffeb9c"),
                "Fail": QColor("#ffc7ce"),
                "Insufficient Data": QColor("#d9e1f2"),
            }.get(text)
        if column == "Compliance Conclusion":
            if text.startswith("FAIL"):
                return QColor("#ffc7ce")
            if text.startswith("MARGINAL"):
                return QColor("#ffeb9c")
            if text.startswith("PASS"):
                return QColor("#c6efce")
        if column in {"Result", "Conclusion"}:
            if text.startswith("Not stable"):
                return QColor("#ffc7ce")
            if text.startswith("Stable from loop"):
                return QColor("#c6efce")
            if "preliminary" in text.lower() or "collect at least" in text.lower():
                return QColor("#ffeb9c")
            if (
                "not demonstrated" in text.lower()
                or "detected offset" in text.lower()
                or text == "Bias detected"
            ):
                return QColor("#ffeb9c")
            if (
                "equivalent" in text.lower()
                or "no significant" in text.lower()
                or "no statistically" in text.lower()
            ):
                return QColor("#c6efce")
        if column == "Passed":
            return QColor("#c6efce" if bool(value) else "#ffc7ce")
        if column == "Stability Reached":
            return QColor("#c6efce" if text == "Yes" else "#ffc7ce")
        if column == "Movement Relative to Zero":
            if text == "Moving toward zero":
                return QColor("#c6efce")
            if text == "Moving away from zero":
                return QColor("#ffc7ce")
        if column == "Boundary Direction":
            if text in {"Approaching boundary", "Near or beyond boundary"}:
                return QColor("#ffc7ce")
            if text == "Moving away from boundary":
                return QColor("#c6efce")
        if column == "Trend Direction" and text == "Flat":
            return QColor("#c6efce")
        if column in {"Practically Meaningful", "Difference Detected"}:
            if text == "Yes":
                return QColor("#ffeb9c")
            if text == "No":
                return QColor("#c6efce")
        if column == "Minimum Error" or value == "Minimum":
            return QColor("#c6efce")
        if column == "Maximum Error" or value in {"Maximum", "Maximum Absolute"}:
            return QColor("#ffc7ce")
        if column == "Pass Rate (%)":
            try:
                return QColor("#c6efce" if float(value) >= 100.0 else "#ffeb9c")
            except (TypeError, ValueError):
                return None
        return None

    def _populate_table(self, table, dataframe):
        table.clear()
        table.analysis_dataframe = pd.DataFrame()
        if dataframe.empty:
            table.setRowCount(0)
            table.setColumnCount(0)
            return
        displayed = dataframe.head(MAX_DISPLAY_TABLE_ROWS).reset_index(
            drop=True
        )
        table.analysis_dataframe = displayed
        table.setToolTip(
            f"Showing {len(displayed)} of {len(dataframe)} rows. "
            "All rows remain available in exported analysis CSV files."
        )
        columns = list(displayed.columns)
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(displayed))
        for row_index, (_, row) in enumerate(displayed.iterrows()):
            for column_index, column in enumerate(columns):
                value = row[column]
                item = QTableWidgetItem(self._format_value(value))
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                color = self._cell_color(column, value)
                if color:
                    item.setBackground(color)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                table.setItem(row_index, column_index, item)

    def _sync_dashboard_from_summary_selection(self):
        row_index = self.summary_table.currentRow()
        if row_index < 0 or self.last_result is None:
            return
        displayed = getattr(
            self.summary_table,
            "analysis_dataframe",
            pd.DataFrame(),
        )
        if row_index >= len(displayed):
            return
        source = displayed.iloc[row_index]
        self.visualization_widget.select_condition(
            {
                "DUT": source["DUT"],
                "Test": source["Test"],
                "Metric": source["Metric"],
                "Channel": source["Channel"],
                "Set Voltage (V)": source["Set Voltage (V)"],
                "Set Current (A)": source["Set Current (A)"],
            }
        )
        self.analysis_tabs.setCurrentWidget(self.visualization_widget)

    def _set_output_roots(self, output_root):
        self.output_roots = self._normalize_output_roots(output_root)
        self.output_root = (
            self.output_roots[0] if len(self.output_roots) == 1 else None
        )
        self.analysis_mode_combo.setCurrentIndex(
            0 if len(self.output_roots) == 1 else 1
        )
        if len(self.output_roots) == 1:
            self.single_root_input.setText(str(self.output_roots[0]))
        elif len(self.output_roots) >= 2:
            self.comparison_root_a.setText(str(self.output_roots[0]))
            self.comparison_root_b.setText(str(self.output_roots[1]))
        if len(self.output_roots) == 1:
            source_text = f"Results folder: {self.output_roots[0]}"
        else:
            source_text = (
                f"Compared folders ({len(self.output_roots)}): "
                + " | ".join(str(path) for path in self.output_roots)
            )
        self.source_label.setText(source_text)
        self.source_label.setToolTip(source_text)

    def refresh(self, output_root=None, export_directory=None):
        if output_root is not None:
            self._set_output_roots(output_root)
        elif not self.output_roots and self.output_root:
            self._set_output_roots([Path(self.output_root)])
        if not self.output_roots:
            self.status_label.setText(
                "Select one or more results folders before refreshing."
            )
            return None

        result = analyze_bundle_runs(
            self.output_roots,
            practical_difference_threshold_percent=(
                self.practical_threshold_spin.value()
            ),
        )
        return self._apply_analysis_result(result, export_directory)

    def _apply_analysis_result(self, result, export_directory=None):
        self.last_result = result
        self.export_button.setEnabled(not result.empty)
        self.visualization_widget.set_result(result)
        trend_report = getattr(result, "trend_report", ())
        comparison_report = getattr(result, "comparison_report", ())
        trend_summary = getattr(result, "trend_summary", pd.DataFrame())
        overview_lines = []
        priority_started = False
        for line in trend_report:
            if line == "Highest-priority findings:":
                overview_lines.append("<h3>Highest-Priority Findings</h3>")
                priority_started = True
                continue
            if priority_started:
                overview_lines.append(f"<p>{line}</p>")
            else:
                overview_lines.append(f"<p>&bull; {line}</p>")
        self.trend_browser.setHtml(
            "<h2>Individual Run Decision Summary</h2>"
            "<p><b>Read each finding as:</b> Status &rarr; Finding &rarr; "
            "Magnitude &rarr; Confidence &rarr; Recommended Action. "
            "Technical calculations remain available in the tables.</p>"
            + "".join(overview_lines)
            + "<h2>Compare Two Runs Decision Summary</h2>"
            + "".join(
                f"<p>&bull; {line}</p>"
                for line in comparison_report
            )
        )
        self._populate_table(
            self.trend_table,
            self._sort_table_data(
                trend_summary,
                "Priority Score",
            ),
        )
        self._populate_table(
            self.comparison_text_table,
            self._sort_table_data(
                result.channel_comparison,
                "Comparison Priority Score",
            ),
        )
        self._populate_table(
            self.summary_table,
            self._sort_table_data(
                result.summary,
                "Maximum Limit Usage (%)",
            ),
        )
        self._populate_table(
            self.loop_table,
            self._sort_table_data(
                result.loop_performance,
                "Maximum Absolute Error",
            ),
        )
        self._populate_table(
            self.stability_table,
            self._sort_table_data(
                result.stability_summary,
                "Span Limit Usage (%)",
            ),
        )
        self._populate_table(
            self.channel_table,
            self._sort_table_data(
                result.channel_comparison,
                "Difference Limit Usage (%)",
            ),
        )
        self._populate_table(
            self.hypothesis_table,
            result.hypothesis_tests,
        )
        self._populate_table(self.extremes_table, result.extremes)
        self.insights.setHtml(
            "<br>".join(f"&bull; {line}" for line in result.insights)
        )
        self.methodology_browser.setHtml(
            "".join(result.methodology)
        )
        if result.empty:
            self.status_label.setText("No analyzable realtime data was found.")
            return result

        if export_directory:
            result.export_csv(export_directory)
        self.status_label.setText(
            f"Analysis ready: {len(result.observations)} measurement rows, "
            f"{result.observations['Channel'].nunique()} channel(s), "
            f"{len(result.summary)} condition/metric conclusion(s). "
            f"Tables display up to {MAX_DISPLAY_TABLE_ROWS} rows."
        )
        return result
