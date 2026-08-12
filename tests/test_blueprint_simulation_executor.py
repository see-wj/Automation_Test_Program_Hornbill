import csv
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from analysis.blueprint_execution import enrich_blueprint_execution_metadata
from execution.blueprint_simulation_executor import (
    BlueprintExecutionControl,
    BlueprintSimulationCancelled,
    BlueprintSimulationExecutor,
)


class BlueprintSimulationExecutorTests(unittest.TestCase):
    def setUp(self):
        blueprint_path = ROOT / "Test Script Analyzer" / "CV Load Full.blueprint.json"
        self.blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
        self.configuration = {
            "simulation_mode": True,
            "instruments": {
                item["variable"]: item["address"]
                for item in self.blueprint["instruments"]
            },
            "parameters": {
                "curr_start": 0.0,
                "curr_step": 10.0,
                "volt_start": 0.0,
                "volt_step": 30.0,
            },
        }

    def test_schema_upgrade_binds_arguments_and_nested_execution(self):
        upgraded = enrich_blueprint_execution_metadata(self.blueprint)
        bindings = {item["line"]: item for item in upgraded["command_bindings"]}

        self.assertEqual(upgraded["schema_version"], 2)
        self.assertEqual(
            bindings[23]["arguments"],
            [
                {
                    "name": "mode",
                    "expression": "VOLTage:DC DEFault,MIN",
                    "source": "literal",
                }
            ],
        )
        self.assertEqual(
            bindings[130]["arguments"],
            [
                {"name": "Value", "expression": "v", "source": "loop"},
                {
                    "name": "ChannelNumber",
                    "expression": "1",
                    "source": "literal",
                },
            ],
        )
        self.assertEqual(
            upgraded["execution_plan"]["template"],
            "cv_voltage_current_sweep_v1",
        )
        self.assertEqual(
            upgraded["execution_plan"]["shutdown_command_lines"],
            [238, 239],
        )

    def test_simulation_runs_sweeps_writes_csv_and_shuts_down(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = BlueprintSimulationExecutor(
                self.blueprint,
                self.configuration,
                output_root=directory,
            )

            result = executor.run()

            self.assertEqual(len(result.rows), 9)
            self.assertTrue(result.csv_path.is_file())
            self.assertTrue((result.run_directory / "SIMULATION_RUN.txt").is_file())
            with result.csv_path.open(newline="", encoding="utf-8") as csv_file:
                self.assertEqual(len(list(csv.DictReader(csv_file))), 9)
            commands = [command for _address, command in result.command_log]
            self.assertIn("VOLT 30, (@1)", commands)
            self.assertIn("SOUR:CURR:LEV:IMM:AMPL 10,(@2)", commands)
            self.assertEqual(commands[-2:], ["OUTP OFF,(@2)", "OUTP OFF,(@1)"])

    def test_abort_saves_partial_results_and_guarantees_shutdown(self):
        control = BlueprintExecutionControl()

        def abort_after_first_point(_message, completed, _total):
            if completed == 1:
                control.abort()

        with tempfile.TemporaryDirectory() as directory:
            executor = BlueprintSimulationExecutor(
                self.blueprint,
                self.configuration,
                output_root=directory,
                control=control,
                progress_callback=abort_after_first_point,
            )

            with self.assertRaises(BlueprintSimulationCancelled):
                executor.run()

            self.assertEqual(len(executor.rows), 1)
            commands = [command for _address, command in executor.manager.state.command_log]
            self.assertEqual(commands[-2:], ["OUTP OFF,(@2)", "OUTP OFF,(@1)"])
            csv_path = executor.run_context.storage.raw / "blueprint_simulation_results.csv"
            self.assertTrue(csv_path.is_file())

    def test_physical_execution_is_rejected(self):
        configuration = dict(self.configuration)
        configuration["simulation_mode"] = False

        with tempfile.TemporaryDirectory() as directory:
            executor = BlueprintSimulationExecutor(
                self.blueprint,
                configuration,
                output_root=directory,
            )
            with self.assertRaisesRegex(ValueError, "restricted to simulation"):
                executor.run()

    def test_pause_blocks_checkpoint_until_resume(self):
        control = BlueprintExecutionControl()
        passed_checkpoint = threading.Event()
        control.pause()
        thread = threading.Thread(
            target=lambda: (control.checkpoint(), passed_checkpoint.set()),
            daemon=True,
        )
        thread.start()
        time.sleep(0.05)

        self.assertFalse(passed_checkpoint.is_set())
        control.resume()
        thread.join(timeout=1)
        self.assertTrue(passed_checkpoint.is_set())


if __name__ == "__main__":
    unittest.main()
