"""Explainable visual anomaly detection for oscilloscope screenshots."""

import csv
import re
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class WaveformAnalysisResult:
    status: str
    score: int
    reasons: tuple[str, ...]
    trace_coverage: float
    trace_occupancy: float
    median_envelope_height: float
    p95_envelope_height: float
    vertical_fill: float
    highlighted_path: Path | None = None


@dataclass(frozen=True)
class FolderAnalysisSummary:
    total: int
    normal: int
    abnormal: int
    errors: int
    result_path: Path
    highlighted_directory: Path


class WaveformAnalysisStopped(RuntimeError):
    pass


class WaveformImageAnalyzer:
    """Detect visually unusual trace shapes without interpreting measurements."""

    _PLOT_BOUNDS = (0.12, 0.15, 0.81, 0.88)

    @staticmethod
    def _channel_mask(pixels, scope_channel):
        red = pixels[:, :, 0].astype(np.int16)
        green = pixels[:, :, 1].astype(np.int16)
        blue = pixels[:, :, 2].astype(np.int16)
        color_index = (int(scope_channel) - 1) % 4

        if color_index == 0:
            return (
                (red > 120)
                & (green > 105)
                & (blue < 120)
                & (red > blue * 1.25)
                & (green > blue * 1.15)
            )
        if color_index == 1:
            return (
                (green > 70)
                & (green > red * 1.35)
                & (green > blue * 1.25)
            )
        if color_index == 2:
            return (
                (blue > 70)
                & (blue > red * 1.25)
                & (blue > green * 1.10)
            )
        return (
            (red > 90)
            & (blue > 70)
            & (red > green * 1.25)
            & (blue > green * 1.15)
        )

    @classmethod
    def _plot_region(cls, image):
        width, height = image.size
        left_ratio, top_ratio, right_ratio, bottom_ratio = cls._PLOT_BOUNDS
        bounds = (
            int(width * left_ratio),
            int(height * top_ratio),
            int(width * right_ratio),
            int(height * bottom_ratio),
        )
        return bounds, np.asarray(image.crop(bounds).convert("RGB"))

    @staticmethod
    def _features(mask):
        plot_height, plot_width = mask.shape
        active_columns = np.flatnonzero(mask.any(axis=0))
        coverage = float(len(active_columns) / plot_width)
        occupancy = float(mask.mean())
        if not len(active_columns):
            return coverage, occupancy, 0.0, 0.0, 0.0, None

        envelope_heights = []
        for column_index in active_columns:
            row_indices = np.flatnonzero(mask[:, column_index])
            envelope_heights.append(row_indices[-1] - row_indices[0] + 1)

        mask_rows, mask_columns = np.where(mask)
        median_envelope = float(np.median(envelope_heights) / plot_height)
        p95_envelope = float(np.percentile(envelope_heights, 95) / plot_height)
        vertical_fill = float(
            (mask_rows.max() - mask_rows.min() + 1) / plot_height
        )
        trace_bounds = (
            int(mask_columns.min()),
            int(mask_rows.min()),
            int(mask_columns.max()),
            int(mask_rows.max()),
        )
        return (
            coverage,
            occupancy,
            median_envelope,
            p95_envelope,
            vertical_fill,
            trace_bounds,
        )

    @staticmethod
    def _classify(features):
        coverage, occupancy, median_envelope, p95_envelope, vertical_fill, _ = (
            features
        )
        reasons = []
        score = 0
        if coverage < 0.20:
            reasons.append("selected channel trace is missing or unreadable")
            score += 100
        else:
            if occupancy >= 0.30:
                reasons.append("trace saturates a large part of the plot")
                score += 60
            if median_envelope >= 0.18:
                reasons.append("waveform envelope is unusually broad")
                score += 45
            if p95_envelope >= 0.45:
                reasons.append("large vertical spikes are visible")
                score += 35
            if vertical_fill >= 0.95:
                reasons.append("trace reaches both plot boundaries")
                score += 25

        score = min(100, score)
        status = "ABNORMAL" if score >= 40 else "NORMAL"
        return status, score, tuple(reasons)

    @staticmethod
    def _highlight(image, plot_bounds, trace_bounds, reasons, destination):
        highlighted = image.copy()
        draw = ImageDraw.Draw(highlighted)
        left, top, right, bottom = plot_bounds
        if trace_bounds is None:
            rectangle = (left, top, right, bottom)
        else:
            trace_left, trace_top, trace_right, trace_bottom = trace_bounds
            padding = 6
            rectangle = (
                max(left, left + trace_left - padding),
                max(top, top + trace_top - padding),
                min(right, left + trace_right + padding),
                min(bottom, top + trace_bottom + padding),
            )
        draw.rectangle(rectangle, outline=(255, 0, 0), width=5)

        label = "ABNORMAL: " + "; ".join(reasons)
        label = label[:120]
        text_bounds = draw.textbbox((0, 0), label)
        text_width = text_bounds[2] - text_bounds[0]
        text_height = text_bounds[3] - text_bounds[1]
        label_right = min(highlighted.width - 1, left + text_width + 12)
        label_bottom = min(highlighted.height - 1, top + text_height + 10)
        draw.rectangle(
            (left, top, label_right, label_bottom),
            fill=(180, 0, 0),
        )
        draw.text((left + 6, top + 4), label, fill=(255, 255, 255))
        destination.parent.mkdir(parents=True, exist_ok=True)
        highlighted.save(destination, format="PNG")

    def analyze(self, image_path, scope_channel, highlighted_directory=None):
        image_path = Path(image_path)
        with Image.open(image_path) as source_image:
            image = source_image.convert("RGB")
        plot_bounds, plot_pixels = self._plot_region(image)
        mask = self._channel_mask(plot_pixels, scope_channel)
        features = self._features(mask)
        status, score, reasons = self._classify(features)
        highlighted_path = None

        if status == "ABNORMAL" and highlighted_directory is not None:
            highlighted_path = (
                Path(highlighted_directory)
                / f"{image_path.stem}_ABNORMAL.png"
            )
            self._highlight(
                image,
                plot_bounds,
                features[-1],
                reasons,
                highlighted_path,
            )

        return WaveformAnalysisResult(
            status=status,
            score=score,
            reasons=reasons,
            trace_coverage=features[0],
            trace_occupancy=features[1],
            median_envelope_height=features[2],
            p95_envelope_height=features[3],
            vertical_fill=features[4],
            highlighted_path=highlighted_path,
        )


