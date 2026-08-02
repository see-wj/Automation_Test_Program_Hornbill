"""Generate a safe, simulation-only Python GUI scaffold from a blueprint."""

import json
import re

from analysis.blueprint_execution import enrich_blueprint_execution_metadata


def generate_gui_scaffold_source(blueprint):
    data = blueprint.to_dict() if hasattr(blueprint, "to_dict") else dict(blueprint)
    data = enrich_blueprint_execution_metadata(data)
    if data.get("status") != "approved" or data.get("review_issues"):
        raise ValueError("Only an approved blueprint can generate a GUI scaffold.")
    payload = repr(json.dumps(data))
    return f'''"""Auto-generated simulation-only GUI scaffold.

This file does not execute SCPI commands or open instrument sessions.
"""

import json
import sys
from pathlib import Path


SOURCE_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout

from ui.blueprint_generated_gui import BlueprintGeneratedGui


BLUEPRINT = json.loads({payload})


class GeneratedTestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(BLUEPRINT["test_name"] + " - Simulation Scaffold")
        self.resize(1000, 760)
        layout = QVBoxLayout(self)
        self.generated_gui = BlueprintGeneratedGui(BLUEPRINT)
        layout.addWidget(self.generated_gui)


if __name__ == "__main__":
    application = QApplication(sys.argv)
    dialog = GeneratedTestDialog()
    dialog.show()
    sys.exit(application.exec_())
'''


def suggested_scaffold_filename(test_name):
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", str(test_name)).strip("_")
    return f"{normalized or 'generated_test'}_gui.py"


__all__ = ["generate_gui_scaffold_source", "suggested_scaffold_filename"]
