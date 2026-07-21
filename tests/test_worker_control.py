import threading
import unittest
from unittest.mock import patch

import GUI
from execution import current_test_executor
from execution import measurement_report_exporter
from execution import test_worker
from execution import voltage_test_executor
from DUT_Test_Scripts.Hornbill.Hornbill_DUT_Test_With_ELoad import (
    HornbillVoltageMeasurementwithELoadwithOscilloscope,
)
from DUT_Test_Scripts.instrument_shutdown import ShutdownResult
from SCPI_Library.instrument_errors import TestExecutionError as ExecutionFailure
from execution.test_worker import TestCancelled, TestState, TestWorker


class Parameters(dict):
    __getattr__ = dict.get


def create_worker():
    return TestWorker(
        {},
        {},
        Parameters(DUT="Unknown", noofloop=1),
    )


class WorkerControlTests(unittest.TestCase):
    def test_gui_reexports_worker_types(self):
        self.assertIs(GUI.TestWorker, TestWorker)
        self.assertIs(GUI.TestState, TestState)
        self.assertIs(GUI.TestCancelled, TestCancelled)

    def test_worker_injects_shared_report_exporter(self):
        worker = create_worker()

        self.assertIs(worker.voltage_executor.report_exporter, worker.report_exporter)
        self.assertIs(worker.current_executor.report_exporter, worker.report_exporter)

    def test_dut_dispatch_selects_dolphin_runner(self):
        worker = create_worker()
        worker.params["DUT"] = "Dolphin"

        with patch.object(worker, "_run_dolphin_tests") as dolphin, patch.object(
            worker, "_run_hornbill_tests"
        ) as hornbill:
            worker._dispatch_dut_tests(2)

        dolphin.assert_called_once_with(2)
        hornbill.assert_not_called()

    def test_dut_dispatch_selects_hornbill_runner(self):
        worker = create_worker()
        worker.params["DUT"] = "Hornbill"

        with patch.object(worker, "_run_dolphin_tests") as dolphin, patch.object(
            worker, "_run_hornbill_tests"
        ) as hornbill:
            worker._dispatch_dut_tests(3)

        hornbill.assert_called_once_with(3)
        dolphin.assert_not_called()

    def test_unknown_dut_does_not_run_a_dut_handler(self):
        worker = create_worker()

        with patch.object(worker, "_run_dolphin_tests") as dolphin, patch.object(
            worker, "_run_hornbill_tests"
        ) as hornbill:
            worker._dispatch_dut_tests(0)

        dolphin.assert_not_called()
        hornbill.assert_not_called()

    def test_temperature_monitor_is_optional(self):
        worker = create_worker()

        with patch("execution.test_worker.TemperatureMeasurement") as monitor:
            worker._start_temperature_monitor()

        monitor.assert_not_called()

    def test_temperature_monitor_records_selected_run(self):
        worker = create_worker()
        worker.checkbox_states = {"Temperature": True}
        worker.dict = {"DAQ": "USB0::DAQ::INSTR"}
        sample = type("Sample", (), {"status_text": lambda self: "Temperature: 20 C"})()

        with patch("execution.test_worker.TemperatureMeasurement") as monitor_class:
            monitor = monitor_class.return_value
            monitor.measure.return_value = sample
            worker._start_temperature_monitor()
            worker._record_temperature(2)
            worker._close_temperature_monitor()

        monitor_class.assert_called_once_with(
            "USB0::DAQ::INSTR",
            output_file=None,
        )
        monitor.configure.assert_called_once_with()
        monitor.measure.assert_called_once_with(2)
        monitor.close.assert_called_once_with()

    def test_dolphin_mode_dispatch_selects_voltage_handler(self):
        worker = create_worker()
        worker.checkbox_states = {"Voltage_Test": True, "Current_Test": False}

        with patch.object(worker, "_run_dolphin_voltage_tests") as voltage, patch.object(
            worker, "_run_dolphin_current_tests"
        ) as current:
            worker._run_dolphin_tests(4)

        voltage.assert_called_once_with(4)
        current.assert_not_called()

    def test_hornbill_mode_dispatch_selects_current_handler(self):
        worker = create_worker()
        worker.checkbox_states = {"Voltage_Test": False, "Current_Test": True}

        with patch.object(worker, "_run_hornbill_voltage_tests") as voltage, patch.object(
            worker, "_run_hornbill_current_tests"
        ) as current:
            worker._run_hornbill_tests(5)

        current.assert_called_once_with(5)
        voltage.assert_not_called()

    def test_dut_voltage_handlers_run_shared_auxiliary_tests(self):
        cases = (
            ("_run_dolphin_voltage_tests", "run_dolphin_accuracy"),
            ("_run_hornbill_voltage_tests", "run_hornbill_accuracy"),
        )

        for handler_name, accuracy_name in cases:
            with self.subTest(handler=handler_name):
                worker = create_worker()
                executor = worker.voltage_executor
                with patch.object(
                    executor,
                    accuracy_name,
                    return_value=False,
                ) as accuracy, patch.object(
                    executor,
                    "run_auxiliary",
                ) as auxiliary:
                    getattr(worker, handler_name)(3)

                accuracy.assert_called_once_with(3)
                auxiliary.assert_called_once_with()

    def test_aborted_voltage_accuracy_skips_auxiliary_tests(self):
        cases = (
            ("_run_dolphin_voltage_tests", "run_dolphin_accuracy"),
            ("_run_hornbill_voltage_tests", "run_hornbill_accuracy"),
        )

        for handler_name, accuracy_name in cases:
            with self.subTest(handler=handler_name):
                worker = create_worker()
                executor = worker.voltage_executor
                with patch.object(
                    executor,
                    accuracy_name,
                    return_value=True,
                ), patch.object(
                    executor,
                    "run_auxiliary",
                ) as auxiliary:
                    getattr(worker, handler_name)(3)

                auxiliary.assert_not_called()

    def test_dut_current_handlers_run_shared_auxiliary_tests(self):
        worker = create_worker()
        executor = worker.current_executor
        with patch.object(
            executor,
            "run_dolphin_accuracy",
            return_value=False,
        ) as accuracy, patch.object(
            executor,
            "run_auxiliary",
        ) as auxiliary, patch.object(executor, "run_power_test") as power:
            worker._run_dolphin_current_tests(3)

        accuracy.assert_called_once_with(3)
        auxiliary.assert_called_once_with(3)
        power.assert_not_called()

        worker = create_worker()
        executor = worker.current_executor
        with patch.object(
            executor,
            "run_hornbill_accuracy",
            return_value=False,
        ) as accuracy, patch.object(
            executor,
            "run_auxiliary",
        ) as auxiliary, patch.object(executor, "run_power_test") as power:
            worker._run_hornbill_current_tests(4)

        accuracy.assert_called_once_with(4)
        auxiliary.assert_called_once_with(4)
        power.assert_called_once_with(4, "Peak_Power_Test")

    def test_aborted_current_accuracy_skips_auxiliary_tests(self):
        cases = (
            ("_run_dolphin_current_tests", "run_dolphin_accuracy"),
            ("_run_hornbill_current_tests", "run_hornbill_accuracy"),
        )

        for handler_name, accuracy_name in cases:
            with self.subTest(handler=handler_name):
                worker = create_worker()
                executor = worker.current_executor
                with patch.object(
                    executor,
                    accuracy_name,
                    return_value=True,
                ), patch.object(
                    executor,
                    "run_auxiliary",
                ) as auxiliary, patch.object(
                    executor,
                    "run_power_test",
                ) as power:
                    getattr(worker, handler_name)(3)

                auxiliary.assert_not_called()
                power.assert_not_called()

    def test_current_auxiliary_uses_power_accuracy_selection(self):
        worker = create_worker()

        with patch.object(worker.current_executor, "run_power_test") as power:
            worker._run_current_auxiliary_tests(2)

        power.assert_called_once_with(2, "PowerAccuracy")

    def test_power_test_exports_only_on_final_loop(self):
        worker = TestWorker(
            {
                "PowerAccuracy": True,
                "Voltage_Test": False,
                "Current_Test": True,
                "DataReport": True,
            },
            {},
            Parameters(noofloop=2),
        )
        measurement = (["info"], ["measured"], ["readback"])
        with patch.object(
            current_test_executor.PowerMeasurement,
            "executePowerMeasurementA",
            return_value=measurement,
        ), patch.object(worker.current_executor, "export_power_accuracy") as export:
            worker._run_power_test(0, "PowerAccuracy")
            export.assert_not_called()

            worker._run_power_test(1, "PowerAccuracy")

        export.assert_called_once_with(
            ["info"],
            ["measured"],
            ["readback"],
        )

    def test_voltage_modes_use_configured_accuracy_runner(self):
        cases = (
            (
                "Dolphin",
                voltage_test_executor.DOLPHIN_VOLTAGE_ACCURACY_RUNNERS,
                "_run_dolphin_voltage_accuracy",
            ),
            (
                "Hornbill",
                voltage_test_executor.HORNBILL_VOLTAGE_ACCURACY_RUNNERS,
                "_run_hornbill_voltage_accuracy",
            ),
        )

        for dut, runners, method_name in cases:
            for selection in tuple(runners):
                with self.subTest(dut=dut, selection=selection):
                    channels = []

                    def runner(
                        _worker,
                        _configuration,
                        channel,
                        worker=None,
                    ):
                        channels.append(channel)
                        return ["info"], ["measured"], ["readback"]

                    worker = TestWorker(
                        {
                            "VoltageAccuracy": True,
                            selection: True,
                            "DataReport": False,
                        },
                        {"Instrument": "Keysight"},
                        Parameters(
                            DUT=dut,
                            noofloop=1,
                            PSU_Channel=[1, 2],
                        ),
                    )
                    with patch.dict(
                        runners,
                        {selection: runner},
                        clear=True,
                    ):
                        getattr(worker, method_name)(0)

                    self.assertEqual(channels, [1, 2])

    def test_hornbill_scope_mode_uses_scope_capture_class(self):
        runner = voltage_test_executor.HORNBILL_VOLTAGE_ACCURACY_RUNNERS[
            "CurrentStatic(VoltageChange)withOscilloscope"
        ]

        self.assertIs(
            runner,
            HornbillVoltageMeasurementwithELoadwithOscilloscope.Execute_Voltage_Accuracy_Current_Static,
        )

    def test_voltage_accuracy_exports_only_on_final_loop(self):
        def runner(_worker, _configuration, _channel, worker=None):
            return ["info"], ["measured"], ["readback"]

        worker = TestWorker(
            {"DataReport": True},
            {"Instrument": "Keysight"},
            Parameters(noofloop=2, PSU_Channel=[1]),
        )
        with patch.object(worker.voltage_executor, "export_accuracy") as export:
            worker._run_voltage_accuracy(0, runner)
            export.assert_not_called()

            worker._run_voltage_accuracy(1, runner)

        export.assert_called_once_with(
            ["info"],
            ["measured"],
            ["readback"],
        )

    def test_voltage_accuracy_skips_export_when_report_disabled(self):
        def runner(_worker, _configuration, _channel, worker=None):
            return ["info"], ["measured"], ["readback"]

        worker = TestWorker(
            {"DataReport": False},
            {"Instrument": "Keysight"},
            Parameters(noofloop=1, PSU_Channel=[1]),
        )
        with patch.object(worker.voltage_executor, "export_accuracy") as export:
            worker._run_voltage_accuracy(0, runner)

        export.assert_not_called()

    def test_hornbill_current_ranges_use_configured_accuracy_runner(self):
        range_selections = tuple(
            current_test_executor.HORNBILL_CURRENT_ACCURACY_RUNNERS
        )

        for selection in range_selections:
            with self.subTest(selection=selection):
                channels = []

                def runner(_worker, _configuration, channel):
                    channels.append(channel)
                    return ["info"], ["measured"], ["readback"]

                worker = TestWorker(
                    {
                        "CurrentAccuracy": True,
                        selection: True,
                        "DataReport": False,
                    },
                    {"Instrument": "Keysight"},
                    Parameters(
                        DUT="Hornbill",
                        noofloop=1,
                        PSU_Channel=[1, 2],
                    ),
                )
                with patch.dict(
                    current_test_executor.HORNBILL_CURRENT_ACCURACY_RUNNERS,
                    {selection: runner},
                    clear=True,
                ):
                    worker._run_hornbill_current_tests(0)

                self.assertEqual(channels, [1, 2])

    def test_dolphin_current_accuracy_uses_shared_runner(self):
        worker = TestWorker(
            {
                "CurrentAccuracy": True,
                "DataReport": False,
            },
            {"Instrument": "Keysight"},
            Parameters(
                DUT="Dolphin",
                noofloop=1,
                PSU_Channel=[1],
            ),
        )

        with patch.object(
            worker.current_executor,
            "run_accuracy",
            return_value=False,
        ) as run_accuracy:
            worker._run_dolphin_current_accuracy(0)

        run_accuracy.assert_called_once_with(
            0,
            current_test_executor.execute_dolphin_current_accuracy,
        )

    def test_dolphin_current_adapter_binds_measurement_worker(self):
        worker = create_worker()
        configuration = {"Instrument": "Keysight"}

        with patch.object(
            current_test_executor,
            "NewCurrentMeasurement",
        ) as measurement_type:
            result = current_test_executor.execute_dolphin_current_accuracy(
                worker,
                configuration,
                1,
            )

        measurement_method = (
            measurement_type.return_value.executeCurrentMeasurementA
        )
        measurement_method.assert_called_once_with(configuration, 1, worker)
        self.assertIs(result, measurement_method.return_value)

    def test_hornbill_current_accuracy_exports_only_on_final_loop(self):
        def runner(_worker, _configuration, _channel):
            return ["info"], ["measured"], ["readback"]

        worker = TestWorker(
            {
                "CurrentAccuracy": True,
                "CurrentAccuracy_20A_Range": True,
                "DataReport": True,
            },
            {"Instrument": "Keysight"},
            Parameters(
                DUT="Hornbill",
                noofloop=2,
                PSU_Channel=[1],
            ),
        )
        with patch.dict(
            current_test_executor.HORNBILL_CURRENT_ACCURACY_RUNNERS,
            {"CurrentAccuracy_20A_Range": runner},
            clear=True,
        ), patch.object(worker.current_executor, "export_accuracy") as export:
            worker._run_hornbill_current_tests(0)
            export.assert_not_called()

            worker._run_hornbill_current_tests(1)

        export.assert_called_once_with(
            ["info"],
            ["measured"],
            ["readback"],
        )

    def test_pause_resume_and_stop_checkpoint(self):
        worker = create_worker()
        worker.state = TestState.RUNNING

        worker.pause()
        self.assertTrue(worker.is_paused)
        self.assertEqual(worker.state, TestState.PAUSING)

        checkpoint_reached = threading.Event()

        def reach_checkpoint():
            checkpoint_reached.set()
            worker.checkpoint()

        checkpoint_thread = threading.Thread(target=reach_checkpoint)
        checkpoint_thread.start()
        self.assertTrue(checkpoint_reached.wait(timeout=1.0))
        for _ in range(100):
            if worker.state == TestState.PAUSED:
                break
            threading.Event().wait(0.01)
        self.assertEqual(worker.state, TestState.PAUSED)

        worker.resume()
        self.assertFalse(worker.is_paused)
        self.assertEqual(worker.state, TestState.RUNNING)
        checkpoint_thread.join(timeout=1.0)
        self.assertFalse(checkpoint_thread.is_alive())

        worker.request_stop()
        self.assertEqual(worker.state, TestState.STOPPING)
        with self.assertRaises(TestCancelled):
            worker.checkpoint()

    def test_paused_checkpointed_operation_waits_for_resume(self):
        worker = create_worker()
        worker.state = TestState.RUNNING
        operation_started = threading.Event()
        operation_finished = threading.Event()

        def operation():
            operation_started.set()

        def run_operation():
            worker._execute_checkpointed(operation)
            operation_finished.set()

        worker.pause()
        self.assertEqual(worker.state, TestState.PAUSING)
        operation_thread = threading.Thread(target=run_operation)
        operation_thread.start()

        self.assertFalse(operation_started.wait(timeout=0.05))
        self.assertEqual(worker.state, TestState.PAUSED)
        worker.resume()
        self.assertTrue(operation_finished.wait(timeout=1.0))
        operation_thread.join(timeout=1.0)
        self.assertFalse(operation_thread.is_alive())

    def test_stop_after_voltage_channel_prevents_next_channel_and_export(self):
        channels = []

        def runner(_worker, _configuration, channel, worker=None):
            channels.append(channel)
            worker.request_stop()
            return ["info"], ["measured"], ["readback"]

        worker = TestWorker(
            {"DataReport": True},
            {},
            Parameters(noofloop=1, PSU_Channel=[1, 2]),
        )
        with patch.object(worker.voltage_executor, "export_accuracy") as export:
            with self.assertRaises(TestCancelled):
                worker._run_voltage_accuracy(0, runner)

        self.assertEqual(channels, [1])
        export.assert_not_called()

    def test_stop_after_auxiliary_measurement_skips_reports_and_later_tests(self):
        worker = TestWorker(
            {
                "VoltageLoadRegulation": True,
                "TransientRecovery": True,
                "SpecialCase": True,
                "NormalCase": False,
            },
            {},
            Parameters(Instrument="Keysight", PSU_Channel=[1]),
        )

        def stop_after_measurement(_worker, _configuration):
            worker.request_stop()
            return ["measurement"]

        with patch.object(
            voltage_test_executor.NewLoadRegulation,
            "executeCV_LoadRegulation",
            side_effect=stop_after_measurement,
        ), patch.object(
            voltage_test_executor,
            "datatoCSV_LoadRegulation",
        ) as export, patch.object(
            voltage_test_executor.RiseFallTime,
            "executeC",
        ) as transient:
            with self.assertRaises(TestCancelled):
                worker._run_voltage_auxiliary_tests()

        export.assert_not_called()
        transient.assert_not_called()

    def test_stop_during_export_prevents_remaining_report_steps(self):
        worker = TestWorker(
            {},
            {},
            Parameters(PSU="PSU", DMM="DMM", ELoad="ELoad"),
        )

        def stop_after_instrument_data(*_args):
            worker.request_stop()

        with patch.object(
            measurement_report_exporter,
            "instrumentData",
            side_effect=stop_after_instrument_data,
        ), patch.object(
            measurement_report_exporter,
            "datatoCSV_Accuracy",
        ) as export:
            with self.assertRaises(TestCancelled):
                worker._export_voltage_accuracy(
                    ["info"],
                    ["measured"],
                    ["readback"],
                )

        export.assert_not_called()

    def test_success_closes_sessions_before_hardware_shutdown(self):
        worker = create_worker()
        events = []
        terminal_signals = []
        worker.finished.connect(lambda: terminal_signals.append("finished"))
        worker.aborted.connect(lambda: terminal_signals.append("aborted"))
        worker.error.connect(lambda *_: terminal_signals.append("error"))

        with patch.object(
            test_worker, "begin_visa_session_scope", lambda: events.append("begin")
        ), patch.object(
            test_worker, "close_visa_session_scope", lambda: events.append("close") or ()
        ), patch.object(
            test_worker,
            "shutdown_instruments",
            lambda config: events.append("shutdown") or ShutdownResult((), ()),
        ):
            worker.run()

        self.assertEqual(events, ["begin", "close", "shutdown"])
        self.assertEqual(terminal_signals, ["finished"])
        self.assertEqual(worker.state, TestState.COMPLETED)

    def test_stop_emits_only_aborted_terminal_signal(self):
        worker = create_worker()
        terminal_signals = []
        worker.finished.connect(lambda: terminal_signals.append("finished"))
        worker.aborted.connect(lambda: terminal_signals.append("aborted"))
        worker.error.connect(lambda *_: terminal_signals.append("error"))
        worker.request_stop()

        with patch.object(test_worker, "begin_visa_session_scope", lambda: None), patch.object(
            test_worker, "close_visa_session_scope", lambda: ()
        ), patch.object(
            test_worker, "shutdown_instruments", lambda config: ShutdownResult((), ())
        ):
            worker.run()

        self.assertEqual(terminal_signals, ["aborted"])
        self.assertEqual(worker.state, TestState.ABORTED)

    def test_startup_failure_emits_contextual_error_and_still_shuts_down(self):
        worker = create_worker()
        events = []
        errors = []
        worker.error.connect(lambda error, trace: errors.append(error))

        def fail_startup():
            events.append("begin")
            raise RuntimeError("VISA startup failed")

        with patch.object(test_worker, "begin_visa_session_scope", fail_startup), patch.object(
            test_worker, "close_visa_session_scope", lambda: events.append("close") or ()
        ), patch.object(
            test_worker,
            "shutdown_instruments",
            lambda config: events.append("shutdown") or ShutdownResult((), ()),
        ):
            worker.run()

        self.assertEqual(events, ["begin", "close", "shutdown"])
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ExecutionFailure)
        self.assertEqual(worker.state, TestState.FAILED)


if __name__ == "__main__":
    unittest.main()
