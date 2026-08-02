"""Production application entry point and main launcher window."""

import datetime
import faulthandler
import os
import sys
import traceback
from pathlib import Path


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from SCPI_Library.simulation import initialize_main_thread_visa, is_simulation_mode


if __name__ == "__main__":
    main_thread_resource_manager = initialize_main_thread_visa()
    if "--visa-diagnostics" in sys.argv:
        print(f"VISA library: {main_thread_resource_manager.visalib}")
        print("VISA resources:")
        visa_resources = main_thread_resource_manager.list_resources()
        for visa_resource in visa_resources:
            print(f"  {visa_resource}")
        for visa_resource in visa_resources:
            if not visa_resource.upper().startswith("GPIB"):
                continue
            gpib_instrument = None
            try:
                gpib_instrument = main_thread_resource_manager.open_resource(
                    visa_resource
                )
                gpib_instrument.timeout = 10000
                gpib_instrument.write_termination = "\n"
                gpib_instrument.read_termination = "\n"
                gpib_instrument.clear()
                gpib_instrument.write("ID?")
                print(
                    f"GPIB identity ({visa_resource}): "
                    f"{gpib_instrument.read()}"
                )
            except Exception as exception:
                print(f"GPIB probe failed ({visa_resource}): {exception}")
                raise SystemExit(1) from exception
            finally:
                if gpib_instrument is not None:
                    gpib_instrument.close()
        raise SystemExit(0)


from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from common.output_capture import my_result
from common.output_logging import print_console_safe
from common.path import setup_img_folder
from DUT_Test_Scripts.DUT_screenshot import ScreenShotDialog
from instruments.LowVoltageTest import LowVoltageTestDialog
from instruments.NoiseTestVoltageSweep import NoiseVoltageSweepDialog
from instruments.TemperatureMeasurement import TemperatureMeasurementDialog
from instruments.TestVolt_HB_34470A import (
    VoltageCalibrationDialog as VoltageCalibration34470ADialog,
)
from instruments.TestVolt_HB_3458 import (
    VoltageCalibrationDialog as VoltageCalibration3458Dialog,
)
from instruments.instrument_discovery import (
    get_all_visa_resources as NewGetVisaSCPIResources,
)
from instruments.waveform_anomaly import WaveformFolderAnalyzerDialog
from ui.all_test_dialog import (
    ACSourceSetting,
    AllTestMeasurement,
    ComboBoxWheelFilter,
    DiscoveryResult,
    ParameterSnapshot,
    Parameters,
    ScanSelectedVisaResources,
    TestCancelled,
    TestState,
    TestWorker,
    VoltageAccuracyPlotWindow,
    image_Window,
    image_Window2,
)
from ui.dialog_registry import DialogRegistration, DialogRegistry
from ui.documentation_tab import ProgramDocumentationTab, TestPatternsTab
from ui.keysight_command_tab import KeysightCommandTab
from ui.software_update_tab import SoftwareUpdateTab
from ui.test_script_assistant_tab import TestScriptAssistantTab


_fatal_error_log = None


def _application_crash_log_path():
    if getattr(sys, "frozen", False):
        application_root = Path(sys.executable).resolve().parent
    else:
        application_root = Path(__file__).resolve().parent.parent
    return application_root / "crash_log.txt"


def _install_global_crash_logging():
    global _fatal_error_log

    crash_log_path = _application_crash_log_path()
    _fatal_error_log = crash_log_path.open("a", encoding="utf-8", buffering=1)
    _fatal_error_log.write(
        f"\n=== APPLICATION START {datetime.datetime.now().isoformat()} ===\n"
    )
    faulthandler.enable(file=_fatal_error_log, all_threads=True)
    original_excepthook = sys.excepthook

    def log_uncaught_exception(exception_type, exception, exception_traceback):
        _fatal_error_log.write(
            f"\n=== UNCAUGHT EXCEPTION "
            f"{datetime.datetime.now().isoformat()} ===\n"
        )
        traceback.print_exception(
            exception_type,
            exception,
            exception_traceback,
            file=_fatal_error_log,
        )
        _fatal_error_log.flush()
        original_excepthook(exception_type, exception, exception_traceback)

    sys.excepthook = log_uncaught_exception


