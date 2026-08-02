import json
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from io import BytesIO, TextIOWrapper
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QApplication, QMessageBox

import GUI
from ui import all_test_dialog
from queueing.queue_persistence import QueuePersistence
from execution.run_storage import create_run_storage
from execution.test_run_controller import TestRunRequest


class DummySignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in tuple(self.callbacks):
            callback(*args)


class DummyWorker:
    def __init__(self, checkbox_states=None, configuration=None, parameters=None):
        self.checkbox_states = checkbox_states
        self.configuration = configuration
        self.parameters = parameters
        self.running = False
        self.pause_calls = 0
        self.resume_calls = 0
        self.stop_calls = 0
        self.deleted = False
        for signal_name in (
            "progress",
            "progress_value",
            "finished",
            "aborted",
            "error",
            "warning",
            "new_data",
            "temperature_data",
            "popup_data",
            "state_changed",
        ):
            setattr(self, signal_name, DummySignal())

    def start(self):
        self.running = True

    def isRunning(self):
        return self.running

    def pause(self):
        self.pause_calls += 1

    def resume(self):
        self.resume_calls += 1

    def request_stop(self):
        self.stop_calls += 1

    def deleteLater(self):
        self.deleted = True


class DummyPlotWindow:
    def __init__(self, *_args):
        pass

    def show(self):
        return None

    def popup_plot(self, *args):
        return None


class DummyRunContext:
    def __init__(self, storage, output_root, parameters):
        self.storage = storage
        self.output_root = Path(output_root)
        self.parameters = parameters
        self.data_index = 0
        self.realtime_rows = []
        self.voltage_chart = storage.charts / "Chart.png"
        self.voltage_percentage_chart = storage.charts / "Chart2.png"

    def open_realtime_csv(self, timestamp):
        return self.storage.raw / f"realtime_voltage_data_{timestamp}.csv"

    def close(self):
        return None

    def write_realtime_row(self, values):
        self.data_index += 1
        self.realtime_rows.append(tuple(values))

    def restore_parameter_paths(self):
        self.parameters.savelocation = str(self.output_root)


class GuiWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.queue_directory = tempfile.TemporaryDirectory()
        self.queue_file = Path(self.queue_directory.name) / "queue.json"
        self.dialog = GUI.AllTestMeasurement(queue_file=self.queue_file)
        self.dialog.QCheckBox_Image_Widget.setChecked(False)

    def tearDown(self):
        self.wait_for_instrument_discovery()
        self.dialog.worker = None
        self.dialog.close()
        self.dialog.deleteLater()
        self.application.processEvents()
        self.queue_directory.cleanup()

    def wait_for_instrument_discovery(self, timeout=2.0):
        deadline = time.monotonic() + timeout
        while (
            self.dialog.instrument_discovery_thread is not None
            and time.monotonic() < deadline
        ):
            self.application.processEvents()
            time.sleep(0.01)
        self.application.processEvents()
        self.assertIsNone(self.dialog.instrument_discovery_thread)

    def test_console_output_replaces_unsupported_windows_characters(self):
        raw_stream = BytesIO()
        stream = TextIOWrapper(raw_stream, encoding="cp1252")

        GUI.print_console_safe("✅ Measurement complete", stream=stream)
        stream.flush()

        self.assertEqual(
            raw_stream.getvalue().decode("cp1252").strip(),
            "? Measurement complete",
        )

    def test_ui_builders_assemble_expected_sections(self):
        self.assertEqual(self.dialog.layout().count(), 2)
        self.assertEqual(self.dialog.windowTitle(), "Bundle Test Control Center")
        self.assertEqual(self.dialog.dialog_tabs.objectName(), "bundleTabs")
        self.assertFalse(self.dialog.dialog_tabs.tabBar().expanding())
        self.assertEqual(
            self.dialog.Connection_group.title(),
            "Instrument Connections",
        )
        self.assertLessEqual(self.dialog.image_label.maximumWidth(), 360)
        self.assertLessEqual(self.dialog.image_label.maximumHeight(), 210)
        self.assertEqual(
            [
                self.dialog.dialog_tabs.tabText(index)
                for index in range(self.dialog.dialog_tabs.count())
            ],
            [
                "Test Setup",
                "Graph Plotting",
                "Temperature Plotting",
                "Webcam",
                "Data Analysis",
            ],
        )
        self.assertFalse(self.dialog.webcam_widget.preview_active)
        self.assertIsNotNone(self.dialog.Connection_group.layout())
        self.assertFalse(hasattr(self.dialog, "QPushButton_Widget2"))
        self.assertEqual(
            self.dialog.DMM_Settings_group.title(),
            "DMM Measurement Settings",
        )
        self.assertEqual(
            self.dialog.Auxiliary_group.title(),
            "Auxiliary Equipment",
        )
        self.assertIsNotNone(self.dialog.Auxiliary_group.layout())
        self.assertEqual(
            [
                self.dialog.QComboBox_Relay_Control.itemText(index)
                for index in range(self.dialog.QComboBox_Relay_Control.count())
            ],
            [
                "None",
                "Voltage Relay (Channel 3)",
                "Current Relay (Channel 2)",
                "Both Relays",
            ],
        )
        self.assertEqual(self.dialog.dialog_tabs.count(), 5)
        self.assertEqual(self.dialog.dialog_tabs.tabText(0), "Test Setup")
        self.assertEqual(self.dialog.dialog_tabs.tabText(1), "Graph Plotting")
        self.assertEqual(
            self.dialog.dialog_tabs.tabText(2),
            "Temperature Plotting",
        )
        self.assertEqual(self.dialog.dialog_tabs.tabText(3), "Webcam")
        self.assertEqual(self.dialog.dialog_tabs.tabText(4), "Data Analysis")

    def test_inline_dmm_settings_follow_selected_model(self):
        model_index = self.dialog.QComboBox_DMM_Model.findData("344xxA")
        self.dialog.QComboBox_DMM_Model.setCurrentIndex(model_index)
        self.dialog.QComboBox_344XXA_Range.setCurrentText("10V")
        self.dialog.QComboBox_344XXA_NPLC.setCurrentText("10")
        self.dialog.QComboBox_344XXA_AutoZero.setCurrentText("OFF")
        self.dialog.QComboBox_344XXA_InputZ.setCurrentIndex(0)

        self.assertEqual(self.dialog.params.DMM_Model, "344xxA")
        self.assertEqual(self.dialog.params.Range, "10V")
        self.assertEqual(self.dialog.params.Aperture, "10")
        self.assertEqual(self.dialog.params.AutoZero, "OFF")
        self.assertEqual(self.dialog.params.inputZ, "ON")
        self.assertFalse(self.dialog.DMM_344XXA_Settings_group.isHidden())
        self.assertTrue(self.dialog.DMM_3458A_Settings_group.isHidden())

        model_index = self.dialog.QComboBox_DMM_Model.findData("3458A")
        self.dialog.QComboBox_DMM_Model.setCurrentIndex(model_index)
        self.dialog.QComboBox_3458A_Range.setCurrentIndex(3)
        self.dialog.QComboBox_3458A_NPLC.setCurrentText("100")
        self.dialog.QComboBox_3458A_AutoZero.setCurrentText("ON")

        self.assertEqual(self.dialog.params.DMM_Model, "3458A")
        self.assertEqual(self.dialog.params.Range, "10")
        self.assertEqual(self.dialog.params.Aperture, "100")
        self.assertEqual(self.dialog.params.AutoZero, "ON")
        self.assertTrue(self.dialog.DMM_344XXA_Settings_group.isHidden())
        self.assertFalse(self.dialog.DMM_3458A_Settings_group.isHidden())

    def test_sinking_voltage_settings_are_only_shown_for_sinking_mode(self):
        self.assertTrue(self.dialog.Sinking_Test_group.isHidden())

        self.dialog.QCheckBox_Sinking_Test_Widget.setChecked(True)
        self.dialog.QLineEdit_Sinking_Initial_Voltage.setText("10")
        self.dialog.QLineEdit_Sinking_Initial_Voltage.textEdited.emit("10")
        self.dialog.QLineEdit_Sinking_Final_Voltage.setText("20")
        self.dialog.QLineEdit_Sinking_Final_Voltage.textEdited.emit("20")
        self.dialog.QLineEdit_Sinking_Voltage_Step_Size.setText("2.5")
        self.dialog.QLineEdit_Sinking_Voltage_Step_Size.textEdited.emit("2.5")

        self.assertFalse(self.dialog.Sinking_Test_group.isHidden())
        self.assertEqual(self.dialog.params.Sinking_Initial_Voltage, "10")
        self.assertEqual(self.dialog.params.Sinking_Final_Voltage, "20")
        self.assertEqual(self.dialog.params.Sinking_Voltage_Step_Size, "2.5")

        self.dialog.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget.setChecked(True)
        self.assertTrue(self.dialog.Sinking_Test_group.isHidden())

    def test_graph_button_opens_graph_plotting_subtab(self):
        self.dialog.dialog_tabs.setCurrentIndex(0)

        self.dialog.show_popup_plot()

        self.assertIs(
            self.dialog.dialog_tabs.currentWidget(),
            self.dialog.plot_window,
        )

    def test_worker_plot_data_updates_graph_subtab_without_popup(self):
        self.dialog.plot_window.popup_plot(
            0.1,
            0.2,
            0.5,
            -0.5,
            0.5,
            -0.5,
            1.0,
            2.0,
            100.0,
            -100.0,
        )

        self.assertEqual(self.dialog.plot_window.x, [0])
        self.assertEqual(self.dialog.plot_window.prog_data, [0.1])
        self.assertFalse(self.dialog.plot_window.isWindow())

    def test_temperature_samples_update_dedicated_plotting_subtab(self):
        plot_widget = self.dialog.temperature_plot_widget
        started = datetime(2026, 1, 1, 12, 0, 0)
        plot_widget.reset(enabled=True)

        plot_widget.add_sample(
            SimpleNamespace(
                timestamp=started,
                readings={101: 20.0, 103: 21.0},
            ),
            0,
        )
        plot_widget.add_sample(
            SimpleNamespace(
                timestamp=started + timedelta(seconds=5),
                readings={101: 20.5, 103: 21.5},
            ),
            1,
        )

        self.assertEqual(plot_widget.elapsed_seconds, [0.0, 5.0])
        self.assertEqual(plot_widget.channel_data[101], [20.0, 20.5])
        self.assertEqual(plot_widget.channel_data[103], [21.0, 21.5])
        self.assertEqual(set(plot_widget.channel_curves), {101, 103})
        self.assertIn("Loop 2", plot_widget.status_label.text())
        self.assertIn("CH101: 20.500 °C", plot_widget.status_label.text())

        plot_widget.update_test_state("COMPLETED")

        self.assertTrue(plot_widget.status_label.text().startswith("COMPLETED |"))

    def test_worker_temperature_signal_updates_plotting_tab(self):
        worker = DummyWorker()
        self.dialog._connect_worker(worker)
        sample = SimpleNamespace(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            readings={101: 23.5},
        )

        worker.temperature_data.emit(sample, 0)

        self.assertEqual(
            self.dialog.temperature_plot_widget.channel_data[101],
            [23.5],
        )

    def test_graph_hover_shows_values_for_nearest_point(self):
        plot_window = self.dialog.plot_window
        plot_window.popup_plot(
            0.1,
            0.2,
            0.5,
            -0.5,
            0.5,
            -0.5,
            1.0,
            2.0,
            100.0,
            -100.0,
        )
        self.dialog.show()
        self.dialog.dialog_tabs.setCurrentWidget(plot_window)
        self.application.processEvents()

        plot, series, label, vertical_line, horizontal_line = (
            plot_window._hover_controls[0]
        )
        scene_position = plot.plotItem.vb.mapViewToScene(QPointF(0.0, 0.1))
        plot_window._update_hover(
            (scene_position,),
            plot,
            series,
            label,
            vertical_line,
            horizontal_line,
        )

        self.assertTrue(label.isVisible())
        self.assertIn("Programming Error: 0.1", label.toPlainText())
        self.assertTrue(vertical_line.isVisible())
        self.assertTrue(horizontal_line.isVisible())

    def test_temperature_checkbox_reveals_optional_daq_address(self):
        self.assertTrue(self.dialog.QLineEdit_DAQ_VisaAddress.isHidden())

        self.dialog.QCheckBox_Temperature_Widget.setChecked(True)

        self.assertFalse(self.dialog.QLineEdit_DAQ_VisaAddress.isHidden())
        self.assertFalse(self.dialog.QLabel_DAQ_VisaAddress.isHidden())

    def test_blynk_monitoring_is_optional_and_reports_missing_token(self):
        self.assertFalse(self.dialog.QCheckBox_Blynk_Widget.isChecked())
        self.assertEqual(self.dialog.Blynk_Status_Label.text(), "Blynk: Disabled")

        self.dialog.QCheckBox_Blynk_Widget.setChecked(True)

        if not self.dialog.blynk_publisher.configured:
            self.assertIn(
                "BLYNK_AUTH_TOKEN",
                self.dialog.Blynk_Status_Label.text(),
            )

    def test_blynk_measurement_uses_documented_virtual_pins(self):
        published = []
        self.dialog.blynk_active = True
        self.dialog.blynk_publisher = SimpleNamespace(
            publish=lambda values, force=False: published.append(
                (dict(values), force)
            ),
            stop=lambda: None,
        )
        measurement = all_test_dialog.RealtimeMeasurement(
            set_voltage=5.0,
            set_current=1.0,
            programming_voltage=4.999,
            readback_voltage=4.998,
            readback_current=1.001,
            programming_error=-0.001,
            readback_error=-0.002,
            programming_percent=-0.2,
            readback_percent=-0.4,
            programming_upper_bound=0.5,
            programming_lower_bound=-0.5,
            readback_upper_bound=0.5,
            readback_lower_bound=-0.5,
            percentage_upper_bound=100.0,
            percentage_lower_bound=-100.0,
        )

        self.dialog._publish_blynk_measurement(measurement)

        self.assertEqual(
            set(published[0][0]),
            {"v0", "v1", "v2", "v3", "v4", "v5", "v6", "v8"},
        )

    def test_blynk_temperature_uses_documented_channel_pins(self):
        published = []
        self.dialog.blynk_active = True
        self.dialog.blynk_publisher = SimpleNamespace(
            publish=lambda values, force=False: published.append(
                (dict(values), force)
            ),
            stop=lambda: None,
        )
        sample = SimpleNamespace(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            readings={101: 20.1, 103: 20.3, 104: 20.4, 105: 20.5},
        )

        self.dialog._handle_temperature_sample(sample, 0)

        self.assertEqual(
            published[0][0],
            {"v10": 20.1, "v11": 20.3, "v12": 20.4, "v16": 20.5},
        )

    def test_blynk_run_metadata_publishes_collection_count_and_channel(self):
        published = []
        self.dialog.blynk_active = True
        self.dialog.blynk_publisher = SimpleNamespace(
            publish=lambda values, force=False: published.append(
                (dict(values), force)
            ),
            stop=lambda: None,
        )

        self.dialog._publish_blynk_run_metadata(
            {"noofloop": "3", "PSU_Channel": "2"}
        )

        self.assertEqual(published, [({"v13": 3, "v14": "2"}, True)])

    def test_blynk_start_notification_includes_run_metadata(self):
        notifications = []
        self.dialog.blynk_active = True
        self.dialog.blynk_publisher = SimpleNamespace(
            notify_start=notifications.append,
            stop=lambda: None,
        )

        self.dialog._notify_blynk_start(
            {
                "DUT": "Hornbill",
                "PSU_Channel": "2",
                "noofloop": "3",
            }
        )

        self.assertEqual(
            notifications,
            [
                "Test started: DUT=Hornbill, channel=2, "
                "data collections=3."
            ],
        )

    def test_hornbill_configuration_loads_default_daq_address(self):
        self.dialog.QComboBox_DUT.setCurrentText("Hornbill")

        self.assertEqual(
            self.dialog.QLineEdit_DAQ_VisaAddress.currentText(),
            "USB0::0x2A8D::0x8601::MY59010677::0::INSTR",
        )

    def test_hornbill_sinking_selection_shows_external_source_settings(self):
        self.dialog.QComboBox_DUT.setCurrentText("Hornbill")
        self.dialog.QCheckBox_VoltageLoadRegulation_Widget.setChecked(True)
        self.dialog.QCheckBox_CurrentAccuracy_Widget.setChecked(True)

        self.assertFalse(self.dialog.QCheckBox_Sinking_Test_Widget.isHidden())
        self.dialog.QCheckBox_Sinking_Test_Widget.setChecked(True)

        self.assertFalse(self.dialog.Sinking_Test_group.isHidden())
        self.assertFalse(
            self.dialog.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget.isChecked()
        )
        self.assertFalse(
            self.dialog.QCheckBox_Voltage_Accuracy_Current_Mode_Widget.isChecked()
        )
        self.assertFalse(
            self.dialog.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget.isChecked()
        )
        self.assertFalse(
            self.dialog.QCheckBox_VoltageLoadRegulation_Widget.isChecked()
        )
        self.assertFalse(self.dialog.QCheckBox_CurrentAccuracy_Widget.isChecked())
        self.assertEqual(
            self.dialog.QLineEdit_External_Source_Positive_Current_Limit.text(),
            "7",
        )
        self.assertEqual(
            self.dialog.QLineEdit_External_Source_Negative_Current_Limit.text(),
            "-7",
        )
        self.assertEqual(self.dialog.QLineEdit_Sink_Slew_Rate.text(), "10")

    def test_ocp_level_updates_parameters_and_output(self):
        self.dialog.OCP_Level_changed("2.5")

        self.assertEqual(self.dialog.params.OCP_Level, "2.5")
        self.assertIn("OCP Level Set to: 2.5", self.dialog.OutputBox.toPlainText())
        self.assertIsNotNone(self.dialog.General_group.layout())
        self.assertIsNotNone(self.dialog.Ratings_Widget.layout())
        self.assertIsNotNone(self.dialog.oscilloscope_settings_widget.layout())
        self.assertIsNotNone(self.dialog.collection_group.layout())
        self.assertIsNotNone(self.dialog.queue_widget.parent())

    def test_realtime_plot_accepts_complete_worker_measurement(self):
        context = DummyRunContext(
            create_run_storage(self.queue_directory.name, "REALTIME"),
            self.queue_directory.name,
            self.dialog.params,
        )
        self.dialog.active_run_context = context

        self.dialog.update_plot(
            5.0,
            1.0,
            5.1,
            5.05,
            1.0,
            0.1,
            0.05,
            2.0,
            1.0,
            0.5,
            -0.5,
            0.5,
            -0.5,
            100.0,
            -100.0,
        )

        self.assertEqual(self.dialog.realtime_plot_series.counter, 1)
        self.assertEqual(len(context.realtime_rows[0]), 15)
        self.assertEqual(context.realtime_rows[0][7], 20.0)
        self.assertEqual(context.realtime_rows[0][8], 10.0)
        self.assertEqual(self.dialog.plot_window.prog_perc_data, [20.0])
        self.assertEqual(self.dialog.plot_window.rb_perc_data, [10.0])
        self.assertIn("Pass", self.dialog.OutputBox.toPlainText())
        self.assertIn("PASS", self.dialog.plot_window.status_label.text())
        self.assertIn("Point 1", self.dialog.plot_window.status_label.text())
        self.assertIn("Set 5 V, 1 A", self.dialog.plot_window.status_label.text())

    def test_realtime_plots_show_named_legends(self):
        legends = (
            self.dialog.plot_window.prog_plot.plotItem.legend,
            self.dialog.plot_window.rb_plot.plotItem.legend,
            self.dialog.plot_window.prog_perc_plot.plotItem.legend,
            self.dialog.plot_window.rb_perc_plot.plotItem.legend,
        )

        self.assertTrue(all(legend is not None for legend in legends))
        self.assertTrue(all(len(legend.items) == 3 for legend in legends))

    def test_dut_selection_loads_configuration_into_bound_widgets(self):
        self.dialog.params.savelocation = "preserved-output"

        self.dialog.QComboBox_DUT.setCurrentText("Hornbill")

        self.assertEqual(self.dialog.params.DUT, "Hornbill")
        self.assertEqual(self.dialog.params.savelocation, "preserved-output")
        self.assertEqual(self.dialog.QLineEdit_Programming_Error_Gain.text(), "0.0003")
        self.assertEqual(
            self.dialog.QLineEdit_Programming_Response_Up_NoLoad.text(), "80"
        )
        self.assertEqual(self.dialog.QLineEdit_OVP_Error_Gain.text(), "0.002")
        self.assertEqual(self.dialog.QLineEdit_maxVoltage.text(), "60")
        self.assertEqual(self.dialog.QComboBox_Probe_Setting.currentText(), "X10")
        self.assertEqual(self.dialog.QComboBox_Voltage_Res.currentText(), "SLOW")
        self.assertEqual(
            self.dialog.QComboBox_set_Function.currentText(), "Voltage Priority"
        )
        self.assertEqual(self.dialog.QComboBox_Voltage_Sense.currentText(), "4 Wire")
        self.assertEqual(
            self.dialog.QComboBox_Hornbill_Measurement_Command.currentText(),
            "SCPI",
        )
        self.assertEqual(self.dialog.QLineEdit_SweepPoints.text(), "100000")
        self.assertFalse(
            self.dialog.QComboBox_Hornbill_Measurement_Command.isHidden()
        )
        self.assertFalse(self.dialog.QLineEdit_SweepPoints.isHidden())
        self.assertEqual(self.dialog.QLineEdit_OVP_Level.text(), "")

    def test_hornbill_readback_command_can_be_switched_to_scpi(self):
        self.dialog.QComboBox_DUT.setCurrentText("Hornbill")
        self.dialog.QComboBox_Hornbill_Measurement_Command.setCurrentText("SCPI")

        self.assertEqual(
            self.dialog.params.Hornbill_Measurement_Command,
            "SCPI",
        )
        self.dialog.QComboBox_Hornbill_Measurement_Command.setCurrentText("DIAG")
        self.dialog.QLineEdit_SweepPoints.setText("250")
        self.dialog.QLineEdit_SweepPoints.textEdited.emit("250")

        self.assertEqual(self.dialog.params.SweepPoints, "250")

        self.dialog.QComboBox_DUT.setCurrentText("Dolphin")
        self.assertTrue(
            self.dialog.QComboBox_Hornbill_Measurement_Command.isHidden()
        )
        self.assertTrue(self.dialog.QLineEdit_SweepPoints.isHidden())

    def test_measurement_mode_updates_related_controls(self):
        self.dialog.QPushButton_Current_Widget.click()

        self.assertEqual(self.dialog.params.unit, "CURRENT")
        self.assertEqual(
            self.dialog.QComboBox_set_Function.currentText(), "Voltage Priority"
        )
        self.assertFalse(self.dialog.Current_Test_group.isHidden())
        self.assertTrue(self.dialog.Voltage_Test_group.isHidden())
        self.assertFalse(self.dialog.QLineEdit_DMM_VisaAddressforCurrent.isHidden())
        self.assertTrue(self.dialog.QLineEdit_rshunt.isEnabled())

        self.dialog.QPushButton_Voltage_Widget.click()

        self.assertEqual(self.dialog.params.unit, "VOLTAGE")
        self.assertFalse(self.dialog.Voltage_Test_group.isHidden())
        self.assertTrue(self.dialog.Current_Test_group.isHidden())
        self.assertTrue(self.dialog.QLineEdit_DMM_VisaAddressforCurrent.isHidden())
        self.assertFalse(self.dialog.QLineEdit_rshunt.isEnabled())

    def test_oscilloscope_visibility_combines_all_requiring_tests(self):
        scope_checkboxes = (
            self.dialog.QCheckBox_OCP_Test_Widget,
            self.dialog.QCheckBox_TransientRecovery_Widget,
            self.dialog.QCheckBox_ProgrammingSpeed_Widget,
        )
        for checkbox in scope_checkboxes:
            checkbox.setChecked(False)
        self.dialog.InteractiveAction()
        self.assertTrue(self.dialog.oscilloscope_settings_widget.isHidden())

        for checkbox in scope_checkboxes:
            checkbox.setChecked(True)
            self.assertFalse(self.dialog.oscilloscope_settings_widget.isHidden())
            checkbox.setChecked(False)

        self.assertTrue(self.dialog.oscilloscope_settings_widget.isHidden())

    def test_voltage_accuracy_modes_are_exclusive_and_scope_mode_shows_settings(self):
        static_mode = self.dialog.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget
        current_mode = self.dialog.QCheckBox_Voltage_Accuracy_Current_Mode_Widget
        scope_mode = (
            self.dialog.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget
        )

        scope_mode.setChecked(True)

        self.assertFalse(static_mode.isChecked())
        self.assertFalse(current_mode.isChecked())
        self.assertFalse(self.dialog.oscilloscope_settings_widget.isHidden())

        current_mode.setChecked(True)

        self.assertFalse(static_mode.isChecked())
        self.assertFalse(scope_mode.isChecked())
        self.assertTrue(self.dialog.oscilloscope_settings_widget.isHidden())

    def test_state_controls_follow_worker_state(self):
        self.dialog.set_test_state(GUI.TestState.RUNNING)
        self.assertFalse(self.dialog.QPushButton_Widget1.isEnabled())
        self.assertFalse(self.dialog.pause_button.isHidden())
        self.assertEqual(self.dialog.pause_button.text(), "Pause")

        self.dialog.set_test_state(GUI.TestState.PAUSING)
        self.assertEqual(self.dialog.pause_button.text(), "Pausing...")
        self.assertFalse(self.dialog.pause_button.isEnabled())
        self.assertTrue(self.dialog.abort_button.isEnabled())

        self.dialog.set_test_state(GUI.TestState.PAUSED)
        self.assertEqual(self.dialog.pause_button.text(), "Resume")

        self.dialog.set_test_state(GUI.TestState.COMPLETED)
        self.assertTrue(self.dialog.QPushButton_Widget1.isEnabled())
        self.assertTrue(self.dialog.pause_button.isHidden())

    def test_pause_resume_and_abort_controls_worker(self):
        worker = DummyWorker()
        worker.running = True
        self.dialog.worker = worker

        self.dialog.set_test_state(GUI.TestState.RUNNING)
        self.dialog.toggle_pause_test()
        self.assertEqual(worker.pause_calls, 1)

        self.dialog.set_test_state(GUI.TestState.PAUSED)
        self.dialog.toggle_pause_test()
        self.assertEqual(worker.resume_calls, 1)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            self.dialog.abort_test()

        self.assertEqual(worker.stop_calls, 1)
        self.assertEqual(self.dialog.test_state, GUI.TestState.STOPPING)
        self.assertEqual(self.dialog.abort_button.text(), "Stopping...")

    def test_discovery_populates_all_instrument_widgets_and_assigns_roles(self):
        result = GUI.DiscoveryResult(
            addresses=["USB0::PSU::INSTR", "USB0::DMM::INSTR"],
            identities=["VENDOR,PSU", "VENDOR,DMM"],
            roles={
                "PSU": "USB0::PSU::INSTR",
                "DMM": "USB0::DMM::INSTR",
            },
        )

        with patch.object(
            all_test_dialog, "GetConfiguredVisaResources", return_value=result
        ):
            self.dialog.QPushButton_Widget4.click()
            self.wait_for_instrument_discovery()

        widgets = (
            self.dialog.QLineEdit_PSU_VisaAddress,
            self.dialog.QLineEdit_DMM_VisaAddressforVoltage,
            self.dialog.QLineEdit_DMM_VisaAddressforCurrent,
            self.dialog.QLineEdit_OSC_VisaAddress,
            self.dialog.QLineEdit_ELoad_VisaAddress,
            self.dialog.QLineEdit_DAQ_VisaAddress,
            self.dialog.QLineEdit_External_Source_VisaAddress,
        )
        for widget in widgets:
            expected_count = (
                3 if widget is self.dialog.QLineEdit_ELoad_VisaAddress else 2
            )
            self.assertEqual(widget.count(), expected_count)
        self.assertEqual(
            self.dialog.QLineEdit_PSU_VisaAddress.currentText(),
            "USB0::PSU::INSTR",
        )
        self.assertEqual(
            self.dialog.QLineEdit_DMM_VisaAddressforVoltage.currentText(),
            "USB0::DMM::INSTR",
        )
        self.assertEqual(
            self.dialog.QLineEdit_ELoad_VisaAddress.currentText(),
            "None",
        )

    def test_find_instruments_does_not_block_the_gui_thread(self):
        scan_started = threading.Event()
        release_scan = threading.Event()

        def blocking_scan(*_args, **_kwargs):
            scan_started.set()
            release_scan.wait(1.0)
            return GUI.DiscoveryResult()

        with patch.object(
            all_test_dialog,
            "GetConfiguredVisaResources",
            side_effect=blocking_scan,
        ):
            started_at = time.monotonic()
            self.dialog.QPushButton_Widget4.click()
            click_duration = time.monotonic() - started_at

            self.assertLess(click_duration, 0.2)
            self.assertTrue(scan_started.wait(1.0))
            self.assertFalse(self.dialog.QPushButton_Widget4.isEnabled())
            self.assertEqual(
                self.dialog.QPushButton_Widget4.text(),
                "Scanning...",
            )

            release_scan.set()
            self.wait_for_instrument_discovery()

        self.assertTrue(self.dialog.QPushButton_Widget4.isEnabled())
        self.assertEqual(
            self.dialog.QPushButton_Widget4.text(),
            "Find Instruments",
        )

    def test_connection_selector_has_explicit_gpib_option(self):
        self.assertEqual(self.dialog.QCheckBox_USB_Widget.text(), "USB")
        self.assertEqual(self.dialog.QCheckBox_GPIB_Widget.text(), "GPIB")
        self.assertTrue(self.dialog.QCheckBox_USB_Widget.isChecked())
        self.assertTrue(self.dialog.QCheckBox_GPIB_Widget.isChecked())
        self.assertTrue(self.dialog.QCheckBox_IP_Widget.isChecked())
        self.assertTrue(self.dialog.QCheckBox_Hostname_Widget.isChecked())

    def test_selected_resource_scan_uses_active_dut_configuration(self):
        snapshots = []
        self.dialog.QComboBox_DUT.setCurrentText("Hornbill")
        configured = GUI.DiscoveryResult(
            addresses=[
                "GPIB0::22::INSTR",
                "TCPIP0::host::inst0::INSTR",
            ],
            identities=["HP3458A", "VENDOR,HOST"],
        )
        expected_path = Path("configured-hornbill.txt")

        with patch.object(
            all_test_dialog,
            "configuration_path",
            return_value=expected_path,
        ) as path_builder, patch.object(
            all_test_dialog,
            "GetConfiguredVisaResources",
            return_value=configured,
        ) as configured_scan:
            result = all_test_dialog.ScanSelectedVisaResources(
                self.dialog,
                on_progress=lambda current: snapshots.append(
                    list(current.addresses)
                ),
            )

        self.assertEqual(
            result.addresses,
            ["GPIB0::22::INSTR", "TCPIP0::host::inst0::INSTR"],
        )
        self.assertEqual(snapshots, [result.addresses])
        path_builder.assert_called_once_with(
            all_test_dialog.config_folder,
            "Hornbill",
        )
        configured_scan.assert_called_once_with(
            expected_path,
            enabled_transports={
                "usb",
                "gpib",
                "tcpip_ip",
                "tcpip_hostname",
            },
        )

    def test_discovery_lists_mixed_gpib_and_hostname_resources(self):
        result = GUI.DiscoveryResult(
            addresses=[
                "GPIB0::22::INSTR",
                "TCPIP0::p700-95640339::inst0::INSTR",
            ],
            identities=[
                "HP3458A",
                "KEYSIGHT TECHNOLOGIES,LINUXGEN,TST0000001,00.04",
            ],
            roles={
                "DMM": "GPIB0::22::INSTR",
                "PSU": "TCPIP0::p700-95640339::inst0::INSTR",
            },
        )

        with patch.object(
            all_test_dialog, "GetConfiguredVisaResources", return_value=result
        ):
            self.dialog.QPushButton_Widget4.click()
            self.wait_for_instrument_discovery()

        psu_widget = self.dialog.QLineEdit_PSU_VisaAddress
        dmm_widget = self.dialog.QLineEdit_DMM_VisaAddressforVoltage
        expected_items = result.addresses
        self.assertEqual(
            [psu_widget.itemText(index) for index in range(psu_widget.count())],
            expected_items,
        )
        self.assertEqual(
            [dmm_widget.itemText(index) for index in range(dmm_widget.count())],
            expected_items,
        )
        self.assertEqual(
            psu_widget.currentText(),
            "TCPIP0::p700-95640339::inst0::INSTR",
        )
        self.assertEqual(dmm_widget.currentText(), "GPIB0::22::INSTR")
        self.assertIn(
            "Found 2 available configured instrument(s)",
            self.dialog.OutputBox.toPlainText(),
        )

    def test_failure_termination_uses_safe_stop_state(self):
        class TerminateMessageBox:
            Warning = QMessageBox.Warning
            AcceptRole = QMessageBox.AcceptRole
            RejectRole = QMessageBox.RejectRole

            def __init__(self, _parent):
                self.terminate_button = None

            def setIcon(self, _icon):
                return None

            def setWindowTitle(self, _title):
                return None

            def setText(self, _text):
                return None

            def addButton(self, text, _role):
                button = object()
                if text == "Terminate Test":
                    self.terminate_button = button
                return button

            def exec_(self):
                return None

            def clickedButton(self):
                return self.terminate_button

        worker = DummyWorker()
        worker.running = True
        self.dialog.worker = worker
        self.dialog.set_test_state(GUI.TestState.PAUSED)

        with patch.object(all_test_dialog, "QMessageBox", TerminateMessageBox):
            self.dialog.handle_test_failure()

        self.assertTrue(self.dialog.was_aborted)
        self.assertEqual(self.dialog.test_state, GUI.TestState.STOPPING)
        self.assertEqual(worker.stop_calls, 1)

    def test_failure_can_continue_all_remaining_boundary_failures(self):
        class ContinueAllMessageBox:
            Warning = QMessageBox.Warning
            AcceptRole = QMessageBox.AcceptRole
            RejectRole = QMessageBox.RejectRole

            def __init__(self, _parent):
                self.continue_all_button = None

            def setIcon(self, _icon):
                return None

            def setWindowTitle(self, _title):
                return None

            def setText(self, _text):
                return None

            def addButton(self, text, _role):
                button = object()
                if text == "Continue All Failures":
                    self.continue_all_button = button
                return button

            def exec_(self):
                return None

            def clickedButton(self):
                return self.continue_all_button

        worker = DummyWorker()
        self.dialog.worker = worker
        self.dialog.fail_prompt_active = True

        with patch.object(all_test_dialog, "QMessageBox", ContinueAllMessageBox):
            self.dialog.handle_test_failure()

        self.assertTrue(self.dialog.continue_on_boundary_failure)
        self.assertFalse(self.dialog.fail_prompt_active)
        self.assertEqual(worker.resume_calls, 1)
        self.assertEqual(worker.stop_calls, 0)

    def test_failure_countdown_resumes_test_after_ten_seconds(self):
        class TimeoutSignal:
            def __init__(self):
                self.callback = None

            def connect(self, callback):
                self.callback = callback

        class ImmediateCountdownTimer:
            instances = []

            def __init__(self, _parent):
                self.timeout = TimeoutSignal()
                self.interval = None
                self.stopped = False
                self.instances.append(self)

            def setInterval(self, interval):
                self.interval = interval

            def start(self):
                for _tick in range(10):
                    if self.stopped:
                        break
                    self.timeout.callback()

            def stop(self):
                self.stopped = True

        class CountdownMessageBox:
            Warning = QMessageBox.Warning
            AcceptRole = QMessageBox.AcceptRole
            RejectRole = QMessageBox.RejectRole
            messages = []

            def __init__(self, _parent):
                self.accepted = False

            def setIcon(self, _icon):
                return None

            def setWindowTitle(self, _title):
                return None

            def setText(self, text):
                self.messages.append(text)

            def addButton(self, _text, _role):
                return object()

            def accept(self):
                self.accepted = True

            def exec_(self):
                return None

            def clickedButton(self):
                return None

        worker = DummyWorker()
        self.dialog.worker = worker
        self.dialog.fail_prompt_active = True

        with patch.object(
            all_test_dialog,
            "QMessageBox",
            CountdownMessageBox,
        ), patch.object(
            all_test_dialog,
            "QTimer",
            ImmediateCountdownTimer,
        ):
            self.dialog.handle_test_failure()

        self.assertFalse(self.dialog.fail_prompt_active)
        self.assertEqual(worker.resume_calls, 1)
        self.assertEqual(ImmediateCountdownTimer.instances[0].interval, 1000)
        self.assertIn("10 seconds", CountdownMessageBox.messages[0])
        self.assertIn(
            "resumed automatically",
            self.dialog.OutputBox.toPlainText(),
        )

    def test_continue_all_policy_does_not_pause_on_later_failures(self):
        class FailedMeasurement:
            passed = False
            set_voltage = 5.0
            set_current = 1.0
            programming_error = 0.1
            programming_percent = 2.0
            readback_error = 0.2
            readback_percent = 4.0

        worker = DummyWorker()
        self.dialog.worker = worker
        self.dialog.continue_on_boundary_failure = True

        with patch.object(self.dialog, "handle_test_failure") as failure_dialog:
            self.dialog._handle_realtime_measurement_failure(FailedMeasurement())

        self.assertEqual(worker.pause_calls, 0)
        failure_dialog.assert_not_called()

    def test_duplicate_start_is_rejected_before_preflight(self):
        worker = DummyWorker()
        worker.running = True
        self.dialog.worker = worker

        with patch.object(QMessageBox, "warning") as warning, patch.object(
            self.dialog, "pre_test_check"
        ) as preflight:
            self.dialog.executeTest()

        warning.assert_called_once()
        preflight.assert_not_called()
        self.assertIs(self.dialog.worker, worker)

    def test_invalid_configuration_prevents_execution(self):
        with patch.object(QMessageBox, "warning") as warning:
            result = self.dialog.pre_test_check({})

        self.assertFalse(result)
        warning.assert_called_once()
        self.assertIn("Preflight validation failed", self.dialog.OutputBox.toPlainText())

    def test_submission_uses_one_selection_snapshot_for_preflight(self):
        self.dialog.params.DUT = "Dolphin"
        selections = {
            "Voltage_Test": True,
            "VoltageAccuracy": True,
            "DataReport": True,
            "DataImage": False,
        }
        with patch.object(
            all_test_dialog,
            "collect_test_selections",
            return_value=selections,
        ), patch.object(
            self.dialog,
            "pre_test_check",
            return_value=False,
        ) as preflight:
            self.dialog.executeTest()

        preflight.assert_called_once()
        configuration, preflight_selections = preflight.call_args.args
        self.assertEqual(preflight_selections, selections)
        self.assertEqual(configuration["DUT"], self.dialog.params.DUT)
        self.assertTrue(self.dialog.isEnabled())

    def test_confirmed_start_creates_and_starts_worker(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage = create_run_storage(temporary_directory, "GUI_SIMULATION")

            def prepare_storage(configuration, run_parameters, run_id):
                self.dialog.run_storage = storage
                self.dialog._output_root = temporary_directory
                return DummyRunContext(storage, temporary_directory, run_parameters)

            self.dialog.checkbox_states = {
                "Voltage_Test": True,
                "VoltageAccuracy": True,
                "CurrentStatic(VoltageChange)": True,
                "DataImage": False,
            }
            self.dialog.params.DUT = "Dolphin"
            self.dialog.params.savelocation = temporary_directory
            with patch.object(
                self.dialog, "pre_test_check", return_value=True
            ), patch.object(
                self.dialog, "prepare_run_storage", side_effect=prepare_storage
            ), patch.object(
                QMessageBox, "question", return_value=QMessageBox.Yes
            ), patch.object(
                all_test_dialog, "VoltageAccuracyPlotWindow", DummyPlotWindow
            ), patch.object(
                all_test_dialog, "TestWorker", DummyWorker
            ), patch.object(
                all_test_dialog, "show_error_dialog"
            ) as error_dialog:
                self.dialog.executeTest()

            error_dialog.assert_not_called()
            self.assertIsInstance(self.dialog.worker, DummyWorker)
            self.assertTrue(self.dialog.worker.isRunning())
            self.assertEqual(self.dialog.test_state, GUI.TestState.RUNNING)
            self.assertFalse(self.dialog.QPushButton_Widget1.isEnabled())
            self.dialog.worker.running = False
            self.dialog.cleanup_test("test")

    def test_queue_submission_snapshots_parameters_until_started(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage = create_run_storage(temporary_directory, "QUEUE_SIMULATION")

            def prepare_storage(configuration, run_parameters, run_id):
                self.dialog.run_storage = storage
                self.dialog._output_root = temporary_directory
                return DummyRunContext(storage, temporary_directory, run_parameters)

            self.dialog.params.DUT = "Dolphin"
            self.dialog.params.savelocation = temporary_directory
            self.dialog.params.noofloop = "1"
            with patch.object(
                self.dialog, "pre_test_check", return_value=True
            ), patch.object(
                self.dialog, "prepare_run_storage", side_effect=prepare_storage
            ), patch.object(
                QMessageBox, "question", return_value=QMessageBox.Yes
            ), patch.object(
                all_test_dialog, "VoltageAccuracyPlotWindow", DummyPlotWindow
            ), patch.object(
                all_test_dialog, "TestWorker", DummyWorker
            ):
                self.dialog.executeTest(queue_only=True)
                self.dialog.params.noofloop = "9"

                self.assertEqual(self.dialog.run_controller.pending_count, 1)
                self.assertEqual(self.dialog.queue_widget.table.rowCount(), 1)
                self.assertIsNone(self.dialog.worker)

                request = self.dialog.run_controller.pending_requests[0]
                self.assertEqual(request.parameters.noofloop, "1")
                self.dialog.run_controller.start_queue()

            self.assertIsInstance(self.dialog.worker, DummyWorker)
            self.assertEqual(self.dialog.worker.parameters.noofloop, "1")
            self.dialog.worker.running = False
            self.dialog.cleanup_test("queue-test")

    def test_queue_runs_two_items_with_separate_storage(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage_roots = []

            def prepare_storage(configuration, run_parameters, run_id):
                storage = create_run_storage(
                    temporary_directory,
                    f"QUEUE_{len(storage_roots) + 1}",
                )
                storage_roots.append(storage.root)
                self.dialog.run_storage = storage
                self.dialog._output_root = temporary_directory
                return DummyRunContext(storage, temporary_directory, run_parameters)

            self.dialog.params.DUT = "Dolphin"
            self.dialog.params.savelocation = temporary_directory
            with patch.object(
                self.dialog, "pre_test_check", return_value=True
            ), patch.object(
                self.dialog, "prepare_run_storage", side_effect=prepare_storage
            ), patch.object(
                QMessageBox, "question", return_value=QMessageBox.Yes
            ), patch.object(
                all_test_dialog, "VoltageAccuracyPlotWindow", DummyPlotWindow
            ), patch.object(
                all_test_dialog, "TestWorker", DummyWorker
            ):
                self.dialog.params.noofloop = "1"
                self.dialog.executeTest(queue_only=True)
                self.dialog.params.noofloop = "2"
                self.dialog.executeTest(queue_only=True)
                self.dialog.run_controller.start_queue()

                first_worker = self.dialog.worker
                self.assertEqual(first_worker.parameters.noofloop, "1")
                self.dialog.realtime_plot_series.counter = 7
                self.dialog.last_Iset = 1.0
                self.dialog.fail_prompt_active = True
                first_worker.running = False
                first_worker.finished.emit()
                self.application.processEvents()

                self.assertIsNot(self.dialog.worker, first_worker)
                self.assertEqual(self.dialog.worker.parameters.noofloop, "2")
                self.assertEqual(self.dialog.realtime_plot_series.counter, 0)
                self.assertIsNone(self.dialog.last_Iset)
                self.assertFalse(self.dialog.fail_prompt_active)
                self.assertEqual(len(storage_roots), 2)
                self.assertNotEqual(storage_roots[0], storage_roots[1])

            self.dialog.worker.running = False
            self.dialog.cleanup_test("queue-sequence-test")

    def test_pending_queue_restores_in_new_dialog(self):
        self.dialog.run_controller.enqueue(
            {"Voltage_Test": True},
            {"DUT": "Dolphin"},
            GUI.ParameterSnapshot(noofloop="3", savelocation="output"),
            label="Restored voltage test",
            prepare=self.dialog._prepare_queued_run,
            auto_start=False,
        )

        restored_dialog = GUI.AllTestMeasurement(queue_file=self.queue_file)
        try:
            self.assertEqual(restored_dialog.run_controller.pending_count, 1)
            request = restored_dialog.run_controller.pending_requests[0]
            self.assertEqual(request.label, "Restored voltage test")
            self.assertEqual(request.parameters.noofloop, "3")
            self.assertEqual(restored_dialog.queue_widget.table.rowCount(), 1)
        finally:
            restored_dialog.close()
            restored_dialog.deleteLater()
            self.application.processEvents()

    def test_active_run_restores_as_interrupted_and_requires_retry(self):
        active = TestRunRequest(
            {"Voltage_Test": True},
            {"DUT": "Dolphin"},
            GUI.ParameterSnapshot(noofloop="3", savelocation="output"),
            label="Interrupted voltage test",
            run_id="interrupted-run",
            recovery_run_directory="output/previous-run",
        )
        QueuePersistence(self.queue_file).save([], active)

        restored_dialog = GUI.AllTestMeasurement(queue_file=self.queue_file)
        try:
            controller = restored_dialog.run_controller
            self.assertEqual(controller.pending_count, 0)
            self.assertIsNone(controller.active_worker)
            self.assertEqual(
                controller.status_for("interrupted-run"),
                "Interrupted",
            )
            self.assertEqual(restored_dialog.queue_widget.table.rowCount(), 1)
            self.assertEqual(
                restored_dialog.queue_widget.table.item(0, 3).text(),
                "Interrupted",
            )
            self.assertIn(
                "output/previous-run",
                restored_dialog.OutputBox.toPlainText(),
            )
            recovered_snapshot = QueuePersistence(self.queue_file).load_snapshot()
            self.assertIsNone(recovered_snapshot["active"])
            self.assertEqual(
                recovered_snapshot["interrupted"][0]["run_id"],
                "interrupted-run",
            )

            restored_dialog.queue_widget.table.selectRow(0)
            restored_dialog.queue_widget.retry_button.click()

            self.assertEqual(controller.pending_count, 1)
            self.assertEqual(
                controller.status_for("interrupted-run"),
                "Retried",
            )
            self.assertIsNone(controller.active_worker)
            retry_snapshot = QueuePersistence(self.queue_file).load_snapshot()
            self.assertEqual(retry_snapshot["interrupted"], [])
            self.assertEqual(len(retry_snapshot["pending"]), 1)
        finally:
            restored_dialog.close()
            restored_dialog.deleteLater()
            self.application.processEvents()

    def test_queue_template_save_and_load_appends_new_requests(self):
        template_path = Path(self.queue_directory.name) / "template.json"
        self.dialog.run_controller.enqueue(
            {"Voltage_Test": True},
            {"DUT": "Dolphin"},
            GUI.ParameterSnapshot(noofloop="4", savelocation="output"),
            label="Template voltage test",
            prepare=self.dialog._prepare_queued_run,
            auto_start=False,
        )
        with patch.object(
            GUI.QFileDialog,
            "getSaveFileName",
            return_value=(str(template_path), "Queue Template (*.json)"),
        ):
            self.dialog.queue_coordinator.save_template()

        self.dialog.run_controller.clear_pending()
        with patch.object(
            GUI.QFileDialog,
            "getOpenFileName",
            return_value=(str(template_path), "Queue Template (*.json)"),
        ):
            self.dialog.queue_coordinator.load_template()

        self.assertEqual(self.dialog.run_controller.pending_count, 1)
        loaded = self.dialog.run_controller.pending_requests[0]
        self.assertEqual(loaded.label, "Template voltage test")
        self.assertEqual(loaded.parameters.noofloop, "4")

    def test_terminal_handlers_cleanup_worker(self):
        completed_worker = DummyWorker()
        self.dialog.worker = completed_worker
        self.dialog.checkbox_states = {"DataImage": False}
        self.dialog.was_aborted = False
        self.dialog.test_finished()

        self.assertEqual(self.dialog.test_state, GUI.TestState.COMPLETED)
        self.assertTrue(completed_worker.deleted)
        self.assertIsNone(self.dialog.worker)

        aborted_worker = DummyWorker()
        self.dialog.worker = aborted_worker
        self.dialog._cleanup_done = False
        self.dialog.test_aborted()

        self.assertEqual(self.dialog.test_state, GUI.TestState.ABORTED)
        self.assertTrue(aborted_worker.deleted)
        self.assertIsNone(self.dialog.worker)

    def test_failure_writes_structured_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            self.dialog.run_storage = create_run_storage(
                temporary_directory, "FAILED_SIMULATION"
            )
            with patch.object(
                all_test_dialog, "show_error_dialog"
            ) as error_dialog:
                self.dialog.handle_test_error(
                    RuntimeError("simulated VISA timeout"), "simulated traceback"
                )

            error_dialog.assert_called_once()
            self.assertEqual(self.dialog.test_state, GUI.TestState.FAILED)
            entries = [
                json.loads(line)
                for line in self.dialog.run_storage.diagnostics_file.read_text(
                    encoding="utf-8"
                ).splitlines()
                if line
            ]
            self.assertTrue(any(entry["event"] == "test_failed" for entry in entries))


if __name__ == "__main__":
    unittest.main()
