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
<p>
If no configured electronic load responds, the ELoad box selects <code>None</code>.
This mode supports Hornbill <b>Voltage Accuracy → Current Static (Voltage
Change)</b>, with or without <b>Oscilloscope Capture</b>. The test performs one
voltage sweep at the natural no-load current; scope mode saves a screenshot at
each voltage point. Load-change, current, power, transient, and other
load-dependent tests still require a responsive ELoad.
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
<p>
Multiple instruments for the same role can be configured with numbered keys.
Keep the preferred instrument in the base key, then add
<code>PSU_2</code>, <code>PSU_3</code>, <code>DMM_2</code>,
<code>ELoad_2</code>, and equivalent numbered keys. Find Instruments probes every
candidate and adds only responsive addresses to the selection boxes. If the
preferred address is unavailable, the first responsive candidate is selected.
</p>

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
  <li>Retired standalone dialogs are archived in <code>src/legacy/legacy_gui.py</code> and are not loaded by the production application.</li>
</ul>

<h2>8. Architecture for Developers</h2>
<table>
  <tr><th>Module</th><th>Responsibility</th></tr>
  <tr><td><code>src/GUI.py</code></td><td>Application entry point, VISA-before-Qt bootstrap, main tabs, and supported production launchers.</td></tr>
  <tr><td><code>src/legacy/legacy_gui.py</code></td><td>Archived monolithic standalone dialogs retained only for historical reference.</td></tr>
  <tr><td><code>src/ui/all_test_dialog.py</code></td><td>Production bundle-test UI and direct signal wiring.</td></tr>
  <tr><td><code>src/execution/test_run_controller.py</code></td><td>Worker lifecycle and sequential FIFO queue.</td></tr>
  <tr><td><code>src/execution/test_worker.py</code></td><td>Background execution, dispatch, state machine, checkpoints, abort, and cleanup.</td></tr>
  <tr><td><code>src/execution/run_context.py</code></td><td>Per-run paths and realtime CSV ownership, including measurement index, loop, and channel metadata.</td></tr>
  <tr><td><code>src/analysis/bundle_data_analysis.py</code></td><td>Loads, normalizes, groups, and calculates Bundle Test statistics.</td></tr>
  <tr><td><code>src/ui/bundle_data_analysis_widget.py</code></td><td>Displays condition, loop, channel, and extrema analysis tables.</td></tr>
  <tr><td><code>src/execution/voltage_test_executor.py</code></td><td>Voltage-test selection and execution orchestration.</td></tr>
  <tr><td><code>src/execution/current_test_executor.py</code></td><td>Current and power-test selection and execution orchestration.</td></tr>
  <tr><td><code>src/execution/measurement_report_exporter.py</code></td><td>Measurement report and chart export coordination.</td></tr>
  <tr><td><code>src/instruments/instrument_discovery.py</code></td><td>Configured VISA probing, identity handling, and role assignment.</td></tr>
  <tr><td><code>src/analysis/test_script_analyzer.py</code></td><td>Static AST analysis of external Python tests, including SCPI mapping, timing, loops, resources, and integration warnings.</td></tr>
  <tr><td><code>src/analysis/integration_blueprint.py</code></td><td>Non-executable reviewed blueprint schema with mandatory command and safety approval.</td></tr>
  <tr><td><code>src/ui/test_script_assistant_tab.py</code></td><td>Safe Script Assistant UI; selected scripts are analyzed but never executed.</td></tr>
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

<h2>12. Bundle Test Data Analysis</h2>
<p>
The Bundle Test dialog contains a <b>Data Analysis</b> sub-tab. Analysis runs
automatically after a completed or aborted run. Use <b>Refresh Analysis</b> to
rescan the current selection. First select an <b>Analysis type</b>:
<b>Analyze Existing Results</b> for one run or parent results location, or
<b>Compare Two Runs</b> for two independently stored run folders. Only the
controls needed for the selected workflow are displayed.
</p>