class MainWindow(QMainWindow):
    """Main launcher for supported production workflows."""

    TEST_SELECTION_DIALOGS = (
        "voltage_calibration_dialog",
        "voltage_calibration_34470a_dialog",
        "low_voltage_test_dialog",
        "noise_voltage_sweep_dialog",
        "temperature_measurement_dialog",
        "waveform_analyzer_dialog",
    )

    def __init__(self):
        super().__init__()
        self.params = Parameters()
        title = "DUT TEST GUI"
        if is_simulation_mode():
            title += " - SIMULATION MODE"
        self.setWindowTitle(title)
        self.resize(1180, 820)
        self.setWindowFlags(Qt.Window)
        self.CurrentTab = 0

        self.dialog_registry = self._create_dialog_registry()
        self.test_options = self.dialog_registry.indexed_selection_options(
            self.TEST_SELECTION_DIALOGS
        )
        self.initTabs()

        if is_simulation_mode():
            self.statusBar().showMessage(
                "SIMULATION MODE - no real instruments are controlled"
            )
            self.statusBar().setStyleSheet(
                "background-color: #b45309; color: white; font-weight: bold;"
            )

        heading = QLabel("Automation Test Control Center")
        heading.setObjectName("mainTitle")
        subtitle = QLabel(
            "Configure instruments, run DUT workflows, inspect results, and "
            "manage engineering utilities from one workspace."
        )
        subtitle.setObjectName("mainSubtitle")
        subtitle.setWordWrap(True)
        heading_layout = QVBoxLayout()
        heading_layout.setSpacing(3)
        heading_layout.addWidget(heading)
        heading_layout.addWidget(subtitle)

        mode_badge = QLabel("SIMULATION" if is_simulation_mode() else "HARDWARE")
        mode_badge.setObjectName(
            "simulationBadge" if is_simulation_mode() else "hardwareBadge"
        )
        mode_badge.setAlignment(Qt.AlignCenter)
        header_layout = QHBoxLayout()
        header_layout.addLayout(heading_layout, stretch=1)
        header_layout.addWidget(mode_badge)
        header_card = QFrame()
        header_card.setObjectName("mainHeaderCard")
        header_card.setLayout(header_layout)

        self.QButton_Widget = QPushButton("Open Bundle Test")
        self.QButton_Widget.setObjectName("mainAction")

        layout = QVBoxLayout()
        layout.addWidget(header_card)
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.QButton_Widget)
        layout.setSpacing(14)
        layout.setContentsMargins(22, 22, 22, 22)

        self.page_home = QWidget()
        self.page_home.setObjectName("homePage")
        self.page_home.setLayout(layout)
        self.setCentralWidget(self.page_home)
        self.tab_widget.currentChanged.connect(self.currentTabChanged)
        self.QButton_Widget.clicked.connect(self.PushBtnClicked)
        self._apply_main_theme()

    def initTabs(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("mainTabs")
        self.tab_NewBundle = QWidget()
        self.tab_ScreenShot = QWidget()
        self.tab_TestList = QWidget()
        self.tab_Documentation = ProgramDocumentationTab()
        self.tab_TestPatterns = TestPatternsTab()
        self.tab_KeysightCommands = KeysightCommandTab()
        self.tab_TestScriptAssistant = TestScriptAssistantTab()
        self.tab_SoftwareUpdate = SoftwareUpdateTab()

        for widget, title in (
            (self.tab_NewBundle, "Bundle Test"),
            (self.tab_ScreenShot, "Screenshot"),
            (self.tab_TestList, "Test Selection"),
            (self.tab_Documentation, "Documentation"),
            (self.tab_TestPatterns, "Test Patterns"),
            (self.tab_KeysightCommands, "Keysight Commands"),
            (self.tab_TestScriptAssistant, "Script Assistant"),
            (self.tab_SoftwareUpdate, "Software Update"),
        ):
            tab_index = self.tab_widget.addTab(widget, title)
            self.tab_widget.setTabToolTip(tab_index, title)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setElideMode(Qt.ElideNone)
        self.tab_widget.setUsesScrollButtons(True)
        self.tab_widget.tabBar().setExpanding(False)

        self.NewBundleUI()
        self.ScreenShotUI()
        self.TestListUI()
        QTimer.singleShot(2000, self.tab_SoftwareUpdate.check_automatically)

    def setupTabUI(
        self,
        tab,
        image_path,
        description,
        tab_index,
        tab_text,
        label_size=(800, 600),
    ):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                *label_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        else:
            pixmap = QPixmap(*label_size)
            pixmap.fill(Qt.lightGray)

        image_label = QLabel()
        image_label.setObjectName("workflowImage")
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)

        description_label = QLabel(description)
        description_label.setObjectName("workflowDescription")
        description_label.setAlignment(Qt.AlignCenter)
        description_label.setWordWrap(True)

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(image_label)
        layout.addWidget(description_label)
        self.tab_widget.setTabText(tab_index, tab_text)

    def NewBundleUI(self):
        self.setupTabUI(
            self.tab_NewBundle,
            str(setup_img_folder / "2.png"),
            "Test GUI for Bundle Measurement\n\n"
            "Configure and execute supported DUT tests.",
            0,
            "Bundle Test (Voltage/Current)",
        )

    def ScreenShotUI(self):
        self.setupTabUI(
            self.tab_ScreenShot,
            str(setup_img_folder / "7.png"),
            "Instrument Display Capture\n\n"
            "Capture instrument screenshots for documentation and analysis.",
            1,
            "Instrument ScreenShot",
        )

    def TestListUI(self):
        layout = QVBoxLayout(self.tab_TestList)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title_label = QLabel("Engineering Workflows")
        title_label.setObjectName("sectionTitle")
        title_label.setAlignment(Qt.AlignCenter)

        description_label = QLabel(
            "Select a supported Hornbill calibration or scope-capture workflow."
        )
        description_label.setObjectName("sectionDescription")
        description_label.setAlignment(Qt.AlignCenter)
        description_label.setWordWrap(True)

        self.test_list = QListWidget()
        self.test_list.setObjectName("workflowList")
        for test_index, title, description in self.test_options:
            item = QListWidgetItem(f"{title}\n{description}")
            item.setData(Qt.UserRole, test_index)
            self.test_list.addItem(item)
        self.test_list.itemDoubleClicked.connect(self.on_test_selected)
        if self.test_list.count():
            self.test_list.setCurrentRow(0)

        select_button = QPushButton("Open Selected Test")
        select_button.setObjectName("workflowAction")
        select_button.clicked.connect(self.on_select_button_clicked)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(self.test_list)
        layout.addWidget(select_button)
        self.tab_widget.setTabText(2, "Test Selection")

    def _apply_main_theme(self):
        self.setStyleSheet(
            """
            QWidget#homePage { background: #eef3f9; }
            QFrame#mainHeaderCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #17365d, stop:1 #2563a5);
                border-radius: 13px;
                padding: 14px 18px;
            }
            QLabel#mainTitle {
                color: white;
                font-size: 25px;
                font-weight: 700;
            }
            QLabel#mainSubtitle { color: #dbeafe; font-size: 13px; }
            QLabel#hardwareBadge, QLabel#simulationBadge {
                color: white;
                border-radius: 12px;
                padding: 7px 14px;
                font-size: 11px;
                font-weight: 700;
                min-width: 90px;
            }
            QLabel#hardwareBadge { background: #15803d; }
            QLabel#simulationBadge { background: #d97706; }
            QTabWidget#mainTabs::pane {
                background: white;
                border: 1px solid #d4deea;
                border-radius: 10px;
                top: -1px;
            }
            QTabWidget#mainTabs QTabBar::tab {
                background: #dfe7f1;
                color: #4a5d73;
                border: none;
                min-width: 220px;
                padding: 11px 14px;
                margin-right: 3px;
                font-size: 11px;
                font-weight: 600;
            }
            QTabWidget#mainTabs QTabBar::tab:selected {
                background: #2563eb;
                color: white;
            }
            QTabWidget#mainTabs QTabBar::tab:hover:!selected {
                background: #cbd8e7;
                color: #17365d;
            }
            QLabel#workflowImage {
                background: #f8fafc;
                border: 1px solid #d5dfeb;
                border-radius: 10px;
                padding: 10px;
            }
            QLabel#workflowDescription {
                background: #eff6ff;
                color: #334e68;
                border-left: 5px solid #3b82f6;
                border-radius: 7px;
                padding: 14px;
                font-size: 15px;
                font-weight: 600;
            }
            QLabel#sectionTitle {
                color: #17365d;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#sectionDescription {
                color: #5b6b7f;
                font-size: 14px;
                padding-bottom: 5px;
            }
            QListWidget#workflowList {
                background: #f8fafc;
                border: 1px solid #cfdae7;
                border-radius: 9px;
                padding: 8px;
                outline: none;
                font-size: 14px;
            }
            QListWidget#workflowList::item {
                background: white;
                color: #31445b;
                border: 1px solid #e1e8f0;
                border-radius: 7px;
                padding: 12px;
                margin: 4px;
            }
            QListWidget#workflowList::item:selected {
                background: #dbeafe;
                color: #17365d;
                border: 2px solid #3b82f6;
            }
            QListWidget#workflowList::item:hover:!selected {
                background: #eff6ff;
                border-color: #93c5fd;
            }
            QPushButton#mainAction, QPushButton#workflowAction {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 11px 22px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton#mainAction:hover, QPushButton#workflowAction:hover {
                background: #1d4ed8;
            }
            QPushButton#mainAction:pressed, QPushButton#workflowAction:pressed {
                background: #1e40af;
            }
            QStatusBar {
                background: #17365d;
                color: white;
                font-weight: 600;
            }
            """
        )

    def on_test_selected(self, item):
        return self.open_test_by_index(item.data(Qt.UserRole))

    def on_select_button_clicked(self):
        current_item = self.test_list.currentItem()
        if current_item is not None:
            return self.on_test_selected(current_item)
        return None

    def open_test_dialog(self, test_index):
        return self.open_test_by_index(test_index)

    def currentTabChanged(self, index):
        self.CurrentTab = index
        self.QButton_Widget.setVisible(index < 3)
        action_labels = {
            0: "Open Bundle Test",
            1: "Open Screenshot Tool",
            2: "Open Selected Workflow",
        }
        if index in action_labels:
            self.QButton_Widget.setText(action_labels[index])
        print_console_safe(f"Current tab changed to: {index}")

    def PushBtnClicked(self):
        if self.CurrentTab >= 3:
            return None
        if self.CurrentTab < 2:
            return self.open_test_by_index(self.CurrentTab)
        current_item = self.test_list.currentItem()
        if current_item is None:
            print_console_safe("Please select a test from the list first.")
            return None
        return self.open_test_by_index(current_item.data(Qt.UserRole))

    def open_test_by_index(self, index):
        return self.dialog_registry.open(self, index)

    def _create_dialog_registry(self):
        registrations = (
            DialogRegistration(
                "Bundle Test",
                "Production queued test dialog",
                "bundle_dialog",
                AllTestMeasurement,
            ),
            DialogRegistration(
                "Screenshot",
                "Instrument screenshot dialog",
                "screenshot_dialog",
                lambda: ScreenShotDialog(self),
            ),
            DialogRegistration(
                "Voltage Calibration - 3458A",
                "Hornbill voltage calibration using a 3458A DMM",
                "voltage_calibration_dialog",
                VoltageCalibration3458Dialog,
            ),
            DialogRegistration(
                "Voltage Calibration - 34470A",
                "Hornbill voltage calibration using a 34470A DMM",
                "voltage_calibration_34470a_dialog",
                VoltageCalibration34470ADialog,
            ),
            DialogRegistration(
                "Hornbill Low Voltage Scope Capture",
                "Sweep Hornbill DIAG points and save one scope image per increment",
                "low_voltage_test_dialog",
                LowVoltageTestDialog,
            ),
            DialogRegistration(
                "Hornbill Noise Test Voltage Sweep",
                "Sweep Hornbill voltage with SCPI and save scope images",
                "noise_voltage_sweep_dialog",
                NoiseVoltageSweepDialog,
            ),
            DialogRegistration(
                "DAQ973A Temperature Measurement",
                "Acquire thermocouple temperatures and save them to CSV",
                "temperature_measurement_dialog",
                TemperatureMeasurementDialog,
            ),
            DialogRegistration(
                "Waveform Image Anomaly Analyzer",
                "Load a folder of scope PNG files and highlight abnormal traces",
                "waveform_analyzer_dialog",
                WaveformFolderAnalyzerDialog,
            ),
        )
        return DialogRegistry(registrations, print_console_safe)


if __name__ == "__main__":
    _install_global_crash_logging()
    original_stdout = sys.stdout
    my_result.seek(0)
    my_result.truncate(0)
    sys.stdout = my_result

    app = QApplication(sys.argv)
    win = MainWindow()
    win.setWindowFlags(
        Qt.Window
        | Qt.WindowMinimizeButtonHint
        | Qt.WindowMaximizeButtonHint
        | Qt.WindowCloseButtonHint
    )
    win.show()

    sys.stdout = original_stdout
    sys.exit(app.exec())
