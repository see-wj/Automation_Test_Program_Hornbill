"""In-application user and developer documentation."""

import math
from pathlib import Path

import pyqtgraph as pg
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from configuration.configuration_service import load_configuration
from common.path import config_folder


PROGRAM_DOCUMENTATION_HTML = """
<style>
  body { font-family: Arial; font-size: 14px; color: #243447; }
  h1 { color: #173f5f; margin-bottom: 4px; }
  h2 { color: #20639b; margin-top: 22px; }
  h3 { color: #3b6f8f; margin-top: 16px; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  th { background: #dceaf5; text-align: left; }
  th, td { border: 1px solid #9fb7c8; padding: 7px; vertical-align: top; }
  code { background: #edf2f7; color: #8b1e3f; padding: 2px 4px; }
  pre { background: #edf2f7; border: 1px solid #c9d6df; padding: 10px; }
  .warning { background: #fff3cd; border: 1px solid #e0ad2f; padding: 10px; }
  .danger { background: #f8d7da; border: 1px solid #c94b59; padding: 10px; }
  .note { background: #dff3ff; border: 1px solid #5aa4cc; padding: 10px; }
</style>

<h1>DUT Test Automation Program</h1>
<p>
This application controls power supplies, digital multimeters, electronic loads,
oscilloscopes, and AC sources to run repeatable DUT measurements. It provides
instrument discovery, configurable test execution, live monitoring, queued runs,
safe pause/abort handling, graphs, diagnostics, and Excel reports.
</p>

<div class="danger">
<b>Hardware safety:</b> Confirm wiring, polarity, channel selection, grounding,
voltage/current/power limits, and instrument output state before every hardware run.
Use conservative limits for the first run. Never leave an energized setup unattended.
</div>

<h2>1. Quick Start</h2>
<ol>
  <li>Connect the required instruments and DUT while outputs are off.</li>
  <li>Start only one application instance with <code>python src/GUI.py</code>.</li>
  <li>Open <b>Bundle Test</b> and select the DUT, such as Dolphin or Hornbill.</li>
  <li>Click <b>Find Instruments</b>. Discovery probes only addresses configured for the selected DUT.</li>
  <li>Verify every role and address before continuing: PSU, DMM, DMM2, ELoad, scope, and AC source.</li>
  <li>Select Voltage or Current mode and enable the required tests.</li>
  <li>Review ratings, limits, channel numbers, loop count, output folder, and advanced settings.</li>
  <li>Use <b>Add to Queue</b> to save a run without starting it, or confirm a single run.</li>
  <li>Monitor progress, live graphs, warnings, and instrument output states.</li>
  <li>Open generated reports manually after the run. Monitoring graphs appear automatically.</li>
</ol>

<h2>2. Instrument Configuration and Discovery</h2>
<p>
Each DUT has a text configuration under <code>Instrument_Config_Files/</code>.
For example, Hornbill uses <code>config_Hornbill.txt</code>. The configured values
populate GUI defaults and define the VISA addresses that discovery probes.
</p>
<table>
  <tr><th>Configuration key</th><th>Purpose</th></tr>
  <tr><td><code>PSU</code></td><td>DUT power supply address</td></tr>
  <tr><td><code>DMM</code></td><td>Primary measurement DMM</td></tr>
  <tr><td><code>DMM2</code></td><td>Secondary DMM when required</td></tr>
  <tr><td><code>ELoad</code></td><td>Electronic load</td></tr>
  <tr><td><code>OSC</code></td><td>Oscilloscope</td></tr>
  <tr><td><code>ACSource</code></td><td>AC source</td></tr>
</table>
<p>
Only responsive configured addresses are added to the instrument boxes. USB, GPIB,
IP, and hostname checkboxes act as transport filters. The 3458A is a legacy GPIB
instrument and is identified using <code>ID?</code>, not <code>*IDN?</code>.
</p>
<div class="note">
Start the program through <code>src/GUI.py</code>. Native VISA must initialize before
Qt loads its DLLs; changing the startup import order can break GPIB and hostname discovery.
</div>

<h2>3. Running, Pausing, Resuming, and Aborting</h2>
<ul>
  <li><b>Pause</b> is cooperative. It takes effect at the next safe checkpoint, not halfway through a VISA command.</li>
  <li><b>Resume</b> continues from the paused checkpoint.</li>
  <li><b>Abort</b> requests a controlled stop, closes worker VISA sessions, and attempts independent shutdown of every instrument role.</li>
  <li>Do not force-close the application unless normal abort and window-close handling cannot respond.</li>
  <li>An interrupted queued run never restarts automatically. Review it and use Retry when safe.</li>
</ul>

<h2>4. Queue and Results</h2>
<p>
Queued tests run sequentially. Duplicate and Retry create independent parameter snapshots.
Pending runs can be reordered, removed, saved as a JSON template, or restored later.
Every run receives its own timestamped directory:
</p>
<pre>RUN_DIRECTORY/
  raw/       CSV data and parameters.json
  charts/    generated graph images
  reports/   Excel reports
  logs/      run.log, diagnostics.jsonl, execution checkpoint</pre>
<p>
Use <code>logs/run.log</code> for an operator-readable history and
<code>logs/diagnostics.jsonl</code> for instrument address, command, state,
cleanup, and traceback details.
</p>

<h2>5. Simulation Mode</h2>
<p>When hardware is unavailable, start with:</p>
<pre>python src/GUI.py --simulate</pre>
<p>
Simulation provides fake instrument sessions and exercises normal worker, queue,
pause, abort, graph, and report paths. Simulated results are clearly labeled and
must never be used as hardware-validation evidence.
</p>

<h2>6. Troubleshooting</h2>
<table>
  <tr><th>Problem</th><th>What to check</th></tr>
  <tr><td>Instrument is missing</td><td>Selected DUT config, transport checkbox, VISA address, cable, power, Keysight Connection Expert, and whether another process owns the instrument.</td></tr>
  <tr><td><code>VI_ERROR_LIBRARY_NFOUND</code> for GPIB</td><td>Start through <code>src/GUI.py</code>, run only one GUI instance, and do not move Qt imports ahead of early VISA initialization.</td></tr>
  <tr><td>3458A does not identify</td><td>Use <code>GPIB0::22::INSTR</code>, newline terminations, and the legacy <code>ID?</code> command.</td></tr>
  <tr><td>Pause appears delayed</td><td>The current instrument operation must finish before the next cooperative checkpoint.</td></tr>
  <tr><td>No graph data</td><td>Confirm the selected test emits the expected telemetry signal and that the graph mode matches Voltage or Current.</td></tr>
  <tr><td>No report</td><td>Check the run directory, <code>run.log</code>, diagnostics, selected save location, and report exporter error.</td></tr>
</table>

<h2>7. Current Limitations</h2>
<ul>
  <li>Production test execution is sequential; multiple queued runs do not control hardware concurrently.</li>
  <li>Pause cannot interrupt a SCPI command already executing inside an instrument driver.</li>
  <li>Calibration is work in progress and must not be treated as production-ready.</li>
  <li>The legacy standalone dialogs in <code>src/GUI.py</code> remain for compatibility; new production work should use the modular files.</li>
</ul>

<h2>8. Architecture for Developers</h2>
<table>
  <tr><th>Module</th><th>Responsibility</th></tr>
  <tr><td><code>src/GUI.py</code></td><td>Application entry point, VISA-before-Qt bootstrap, main tabs, and legacy dialog launcher.</td></tr>
  <tr><td><code>src/ui/all_test_dialog.py</code></td><td>Production bundle-test UI and direct signal wiring.</td></tr>
  <tr><td><code>src/execution/test_run_controller.py</code></td><td>Worker lifecycle and sequential FIFO queue.</td></tr>
  <tr><td><code>src/execution/test_worker.py</code></td><td>Background execution, dispatch, state machine, checkpoints, abort, and cleanup.</td></tr>
  <tr><td><code>src/execution/voltage_test_executor.py</code></td><td>Voltage-test selection and execution orchestration.</td></tr>
  <tr><td><code>src/execution/current_test_executor.py</code></td><td>Current and power-test selection and execution orchestration.</td></tr>
  <tr><td><code>src/execution/measurement_report_exporter.py</code></td><td>Measurement report and chart export coordination.</td></tr>
  <tr><td><code>src/instruments/instrument_discovery.py</code></td><td>Configured VISA probing, identity handling, and role assignment.</td></tr>
  <tr><td><code>DUT_Test_Scripts/</code></td><td>DUT-specific instrument operations and measurement sequences.</td></tr>
  <tr><td><code>SCPI_Library/</code></td><td>Instrument classes, VISA session management, errors, configuration, and simulation support.</td></tr>
  <tr><td><code>tests/</code></td><td>Unit, integration, simulation, queue, and report regression coverage.</td></tr>
</table>

<h2>9. Adding a New Standalone Test Dialog</h2>
<ol>
  <li>Create a focused dialog module under <code>src/</code>. Keep instrument work out of the GUI thread.</li>
  <li>Use a worker object or <code>QThread</code> and communicate through signals.</li>
  <li>Add a <code>DialogRegistration</code> in <code>MainWindow._create_dialog_registry()</code>.</li>
  <li>Prefer a lazy factory when the dialog imports optional or experimental dependencies.</li>
  <li>Add tests for registration, validation, worker completion, errors, and safe stop.</li>
</ol>
<pre>DialogRegistration(
    "New Test",
    "Short operator description",
    "new_test_dialog",
    NewTestDialog,
)</pre>

<h2>10. Adding a New Bundle Test Script</h2>
<ol>
  <li>Implement the DUT-specific measurement operation in <code>DUT_Test_Scripts/</code>. Keep the function small and parameter-driven.</li>
  <li>Add the selection control and stable selection key through the production selection/UI modules.</li>
  <li>Route the selection through <code>VoltageTestExecutor</code>, <code>CurrentTestExecutor</code>, or a new focused executor.</li>
  <li>Call blocking operations through worker checkpoints and replace long <code>sleep</code> calls with <code>worker.interruptible_sleep()</code>.</li>
  <li>Emit progress and telemetry signals; never update Qt widgets directly from a worker thread.</li>
  <li>Add report export through <code>MeasurementReportExporter</code> and the run context directories.</li>
  <li>Add simulation support and focused tests before using physical hardware.</li>
  <li>Perform low-power hardware validation using <code>HARDWARE_VALIDATION.md</code>.</li>
</ol>

<h3>Required safety behavior for every new test</h3>
<ul>
  <li>Validate required roles and numerical limits before starting.</li>
  <li>Check pause/abort checkpoints between instrument operations.</li>
  <li>Turn outputs off during normal completion, abort, and exception cleanup.</li>
  <li>Do not suppress VISA exceptions; preserve address, command, and operation context.</li>
  <li>Do not use <code>QMessageBox</code> from a worker thread. Emit an error or warning signal.</li>
</ul>

<h2>11. Developer Validation</h2>
<pre>python -B -m unittest discover -s tests -v
python -m ruff check .
python src/GUI.py --simulate</pre>
<p>
Run focused automated tests first, then the complete suite. Use simulation before
hardware. Do not modify a known-working DUT script merely to support a different
test setup; create a separate script or focused strategy when the hardware topology differs.
</p>
"""