<h3>Choosing an analysis type</h3>
<table>
  <tr><th>Analysis type</th><th>Purpose</th><th>What is included</th><th>Typical use</th></tr>
  <tr>
    <td>Analyze Existing Results</td>
    <td>Uses one selected folder as the analysis root and replaces any previous selection.</td>
    <td>The analyzer recursively includes every supported run found below that folder.</td>
    <td>Analyze one completed run, refresh the current run, or analyze a deliberately organized parent folder.</td>
  </tr>
  <tr>
    <td>Compare Two Runs</td>
    <td>Uses the two independently entered or browsed run folders as separate analysis roots.</td>
    <td>Run A and Run B may be located anywhere. Their data is combined and duplicate file paths are removed. Files are read in place and are not copied or modified.</td>
    <td>Compare Channel 1 against Channel 2, compare different DUT runs, or combine runs stored in separate locations.</td>
  </tr>
</table>
<div class="note">
Choose the smallest folder that contains the intended data. Selecting a high-level
parent in <b>Analyze Existing Results</b> may unintentionally include unrelated
historical runs. Select <b>Compare Two Runs</b> when the intended runs are in
different branches or when explicit control over the included runs is important.
</div>
<p>
For either mode, a realtime CSV is preferred. If a selected run has no realtime
CSV, a compatible voltage Excel report is used as a labelled fallback. Channel
comparison occurs only when DUT, test, metric, set voltage, set current, and loop
conditions match.
</p>

<h3>Practical difference threshold</h3>
<p>
The <b>Practical difference threshold</b> control defines how large a matched
Run A minus Run B difference must be, relative to the applicable engineering
error limit, before it is labelled practically meaningful. The default is
10%. For example, with a 0.010 V error limit, a 10% threshold corresponds to a
0.001 V channel difference.
</p>
<div class="warning">
Changing this threshold does not change specification boundaries, individual
point pass/fail results, or statistical confidence intervals. It changes only
the engineering-significance label used for channel comparison. After changing
the value, press <b>Compare Run A and Run B</b> or <b>Refresh Analysis</b> to
recalculate the conclusions.
</div>

<h3>Exporting analysis results</h3>
<p>
After an analysis completes, press <b>Export Analysis Results</b> and choose a
destination folder. The program creates a timestamped
<code>analysis_export_*</code> or <code>analysis_comparison_*</code> subfolder,
so existing files are not overwritten.
</p>
<ul>
  <li>All analysis CSV tables are exported without the 500-row GUI display limit.</li>
  <li><code>compliance_heatmap.png</code> captures voltage/current specification usage.</li>
  <li><code>confidence_intervals.png</code> captures mean errors, confidence intervals, and boundaries.</li>
  <li><code>channel_difference_heatmap.png</code> captures matched Run A minus Run B differences.</li>
  <li><code>loop_stability.png</code> captures loop-to-loop error movement.</li>
  <li><code>analysis_manifest.json</code> records Run A/Run B paths, channels, loops, source types, row counts, the selected practical threshold, and exported graph names.</li>
  <li><code>analysis_summary.txt</code> records the source paths and operator-readable conclusions.</li>
</ul>

<h3>Visual dashboard</h3>
<p>
The dashboard uses separate full-width graph tabs for
<b>Compliance Heatmap</b>, <b>Confidence Intervals</b>,
<b>Channel Comparison</b>, and <b>Loop Stability</b>. The selected filters and
summary cards apply to every graph tab, allowing each graph to use the available
window area instead of sharing a compact four-graph grid.
</p>
<ul>
  <li><b>Summary cards</b> show filtered error-record count, weighted pass rate, worst limit usage, maximum absolute error, weighted mean bias, and pass/marginal/fail condition counts.</li>
  <li><b>Compliance heatmap</b> places set voltage on the horizontal axis and load current on the vertical axis. Each cell uses the worst selected metric/channel result: green below 80% limit usage, amber from 80% through 100%, and red above 100%.</li>
  <li><b>Confidence plot</b> shows mean error with its 95% confidence interval and the applicable upper/lower engineering limits.</li>
  <li><b>Matched channel difference heatmap</b> shows Channel A minus Channel B as a signed percentage of the applicable error limit. Blue is a negative practical difference, red is a positive practical difference, and green remains within the default ±10% practical threshold.</li>
  <li><b>Loop stability</b> plots loop mean error using a separate color for each channel, voltage, current, and metric combination.</li>
  <li>To prevent unreadable overlays, the default Loop Stability graph shows the eight conditions with highest specification-limit usage and the Confidence graph shows the top 30 conditions. Use filters to expose any omitted condition.</li>
  <li>Use the DUT, test, metric, channel, voltage, and current filters to reduce visual clutter. Pointing at heatmap or confidence points displays exact values and conclusions.</li>
  <li>Selecting a Condition Compliance table row transfers that exact condition into the dashboard filters.</li>
  <li>For responsiveness, each GUI table displays the 500 most important rows. Statistical calculations and exported analysis CSV files retain every row.</li>
