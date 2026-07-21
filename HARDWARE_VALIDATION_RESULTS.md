# Hardware Validation Record

Complete this record only with the intended DUT and physical instruments. Simulation
results are not acceptable hardware-validation evidence.

## Release Candidate

- Commit: a458c29 plus validated pause/telemetry changes
- Branch or release: `fix/hardware-discovery`
- Date and time: 2026-07-18 12:38-14:47 MYT
- Operator: weijsee6
- Workstation: 5CD4258719
- VISA backend/version: PyVISA 1.14.1; Keysight VISA `visa32.dll`
- Result folders:
  - `C:\Users\weijsee6\OneDrive - Keysight Technologies\Intern_Junior\Shamman Xian Jun Lee\Test Data\Codex Helper\20260718_123834_476368_Dolphin`
  - `C:\Users\weijsee6\OneDrive - Keysight Technologies\Intern_Junior\Shamman Xian Jun Lee\Test Data\Codex Helper\20260718_124717_146941_Dolphin`
  - `C:\Users\weijsee6\OneDrive - Keysight Technologies\Intern_Junior\Shamman Xian Jun Lee\Test Data\Codex Helper\20260718_125313_964341_Dolphin`
  - `C:\Users\weijsee6\OneDrive - Keysight Technologies\Intern_Junior\Shamman Xian Jun Lee\Test Data\Codex Helper\20260718_130635_394391_Dolphin`
  - `C:\Users\weijsee6\OneDrive - Keysight Technologies\Intern_Junior\Shamman Xian Jun Lee\Test Data\Codex Helper\20260718_132343_205335_Dolphin`
  - `C:\Users\weijsee6\OneDrive - Keysight Technologies\Intern_Junior\Shamman Xian Jun Lee\Test Data\Codex Helper\20260718_140524_831370_Dolphin`
  - `C:\Users\weijsee6\OneDrive - Keysight Technologies\Intern_Junior\Shamman Xian Jun Lee\Test Data\Codex Helper\20260718_143811_109768_Dolphin`
  - `C:\Users\weijsee6\OneDrive - Keysight Technologies\Intern_Junior\Shamman Xian Jun Lee\Test Data\Codex Helper\20260718_144252_826032_Dolphin`

## Instrument Inventory

| Role | Manufacturer | Model | Serial Number | Firmware | VISA Address |
| --- | --- | --- | --- | --- | --- |
| PSU | Keysight Technologies | E36441A | CN10000023 | 01.00-01.01-01.01-2024100301 | `USB0::0x2A8D::0xCC04::CN10000023::0::INSTR` |
| DMM | Keysight Technologies | 34470A | MY57702180 | A.03.00-02.40-03.00-00.52-04-01 | `USB0::0x2A8D::0x0501::MY57702180::0::INSTR` |
| DMM2 | HP | 3458A | Not reported by `ID?` | Not reported by `ID?` | `GPIB0::22::INSTR` |
| ELoad | Keysight Technologies | E36731A | MY62100043 | K-01.13.93-01.00-02.11-01.05-2025011301 | `USB0::0x2A8D::0x5C02::MY62100043::0::INSTR` |
| Oscilloscope | N/A | Not required for voltage accuracy |  |  |  |
| AC Source | N/A | Not required for voltage accuracy |  |  |  |

## Safety Results

| Scenario | Outputs Disabled | Sessions Closed | GUI Responsive | Diagnostics Saved | Result |
| --- | --- | --- | --- | --- | --- |
| Normal completion | Pass: PSU and ELoad channel 1 queried as `0` | Pass: post-run VISA queries opened normally | Pass | Pass | Pass |
| Operator abort | Pass: PSU and ELoad channel 1 queried as `0` | Pass: post-run VISA queries opened normally | Pass | Pass | Pass |
| VISA timeout |  |  |  |  |  |
| Instrument disconnect |  |  |  |  |  |
| Report failure | Pass: PSU and ELoad channel 1 queried as `0` | Pass: post-run VISA queries opened normally | Pass | Pass | Pass |
| Application restart |  |  |  |  |  |

## DUT Test Matrix

| DUT | Mode | Measurement | Pause/Resume | Abort | Complete | Report | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dolphin | Voltage | Voltage Accuracy, 1-3 V, one and two loops | Pass | Pass | Pass | Pass | Pass |
| Dolphin | Current | Current Accuracy, 1-3 V and 1-3 A, one and two loops | Pass | Pass | Pass | Pass | Pass |
| Hornbill | Voltage |  |  |  |  |  |  |
| Hornbill | Current |  |  |  |  |  |  |

## Interrupted-Run Recovery

1. Start a run with at least two loops.
2. Allow the first loop to complete, then terminate the application during the next
   loop only after manually confirming a safe test condition.
3. Restart the application and verify the row is `Interrupted` and does not start.
4. Confirm the previous artifact directory is displayed.
5. Select **Retry Failed**, then **Run Queue**.
6. Verify the retry starts at the next fully completed loop and produces a new run
   directory with its own diagnostics and report artifacts.

Result:

## Deviations and Evidence

- Deviations:
- The operator selected `...\Test Data\Codex Helper` rather than the initially
  proposed repository-local evidence folder. The timestamped run directory above
  contains the complete evidence set.
- One earlier queue row with DUT `None` displayed `Failed`; it produced no run
  artifacts and is not counted as a hardware-validation attempt.
- Diagnostic files:
- `logs/run.log`
- `logs/diagnostics.jsonl`
- `logs/execution_checkpoint.json`
- The two-loop run recorded three `RUNNING -> PAUSED -> RUNNING`
  transitions, 18 realtime rows, `next_loop_index: 2`, and normal completion.
- The abort run recorded `RUNNING -> STOPPING -> ABORTED`, retained parameters,
  realtime data, logs, and `next_loop_index: 1`; no report was expected after abort.
- The first current run completed all measurements but exposed a report parameter
  key mismatch. A retry then exposed graph state incorrectly owned by `TestWorker`.
  Both failures retained diagnostics and left PSU and ELoad channel 1 off.
- The corrected current run completed with nine readings, CSV/error data, two
  charts, a valid workbook, and `next_loop_index: 1`.
- The current abort run recorded `RUNNING -> STOPPING -> ABORTED` and
  `next_loop_index: 0`; the operator confirmed that Abort functioned correctly.
- The final two-loop current run recorded `RUNNING -> PAUSING -> PAUSED -> RUNNING`,
  retained the paused state for approximately two minutes, wrote 18 realtime
  rows, completed both loops, and produced two charts and a valid workbook.
- The operator visually confirmed that current data appeared on the realtime
  graph and stopped and resumed with the test at safe checkpoints.
- The current percentage graph was regenerated with current on the x-axis and
  separate 1 V, 2 V, and 3 V series. The corrected workbook is
  `reports/CURRENT_CORRECTED_2026-07-18--13-29-02.xlsx`.
- Screenshots or photographs:
- GUI completion state and live voltage graph visually inspected on 2026-07-18.
- Issues created:
- Hardware discovery selected duplicate E36731A resources ambiguously and did not
  reach the 3458A legacy `ID?` fallback after guarded timeouts. Fixes are present
  on `fix/hardware-discovery` and covered by focused tests.
- Current report export used configuration keys instead of immutable GUI snapshot
  names and called graph methods with the worker as `self`. Both defects are fixed
  with report-generation regression coverage.
- Current percentage plots used voltage values on an axis labelled current,
  producing vertical lines. Percentage plots now sweep current horizontally and
  label each voltage series.
- Final approval:
- Pending fault/restart scenarios and Hornbill validation with the intended DUT.