HORNBILL_CONFIG_PATH = config_folder / "config_Hornbill.txt"


def build_hornbill_voltage_accuracy_patterns(config_path=HORNBILL_CONFIG_PATH):
    """Reproduce the two nested setpoint loops used by the Hornbill script."""
    config = load_configuration(config_path)
    minimum_voltage = float(config.get("minVoltage", 3))
    maximum_voltage = float(config.get("maxVoltage", 60))
    voltage_step = float(config.get("voltage_step_size", 3))
    minimum_current = float(config.get("minCurrent", 1))
    maximum_current = float(config.get("maxCurrent", 20))
    current_step = float(config.get("current_step_size", 5))
    power_limit = float(config.get("Power", 300))

    voltage_iterations = math.ceil(
        ((maximum_voltage - minimum_voltage) / voltage_step) + 1
    )
    current_iterations = math.ceil(
        ((maximum_current - minimum_current) / current_step) + 1
    )

    static_voltage = []
    static_current = []
    current_level = minimum_current
    for _ in range(current_iterations):
        current_level = min(current_level, maximum_current)
        voltage_level = minimum_voltage
        for _ in range(voltage_iterations):
            voltage_level = min(voltage_level, maximum_voltage)
            static_voltage.append(voltage_level)
            static_current.append(
                maximum_current - 0.1
                if current_level == maximum_current
                else current_level
            )
            voltage_level += voltage_step
            if voltage_level * current_level > power_limit:
                break
        current_level += current_step

    changing_voltage = []
    changing_current = []
    voltage_level = minimum_voltage
    for _ in range(voltage_iterations):
        voltage_level = min(voltage_level, maximum_voltage)
        current_level = minimum_current
        for _ in range(current_iterations):
            current_level = min(current_level, maximum_current)
            changing_voltage.append(voltage_level)
            changing_current.append(
                maximum_current - 0.1
                if current_level == maximum_current
                else max(0, current_level - 0.001)
            )
            current_level += current_step
            if voltage_level * current_level > power_limit:
                break
        voltage_level += voltage_step

    return {
        "settings": {
            "minimum_voltage": minimum_voltage,
            "maximum_voltage": maximum_voltage,
            "voltage_step": voltage_step,
            "minimum_current": minimum_current,
            "maximum_current": maximum_current,
            "current_step": current_step,
            "power_limit": power_limit,
        },
        "current_static": {
            "voltage": static_voltage,
            "current": static_current,
        },
        "current_change": {
            "voltage": changing_voltage,
            "current": changing_current,
        },
    }