</ul>

<h3>Analysis workflow</h3>
<ol>
  <li>The worker records every realtime measurement with its sequential index, loop number, and PSU channel.</li>
  <li>The run context writes the values to <code>raw/realtime_voltage_data_*.csv</code> and stores setup metadata in <code>raw/parameters.json</code>.</li>
  <li>The analyzer recursively finds realtime files beneath the selected results folder.</li>
  <li>If a run has no realtime CSV, a compatible <code>reports/VOLTAGE_*.xlsx</code> Data sheet is loaded as a clearly labelled report fallback. A realtime CSV always takes priority when both exist.</li>
  <li>Each file is joined with its DUT, test type, channel, and requested loop count from <code>parameters.json</code>.</li>
  <li>Programming and readback errors are converted into separate analysis records.</li>
  <li>Records are grouped only when DUT, test type, channel, set voltage, and set current match.</li>
  <li>Point compliance, confidence intervals, equivalence, loop statistics, matched channel comparisons, extrema, and operator insights are calculated.</li>
  <li>The GUI tables are refreshed and analysis CSV files are written into the latest run's <code>raw/</code> folder.</li>
</ol>

<h3>Setpoint condition and data sorting</h3>
<div class="note">
<b>Set voltage and set current are part of the statistical condition.</b>
For example, Channel 1 at 5 V / 1 A is never averaged together with Channel 1
at 10 V / 1 A or 5 V / 2 A. Channel-to-channel comparison also requires the
same DUT, test type, set voltage, and set current.
</div>
<p>The effective grouping and display order is:</p>
<pre>DUT → Test → Channel → Set Voltage → Set Current → Loop → Error Type</pre>
<p>
New realtime files contain explicit <code>Loop</code> and <code>Channel</code>
columns. For an older file, the channel is read from <code>parameters.json</code>
and loop numbers are inferred by dividing the ordered rows by the configured
loop count. Explicit metadata is therefore more reliable than legacy inference.
</p>

<h3>Individual channel calculation</h3>
<p>
The <b>Condition Compliance</b> table combines repeated loops for one exact
channel/setpoint condition. The <b>Loop Repeatability</b> table shows each run
and loop separately.
For errors <i>x</i><sub>1</sub>...<i>x</i><sub>n</sub>:
</p>
<table>
  <tr><th>Statistic</th><th>Calculation and meaning</th></tr>
  <tr><td>Mean error</td><td><code>sum(x) / n</code>. Signed bias of the measurement.</td></tr>
  <tr><td>Standard deviation</td><td><code>sqrt(sum((x - mean)^2) / (n - 1))</code>. Sample repeatability; lower is more consistent. One sample reports zero.</td></tr>
  <tr><td>95% confidence interval</td><td>Student-t interval for the mean error. An interval excluding zero indicates detectable systematic bias.</td></tr>
  <tr><td>MAD</td><td>Median absolute deviation from the median. A robust spread indicator that is less sensitive to one unusual value.</td></tr>
  <tr><td>Minimum / Maximum error</td><td>Most negative and most positive signed errors for the exact condition.</td></tr>
  <tr><td>MAE</td><td><code>mean(abs(x))</code>. Typical error magnitude without sign cancellation.</td></tr>
  <tr><td>RMSE</td><td><code>sqrt(mean(x^2))</code>. Error magnitude with stronger penalty for large errors.</td></tr>
  <tr><td>P95 absolute error</td><td>95th percentile of <code>abs(x)</code>; 95% of observed magnitudes are at or below this value.</td></tr>
  <tr><td>Maximum absolute error</td><td>Largest observed <code>abs(x)</code>, regardless of polarity.</td></tr>
  <tr><td>Pass rate</td><td><code>passing samples / all samples × 100%</code>, using the recorded upper and lower error boundaries.</td></tr>
  <tr><td>Maximum limit usage</td><td>Largest <code>abs(error / applicable boundary) × 100%</code>. Values above 100% are failures.</td></tr>
  <tr><td>Mean equivalence</td><td>TOST confidence-interval rule: the two-sided 90% interval for mean error must remain inside the engineering limits.</td></tr>
