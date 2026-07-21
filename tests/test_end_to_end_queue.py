import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtWidgets import QApplication

import GUI
from ui import all_test_dialog
from DUT_Test_Scripts.Dolphin import DUT_Test as dut_measurements
from DUT_Test_Scripts.Hornbill import Hornbill_DUT_Test_With_ELoad as hornbill_measurements
from SCPI_Library.session_manager import close_visa_session_scope, get_visa_resource
from SCPI_Library.simulation import (
    clear_simulation_faults,
    get_simulation_state,
    inject_simulation_fault,
    reset_simulation,
)
from configuration.test_configuration import ParameterSnapshot


class EndToEndQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        reset_simulation()

    def tearDown(self):
        close_visa_session_scope()

    def _request_data(self, directory, dut, unit):
        values = {
            "DUT": dut,
            "selected_DUT": dut,
            "Instrument": "Keysight",
            "PSU": "USB0::SIM::PSU::INSTR",
            "DMM": "USB0::SIM::DMM::INSTR",
            "DMM2": "USB0::SIM::DMM2::INSTR",
            "ELoad": "USB0::SIM::ELOAD::INSTR",
            "DMM_Model": "344xxA",
            "ELoad_Model": "E367XXA",
            "PSU_Channel": [1],
            "ELoad_Channel": 1,
            "VoltageRes": "MIN",
            "OperationMode": "OFF",
            "VoltageSense": "INT",
            "Aperture": 1,
            "AutoZero": "ON",
            "InputZ": "AUTO",
            "Range": "Auto",
            "Programming_Error_Gain": 0.001,
            "Programming_Error_Offset": 0.001,
            "Readback_Error_Gain": 0.001,
            "Readback_Error_Offset": 0.001,
            "unit": unit,
            "updatedelay": 0,
            "noofloop": 1,
            "power": 100,
            "minCurrent": 1,
            "maxCurrent": 1,
            "current_step_size": 1,
            "minVoltage": 5,
            "maxVoltage": 5,
            "voltage_step_size": 1,
            "DownTime": 0,
            "rshunt": 0.01,
            "Voltage_Rating": 5,
            "Current_Rating": 2,
            "I_Rating": 2,
            "savelocation": directory,
            "savedir": directory,
            "counter": 0,
            "x_data": [],
            "prog_data": [],
            "read_data": [],
            "up_data": [],
            "low_data": [],
        }
        selections = {
            "Voltage_Test": True,
            "Current_Test": False,
            "VoltageAccuracy": True,
            "CurrentStatic(VoltageChange)": True,
            "CurrentChange(LoadChange)": False,
            "DataReport": True,
            "DataImage": False,
        }
        return selections, dict(values), ParameterSnapshot(values)

    def _run_event_loop(self, controller, timeout_ms=20000):
        loop = QEventLoop()
        timed_out = []
        controller.queue_finished.connect(loop.quit)

        def timeout():
            timed_out.append(True)
            loop.quit()

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(timeout)
        timer.start(timeout_ms)
        controller.start_queue()
        loop.exec_()
        timer.stop()
        self.assertFalse(timed_out, "simulated queue did not finish in time")

    def _wait_for_signal(self, signal, starter, timeout_ms=20000):
        loop = QEventLoop()
        timed_out = []
        signal.connect(loop.quit)

        def timeout():
            timed_out.append(True)
            loop.quit()

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(timeout)
        timer.start(timeout_ms)
        starter()
        loop.exec_()
        timer.stop()
        signal.disconnect(loop.quit)
        self.assertFalse(timed_out, "expected queue signal was not emitted")

    def test_real_workers_run_two_duts_and_isolate_artifacts(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(
            dut_measurements, "sleep", lambda *_: None
        ), patch.object(
            hornbill_measurements, "sleep", lambda *_: None
        ), patch.object(
            GUI, "show_error_dialog"
        ) as error_dialog:
            queue_file = Path(directory) / "queue.json"
            dialog = GUI.AllTestMeasurement(queue_file=queue_file)
            dialog.QCheckBox_Image_Widget.setChecked(False)
            statuses = []
            dialog.run_controller.request_status_changed.connect(
                lambda request, status: statuses.append((request.label, status))
            )

            for dut, unit in (("Dolphin", "DOLPHIN_V"), ("Hornbill", "HORNBILL_V")):
                selections, configuration, parameters = self._request_data(
                    directory, dut, unit
                )
                dialog.run_controller.enqueue(
                    selections,
                    configuration,
                    parameters,
                    label=f"{dut} voltage accuracy",
                    prepare=dialog._prepare_queued_run,
                    auto_start=False,
                )

            self._run_event_loop(dialog.run_controller)

            error_dialog.assert_not_called()
            self.assertEqual(dialog.run_controller.pending_count, 0)
            self.assertIsNone(dialog.run_controller.active_worker)
            self.assertIn(("Dolphin voltage accuracy", "Completed"), statuses)
            self.assertIn(("Hornbill voltage accuracy", "Completed"), statuses)

            run_directories = sorted(
                path for path in Path(directory).iterdir() if path.is_dir()
            )
            self.assertEqual(len(run_directories), 2)
            for run_directory in run_directories:
                raw = run_directory / "raw"
                charts = run_directory / "charts"
                reports = run_directory / "reports"
                logs = run_directory / "logs"
                self.assertTrue((raw / "parameters.json").is_file())
                self.assertTrue((raw / "config.csv").is_file())
                self.assertTrue((raw / "error.csv").is_file())
                self.assertEqual(len(list(raw.glob("realtime_voltage_data_*.csv"))), 1)
                self.assertTrue((charts / "Chart.png").is_file())
                self.assertTrue((charts / "Chart2.png").is_file())
                self.assertEqual(len(list(reports.glob("*.xlsx"))), 1)
                self.assertTrue((logs / "run.log").is_file())
                self.assertTrue((logs / "diagnostics.jsonl").is_file())
                self.assertTrue((run_directory / "SIMULATION_RUN.txt").is_file())

            state = get_simulation_state()
            self.assertFalse(state.output_enabled)
            self.assertEqual(state.voltage, 0.0)
            self.assertEqual(state.current, 0.0)
            self.assertEqual(state.load_current, 0.0)

            restored = GUI.AllTestMeasurement(queue_file=queue_file)
            self.assertEqual(restored.run_controller.pending_count, 0)
            restored.close()
            restored.deleteLater()
            dialog.close()
            dialog.deleteLater()
            self.application.processEvents()

    def test_current_accuracy_streams_realtime_data(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(
            dut_measurements, "sleep", lambda *_: None
        ), patch.object(
            GUI, "show_error_dialog"
        ) as error_dialog:
            dialog = GUI.AllTestMeasurement(
                queue_file=Path(directory) / "current_queue.json"
            )
            dialog._handle_realtime_measurement_failure = lambda _measurement: None
            selections, configuration, parameters = self._request_data(
                directory,
                "Dolphin",
                "CURRENT",
            )
            selections.update(
                Voltage_Test=False,
                VoltageAccuracy=False,
                Current_Test=True,
                CurrentAccuracy=True,
                CurrentAccuracy_20A_Range=True,
            )
            dialog.run_controller.enqueue(
                selections,
                configuration,
                parameters,
                label="Dolphin current accuracy",
                prepare=dialog._prepare_queued_run,
                auto_start=False,
            )

            self._run_event_loop(dialog.run_controller)

            error_dialog.assert_not_called()
            self.assertEqual(dialog.realtime_plot_series.counter, 1)
            run_directory = next(
                path for path in Path(directory).iterdir() if path.is_dir()
            )
            realtime_file = next(
                (run_directory / "raw").glob("realtime_voltage_data_*.csv")
            )
            self.assertEqual(len(realtime_file.read_text().splitlines()), 2)
            dialog.close()
            dialog.deleteLater()
            self.application.processEvents()

    def test_pause_resume_and_abort_continue_to_next_real_worker(self):
        worker_states = []
        dispatched_units = []

        def controlled_dispatch(worker, _loop_index):
            dispatched_units.append(worker.params["unit"])
            if worker.params["unit"] == "ABORT_ME":
                while True:
                    worker.interruptible_sleep(0.01)

        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(
            GUI.TestWorker, "_dispatch_dut_tests", controlled_dispatch
        ), patch.object(
            GUI, "show_error_dialog"
        ) as error_dialog:
            dialog = GUI.AllTestMeasurement(
                queue_file=Path(directory) / "control_queue.json"
            )
            statuses = []
            workers = []
            dialog.run_controller.request_status_changed.connect(
                lambda request, status: statuses.append((request.label, status))
            )

            def worker_created(worker):
                workers.append(worker)
                worker.state_changed.connect(worker_states.append)
                if len(workers) == 1:
                    QTimer.singleShot(25, dialog.run_controller.pause)
                    QTimer.singleShot(75, dialog.run_controller.resume)
                    QTimer.singleShot(
                        125,
                        lambda: dialog.run_controller.request_stop(
                            clear_pending=False
                        ),
                    )

            dialog.run_controller.worker_created.connect(worker_created)
            for label, unit in (
                ("Abort controlled run", "ABORT_ME"),
                ("Continue controlled run", "CONTINUE"),
            ):
                selections, configuration, parameters = self._request_data(
                    directory, "Dolphin", unit
                )
                selections["DataReport"] = False
                dialog.run_controller.enqueue(
                    selections,
                    configuration,
                    parameters,
                    label=label,
                    prepare=dialog._prepare_queued_run,
                    auto_start=False,
                )

            self._run_event_loop(dialog.run_controller)

            error_dialog.assert_not_called()
            self.assertEqual(dispatched_units, ["ABORT_ME", "CONTINUE"])
            self.assertIn("PAUSED", worker_states)
            self.assertGreaterEqual(worker_states.count("RUNNING"), 2)
            self.assertIn("STOPPING", worker_states)
            self.assertIn(("Abort controlled run", "Aborted"), statuses)
            self.assertIn(("Continue controlled run", "Completed"), statuses)
            self.assertEqual(dialog.run_controller.pending_count, 0)
            self.assertIsNone(dialog.run_controller.active_worker)

            dialog.close()
            dialog.deleteLater()
            self.application.processEvents()

    def test_timeout_halts_queue_then_recovers_after_fault_is_cleared(self):
        dmm_address = "USB0::SIM::DMM::INSTR"
        errors = []
        statuses = []

        def measurement_dispatch(worker, _loop_index):
            psu = get_visa_resource(worker.params["PSU"])
            dmm = get_visa_resource(worker.params["DMM"])
            psu.write("VOLT 5")
            psu.write("OUTP ON")
            float(dmm.query("MEAS:VOLT:DC?"))

        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(
            GUI.TestWorker, "_dispatch_dut_tests", measurement_dispatch
        ), patch.object(
            all_test_dialog,
            "show_error_dialog",
            side_effect=lambda _, error, __: errors.append(error),
        ):
            dialog = GUI.AllTestMeasurement(
                queue_file=Path(directory) / "recovery_queue.json"
            )
            dialog.run_controller.request_status_changed.connect(
                lambda request, status: statuses.append((request.label, status))
            )
            for label in ("Faulted run", "Recovery run"):
                selections, configuration, parameters = self._request_data(
                    directory, "Dolphin", label.replace(" ", "_")
                )
                selections["DataReport"] = False
                dialog.run_controller.enqueue(
                    selections,
                    configuration,
                    parameters,
                    label=label,
                    prepare=dialog._prepare_queued_run,
                    auto_start=False,
                )

            inject_simulation_fault(
                "query", "timeout", resource_name=dmm_address
            )
            self._wait_for_signal(
                dialog.run_controller.queue_halted,
                dialog.run_controller.start_queue,
            )

            self.assertEqual(dialog.run_controller.pending_count, 1)
            self.assertIsNone(dialog.run_controller.active_worker)
            self.assertFalse(get_simulation_state().output_enabled)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].context["role"], "DMM")
            self.assertEqual(errors[0].context["operation"], "query")

            clear_simulation_faults()
            self._wait_for_signal(
                dialog.run_controller.queue_finished,
                dialog.run_controller.start_queue,
            )

            self.assertIn(("Faulted run", "Failed"), statuses)
            self.assertIn(("Recovery run", "Completed"), statuses)
            self.assertEqual(dialog.run_controller.pending_count, 0)
            self.assertFalse(get_simulation_state().output_enabled)

            dialog.close()
            dialog.deleteLater()
            self.application.processEvents()


if __name__ == "__main__":
    unittest.main()
