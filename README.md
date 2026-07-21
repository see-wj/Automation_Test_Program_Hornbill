# Python Test Automation Program

This is the remote repository for the automation test program used for Excavator, Hornbill and future DUT. 

## 📖 Getting Started

The program was developed using PyQt5 integrated with PyVisa Module to control the instrument via SCPI command.


## 🖥 For Non-Technical Users
You don’t need Python or VS Code!  
You can download the latest `.exe` build from **[GitHub Releases](https://github.com/ztian914/Automation_Test_Program/releases/)** and run it directly.

## 📚 User Guide

To access the **User Guide** (hosted on the company network):

**Path:**  
`file://remus/BID_RnD/Excavator/Zhuo_Tian_Test_Program/Internship_Documentation_ZhuoTian/`  

> 💡 Make sure you are connected to the **company Wi-Fi** and have mapped the network drive.  
> Then, copy the path above and paste it into **Microsoft Edge** to open the guide.
> Else, you can get the documentation from **Wei Jing**


## 📦Getting Started
Follow these steps to set up and run the application

### 1. Requirements
- **Python** `>= 3.11.2`  
  Download from the [official Python website](https://www.python.org/downloads/).
- **Visual Studio Code**  
  Download from the [VS Code website](https://code.visualstudio.com/).  
  Install the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python).

---
### 2. Create and Activate a Virtual Environment in VS Code (Recommended) 
Using a virtual environment keeps dependencies isolated from other projects.

1. Open your project folder in **VS Code**.
2. Open the integrated terminal (**Ctrl + `**).
3. Create the virtual environment:
    ```cmd
   python -m venv .venv
    ```
4. In VS Code, press **Ctrl + Shift + P**, search for **Python: Select Interpreter**,  
   and choose the one from `.venv`.
5. Close the terminal and open a new one — VS Code should automatically activate the venv.  
   You’ll know it’s active if your terminal prompt shows:
   ```
   (.venv) path\to\project>
   ```
---
### 3.   Install Dependencies
The dependencies for this program has been listed in `requirements.txt`. If you are running a virtual environment, you can install the dependencies using:

```cmd
pip install -r requirements.txt
```

The supported development runtime is Python 3.11.0, recorded in
`.python-version`. `requirements.txt` pins direct application dependencies.
For an exact copy of the environment used by CI and regression testing, install:

```cmd
pip install -r requirements-lock.txt
```

### VISA timeout

Instrument communication uses a 15-second timeout by default. Set the
`VISA_TIMEOUT_MS` environment variable to a positive millisecond value to
override it for normal SCPI and test-preflight connections.

### Test result folders

Each confirmed test run creates a unique timestamped folder inside the selected
save location:

```text
YYYYMMDD_HHMMSS_microseconds_DUT/
â”œâ”€â”€ raw/       Intermediate CSV files and parameters.json
â”œâ”€â”€ charts/    Generated chart images
â”œâ”€â”€ reports/   Excel reports
â””â”€â”€ logs/      Persistent run.log
```

`logs/run.log` is the readable execution log. `logs/diagnostics.jsonl` stores
structured state, instrument, command, cleanup, and traceback details for debugging.

Successful completion, abort, execution failure, and test-window close requests all
use the same cooperative shutdown path. ELoad, PSU, AC source, and oscilloscope
shutdown actions run independently so one instrument failure does not skip the rest.

During a test run, SCPI wrappers reuse one VISA session per instrument address.
Sessions are isolated to the worker thread, closed before final hardware shutdown,
and remain independent from GUI discovery and preflight connections.
Production test execution and cooperative pause, resume, and abort behavior live in
`src/execution/test_worker.py`; `src/GUI.py` owns presentation and signal wiring.
`src/GUI.py` remains the application entry point and legacy-dialog host, while the
production `AllTestMeasurement` dialog and its direct UI helpers live in
`src/ui/all_test_dialog.py`.
Mutable GUI parameter state and setup-file loading live in
`src/configuration/test_parameters.py`, keeping dialog construction separate from configuration data.
Each execution receives a `RunContext` from `src/execution/run_context.py`. It owns the run
tree, parameter snapshot, realtime CSV, chart paths, and diagnostics destinations;
queued runs therefore do not share output files. Report generators infer their own
`raw/` and `charts/` directories from the requested `reports/` directory.
`src/execution/test_run_controller.py` owns worker lifecycle and provides a FIFO queue for
sequential runs. `src/queueing/queue_coordinator.py` connects that controller to queue UI,
persistence, interrupted-run recovery, and reusable templates. Test-selection
widgets/state and worker parameter construction are
isolated in `src/configuration/test_selection.py` and
`src/configuration/test_configuration.py`. DUT setup files are loaded through
`src/configuration/configuration_service.py`.
Queue-template serialization and reconstruction are isolated in
`src/queueing/queue_template_service.py`; encoding-safe console and run-log writes
live in `src/common/output_logging.py`.
VISA enumeration, identity queries, IP/hostname classification, model-role mapping,
and discovery-resource cleanup live in `src/instruments/instrument_discovery.py`.
Production widget population and automatic role selection live in
`src/ui/instrument_discovery_ui.py`.
Production dialog signal declarations live in `src/ui/all_test_signal_bindings.py`,
and the legacy launcher uses `src/ui/dialog_registry.py` instead of an index-based
dialog chain. Shared DUT SCPI class loading and VISA preflight plumbing live in
`DUT_Test_Scripts/scpi_runtime.py`.

Use **Add to Queue** to snapshot the current setup without starting it. Pending rows
can be reordered or removed, and **Run Queue** executes them sequentially. Every row
receives its own run directory and reports `Pending`, `Running`, `Paused`,
`Stopping`, `Completed`, `Failed`, `Aborted`, `Interrupted`, or `Retried`. Aborting
an active row leaves the remaining queue available;
**Clear Pending** removes waiting rows.
**Duplicate** creates an independent copy of any selected row. **Retry Failed**
requeues failed, aborted, or interrupted rows using their original parameter
snapshot. **Save Template** stores pending rows in portable JSON, and **Load
Template** appends new
queue entries without reusing old run IDs.
Completed, failed, aborted, and removed history is limited to the newest 200 rows
per dialog session so long-running stations do not accumulate unbounded objects.
Pending and active items are saved atomically to
`Instrument_Config_Files/test_queue.json` and restored when the test dialog opens
again. A run that was active when the application exited is restored as
`Interrupted` with its previous artifact-directory path. It never starts
automatically; review its output and retry or remove it manually. Completed, failed,
and aborted rows are not restored.

Each run also writes `logs/execution_checkpoint.json` after a complete loop. Retrying
an interrupted run continues from the next fully completed loop and links the new
run to the previous artifact directory. A partially completed loop is intentionally
restarted because resuming from an unknown SCPI command would be unsafe.

The old multithread voltage prototype is retained under `src/experiments/` and is
loaded only when its legacy dialog is explicitly opened.

---

### 4. Run the Application
Inside the activated virtual environment, run:

```cmd
python src/GUI.py
```

Before validating changes with connected instruments, follow
[`HARDWARE_VALIDATION.md`](HARDWARE_VALIDATION.md).

### Run Automated Tests

From the project root, run the dependency-free regression suite with:

```cmd
python -B -m unittest discover -s tests -v
```

The suite uses mocked VISA resources and does not communicate with real instruments.
The Windows CI workflow in `.github/workflows/tests.yml` installs the locked
dependencies and runs this command for every push and pull request.

### Run Static Analysis

Ruff checks undefined names and unused imports in the modernized modules and test
suite. Install development dependencies and run:

```cmd
pip install -r requirements-dev.txt
python -m ruff check .
```

The initial scope is listed in `pyproject.toml`. Expand it gradually as legacy GUI
and measurement modules are refactored; do not hide new findings with broad ignores.

### Simulation Mode

When instruments are unavailable, launch the application with the explicit
simulation flag:

```cmd
python src/GUI.py --simulate
```

Simulation mode provides fake PSU, DMM, DMM2, ELoad, oscilloscope, and AC-source
VISA resources. The window title, status bar, run directory, parameter file, marker
file, and generated Excel report names identify simulated data. Simulation mode is
disabled by default and must not be used as hardware-validation evidence.

The automated suite covers Dolphin and Hornbill voltage/current worker workflows
and verifies that simulated outputs and setpoints return to a safe state afterward.
It also executes one-point voltage/current accuracy measurements through the real
Dolphin and Hornbill measurement classes with hardware delays disabled.
Temporary-directory integration tests generate simulated voltage/current CSV data,
two chart images, instrument metadata, configuration data, and labeled Excel reports.
An end-to-end queue test runs real `TestWorker` instances for Dolphin and Hornbill,
checks per-run artifact isolation and restart persistence, and verifies that pause,
resume, and abort can continue safely to the next queued run.

---

## 🔄 Git Integration
This project uses Git for version control.

- To clone the repository:

```cmd
git clone https://github.com/ztian914/Automation_Test_Program.git
```

- To pull the latest updates:

```cmd
git pull
```

**For better understanding on the use of git, you can refer to the user guide slide.**

---
## ⚙ Build Information
- The `.exe` file is **automatically built** using **GitHub Actions** whenever changes are pushed to the `master` branch, and uploaded to **GitHub Releases**.
- If you want to build it manually, you can use the included `Make_GUI_Executable_Program.py` build script:

```cmd
python Make_GUI_Executable_Program.py
```

The generated `.exe` will be inside the `src` folder.

---
## 👤 Authors

Contributors names and contact info
- Zhi Yuan Wong

- Lim Zhuo Tian
[@ZhuoTian](https://www.linkedin.com/in/lim-zhuo-tian-1741342b4)

- Wei Jing See

---

## 📌 Others
- This project has no license, but it is confidential under the use of **Keysight Technologies**. 
- Contributions, suggestions, and bug reports are welcome.
- Good luck for reading the code for the next developers.

---