class VoltageAccuracyPatternGraphs(QGroupBox):
    """Visualize the real Hornbill voltage-accuracy setpoint order."""

    def __init__(self, parent=None):
        super().__init__("Hornbill Voltage Accuracy Test Patterns", parent)
        self.patterns = build_hornbill_voltage_accuracy_patterns()

        self.current_static_plot = self._build_plot(
            title="1. Current Static (Voltage Change)",
            pattern=self.patterns["current_static"],
        )
        self.current_change_plot = self._build_plot(
            title="2. Current Change (Load Change)",
            pattern=self.patterns["current_change"],
        )

        settings = self.patterns["settings"]
        explanation = QLabel(
            "Generated from DUT_Test_Scripts/Hornbill/Hornbill_DUT_Test_With_ELoad.py "
            "and the current Hornbill "
            f"configuration: voltage {settings['minimum_voltage']:g} to "
            f"{settings['maximum_voltage']:g} V in {settings['voltage_step']:g} V "
            f"steps, load current {settings['minimum_current']:g} to "
            f"{settings['maximum_current']:g} A in {settings['current_step']:g} A "
            f"steps, limited to {settings['power_limit']:g} W. In test 1, current "
            "holds while voltage ramps, then voltage resets for the next current. "
            "In test 2, voltage holds while load current ramps, then current resets "
            "for the next voltage. Sweeps shorten when the next point would exceed "
            "the power limit. The maximum load is shown as 19.9 A because the script "
            "subtracts 0.1 A to prevent overload."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet(
            "background-color: #dff3ff; border: 1px solid #5aa4cc; "
            "padding: 7px; color: #243447;"
        )

        graph_layout = QHBoxLayout()
        graph_layout.addWidget(self.current_static_plot)
        graph_layout.addWidget(self.current_change_plot)

        layout = QVBoxLayout(self)
        layout.addLayout(graph_layout)
        layout.addWidget(explanation)

    @staticmethod
    def _build_plot(title, pattern):
        plot = pg.PlotWidget(background="w")
        plot.setMinimumHeight(235)
        plot.setTitle(title, color="#173f5f", size="12pt")
        plot.setLabel("bottom", "Measurement Step", color="#243447")
        plot.setLabel("left", "Programmed Level (V or A)", color="#243447")
        plot.showGrid(x=True, y=True, alpha=0.25)
        plot.addLegend(offset=(8, 8))
        steps = list(range(1, len(pattern["voltage"]) + 1))
        plot.plot(
            steps,
            pattern["voltage"],
            name="PSU Voltage (V)",
            pen=pg.mkPen("#20639b", width=2),
        )
        plot.plot(
            steps,
            pattern["current"],
            name="ELoad Current (A)",
            pen=pg.mkPen("#d97706", width=2),
            symbol="o",
            symbolSize=4,
            symbolBrush="#d97706",
        )
        return plot


def build_remaining_test_patterns(config_path=HORNBILL_CONFIG_PATH):
    """Build script-derived stimuli for the other production test selections."""
    voltage_accuracy = build_hornbill_voltage_accuracy_patterns(config_path)
    settings = voltage_accuracy["settings"]
    maximum_voltage = settings["maximum_voltage"]
    maximum_current = settings["maximum_current"]
    power_limit = settings["power_limit"]
    low_voltage = round(power_limit / maximum_current, 2)
    low_current = round(power_limit / maximum_voltage, 2)

    transient_high_half = low_current / 2
    transient_high_full = max(0, low_current - 1)
    transient_low_half = maximum_current / 2
    transient_low_full = max(0, maximum_current - 1)

    power_step = 10
    power_values = list(range(0, int(power_limit) + power_step, power_step))

    line_voltage = []
    line_output_voltage = []
    line_load_current = []
    for nominal in (100, 115, 230):
        line_stimulus = [nominal, round(nominal * 0.9, 1), round(nominal * 1.1, 1)]
        line_voltage.extend(line_stimulus + line_stimulus)
        line_output_voltage.extend([maximum_voltage] * 3 + [low_voltage] * 3)
        line_load_current.extend([low_current] * 3 + [maximum_current] * 3)

    return {
        "current_accuracy": {
            "description": (
                "The ELoad voltage holds at each level while the PSU current setpoint "
                "ramps. Current resets before the next voltage level; the power limit "
                "shortens high-voltage sweeps."
            ),
            "series": (
                ("ELoad Voltage (V)", voltage_accuracy["current_change"]["voltage"], "#20639b"),
                ("PSU Current (A)", voltage_accuracy["current_change"]["current"], "#d97706"),
            ),
        },
        "voltage_load_regulation": {
            "description": (
                "CV load regulation compares no-load and full-load voltage at the "
                "high-voltage/low-current and low-voltage/high-current operating points."
            ),
            "series": (
                ("PSU Voltage (V)", [maximum_voltage, maximum_voltage, 0, low_voltage, low_voltage], "#20639b"),
                ("ELoad Current (A)", [0, low_current, 0, 0, maximum_current], "#d97706"),
            ),
        },
        "current_load_regulation": {
            "description": (
                "CC load regulation compares light-load and full-load current at "
                "low-voltage/high-current and high-voltage/low-current points."
            ),
            "series": (
                ("Operating Voltage (V)", [low_voltage, low_voltage, 0, maximum_voltage, maximum_voltage], "#20639b"),
                ("PSU Current Limit (A)", [maximum_current, maximum_current, 0, low_current, low_current], "#d97706"),
                ("Load Condition (%)", [0, 100, 0, 0, 100], "#7c3aed"),
            ),
        },
        "transient_recovery": {
            "description": (
                "Normal transient recovery toggles the ELoad between 50% and near "
                "100% load at high-voltage and high-current operating points. The "
                "oscilloscope captures undershoot and overshoot after each edge."
            ),
            "series": (
                ("PSU Voltage (V)", [maximum_voltage] * 6 + [low_voltage] * 6, "#20639b"),
                (
                    "ELoad Current (A)",
                    [transient_high_half, transient_high_full, transient_high_half] * 2
                    + [transient_low_half, transient_low_full, transient_low_half] * 2,
                    "#d97706",
                ),
            ),
        },
        "transient_special": {
            "description": (
                "Special-case transient recovery toggles the ELoad between 0% and "
                "100% load at the high-voltage and high-current operating points."
            ),
            "series": (
                ("PSU Voltage (V)", [maximum_voltage] * 6 + [low_voltage] * 6, "#20639b"),
                (
                    "ELoad Current (A)",
                    [0, low_current, 0] * 2 + [0, maximum_current, 0] * 2,
                    "#d97706",
                ),
            ),
        },
        "programming_response": {
            "description": (
                "Programming response captures 0-to-target and target-to-0 voltage "
                "steps at no load and full load for both maximum-voltage and "
                "maximum-current operating points."
            ),
            "series": (
                (
                    "PSU Voltage (V)",
                    [0, maximum_voltage, 0, 0, maximum_voltage, 0, 0, low_voltage, 0, 0, low_voltage, 0],
                    "#20639b",
                ),
                (
                    "ELoad Current (A)",
                    [0, 0, 0, low_current, low_current, low_current, 0, 0, 0, maximum_current, maximum_current, maximum_current],
                    "#d97706",
                ),
            ),
        },
        "line_regulation": {
            "description": (
                "Voltage and current line-regulation selections share this stimulus: "
                "the AC source moves nominal, 90%, and 110% line while the DUT holds "
                "two output operating points."
            ),
            "series": (
                ("AC Input Voltage (V)", line_voltage, "#2e8b57"),
                ("DUT Output Voltage (V)", line_output_voltage, "#20639b"),
                ("Load Current (A)", line_load_current, "#d97706"),
            ),
        },
        "power_accuracy": {
            "description": (
                "The PSU programmed-power limit ramps from zero to the configured "
                "maximum in 10 W steps while voltage, current, and readback power are measured."
            ),
            "series": (("Programmed Power (W)", power_values, "#7c3aed"),),
        },
        "ovp": {
            "description": (
                "For 25%, 50%, and 100% of the selected OVP level, the script starts "
                "at 90% and adaptively converges toward the trip threshold. The exact "
                "probe path depends on each trip response; this normalized graph shows "
                "the intended convergence window."
            ),
            "series": (
                ("Probe (% of sub-level)", [90, 99, 100, 90, 99, 100, 90, 99, 100], "#20639b"),
                ("Trip Target (%)", [100] * 9, "#c2414b"),
            ),
        },
        "ocp": {
            "description": (
                "OCP activation sets the PSU current one amp below the selected OCP "
                "level, commands the ELoad to the OCP level, waits through the 10 s "
                "protection delay, then measures the output-current fall time. Values "
                "are normalized because OCP level is entered by the operator."
            ),
            "x": [0, 1, 9, 10, 10.1, 12],
            "x_label": "Time (s)",
            "series": (
                ("PSU Output Current (% OCP)", [90, 90, 90, 90, 0, 0], "#20639b"),
                ("ELoad Command (% OCP)", [100, 100, 100, 100, 100, 0], "#d97706"),
            ),
        },
    }


class ScriptPatternGraph(QGroupBox):
    """Reusable graph card for a script-derived production test pattern."""

    def __init__(self, title, pattern, parent=None):
        super().__init__(title, parent)
        self.pattern = pattern
        self.plot = pg.PlotWidget(background="w")
        self.plot.setMinimumHeight(210)
        self.plot.setLabel("bottom", pattern.get("x_label", "Sequence Step"), color="#243447")
        self.plot.setLabel("left", "Programmed Level", color="#243447")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.addLegend(offset=(8, 8))

        for name, values, color in pattern["series"]:
            x_values = pattern.get("x") or list(range(1, len(values) + 1))
            self.plot.plot(
                x_values,
                values,
                name=name,
                pen=pg.mkPen(color, width=2),
                symbol="o",
                symbolSize=4,
                symbolBrush=color,
            )

        description = QLabel(pattern["description"])
        description.setWordWrap(True)
        description.setStyleSheet("padding: 5px; color: #243447;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.plot)
        layout.addWidget(description)


def _scrolling_panel(widgets):
    content = QWidget()
    layout = QGridLayout(content)
    for index, widget in enumerate(widgets):
        layout.addWidget(widget, index // 2, index % 2)
    layout.setRowStretch((len(widgets) + 1) // 2, 1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(content)
    return scroll


class TestPatternsTab(QWidget):
    """Dedicated main-window tab for script-derived test visualizations."""

    def __init__(self, parent=None):
        super().__init__(parent)

        title = QLabel("Test Sequence Visualizer")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #173f5f;")

        introduction = QLabel(
            "These graphs show the programmed PSU voltage and electronic-load "
            "current at each measurement step. They are generated from the actual "
            "Hornbill voltage-accuracy loop structure and current configuration."
        )
        introduction.setWordWrap(True)

        self.patterns = build_remaining_test_patterns()
        self.category_tabs = QTabWidget()

        self.pattern_graphs = VoltageAccuracyPatternGraphs()
        self.current_accuracy_graph = ScriptPatternGraph(
            "Current Accuracy",
            self.patterns["current_accuracy"],
        )
        self.category_tabs.addTab(
            _scrolling_panel([self.pattern_graphs, self.current_accuracy_graph]),
            "Accuracy",
        )

        self.voltage_load_graph = ScriptPatternGraph(
            "Voltage Load Regulation",
            self.patterns["voltage_load_regulation"],
        )
        self.current_load_graph = ScriptPatternGraph(
            "Current Load Regulation",
            self.patterns["current_load_regulation"],
        )
        self.line_regulation_graph = ScriptPatternGraph(
            "Voltage / Current Line Regulation",
            self.patterns["line_regulation"],
        )
        self.category_tabs.addTab(
            _scrolling_panel(
                [
                    self.voltage_load_graph,
                    self.current_load_graph,
                    self.line_regulation_graph,
                ]
            ),
            "Regulation",
        )

        self.transient_graph = ScriptPatternGraph(
            "Transient Recovery - Normal (50% to 100%)",
            self.patterns["transient_recovery"],
        )
        self.transient_special_graph = ScriptPatternGraph(
            "Transient Recovery - Special (0% to 100%)",
            self.patterns["transient_special"],
        )
        self.programming_graph = ScriptPatternGraph(
            "Programming Speed / Response",
            self.patterns["programming_response"],
        )
        self.category_tabs.addTab(
            _scrolling_panel(
                [
                    self.transient_graph,
                    self.transient_special_graph,
                    self.programming_graph,
                ]
            ),
            "Dynamic",
        )

        self.ovp_graph = ScriptPatternGraph("OVP Test", self.patterns["ovp"])
        self.ocp_graph = ScriptPatternGraph("OCP Activation", self.patterns["ocp"])
        self.category_tabs.addTab(
            _scrolling_panel([self.ovp_graph, self.ocp_graph]),
            "Protection",
        )

        self.power_graph = ScriptPatternGraph(
            "Power Accuracy",
            self.patterns["power_accuracy"],
        )
        self.category_tabs.addTab(
            _scrolling_panel([self.power_graph]),
            "Power",
        )

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(introduction)
        layout.addWidget(self.category_tabs)


class ProgramDocumentationTab(QWidget):
    """Searchable operator and developer guide displayed in the main window."""

    def __init__(self, parent=None):
        super().__init__(parent)

        title = QLabel("Program Guide")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #173f5f;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search this guide...")
        self.search_input.returnPressed.connect(self.find_next)

        find_button = QPushButton("Find Next")
        find_button.clicked.connect(self.find_next)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(find_button)

        self.browser = QTextBrowser()
        self.browser.setHtml(PROGRAM_DOCUMENTATION_HTML)
        self.browser.setOpenExternalLinks(False)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(search_layout)
        layout.addWidget(self.browser)

    def find_next(self):
        search_text = self.search_input.text().strip()
        if not search_text:
            return False
        if self.browser.find(search_text):
            return True
        cursor = self.browser.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.browser.setTextCursor(cursor)
        return self.browser.find(search_text)
