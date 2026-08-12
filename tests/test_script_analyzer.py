import os
import sys
import tempfile
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from PyQt5.QtWidgets import QApplication

from analysis.test_script_analyzer import (
    analyze_test_script,
    build_scpi_command_catalog,
)
from ui.test_script_assistant_tab import TestScriptAssistantTab


SAMPLE_SCRIPT = '''
import time
import pyvisa

VISA_ADDRESS = "TCPIP0::example-psu::inst0::INSTR"

def run_test():
    manager = pyvisa.ResourceManager()
    dut = manager.open_resource(VISA_ADDRESS)
    try:
        for channel in range(1, 3):
            dut.write(f"SENSe:SWEep:POINts 100000, (@{channel})")
            time.sleep(0.5)
            dut.query(f"MEAS:VOLT? (@{channel})")
            dut.query("SYST:ERR?")
    finally:
        dut.close()
        manager.close()
'''


CV_STYLE_SCRIPT = '''
import keyboard
import numpy as np
import pandas as pd
import pyvisa
import socket

def send_scpi_command(sock, command):
    sock.send((command + "\\n").encode())
    return sock.recv(1024).decode().strip()

HOST = "hornbill-lab"
PORT = 5025
manager = pyvisa.ResourceManager()
VOUT = manager.open_resource("USB0::DMM::INSTR")
CURR = manager.open_resource("USB0::ELOAD::INSTR")
VOUT.write(":CONFigure:VOLTage:DC %s,%s" % ("DEFault", "MIN"))
curr_start = float(input("Starting current: "))
curr_step = float(input("Current step: "))
power_lim = 300
data = pd.DataFrame({"Set Voltage (V)": [], "VMON (V)": []})
data.to_excel("C:/Users/example/results.xlsx")

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    sock.send(("OUTP ON,(@1)" + "\\n").encode())
    sweep_values = np.arange(3, 61, 3)
    for voltage in sweep_values:
        command = f"VOLT {voltage},(@1)"
        sock.send((command + "\\n").encode())
        send_scpi_command(sock, "DIAG:PEEK? 20,0")
        if keyboard.is_pressed("a"):
            break
    while 1:
        VOUT.query_ascii_values(":STATus:OPERation:CONDition?")
        break
except:
    pass
finally:
    sock.close()
    VOUT.close()
    CURR.close()
    manager.close()
'''


MULTI_LIBRARY_SCRIPT = '''
import pyvisa

manager = pyvisa.ResourceManager()
VOUT = manager.open_resource("USB0::DMM::INSTR")
CURR = manager.open_resource("USB0::ELOAD::INSTR")
VOUT.write("*TRG")
CURR.write("CURR 1,(@2)")
'''


class TestScriptAnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def analyze_sample(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        script_path = Path(directory.name) / "external_test.py"
        script_path.write_text(SAMPLE_SCRIPT, encoding="utf-8")
        return analyze_test_script(script_path)

    def test_detects_test_structure_without_executing_script(self):
        analysis = self.analyze_sample()

        self.assertEqual(analysis.functions, ["run_test"])
        self.assertEqual(
            analysis.visa_addresses,
            ["TCPIP0::example-psu::inst0::INSTR"],
        )
        self.assertEqual(len(analysis.commands), 3)
        self.assertEqual(analysis.commands[0].operation, "write")
        self.assertIn("SENSe:SWEep:POINts", analysis.commands[0].command)
        self.assertTrue(analysis.commands[0].mappings)
        self.assertEqual(analysis.delays[0].expression, "0.5")
        self.assertEqual(analysis.loops[0].kind, "for")
        self.assertFalse(
            any("no close()" in warning.lower() for warning in analysis.warnings)
        )
        self.assertTrue(
            any("hardcoded visa" in warning.lower() for warning in analysis.warnings)
        )

    def test_assistant_displays_commands_warnings_and_plan(self):
        analysis = self.analyze_sample()
        tab = TestScriptAssistantTab()
        self.addCleanup(tab.deleteLater)

        tab.show_analysis(analysis)

        self.assertEqual(tab.command_table.rowCount(), 3)
        self.assertIn("Analysis complete", tab.status_label.text())
        self.assertIn("Hardcoded VISA", tab.warning_output.toPlainText())
        self.assertIn("TestWorker checkpoints", tab.integration_output.toPlainText())
        self.assertTrue(tab.export_button.isEnabled())

    def test_invalid_python_reports_the_source_line(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "broken.py"
            script_path.write_text("def broken(:\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "line 1"):
                analyze_test_script(script_path)

    def test_resolves_socket_wrappers_parameters_roles_and_safety_risks(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "cv_style.py"
            script_path.write_text(CV_STYLE_SCRIPT, encoding="utf-8")

            analysis = analyze_test_script(script_path)

        commands = {item.command for item in analysis.commands}
        self.assertIn(":CONFigure:VOLTage:DC DEFault,MIN", commands)
        self.assertIn("OUTP ON,(@1)", commands)
        self.assertIn("VOLT {voltage},(@1)", commands)
        self.assertIn("DIAG:PEEK? 20,0", commands)
        self.assertEqual(
            [(item.name, item.conversion) for item in analysis.parameters],
            [("curr_start", "float"), ("curr_step", "float")],
        )
        self.assertEqual(analysis.safety_limits[0].name, "power_lim")
        self.assertEqual(analysis.sweeps[0].stop, "61")
        self.assertEqual(
            {item.variable: item.role for item in analysis.instrument_roles},
            {"CURR": "ELOAD", "VOUT": "DMM", "sock": "DUT/Hornbill"},
        )
        self.assertEqual(
            analysis.data_fields,
            ["Set Voltage (V)", "VMON (V)"],
        )
        warning_text = "\n".join(analysis.warnings)
        self.assertIn("no detected timeout", warning_text)
        self.assertIn("Unbounded while-loop", warning_text)
        self.assertIn("outside a cleanup-protected", warning_text)
        self.assertIn("Bare except", warning_text)
        self.assertIn("user-specific output", warning_text)

    def test_maps_commands_across_scpi_libraries(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "multi_library.py"
            script_path.write_text(MULTI_LIBRARY_SCRIPT, encoding="utf-8")

            analysis = analyze_test_script(script_path)

        mappings_by_command = {
            finding.command: finding.mappings for finding in analysis.commands
        }
        self.assertIn("IEEEStandard.TRG", mappings_by_command["*TRG"])
        self.assertEqual(
            mappings_by_command["CURR 1,(@2)"][0],
            "ELOAD_E363XXA.setOutputCurrent",
        )

    def test_catalog_namespaces_non_keysight_libraries(self):
        library_directory = ROOT / "SCPI_Library"
        catalog, _known_classes = build_scpi_command_catalog(
            (
                library_directory / "IEEEStandard.py",
                library_directory / "Chroma.py",
                library_directory / "Keithley.py",
            )
        )
        mapping_names = {entry[1] for entry in catalog}

        self.assertIn("IEEEStandard.TRG", mapping_names)
        self.assertTrue(any(name.startswith("Chroma.") for name in mapping_names))
        self.assertTrue(any(name.startswith("Keithley.") for name in mapping_names))


if __name__ == "__main__":
    unittest.main()
