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

from analysis.integration_blueprint import create_integration_blueprint
from analysis.gui_scaffold_generator import generate_gui_scaffold_source
from analysis.test_script_analyzer import analyze_test_script
from ui.blueprint_generated_gui import BlueprintGeneratedGui
from ui.integration_blueprint_review import IntegrationBlueprintReviewWidget


BLUEPRINT_SCRIPT = '''
import pyvisa

voltage_start = float(input("Starting voltage: "))
power_limit = 50
manager = pyvisa.ResourceManager()
DUT = manager.open_resource("TCPIP0::hornbill::inst0::INSTR")
try:
    DUT.write("VOLT 5,(@1)")
    DUT.query("SYST:ERR?")
finally:
    DUT.close()
    manager.close()
'''


SWEEP_SCRIPT = '''
import numpy as np

voltage_points = np.arange(0, 61, 1)
current_points = np.arange(0, 20.1, 1)
'''


class IntegrationBlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def analyze_script(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        script_path = Path(directory.name) / "blueprint_source.py"
        script_path.write_text(BLUEPRINT_SCRIPT, encoding="utf-8")
        return analyze_test_script(script_path)

    def test_blueprint_remains_review_required_without_explicit_approval(self):
        analysis = self.analyze_script()

        blueprint = create_integration_blueprint(
            analysis,
            test_name="Hornbill Imported Test",
            safety_settings={
                "maximum_voltage": "30",
                "maximum_current": "10",
                "maximum_power": "50",
            },
        )

        self.assertEqual(blueprint.status, "review_required")
        issue_text = "\n".join(blueprint.review_issues)
        self.assertIn("developer approval", issue_text)
        self.assertIn("explicit developer confirmation", issue_text)

    def test_fully_reviewed_blueprint_can_be_approved(self):
        analysis = self.analyze_script()
        command_settings = {
            index: {
                "approved": True,
                "selected_mapping": (
                    finding.mappings[0]
                    if finding.mappings
                    else "Hornbill.developerApprovedMethod"
                ),
            }
            for index, finding in enumerate(analysis.commands)
        }

        blueprint = create_integration_blueprint(
            analysis,
            test_name="Hornbill Imported Test",
            command_settings=command_settings,
            safety_settings={
                "maximum_voltage": "30",
                "maximum_current": "10",
                "maximum_power": "50",
                "polling_timeout_seconds": 30,
                "settling_delay_seconds": 1,
                "checkpoint_each_point": True,
                "guaranteed_shutdown": True,
                "confirmed_by_developer": True,
            },
        )

        self.assertEqual(blueprint.status, "approved")
        self.assertEqual(blueprint.review_issues, [])
        self.assertEqual(blueprint.parameters[0].name, "voltage_start")
        self.assertEqual(blueprint.safety.maximum_power, "50")

    def test_review_widget_requires_unmapped_command_and_safety_confirmation(self):
        analysis = self.analyze_script()
        widget = IntegrationBlueprintReviewWidget()
        self.addCleanup(widget.deleteLater)
        widget.set_analysis(analysis)
        widget.maximum_voltage_input.setText("30")
        widget.maximum_current_input.setText("10")
        widget.maximum_power_input.setText("50")
        widget.approve_suggested_mappings()

        first_blueprint = widget.generate_blueprint()

        self.assertEqual(first_blueprint.status, "review_required")
        self.assertIn(
            "explicit developer confirmation",
            "\n".join(first_blueprint.review_issues),
        )

        for approved_checkbox, mapping_selector in widget.command_controls:
            if not mapping_selector.currentText().strip():
                mapping_selector.setCurrentText("Hornbill.developerApprovedMethod")
                approved_checkbox.setChecked(True)
        widget.safety_confirmed_checkbox.setChecked(True)

        approved_blueprint = widget.generate_blueprint()

        self.assertEqual(approved_blueprint.status, "approved")
        self.assertTrue(widget.save_button.isEnabled())
        self.assertIn("APPROVED blueprint", widget.blueprint_status.text())
        self.assertIsNotNone(widget.generated_gui_preview)
        self.assertTrue(widget.export_gui_button.isEnabled())
        self.assertEqual(widget.generated_gui_preview.command_table.rowCount(), 2)

    def test_blueprint_rejects_safety_limits_below_detected_sweeps(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "safety_sweep.py"
            script_path.write_text(SWEEP_SCRIPT, encoding="utf-8")
            analysis = analyze_test_script(script_path)

        blueprint = create_integration_blueprint(
            analysis,
            test_name="Unsafe Sweep",
            safety_settings={
                "maximum_voltage": "10",
                "maximum_current": "10",
                "maximum_power": "300",
                "confirmed_by_developer": True,
            },
        )

        self.assertEqual(blueprint.status, "review_required")
        issue_text = "\n".join(blueprint.review_issues)
        self.assertIn("voltage sweep stop 61", issue_text)
        self.assertIn("current sweep stop 20.1", issue_text)

    def test_approved_blueprint_generates_safe_gui_scaffold(self):
        analysis = self.analyze_script()
        command_settings = {
            index: {
                "approved": True,
                "selected_mapping": finding.mappings[0],
            }
            for index, finding in enumerate(analysis.commands)
        }
        blueprint = create_integration_blueprint(
            analysis,
            test_name="Generated Hornbill Test",
            parameter_settings={
                "voltage_start": {"include_in_gui": True, "default": "1.5"}
            },
            command_settings=command_settings,
            safety_settings={
                "maximum_voltage": "30",
                "maximum_current": "10",
                "maximum_power": "50",
                "confirmed_by_developer": True,
            },
        )

        generated_gui = BlueprintGeneratedGui(blueprint)
        self.addCleanup(generated_gui.deleteLater)
        configuration = generated_gui.configuration()
        source = generate_gui_scaffold_source(blueprint)

        self.assertTrue(configuration["simulation_mode"])
        self.assertEqual(configuration["parameters"]["voltage_start"], 1.5)
        self.assertEqual(generated_gui.command_table.columnCount(), 5)
        self.assertNotIn("ResourceManager", source)
        self.assertNotIn("open_resource", source)
        compiled = compile(source, "generated_gui.py", "exec")
        namespace = {
            "__name__": "generated_gui_test",
            "__file__": str(ROOT / "src" / "instruments" / "generated_gui.py"),
        }
        exec(compiled, namespace)
        self.assertEqual(namespace["BLUEPRINT"]["status"], "approved")


if __name__ == "__main__":
    unittest.main()