def _natural_path_key(path):
    return tuple(
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", str(path))
    )


def discover_waveform_images(folder):
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("Select a folder containing oscilloscope PNG images")
    output_directory = folder / "waveform_anomaly_analysis"
    images = (
        path
        for path in folder.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".png"
        and output_directory not in path.parents
        and not path.stem.upper().endswith("_ABNORMAL")
    )
    return tuple(sorted(images, key=_natural_path_key))


def analyze_waveform_folder(
    folder,
    scope_channel,
    analyzer=None,
    progress_callback=None,
    result_callback=None,
    stop_requested=None,
):
    folder = Path(folder)
    images = discover_waveform_images(folder)
    if not images:
        raise ValueError("No PNG oscilloscope images were found in the selected folder")

    analyzer = analyzer or WaveformImageAnalyzer()
    output_directory = folder / "waveform_anomaly_analysis"
    highlighted_directory = output_directory / "abnormal_waveforms"
    output_directory.mkdir(parents=True, exist_ok=True)
    highlighted_directory.mkdir(parents=True, exist_ok=True)
    result_path = output_directory / "waveform_anomaly_results.csv"
    fieldnames = (
        "Image",
        "Scope Channel",
        "Status",
        "Anomaly Score",
        "Reasons",
        "Trace Coverage",
        "Trace Occupancy",
        "Median Envelope Height",
        "P95 Envelope Height",
        "Vertical Fill",
        "Highlighted Image",
    )
    normal_count = 0
    abnormal_count = 0
    error_count = 0

    with result_path.open("w", newline="", encoding="utf-8") as result_file:
        writer = csv.DictWriter(result_file, fieldnames=fieldnames)
        writer.writeheader()
        for index, image_path in enumerate(images, start=1):
            if stop_requested is not None and stop_requested():
                raise WaveformAnalysisStopped("Waveform folder analysis stopped")
            try:
                result = analyzer.analyze(
                    image_path,
                    scope_channel,
                    highlighted_directory,
                )
                if result.status == "ABNORMAL":
                    abnormal_count += 1
                else:
                    normal_count += 1
                writer.writerow(
                    {
                        "Image": str(image_path),
                        "Scope Channel": scope_channel,
                        "Status": result.status,
                        "Anomaly Score": result.score,
                        "Reasons": "; ".join(result.reasons),
                        "Trace Coverage": result.trace_coverage,
                        "Trace Occupancy": result.trace_occupancy,
                        "Median Envelope Height": result.median_envelope_height,
                        "P95 Envelope Height": result.p95_envelope_height,
                        "Vertical Fill": result.vertical_fill,
                        "Highlighted Image": str(result.highlighted_path or ""),
                    }
                )
                message = f"{result.status}: {image_path.name}"
                if result.reasons:
                    message += f" - {'; '.join(result.reasons)}"
                if result_callback is not None:
                    result_callback(image_path, result)
            except Exception as exception:
                error_count += 1
                writer.writerow(
                    {
                        "Image": str(image_path),
                        "Scope Channel": scope_channel,
                        "Status": "ANALYSIS_ERROR",
                        "Anomaly Score": "",
                        "Reasons": str(exception),
                        "Highlighted Image": "",
                    }
                )
                message = f"ANALYSIS_ERROR: {image_path.name} - {exception}"
            result_file.flush()
            if progress_callback is not None:
                progress_callback(index, len(images), message)

    return FolderAnalysisSummary(
        total=len(images),
        normal=normal_count,
        abnormal=abnormal_count,
        errors=error_count,
        result_path=result_path,
        highlighted_directory=highlighted_directory,
    )