</table>

<div class="note">
Observed point compliance always has priority. Mean equivalence cannot convert
an observed failed point into a pass. At least two repeated samples are needed
for confidence-interval assessments. Results based on two through four repeated
samples are marked preliminary; use at least five loops for stronger inference.
</div>

<h3>Channel-to-channel comparison</h3>
<p>
Only channels tested at the same DUT, test, voltage, current, metric and loop
are paired. Each row states both setpoints so the relationship is unambiguous.
</p>
<table>
  <tr><th>Term</th><th>Definition</th></tr>
  <tr><td>Mean difference (A-B)</td><td>Average paired error for Channel A minus Channel B. Its sign shows the direction of channel offset.</td></tr>
  <tr><td>95% CI difference</td><td>Student-t confidence interval for matched differences. Excluding zero indicates a detectable channel offset.</td></tr>
  <tr><td>Matched correlation</td><td>Pearson correlation of matched loop means. It is reported only when both channels vary and at least two loop pairs exist.</td></tr>
  <tr><td>Difference detected</td><td>Statistical evidence of an offset, not by itself a specification failure. Each channel's point compliance remains the primary decision.</td></tr>
  <tr><td>Difference limit usage</td><td><code>abs(mean channel difference) / strictest applicable error limit × 100%</code>. The default practical threshold is 10%.</td></tr>
  <tr><td>Practically meaningful</td><td>Yes when difference limit usage reaches the practical threshold. This prevents a tiny but consistent offset from being described as an important engineering difference.</td></tr>
</table>

<h3>Detailed statistical mathematics reference</h3>
<p>
For one exact condition, let <code>n</code> be the valid record count and
<code>x_i</code> be error record <code>i</code>. Let <code>V_set</code> be the
programmed voltage, <code>V_ref</code> the reference DMM reading and
<code>V_rb</code> the PSU readback.
</p>
<table>
  <tr><th>Quantity</th><th>Implemented equation</th><th>Meaning</th></tr>
  <tr><td>Programming error</td><td><code>e_prog = V_ref - V_set</code></td><td>Error between the reference measurement and requested output.</td></tr>
  <tr><td>Readback error</td><td><code>e_rb = V_rb - V_ref</code></td><td>Error between the PSU internal readback and external reference.</td></tr>
  <tr><td>Nominal boundary</td><td><code>U = gain * V_set + offset; L = -U</code></td><td>Programming and readback use independent configured gain and offset values. Analysis uses the boundaries stored with each point.</td></tr>
  <tr><td>Strict repeated boundary</td><td><code>L_strict = max(L_i); U_strict = min(U_i)</code></td><td>The intersection of all repeated-point boundaries.</td></tr>
</table>

<h4>Point decision and normalized usage</h4>
<pre>
point passes when L_i &lt;= x_i &lt;= U_i
if x_i &gt;= 0: usage_i = 100 * x_i / U_i
if x_i &lt;  0: usage_i = 100 * x_i / abs(L_i)
maximum limit usage = max(abs(usage_i))
margin remaining = 100 - abs(usage_i)
pass rate = 100 * passed point count / n
</pre>
<p>
Directional normalization supports asymmetric limits. A usage magnitude of
100% is on a boundary, above 100% exceeds it, and negative remaining margin
means the point is outside its boundary.
</p>

