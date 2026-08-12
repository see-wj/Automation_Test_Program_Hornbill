"""Interactive visual dashboard for Bundle Test statistical results."""

import math

import pandas as pd
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


FILTERS = (
    ("DUT", "DUT"),
    ("Test", "Test"),
    ("Metric", "Metric"),
    ("Channel", "Channel"),
    ("Voltage", "Set Voltage (V)"),
    ("Current", "Set Current (A)"),
)
CHANNEL_COLORS = (
    "#0072b2",
    "#d55e00",
    "#009e73",
    "#cc79a7",
    "#56b4e9",
    "#e69f00",
    "#6a3d9a",
    "#4d4d4d",
)
MAX_HEATMAP_LABELS = 100
MAX_CONFIDENCE_POINTS = 30
MAX_LOOP_SERIES = 8


class AnalysisVisualizationWidget(QWidget):
    """Present filtered compliance, confidence, and stability plots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self.filter_combos = {}
        self.card_values = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(7)

        filter_bar = QFrame()
        filter_bar.setObjectName("analysisFilterBar")
        filter_bar.setStyleSheet(
            "QFrame#analysisFilterBar { background: #f4f7fb; "
            "border: 1px solid #cbd6e2; border-radius: 6px; }"
        )
        filters = QGridLayout(filter_bar)
        filters.setContentsMargins(10, 7, 10, 7)
        filters.setHorizontalSpacing(9)
        filters.setVerticalSpacing(5)
        filter_title = QLabel("FILTERS")
        filter_title.setStyleSheet(
            "font-weight: bold; color: #244b74; letter-spacing: 1px;"
        )
        filters.addWidget(filter_title, 0, 0)
        for index, (label_text, column) in enumerate(FILTERS):
            label = QLabel(f"{label_text}:")
            label.setStyleSheet("font-weight: bold; color: #455a6f;")
            combo = QComboBox()
            combo.addItem("All", None)
            combo.setMinimumWidth(120)
            combo.setMaximumWidth(210)
            combo.currentIndexChanged.connect(self._refresh_dashboard)
            row = index // 3
            column_index = 1 + (index % 3) * 2
            filters.addWidget(label, row, column_index)
            filters.addWidget(combo, row, column_index + 1)
            self.filter_combos[column] = combo
        self.reset_filters_button = QPushButton("Reset")
        self.reset_filters_button.setToolTip(
            "Reset every dashboard filter to All."
        )
        self.reset_filters_button.clicked.connect(self.reset_filters)
        filters.addWidget(self.reset_filters_button, 1, 7)
        filters.setColumnStretch(6, 1)
        layout.addWidget(filter_bar)

        cards = QHBoxLayout()
        cards.setSpacing(6)
        for key, title in (
            ("records", "Error Records"),
            ("pass_rate", "Weighted Pass Rate"),
            ("limit_usage", "Worst Limit Usage"),
            ("max_error", "Maximum |Error|"),
            ("mean_bias", "Weighted Mean Bias"),
            ("conclusion", "Condition Conclusions"),
        ):
            card, value_label = self._create_card(title)
            self.card_values[key] = value_label
            cards.addWidget(card, stretch=1)
        layout.addLayout(cards)

        self.hover_label = QLabel(
            "Graph details appear here when the cursor is over a data point."
        )
        self.hover_label.setWordWrap(True)
        self.hover_label.setMinimumHeight(34)
        self.hover_label.setMaximumHeight(52)
        self.hover_label.setStyleSheet(
            "padding: 8px; background: #f5f7fa; border: 1px solid #d5dbe3; "
            "border-radius: 4px;"
        )
        layout.addWidget(self.hover_label)

        self.heatmap = pg.PlotWidget(
            title="Voltage / Current Compliance Heatmap"
        )
        self.confidence_plot = pg.PlotWidget(
            title="Mean Error and 95% Confidence Interval"
        )
        self.loop_plot = pg.PlotWidget(
            title="Individual Error Trend by Loop"
        )
        self.individual_trend_plot = self.loop_plot
        self.channel_difference_plot = pg.PlotWidget(
            title="Matched Channel Difference (A-B)"
        )
        self.comparison_trend_plot = pg.PlotWidget(
            title="Matched A-B Difference Trend by Loop"
        )
        self.plot_tabs = QTabWidget()
        self.plot_tabs.setDocumentMode(True)
        self.plot_tabs.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        self.plot_tabs.addTab(
            self._plot_page(
                self.heatmap,
                "Shows worst specification-limit usage at each voltage and "
                "current condition. Green is below 80%, amber is 80–100%, "
                "and red exceeds 100%.",
            ),
            "Compliance Heatmap",
        )
        self.plot_tabs.addTab(
            self._plot_page(
                self.confidence_plot,
                "Shows condition mean errors, 95% confidence intervals, and "
                "their applicable lower and upper engineering boundaries.",
            ),
            "Confidence Intervals",
        )
        self.plot_tabs.addTab(
            self._plot_page(
                self.channel_difference_plot,
                "Compares matched Channel A minus Channel B error as a "
                "percentage of the strict engineering limit.",
            ),
            "Channel Comparison",
        )
        self.plot_tabs.addTab(
            self._plot_page(
                self.loop_plot,
                "Tracks loop mean error for each selected channel, voltage, "
                "current, and metric to expose drift and repeatability.",
            ),
            "Individual Trend",
        )
        self.plot_tabs.addTab(
            self._plot_page(
                self.comparison_trend_plot,
                "Tracks the matched Channel A minus Channel B error for each "
                "loop. A flat line near zero indicates similar behavior; "
                "movement away from zero indicates a growing run difference.",
            ),
            "Comparison Trend",
        )
        layout.addWidget(self.plot_tabs, stretch=10)

        for plot in (
            self.heatmap,
            self.confidence_plot,
            self.channel_difference_plot,
            self.loop_plot,
            self.comparison_trend_plot,
        ):
            plot.showGrid(x=True, y=True, alpha=0.2)
            plot.setBackground("#ffffff")
            plot.getAxis("left").setTextPen("#202020")
            plot.getAxis("bottom").setTextPen("#202020")
            plot.getPlotItem().titleLabel.setText(
                plot.getPlotItem().titleLabel.text,
                color="#202020",
                size="13pt",
            )
            plot.getAxis("left").setStyle(tickFont=QFont("Arial", 10))
            plot.getAxis("bottom").setStyle(tickFont=QFont("Arial", 10))

    @staticmethod
    def _plot_page(plot, description):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(5, 6, 5, 5)
        layout.setSpacing(5)
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet(
            "padding: 5px 8px; color: #34495e; background: #eef3f8; "
            "border-radius: 4px;"
        )
        plot.setMinimumHeight(300)
        plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(description_label)
        layout.addWidget(plot, stretch=1)
        return page

    @staticmethod
    def _create_card(title):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setMinimumHeight(58)
        frame.setMaximumHeight(68)
        frame.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #c7d1dc; "
            "border-radius: 6px; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("border: none; color: #405060;")
        value_label = QLabel("N/A")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setFont(QFont("Arial", 12, QFont.Bold))
        value_label.setStyleSheet("border: none; color: #172b4d;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return frame, value_label

    def reset_filters(self):
        for combo in self.filter_combos.values():
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self._refresh_dashboard()

    def set_result(self, result):
        self.result = result
        self._populate_filters()
        self._refresh_dashboard()

    def select_condition(self, values):
        for column, value in values.items():
            combo = self.filter_combos.get(column)
            if combo is None:
                continue
            index = combo.findData(value)
            if index < 0:
                text = self._format_filter_value(value)
                index = combo.findText(text)
            if index >= 0:
                combo.setCurrentIndex(index)

    def _populate_filters(self):
        summary = (
            self.result.summary
            if self.result is not None
            else pd.DataFrame()
        )
        for _label, column in FILTERS:
            combo = self.filter_combos[column]
            selected = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("All", None)
            if column in summary.columns:
                values = [
                    value
                    for value in summary[column].drop_duplicates().tolist()
                    if not pd.isna(value)
                ]
                for value in sorted(values, key=self._sort_key):
                    combo.addItem(self._format_filter_value(value), value)
            selected_index = combo.findData(selected)
            combo.setCurrentIndex(max(0, selected_index))
            combo.blockSignals(False)

    @staticmethod
    def _sort_key(value):
        try:
            return 0, float(value)
        except (TypeError, ValueError):
            return 1, str(value)

    @staticmethod
    def _format_filter_value(value):
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)

    def _filtered(self, dataframe):
        if dataframe is None or dataframe.empty:
            return pd.DataFrame()
        filtered = dataframe
        for _label, column in FILTERS:
            if column not in filtered.columns:
                continue
            selected = self.filter_combos[column].currentData()
            if selected is None:
                continue
            if isinstance(selected, float):
                numeric = pd.to_numeric(filtered[column], errors="coerce")
                filtered = filtered.loc[
                    (numeric - selected).abs() <= 1e-12
                ]
            else:
                filtered = filtered.loc[filtered[column] == selected]
        return filtered.copy()

    def _refresh_dashboard(self, *_args):
        if self.result is None:
            self._clear_dashboard()
            return
        summary = self._filtered(self.result.summary)
        loops = self._filtered(self.result.loop_performance)
        channel_comparison = self._filtered_channel_comparison(
            getattr(self.result, "channel_comparison", pd.DataFrame())
        )
        self._update_cards(summary)
        self._update_heatmap(summary)
        self._update_confidence_plot(summary)
        self._update_channel_difference_plot(channel_comparison)
        self._update_loop_plot(loops)
        self._update_comparison_trend_plot(loops, channel_comparison)

    def _clear_dashboard(self):
        for value_label in self.card_values.values():
            value_label.setText("N/A")
        self.heatmap.clear()
        self.confidence_plot.clear()
        self.channel_difference_plot.clear()
        self.loop_plot.clear()
        self.comparison_trend_plot.clear()

    def _filtered_channel_comparison(self, dataframe):
        filtered = self._filtered(dataframe)
        if filtered.empty:
            return filtered
        channel = self.filter_combos["Channel"].currentData()
        if channel is not None:
            comparison_basis = (
                filtered["Comparison Basis"].astype(str).str.lower()
                if "Comparison Basis" in filtered.columns
                else pd.Series("channel", index=filtered.index)
            )
            run_comparison = comparison_basis == "run"
            channel_match = (
                (filtered["Channel A"] == channel)
                | (filtered["Channel B"] == channel)
            )
            if {"DUT Channel A", "DUT Channel B"}.issubset(filtered.columns):
                channel_text = str(channel)
                channel_match = channel_match | (
                    run_comparison
                    & (
                        (filtered["DUT Channel A"].astype(str) == channel_text)
                        | (filtered["DUT Channel B"].astype(str) == channel_text)
                    )
                )
            filtered = filtered.loc[channel_match]
        return filtered

    def _update_cards(self, summary):
        if summary.empty:
            for value_label in self.card_values.values():
                value_label.setText("N/A")
            return
        samples = summary["Samples"].astype(float)
        record_count = int(samples.sum())
        weighted_pass_rate = float(
            (summary["Pass Rate (%)"] * samples).sum() / samples.sum()
        )
        weighted_bias = float(
            (summary["Mean Error"] * samples).sum() / samples.sum()
        )
        failed = int(
            summary["Compliance Conclusion"].str.startswith("FAIL").sum()
        )
        marginal = int(
            summary["Compliance Conclusion"].str.startswith("MARGINAL").sum()
        )
        passed = len(summary) - failed - marginal
        self.card_values["records"].setText(str(record_count))
        self.card_values["pass_rate"].setText(f"{weighted_pass_rate:.2f}%")
        self.card_values["limit_usage"].setText(
            f"{summary['Maximum Limit Usage (%)'].max():.2f}%"
        )
        self.card_values["max_error"].setText(
            f"{summary['Maximum Absolute Error'].max():.6g}"
        )
        self.card_values["mean_bias"].setText(f"{weighted_bias:.6g}")
        self.card_values["conclusion"].setText(
            f"{passed} P / {marginal} M / {failed} F"
        )
        conclusion_color = (
            "#b22222" if failed else "#b36b00" if marginal else "#1b7f3a"
        )
        self.card_values["conclusion"].setStyleSheet(
            f"border: none; color: {conclusion_color};"
        )

    @staticmethod
    def _usage_color(limit_usage):
        if limit_usage > 100.0:
            return "#d73027"
        if limit_usage >= 80.0:
            return "#fdae61"
        return "#1a9850"

    def _update_heatmap(self, summary):
        self.heatmap.clear()
        self.heatmap.setLabel("bottom", "Set Voltage", units="V")
        self.heatmap.setLabel("left", "Load Current", units="A")
        if summary.empty:
            return
        grouped = (
            summary.groupby(
                ["Set Voltage (V)", "Set Current (A)"],
                dropna=False,
                as_index=False,
            )
            .agg(
                {
                    "Maximum Limit Usage (%)": "max",
                    "Pass Rate (%)": "min",
                }
            )
        )
        voltages = sorted(
            grouped["Set Voltage (V)"].drop_duplicates(),
            key=self._sort_key,
        )
        currents = sorted(
            grouped["Set Current (A)"].drop_duplicates(),
            key=self._sort_key,
        )
        voltage_positions = {
            value: index for index, value in enumerate(voltages)
        }
        current_positions = {
            value: index for index, value in enumerate(currents)
        }
        spots = []
        for _, row in grouped.iterrows():
            voltage = row["Set Voltage (V)"]
            current = row["Set Current (A)"]
            usage = float(row["Maximum Limit Usage (%)"])
            passed = float(row["Pass Rate (%)"])
            spots.append(
                {
                    "pos": (
                        voltage_positions[voltage],
                        current_positions[current],
                    ),
                    "symbol": "s",
                    "size": 34,
                    "brush": pg.mkBrush(self._usage_color(usage)),
                    "pen": pg.mkPen("#ffffff", width=1),
                    "data": {
                        "kind": "heatmap",
                        "voltage": voltage,
                        "current": current,
                        "usage": usage,
                        "pass_rate": passed,
                    },
                }
            )
            if len(grouped) <= MAX_HEATMAP_LABELS:
                label = pg.TextItem(
                    f"{usage:.1f}%",
                    color="#ffffff",
                    anchor=(0.5, 0.5),
                )
                label.setPos(
                    voltage_positions[voltage],
                    current_positions[current],
                )
                self.heatmap.addItem(label)
        scatter = pg.ScatterPlotItem(spots=spots, hoverable=True)
        scatter.sigHovered.connect(self._show_hovered_points)
        self.heatmap.addItem(scatter)
        self.heatmap.getAxis("bottom").setTicks(
            [[
                (index, self._format_filter_value(value))
                for index, value in enumerate(voltages)
            ]]
        )
        self.heatmap.getAxis("left").setTicks(
            [[
                (index, self._format_filter_value(value))
                for index, value in enumerate(currents)
            ]]
        )

    def _update_confidence_plot(self, summary):
        self.confidence_plot.clear()
        self.confidence_plot.setLabel("bottom", "Channel / Test Condition")
        self.confidence_plot.setLabel("left", "Mean Error")
        self.confidence_plot.addItem(
            pg.InfiniteLine(
                pos=0.0,
                angle=0,
                pen=pg.mkPen("#666666", width=1, style=Qt.DashLine),
            )
        )
        if summary.empty:
            return
        ordered = summary.sort_values(
            "Maximum Limit Usage (%)",
            ascending=False,
        ).head(MAX_CONFIDENCE_POINTS).reset_index(drop=True)
        if len(summary) > MAX_CONFIDENCE_POINTS:
            self.hover_label.setText(
                f"Confidence plot shows the {MAX_CONFIDENCE_POINTS} "
                "conditions with highest limit usage. Use filters to inspect "
                "a specific channel or setpoint."
            )
        x_values = list(range(len(ordered)))
        labels = []
        for index, row in ordered.iterrows():
            labels.append(
                (
                    index,
                    f"Ch {row['Channel']}\n"
                    f"{row['Set Voltage (V)']:.4g}V/"
                    f"{row['Set Current (A)']:.4g}A",
                )
            )
        self.confidence_plot.getAxis("bottom").setTicks([labels])

        for color_index, (channel, channel_rows) in enumerate(
            ordered.groupby("Channel", sort=False)
        ):
            color = CHANNEL_COLORS[color_index % len(CHANNEL_COLORS)]
            positions = channel_rows.index.to_numpy(dtype=float)
            means = channel_rows["Mean Error"].to_numpy(dtype=float)
            ci_lower = channel_rows["95% CI Lower"].to_numpy(dtype=float)
            ci_upper = channel_rows["95% CI Upper"].to_numpy(dtype=float)
            finite = [
                index
                for index, (lower, upper) in enumerate(
                    zip(ci_lower, ci_upper)
                )
                if math.isfinite(lower) and math.isfinite(upper)
            ]
            if finite:
                self.confidence_plot.addItem(
                    pg.ErrorBarItem(
                        x=positions[finite],
                        y=means[finite],
                        top=ci_upper[finite] - means[finite],
                        bottom=means[finite] - ci_lower[finite],
                        beam=0.25,
                        pen=pg.mkPen(color, width=2),
                    )
                )
            spots = []
            for position, (_, row) in zip(positions, channel_rows.iterrows()):
                spots.append(
                    {
                        "pos": (position, float(row["Mean Error"])),
                        "size": 10,
                        "brush": pg.mkBrush(color),
                        "pen": pg.mkPen("#ffffff", width=1),
                        "data": {
                            "kind": "confidence",
                            "channel": channel,
                            "voltage": row["Set Voltage (V)"],
                            "current": row["Set Current (A)"],
                            "metric": row["Metric"],
                            "mean": row["Mean Error"],
                            "ci_lower": row["95% CI Lower"],
                            "ci_upper": row["95% CI Upper"],
                            "lower_limit": row["Lower Limit"],
                            "upper_limit": row["Upper Limit"],
                            "conclusion": row["Compliance Conclusion"],
                        },
                    }
                )
            scatter = pg.ScatterPlotItem(spots=spots, hoverable=True)
            scatter.sigHovered.connect(self._show_hovered_points)
            self.confidence_plot.addItem(scatter)
        self.confidence_plot.plot(
            x_values,
            ordered["Upper Limit"].to_numpy(dtype=float),
            pen=pg.mkPen("#b22222", width=2),
            symbol="t",
            symbolSize=7,
            symbolBrush="#b22222",
        )
        self.confidence_plot.plot(
            x_values,
            ordered["Lower Limit"].to_numpy(dtype=float),
            pen=pg.mkPen("#b22222", width=2, style=Qt.DashLine),
            symbol="t1",
            symbolSize=7,
            symbolBrush="#b22222",
        )

    @staticmethod
    def _difference_color(signed_usage, threshold):
        if signed_usage >= threshold:
            return "#d73027"
        if signed_usage <= -threshold:
            return "#4575b4"
        return "#91cf60"

    def _update_channel_difference_plot(self, comparisons):
        self.channel_difference_plot.clear()
        self.channel_difference_plot.setLabel(
            "bottom",
            "Set Voltage",
            units="V",
        )
        self.channel_difference_plot.setLabel(
            "left",
            "Load Current",
            units="A",
        )
        if comparisons.empty:
            return
        selected_rows = []
        for _, group in comparisons.groupby(
            ["Set Voltage (V)", "Set Current (A)"],
            dropna=False,
            sort=False,
        ):
            index = group["Difference Limit Usage (%)"].abs().idxmax()
            selected_rows.append(comparisons.loc[index])
        grouped = pd.DataFrame(selected_rows)
        voltages = sorted(
            grouped["Set Voltage (V)"].drop_duplicates(),
            key=self._sort_key,
        )
        currents = sorted(
            grouped["Set Current (A)"].drop_duplicates(),
            key=self._sort_key,
        )
        voltage_positions = {
            value: index for index, value in enumerate(voltages)
        }
        current_positions = {
            value: index for index, value in enumerate(currents)
        }
        spots = []
        for _, row in grouped.iterrows():
            difference = float(row["Mean Difference (A-B)"])
            usage = float(row["Difference Limit Usage (%)"])
            signed_usage = math.copysign(usage, difference)
            threshold = float(row["Practical Threshold (%)"])
            voltage = row["Set Voltage (V)"]
            current = row["Set Current (A)"]
            spots.append(
                {
                    "pos": (
                        voltage_positions[voltage],
                        current_positions[current],
                    ),
                    "symbol": "s",
                    "size": 34,
                    "brush": pg.mkBrush(
                        self._difference_color(
                            signed_usage,
                            threshold,
                        )
                    ),
                    "pen": pg.mkPen("#ffffff", width=1),
                    "data": {
                        "kind": "channel_difference",
                        "voltage": voltage,
                        "current": current,
                        "channel_a": row["Channel A"],
                        "channel_b": row["Channel B"],
                        "metric": row["Metric"],
                        "difference": difference,
                        "signed_usage": signed_usage,
                        "threshold": threshold,
                        "detected": row["Difference Detected"],
                        "evidence": row["Evidence Strength"],
                        "conclusion": row["Conclusion"],
                    },
                }
            )
            if len(grouped) <= MAX_HEATMAP_LABELS:
                label = pg.TextItem(
                    f"{signed_usage:+.1f}%",
                    color="#ffffff",
                    anchor=(0.5, 0.5),
                )
                label.setPos(
                    voltage_positions[voltage],
                    current_positions[current],
                )
                self.channel_difference_plot.addItem(label)
        scatter = pg.ScatterPlotItem(spots=spots, hoverable=True)
        scatter.sigHovered.connect(self._show_hovered_points)
        self.channel_difference_plot.addItem(scatter)
        self.channel_difference_plot.getAxis("bottom").setTicks(
            [[
                (index, self._format_filter_value(value))
                for index, value in enumerate(voltages)
            ]]
        )
        self.channel_difference_plot.getAxis("left").setTicks(
            [[
                (index, self._format_filter_value(value))
                for index, value in enumerate(currents)
            ]]
        )

    def _update_loop_plot(self, loops):
        self.loop_plot.clear()
        self.loop_plot.setTitle(
            "Individual Error Trend by Loop (no loop data)"
        )
        self.loop_plot.setLabel("bottom", "Loop Number")
        self.loop_plot.setLabel("left", "Mean Error")
        legend = self.loop_plot.addLegend(offset=(10, 10))
        if loops.empty:
            return
        loop_values = sorted(
            pd.to_numeric(loops["Loop"], errors="coerce")
            .dropna()
            .unique()
            .tolist()
        )
        self.loop_plot.setTitle(
            "Individual Error Trend by Loop "
            f"({len(loop_values)} loops detected)"
        )
        if len(loop_values) <= 20:
            self.loop_plot.getAxis("bottom").setTicks(
                [[
                    (
                        float(loop),
                        str(int(loop)) if float(loop).is_integer() else str(loop),
                    )
                    for loop in loop_values
                ]]
            )
        group_columns = (
            "Channel",
            "Set Voltage (V)",
            "Set Current (A)",
            "Metric",
        )
        grouped = list(
            loops.groupby(
                list(group_columns),
                dropna=False,
                sort=False,
            )
        )
        grouped.sort(
            key=lambda item: float(
                item[1]["Maximum Limit Usage (%)"].max()
                if "Maximum Limit Usage (%)" in item[1]
                else item[1]["Mean Error"].abs().max()
            ),
            reverse=True,
        )
        for color_index, (keys, group) in enumerate(
            grouped[:MAX_LOOP_SERIES]
        ):
            channel, voltage, current, metric = keys
            ordered = group.sort_values("Loop")
            color = CHANNEL_COLORS[color_index % len(CHANNEL_COLORS)]
            name = (
                f"Ch {channel} | {voltage:.4g} V / {current:.4g} A | "
                f"{metric.replace(' Error', '')}"
            )
            self.loop_plot.plot(
                ordered["Loop"].to_numpy(dtype=float),
                ordered["Mean Error"].to_numpy(dtype=float),
                pen=pg.mkPen(color, width=2),
                symbol="o",
                symbolSize=7,
                symbolBrush=color,
                name=name,
            )
        if legend is not None:
            legend.setLabelTextColor("#202020")
        self.loop_plot.enableAutoRange(x=True, y=True)
        self.loop_plot.autoRange()
        if len(grouped) > MAX_LOOP_SERIES:
            self.hover_label.setText(
                f"Loop plot shows the {MAX_LOOP_SERIES} conditions with "
                "highest specification-limit usage. Use filters to display other "
                "conditions."
            )

    def _update_comparison_trend_plot(self, loops, comparisons):
        self.comparison_trend_plot.clear()
        self.comparison_trend_plot.setLabel("bottom", "Loop Number")
        self.comparison_trend_plot.setLabel("left", "Mean Error A-B")
        self.comparison_trend_plot.addItem(
            pg.InfiniteLine(
                pos=0.0,
                angle=0,
                pen=pg.mkPen("#555555", width=1, style=Qt.DashLine),
            )
        )
        if loops.empty or comparisons.empty:
            self.comparison_trend_plot.setTitle(
                "Matched A-B Difference Trend by Loop (no matched data)"
            )
            return

        priority_column = "Comparison Priority Score"
        ordered_comparisons = (
            comparisons.sort_values(priority_column, ascending=False)
            if priority_column in comparisons.columns
            else comparisons
        )
        legend = self.comparison_trend_plot.addLegend(offset=(10, 10))
        plotted = 0
        loop_values = set()
        for _, comparison in ordered_comparisons.iterrows():
            condition_mask = (
                (loops["DUT"] == comparison["DUT"])
                & (loops["Test"] == comparison["Test"])
                & (
                    loops["Set Voltage (V)"]
                    == comparison["Set Voltage (V)"]
                )
                & (
                    loops["Set Current (A)"]
                    == comparison["Set Current (A)"]
                )
                & (loops["Metric"] == comparison["Metric"])
            )
            condition = loops.loc[condition_mask]
            comparison_basis = str(
                comparison.get("Comparison Basis", "Channel")
            )
            comparison_column = (
                "Run" if comparison_basis.lower() == "run" else "Channel"
            )
            left = condition.loc[
                condition[comparison_column] == comparison["Channel A"],
                ["Loop", "Mean Error"],
            ].rename(columns={"Mean Error": "Error A"})
            right = condition.loc[
                condition[comparison_column] == comparison["Channel B"],
                ["Loop", "Mean Error"],
            ].rename(columns={"Mean Error": "Error B"})
            matched = left.merge(right, on="Loop").sort_values("Loop")
            if matched.empty:
                continue
            matched["Difference"] = matched["Error A"] - matched["Error B"]
            color = CHANNEL_COLORS[plotted % len(CHANNEL_COLORS)]
            name = (
                f"{comparison_basis} {comparison['Channel A']}-"
                f"{comparison['Channel B']} | "
                f"{comparison['Set Voltage (V)']:.4g} V / "
                f"{comparison['Set Current (A)']:.4g} A | "
                f"{str(comparison['Metric']).replace(' Error', '')}"
            )
            self.comparison_trend_plot.plot(
                matched["Loop"].to_numpy(dtype=float),
                matched["Difference"].to_numpy(dtype=float),
                pen=pg.mkPen(color, width=2),
                symbol="o",
                symbolSize=7,
                symbolBrush=color,
                name=name,
            )
            loop_values.update(matched["Loop"].tolist())
            plotted += 1
            if plotted >= MAX_LOOP_SERIES:
                break

        self.comparison_trend_plot.setTitle(
            "Matched A-B Difference Trend by Loop "
            f"({len(loop_values)} loops detected)"
        )
        if legend is not None:
            legend.setLabelTextColor("#202020")
        if len(loop_values) <= 20:
            self.comparison_trend_plot.getAxis("bottom").setTicks(
                [[
                    (
                        float(loop),
                        str(int(loop))
                        if float(loop).is_integer()
                        else str(loop),
                    )
                    for loop in sorted(loop_values)
                ]]
            )
        self.comparison_trend_plot.enableAutoRange(x=True, y=True)
        self.comparison_trend_plot.autoRange()

    def _show_hovered_points(self, _item, points, _event):
        if not points:
            return
        data = points[0].data()
        if not data:
            return
        if data["kind"] == "heatmap":
            text = (
                f"Condition: {data['voltage']:.6g} V / "
                f"{data['current']:.6g} A | "
                f"Worst limit usage: {data['usage']:.2f}% | "
                f"Minimum pass rate: {data['pass_rate']:.2f}%"
            )
        elif data["kind"] == "channel_difference":
            text = (
                f"Channels {data['channel_a']} - {data['channel_b']} | "
                f"{data['voltage']:.6g} V / {data['current']:.6g} A | "
                f"{data['metric']} | Mean difference: "
                f"{data['difference']:.6g} | Limit usage: "
                f"{data['signed_usage']:+.2f}% | Practical threshold: "
                f"±{data['threshold']:.2f}% | Statistical difference: "
                f"{data['detected']} ({data['evidence']}) | "
                f"{data['conclusion']}"
            )
        else:
            ci_lower = data["ci_lower"]
            ci_upper = data["ci_upper"]
            interval = (
                f"[{ci_lower:.6g}, {ci_upper:.6g}]"
                if pd.notna(ci_lower) and pd.notna(ci_upper)
                else "N/A"
            )
            text = (
                f"Channel {data['channel']} | {data['voltage']:.6g} V / "
                f"{data['current']:.6g} A | {data['metric']} | "
                f"Mean: {data['mean']:.6g} | 95% CI: {interval} | "
                f"Limits: [{data['lower_limit']:.6g}, "
                f"{data['upper_limit']:.6g}] | {data['conclusion']}"
            )
        self.hover_label.setText(text)