class WaveformFolderAnalysisWorker(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    completed = pyqtSignal(object)
    stopped = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, folder, scope_channel, parent=None):
        super().__init__(parent)
        self.folder = Path(folder)
        self.scope_channel = int(scope_channel)
        self._stop_requested = threading.Event()

    def stop(self):
        self._stop_requested.set()

    def _progress(self, completed, total, message):
        self.progress.emit(int(completed * 100 / total))
        self.message.emit(message)

    def _result(self, image_path, result):
        self.result_ready.emit(
            {
                "image_path": str(image_path),
                "display_path": str(result.highlighted_path or image_path),
                "status": result.status,
                "score": result.score,
                "reasons": tuple(result.reasons),
            }
        )

    def run(self):
        try:
            summary = analyze_waveform_folder(
                self.folder,
                self.scope_channel,
                progress_callback=self._progress,
                result_callback=self._result,
                stop_requested=self._stop_requested.is_set,
            )
            self.completed.emit(summary)
        except WaveformAnalysisStopped:
            self.stopped.emit()
        except Exception as exception:
            self.message.emit(f"ERROR: {exception}\n{traceback.format_exc()}")
            self.error.emit(str(exception))


class WaveformFolderAnalyzerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Waveform Image Anomaly Analyzer")
        self.resize(1180, 760)
        self.worker = None
        self._preview_pixmap = None
        self._result_counts = {"total": 0, "normal": 0, "abnormal": 0, "errors": 0}

        title = QLabel("Waveform Anomaly Studio")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Review oscilloscope captures, detect visual anomalies, and inspect "
            "highlighted evidence without changing the original images."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        header_layout = QVBoxLayout()
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_card.setLayout(header_layout)

        self.folder = QLineEdit()
        self.folder.setPlaceholderText("Folder containing oscilloscope PNG images")
        browse_button = QPushButton("Browse...")
        browse_button.setObjectName("secondaryButton")
        browse_button.clicked.connect(self._browse)
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder)
        folder_layout.addWidget(browse_button)

        self.scope_channel = QSpinBox()
        self.scope_channel.setRange(1, 4)
        self.scope_channel.setValue(2)
        self.scope_channel.setToolTip(
            "Select the oscilloscope channel whose colored trace is analyzed."
        )

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow("Image Folder:", folder_layout)
        form.addRow("Scope Channel:", self.scope_channel)

        self.start_button = QPushButton("Analyze Folder")
        self.start_button.setObjectName("primaryButton")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self._start)
        self.stop_button.clicked.connect(self._stop)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch(1)

        settings_layout = QVBoxLayout()
        settings_layout.addLayout(form)
        settings_layout.addLayout(button_layout)
        settings_card = QFrame()
        settings_card.setObjectName("panelCard")
        settings_card.setLayout(settings_layout)

        stats_layout = QGridLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setHorizontalSpacing(12)
        self.total_value = self._create_stat_card(
            stats_layout, 0, "TOTAL IMAGES", "#2563eb"
        )
        self.normal_value = self._create_stat_card(
            stats_layout, 1, "NORMAL", "#16a34a"
        )
        self.abnormal_value = self._create_stat_card(
            stats_layout, 2, "ABNORMAL", "#dc2626"
        )
        self.error_value = self._create_stat_card(
            stats_layout, 3, "ERRORS", "#d97706"
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status = QLabel(
            "Ready. Original screenshots are preserved; only abnormal copies "
            "receive red highlighting."
        )
        self.status.setObjectName("statusPill")
        self.status.setWordWrap(True)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)

        self.result_list = QListWidget()
        self.result_list.setObjectName("resultList")
        self.result_list.setMinimumWidth(330)
        self.result_list.currentItemChanged.connect(self._show_selected_image)
        self.preview_label = QLabel("Analyzed images will appear here")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(560, 400)
        self.preview_label.setStyleSheet(
            "QLabel { background: #08111f; color: #94a3b8; "
            "border: 1px solid #26364d; border-radius: 10px; }"
        )
        self.preview_details = QLabel("Select a result to view its details.")
        self.preview_details.setObjectName("previewDetails")
        self.preview_details.setWordWrap(True)
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self.preview_label, stretch=1)
        preview_layout.addWidget(self.preview_details)
        preview_widget = QWidget()
        preview_widget.setLayout(preview_layout)

        result_splitter = QSplitter(Qt.Horizontal)
        result_splitter.setObjectName("resultSplitter")
        result_splitter.addWidget(self.result_list)
        result_splitter.addWidget(preview_widget)
        result_splitter.setSizes((340, 800))

        results_title = QLabel("Analysis Results")
        results_title.setObjectName("sectionTitle")
        log_title = QLabel("Activity Log")
        log_title.setObjectName("sectionTitle")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)
        layout.addWidget(header_card)
        layout.addWidget(settings_card)
        layout.addLayout(stats_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status)
        layout.addWidget(results_title)
        layout.addWidget(result_splitter, stretch=1)
        layout.addWidget(log_title)
        layout.addWidget(self.log)
        self._apply_theme()
        self._set_status(self.status.text(), "ready")

    @staticmethod
    def _create_stat_card(layout, column, caption, accent):
        value = QLabel("0")
        value.setObjectName("statValue")
        value.setStyleSheet(f"color: {accent};")
        caption_label = QLabel(caption)
        caption_label.setObjectName("statCaption")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 10, 16, 10)
        card_layout.addWidget(value)
        card_layout.addWidget(caption_label)
        card = QFrame()
        card.setObjectName("statCard")
        card.setStyleSheet(
            f"QFrame#statCard {{ border-left: 5px solid {accent}; }}"
        )
        card.setLayout(card_layout)
        layout.addWidget(card, 0, column)
        return value

    def _apply_theme(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #eef3f9;
                color: #172033;
                font-size: 13px;
            }
            QFrame#headerCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #17365d, stop:1 #2563a5);
                border-radius: 12px;
            }
            QLabel#pageTitle {
                color: white;
                font-size: 25px;
                font-weight: 700;
            }
            QLabel#pageSubtitle { color: #dbeafe; font-size: 13px; }
            QFrame#panelCard, QFrame#statCard {
                background: white;
                border: 1px solid #d8e1ec;
                border-radius: 10px;
            }
            QLabel#statValue { font-size: 24px; font-weight: 700; }
            QLabel#statCaption {
                color: #64748b;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#sectionTitle {
                color: #263a55;
                font-size: 15px;
                font-weight: 700;
            }
            QLineEdit, QSpinBox {
                background: white;
                border: 1px solid #b9c7d8;
                border-radius: 7px;
                padding: 8px;
                selection-background-color: #2563eb;
            }
            QLineEdit:focus, QSpinBox:focus { border: 2px solid #3b82f6; }
            QPushButton {
                border: none;
                border-radius: 7px;
                padding: 9px 18px;
                font-weight: 700;
            }
            QPushButton#primaryButton { background: #2563eb; color: white; }
            QPushButton#primaryButton:hover { background: #1d4ed8; }
            QPushButton#secondaryButton { background: #e2e8f0; color: #334155; }
            QPushButton#secondaryButton:hover { background: #cbd5e1; }
            QPushButton#dangerButton { background: #fee2e2; color: #b91c1c; }
            QPushButton#dangerButton:hover { background: #fecaca; }
            QPushButton:disabled { background: #dbe3ed; color: #8492a6; }
            QProgressBar {
                background: #dce5f0;
                border: none;
                border-radius: 6px;
                height: 12px;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk { background: #3b82f6; border-radius: 6px; }
            QLabel#statusPill { border-radius: 7px; padding: 9px 12px; }
            QListWidget#resultList {
                background: white;
                border: 1px solid #ced9e6;
                border-radius: 9px;
                padding: 6px;
                outline: none;
            }
            QListWidget#resultList::item {
                border-bottom: 1px solid #edf1f6;
                border-radius: 5px;
                padding: 10px 8px;
                margin: 2px;
            }
            QListWidget#resultList::item:selected {
                background: #dbeafe;
                color: #17365d;
            }
            QLabel#previewDetails {
                background: white;
                border: 1px solid #d8e1ec;
                border-radius: 8px;
                padding: 10px;
                color: #334155;
            }
            QTextEdit {
                background: #0f172a;
                color: #cbd5e1;
                border: 1px solid #26364d;
                border-radius: 8px;
                padding: 7px;
                font-family: Consolas;
                font-size: 11px;
            }
            QSplitter::handle { background: #cbd5e1; width: 5px; }
            """
        )

    def _set_status(self, text, state):
        palette = {
            "ready": ("#e0f2fe", "#075985"),
            "running": ("#dbeafe", "#1d4ed8"),
            "success": ("#dcfce7", "#166534"),
            "warning": ("#fef3c7", "#92400e"),
            "error": ("#fee2e2", "#991b1b"),
        }
        background, foreground = palette[state]
        self.status.setText(text)
        self.status.setStyleSheet(
            f"background: {background}; color: {foreground}; "
            "border-radius: 7px; padding: 9px 12px; font-weight: 600;"
        )

    def _update_stat_cards(self):
        self.total_value.setText(str(self._result_counts["total"]))
        self.normal_value.setText(str(self._result_counts["normal"]))
        self.abnormal_value.setText(str(self._result_counts["abnormal"]))
        self.error_value.setText(str(self._result_counts["errors"]))

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Oscilloscope Image Folder",
            self.folder.text().strip(),
        )
        if folder:
            self.folder.setText(folder)

    def _start(self):
        folder = self.folder.text().strip()
        try:
            images = discover_waveform_images(folder)
            if not images:
                raise ValueError(
                    "No PNG oscilloscope images were found in the selected folder"
                )
        except ValueError as exception:
            QMessageBox.warning(self, "Invalid Image Folder", str(exception))
            return

        self.log.clear()
        self.result_list.clear()
        self._result_counts = {"total": 0, "normal": 0, "abnormal": 0, "errors": 0}
        self._update_stat_cards()
        self._preview_pixmap = None
        self.preview_label.clear()
        self.preview_label.setText("Waiting for analyzed images...")
        self.preview_details.setText("Analysis is running.")
        self.progress_bar.setValue(0)
        self._set_status(f"Analyzing {len(images)} image(s)...", "running")
        self.worker = WaveformFolderAnalysisWorker(
            folder,
            self.scope_channel.value(),
            self,
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.message.connect(self.log.append)
        self.worker.result_ready.connect(self._result_ready)
        self.worker.completed.connect(self._completed)
        self.worker.stopped.connect(self._stopped)
        self.worker.error.connect(self._error)
        self.worker.finished.connect(self._finished)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.worker.start()

    def _result_ready(self, payload):
        status = payload["status"]
        score = payload["score"]
        image_name = Path(payload["image_path"]).name
        marker = "●"
        item = QListWidgetItem(f"{marker}  {status}  [{score:3d}]  {image_name}")
        item.setData(Qt.UserRole, payload["display_path"])
        item.setData(Qt.UserRole + 1, payload)
        item.setForeground(
            QColor("#d32f2f") if status == "ABNORMAL" else QColor("#2e7d32")
        )
        self.result_list.addItem(item)
        self._result_counts["total"] += 1
        self._result_counts[status.lower()] += 1
        self._update_stat_cards()
        if self.result_list.count() == 1 or status == "ABNORMAL":
            self.result_list.setCurrentItem(item)

    def _show_selected_image(self, item, _previous=None):
        if item is None:
            return
        payload = item.data(Qt.UserRole + 1)
        image_path = item.data(Qt.UserRole)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self._preview_pixmap = None
            self.preview_label.setText(f"Unable to display image:\n{image_path}")
            return
        self._preview_pixmap = pixmap
        self._update_preview()
        reasons = "; ".join(payload["reasons"]) or "No visual anomaly detected"
        self.preview_details.setText(
            f"{payload['status']} | Score: {payload['score']} | "
            f"{Path(payload['image_path']).name}\n{reasons}"
        )
        detail_color = "#dc2626" if payload["status"] == "ABNORMAL" else "#16a34a"
        self.preview_details.setStyleSheet(
            f"border-left: 5px solid {detail_color};"
        )

    def _update_preview(self):
        if self._preview_pixmap is None:
            return
        self.preview_label.setPixmap(
            self._preview_pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _stop(self):
        if self.worker is not None:
            self.worker.stop()
            self.stop_button.setEnabled(False)
            self._set_status("Stop requested...", "warning")

    def _completed(self, summary):
        self.progress_bar.setValue(100)
        self._result_counts = {
            "total": summary.total,
            "normal": summary.normal,
            "abnormal": summary.abnormal,
            "errors": summary.errors,
        }
        self._update_stat_cards()
        self._set_status(
            f"Completed: {summary.total} analyzed, {summary.abnormal} abnormal, "
            f"{summary.normal} normal, {summary.errors} error(s). Results: "
            f"{summary.result_path}",
            "success" if not summary.errors else "warning",
        )

    def _stopped(self):
        self._set_status("Waveform image analysis stopped.", "warning")

    def _error(self, message):
        self._set_status("Waveform image analysis failed.", "error")
        QMessageBox.critical(self, "Waveform Analysis Error", message)

    def _finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.worker = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_preview()

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
        super().closeEvent(event)
