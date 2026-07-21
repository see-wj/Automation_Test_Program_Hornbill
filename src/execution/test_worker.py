"""Background worker for production DUT test execution."""

import threading
import traceback
from enum import Enum
from time import monotonic as monotonic_time

from PyQt5.QtCore import QThread, pyqtSignal

from execution.current_test_executor import CurrentTestExecutor
from DUT_Test_Scripts.execution_control import clear_execution_worker, set_execution_worker
from DUT_Test_Scripts.instrument_shutdown import shutdown_instruments
from SCPI_Library.instrument_errors import (
    CleanupError,
    clear_diagnostic_context,
    normalize_execution_error,
    set_diagnostic_context,
)
from SCPI_Library.session_manager import begin_visa_session_scope, close_visa_session_scope
from execution.measurement_report_exporter import MeasurementReportExporter
from execution.voltage_test_executor import VoltageTestExecutor
from execution.execution_journal import ExecutionJournal
from External_Auxiliary_Equipment.Temperature_Measurement import TemperatureMeasurement

class TestState(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


class TestCancelled(Exception):
    pass


class TestWorker(QThread):
    progress = pyqtSignal(str)
    progress_value = pyqtSignal(int) 
    finished = pyqtSignal()
    error = pyqtSignal(Exception, str)
    failed = pyqtSignal()
    warning = pyqtSignal(Exception, str)
    aborted = pyqtSignal() 
    new_data = pyqtSignal(float, float, float, float, float, float, float, float, float, float, float, float, float, float, float)  #Shamman changes for Vset, Iset, PSU readback voltage, and PSU readback current 
    popup_data = pyqtSignal(float, float, float, float, float, float, float, float, float, float) #Shamman changes
    test_failed = pyqtSignal(dict)   # send context
    resume_test = pyqtSignal()
    stop_test = pyqtSignal()
    state_changed = pyqtSignal(str)
    #fail_signal = pyqtSignal(float)     # send error value
    #decision_signal = pyqtSignal(bool)  # receive Continue / Abort

    def __init__(self, checkbox_state, dict, params):
        super().__init__()
        self.params = params  # shared Parameters object
        self.run_context = params.get("run_context")
        self.checkbox_states = checkbox_state
        self.dict = dict

        self.infoList = []
        self.dataList = []
        self.dataList2 = []
        self.ProgrammingV_percent_error_list = []
        self.ReadbackV_percent_error_list = []
        self.results = []
        self.results2 = []
        self.currenttime = None

        self.was_aborted = False
        self._control = threading.Condition()
        self._paused = False
        self._stop_requested = False
        self.state = TestState.IDLE
        self.force_exit = False   # ✅ Add this line
        self.report_exporter = MeasurementReportExporter(self)
        self.voltage_executor = VoltageTestExecutor(self, self.report_exporter)
        self.current_executor = CurrentTestExecutor(self, self.report_exporter)
        self.execution_journal = None
        self.temperature_monitor = None

    def _set_state(self, state):
        if state == self.state:
            return
        self.state = state
        self.state_changed.emit(state.value)

    @property
    def is_paused(self):
        with self._control:
            return self._paused

    def pause(self):
        with self._control:
            if not self._stop_requested and self.state == TestState.RUNNING:
                self._paused = True
                self._set_state(TestState.PAUSING)

    def resume(self):
        with self._control:
            if self.state != TestState.PAUSED:
                return
            self._paused = False
            self._set_state(TestState.RUNNING)
            self._control.notify_all()

    def stop(self):
        self.request_stop()

    def request_stop(self):
        with self._control:
            if self._stop_requested:
                return
            self._stop_requested = True
            self._paused = False
            self.was_aborted = True
            self._set_state(TestState.STOPPING)
            self._control.notify_all()

    def checkpoint(self):
        with self._control:
            if self._paused and self.state == TestState.PAUSING:
                self._set_state(TestState.PAUSED)
            while self._paused and not self._stop_requested:
                self._control.wait(timeout=0.25)
            if self._stop_requested:
                raise TestCancelled("Test stopped by operator")

    def interruptible_sleep(self, seconds):
        deadline = monotonic_time() + max(0.0, float(seconds))
        while True:
            self.checkpoint()
            remaining = deadline - monotonic_time()
            if remaining <= 0:
                return
            with self._control:
                self._control.wait(timeout=min(0.1, remaining))

    def _execute_checkpointed(self, operation, *args, **kwargs):
        self.checkpoint()
        result = operation(*args, **kwargs)
        self.checkpoint()
        return result

    def safe_shutdown(self):
        result = shutdown_instruments(self.dict)
        if result.succeeded:
            return

        failure_details = [failure.to_dict() for failure in result.failures]
        traceback_text = "\n\n".join(
            failure.traceback_text for failure in result.failures
        )
        cleanup_error = CleanupError(
            f"Instrument shutdown completed with {len(result.failures)} warning(s)",
            operation="shutdown_instruments",
            dut=self.params.get("DUT"),
            attempted_roles=list(result.attempted_roles),
            failures=failure_details,
        )
        self.warning.emit(cleanup_error, traceback_text)

    def close_visa_sessions(self):
        failures = close_visa_session_scope()
        if not failures:
            return

        cleanup_error = CleanupError(
            f"VISA session cleanup completed with {len(failures)} warning(s)",
            operation="close_visa_sessions",
            dut=self.params.get("DUT"),
            failures=[failure.to_dict() for failure in failures],
        )
        traceback_text = "\n\n".join(
            failure.traceback_text for failure in failures
        )
        self.warning.emit(cleanup_error, traceback_text)

    '''@pyqtSlot(bool)         #Shamman changes
    def receive_decision(self, decision):
        self.decision = decision'''

    def _write_config_csv(self, file_name):
        return self.report_exporter.write_config_csv(file_name)

    def _dispatch_dut_tests(self, loop_index):
        if self.params["DUT"] == "Dolphin":
            self._run_dolphin_tests(loop_index)
        elif self.params["DUT"] == "Hornbill":
            self._run_hornbill_tests(loop_index)

    def _start_temperature_monitor(self):
        if not self.checkbox_states.get("Temperature"):
            return
        output_file = None
        if self.run_context:
            output_file = self.run_context.storage.raw / "temperature.csv"
        self.temperature_monitor = TemperatureMeasurement(
            self.dict["DAQ"],
            output_file=output_file,
        )
        self._execute_checkpointed(self.temperature_monitor.configure)
        self.progress.emit("DAQ973A temperature monitoring enabled")

    def _record_temperature(self, loop_index):
        if not self.temperature_monitor:
            return
        sample = self._execute_checkpointed(
            self.temperature_monitor.measure,
            loop_index,
        )
        self.progress.emit(sample.status_text())

    def _close_temperature_monitor(self):
        if not self.temperature_monitor:
            return
        try:
            try:
                self.temperature_monitor.close()
            except Exception as exception:
                self.progress.emit(
                    f"DAQ973A close warning: {exception}"
                )
        finally:
            self.temperature_monitor = None

    def _run_dolphin_tests(self, loop_index):
        if self.checkbox_states["Voltage_Test"]:
            self._run_dolphin_voltage_tests(loop_index)
        elif self.checkbox_states["Current_Test"]:
            self._run_dolphin_current_tests(loop_index)

        if self.force_exit:
            return

    def _run_dolphin_voltage_tests(self, loop_index):
        return self.voltage_executor.run_dolphin(loop_index)

    def _run_voltage_auxiliary_tests(self):
        return self.voltage_executor.run_auxiliary()

    def _run_dolphin_current_tests(self, loop_index):
        return self.current_executor.run_dolphin(loop_index)

    def _run_current_auxiliary_tests(self, loop_index):
        return self.current_executor.run_auxiliary(loop_index)

    def _run_power_test(self, loop_index, selection):
        return self.current_executor.run_power_test(loop_index, selection)

    def _export_power_accuracy(
        self,
        info_list,
        data_list,
        readback_list,
    ):
        return self.current_executor.export_power_accuracy(
            info_list,
            data_list,
            readback_list,
        )

    def _run_hornbill_tests(self, loop_index):
        if self.checkbox_states["Voltage_Test"]:
            self._run_hornbill_voltage_tests(loop_index)
        elif self.checkbox_states["Current_Test"]:
            self._run_hornbill_current_tests(loop_index)

        if self.force_exit:
            return

    def _run_hornbill_voltage_tests(self, loop_index):
        return self.voltage_executor.run_hornbill(loop_index)

    def _selected_voltage_accuracy_runner(self, runners):
        return self.voltage_executor.selected_accuracy_runner(runners)

    def _run_voltage_accuracy(self, loop_index, runner):
        return self.voltage_executor.run_accuracy(loop_index, runner)

    def _run_dolphin_voltage_accuracy(self, loop_index):
        return self.voltage_executor.run_dolphin_accuracy(loop_index)

    def _run_hornbill_voltage_accuracy(self, loop_index):
        return self.voltage_executor.run_hornbill_accuracy(loop_index)

    def _run_selected_voltage_accuracy(self, loop_index, runners):
        return self.voltage_executor.run_selected_accuracy(loop_index, runners)

    def _export_voltage_accuracy(
        self,
        info_list,
        data_list,
        readback_list,
    ):
        return self.voltage_executor.export_accuracy(
            info_list,
            data_list,
            readback_list,
        )

    def _run_current_accuracy(self, loop_index, runner):
        return self.current_executor.run_accuracy(loop_index, runner)

    def _run_dolphin_current_accuracy(self, loop_index):
        return self.current_executor.run_dolphin_accuracy(loop_index)

    def _selected_hornbill_current_accuracy_runner(self):
        return self.current_executor.selected_hornbill_accuracy_runner()

    def _run_hornbill_current_accuracy(self, loop_index):
        return self.current_executor.run_hornbill_accuracy(loop_index)

    def _export_current_accuracy(
        self,
        info_list,
        data_list,
        readback_list,
    ):
        return self.current_executor.export_accuracy(
            info_list,
            data_list,
            readback_list,
        )

    def _run_hornbill_current_tests(self, loop_index):
        return self.current_executor.run_hornbill(loop_index)

    def run(self):
        cancelled = False
        failed = False
        selected_tests = [
            name for name, selected in self.checkbox_states.items() if selected
        ]
        instrument_roles = {}
        for role in ("PSU", "DMM", "DMM2", "ELoad", "ACSource", "OSC", "DAQ"):
            address = self.dict.get(role)
            if address:
                instrument_roles[str(address)] = role
        diagnostic_context = {
            "dut": self.params.get("DUT"),
            "test": selected_tests,
            "instrument_roles": instrument_roles,
        }
        self._set_state(TestState.RUNNING)
        set_execution_worker(self)
        set_diagnostic_context(**diagnostic_context)
        try:
            if self.run_context:
                self.run_context.activate_data_paths()
                self.execution_journal = ExecutionJournal.for_run(
                    self.run_context,
                    self.params.get("resume_run_directory"),
                )
            begin_visa_session_scope()
            self._start_temperature_monitor()
            start_loop = (
                self.execution_journal.next_loop_index
                if self.execution_journal
                else 0
            )
            if start_loop:
                self.progress.emit(
                    f"Resuming safely from completed loop {start_loop}"
                )
            for x in range(start_loop, int(self.params["noofloop"])):
                self.checkpoint()
                #Execute Voltage Measurement for each test checked---------------
                #Voltage Accuracy Test
                self._dispatch_dut_tests(x)
                self._record_temperature(x)
                if self.force_exit:
                    return
                if self.execution_journal:
                    self.execution_journal.complete_loop(x)

            if not self.force_exit:
                self.progress_value.emit(100)
                self.progress.emit("All measurements completed!")

                
                                    
        except TestCancelled:
            cancelled = True
            self.progress.emit("Test stopped by operator. Disabling instrument outputs...")
        except Exception as e:
            failed = True
            tb = traceback.format_exc()
            normalized_error = normalize_execution_error(
                e,
                tb,
                dut=self.params.get("DUT"),
                test=selected_tests,
            )
            self.error.emit(normalized_error, tb)
        finally:
            self._close_temperature_monitor()
            self.close_visa_sessions()
            self.safe_shutdown()
            clear_execution_worker()
            clear_diagnostic_context()
            if failed:
                self._set_state(TestState.FAILED)
                self.failed.emit()
            elif cancelled or self.was_aborted:
                self._set_state(TestState.ABORTED)
                self.aborted.emit()
            else:
                self._set_state(TestState.COMPLETED)
                self.finished.emit()

