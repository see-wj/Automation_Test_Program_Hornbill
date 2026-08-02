import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from PyQt5.QtWidgets import QApplication

from instruments.waveform_anomaly import (
    WaveformFolderAnalyzerDialog,
    WaveformImageAnalyzer,
    analyze_waveform_folder,
    discover_waveform_images,
)


class WaveformImageAnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def _image(path, trace_bounds=None):
        image = Image.new("RGB", (800, 632), "black")
        if trace_bounds is not None:
            ImageDraw.Draw(image).rectangle(trace_bounds, fill=(0, 220, 0))
        image.save(path)

    def test_narrow_trace_is_normal(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            image_path = Path(temporary_directory) / "normal.png"
            self._image(image_path, (96, 330, 647, 336))

            result = WaveformImageAnalyzer().analyze(image_path, 2)

        self.assertEqual("NORMAL", result.status)
        self.assertEqual(0, result.score)
        self.assertGreater(result.trace_coverage, 0.95)
        self.assertIsNone(result.highlighted_path)

    def test_broad_trace_is_highlighted_without_changing_original(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            image_path = root / "broad.png"
            highlighted_directory = root / "abnormal"
            self._image(image_path, (96, 260, 647, 380))
            original_data = image_path.read_bytes()

            result = WaveformImageAnalyzer().analyze(
                image_path,
                2,
                highlighted_directory,
            )

            self.assertEqual("ABNORMAL", result.status)
            self.assertIn("waveform envelope is unusually broad", result.reasons)
            self.assertTrue(result.highlighted_path.is_file())
            self.assertEqual(original_data, image_path.read_bytes())

    def test_missing_selected_trace_is_highlighted(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            image_path = root / "missing.png"
            self._image(image_path)

            result = WaveformImageAnalyzer().analyze(
                image_path,
                2,
                root / "abnormal",
            )

        self.assertEqual("ABNORMAL", result.status)
        self.assertEqual(100, result.score)
        self.assertIn("selected channel trace is missing or unreadable", result.reasons)

    def test_folder_analysis_scans_recursively_and_writes_summary(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            normal_path = root / "normal.png"
            nested_directory = root / "nested"
            nested_directory.mkdir()
            abnormal_path = nested_directory / "abnormal.png"
            self._image(normal_path, (96, 330, 647, 336))
            self._image(abnormal_path, (96, 240, 647, 400))

            displayed_results = []
            summary = analyze_waveform_folder(
                root,
                2,
                result_callback=lambda image_path, result: displayed_results.append(
                    (image_path, result)
                ),
            )

            self.assertEqual(2, summary.total)
            self.assertEqual(1, summary.normal)
            self.assertEqual(1, summary.abnormal)
            self.assertTrue(summary.result_path.is_file())
            self.assertEqual(2, len(discover_waveform_images(root)))
            self.assertEqual(2, len(displayed_results))
            with summary.result_path.open(
                newline="", encoding="utf-8"
            ) as result_file:
                rows = list(csv.DictReader(result_file))

        self.assertCountEqual(
            ["NORMAL", "ABNORMAL"],
            [row["Status"] for row in rows],
        )

    def test_standalone_dialog_defaults_to_scope_channel_two(self):
        dialog = WaveformFolderAnalyzerDialog()
        try:
            self.assertEqual(2, dialog.scope_channel.value())
            self.assertEqual("Analyze Folder", dialog.start_button.text())
        finally:
            dialog.close()

    def test_dialog_displays_analyzed_image_and_details(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            image_path = root / "abnormal.png"
            self._image(image_path, (96, 240, 647, 400))
            payload = {
                "image_path": str(image_path),
                "display_path": str(image_path),
                "status": "ABNORMAL",
                "score": 80,
                "reasons": ("large vertical spikes are visible",),
            }
            dialog = WaveformFolderAnalyzerDialog()
            try:
                dialog._result_ready(payload)

                self.assertEqual(1, dialog.result_list.count())
                self.assertFalse(dialog.preview_label.pixmap().isNull())
                self.assertIn("large vertical spikes", dialog.preview_details.text())
                self.assertEqual("1", dialog.total_value.text())
                self.assertEqual("1", dialog.abnormal_value.text())
                self.assertEqual("0", dialog.normal_value.text())
            finally:
                dialog.close()


if __name__ == "__main__":
    unittest.main()