<h4>Descriptive statistics</h4>
<table>
  <tr><th>Statistic</th><th>Equation</th><th>Interpretation</th></tr>
  <tr><td>Mean</td><td><code>x_bar = sum(x_i) / n</code></td><td>Signed average bias; opposite signs can cancel.</td></tr>
  <tr><td>Sample standard deviation</td><td><code>s = sqrt(sum((x_i-x_bar)^2)/(n-1))</code></td><td>Observed repeatability. One sample is reported as zero.</td></tr>
  <tr><td>Standard error</td><td><code>SE = s / sqrt(n)</code></td><td>Sampling uncertainty of the mean, not a complete uncertainty budget.</td></tr>
  <tr><td>Median</td><td><code>median(x_i)</code></td><td>Middle ordered error.</td></tr>
  <tr><td>MAD</td><td><code>median(abs(x_i - median(x)))</code></td><td>Unscaled robust spread; no 1.4826 multiplier is applied.</td></tr>
  <tr><td>MAE</td><td><code>sum(abs(x_i))/n</code></td><td>Average error magnitude.</td></tr>
  <tr><td>RMSE</td><td><code>sqrt(sum(x_i^2)/n)</code></td><td>Magnitude measure that weights large errors more strongly.</td></tr>
  <tr><td>P95 absolute error</td><td><code>quantile(abs(x_i), 0.95)</code></td><td>Pandas linear-interpolated 95th percentile.</td></tr>
  <tr><td>Estimated spread</td><td><code>x_bar - 2s</code> to <code>x_bar + 2s</code></td><td>Descriptive screening band, not a formal confidence or prediction interval.</td></tr>
</table>

<h4>Student-t confidence intervals</h4>
<pre>CI_C = x_bar +/- t(C, n-1) * s / sqrt(n)</pre>
<p>
The application uses two-sided 95% and 90% intervals. Stored Student-t critical
values are used through 31 samples; larger samples use 1.960 for 95% and 1.645
for 90%. An interval requires at least two samples.
</p>

<h4>Bias hypothesis</h4>
<p>
The null hypothesis is <code>H0: mean error = 0</code>. Bias is detected when
the 95% confidence interval excludes zero:
<code>CI95_lower &gt; 0</code> or <code>CI95_upper &lt; 0</code>. An interval
containing zero means that non-zero bias was not established; it does not prove
the true bias is exactly zero. This implementation uses the interval rule and
does not report a p-value.
</p>

<h4>Mean equivalence (TOST confidence-interval rule)</h4>
<p>
The equivalence null hypothesis states that the mean is outside the strict
engineering interval. At alpha 0.05, mean equivalence is demonstrated only when:
</p>
<pre>CI90_lower &gt;= L_strict AND CI90_upper &lt;= U_strict</pre>
<p>
Equivalence applies only to the mean and never overrides an observed failed
point.
</p>

<h4>Compliance conclusion priority</h4>
<ol>
  <li>Any failed point makes the condition <b>FAIL</b>.</li>
  <li>One passing sample is <b>PASS</b>, but repeatability is not established.</li>
  <li>Two through four passing samples are <b>PASS</b> with preliminary statistics.</li>
  <li>With at least five samples, failure to demonstrate mean equivalence is <b>MARGINAL</b>.</li>
  <li>If <code>x_bar +/- 2s</code> crosses a strict boundary, the condition is <b>MARGINAL</b>.</li>
  <li>Otherwise it is <b>PASS - compliant and statistically stable</b>.</li>
</ol>

<h4>Matched channel comparison</h4>
<p>
Only identical DUT, test, set voltage, set current, metric and loop conditions
are paired. Multiple records within one channel/loop are averaged before
matching. For matched loop <code>j</code>:
</p>
<pre>
d_j = mean_error_A,j - mean_error_B,j
d_bar = sum(d_j) / m
CI_difference = d_bar +/- t(0.95, m-1) * s_d / sqrt(m)
</pre>
<p>
Here <code>m</code> is the matched-loop count. A statistical channel difference
is detected when this 95% interval excludes zero.
</p>

<h4>Pearson matched correlation</h4>
<pre>
r = sum((A_j-A_bar)(B_j-B_bar))
    / sqrt(sum((A_j-A_bar)^2) * sum((B_j-B_bar)^2))
</pre>
<p>
Correlation requires at least two matched loops and non-zero spread in both
channels. It measures shared movement, not agreement or causation. A high
correlation can exist together with a large constant channel offset.
</p>

<h4>Practical difference threshold</h4>
<pre>
P = min(abs(L_strict), abs(U_strict))
difference limit usage = 100 * abs(d_bar) / P
practically meaningful when difference limit usage &gt;= selected threshold
</pre>
<p>
The default threshold is 10% of the engineering limit. If the strict limit is
+/-0.010 V, the practical level is <code>0.10 * 0.010 = 0.001 V</code>. A mean
A-B difference of 0.0012 V uses 12% and crosses the threshold.
</p>
<div class="warning">
This is a configurable engineering screening rule, not a p-value, confidence
level, guardband, uncertainty ratio or additional pass/fail specification.
Changing it only changes the practical-importance label.
</div>

