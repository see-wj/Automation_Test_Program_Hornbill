# Hardware Smoke-Test Checklist

> Status: pending until supported instruments are physically available. Automated
> simulation and offscreen tests do not replace the checks in this document.

Calibration development remains gated until the baseline hardware checks below
pass with the intended DUT and instrument setup.

Record the release candidate, instrument inventory, safety outcomes, and DUT matrix
in `HARDWARE_VALIDATION_RESULTS.md` while performing this checklist.

Use this checklist after worker, VISA, shutdown, or measurement changes. Automated
tests use mocked instruments and do not replace this validation.

Runs created with `python src/GUI.py --simulate` are software checks only and do
not satisfy any item in the hardware test matrix.

## Fault-Injection Checks

The simulation backend supports deterministic one-shot failures for automated
recovery testing:

```python
from SCPI_Library.simulation import clear_simulation_faults, inject_simulation_fault

inject_simulation_fault(
    "query",
    "timeout",
    resource_name="USB0::SIM::DMM::INSTR",
)
clear_simulation_faults()
```

Supported operations are `connect`, `write`, `query`, `read`, `report`, `close`,
and `close_manager`. Supported failures are `timeout`, `disconnect`, `report`, and
`cleanup`. Optional `command_pattern`, `after`, and `repeat` arguments narrow when
the fault occurs. Run `python -m unittest tests.test_simulation
tests.test_simulation_workflows tests.test_end_to_end_queue` to verify timeout,
disconnect, report, cleanup, queue halt, and queue resume behavior without hardware.

## Safety Preconditions

- Confirm the DUT voltage, current, and power ratings match the selected setup.
- Confirm PSU and ELoad outputs are off before connecting the DUT.
- Confirm the expected PSU, DMM, DMM2, ELoad, scope, and AC source addresses.
- Use a new writable save directory; do not use the legacy default path from the
  configuration files.
- Set the loop count to one and select only one measurement for each smoke test.
- Keep the instrument front panels and emergency stop accessible.

Do not continue if discovery assigns two roles to the same VISA address or if an
unexpected instrument is identified.

## Startup

From the project root with the virtual environment active:

```cmd
python src/GUI.py
```

Confirm that the GUI opens, instrument discovery completes, and preflight reports
no missing or duplicate addresses.

## Test Matrix

Record Pass, Fail, or Not Applicable for each row.

| DUT | Mode | Setup | Start | Pause/Resume | Stop | Complete | Report |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dolphin | Voltage | Required instruments connected |  |  |  |  |  |
| Dolphin | Current | Required instruments connected |  |  |  |  |  |
| Hornbill | Voltage | Required instruments connected |  |  |  |  |  |
| Hornbill | Current | Required instruments connected |  |  |  |  |  |

Use the actual ELoad or no-ELoad setup required by the selected measurement. Do
not substitute instruments solely to complete the matrix.

## Per-Test Procedure

1. Select the DUT, one mode, one measurement, and one loop.
2. Confirm all displayed ratings, channels, addresses, and save paths.
3. Start the test and verify live progress or graph updates appear.
4. Pause during a safe steady-state section and verify measurements stop advancing.
5. Resume and verify the same test continues without restarting the loop.
6. Repeat the test and request Stop during a safe steady-state section.
7. Verify the worker reports an abort and the GUI remains responsive.
8. Run once without interruption and verify normal completion.
9. Manually confirm PSU, ELoad, AC source, and scope outputs are in their expected
   safe states after completion, abort, and any failure.

## Result Verification

For every completed run, verify the timestamped run folder contains:

```text
raw/parameters.json
charts/
reports/
logs/run.log
logs/diagnostics.jsonl
```

Confirm CSV values match the instrument displays, the Excel report opens, graph
limits and units are correct, and no report opens automatically. Graph or monitoring
windows should appear automatically when selected.

## Failure Evidence

If a row fails, preserve the complete timestamped run folder and record:

- DUT, measurement, setup, and loop step.
- Instrument models, roles, VISA addresses, and firmware versions.
- Whether the failure occurred during start, pause, resume, stop, or cleanup.
- Front-panel output states immediately after the failure.
- The displayed error text and relevant `logs/run.log` timestamp.

Do not retry an unsafe shutdown failure until instrument outputs are manually
confirmed off and the cause is understood.