<h4>Statistical and practical evidence</h4>
<table>
  <tr><th>Statistical</th><th>Practical</th><th>Meaning</th></tr>
  <tr><td>Yes</td><td>Yes</td><td>Repeatably detectable and large enough under the selected engineering rule.</td></tr>
  <tr><td>Yes</td><td>No</td><td>Consistent but small relative to the allowed error.</td></tr>
  <tr><td>No</td><td>Yes</td><td>Important observed magnitude, but consistency is not established.</td></tr>
  <tr><td>No</td><td>No</td><td>No meaningful offset is established.</td></tr>
</table>
<p>
Evidence is <b>Insufficient</b> below two matched loops,
<b>Preliminary</b> for two through four, and <b>Supported</b> for five or more.
</p>

<h4>Dashboard aggregation</h4>
<ul>
  <li>Weighted pass rate = <code>sum(condition pass rate * samples) / sum(samples)</code>.</li>
  <li>Weighted mean bias = <code>sum(condition mean * samples) / sum(samples)</code>.</li>
  <li>Worst usage and maximum absolute error are maxima among visible conditions.</li>
  <li>A heatmap cell takes the highest usage and lowest pass rate among visible metrics and channels at the same setpoint.</li>
</ul>

<h4>Assumptions and limitations</h4>
<ul>
  <li>Student-t interpretation assumes sufficiently independent repeated errors and a mean reasonably described by the t method. Drift or autocorrelation can overstate evidence.</li>
  <li>Outliers remain in the calculations; MAD describes robust spread but does not delete points.</li>
  <li>No multiple-comparison correction is applied across many conditions.</li>
  <li>Reference uncertainty, DUT uncertainty, environmental effects, guardbanding and formal uncertainty budgets are not included automatically.</li>
  <li>Five samples is the program's minimum supported label, not a guarantee of adequate statistical power.</li>
</ul>

<h3>Loop stability detection algorithm</h3>
<p>
The <b>Stability Detection</b> table evaluates each run, DUT, channel, voltage,
current and error metric independently. It first calculates one mean error for
each loop. Starting from Loop 1, it tests each possible starting loop together
with every later loop. The first remaining sequence that satisfies every rule
is reported as the stable period.
</p>
<pre>
P = min(abs(L_strict), abs(U_strict))
span usage = 100 * (maximum loop mean - minimum loop mean) / P
standard-deviation usage = 100 * sample_std(loop means) / P
drift usage = 100 * abs(OLS slope of loop mean versus loop number) / P
</pre>
<table>
  <tr><th>Rule</th><th>Default requirement</th><th>Reason</th></tr>
  <tr><td>Confirmation length</td><td>At least 2 consecutive loops</td><td>Requires the behavior to repeat at least once before stability can be reported.</td></tr>
  <tr><td>Point compliance</td><td>100% of points pass</td><td>A stable but out-of-bound output is not acceptable stability.</td></tr>
  <tr><td>Loop-mean span</td><td>At most 10% of the strict engineering limit</td><td>Controls total peak-to-peak movement.</td></tr>
  <tr><td>Loop-mean standard deviation</td><td>At most 5% of the strict engineering limit</td><td>Controls typical loop-to-loop scatter.</td></tr>
  <tr><td>Linear drift</td><td>At most 1% of the strict engineering limit per loop</td><td>Rejects a sequence that is still steadily warming, cooling or drifting.</td></tr>
</table>
<p>
<b>Stable From Loop</b> identifies the first loop in the accepted sequence.
<b>Confirmed At Loop</b> identifies the second qualifying loop, which is the
earliest point when the program has enough evidence to declare stability. For
example, stability beginning at Loop 3 is confirmed at Loop 4.
</p>
<p>
The program labels the <b>overall DUT stable</b> only when every analyzed
voltage/current/metric series reaches stability. The overall confirmation loop
is the latest <b>Confirmed At Loop</b> among all those series. If even one
series remains unstable, the insight summary reports that overall DUT stability
was not reached and states how many series failed the criteria.
</p>
<div class="warning">
This is a transparent engineering screening algorithm, not a formal
change-point, stationarity or time-series hypothesis test. The conclusion
depends on the configured engineering limits and thresholds. Slow nonlinear
drift, environmental cycles and correlated measurements still require graph
review and engineering judgment.
</div>

<h3>Hornbill sinking test</h3>
<p>
In Bundle Test, select <b>Hornbill</b>, enable <b>Voltage Accuracy</b>, then
check <b>Sinking Test (External Source/Sink PSU)</b>. Sinking Test is an
exclusive voltage-accuracy mode: selecting it clears static-current,
changing-current, oscilloscope, and all other measurement-test selections.
Report, graph, temperature, and Blynk options are preserved. The option uses
<code>HornbillVoltageMeasurementwithSinkBox_External_PSU_Capable_Source_and_Sink</code>
instead of the standard Hornbill voltage runner.
</p>
<p>
Enter a distinct VISA address under <b>External Source/Sink PSU</b>. Configure
the positive current limit as a value greater than zero, the negative current
limit as a value below zero, and the sink-box slew rate as a value greater
than zero. Preflight prevents the run when these values or the external-source
address are missing. Oscilloscope capture mode is not supported by this
sinking runner.
</p>

<h3>Automated text and error-trend analysis</h3>
<p>
The <b>Text Analysis</b> tab converts loop statistics into deterministic
operator-readable conclusions. It does not use an online AI service. Every
sentence is produced from stored measurements, explicit formulas and fixed
engineering thresholds, so the conclusion can be reproduced and debugged.
</p>
<p>
Both <b>Analyze Existing Data</b> and <b>Compare Two Runs</b> use the same
five-part decision format:
</p>
<ol>
  <li><b>Status</b>: Pass, Warning, Fail, or Insufficient Data.</li>
  <li><b>Finding</b>: the most important result in plain language.</li>
  <li><b>Magnitude</b>: the measured effect relative to the strict engineering limit.</li>
  <li><b>Confidence</b>: Insufficient, Low, Medium, or High according to repeated-loop evidence.</li>
  <li><b>Recommended Action</b>: the next operator or engineering check.</li>
</ol>
<p>
For an individual trend, Fail means the latest mean reached or exceeded its
limit. Warning identifies near-limit behavior, worsening magnitude, jumps,
outliers, or unconfirmed stability. For comparison, Fail is reserved for a
supported difference that is both statistical and practically meaningful;
preliminary or one-sided evidence is a Warning. Insufficient Data is used when
repeatability cannot yet be evaluated.
</p>
<table>
  <tr><th>Term</th><th>Calculation</th><th>Interpretation</th></tr>
  <tr><td>Signed trend</td><td>OLS slope of loop mean error versus loop number. Flat when <code>100 * abs(slope) / P &lt;= 0.25%</code> per loop.</td><td>Increasing/decreasing describes signed error direction, not automatically improvement or deterioration.</td></tr>
  <tr><td>Early mean</td><td>Mean of the first three loops, or half the available loops when fewer exist.</td><td>Initial operating level.</td></tr>
  <tr><td>Late mean</td><td>Mean of the final matching window.</td><td>Latest operating level.</td></tr>
  <tr><td>Movement relative to zero</td><td><code>100 * (abs(late)-abs(early)) / P</code>. Above +1% moves away; below -1% moves toward zero.</td><td>Determines whether error magnitude improved or worsened.</td></tr>
  <tr><td>Boundary direction</td><td>Uses movement in absolute error and late mean limit usage.</td><td>Labels approaching, moving away, no meaningful movement, or near/beyond the boundary.</td></tr>
  <tr><td>Sudden jump</td><td>Consecutive loop-mean change of at least 5% of <code>P</code>.</td><td>Highlights abrupt behavior requiring wiring, range, load or DUT review.</td></tr>
  <tr><td>Robust outlier</td><td><code>robust_z = 0.6745 * abs(x-median) / MAD</code>; flagged above 3.5.</td><td>Identifies unusual loop means without deleting them.</td></tr>
  <tr><td>Oscillation</td><td>Rate at which the sign of consecutive loop changes reverses. At least 60% is oscillating; at most 20% is mostly monotonic.</td><td>Separates alternating movement from one-direction drift.</td></tr>
  <tr><td>Priority score</td><td>Combines late limit usage, drift, jumps, outliers, instability and movement away from zero.</td><td>Sorts review order only; it is not a specification, p-value or probability.</td></tr>
</table>
<p>
The text overview reports overall counts and the ten highest-priority
conditions. The table below it contains every condition with its calculation,
classification and complete narrative. Export creates
<code>analysis_trend_summary.csv</code> and
<code>analysis_trend_report.txt</code>.
</p>
<p>
When <b>Compare Two Runs</b> is selected, the same tab adds a
<b>Run / Channel Comparison</b> detail table and comparison narrative. Conditions
are matched only when DUT, test, set voltage, set current, metric and loop agree.
The text states the signed A-B difference, percentage of the strict limit,
statistical-difference result, practical-difference result, evidence strength
and engineering conclusion. The ten highest-priority matched differences appear
in the overview. Export also creates
<code>analysis_comparison_report.txt</code>.
</p>
<p>
The <b>Visual Dashboard</b> includes two trend graphs. <b>Individual Trend</b>
plots each condition's mean error against loop number. <b>Comparison Trend</b>
plots the matched A-B mean-error difference against loop number. A comparison
line that remains flat near zero indicates similar run behavior; a persistent
offset or movement away from zero indicates a systematic or growing
difference. Dashboard filters apply to both graphs, and export writes
<code>loop_stability.png</code> and <code>comparison_trend.png</code>.
</p>
<p>
Folder analysis started from the <b>Analyze Selected Results</b> or
<b>Compare Run A and Run B</b> buttons runs on a background Qt thread. Large
Excel/report comparisons can take tens of seconds, but the window remains
responsive and the status line shows that loading and matching are in progress.
Automatic post-test refresh still uses the same deterministic analysis engine.
</p>

<h3>Software update workflow</h3>
<p>
The <b>Software Update</b> tab allows packaged installations to update without
running the installer again. Enter the internal network path or HTTPS URL of
<code>update_manifest.json</code>, save it, and select
<b>Check for Updates</b>. When a newer version is available, select
<b>Download and Install</b>. The program verifies the package SHA-256, closes,
starts the external updater, and restarts after installation.
</p>
<p>
Publishers set the version in <code>VERSION</code> and run
<code>Make_GUI_Executable_Program.py</code>. The build creates the application
folder, versioned ZIP, updater helper and manifest. Publish the generated ZIP
and manifest in the same folder. Existing
<code>Instrument_Config_Files</code> and <code>csv</code> data are preserved.
The previous application remains in
<code>Test_Automation_Program.previous</code> for rollback.
</p>
<div class="warning">
Only publish trusted packages. Never bypass SHA-256 verification or install an
update from an untrusted manifest location.
</div>

<h3>Maximum/minimum highlighting and generated files</h3>
<ul>
  <li>Minimum signed-error cells and rows are highlighted green.</li>
  <li>Maximum and maximum-absolute-error cells and rows are highlighted red.</li>
  <li><code>analysis_summary.csv</code> contains condition-specific channel statistics.</li>
  <li><code>analysis_loop_performance.csv</code> contains individual run/loop performance.</li>
  <li><code>analysis_stability_summary.csv</code> contains the detected stable start, confirmation loop, span, scatter, drift and failed criteria.</li>
  <li><code>analysis_trend_summary.csv</code> contains trend direction, early/late shift, boundary movement, jumps, oscillation, outliers, stability and narrative text.</li>
  <li><code>analysis_trend_report.txt</code> contains the operator-readable trend overview and highest-priority conclusions.</li>
  <li><code>analysis_comparison_report.txt</code> contains matched Run A/Run B statistical and practical conclusions.</li>
  <li><code>analysis_channel_comparison.csv</code> contains matched-condition channel relationships.</li>
  <li><code>analysis_hypothesis_tests.csv</code> contains bias and mean-equivalence assessments with their null hypotheses.</li>
  <li><code>analysis_extremes.csv</code> identifies the run, loop, voltage, and current where each extreme occurred.</li>
</ul>

<div class="warning">
Statistics describe the collected sample only. A small sample count, inferred
legacy loop number, changed wiring, different instrument range, temperature
change, or unmatched setpoint can make channels unsuitable for comparison.
</div>
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
