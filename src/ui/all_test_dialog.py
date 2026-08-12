"""Production all-tests dialog and its direct UI helpers."""

import datetime
import traceback
from pathlib import Path
from types import SimpleNamespace

import pyqtgraph as pg
from PyQt5.QtCore import QObject, QPointF, QThread, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from common.diagnostics import append_diagnostic
from configuration.configuration_service import configuration_path
from ui.error_dialogs import show_error_dialog
from instruments.instrument_discovery import (
    DiscoveryResult,
    get_configured_visa_resources as GetConfiguredVisaResources,
    get_visa_scpi_resources as GetVisaSCPIResources,
)
from ui.instrument_discovery_ui import present_discovery_result
from common.output_logging import append_timestamped_line, print_console_safe
from common.output_capture import my_result
from common.path import (
    IMAGE_PATH,
    IMAGE_PATH_2,
    POWER_IMAGE_PATH,
    config_folder,
)
from execution.preflight import validate_preflight
from SCPI_Library.instrument_errors import CleanupError, normalize_execution_error
from SCPI_Library.simulation import is_simulation_mode
from DUT_Test_Scripts.Dolphin.Dolphin_DUT_Test_No_ELoad_No_DMM import (
    VisaResourceManager,
)

desp_font = QFont("Times New Roman", 14, QFont.Bold)


def ScanSelectedVisaResources(dialog, on_progress=None):
    enabled_transports = set()
    transport_widgets = (
        ("usb", dialog.QCheckBox_USB_Widget),
        ("gpib", dialog.QCheckBox_GPIB_Widget),
        ("tcpip_ip", dialog.QCheckBox_IP_Widget),
        ("tcpip_hostname", dialog.QCheckBox_Hostname_Widget),
    )
    for transport, checkbox in transport_widgets:
        if checkbox.isChecked():
            enabled_transports.add(transport)

    selected_dut = dialog.QComboBox_DUT.currentText()
    config_path = configuration_path(config_folder, selected_dut)
    result = GetConfiguredVisaResources(
        config_path,
        enabled_transports=enabled_transports,
    )
    if on_progress is not None:
        on_progress(result)
    return result


class InstrumentDiscoveryWorker(QObject):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, configuration_file, enabled_transports, scan_function):
        super().__init__()
        self.configuration_file = configuration_file
        self.enabled_transports = set(enabled_transports)
        self.scan_function = scan_function

    @pyqtSlot()
    def run(self):
        try:
            result = self.scan_function(
                self.configuration_file,
                enabled_transports=self.enabled_transports,
            )
        except Exception as exception:
            self.failed.emit(str(exception))
            return
        self.completed.emit(result)


class image_Window(QDialog):
    """Class to display graph of DUT Test results"""

    def __init__(self, image_path_1=None, image_path_2=None):
        super().__init__()
        self.setWindowTitle("Image")

        # Convert Path objects to str
        image_path_1 = str(image_path_1 or IMAGE_PATH)
        image_path_2 = str(image_path_2 or IMAGE_PATH_2)

        self.im = QPixmap(image_path_1)
        self.im2 = QPixmap(image_path_2)
        
        # Check if the image loaded successfully
        if self.im.isNull():
            QMessageBox.warning(self, "Error", f"Failed to load image: {image_path_1}")
            self.close()
            return

        if self.im2.isNull():
            QMessageBox.warning(self, "Error", f"Failed to load image: {image_path_2}")
            self.close()
            return
        
        self.label = QLabel()
        self.label.setPixmap(self.im)

        self.label2 = QLabel()
        self.label2.setPixmap(self.im2)
        
        self.grid = QGridLayout()
        self.grid.addWidget(self.label, 1, 1)
        self.grid.addWidget(self.label2, 1, 2)

        self.setLayout(self.grid)

        self.setWindowFlags(Qt.Window)
        self.setModal(False)
        self.show()

        # Standard window flags
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

    def close_window(self):
        self.close()

class image_Window2(QDialog):
    """Class to display graph of DUT Test results"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image")
        self.im = QPixmap(POWER_IMAGE_PATH)
        
        # Check if the image loaded successfully
        if self.im.isNull():
            QMessageBox.warning(self, "Error", "Failed to load image.")
            self.close()  # Close the window
            return
        
        self.label = QLabel()
        self.label.setPixmap(self.im)
        
        self.grid = QGridLayout()
        self.grid.addWidget(self.label, 1, 1)
        self.setLayout(self.grid)
        self.setWindowFlags(Qt.Window)
        self.setModal(False)  # Set the dialog to be non-modal
        self.show()
        # Ensure standard window behavior
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

    def close_window(self):
        self.close()


#########----------------------- New Bundle Test (with Parameters)--------------------######################

# Class Parameters: Read Instrument Configuration Txt File (Gain etc..)
from configuration.test_parameters import (
    ComboBoxWheelFilter as ComboBoxWheelFilter,
    Parameters as Parameters,
)

from execution.test_worker import TestCancelled as TestCancelled, TestState, TestWorker
from execution.test_run_controller import TestRunController
from configuration.test_configuration import (
    ParameterSnapshot as ParameterSnapshot,
    prepare_run_submission,
)
from configuration.test_selection import (
    collect_test_selections,
    create_current_selection_widget,
    create_voltage_selection_widget,
)
from ui.test_queue_widget import TestQueueWidget
from queueing.queue_coordinator import QueueCoordinator
from ui.all_test_signal_bindings import connect_all_test_signals
from ui.realtime_plot import (
    RealtimeMeasurement,
    RealtimePlotSeries,
    report_percentage_error,
)
from ui.bundle_data_analysis_widget import BundleDataAnalysisWidget
from ui.temperature_plot_widget import TemperaturePlotWidget
from ui.webcam_widget import WebcamWidget
from execution.progress_timing import (
    MeasurementProgressTracker,
    expected_measurement_points,
    format_duration,
)
from execution.run_context import RunContext
from integrations.blynk_publisher import BlynkPublisher

class AllTestMeasurement(QDialog):
    """Class for configuring the voltage measurement DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguments, see DUT_Test_Scripts/Dolphin/DUT_Test.py.


    """
    DEFAULT_SAVE_LOCATION = (
        "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"
    )
    PARAMETER_TEXT_BINDINGS = (
        ("QLineEdit_Programming_Error_Gain", "Programming_Error_Gain"),
        ("QLineEdit_Programming_Error_Offset", "Programming_Error_Offset"),
        ("QLineEdit_Readback_Error_Gain", "Readback_Error_Gain"),
        ("QLineEdit_Readback_Error_Offset", "Readback_Error_Offset"),
        ("QLineEdit_Load_Programming_Error_Gain", "Load_Programming_Error_Gain"),
        ("QLineEdit_Load_Programming_Error_Offset", "Load_Programming_Error_Offset"),
        ("QLineEdit_Power", "Power"),
        ("QLineEdit_minVoltage", "minVoltage"),
        ("QLineEdit_maxVoltage", "maxVoltage"),
        ("QLineEdit_voltage_stepsize", "voltage_step_size"),
        ("QLineEdit_minCurrent", "minCurrent"),
        ("QLineEdit_maxCurrent", "maxCurrent"),
        ("QLineEdit_current_stepsize", "current_step_size"),
        ("QLineEdit_current_rated", "Current_Rating"),
        ("QLineEdit_voltage_rated", "Voltage_Rating"),
        ("QLineEdit_power_rated", "Power_Rating"),
        ("QLineEdit_power_step_size", "power_step_size"),
        ("QLineEdit_PowerINI", "powerini"),
        ("QLineEdit_rshunt", "rshunt"),
        ("QLineEdit_SweepPoints", "SweepPoints"),
        (
            "QLineEdit_External_Source_Positive_Current_Limit",
            "External_Source_Positive_Current_Limit",
        ),
        (
            "QLineEdit_External_Source_Negative_Current_Limit",
            "External_Source_Negative_Current_Limit",
        ),
        ("QLineEdit_Sink_Slew_Rate", "slewrate"),
        ("QLineEdit_Sinking_Initial_Voltage", "Sinking_Initial_Voltage"),
        ("QLineEdit_Sinking_Final_Voltage", "Sinking_Final_Voltage"),
        ("QLineEdit_Sinking_Voltage_Step_Size", "Sinking_Voltage_Step_Size"),
        ("QLineEdit_OVP_Level", "OVP_Level"),
        ("QLineEdit_Power_Programming_Error_Gain", "Power_Programming_Error_Gain"),
        ("QLineEdit_Power_Programming_Error_Offset", "Power_Programming_Error_Offset"),
        ("QLineEdit_Power_Readback_Error_Gain", "Power_Readback_Error_Gain"),
        ("QLineEdit_Power_Readback_Error_Offset", "Power_Readback_Error_Offset"),
        ("QLineEdit_Programming_Response_Up_NoLoad", "Programming_Response_Up_NoLoad"),
        ("QLineEdit_Programming_Response_Up_FullLoad", "Programming_Response_Up_FullLoad"),
        ("QLineEdit_Programming_Response_Down_NoLoad", "Programming_Response_Down_NoLoad"),
        ("QLineEdit_Programming_Response_Down_FullLoad", "Programming_Response_Down_FullLoad"),
        ("QLineEdit_OVP_Error_Gain", "OVP_ErrorGain"),
        ("QLineEdit_OVP_Error_Offset", "OVP_ErrorOffset"),
        ("QLineEdit_OSC_Display_Channel", "OSC_Channel"),
        ("QLineEdit_V_Settling_Band", "V_Settling_Band"),
        ("QLineEdit_T_Settling_Band", "T_Settling_Band"),
        ("QLineEdit_TimeScale", "TimeScale"),
        ("QLineEdit_VerticalScale", "VerticalScale"),
    )
    PARAMETER_COMBO_BINDINGS = (
        ("QLineEdit_DAQ_VisaAddress", "DAQ"),
        ("QLineEdit_External_Source_VisaAddress", "ExternalSource"),
        ("QComboBox_DMM_Instrument", "DMM_Instrument"),
        ("QComboBox_Hornbill_Measurement_Command", "Hornbill_Measurement_Command"),
        ("QComboBox_Relay_Control", "Relay_Control"),
        ("QComboBox_Voltage_Res", "VoltageRes"),
        ("QComboBox_set_PSU_Channel", "PSU_Channel"),
        ("QComboBox_set_ELoad_Channel", "ELoad_Channel"),
        ("QComboBox_SPOperationMode", "SPOperationMode"),
        ("QComboBox_Probe_Setting", "Probe_Setting"),
        ("QComboBox_Acq_Type", "Acq_Type"),
        ("QComboBox_Channel_CouplingMode", "Channel_CouplingMode"),
        ("QComboBox_Trigger_Mode", "Trigger_Mode"),
        ("QComboBox_Trigger_CouplingMode", "Trigger_CouplingMode"),
        ("QComboBox_Trigger_SweepMode", "Trigger_SweepMode"),
        ("QComboBox_Trigger_SlopeMode", "Trigger_SlopeMode"),
        ("QComboBox_noofloop", "noofloop"),
        ("QComboBox_updatedelay", "updatedelay"),
        ("QComboBox_AC_Supply_Type", "AC_Supply_Type"),
    )

    def __init__(self, queue_file=None):
        super().__init__()
        self.params = Parameters()
        self.worker = None
        self.active_params = None
        self.active_run_context = None
        self.queue_file = queue_file or (Path(config_folder) / "test_queue.json")
        self.run_controller = TestRunController(
            worker_factory=lambda *args: TestWorker(*args),
            parent=self,
        )
        self.run_controller.worker_created.connect(self._connect_worker)
        self.run_controller.request_setup_failed.connect(self._queue_setup_failed)
        self.test_state = TestState.IDLE
        self._cleanup_done = False
        self.run_storage = None
        self._output_root = None
        self.plot_window = VoltageAccuracyPlotWindow()
        self.temperature_plot_widget = TemperaturePlotWidget()
        self.webcam_widget = WebcamWidget()
        self.analysis_widget = BundleDataAnalysisWidget()
        self.last_Iset = None               #Shamman changes
        self.fail_prompt_active = False
        self.continue_on_boundary_failure = False
        self.realtime_plot_series = RealtimePlotSeries()
        self.progress_tracker = None
        self.blynk_active = False
        self.blynk_publisher = BlynkPublisher.from_environment(parent=self)
        self.instrument_discovery_thread = None
        self.instrument_discovery_worker = None

        self._build_ui()
        self.blynk_publisher.status_changed.connect(
            self._on_blynk_status_changed
        )
        self.blynk_publisher.notification_status_changed.connect(
            self._on_blynk_notification_status
        )
        self._update_blynk_controls()
        self.queue_coordinator = QueueCoordinator(
            self.run_controller,
            self.queue_widget,
            self.queue_file,
            self._prepare_queued_run,
            self.OutputBox.append,
            parent=self,
            template_directory=config_folder,
        )
        self._connect_signals()

        #Voltage/Current Test Selection with Enable/Disable Input Fields
        self.select_button()
        self.InteractiveAction()
        self.Image_Label_Setup()
        self.queue_coordinator.restore()

    def _build_ui(self):
        self._create_control_widgets()
        ui = self._create_configuration_widgets()
        self._create_dmm_settings_group()
        test_selection_layout = self._create_test_selection_layout(ui)
        self._create_connection_and_general_groups(ui)
        self._create_rating_and_error_groups(ui)
        self._create_scope_and_collection_groups(ui)
        right_container = self._create_execution_panel(ui)
        left_container = self._create_settings_panel(ui, test_selection_layout)
        self._install_main_layout(left_container, right_container)
        self._apply_bundle_theme()

    def _create_control_widgets(self):
        #Create find button 
        self.QPushButton_Widget0 = QPushButton()
        self.QPushButton_Widget0.setText("Save Path")
        self.QPushButton_Widget0.setObjectName("secondaryAction")
        self.QPushButton_Widget1 = QPushButton()
        self.QPushButton_Widget1.setText("Execute Test")
        self.QPushButton_Widget1.setObjectName("primaryAction")
        self.queue_test_button = QPushButton("Add to Queue")
        self.queue_test_button.setObjectName("secondaryAction")
        self.queue_widget = TestQueueWidget()
        self.QPushButton_Widget3 = QPushButton()
        self.QPushButton_Widget3.setText("Estimate Data Collection Time")
        self.QPushButton_Widget3.setObjectName("secondaryAction")
        self.QPushButton_Widget4 = QPushButton()
        self.QPushButton_Widget4.setText("Find Instruments")
        self.QPushButton_Widget4.setObjectName("discoveryAction")
        QPushButton_Widget5 = QPushButton()
        QPushButton_Widget5.setText("Return Home")
        
        
        self.QPushButton_Voltage_Widget = QPushButton()
        self.QPushButton_Voltage_Widget.setText("Voltage")
        self.QPushButton_Voltage_Widget.setObjectName("modeSelector")
        self.QPushButton_Current_Widget = QPushButton()
        self.QPushButton_Current_Widget.setText("Current/Power")
        self.QPushButton_Current_Widget.setObjectName("modeSelector")
        self.QPushButton_Voltage_Widget.setCheckable(True)
        self.QPushButton_Current_Widget.setCheckable(True)
        self.QPushButton_Voltage_Widget.setChecked(True)

        #Checkbox
        self.QCheckBox_Report_Widget = QCheckBox()
        self.QCheckBox_Report_Widget.setText("Generate Excel Report")
        self.QCheckBox_Report_Widget.setCheckState(Qt.Checked)
        self.QCheckBox_Image_Widget = QCheckBox()
        self.QCheckBox_Image_Widget.setText("Show Graph")
        self.QCheckBox_Image_Widget.setCheckState(Qt.Checked)
        self.QCheckBox_Temperature_Widget = QCheckBox()
        self.QCheckBox_Temperature_Widget.setText("Measure Temperature (DAQ973A)")
        self.QCheckBox_Temperature_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_Blynk_Widget = QCheckBox()
        self.QCheckBox_Blynk_Widget.setText(
            "Send Live Data to Blynk "
            f"({self.blynk_publisher.update_interval:g}-second batch)"
        )
        self.QCheckBox_Blynk_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_Blynk_Widget.setToolTip(
            "Requires the BLYNK_AUTH_TOKEN environment variable. "
            "Blynk failures never stop the instrument test."
        )
        self.Blynk_Status_Label = QLabel("Blynk: Disabled")
        self.QCheckBox_SpecialCase_Widget = QCheckBox()
        self.QCheckBox_SpecialCase_Widget.setText("Special Case (0% <-> 100%)")
        self.QCheckBox_SpecialCase_Widget.setCheckState(Qt.Checked)
        self.QCheckBox_NormalCase_Widget = QCheckBox()
        self.QCheckBox_NormalCase_Widget.setText("Normal Case (50% <-> 100%)")
        self.QCheckBox_NormalCase_Widget.setCheckState(Qt.Checked)
        self.QCheckBox_Lock_Widget = QCheckBox()
        self.QCheckBox_Lock_Widget.setText("🔒Lock Widget")
        self.QCheckBox_USB_Widget = QCheckBox()
        self.QCheckBox_USB_Widget.setText("USB")
        self.QCheckBox_USB_Widget.setChecked(True)
        self.QCheckBox_GPIB_Widget = QCheckBox()
        self.QCheckBox_GPIB_Widget.setText("GPIB")
        self.QCheckBox_GPIB_Widget.setChecked(True)
        self.QCheckBox_IP_Widget = QCheckBox()
        self.QCheckBox_IP_Widget.setText("IP address")
        self.QCheckBox_IP_Widget.setChecked(True)
        self.QCheckBox_Hostname_Widget = QCheckBox()
        self.QCheckBox_Hostname_Widget.setText("Host name")
        self.QCheckBox_Hostname_Widget.setChecked(True)


        #Test Selection checkbox
        self.QCheckBox_VoltageAccuracy_Widget = QCheckBox()
        self.QCheckBox_VoltageAccuracy_Widget.setText("Voltage Accuracy")
        self.QCheckBox_VoltageAccuracy_Widget.setCheckState(Qt.Checked)

        # Child checkbox under Voltage Accuracy
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget = QCheckBox()
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget.setText("Current Static (Voltage Change)")
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget.setCheckState(Qt.Checked)

        self.QCheckBox_Voltage_Accuracy_Current_Mode_Widget = QCheckBox()
        self.QCheckBox_Voltage_Accuracy_Current_Mode_Widget.setText("Current Change (Load Change)")
        self.QCheckBox_Voltage_Accuracy_Current_Mode_Widget.setCheckState(Qt.Unchecked)

        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget = QCheckBox()
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget.setText("Oscilloscope Capture (Voltage Change)")
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_Sinking_Test_Widget = QCheckBox()
        self.QCheckBox_Sinking_Test_Widget.setText(
            "Sinking Test (External Source/Sink PSU)"
        )
        self.QCheckBox_Sinking_Test_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_Sinking_Test_Widget.setVisible(False)
        self.voltage_accuracy_mode_group = QButtonGroup(self)
        self.voltage_accuracy_mode_group.setExclusive(True)
        for checkbox in (
            self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget,
            self.QCheckBox_Voltage_Accuracy_Current_Mode_Widget,
            self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget,
            self.QCheckBox_Sinking_Test_Widget,
        ):
            self.voltage_accuracy_mode_group.addButton(checkbox)

        self.QCheckBox_VoltageLoadRegulation_Widget = QCheckBox()
        self.QCheckBox_VoltageLoadRegulation_Widget.setText("Voltage Load Regulation")
        self.QCheckBox_VoltageLoadRegulation_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_TransientRecovery_Widget = QCheckBox()
        self.QCheckBox_TransientRecovery_Widget.setText("Transient Recovery")
        self.QCheckBox_TransientRecovery_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_OVP_Test_Widget = QCheckBox()
        self.QCheckBox_OVP_Test_Widget.setText("OVP Test")
        self.QCheckBox_OVP_Test_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_VoltageLineRegulation_Widget = QCheckBox()
        self.QCheckBox_VoltageLineRegulation_Widget.setText("Voltage Line Regulation")
        self.QCheckBox_VoltageLineRegulation_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_ProgrammingSpeed_Widget = QCheckBox()
        self.QCheckBox_ProgrammingSpeed_Widget.setText("Programming Response")
        self.QCheckBox_ProgrammingSpeed_Widget.setCheckState(Qt.Unchecked)

        self.QCheckBox_CurrentAccuracy_Widget = QCheckBox()
        self.QCheckBox_CurrentAccuracy_Widget.setText("Current Accuracy")
        self.QCheckBox_CurrentAccuracy_Widget.setCheckState(Qt.Unchecked) 

        #Child checkbox under Current Accuracy
        self.QCheckBox_Current_Accuracy_20A_Range_Widget = QCheckBox()
        self.QCheckBox_Current_Accuracy_20A_Range_Widget.setText("Current Range : 20A")
        self.QCheckBox_Current_Accuracy_20A_Range_Widget.setCheckState(Qt.Checked)

        self.QCheckBox_Current_Accuracy_2A_Range_Widget = QCheckBox()
        self.QCheckBox_Current_Accuracy_2A_Range_Widget.setText("Current Range : 2A")
        self.QCheckBox_Current_Accuracy_2A_Range_Widget.setCheckState(Qt.Unchecked)

        self.QCheckBox_Current_Accuracy_200mA_Range_Widget = QCheckBox()
        self.QCheckBox_Current_Accuracy_200mA_Range_Widget.setText("Current Range : 200mA")
        self.QCheckBox_Current_Accuracy_200mA_Range_Widget.setCheckState(Qt.Unchecked)

        self.QCheckBox_Current_Accuracy_20mA_Range_Widget = QCheckBox()
        self.QCheckBox_Current_Accuracy_20mA_Range_Widget.setText("Current Range : 20mA")
        self.QCheckBox_Current_Accuracy_20mA_Range_Widget.setCheckState(Qt.Unchecked)

        self.QCheckBox_Current_Accuracy_2mA_Range_Widget = QCheckBox()
        self.QCheckBox_Current_Accuracy_2mA_Range_Widget.setText("Current Range : 2mA")
        self.QCheckBox_Current_Accuracy_2mA_Range_Widget.setCheckState(Qt.Unchecked)
        
        self.QCheckBox_Current_Accuracy_200uA_Range_Widget = QCheckBox()
        self.QCheckBox_Current_Accuracy_200uA_Range_Widget.setText("Current Range : 200uA")
        self.QCheckBox_Current_Accuracy_200uA_Range_Widget.setCheckState(Qt.Unchecked)

        self.QCheckBox_CurrentLoadRegulation_Widget = QCheckBox()    
        self.QCheckBox_CurrentLoadRegulation_Widget.setText("Current Load Regulation")
        self.QCheckBox_CurrentLoadRegulation_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_PowerAccuracy_Widget = QCheckBox()
        self.QCheckBox_PowerAccuracy_Widget.setText("Power Accuracy")
        self.QCheckBox_PowerAccuracy_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_CurrentLineRegulation_Widget = QCheckBox()
        self.QCheckBox_CurrentLineRegulation_Widget.setText("Current Line Regulation")
        self.QCheckBox_CurrentLineRegulation_Widget.setCheckState(Qt.Unchecked)
        self.QCheckBox_OCP_Test_Widget = QCheckBox()
        self.QCheckBox_OCP_Test_Widget.setText("OCP Test / Activation")
        self.QCheckBox_OCP_Test_Widget.setCheckState(Qt.Unchecked)
        
        #Create Bundle test view
        self.setWindowTitle("Bundle Test Control Center")
        self.resize(1500, 900)
        self.image_window = None
        self.setWindowFlags(Qt.Window)
        font = QFont()
        font.setPointSize(12)   # Adjust size here
        self.setFont(font)

        # Abort button
        self.abort_button = QPushButton("Abort")
        self.abort_button.setObjectName("dangerAction")
        self.abort_button.clicked.connect(self.abort_test)
        self.abort_button.setVisible(False)
        self.abort_button.setEnabled(False)
        self.pause_button = QPushButton("Pause")
        self.pause_button.setObjectName("warningAction")
        self.pause_button.clicked.connect(self.toggle_pause_test)
        self.pause_button.setVisible(False)
        self.pause_button.setEnabled(False)
        self.show_plot_button = QPushButton("Graph Plotting")
        self.show_plot_button.setObjectName("secondaryAction")
        self.show_plot_button.clicked.connect(self.show_popup_plot)
        self.show_plot_button.setVisible(False)
        self.show_plot_button.setEnabled(False)

        # Progress bar NEEDS FIXING!
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("testProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setVisible(False)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("progressStatus")
        self.progress_label.setMinimumWidth(260)
        self.progress_label.setVisible(False)

        #Output Display
        self.OutputBox = QTextBrowser()
        self.OutputBox.setObjectName("executionConsole")
        self.OutputBox.append(f"{my_result.getvalue()}")
        self.OutputBox.append("")  # Empty line after each append

    def _create_configuration_widgets(self):
        connection_section = self._create_connection_configuration_widgets()
        sections = (
            connection_section,
            self._create_rating_widgets(),
            self._create_oscilloscope_widgets(),
            self._create_collection_widgets(connection_section.QLabel_Save_Path),
        )
        return SimpleNamespace(
            **{name: value for section in sections for name, value in vars(section).items()}
        )

    def _create_connection_configuration_widgets(self):
        #Description 1-7
        Desp0 = QLabel()
        Desp1 = QLabel()
        Desp2 = QLabel()
        Desp3 = QLabel()
        Desp4 = QLabel()
        Desp5 = QLabel()
        Desp6 = QLabel()
        Desp7 = QLabel()
        Desp8 = QLabel()
        Desp9 = QLabel()
        PerformTest = QLabel()
        OscilloscopeSetting = QLabel()

        Desp0.setFont(desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp5.setFont(desp_font)
        Desp6.setFont(desp_font)
        Desp7.setFont(desp_font)
        Desp8.setFont(desp_font)
        Desp9.setFont(desp_font)
        PerformTest.setFont(desp_font)
        OscilloscopeSetting.setFont(desp_font)

        Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Gain Error:")
        Desp4.setText("Power Sweep:")
        Desp5.setText("Voltage Sweep:")
        Desp6.setText("Current Sweep:")
        Desp7.setText("No. of Collection:")
        Desp8.setText("Rated Power [W]")
        Desp9.setText("Maximum Current")
        PerformTest.setText("Perform Test:")
        OscilloscopeSetting.setText("Oscilloscope Setting:")

        #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location/Output Wndow:")

        #Testing Selection
        QLabel_Testing_Selection = QLabel()
        QLabel_Testing_Selection.setFont(desp_font)
        QLabel_Testing_Selection.setText("Test:")

        # Connections section
        self.image_label = QLabel()
        self.image_label.setObjectName("setupIllustration")
        self.image_label.setMaximumSize(360, 210)
        self.image_label.setMinimumHeight(120)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        QLabel_Connection_Selection = QLabel()
        QLabel_PSU_VisaAddress = QLabel()
        QLabel_DMM_VisaAddressforVoltage = QLabel()
        self.QLabel_DMM_VisaAddressforCurrent = QLabel()
        self.QLabel_OSC_VisaAddress = QLabel()
        self.QLabel_DAQ_VisaAddress = QLabel()
        self.QLabel_External_Source_VisaAddress = QLabel()
        QLabel_ELoad_VisaAddress = QLabel()
        QLabel_DMM_Instrument = QLabel()
        QLabel_DUT = QLabel()
        QLabel_AC_Supply_Type = QLabel()

        QLabel_Connection_Selection.setText("Connection Selection:")
        QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        QLabel_DMM_VisaAddressforVoltage.setText("Visa Address (DMM):")
        self.QLabel_DMM_VisaAddressforCurrent.setText("Visa Address (DMM-Current Shunt):")
        self.QLabel_OSC_VisaAddress.setText("Visa Address (OSC):")
        self.QLabel_DAQ_VisaAddress.setText("Visa Address (DAQ973A):")
        self.QLabel_External_Source_VisaAddress.setText(
            "External Source/Sink PSU:"
        )
        QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DMM_Instrument.setText("Instrument Type (DMM):")
        QLabel_DUT.setText("DUT:")
        QLabel_AC_Supply_Type.setText("AC Supply:")

        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_DMM_VisaAddressforVoltage = QComboBox()
        self.QLineEdit_DMM_VisaAddressforCurrent = QComboBox()
        self.QLineEdit_OSC_VisaAddress = QComboBox()
        self.QLineEdit_DAQ_VisaAddress = QComboBox()
        self.QLineEdit_DAQ_VisaAddress.setEditable(True)
        self.QLineEdit_External_Source_VisaAddress = QComboBox()
        self.QLineEdit_External_Source_VisaAddress.setEditable(True)
        self.QComboBox_Relay_Control = QComboBox()
        self.QComboBox_Relay_Control.addItems(
            [
                "None",
                "Voltage Relay (Channel 3)",
                "Current Relay (Channel 2)",
                "Both Relays",
            ]
        )
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        self.QComboBox_DMM_Instrument = QComboBox()
        self.QComboBox_DUT = QComboBox()
        self.QComboBox_AC_Supply_Type = QComboBox()
        # General Setting
        QLabel_Voltage_Res = QLabel()
        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
        self.QLabel_Hornbill_Measurement_Command = QLabel()
        self.QLabel_SweepPoints = QLabel()
        QLabel_OVP_Level = QLabel()
        QLabel_OCP_Level = QLabel()
        QLabel_OCP_Activation_Time = QLabel()
        QLabel_SPOperationMode = QLabel()
        QLabel_Line_Reg_Range = QLabel()
        self.QLabel_External_Source_Positive_Current_Limit = QLabel(
            "Positive Current Limit (A):"
        )
        self.QLabel_External_Source_Negative_Current_Limit = QLabel(
            "Negative Current Limit (A):"
        )
        self.QLabel_Sink_Slew_Rate = QLabel("Sink Box Slew Rate:")
        self.QLabel_Sinking_Initial_Voltage = QLabel("Initial Voltage (V):")
        self.QLabel_Sinking_Final_Voltage = QLabel("Final Voltage (V):")
        self.QLabel_Sinking_Voltage_Step_Size = QLabel("Voltage Step Size (V):")
        #Programming Error
        QLabel_Programming_Error_Gain = QLabel()
        QLabel_Programming_Error_Offset = QLabel()
        QLabel_Readback_Error_Gain = QLabel()
        QLabel_Readback_Error_Offset = QLabel()
        QLabel_Load_Programming_Error_Gain = QLabel()
        QLabel_Load_Programming_Error_Offset = QLabel()
        self.QLabel_Power_Programming_Error_Gain = QLabel()
        self.QLabel_Power_Programming_Error_Offset = QLabel()
        self.QLabel_Power_Readback_Error_Gain = QLabel()
        self.QLabel_Power_Readback_Error_Offset = QLabel()
        QLabel_Programming_Response_Up_NoLoad= QLabel()
        QLabel_Programming_Response_Up_FullLoad= QLabel()
        QLabel_Programming_Response_Down_NoLoad= QLabel()
        QLabel_Programming_Response_Down_FullLoad= QLabel()
        QLabel_OVP_Error_Gain = QLabel()
        QLabel_OVP_Error_Offset = QLabel()

        QLabel_Voltage_Res.setText("Voltage Resolution (DMM):")
        QLabel_set_PSU_Channel.setText("Set PSU Channel:")
        QLabel_set_ELoad_Channel.setText("Set Eload Channel:")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        self.QLabel_Hornbill_Measurement_Command.setText(
            "Hornbill Readback Command:"
        )
        self.QLabel_SweepPoints.setText("Hornbill Sweep Points:")
        QLabel_OVP_Level.setText("OVP Level:")
        QLabel_OCP_Level.setText("OCP Level")
        QLabel_OCP_Activation_Time.setText("OCP Activation Time Error")
        QLabel_SPOperationMode.setText("DUT Operation Mode:")
        QLabel_Line_Reg_Range.setText("Line Regulation Test Range")

        QLabel_Programming_Error_Gain.setText("Programming Desired Specification (Gain):")
        QLabel_Programming_Error_Offset.setText("Programming Desired Specification (Offset):")
        QLabel_Readback_Error_Gain.setText("Readback Desired Specification (Gain):")
        QLabel_Readback_Error_Offset.setText("Readback Desired Specification (Offset):")
        QLabel_Load_Programming_Error_Gain.setText("Load_Regulation_Error_Gain:")
        QLabel_Load_Programming_Error_Offset.setText("Load_Regulation_Offset_Gain:")
        self.QLabel_Power_Programming_Error_Gain.setText("Power_Programming Desired Specification (Gain):")
        self.QLabel_Power_Programming_Error_Offset.setText("Power_Programming Desired Specification (Offset):")
        self.QLabel_Power_Readback_Error_Gain.setText("Power_Readback Desired Specification (Gain):")
        self.QLabel_Power_Readback_Error_Offset.setText("Power_Readback Desired Specification (Offset):")
        QLabel_Programming_Response_Up_NoLoad.setText("Programming Response Limit (Up-NoLoad)")
        QLabel_Programming_Response_Up_FullLoad.setText("Programming Response Limit (Up-FullLoad)")
        QLabel_Programming_Response_Down_NoLoad.setText("Programming Response Limit (Down-NoLoad)")
        QLabel_Programming_Response_Down_FullLoad.setText("Programming Response Limit (Down-FullLoad)")
        QLabel_OVP_Error_Gain.setText("OVP Error Gain:")
        QLabel_OVP_Error_Offset.setText("OVP Error Offset:")

        self.QComboBox_Voltage_Res = QComboBox()
        self.QComboBox_set_PSU_Channel = QComboBox()
        self.QComboBox_set_ELoad_Channel = QComboBox()
        self.QComboBox_set_Function = QComboBox()
        self.QComboBox_Voltage_Sense = QComboBox()
        self.QComboBox_Hornbill_Measurement_Command = QComboBox()
        self.QLineEdit_SweepPoints = QLineEdit()
        self.QLineEdit_External_Source_Positive_Current_Limit = QLineEdit()
        self.QLineEdit_External_Source_Negative_Current_Limit = QLineEdit()
        self.QLineEdit_Sink_Slew_Rate = QLineEdit()
        self.QLineEdit_Sinking_Initial_Voltage = QLineEdit()
        self.QLineEdit_Sinking_Final_Voltage = QLineEdit()
        self.QLineEdit_Sinking_Voltage_Step_Size = QLineEdit()

        self.QLineEdit_OVP_Level = QLineEdit()
        self.QLineEdit_OCP_Level = QLineEdit()
        self.QLineEdit_OCP_ActivationTime_Error = QLineEdit()
        self.QComboBox_SPOperationMode = QComboBox()
        self.QComboBox_Line_Reg_Range = QComboBox()

        self.QLineEdit_Programming_Error_Gain = QLineEdit()
        self.QLineEdit_Programming_Error_Offset = QLineEdit()
        self.QLineEdit_Readback_Error_Gain = QLineEdit()
        self.QLineEdit_Readback_Error_Offset = QLineEdit()
        self.QLineEdit_Load_Programming_Error_Gain = QLineEdit()
        self.QLineEdit_Load_Programming_Error_Offset = QLineEdit()
        self.QLineEdit_Power_Programming_Error_Gain = QLineEdit()
        self.QLineEdit_Power_Programming_Error_Offset = QLineEdit()
        self.QLineEdit_Power_Readback_Error_Gain = QLineEdit()
        self.QLineEdit_Power_Readback_Error_Offset = QLineEdit()
        self.QLineEdit_Programming_Response_Up_NoLoad  = QLineEdit()
        self.QLineEdit_Programming_Response_Up_FullLoad  = QLineEdit()
        self.QLineEdit_Programming_Response_Down_NoLoad = QLineEdit()
        self.QLineEdit_Programming_Response_Down_FullLoad = QLineEdit()
        self.QLineEdit_OVP_Error_Gain = QLineEdit()
        self.QLineEdit_OVP_Error_Offset = QLineEdit()

        self.QComboBox_DUT.addItems(["Others", "Excavator", "Dolphin", "SMU", "Hornbill"])
        self.QComboBox_AC_Supply_Type.addItems(["Plug", "AC Source"])
        self.QComboBox_DMM_Instrument.addItems(["Keysight", "Keithley"])
        self.QComboBox_Voltage_Res.addItems(["SLOW", "MEDIUM", "FAST"])
        self.QComboBox_set_Function.addItems(
            [
                "Current Priority",
                "Voltage Priority",
                "Resistance Priority",
            ]
        )
        self.QComboBox_set_Function.setEnabled(False)
        self.QComboBox_set_PSU_Channel.addItems(["1", "2", "3", "4","ALL"])
        self.QComboBox_set_PSU_Channel.setEnabled(True)
        self.QComboBox_set_ELoad_Channel.addItems(["1", "2"])
        self.QComboBox_set_ELoad_Channel.setEnabled(True)
        self.QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])
        self.QComboBox_Voltage_Sense.setEnabled(True)
        self.QComboBox_Hornbill_Measurement_Command.addItems(["DIAG", "SCPI"])
        self.QLabel_Hornbill_Measurement_Command.setVisible(False)
        self.QComboBox_Hornbill_Measurement_Command.setVisible(False)
        self.QLabel_SweepPoints.setVisible(False)
        self.QLineEdit_SweepPoints.setVisible(False)
        self.QComboBox_SPOperationMode.setEnabled(True)
        self.QComboBox_SPOperationMode.addItems(["Independent","Series","Parallel"])
        self.QComboBox_Line_Reg_Range.addItems(["100-115-230","100"])
        self.QComboBox_Line_Reg_Range.setEnabled(False)
        self.QLabel_DAQ_VisaAddress.setVisible(False)
        self.QLineEdit_DAQ_VisaAddress.setVisible(False)
        return SimpleNamespace(
            Desp0=Desp0,
            Desp1=Desp1,
            Desp2=Desp2,
            Desp3=Desp3,
            Desp4=Desp4,
            Desp5=Desp5,
            Desp6=Desp6,
            Desp7=Desp7,
            Desp8=Desp8,
            Desp9=Desp9,
            OscilloscopeSetting=OscilloscopeSetting,
            PerformTest=PerformTest,
            QLabel_AC_Supply_Type=QLabel_AC_Supply_Type,
            QLabel_Connection_Selection=QLabel_Connection_Selection,
            QLabel_DMM_Instrument=QLabel_DMM_Instrument,
            QLabel_DMM_VisaAddressforVoltage=QLabel_DMM_VisaAddressforVoltage,
            QLabel_DUT=QLabel_DUT,
            QLabel_ELoad_VisaAddress=QLabel_ELoad_VisaAddress,
            QLabel_Line_Reg_Range=QLabel_Line_Reg_Range,
            QLabel_Load_Programming_Error_Gain=QLabel_Load_Programming_Error_Gain,
            QLabel_Load_Programming_Error_Offset=QLabel_Load_Programming_Error_Offset,
            QLabel_OCP_Activation_Time=QLabel_OCP_Activation_Time,
            QLabel_OCP_Level=QLabel_OCP_Level,
            QLabel_OVP_Error_Gain=QLabel_OVP_Error_Gain,
            QLabel_OVP_Error_Offset=QLabel_OVP_Error_Offset,
            QLabel_OVP_Level=QLabel_OVP_Level,
            QLabel_PSU_VisaAddress=QLabel_PSU_VisaAddress,
            QLabel_Programming_Error_Gain=QLabel_Programming_Error_Gain,
            QLabel_Programming_Error_Offset=QLabel_Programming_Error_Offset,
            QLabel_Programming_Response_Down_FullLoad=QLabel_Programming_Response_Down_FullLoad,
            QLabel_Programming_Response_Down_NoLoad=QLabel_Programming_Response_Down_NoLoad,
            QLabel_Programming_Response_Up_FullLoad=QLabel_Programming_Response_Up_FullLoad,
            QLabel_Programming_Response_Up_NoLoad=QLabel_Programming_Response_Up_NoLoad,
            QLabel_Readback_Error_Gain=QLabel_Readback_Error_Gain,
            QLabel_Readback_Error_Offset=QLabel_Readback_Error_Offset,
            QLabel_SPOperationMode=QLabel_SPOperationMode,
            QLabel_Save_Path=QLabel_Save_Path,
            QLabel_Testing_Selection=QLabel_Testing_Selection,
            QLabel_Voltage_Res=QLabel_Voltage_Res,
            QLabel_Voltage_Sense=QLabel_Voltage_Sense,
            QLabel_set_ELoad_Channel=QLabel_set_ELoad_Channel,
            QLabel_set_Function=QLabel_set_Function,
            QLabel_set_PSU_Channel=QLabel_set_PSU_Channel,
        )

    def _create_rating_widgets(self):
        #Rated Power
        QLabel_power_rated = QLabel()
        QLabel_power_rated.setText("DUT Rated Power (W):")
        self.QLineEdit_power_rated = QLineEdit()

        #Power
        QLabel_Power = QLabel()
        QLabel_Power.setText("Power Test(W):")
        self.QLineEdit_Power = QLineEdit()
        
        self.QLabel_PowerINI = QLabel()
        self.QLabel_PowerINI.setText("Initial Power (W):")
        self.QLineEdit_PowerINI = QLineEdit()

        self.QLabel_power_step_size = QLabel()
        self.QLabel_power_step_size.setText("Step Size:")
        self.QLineEdit_power_step_size = QLineEdit()

        # Current Sweep
        self.QLabel_rshunt = QLabel()
        self.QLabel_rshunt.setText("Shunt Resistance Value (ohm):")
        self.QLineEdit_rshunt = QLineEdit()

        QLabel_minCurrent = QLabel()
        QLabel_maxCurrent = QLabel()
        QLabel_current_step_size = QLabel()
        QLabel_current_rated = QLabel()
        QLabel_minCurrent.setText("Initial Current (A):")
        QLabel_maxCurrent.setText("Final Current (A):")
        QLabel_current_step_size.setText("Step Size:")
        QLabel_current_rated.setText("DUT Rated Current:")

        self.QLineEdit_minCurrent = QLineEdit()
        self.QLineEdit_maxCurrent = QLineEdit()
        self.QLineEdit_current_stepsize = QLineEdit()
        self.QLineEdit_current_rated = QLineEdit()

        # Voltage Sweep
        QLabel_minVoltage = QLabel()
        QLabel_maxVoltage = QLabel()
        QLabel_voltage_step_size = QLabel()
        QLabel_voltage_rated = QLabel()
        QLabel_minVoltage.setText("Initial Voltage (V):")
        QLabel_maxVoltage.setText("Final Voltage (V):")
        QLabel_voltage_step_size.setText("Step Size:")
        QLabel_voltage_rated.setText("DUT Rated Voltage:")

        self.QLineEdit_minVoltage = QLineEdit()
        self.QLineEdit_maxVoltage = QLineEdit()
        self.QLineEdit_voltage_stepsize = QLineEdit()
        self.QLineEdit_voltage_rated = QLineEdit()
        self.QLineEdit_voltage_rated.setFixedSize(100, 40)
        return SimpleNamespace(
            QLabel_Power=QLabel_Power,
            QLabel_current_rated=QLabel_current_rated,
            QLabel_current_step_size=QLabel_current_step_size,
            QLabel_maxCurrent=QLabel_maxCurrent,
            QLabel_maxVoltage=QLabel_maxVoltage,
            QLabel_minCurrent=QLabel_minCurrent,
            QLabel_minVoltage=QLabel_minVoltage,
            QLabel_power_rated=QLabel_power_rated,
            QLabel_voltage_rated=QLabel_voltage_rated,
            QLabel_voltage_step_size=QLabel_voltage_step_size,
        )

    def _create_oscilloscope_widgets(self):
        # Oscilloscope Settings
        QLabel_OSC_Display_Channel = QLabel()
        QLabel_V_Settling_Band = QLabel()
        QLabel_T_Settling_Band = QLabel()
        QLabel_Probe_Setting = QLabel()
        QLabel_Acq_Type = QLabel()
        QLabel_OSC_Display_Channel.setText("Display Channel (OSC)")
        QLabel_V_Settling_Band.setText("Settling Band Voltage (V) / Error Band:")
        QLabel_T_Settling_Band.setText("Settling Band Time (s):")
        QLabel_Probe_Setting.setText("Probe Setting Ratio:")
        QLabel_Acq_Type.setText("Acquire Mode:")
        self.QLineEdit_OSC_Display_Channel = QLineEdit()
        self.QLineEdit_V_Settling_Band = QLineEdit()
        self.QLineEdit_T_Settling_Band = QLineEdit()
        self.QComboBox_Probe_Setting = QComboBox()
        self.QComboBox_Acq_Type = QComboBox()
        self.QComboBox_Probe_Setting.addItems(["0.01","X1", "X10", "X20", "X100"])
        self.QComboBox_Acq_Type.addItems(["NORMal", "PEAK", "AVERage", "HRESolution"])
        QLabel_Channel_CouplingMode = QLabel()
        QLabel_Trigger_Mode = QLabel()
        QLabel_Trigger_CouplingMode = QLabel()
        QLabel_Trigger_SweepMode = QLabel()
        QLabel_Trigger_SlopeMode = QLabel()
        QLabel_TimeScale = QLabel()
        QLabel_VerticalScale = QLabel()

        QLabel_Channel_CouplingMode.setText("Coupling Mode (Channel)")
        QLabel_Trigger_Mode.setText("Trigger Mode:")
        QLabel_Trigger_CouplingMode.setText("Coupling Mode (Trigger):")
        QLabel_Trigger_SweepMode.setText("Trigger Sweep Mode:")
        QLabel_Trigger_SlopeMode.setText("Trigger Slope Mode:")
        QLabel_TimeScale.setText("Time Scale:")
        QLabel_VerticalScale.setText("Vertical Scale:")

        self.QComboBox_Channel_CouplingMode = QComboBox()
        self.QComboBox_Trigger_Mode = QComboBox()
        self.QComboBox_Trigger_CouplingMode = QComboBox()
        self.QComboBox_Trigger_SweepMode = QComboBox()
        self.QComboBox_Trigger_SlopeMode = QComboBox()
        self.QLineEdit_TimeScale = QLineEdit()
        self.QLineEdit_VerticalScale = QLineEdit()

        self.QComboBox_Channel_CouplingMode.addItems(["AC", "DC"])
        self.QComboBox_Trigger_Mode.addItems(["EDGE", "IIC", "EBUR"])
        self.QComboBox_Trigger_CouplingMode.addItems(["AC", "DC"])
        self.QComboBox_Trigger_SweepMode.addItems(["NORMAL", "AUTO"])
        self.QComboBox_Trigger_SlopeMode.addItems(["ALT", "POS", "NEG", "EITH"])
        return SimpleNamespace(
            QLabel_Acq_Type=QLabel_Acq_Type,
            QLabel_Channel_CouplingMode=QLabel_Channel_CouplingMode,
            QLabel_OSC_Display_Channel=QLabel_OSC_Display_Channel,
            QLabel_Probe_Setting=QLabel_Probe_Setting,
            QLabel_T_Settling_Band=QLabel_T_Settling_Band,
            QLabel_TimeScale=QLabel_TimeScale,
            QLabel_Trigger_CouplingMode=QLabel_Trigger_CouplingMode,
            QLabel_Trigger_Mode=QLabel_Trigger_Mode,
            QLabel_Trigger_SlopeMode=QLabel_Trigger_SlopeMode,
            QLabel_Trigger_SweepMode=QLabel_Trigger_SweepMode,
            QLabel_V_Settling_Band=QLabel_V_Settling_Band,
            QLabel_VerticalScale=QLabel_VerticalScale,
        )

    def _create_collection_widgets(self, save_path_label):
        #Loop & Delay
        QLabel_noofloop = QLabel()
        QLabel_noofloop.setText("No. of Data Collection:")
        self.QComboBox_noofloop = QComboBox()
        self.QComboBox_noofloop.addItems(["1","2","3","4","5","6","7","8","9","10"])

        QLabel_updatedelay = QLabel()
        QLabel_updatedelay.setText("Delay Time (second) :(Default=50ms)")
        self.QComboBox_updatedelay = QComboBox()
        self.QComboBox_updatedelay.addItems(["0.0","0.8","1.0","2.0","3.0", "4.0"])

        #Create a horizontal layout for the "Save Path" and checkboxes
        save_path_layout = QVBoxLayout()
        save_path_layout.addWidget(save_path_label)  # QLabel for "Save Path"
        #save_path_layout.addWidget(QLineEdit_Save_Path)  # QLineEdit for the path
        save_path_layout.addWidget(self.QCheckBox_Report_Widget)  # Checkbox for "Generate Excel Report"
        save_path_layout.addWidget(self.QCheckBox_Image_Widget)  # Checkbox for "Show Graph"
        save_path_layout.addWidget(self.QCheckBox_Lock_Widget)  # Checkbox for "Show Graph"
        return SimpleNamespace(
            QLabel_noofloop=QLabel_noofloop,
            QLabel_updatedelay=QLabel_updatedelay,
            save_path_layout=save_path_layout,
        )

    def _create_test_selection_layout(self, ui):
        #+++++++++++++++++++++++++Layout Organization Part --(Organize Layout of GUI here)++++++++++++++++++++++++++++++++++++++++++++++++++++
        Voltage_Current_Selection_Layout = QVBoxLayout()
        Voltage_Current_Selection_Layout.addWidget(self.QPushButton_Voltage_Widget)
        Voltage_Current_Selection_Layout.addWidget(self.QPushButton_Current_Widget)
        
        self.Current_Test_group, self.CurrentAccuracy_Branch_Widget = (
            create_current_selection_widget(self, ui.QLabel_Testing_Selection)
        )
        voltage_heading = QLabel("Testing Selection")
        self.Voltage_Test_group, self.VoltageAccuracy_Branch_Widget = (
            create_voltage_selection_widget(self, voltage_heading)
        )
        return Voltage_Current_Selection_Layout

    def _create_connection_and_general_groups(self, ui):
        #Connections Layout
        self.Connection_group = QGroupBox("Instrument Connections")
        Connection_layout = QFormLayout(self.Connection_group)
        Checkbox_row = QHBoxLayout(self.Connection_group)
        Connection_layout.addRow(self.QPushButton_Widget4)
        Checkbox_row.addWidget(self.QCheckBox_USB_Widget)
        Checkbox_row.addWidget(self.QCheckBox_GPIB_Widget)
        Checkbox_row.addWidget(self.QCheckBox_IP_Widget)
        Checkbox_row.addWidget(self.QCheckBox_Hostname_Widget)
        Connection_layout.addRow(ui.QLabel_Connection_Selection, Checkbox_row)
        Connection_layout.addRow(ui.QLabel_DUT, self.QComboBox_DUT)
        Connection_layout.addRow(ui.QLabel_AC_Supply_Type, self.QComboBox_AC_Supply_Type)
        Connection_layout.addRow(ui.QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        Connection_layout.addRow(ui.QLabel_DMM_VisaAddressforVoltage, self.QLineEdit_DMM_VisaAddressforVoltage)
        Connection_layout.addRow(self.QLabel_DMM_VisaAddressforCurrent, self.QLineEdit_DMM_VisaAddressforCurrent)
        Connection_layout.addRow(ui.QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        Connection_layout.addRow(self.QLabel_OSC_VisaAddress, self.QLineEdit_OSC_VisaAddress)
        Connection_layout.addRow(ui.QLabel_DMM_Instrument, self.QComboBox_DMM_Instrument)

        self.Auxiliary_group = QGroupBox("Auxiliary Equipment")
        auxiliary_layout = QFormLayout(self.Auxiliary_group)
        auxiliary_layout.addRow("Relay Control:", self.QComboBox_Relay_Control)
        auxiliary_layout.addRow(self.QCheckBox_Temperature_Widget)
        auxiliary_layout.addRow(
            self.QLabel_DAQ_VisaAddress,
            self.QLineEdit_DAQ_VisaAddress,
        )
        auxiliary_layout.addRow(self.QCheckBox_Blynk_Widget)
        auxiliary_layout.addRow(self.Blynk_Status_Label)

        self.Sinking_Test_group = QGroupBox("Sinking Test Settings")
        sinking_layout = QFormLayout(self.Sinking_Test_group)
        sinking_layout.addRow(
            self.QLabel_External_Source_VisaAddress,
            self.QLineEdit_External_Source_VisaAddress,
        )
        sinking_layout.addRow(
            self.QLabel_External_Source_Positive_Current_Limit,
            self.QLineEdit_External_Source_Positive_Current_Limit,
        )
        sinking_layout.addRow(
            self.QLabel_External_Source_Negative_Current_Limit,
            self.QLineEdit_External_Source_Negative_Current_Limit,
        )
        sinking_layout.addRow(
            self.QLabel_Sink_Slew_Rate,
            self.QLineEdit_Sink_Slew_Rate,
        )
        sinking_layout.addRow(
            self.QLabel_Sinking_Initial_Voltage,
            self.QLineEdit_Sinking_Initial_Voltage,
        )
        sinking_layout.addRow(
            self.QLabel_Sinking_Final_Voltage,
            self.QLineEdit_Sinking_Final_Voltage,
        )
        sinking_layout.addRow(
            self.QLabel_Sinking_Voltage_Step_Size,
            self.QLineEdit_Sinking_Voltage_Step_Size,
        )
        self.Sinking_Test_group.setVisible(False)

        #General Setting Layout
        self.General_group = QGroupBox("General Test Settings")
        General_Setting_layout = QFormLayout(self.General_group)
        General_Setting_layout.addRow(ui.QLabel_set_PSU_Channel, self.QComboBox_set_PSU_Channel)
        General_Setting_layout.addRow(ui.QLabel_set_ELoad_Channel, self.QComboBox_set_ELoad_Channel)
        General_Setting_layout.addRow(ui.QLabel_set_Function, self.QComboBox_set_Function)
        General_Setting_layout.addRow(self.QLabel_rshunt, self.QLineEdit_rshunt)
        General_Setting_layout.addRow(ui.QLabel_Voltage_Sense, self.QComboBox_Voltage_Sense)
        General_Setting_layout.addRow(
            self.QLabel_Hornbill_Measurement_Command,
            self.QComboBox_Hornbill_Measurement_Command,
        )
        General_Setting_layout.addRow(
            self.QLabel_SweepPoints,
            self.QLineEdit_SweepPoints,
        )
        General_Setting_layout.addRow(ui.QLabel_OVP_Level, self.QLineEdit_OVP_Level)
        General_Setting_layout.addRow(ui.QLabel_OCP_Level, self.QLineEdit_OCP_Level)
        General_Setting_layout.addRow(ui.QLabel_OCP_Activation_Time, self.QLineEdit_OCP_ActivationTime_Error)
        General_Setting_layout.addRow(ui.QLabel_SPOperationMode, self.QComboBox_SPOperationMode)
        General_Setting_layout.addRow(ui.QLabel_Line_Reg_Range, self.QComboBox_Line_Reg_Range)

    def _create_rating_and_error_groups(self, ui):
        #Test Ratings (Current/Voltage/Power)
        self.power_setting_widget = QWidget()
        power_init_step_layout = QFormLayout(self.power_setting_widget)
        power_init_step_layout
        power_init_step_layout.addRow(self.QLabel_PowerINI, self.QLineEdit_PowerINI)
        power_init_step_layout.addRow(self.QLabel_power_step_size, self.QLineEdit_power_step_size)
        power_group = QGroupBox()
        power_sweep_layout = QFormLayout(power_group)
        power_sweep_layout.addRow(ui.Desp4)
        power_sweep_layout.addRow(ui.QLabel_power_rated, self.QLineEdit_power_rated)
        power_sweep_layout.addRow(ui.QLabel_Power, self.QLineEdit_Power)
        power_sweep_layout.addRow("",self.power_setting_widget)
        voltage_group = QGroupBox()
        voltage_inifin_layout = QFormLayout(voltage_group)
        voltage_inifin_layout.addRow(ui.Desp5)
        voltage_inifin_layout.addRow(ui.QLabel_voltage_rated, self.QLineEdit_voltage_rated)
        voltage_inifin_layout.addRow(ui.QLabel_minVoltage, self.QLineEdit_minVoltage)
        voltage_inifin_layout.addRow(ui.QLabel_maxVoltage, self.QLineEdit_maxVoltage)
        voltage_inifin_layout.addRow(ui.QLabel_voltage_step_size, self.QLineEdit_voltage_stepsize)
        current_group = QGroupBox()
        current_inifin_layout = QFormLayout(current_group)
        current_inifin_layout.addRow(ui.Desp6)
        current_inifin_layout.addRow(ui.QLabel_current_rated, self.QLineEdit_current_rated)
        current_inifin_layout.addRow(ui.QLabel_minCurrent, self.QLineEdit_minCurrent)
        current_inifin_layout.addRow(ui.QLabel_maxCurrent, self.QLineEdit_maxCurrent)
        current_inifin_layout.addRow(ui.QLabel_current_step_size, self.QLineEdit_current_stepsize)
        self.Ratings_Widget = QGroupBox("Ratings and Sweep Limits")
        Ratings_Layout = QHBoxLayout(self.Ratings_Widget)
        Ratings_Layout.addWidget(power_group)
        Ratings_Layout.addWidget(voltage_group)
        Ratings_Layout.addWidget(current_group)

        #Gain Error Settings
        self.programming_error_widget = QGroupBox(
            "Voltage Programming and Readback Limits"
        )
        programming_error_layout = QFormLayout(self.programming_error_widget)
        programming_error_layout.addRow(ui.QLabel_Programming_Error_Gain, self.QLineEdit_Programming_Error_Gain)
        programming_error_layout.addRow(ui.QLabel_Programming_Error_Offset, self.QLineEdit_Programming_Error_Offset)
        programming_error_layout.addRow(ui.QLabel_Readback_Error_Gain, self.QLineEdit_Readback_Error_Gain)
        programming_error_layout.addRow(ui.QLabel_Readback_Error_Offset, self.QLineEdit_Readback_Error_Offset)

        self.load_error_widget = QGroupBox("Load Programming Limits")
        load_error_layout = QFormLayout(self.load_error_widget)
        load_error_layout.addRow(ui.QLabel_Load_Programming_Error_Gain, self.QLineEdit_Load_Programming_Error_Gain)
        load_error_layout.addRow(ui.QLabel_Load_Programming_Error_Offset, self.QLineEdit_Load_Programming_Error_Offset)

        self.power_programming_error_widget = QGroupBox(
            "Power Programming and Readback Limits"
        )
        power_programming_error_layout = QFormLayout(self.power_programming_error_widget)
        power_programming_error_layout.addRow(self.QLabel_Power_Programming_Error_Gain, self.QLineEdit_Power_Programming_Error_Gain)
        power_programming_error_layout.addRow(self.QLabel_Power_Programming_Error_Offset, self.QLineEdit_Power_Programming_Error_Offset)
        power_programming_error_layout.addRow(self.QLabel_Power_Readback_Error_Gain, self.QLineEdit_Power_Readback_Error_Gain)
        power_programming_error_layout.addRow(self.QLabel_Power_Readback_Error_Offset, self.QLineEdit_Power_Readback_Error_Offset)

        self.Programming_Response_widget = QGroupBox("Programming Response Limits")
        programming_response_error_layout = QFormLayout(self.Programming_Response_widget)
        programming_response_error_layout.addRow( ui.QLabel_Programming_Response_Up_NoLoad, self.QLineEdit_Programming_Response_Up_NoLoad)
        programming_response_error_layout.addRow( ui.QLabel_Programming_Response_Up_FullLoad, self.QLineEdit_Programming_Response_Up_FullLoad)
        programming_response_error_layout.addRow(ui.QLabel_Programming_Response_Down_NoLoad, self.QLineEdit_Programming_Response_Down_NoLoad)
        programming_response_error_layout.addRow( ui.QLabel_Programming_Response_Down_FullLoad, self.QLineEdit_Programming_Response_Down_FullLoad)

        self.OVP_error_widget = QGroupBox("OVP Accuracy Limits")
        OVP_error_layout = QFormLayout(self.OVP_error_widget)
        OVP_error_layout.addRow(ui.QLabel_OVP_Error_Gain, self.QLineEdit_OVP_Error_Gain)
        OVP_error_layout.addRow(ui.QLabel_OVP_Error_Offset, self.QLineEdit_OVP_Error_Offset)

    def _create_scope_and_collection_groups(self, ui):
        #Oscilloscope Settings
        self.oscilloscope_settings_widget = QGroupBox("Oscilloscope Settings")
        self.oscilloscope_form = QFormLayout(self.oscilloscope_settings_widget)
        self.oscilloscope_form.addRow(ui.OscilloscopeSetting)
        self.oscilloscope_form.addRow(ui.QLabel_OSC_Display_Channel, self.QLineEdit_OSC_Display_Channel)
        self.oscilloscope_form.addRow(ui.QLabel_V_Settling_Band, self.QLineEdit_V_Settling_Band)
        self.oscilloscope_form.addRow(ui.QLabel_T_Settling_Band, self.QLineEdit_T_Settling_Band)
        self.oscilloscope_form.addRow(ui.QLabel_Probe_Setting, self.QComboBox_Probe_Setting)
        self.oscilloscope_form.addRow(ui.QLabel_Acq_Type, self.QComboBox_Acq_Type)
        self.oscilloscope_form.addRow(ui.QLabel_Channel_CouplingMode, self.QComboBox_Channel_CouplingMode)
        self.oscilloscope_form.addRow(ui.QLabel_Trigger_CouplingMode, self.QComboBox_Trigger_CouplingMode)
        self.oscilloscope_form.addRow(ui.QLabel_Trigger_Mode, self.QComboBox_Trigger_Mode)
        self.oscilloscope_form.addRow(ui.QLabel_Trigger_SweepMode, self.QComboBox_Trigger_SweepMode)
        self.oscilloscope_form.addRow(ui.QLabel_Trigger_SlopeMode, self.QComboBox_Trigger_SlopeMode)
        self.oscilloscope_form.addRow(ui.QLabel_TimeScale, self.QLineEdit_TimeScale)
        self.oscilloscope_form.addRow(ui.QLabel_VerticalScale, self.QLineEdit_VerticalScale)
        self.oscilloscope_form.addRow(self.QCheckBox_SpecialCase_Widget)
        self.oscilloscope_form.addRow(self.QCheckBox_NormalCase_Widget)


        """#Transient Recovery Test conditions
        self.performtest_widget = QGroupBox()
        self.performtest_layout = QFormLayout(self.performtest_widget)
        self.performtest_layout.addRow(self.QCheckBox_SpecialCase_Widget)
        self.performtest_layout.addRow(self.QCheckBox_NormalCase_Widget)
"""
        #Collection and Delay
        self.collection_group = QGroupBox("Collection and Timing")
        self.collection_group_layout = QFormLayout(self.collection_group)
        self.collection_group_layout.addRow(ui.QLabel_noofloop, self.QComboBox_noofloop)
        self.collection_group_layout.addRow(ui.QLabel_updatedelay, self.QComboBox_updatedelay)

    def _create_dmm_settings_group(self):
        self.DMM_Settings_group = QGroupBox("DMM Measurement Settings")
        settings_layout = QVBoxLayout(self.DMM_Settings_group)

        model_layout = QFormLayout()
        self.QComboBox_DMM_Model = QComboBox()
        self.QComboBox_DMM_Model.addItem("344xxA / 34470A", "344xxA")
        self.QComboBox_DMM_Model.addItem("3458A", "3458A")
        model_layout.addRow("DMM Model:", self.QComboBox_DMM_Model)
        settings_layout.addLayout(model_layout)

        self.DMM_344XXA_Settings_group = QGroupBox("344xxA / 34470A Settings")
        settings_344xxa = QFormLayout(self.DMM_344XXA_Settings_group)
        self.QComboBox_344XXA_Range = QComboBox()
        self.QComboBox_344XXA_Range.addItems(
            ["Auto", "100mV", "1V", "10V", "100V", "1kV"]
        )
        self.QComboBox_344XXA_NPLC = QComboBox()
        self.QComboBox_344XXA_NPLC.addItems(
            ["0.02", "0.06", "0.2", "1", "10", "100"]
        )
        self.QComboBox_344XXA_AutoZero = QComboBox()
        self.QComboBox_344XXA_AutoZero.addItems(["ON", "OFF"])
        self.QComboBox_344XXA_InputZ = QComboBox()
        self.QComboBox_344XXA_InputZ.addItem("Auto (>10 GOhm)", "ON")
        self.QComboBox_344XXA_InputZ.addItem("10 MOhm", "OFF")
        settings_344xxa.addRow("DC Voltage Range:", self.QComboBox_344XXA_Range)
        settings_344xxa.addRow("Integration (NPLC):", self.QComboBox_344XXA_NPLC)
        settings_344xxa.addRow("Auto Zero:", self.QComboBox_344XXA_AutoZero)
        settings_344xxa.addRow("Input Impedance:", self.QComboBox_344XXA_InputZ)
        settings_layout.addWidget(self.DMM_344XXA_Settings_group)

        self.DMM_3458A_Settings_group = QGroupBox("3458A Settings")
        settings_3458a = QFormLayout(self.DMM_3458A_Settings_group)
        self.QComboBox_3458A_Range = QComboBox()
        for label, value in (
            ("AUTO", "Auto"),
            ("0.1 V", "0.1"),
            ("1 V", "1"),
            ("10 V", "10"),
            ("100 V", "100"),
            ("1000 V", "1000"),
        ):
            self.QComboBox_3458A_Range.addItem(label, value)
        self.QComboBox_3458A_NPLC = QComboBox()
        self.QComboBox_3458A_NPLC.addItems(
            ["0.02", "0.06", "0.2", "1", "10", "100"]
        )
        self.QComboBox_3458A_AutoZero = QComboBox()
        self.QComboBox_3458A_AutoZero.addItems(["ON", "OFF"])
        settings_3458a.addRow("DC Voltage Range:", self.QComboBox_3458A_Range)
        settings_3458a.addRow("Integration (NPLC):", self.QComboBox_3458A_NPLC)
        settings_3458a.addRow("Auto Zero:", self.QComboBox_3458A_AutoZero)
        settings_layout.addWidget(self.DMM_3458A_Settings_group)

        self._load_dmm_settings_from_parameters()
        self.QComboBox_DMM_Model.currentIndexChanged.connect(
            self._dmm_model_changed
        )
        for widget in (
            self.QComboBox_344XXA_Range,
            self.QComboBox_344XXA_NPLC,
            self.QComboBox_344XXA_AutoZero,
            self.QComboBox_344XXA_InputZ,
            self.QComboBox_3458A_Range,
            self.QComboBox_3458A_NPLC,
            self.QComboBox_3458A_AutoZero,
        ):
            widget.currentIndexChanged.connect(self._apply_selected_dmm_settings)
        self._update_dmm_settings_visibility()

    @staticmethod
    def _set_combo_value(combo, value, use_item_data=False):
        normalized = str(value or "").strip()
        if use_item_data:
            index = combo.findData(normalized)
        else:
            index = combo.findText(normalized, Qt.MatchFixedString)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _load_dmm_settings_from_parameters(self):
        model = str(getattr(self.params, "DMM_Model", "3458A") or "3458A")
        model_index = self.QComboBox_DMM_Model.findData(model)
        if model_index < 0:
            model_index = self.QComboBox_DMM_Model.findData("3458A")
        self.QComboBox_DMM_Model.setCurrentIndex(model_index)

        voltage_range = getattr(self.params, "Range", "Auto") or "Auto"
        aperture = getattr(self.params, "Aperture", "10") or "10"
        auto_zero = getattr(self.params, "AutoZero", "ON") or "ON"
        input_impedance = getattr(self.params, "inputZ", "ON") or "ON"
        self._set_combo_value(self.QComboBox_344XXA_Range, voltage_range)
        self._set_combo_value(self.QComboBox_344XXA_NPLC, aperture)
        self._set_combo_value(self.QComboBox_344XXA_AutoZero, auto_zero)
        self._set_combo_value(
            self.QComboBox_344XXA_InputZ,
            {
                "AUTO": "ON",
                "10M": "OFF",
            }.get(str(input_impedance).upper(), str(input_impedance).upper()),
            use_item_data=True,
        )
        self._set_combo_value(
            self.QComboBox_3458A_Range,
            "Auto" if str(voltage_range).upper() == "AUTO" else voltage_range,
            use_item_data=True,
        )
        self._set_combo_value(self.QComboBox_3458A_NPLC, aperture)
        self._set_combo_value(self.QComboBox_3458A_AutoZero, auto_zero)
        self._update_dmm_settings_visibility()
        self._apply_selected_dmm_settings()

    def _dmm_model_changed(self, _index):
        self._update_dmm_settings_visibility()
        self._apply_selected_dmm_settings()

    def _update_dmm_settings_visibility(self):
        model = self.QComboBox_DMM_Model.currentData()
        self.DMM_344XXA_Settings_group.setVisible(model == "344xxA")
        self.DMM_3458A_Settings_group.setVisible(model == "3458A")

    def _apply_selected_dmm_settings(self, _index=None):
        model = self.QComboBox_DMM_Model.currentData()
        self.params.DMM_Model = model
        if model == "344xxA":
            self.params.Range = self.QComboBox_344XXA_Range.currentText()
            self.params.Aperture = self.QComboBox_344XXA_NPLC.currentText()
            self.params.AutoZero = self.QComboBox_344XXA_AutoZero.currentText()
            self.params.inputZ = self.QComboBox_344XXA_InputZ.currentData()
            return
        self.params.Range = self.QComboBox_3458A_Range.currentData()
        self.params.Aperture = self.QComboBox_3458A_NPLC.currentText()
        self.params.AutoZero = self.QComboBox_3458A_AutoZero.currentText()
        self.params.inputZ = "OFF"

    def _create_execution_panel(self, ui):
        #Execute Layout + Outputbox in Right Container
        Right_container = QVBoxLayout()
        exec_layout_box = QHBoxLayout()
        exec_layout = QFormLayout()

        #exec_layout.addRow(ui.Desp0)
        exec_layout.addWidget(self.OutputBox)
        exec_layout.addRow(self.QPushButton_Widget0)

        exec_layout.addRow(self.QPushButton_Widget3)
        exec_layout.addRow(self.QPushButton_Widget1)  
        exec_layout.addRow(self.queue_test_button)
        exec_layout.addRow(self.abort_button) 
        exec_layout.addRow(self.pause_button)
        exec_layout.addRow(self.show_plot_button)

        exec_layout_box.addLayout(exec_layout)
 
        Right_container.addLayout(ui.save_path_layout)         #Need changes
        Right_container.addLayout(exec_layout_box)
        Right_container.addWidget(self.queue_widget)
        return Right_container

    def _create_settings_panel(self, ui, test_selection_layout):
        #Setting Form Layout with Left Container
        top_widget = QWidget()
        top_layout_left = QVBoxLayout()  # Using QVBoxLayout for stacking the left items vertically
        top_layout_left.addLayout(test_selection_layout)
        top_layout_left.addWidget(self.image_label)
        top_layout_left.setAlignment(self.image_label, Qt.AlignHCenter)

        top_layout_right = QVBoxLayout()  # Using QVBoxLayout for stacking the right items vertically
        top_layout_right.addWidget(self.Voltage_Test_group )
        top_layout_right.addWidget(self.Current_Test_group )

        Left_container = QVBoxLayout()
        
        #Configuration Layout Setting (Put every groupbox inside left main layout)
        setting_widget = QWidget()
        setting_layout = QFormLayout(setting_widget)
        setting_layout.addRow(ui.Desp1)
        setting_layout.addRow(self.Connection_group)
        setting_layout.addRow(self.DMM_Settings_group)
        setting_layout.addRow(self.Auxiliary_group)
        setting_layout.addRow(self.Sinking_Test_group)
        setting_layout.addRow(ui.Desp2)
        setting_layout.addRow(self.General_group)
        setting_layout.addRow(ui.Desp3)
        setting_layout.addRow(self.programming_error_widget)
        setting_layout.addRow(self.load_error_widget)
        setting_layout.addRow(self.Programming_Response_widget)
        setting_layout.addRow(self.power_programming_error_widget)
        setting_layout.addRow(self.OVP_error_widget)
        setting_layout.addRow(self.Ratings_Widget)
        setting_layout.addRow(self.oscilloscope_settings_widget)
        #setting_layout.addRow(self.performtest_widget)
        setting_layout.addRow(ui.Desp7)
        setting_layout.addRow(self.collection_group)

        top_combined = QHBoxLayout()
        top_combined.addLayout(top_layout_left)
        top_combined.addLayout(top_layout_right)
        top_widget.setLayout(top_combined)
        top_combined.setStretchFactor(top_layout_left, 2) 
        top_combined.setStretchFactor(top_layout_right, 1) 

        scroll_area = QScrollArea()
        scroll_area.setObjectName("settingsScroll")
        scroll_area.setWidget(setting_widget)  # Set the widget inside scroll area
        scroll_area.setWidgetResizable(True)  # Allow resizing

        Left_container.addWidget(top_widget, stretch =1)
        Left_container.addWidget(scroll_area, stretch =3)
        return Left_container

    def _install_main_layout(self, left_container, right_container):
        setup_tab = QWidget()
        setup_layout = QVBoxLayout(setup_tab)
        setup_layout.setContentsMargins(14, 14, 14, 14)
        setup_layout.setSpacing(12)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar, stretch=1)
        setup_layout.addLayout(progress_layout)

        settings_title = QLabel("Test Configuration")
        settings_title.setObjectName("panelTitle")
        left_container.insertWidget(0, settings_title)
        settings_panel = QFrame()
        settings_panel.setObjectName("workspacePanel")
        settings_panel.setLayout(left_container)

        execution_title = QLabel("Execution Console")
        execution_title.setObjectName("panelTitle")
        right_container.insertWidget(0, execution_title)
        execution_panel = QFrame()
        execution_panel.setObjectName("workspacePanel")
        execution_panel.setLayout(right_container)

        workspace_splitter = QSplitter(Qt.Horizontal)
        workspace_splitter.setObjectName("workspaceSplitter")
        workspace_splitter.addWidget(settings_panel)
        workspace_splitter.addWidget(execution_panel)
        workspace_splitter.setStretchFactor(0, 2)
        workspace_splitter.setStretchFactor(1, 1)
        workspace_splitter.setSizes((980, 480))
        setup_layout.addWidget(workspace_splitter, stretch=1)

        self.dialog_tabs = QTabWidget()
        self.dialog_tabs.setObjectName("bundleTabs")
        for widget, title in (
            (setup_tab, "Test Setup"),
            (self.plot_window, "Graph Plotting"),
            (self.temperature_plot_widget, "Temperature Plotting"),
            (self.webcam_widget, "Webcam"),
            (self.analysis_widget, "Data Analysis"),
        ):
            tab_index = self.dialog_tabs.addTab(widget, title)
            self.dialog_tabs.setTabToolTip(tab_index, title)
        self.dialog_tabs.setDocumentMode(True)
        self.dialog_tabs.setElideMode(Qt.ElideNone)
        self.dialog_tabs.setUsesScrollButtons(True)
        self.dialog_tabs.tabBar().setExpanding(False)

        header_title = QLabel("Bundle Test Control Center")
        header_title.setObjectName("bundleTitle")
        header_subtitle = QLabel(
            "Configure instruments, select measurements, queue runs, and "
            "monitor test execution from a single workspace."
        )
        header_subtitle.setObjectName("bundleSubtitle")
        header_subtitle.setWordWrap(True)
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(2)
        header_text_layout.addWidget(header_title)
        header_text_layout.addWidget(header_subtitle)
        mode_badge = QLabel("SIMULATION" if is_simulation_mode() else "HARDWARE")
        mode_badge.setObjectName(
            "simulationBadge" if is_simulation_mode() else "hardwareBadge"
        )
        mode_badge.setAlignment(Qt.AlignCenter)
        header_layout = QHBoxLayout()
        header_layout.addLayout(header_text_layout, stretch=1)
        header_layout.addWidget(mode_badge)
        header_card = QFrame()
        header_card.setObjectName("bundleHeader")
        header_card.setLayout(header_layout)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)
        main_layout.addWidget(header_card)
        main_layout.addWidget(self.dialog_tabs)

    def _apply_bundle_theme(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #eef3f9;
                color: #1f2d3d;
            }
            QFrame#bundleHeader {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #17365d, stop:1 #2563a5);
                border-radius: 13px;
                padding: 12px 18px;
            }
            QLabel#bundleTitle {
                color: white;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#bundleSubtitle { color: #dbeafe; font-size: 13px; }
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
            QTabWidget#bundleTabs::pane {
                background: white;
                border: 1px solid #d4deea;
                border-radius: 10px;
                top: -1px;
            }
            QTabWidget#bundleTabs QTabBar::tab {
                background: #dfe7f1;
                color: #4a5d73;
                border: none;
                min-width: 155px;
                padding: 10px 14px;
                margin-right: 3px;
                font-size: 12px;
                font-weight: 600;
            }
            QTabWidget#bundleTabs QTabBar::tab:selected {
                background: #2563eb;
                color: white;
            }
            QTabWidget#bundleTabs QTabBar::tab:hover:!selected {
                background: #cbd8e7;
                color: #17365d;
            }
            QFrame#workspacePanel {
                background: #f8fafc;
                border: 1px solid #d5dfeb;
                border-radius: 10px;
            }
            QLabel#panelTitle {
                color: #17365d;
                font-size: 17px;
                font-weight: 700;
                padding: 5px 2px;
            }
            QGroupBox {
                background: white;
                border: 1px solid #d6e0eb;
                border-radius: 8px;
                margin-top: 12px;
                padding: 10px 8px 8px 8px;
                font-weight: 600;
                color: #334e68;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #17365d;
                background: white;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: white;
                border: 1px solid #b9c7d8;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 22px;
                selection-background-color: #2563eb;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
            QDoubleSpinBox:focus { border: 2px solid #3b82f6; }
            QCheckBox { spacing: 7px; color: #34495e; }
            QCheckBox::indicator { width: 17px; height: 17px; }
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                border: none;
                border-radius: 7px;
                padding: 8px 14px;
                font-weight: 700;
            }
            QPushButton:hover { background: #cbd5e1; }
            QPushButton#primaryAction { background: #2563eb; color: white; }
            QPushButton#primaryAction:hover { background: #1d4ed8; }
            QPushButton#discoveryAction { background: #0f766e; color: white; }
            QPushButton#discoveryAction:hover { background: #0d5f59; }
            QPushButton#dangerAction { background: #dc2626; color: white; }
            QPushButton#warningAction { background: #d97706; color: white; }
            QPushButton#modeSelector:checked { background: #2563eb; color: white; }
            QPushButton:disabled { background: #dbe3ed; color: #8795a8; }
            QTextBrowser#executionConsole {
                background: #0f172a;
                color: #cbd5e1;
                border: 1px solid #26364d;
                border-radius: 8px;
                padding: 8px;
                font-family: Consolas;
                font-size: 11px;
            }
            QProgressBar#testProgress {
                background: #dce5f0;
                border: none;
                border-radius: 6px;
                min-height: 14px;
                text-align: center;
                color: #17365d;
                font-weight: 700;
            }
            QProgressBar#testProgress::chunk {
                background: #3b82f6;
                border-radius: 6px;
            }
            QLabel#progressStatus { color: #334e68; font-weight: 600; }
            QLabel#setupIllustration {
                background: white;
                border: 1px solid #d6e0eb;
                border-radius: 8px;
                padding: 6px;
            }
            QScrollArea#settingsScroll {
                background: transparent;
                border: none;
            }
            QSplitter#workspaceSplitter::handle {
                background: #cbd5e1;
                width: 6px;
                margin: 6px 2px;
                border-radius: 3px;
            }
            """
        )


    def _connect_signals(self):
        connect_all_test_signals(self)
    
    def toggle_current_accuracy_branch(self):
        self.CurrentAccuracy_Branch_Widget.setVisible(
        self.QCheckBox_CurrentAccuracy_Widget.isChecked()
        )
    
    def toggle_voltage_accuracy_branch(self):
        self.VoltageAccuracy_Branch_Widget.setVisible(
        self.QCheckBox_VoltageAccuracy_Widget.isChecked()
        )
        if not self.QCheckBox_VoltageAccuracy_Widget.isChecked():
            self.QCheckBox_Sinking_Test_Widget.setChecked(False)

    def voltage_accuracy_mode_changed(self):
        self.InteractiveAction()

    def sinking_test_changed(self):
        if self.QCheckBox_Sinking_Test_Widget.isChecked():
            self.QCheckBox_VoltageAccuracy_Widget.setChecked(True)
            for checkbox in (
                self.QCheckBox_VoltageLoadRegulation_Widget,
                self.QCheckBox_TransientRecovery_Widget,
                self.QCheckBox_OVP_Test_Widget,
                self.QCheckBox_VoltageLineRegulation_Widget,
                self.QCheckBox_ProgrammingSpeed_Widget,
                self.QCheckBox_CurrentAccuracy_Widget,
                self.QCheckBox_CurrentLoadRegulation_Widget,
                self.QCheckBox_PowerAccuracy_Widget,
                self.QCheckBox_CurrentLineRegulation_Widget,
                self.QCheckBox_OCP_Test_Widget,
            ):
                checkbox.setChecked(False)
        self.InteractiveAction()

    def _connect_worker(self, worker):
        self.worker = worker
        worker.progress.connect(self.update_output)
        worker.progress_value.connect(self.update_progress_bar)
        worker.finished.connect(self.test_finished)
        worker.aborted.connect(self.test_aborted)
        worker.error.connect(self.handle_test_error)
        if hasattr(worker, "failed"):
            worker.failed.connect(self._failed_test_finished)
        worker.warning.connect(self.handle_test_warning)
        worker.new_data.connect(self.update_plot)
        worker.temperature_data.connect(self._handle_temperature_sample)
        worker.progress.connect(self.update_status)
        worker.state_changed.connect(self.set_test_state)
        if hasattr(worker, "loop_started"):
            worker.loop_started.connect(self._set_measurement_loop)

    def _set_measurement_loop(self, loop_index):
        if not self.active_run_context:
            return
        channel = self.active_run_context.configuration.get("PSU_Channel")
        self.active_run_context.set_measurement_context(loop_index, channel)

    def _queue_setup_failed(self, request, exception, traceback_text):
        self.set_test_state(TestState.FAILED)
        self.write_diagnostic(
            "queue_setup_failed",
            level="ERROR",
            exception=exception,
            traceback_text=traceback_text,
            run_id=request.run_id,
        )
        show_error_dialog(self, exception, traceback_text)
        self.cleanup_test(reason="queue-setup-failed")

    def _prepare_queued_run(self, request):
        self._cleanup_done = False
        self.was_aborted = False
        self.last_Iset = None
        self.fail_prompt_active = False
        self.continue_on_boundary_failure = False
        self.realtime_plot_series = RealtimePlotSeries()
        total_points = expected_measurement_points(
            request.configuration,
            request.checkbox_states,
        )
        initial_seconds_per_point = 1.0 + max(
            0.0,
            float(request.configuration.get("updatedelay") or 0),
        )
        self.progress_tracker = MeasurementProgressTracker(
            total_points,
            initial_seconds_per_point,
        )
        self._refresh_progress_display()
        self.checkbox_states = dict(request.checkbox_states)
        self.active_params = request.parameters
        self.active_run_context = self.prepare_run_storage(
            request.configuration,
            request.parameters,
            request.run_id,
        )
        measurement_name = (
            "Current"
            if self.checkbox_states.get("CurrentAccuracy")
            else "Voltage"
        )
        self.plot_window.reset(measurement_name)
        self.temperature_plot_widget.reset(
            enabled=self.checkbox_states.get("Temperature", False)
        )
        self.blynk_active = bool(self.checkbox_states.get("Blynk", False))
        if self.blynk_active:
            self.blynk_active = self.blynk_publisher.start()
            if not self.blynk_active:
                self.OutputBox.append(
                    "Blynk monitoring disabled: set BLYNK_AUTH_TOKEN "
                    "before starting the application."
                )
            else:
                self._publish_blynk_run_metadata(request.configuration)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.abort_button.setVisible(True)
        self.abort_button.setEnabled(True)
        self.pause_button.setVisible(True)
        self.pause_button.setEnabled(True)
        self.pause_button.setText("Pause")
        self.show_plot_button.setVisible(True)
        self.show_plot_button.setEnabled(True)
        self.QPushButton_Widget1.setEnabled(False)
        self.queue_test_button.setEnabled(False)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.active_run_context.open_realtime_csv(timestamp)
        self.set_test_state(TestState.RUNNING)
        self._notify_blynk_start(request.configuration)

    def set_test_state(self, state):
        if isinstance(state, str):
            state = TestState(state)

        previous_state = self.test_state
        self.test_state = state

        active = state in {
            TestState.RUNNING,
            TestState.PAUSING,
            TestState.PAUSED,
            TestState.STOPPING,
        }
        self.QPushButton_Widget1.setEnabled(not active)
        self.queue_test_button.setEnabled(not active)
        self.pause_button.setVisible(active)
        self.abort_button.setVisible(active)
        self.pause_button.setEnabled(state in {TestState.RUNNING, TestState.PAUSED})
        self.abort_button.setEnabled(
            state in {TestState.RUNNING, TestState.PAUSING, TestState.PAUSED}
        )
        pause_button_text = {
            TestState.PAUSING: "Pausing...",
            TestState.PAUSED: "Resume",
        }.get(state, "Pause")
        self.pause_button.setText(pause_button_text)
        self.abort_button.setText("Stopping..." if state == TestState.STOPPING else "Abort")
        if self.progress_tracker:
            if state == TestState.PAUSED:
                self.progress_tracker.pause()
            elif state == TestState.RUNNING:
                self.progress_tracker.resume()
            self._refresh_progress_display()
        self.progress_bar.setVisible(active)
        self.progress_label.setVisible(active)
        if not active:
            self.show_plot_button.setVisible(False)
            self.show_plot_button.setEnabled(False)

        if state != previous_state:
            message = f"Test state: {previous_state.value} -> {state.value}"
            self.OutputBox.append(message)
            self.write_run_log(message)
            self.write_diagnostic(
                "state_changed",
                previous_state=previous_state.value,
                state=state.value,
            )
            self._publish_blynk({"v7": state.value}, force=True)
        self.plot_window.update_test_state(state.value)
        self.temperature_plot_widget.update_test_state(state.value)

    def prepare_run_storage(self, parameters, run_parameters, run_id=None):
        simulation_mode = is_simulation_mode()
        output_root = str(run_parameters.savelocation)
        dut_name = parameters.get("DUT") or parameters.get("selected_DUT")
        context = RunContext.create(
            run_id or "direct-run",
            output_root,
            dut_name,
            parameters,
            run_parameters,
            self.checkbox_states,
            simulation_mode=simulation_mode,
        )
        self.run_storage = context.storage
        self._output_root = str(context.output_root)
        self.analysis_widget.output_root = context.output_root
        if simulation_mode:
            self.OutputBox.append("SIMULATION MODE: generated data is not real")
        self.OutputBox.append(f"Run directory: {self.run_storage.root}")
        self.write_run_log(f"Selected tests: {self.checkbox_states}")
        self.write_diagnostic(
            "run_started",
            dut=parameters.get("DUT") or parameters.get("selected_DUT"),
            selected_tests=[
                name for name, selected in self.checkbox_states.items() if selected
            ],
        )
        return context

    def write_run_log(self, message):
        if not self.run_storage:
            return
        try:
            append_timestamped_line(self.run_storage.log_file, message)
        except OSError as exception:
            print_console_safe(f"Run log write failed: {exception}")

    def write_diagnostic(self, event, level="INFO", message=None,
                         exception=None, traceback_text=None, **context):
        if not self.run_storage:
            return
        try:
            append_diagnostic(
                self.run_storage.diagnostics_file,
                event,
                level=level,
                message=message,
                exception=exception,
                traceback_text=traceback_text,
                **context,
            )
        except OSError as diagnostic_error:
            print_console_safe(f"Diagnostic log write failed: {diagnostic_error}")
    
    def stop_worker(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            if self.run_controller.active_worker is self.worker:
                self.run_controller.request_stop()
            else:
                self.worker.request_stop()
            self.OutputBox.append("Stop requested, waiting for worker to finish...")

    def toggle_pause_test(self):
        if not self.worker or not self.worker.isRunning():
            return

        if self.test_state == TestState.PAUSED:
            if self.run_controller.active_worker is self.worker:
                self.run_controller.resume()
            else:
                self.worker.resume()
            self.OutputBox.append("Resume requested...")
        elif self.test_state == TestState.RUNNING:
            if self.run_controller.active_worker is self.worker:
                self.run_controller.pause()
            else:
                self.worker.pause()
            self.OutputBox.append("Pause requested; waiting for a safe checkpoint...")
    
    def update_plot(
        self,
        set_voltage,
        set_current,
        programming_voltage,
        readback_voltage,
        readback_current,
        programming_error,
        readback_error,
        programming_percent,
        readback_percent,
        programming_upper_bound,
        programming_lower_bound,
        readback_upper_bound,
        readback_lower_bound,
        percentage_upper_bound,
        percentage_lower_bound,
    ):
        programming_percent = report_percentage_error(
            programming_error,
            programming_upper_bound,
        )
        readback_percent = report_percentage_error(
            readback_error,
            programming_upper_bound,
        )
        percentage_upper_bound = 100.0
        percentage_lower_bound = -100.0
        measurement = RealtimeMeasurement(
            set_voltage=set_voltage,
            set_current=set_current,
            programming_voltage=programming_voltage,
            readback_voltage=readback_voltage,
            readback_current=readback_current,
            programming_error=programming_error,
            readback_error=readback_error,
            programming_percent=programming_percent,
            readback_percent=readback_percent,
            programming_upper_bound=programming_upper_bound,
            programming_lower_bound=programming_lower_bound,
            readback_upper_bound=readback_upper_bound,
            readback_lower_bound=readback_lower_bound,
            percentage_upper_bound=percentage_upper_bound,
            percentage_lower_bound=percentage_lower_bound,
        )
        self.realtime_plot_series.append(measurement)
        self.plot_window.popup_plot(
            programming_error,
            readback_error,
            programming_upper_bound,
            programming_lower_bound,
            readback_upper_bound,
            readback_lower_bound,
            programming_percent,
            readback_percent,
            percentage_upper_bound,
            percentage_lower_bound,
        )
        self.plot_window.update_measurement_status(
            measurement,
            self.realtime_plot_series.counter,
        )
        if self.progress_tracker:
            self.progress_tracker.record_measurement()
            self._refresh_progress_display()
        self._write_realtime_measurement(measurement)
        self._append_realtime_measurement_status(measurement)
        self._publish_blynk_measurement(measurement)
        self._handle_realtime_measurement_failure(measurement)

    def _publish_blynk_measurement(self, measurement):
        self._publish_blynk(
            {
                "v0": measurement.set_voltage,
                "v1": measurement.set_current,
                "v2": measurement.programming_voltage,
                "v3": measurement.readback_voltage,
                "v4": measurement.readback_current,
                "v5": measurement.programming_percent,
                "v6": measurement.readback_percent,
                "v8": self.progress_bar.value(),
            }
        )

    def _publish_blynk_run_metadata(self, configuration):
        channel = configuration.get("PSU_Channel")
        if isinstance(channel, range):
            channel = "ALL"
        elif isinstance(channel, (list, tuple, set)):
            channel = ",".join(str(item) for item in channel)
        else:
            channel = str(channel)
        self._publish_blynk(
            {
                "v13": int(configuration.get("noofloop") or 1),
                "v14": channel,
            },
            force=True,
        )

    def _handle_temperature_sample(self, sample, loop_index):
        self.temperature_plot_widget.add_sample(sample, loop_index)
        channel_pins = {
            101: "v10",
            103: "v11",
            104: "v12",
            105: "v16",
        }
        self._publish_blynk(
            {
                channel_pins[channel]: value
                for channel, value in sample.readings.items()
                if channel in channel_pins
            }
        )

    def _publish_blynk(self, values, force=False):
        if self.blynk_active:
            self.blynk_publisher.publish(values, force=force)

    def _on_blynk_status_changed(self, status):
        if not self.QCheckBox_Blynk_Widget.isChecked():
            self._update_blynk_controls()
            return
        self.Blynk_Status_Label.setText(f"Blynk: {status}")
        if status in {"Ready", "Connected"}:
            color = "#1b7f3a"
        elif status.startswith(("Offline", "Not configured")):
            color = "#b22222"
        else:
            color = "#404040"
        self.Blynk_Status_Label.setStyleSheet(
            f"font-weight: bold; color: {color};"
        )
        if status.startswith(("Offline", "Connected; skipped")):
            self.OutputBox.append(f"Blynk: {status}")
            self.write_run_log(f"Blynk: {status}")

    def _on_blynk_notification_status(self, status):
        color = "green" if status.startswith("Notification sent") else "red"
        self.OutputBox.append(
            f'<span style="color:{color};">Blynk: {status}</span>'
        )
        self.write_run_log(f"Blynk: {status}")

    def _update_blynk_controls(self):
        enabled = self.QCheckBox_Blynk_Widget.isChecked()
        if not enabled:
            self.Blynk_Status_Label.setText("Blynk: Disabled")
            self.Blynk_Status_Label.setStyleSheet("color: #404040;")
        elif self.blynk_publisher.configured:
            self.Blynk_Status_Label.setText("Blynk: Configured")
            self.Blynk_Status_Label.setStyleSheet(
                "font-weight: bold; color: #1b7f3a;"
            )
        else:
            self.Blynk_Status_Label.setText(
                "Blynk: Set BLYNK_AUTH_TOKEN and restart"
            )
            self.Blynk_Status_Label.setStyleSheet(
                "font-weight: bold; color: #b22222;"
            )

    def checkbox_state_Blynk(self, _state):
        active_test = self.test_state in {
            TestState.RUNNING,
            TestState.PAUSING,
            TestState.PAUSED,
        }
        if active_test and self.QCheckBox_Blynk_Widget.isChecked():
            self.blynk_active = self.blynk_publisher.start()
            self._publish_blynk({"v7": self.test_state.value}, force=True)
        elif active_test and self.blynk_active:
            self._publish_blynk({"v7": "MONITORING_DISABLED"}, force=True)
            self.blynk_active = False
        self._update_blynk_controls()

    def _write_realtime_measurement(self, measurement):
        if self.active_run_context:
            self.active_run_context.write_realtime_row(measurement.csv_values)

    def _append_realtime_measurement_status(self, measurement):
        if (
            self.last_Iset is None
            or abs(measurement.set_current - self.last_Iset) > 1e-6
        ):
            self.OutputBox.append(
                f"<br><b>===== Current Set: {measurement.set_current:.0f}A =====</b>"
            )
            self.last_Iset = measurement.set_current

        data_index = (
            self.active_run_context.data_index
            if self.active_run_context
            else self.realtime_plot_series.counter
        )
        status = "Pass" if measurement.passed else "Fail"
        color = "green" if measurement.passed else "red"
        log_line = (
            f"[{data_index}] {measurement.set_current:.0f}A : "
            f"{measurement.set_voltage:.0f}V : {status}"
        )
        self.OutputBox.append(f'<span style="color:{color};">{log_line}</span>')

    def _handle_realtime_measurement_failure(self, measurement):
        if not measurement.passed:
            self._notify_blynk_error(
                "Boundary failure: "
                f"Vset={measurement.set_voltage:.6g} V, "
                f"Iset={measurement.set_current:.6g} A, "
                f"programming error={measurement.programming_error:.6g} "
                f"({measurement.programming_percent:.3f}%), "
                f"readback error={measurement.readback_error:.6g} "
                f"({measurement.readback_percent:.3f}%)."
            )
        if (
            measurement.passed
            or self.continue_on_boundary_failure
            or self.fail_prompt_active
        ):
            return

        self.fail_prompt_active = True
        if self.worker:
            self.worker.pause()
        self.handle_test_failure()

    def _notify_blynk_error(self, description):
        if self.blynk_active:
            self.blynk_publisher.notify_error(description)

    def _notify_blynk_start(self, configuration):
        if not self.blynk_active:
            return
        channel = configuration.get("PSU_Channel", "Unknown")
        if isinstance(channel, range):
            channel = "ALL"
        collections = configuration.get("noofloop", "Unknown")
        dut = configuration.get("DUT") or configuration.get(
            "selected_DUT", "Unknown"
        )
        self.blynk_publisher.notify_start(
            f"Test started: DUT={dut}, channel={channel}, "
            f"data collections={collections}."
        )

    def _notify_blynk_completion(self):
        if not self.blynk_active:
            return
        configuration = (
            self.active_run_context.configuration
            if self.active_run_context
            else {}
        )
        channel = configuration.get("PSU_Channel", "Unknown")
        if isinstance(channel, range):
            channel = "ALL"
        collections = configuration.get("noofloop", "Unknown")
        dut = configuration.get("DUT") or configuration.get(
            "selected_DUT", "Unknown"
        )
        self.blynk_publisher.notify_completion(
            f"Test completed: DUT={dut}, channel={channel}, "
            f"data collections={collections}."
        )

    def handle_test_failure(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Test Failure Detected")

        countdown = {"remaining": 10, "expired": False}

        def update_message():
            msg.setText(
                "A test point failure has been detected.\n\n"
                f"The test will continue automatically in "
                f"{countdown['remaining']} seconds."
            )

        update_message()

        ignore_btn = msg.addButton("Ignore and Continue", QMessageBox.AcceptRole)
        continue_all_btn = msg.addButton(
            "Continue All Failures", QMessageBox.AcceptRole
        )
        terminate_btn = msg.addButton("Terminate Test", QMessageBox.RejectRole)

        countdown_timer = QTimer(self)
        countdown_timer.setInterval(1000)

        def advance_countdown():
            countdown["remaining"] -= 1
            if countdown["remaining"] <= 0:
                countdown["expired"] = True
                countdown_timer.stop()
                msg.setText(
                    "A test point failure has been detected.\n\n"
                    "Continuing automatically..."
                )
                msg.accept()
                return
            update_message()

        countdown_timer.timeout.connect(advance_countdown)
        countdown_timer.start()

        msg.exec_()
        countdown_timer.stop()

        if countdown["expired"]:
            self.fail_prompt_active = False
            if self.worker:
                self.worker.resume()
            self.OutputBox.append(
                "<span style='color:orange;'>⚠ Failure countdown expired — "
                "test resumed automatically</span>"
            )
            self.write_diagnostic(
                "boundary_failure_auto_continued",
                countdown_seconds=10,
            )
        elif msg.clickedButton() == ignore_btn:
            self.fail_prompt_active = False
            if self.worker:
                self.worker.resume()
            self.OutputBox.append(
                "<span style='color:orange;'>⚠ Failure ignored by operator — test resumed</span>"
            )
        elif msg.clickedButton() == continue_all_btn:
            self.continue_on_boundary_failure = True
            self.fail_prompt_active = False
            self.worker.resume()
            self.OutputBox.append(
                "<span style='color:orange;'>⚠ Continuing automatically after boundary failures for this run</span>"
            )
            self.write_diagnostic(
                "boundary_failure_policy_changed",
                policy="continue_all",
            )
        elif msg.clickedButton() == terminate_btn:
            self.was_aborted = True
            self.set_test_state(TestState.STOPPING)
            if self.run_controller.active_worker is self.worker:
                self.run_controller.request_stop(clear_pending=False)
            else:
                self.worker.request_stop()
            self.OutputBox.append(
                "<span style='color:red;'>⛔ Test terminated by operator</span>"
            )

    def update_status(self, message):
        self.OutputBox.append(message)
    
    def show_error(self, exception, traceback_str=None):
        QMessageBox.critical(self, "Error", str(exception))
 
    def select_button(self):
        sender = self.sender()

        if sender == self.QPushButton_Voltage_Widget:
            self.QPushButton_Voltage_Widget.setChecked(True)
            self.QPushButton_Current_Widget.setChecked(False)
        elif sender == self.QPushButton_Current_Widget:
            self.QPushButton_Current_Widget.setChecked(True)
            self.QPushButton_Voltage_Widget.setChecked(False)

        self.InteractiveAction()

    def on_current_index_changed(self):
        selected_text = self.QComboBox_DUT.currentText()
        self.params.update_selection(selected_text)
        self._apply_parameter_widget_bindings(
            self.PARAMETER_TEXT_BINDINGS, "setText"
        )
        self._apply_parameter_widget_bindings(
            self.PARAMETER_COMBO_BINDINGS, "setCurrentText"
        )

        load_function = getattr(self.params, "setFunction", None)
        if load_function in {"Voltage", "Current", "Resistance"}:
            self.QComboBox_set_Function.setCurrentText(
                f"{load_function} Priority"
            )

        voltage_sense = getattr(self.params, "VoltageSense", None)
        if voltage_sense is not None:
            sense_text = "4 Wire" if voltage_sense == "EXT" else "2 Wire"
            self.QComboBox_Voltage_Sense.setCurrentText(sense_text)

        hornbill_selected = selected_text == "Hornbill"
        self.QCheckBox_Sinking_Test_Widget.setVisible(hornbill_selected)
        if not hornbill_selected:
            self.QCheckBox_Sinking_Test_Widget.setChecked(False)
        self.QLabel_Hornbill_Measurement_Command.setVisible(hornbill_selected)
        self.QComboBox_Hornbill_Measurement_Command.setVisible(hornbill_selected)
        self.QLabel_SweepPoints.setVisible(hornbill_selected)
        self.QLineEdit_SweepPoints.setVisible(hornbill_selected)
        self._load_dmm_settings_from_parameters()

    def _apply_parameter_widget_bindings(self, bindings, setter_name):
        for widget_name, parameter_name in bindings:
            value = getattr(self.params, parameter_name, None)
            if value is None:
                continue
            widget = getattr(self, widget_name)
            getattr(widget, setter_name)(str(value))

    def set_PSU_Channel_changed(self, s):
        
        if self.QComboBox_set_PSU_Channel.currentText() == "ALL":
            self.params.PSU_Channel = range(1,5)
        else:
            self.params.PSU_Channel = s

    def ELoad_Channel_changed(self, s):
       self.params.ELoad_Channel = s

    def Voltage_Rating_changed(self, value):
        self.params.Voltage_Rating = value

    def Current_Rating_changed(self, value):
        self.params.Current_Rating = value

    def Power_Rating_changed(self, value):
        self.params.Power_Rating = value
     
    def Power_changed(self, value):
        self.params.Power = value

    def PowerINI_changed(self, value):
        self.params.powerini= value
    
    def power_step_size_changed(self, value):
        self.params.power_step_size = value
    
    def rshunt_changed(self, value):
        self.params.rshunt = value
    
    def _instrument_address_widgets(self):
        return (
            self.QLineEdit_PSU_VisaAddress,
            self.QLineEdit_DMM_VisaAddressforVoltage,
            self.QLineEdit_DMM_VisaAddressforCurrent,
            self.QLineEdit_OSC_VisaAddress,
            self.QLineEdit_ELoad_VisaAddress,
            self.QLineEdit_DAQ_VisaAddress,
            self.QLineEdit_External_Source_VisaAddress,
        )

    def _instrument_role_widgets(self):
        return {
            "PSU": self.QLineEdit_PSU_VisaAddress,
            "ELOAD": self.QLineEdit_ELoad_VisaAddress,
            "DMM": self.QLineEdit_DMM_VisaAddressforVoltage,
            "DMM2": self.QLineEdit_DMM_VisaAddressforCurrent,
            "SCOPE": self.QLineEdit_OSC_VisaAddress,
            "DAQ": self.QLineEdit_DAQ_VisaAddress,
            "EXTERNALSOURCE": self.QLineEdit_External_Source_VisaAddress,
        }

    def _selected_instrument_scan(self):
        enabled_transports = set()
        transport_widgets = (
            ("usb", self.QCheckBox_USB_Widget),
            ("gpib", self.QCheckBox_GPIB_Widget),
            ("tcpip_ip", self.QCheckBox_IP_Widget),
            ("tcpip_hostname", self.QCheckBox_Hostname_Widget),
        )
        for transport, checkbox in transport_widgets:
            if checkbox.isChecked():
                enabled_transports.add(transport)
        config_path = configuration_path(
            config_folder,
            self.QComboBox_DUT.currentText(),
        )
        return config_path, enabled_transports

    def doFind(self):       #Shamman changes
        if (
            self.instrument_discovery_thread is not None
            and self.instrument_discovery_thread.isRunning()
        ):
            return

        try:
            config_path, enabled_transports = self._selected_instrument_scan()
        except Exception as exception:
            self.OutputBox.append("No Devices Found!!! " + str(exception))
            return

        self.QPushButton_Widget4.setEnabled(False)
        self.QPushButton_Widget4.setText("Scanning...")
        self.OutputBox.append("Scanning configured VISA instruments...")

        thread = QThread(self)
        worker = InstrumentDiscoveryWorker(
            config_path,
            enabled_transports,
            GetConfiguredVisaResources,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._instrument_discovery_completed)
        worker.failed.connect(self._instrument_discovery_failed)
        worker.completed.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._instrument_discovery_stopped)

        self.instrument_discovery_thread = thread
        self.instrument_discovery_worker = worker
        thread.start()

    @pyqtSlot(object)
    def _instrument_discovery_completed(self, discovery):
        self.visaIdList = list(discovery.addresses)
        self.nameList = list(discovery.identities)
        present_discovery_result(
            discovery,
            address_widgets=self._instrument_address_widgets(),
            role_widgets=self._instrument_role_widgets(),
            unavailable_role_items={"ELOAD": "None"},
            output_widget=self.OutputBox,
        )
        self.OutputBox.append(
            f"Found {len(discovery.addresses)} available configured "
            "instrument(s); responsive addresses were added to the lists."
        )
        if not discovery.addresses:
            self.OutputBox.append(
                "No configured instruments responded on the selected transports."
            )

    @pyqtSlot(str)
    def _instrument_discovery_failed(self, message):
        self.OutputBox.append("No Devices Found!!! " + message)

    @pyqtSlot()
    def _instrument_discovery_stopped(self):
        thread = self.instrument_discovery_thread
        self.instrument_discovery_worker = None
        self.instrument_discovery_thread = None
        self.QPushButton_Widget4.setText("Find Instruments")
        self.QPushButton_Widget4.setEnabled(True)
        if thread is not None:
            thread.deleteLater()

    
    def updatedelay_changed(self, value):
        self.params.updatedelay = value

    def noofloop_changed(self, value):
        self.params.noofloop = value

    def DMM_Instrument_changed(self, s):
        self.params.DMM_Instrument = s

    def PSU_VisaAddress_changed(self, s):
        self.params.PSU = s    

    def DMM_VisaAddressforVoltage_changed(self, s):
        self.params.DMM = s
    
    def DMM_VisaAddressforCurrent_changed(self, s):
        self.params.DMM2 = s

    def ELoad_VisaAddress_changed(self, s):
        self.params.ELoad = s

    def OSC_VisaAddress_changed(self, s):
        self.params.OSC = s

    def DAQ_VisaAddress_changed(self, s):
        self.params.DAQ = s

    def External_Source_VisaAddress_changed(self, s):
        self.params.ExternalSource = s

    def OSC_Channel_changed(self, s):
        self.params.OSC_Channel = s

    def DUT_changed(self, s):
        self.params.DUT = s

    def ELoad_Channel_changed(self, s):
        self.params.ELoad_Channel = s

    def PSU_Channel_changed(self, s):
        self.params.PSU_Channel = s

    def Programming_Error_Gain_changed(self, s):
        self.params.Programming_Error_Gain = s

    def Programming_Error_Offset_changed(self, s):
        self.params.Programming_Error_Offset = s

    def Readback_Error_Gain_changed(self, s):
        self.params.Readback_Error_Gain = s

    def Readback_Error_Offset_changed(self, s):
        self.params.Readback_Error_Offset = s
    
    def Load_Programming_Error_Gain_changed(self, s):
        self.params.Load_Programming_Error_Gain = s

    def Load_Programming_Error_Offset_changed(self, s):
        self.params.Load_Programming_Error_Offset = s

    def Power_Programming_Error_Gain_changed(self, s):
        self.params.Power_Programming_Error_Gain = s

    def Power_Programming_Error_Offset_changed(self, s):
        self.params.Power_Programming_Error_Offset = s

    def Power_Readback_Error_Gain_changed(self, s):
        self.params.Power_Readback_Error_Gain = s

    def Power_Readback_Error_Offset_changed(self, s):
        self.params.Power_Readback_Error_Offset = s
    
    def Programming_Response_Up_NoLoad_changed(self, s):
        self.params.Programming_Response_Up_NoLoad = s

    def Programming_Response_Up_FullLoad_changed(self, s):
        self.params.Programming_Response_Up_FullLoad = s

    def Programming_Response_Down_NoLoad_changed(self, s):
        self.params.Programming_Response_Down_NoLoad = s

    def Programming_Response_Down_FullLoad_changed(self, s):
        self.params.Programming_Response_Down_FullLoad = s

    def minVoltage_changed(self, s):
        self.params.minVoltage = s

    def maxVoltage_changed(self, s):
        self.params.maxVoltage = s

    def minCurrent_changed(self, s):
        self.params.minCurrent = s

    def maxCurrent_changed(self, s):
        self.params.maxCurrent = s

    def voltage_step_size_changed(self, s):
        self.params.voltage_step_size = s

    def current_step_size_changed(self, s):
        self.params.current_step_size = s

    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.params.setFunction = "Voltage"

        elif s == "Current Priority":
            self.params.setFunction = "Current"

        elif s == "Resistance Priority":
            self.params.setFunction = "Resistance"

    def set_VoltageRes_changed(self, s):
        self.params.VoltageRes = s

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.params.VoltageSense = "INT"
        elif s == "4 Wire":
            self.params.VoltageSense = "EXT"

    def Hornbill_Measurement_Command_changed(self, command):
        self.params.Hornbill_Measurement_Command = command

    def SweepPoints_changed(self, sample_count):
        self.params.SweepPoints = sample_count

    def External_Source_Positive_Current_Limit_changed(self, value):
        self.params.External_Source_Positive_Current_Limit = value

    def External_Source_Negative_Current_Limit_changed(self, value):
        self.params.External_Source_Negative_Current_Limit = value

    def Sink_Slew_Rate_changed(self, value):
        self.params.slewrate = value

    def Sinking_Initial_Voltage_changed(self, value):
        self.params.Sinking_Initial_Voltage = value

    def Sinking_Final_Voltage_changed(self, value):
        self.params.Sinking_Final_Voltage = value

    def Sinking_Voltage_Step_Size_changed(self, value):
        self.params.Sinking_Voltage_Step_Size = value

    def Relay_Control_changed(self, selection):
        self.params.Relay_Control = selection

    def OVP_Level_changed(self, s):
        self.params.OVP_Level = s
        self.OutputBox.setPlainText("OVP Level Set to: " + str(self.params.OVP_Level))
    
    def OCP_Level_changed(self, s):
        self.params.OCP_Level = s
        self.OutputBox.setPlainText("OCP Level Set to: " + str(self.params.OCP_Level))
    
    def OCP_Activation_Time_changed(self,s):
        self.params.OCPActivationTime = s

    def SPOperationMode_changed(self,s):
        self.params.SPOperationMode = s

        if self.params.SPOperationMode == "Series" or self.params.SPOperationMode == "Parallel":
            self.QComboBox_set_PSU_Channel.setEnabled(False)
            self.QComboBox_set_PSU_Channel.setCurrentIndex(0)
        else:
            self.QComboBox_set_PSU_Channel.setEnabled(True)

    def AC_Supply_Type_changed (self,s):
        self.params.AC_Supply_Type = s
        if s == "AC Source":
            dialogAC = ACSourceSetting(self.params)
            if dialogAC.exec() != QDialog.Accepted:
                self.params.AC_Supply_Type = "Plug"
                self.QComboBox_AC_Supply_Type.blockSignals(True)
                self.QComboBox_AC_Supply_Type.setCurrentText("Plug")
                self.QComboBox_AC_Supply_Type.blockSignals(False)
        self._update_ac_supply_controls()

    def _update_ac_supply_controls(self):
        programmable = self.params.AC_Supply_Type == "AC Source"
        for checkbox in (
            self.QCheckBox_VoltageLineRegulation_Widget,
            self.QCheckBox_CurrentLineRegulation_Widget,
        ):
            checkbox.setEnabled(programmable)
            if not programmable:
                checkbox.setChecked(False)
    
    def Line_Reg_Range_changed (self):
        self.params.Line_Reg_Range = [100,115,230]
    
    def checkbox_state_SpecialCase(self, s):
        self.checkbox_SpecialCase = s

    def checkbox_state_NormalCase(self, s):
        self.checkbox_NormalCase = s

    def checkbox_state_Report(self, s):
        self.checkbox_data_Report = s

    def checkbox_state_Image(self, s):
        self.checkbox_data_Image = s

    def checkbox_state_Temperature(self, state):
        enabled = state == Qt.Checked
        self.QLabel_DAQ_VisaAddress.setVisible(enabled)
        self.QLineEdit_DAQ_VisaAddress.setVisible(enabled)

    def checkbox_state_lock(self, state):
        lockable_widgets = (QPushButton, QLineEdit, QTextEdit, QComboBox)

        for widget in self.findChildren(lockable_widgets):
            widget.setDisabled(state == 2)  # Disable if checkbox is checked

    def checkbox_state_VoltageAccuracy(self, s):
        self.checkbox_test_VoltageAccuracy = s
        self.InteractiveAction()
        self.Image_Label_Setup()

    def checkbox_state_VoltageLoadRegulation(self, s):
        self.checkbox_test_VoltageLoadRegulation = s
        self.InteractiveAction()
        self.Image_Label_Setup()
    
    def checkbox_state_TransientRecovery(self, s):
        self.checkbox_test_TransientRecovery = s
        self.InteractiveAction()
        self.Image_Label_Setup()   
    
    def checkbox_state_CurrentAccuracy(self, s):
        self.checkbox_test_CurrentAccuracy = s
        self.InteractiveAction()
        self.Image_Label_Setup()
    
    def checkbox_state_CurrentLoadRegulation(self, s):
        self.checkbox_test_CurrentLoadRegulation = s
        self.InteractiveAction()
        self.Image_Label_Setup()
    
    def checkbox_state_PowerAccuracy(self, s):
        self.checkbox_test_PowerAccuracy = s
        self.InteractiveAction()
        self.Image_Label_Setup()
    
    def checkbox_state_OVP_Test(self, s):
        self.checkbox_test_OVP_Test = s
        self.InteractiveAction()
        self.Image_Label_Setup()

    def checkbox_state_OCP_Test(self, state):
        self.checkbox_test_OCP_Test = state
        self.InteractiveAction()
        self.Image_Label_Setup()

    def checkbox_state_VoltageLine (self):
        self.InteractiveAction()
        self.Image_Label_Setup()

    def checkbox_state_CurrentLine (self):
        self.InteractiveAction()
        self.Image_Label_Setup()

    def checkbox_state_ProgrammingSpeed_Test(self, s):
        self.checkbox_test_ProgrammingSpeed = s
        self.InteractiveAction()

    def T_Settling_Band_changed(self, s):
        self.params.T_Settling_Band = s

    def V_Settling_Band_changed(self, s):
        self.params.V_Settling_Band = s

    def Channel_CouplingMode_changed(self, s):
        self.params.Channel_CouplingMode = s

    def Trigger_CouplingMode_changed(self, s):
        self.params.Trigger_CouplingMode = s

    def Trigger_Mode_changed(self, s):
        self.params.Trigger_Mode = s

    def Trigger_SweepMode_changed(self, s):
        self.params.Trigger_SweepMode = s

    def Trigger_SlopeMode_changed(self, s):
        self.params.Trigger_SlopeMode = s
    
    def Probe_Setting_changed(self, s):
        self.params.Probe_Setting = s
    
    def Acq_Type_changed(self, s):
        self.params.Acq_Type = s

    def TimeScale_changed(self, s):
        self.params.TimeScale = s

    def VerticalScale_changed(self, s):
        self.params.VerticalScale = s

    def setRange(self, value):
        self.params.Range = value

    def setAperture(self, value):
        self.params.Aperture = value

    def setAutoZero(self, value):
        self.params.AutoZero = value

    def setInputZ(self, value):
        self.params.inputZ = value

    def setUpTime(self, value):
        self.params.UpTime = value

    def setDownTime(self, value):
        self.params.DownTime = value
    
    #Image Set
    def Image_Label_Setup(self):

        for test_name, image_path in self.params.image_connections_path.items():
            # Build the checkbox widget name dynamically based on test_name
            checkbox_name = f"QCheckBox_{test_name}_Widget"

            # Use getattr to dynamically access the checkbox widget
            checkbox = getattr(self, checkbox_name, None)
            if checkbox is None:
                continue

            if checkbox.isChecked():  # Check if the checkbox is selected
                self.pixmap = QPixmap(image_path)
                scaled_pixmap = self.pixmap.scaled(
                    348,
                    198,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )

                # Set the image on the label
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setAlignment(Qt.AlignCenter)
                self.image_label.setVisible(True)
                self.image_label.mousePressEvent = self.open_image_dialog
                
                return
            else:
                self.image_label.setVisible(False)

    # Function to open a dialog with the enlarged image
    def open_image_dialog(self,event):
        dialog = QDialog(self)  # Create the dialog window
        dialog.setWindowTitle("Image Viewer")

        # Create a label for the image in the dialog
        image_label = QLabel(dialog)
        scaled_image = self.pixmap.scaled(1000, 1000, Qt.KeepAspectRatio)
        image_label.setPixmap(scaled_image)  # Set the original (full size) image
        image_label.setAlignment(Qt.AlignCenter)  # Center the image in the dialog

        # Set a layout and add the label to it
        layout = QVBoxLayout(dialog)
        layout.addWidget(image_label)

        # Add close button
        button_box = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        layout.addWidget(button_box)

        # Connect the close button to close the dialog
        button_box.rejected.connect(dialog.accept)

        dialog.setLayout(layout)
        dialog.exec_()  # Open the dialog

    #Disable the INPUT when test changed
    def InteractiveAction(self):
        self._update_measurement_mode()
        self._update_test_option_visibility()
        self._update_ac_supply_controls()
        self._update_save_path_status()

    def _update_measurement_mode(self):
        if self.QPushButton_Current_Widget.isChecked():
            unit = "CURRENT"
            load_mode = "Voltage Priority"
        elif self.QPushButton_Voltage_Widget.isChecked():
            unit = "VOLTAGE"
            load_mode = "Current Priority"
        else:
            return

        current_mode = unit == "CURRENT"
        self.QComboBox_set_Function.setCurrentText(load_mode)
        self.set_Function_changed(load_mode)
        self.params.unit = unit
        self.Voltage_Test_group.setVisible(not current_mode)
        self.Current_Test_group.setVisible(current_mode)
        self.QLabel_DMM_VisaAddressforCurrent.setVisible(current_mode)
        self.QLineEdit_DMM_VisaAddressforCurrent.setVisible(current_mode)
        self.QLineEdit_rshunt.setEnabled(current_mode)

    def _update_test_option_visibility(self):
        accuracy_selected = (
            self.QCheckBox_CurrentAccuracy_Widget.isChecked()
            or self.QCheckBox_VoltageAccuracy_Widget.isChecked()
        )
        self.programming_error_widget.setVisible(accuracy_selected)

        ovp_selected = self.QCheckBox_OVP_Test_Widget.isChecked()
        self.QLineEdit_OVP_Level.setEnabled(ovp_selected)
        self.OVP_error_widget.setVisible(ovp_selected)

        ocp_selected = self.QCheckBox_OCP_Test_Widget.isChecked()
        self.QLineEdit_OCP_Level.setEnabled(ocp_selected)

        power_selected = self.QCheckBox_PowerAccuracy_Widget.isChecked()
        self.QComboBox_set_Function.setEnabled(power_selected)
        self.power_programming_error_widget.setVisible(power_selected)
        self.power_setting_widget.setVisible(power_selected)

        load_regulation_selected = any(
            checkbox.isChecked()
            for checkbox in (
                self.QCheckBox_VoltageLoadRegulation_Widget,
                self.QCheckBox_CurrentLoadRegulation_Widget,
                self.QCheckBox_VoltageLineRegulation_Widget,
                self.QCheckBox_CurrentLineRegulation_Widget,
            )
        )
        self.load_error_widget.setVisible(load_regulation_selected)

        transient_selected = self.QCheckBox_TransientRecovery_Widget.isChecked()
        programming_response_selected = (
            self.QCheckBox_ProgrammingSpeed_Widget.isChecked()
        )
        oscilloscope_required = (
            ocp_selected
            or transient_selected
            or programming_response_selected
            or (
                self.QCheckBox_VoltageAccuracy_Widget.isChecked()
                and self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget.isChecked()
            )
        )
        self.oscilloscope_settings_widget.setVisible(oscilloscope_required)
        self.Programming_Response_widget.setVisible(programming_response_selected)
        self.Sinking_Test_group.setVisible(
            self.QCheckBox_Sinking_Test_Widget.isChecked()
        )

    def _update_save_path_status(self):
        save_location = str(self.params.savelocation)
        if save_location != self.DEFAULT_SAVE_LOCATION:
            self.QPushButton_Widget0.setStyleSheet("color: darkgreen")
            self.QPushButton_Widget0.setText("Save Path Selected ✅")
        else:
            self.QPushButton_Widget0.setStyleSheet("color: orange")
    
    def estimateTime(self, params: Parameters):
        """
        Estimate the total time for nested voltage/current loops,
        considering update delay, number of loops, and power limit.
        """
        try:
            # Read parameters from the Parameters instance
            min_current = float(params.minCurrent)
            max_current = float(params.maxCurrent)
            current_step = float(params.current_step_size)
            min_voltage = float(params.minVoltage)
            max_voltage = float(params.maxVoltage)
            voltage_step = float(params.voltage_step_size)
            update_delay = float(params.updatedelay or 0)
            num_loops = float(params.noofloop or 1)
            power_limit = float(params.Power_Rating or float('inf'))  # Use power rating if available

            # Calculate number of steps
            curr_steps = int((max_current - min_current) / current_step) + 1
            volt_steps = int((max_voltage - min_voltage) / voltage_step) + 1

            total_steps = 0

            # Count only voltage/current combinations that are within the power limit
            for i in range(curr_steps):
                curr = min_current + i * current_step
                for j in range(volt_steps):
                    volt = min_voltage + j * voltage_step
                    if volt * curr <= power_limit:  # Skip steps exceeding power limit
                        total_steps += 1

            # Estimate time per step
            time_per_step = 1.0 + update_delay if update_delay > 0 else 1.0

            # Total estimated time
            params.estimatetime = total_steps * time_per_step * num_loops

            # Show in OutputBox if available
            if hasattr(self, "OutputBox") and self.OutputBox:
                self.OutputBox.append(f"{params.estimatetime:.2f} seconds")
                self.OutputBox.append("")

        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Input error: {e}")
            return

    def savepath(self):
        self.OutputBox.clear()

        # Open a folder selection dialog
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")

        if directory:
            self.params.savelocation = directory
            self.OutputBox.append("Path Selected ✅ " + str(self.params.savelocation))
            self.OutputBox.append("")
            self.InteractiveAction()
        else:
            self.OutputBox.append("No folder selected ❌")
            self.OutputBox.append("")
    
    # Check for empty inputs
    def check_missing_params(self, data_dict):
        missing_keys = [key for key, value in data_dict.items() if not value]  # Find missing values

        if missing_keys:
            QMessageBox.warning(
                self, "Error", f"Missing parameters: {', '.join(missing_keys)}"
            )
            return False

        return True
    
    def pre_test_check(self, configuration, selections=None):
        self.checkbox_states = dict(
            selections if selections is not None else collect_test_selections(self)
        )

        errors, required_roles = validate_preflight(
            configuration, self.checkbox_states
        )
        if errors:
            message = "Preflight validation failed:\n\n- " + "\n- ".join(errors)
            self.OutputBox.append(message.replace("\n", "<br>"))
            QMessageBox.warning(self, "Preflight Validation", message)
            return False

        visa_addresses = [
            configuration[role] for role in sorted(required_roles)
        ]
        resource_manager = VisaResourceManager()
        try:
            connected, errors = resource_manager.openRM(*visa_addresses)
        finally:
            resource_manager.closeRM()

        if connected == 0:
            error_text = " ".join(str(item) for item in errors)
            QMessageBox.warning(self, "VISA IO ERROR", error_text)
            return False

        return True

    def _test_submission_is_blocked(self):
        return self.run_controller.is_running or bool(
            self.worker and self.worker.isRunning()
        )

    def _confirm_test_submission(self):
        return QMessageBox.question(
            self,
            "Test Running",
            "Test will be started.\nDo you still want to continue?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        ) == QMessageBox.Yes

    def _enqueue_submission(self, submission, queue_only):
        request = self.run_controller.enqueue(
            submission.selections,
            submission.configuration,
            submission.parameters,
            label=submission.label,
            prepare=self._prepare_queued_run,
            auto_start=False,
        )
        if queue_only:
            self.OutputBox.append("Test added to queue")
        else:
            self.run_controller.start_queue()
        return request

    def executeTest(self, queue_only=False):
        if not queue_only and self._test_submission_is_blocked():
            QMessageBox.warning(
                self,
                "Test Already Running",
                "Wait for the active test to finish or stop it first.",
            )
            return

        self.setEnabled(False)
        self.OutputBox.clear()
        try:
            selections = collect_test_selections(self)
            submission = prepare_run_submission(self.params, selections)
            self.checkbox_states = submission.selections
            self.dict_reset = submission.configuration

            if not self.pre_test_check(
                submission.configuration, submission.selections
            ):
                return
            if not self._confirm_test_submission():
                print_console_safe("Test canceled by user")
                return

            self._enqueue_submission(submission, queue_only)
        except Exception as exception:
            traceback_str = traceback.format_exc()
            normalized_error = normalize_execution_error(
                exception,
                traceback_str,
                dut=self.params.get("DUT"),
            )
            self.write_diagnostic(
                "test_start_failed",
                level="ERROR",
                exception=normalized_error,
                traceback_text=traceback_str,
            )
            show_error_dialog(self, normalized_error, traceback_str)
        finally:
            self.setEnabled(True)

    # Slot to update OutputBox safely
    def update_output(self, msg):
        self.OutputBox.append(msg)
        self.write_run_log(msg)
        print_console_safe(msg)

    def update_progress_bar(self, value):
        """Update the progress bar value"""
        if self.progress_tracker and value >= 100:
            self.progress_tracker.mark_complete()
            self._refresh_progress_display()
            self._publish_blynk({"v8": 100})
            return
        self.progress_bar.setValue(value)
        self._publish_blynk({"v8": value})

    def _refresh_progress_display(self):
        if not self.progress_tracker:
            return
        snapshot = self.progress_tracker.snapshot()
        self.progress_bar.setValue(snapshot.percent)
        elapsed = format_duration(snapshot.elapsed_seconds)
        if (
            not self.progress_tracker.completed
            and snapshot.total > 0
            and snapshot.completed >= snapshot.total
        ):
            detail = f"Elapsed {elapsed} • Running remaining tests and reports"
        elif snapshot.remaining_seconds is None:
            detail = f"Elapsed {elapsed} • ETA learning from instrument responses"
        else:
            remaining = format_duration(snapshot.remaining_seconds)
            detail = (
                f"Elapsed {elapsed} • Remaining {remaining} • "
                f"{snapshot.completed}/{snapshot.total} points"
            )
        self.progress_label.setText(detail)

    # MODIFIED - Simplified abort function
    def abort_test(self):
        if self.test_state not in {
            TestState.RUNNING,
            TestState.PAUSING,
            TestState.PAUSED,
        }:
            return

        reply = QMessageBox.question(
            self,
            'Confirm Abort',
            'Are you sure you want to safely stop the current operation?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
            )

        if reply == QMessageBox.Yes:
            self.was_aborted = True
            self.update_output("Stop requested; shutting down at the next safe checkpoint...")
            self.set_test_state(TestState.STOPPING)
            if self.worker and self.worker.isRunning():
                if self.run_controller.active_worker is self.worker:
                    self.run_controller.request_stop(clear_pending=False)
                else:
                    self.worker.request_stop()

    def closeEvent(self, event):
        if (
            self.instrument_discovery_thread is not None
            and self.instrument_discovery_thread.isRunning()
        ):
            self.OutputBox.append(
                "Instrument discovery is still running; wait for it to finish "
                "before closing this window."
            )
            event.ignore()
            return

        if not self.worker or not self.worker.isRunning():
            self.webcam_widget.stop_preview()
            self.blynk_publisher.stop()
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Stop Running Test",
            "A test is running. Stop it safely before closing this window?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            event.ignore()
            return

        self.was_aborted = True
        self.update_output(
            "Window close requested; stopping safely before the window can close..."
        )
        self.set_test_state(TestState.STOPPING)
        if self.run_controller.active_worker is self.worker:
            self.run_controller.request_stop()
        else:
            self.worker.request_stop()
        event.ignore()

    def cleanup_test(self, reason="unknown"):       #Shamman changes
        if self._cleanup_done:
            return
        self._cleanup_done = True
        print_console_safe(f"Cleaning up test due to: {reason}")

        if self.active_run_context:
            try:
                self.active_run_context.close()
            except Exception as e:
                cleanup_error = CleanupError(
                    f"CSV cleanup failed: {e}", operation="close_csv"
                )
                self.write_diagnostic(
                    "cleanup_warning", level="WARNING", exception=cleanup_error,
                    traceback_text=traceback.format_exc()
                )
                self.OutputBox.append(f"Cleanup warning: {cleanup_error}")

        # Clean up worker
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

        if self.active_run_context:
            self.active_run_context.restore_parameter_paths()
        self.active_run_context = None
        self.active_params = None

    #Triggers when program experience crash
    def handle_test_error(self, exception, traceback_str):    #Shamman changes
        self.set_test_state(TestState.FAILED)
        self._notify_blynk_error(
            f"Test crashed: {type(exception).__name__}: {exception}"
        )
        self.write_run_log(f"ERROR: {exception}\n{traceback_str}")
        self.write_diagnostic(
            "test_failed",
            level="ERROR",
            exception=exception,
            traceback_text=traceback_str,
        )
        # Show error (same behavior as before)
        show_error_dialog(self, exception, traceback_str)

        # Log in output box (optional)
        self.OutputBox.append("❌ Test crashed due to an error")

    def _failed_test_finished(self):
        self.cleanup_test(reason="crash")

    def handle_test_warning(self, exception, traceback_str):
        self.write_run_log(f"WARNING: {exception}\n{traceback_str}")
        self.write_diagnostic(
            "cleanup_warning",
            level="WARNING",
            exception=exception,
            traceback_text=traceback_str,
        )
        self.OutputBox.append(f"Cleanup warning: {exception}")

    def test_finished(self):
        """Called when the test finishes (completed or aborted)"""
        self.set_test_state(TestState.COMPLETED)
        self._notify_blynk_completion()
        # Hide progress elements
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.abort_button.setVisible(False)
        self.abort_button.setText("Abort")
        self.abort_button.setEnabled(False)
        self.pause_button.setVisible(False)
        self.pause_button.setText("Pause")
        self.pause_button.setEnabled(False)
        self.show_plot_button.setVisible(False)
        self.show_plot_button.setText("Graph Plotting")
        self.show_plot_button.setEnabled(False)
        self.QPushButton_Widget1.setEnabled(True)
                 
        self.OutputBox.append("Test finished ✅")
        self._refresh_data_analysis()
                                                                     
        # Show Graph Image (only if completed successfully and not aborted)
        if not self.was_aborted:
            self.OutputBox.append("Test completed successfully ✅")
            
            # Show Graph Image only if completed successfully
            if self.checkbox_states.get("DataImage", False):
                try:
                    context = self.active_run_context
                    self.image_dialog = image_Window(
                        context.voltage_chart if context else None,
                        context.voltage_percentage_chart if context else None,
                    )
                    self.image_dialog.setModal(True)
                    self.image_dialog.show()
                except Exception as exception:
                    display_error = CleanupError(
                        f"Chart display failed: {exception}",
                        operation="show_chart",
                    )
                    self.write_diagnostic(
                        "chart_display_warning",
                        level="WARNING",
                        exception=display_error,
                        traceback_text=traceback.format_exc(),
                    )
                    self.OutputBox.append(f"Chart display warning: {display_error}")

        self.cleanup_test(reason="completed")
                 
        print_console_safe("Test operation finished")

    def _refresh_data_analysis(self):
        context = self.active_run_context
        if not context:
            return
        try:
            self.analysis_widget.refresh(
                context.output_root,
                export_directory=context.storage.raw,
            )
        except Exception as exception:
            self.OutputBox.append(f"Data analysis warning: {exception}")

    def test_aborted(self):
        """Called when the test is aborted"""
        self.set_test_state(TestState.ABORTED)
        # Hide progress elements
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.abort_button.setVisible(False)
        self.abort_button.setText("Abort")
        self.abort_button.setEnabled(False)
        self.pause_button.setVisible(False)
        self.pause_button.setText("Pause")
        self.pause_button.setEnabled(False)
        self.show_plot_button.setVisible(False)
        self.show_plot_button.setText("Graph Plotting")
        self.show_plot_button.setEnabled(False)
        self.QPushButton_Widget1.setEnabled(True)
        
        # Show abort message
        self.OutputBox.append("Test operation aborted ❌")
        self._refresh_data_analysis()

        self.cleanup_test(reason="aborted") #Shamman changes 
        
        print_console_safe("Test operation aborted")

    def show_popup_plot(self):
        self.dialog_tabs.setCurrentWidget(self.plot_window)

    '''def on_voltage_fail(self, error_value):     #Shamman changes
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Voltage Accuracy FAIL")
        msg.setText(
            f"Voltage accuracy test failed.\n\n"
            f"Error value: {error_value:.6f} V\n\n"
            "Do you want to continue the test?"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        response = msg.exec_()

        if response == QMessageBox.Yes:
            self.worker.decision_signal.emit(True)
        else:
            self.worker.decision_signal.emit(False)'''

class VoltageAccuracyPlotWindow(QWidget): #Shamman changes
    def __init__(self, measurement_name="Voltage"):
        super().__init__()
        self.measurement_name = measurement_name
        self.setWindowTitle(f"{measurement_name} Accuracy Monitor")
        self.resize(900, 600)

        self.x = []
        self.prog_data = []
        self.rb_data = []
        self.prog_up_data = []
        self.prog_low_data = []
        self.rb_up_data = []
        self.rb_low_data = []
        self.prog_perc_data = []
        self.rb_perc_data = []
        self.perc_up_data = []
        self.perc_low_data = []
        self._hover_proxies = []
        self._hover_controls = []
        self.run_state = "IDLE"
        self._last_measurement_text = None
        self._last_measurement_passed = None

        self._setup_ui()

    def reset(self, measurement_name="Voltage"):
        self.measurement_name = measurement_name
        self.x.clear()
        self.prog_data.clear()
        self.rb_data.clear()
        self.prog_up_data.clear()
        self.prog_low_data.clear()
        self.rb_up_data.clear()
        self.rb_low_data.clear()
        self.prog_perc_data.clear()
        self.rb_perc_data.clear()
        self.perc_up_data.clear()
        self.perc_low_data.clear()

        self.prog_plot.setTitle(
            f"Programming {measurement_name} Absolute Error"
        )
        self.rb_plot.setTitle(f"Readback {measurement_name} Absolute Error")
        self.prog_perc_plot.setTitle(
            f"Programming {measurement_name} Percentage Error (%)"
        )
        self.rb_perc_plot.setTitle(
            f"Readback {measurement_name} Percentage Error (%)"
        )
        self.status_label.setText("Status: Waiting for measurement")
        self.status_label.setStyleSheet(self._status_style("#404040"))
        self.run_state = "IDLE"
        self._last_measurement_text = None
        self._last_measurement_passed = None
        for curve in (
            self.programming_curve,
            self.prog_upper_boundary,
            self.prog_lower_boundary,
            self.readback_curve,
            self.rb_upper_boundary,
            self.rb_lower_boundary,
            self.programming_percentage_curve,
            self.prog_perc_upper_boundary,
            self.prog_perc_lower_boundary,
            self.readback_percentage_curve,
            self.rb_perc_upper_boundary,
            self.rb_perc_lower_boundary,
        ):
            curve.setData([], [])
        for _plot, _series, label, vertical_line, horizontal_line in self._hover_controls:
            label.hide()
            vertical_line.hide()
            horizontal_line.hide()

    def _setup_ui(self):
        layout = QGridLayout(self)

        self.status_label = QLabel("Status: Waiting for measurement")
        self.status_label.setStyleSheet(self._status_style("#404040"))
        layout.addWidget(self.status_label, 0, 0, 1, 2)

        # Programming plot
        self.prog_plot = pg.PlotWidget(
            title=f"Programming {self.measurement_name} Absolute Error"
        )
        self.prog_plot.addLegend(offset=(10, 10))
        self.programming_curve = self.prog_plot.plot(
            pen=pg.mkPen('r', width=3), symbol="o", symbolSize=6,
            name="Programming Error",
        )
        self.prog_upper_boundary = self.prog_plot.plot(
            pen=pg.mkPen("y", width=3), name="Upper Bound"
        )
        self.prog_lower_boundary = self.prog_plot.plot(
            pen=pg.mkPen("y", width=3, style=Qt.DashLine),
            name="Lower Bound",
        )
        layout.addWidget(self.prog_plot, 1, 0)

        # Readback plot
        self.rb_plot = pg.PlotWidget(
            title=f"Readback {self.measurement_name} Absolute Error"
        )
        self.rb_plot.addLegend(offset=(10, 10))
        self.readback_curve = self.rb_plot.plot(
            pen=pg.mkPen('b', width=3), symbol="o", symbolSize=6,
            name="Readback Error",
        )
        self.rb_upper_boundary = self.rb_plot.plot(
            pen=pg.mkPen("y", width=3), name="Upper Bound"
        )
        self.rb_lower_boundary = self.rb_plot.plot(
            pen=pg.mkPen("y", width=3, style=Qt.DashLine),
            name="Lower Bound",
        )
        layout.addWidget(self.rb_plot, 1, 1)

        # Programming Percentage Error plot
        self.prog_perc_plot = pg.PlotWidget(
            title=f"Programming {self.measurement_name} Percentage Error (%)"
        )
        self.prog_perc_plot.addLegend(offset=(10, 10))
        self.programming_percentage_curve = self.prog_perc_plot.plot(
            pen=pg.mkPen('r', width=3), symbol="o", symbolSize=6,
            name="Programming Error (%)",
        )
        self.prog_perc_upper_boundary = self.prog_perc_plot.plot(
            pen=pg.mkPen("y", width=3), name="Upper Bound (%)"
        )
        self.prog_perc_lower_boundary = self.prog_perc_plot.plot(
            pen=pg.mkPen("y", width=3, style=Qt.DashLine),
            name="Lower Bound (%)",
        )
        layout.addWidget(self.prog_perc_plot, 2, 0)
        
        # Readback Percentage Error plot
        self.rb_perc_plot = pg.PlotWidget(
            title=f"Readback {self.measurement_name} Percentage Error (%)"
        )
        self.rb_perc_plot.addLegend(offset=(10, 10))
        self.readback_percentage_curve = self.rb_perc_plot.plot(
            pen=pg.mkPen('b', width=3), symbol="o", symbolSize=6,
            name="Readback Error (%)",
        )
        self.rb_perc_upper_boundary = self.rb_perc_plot.plot(
            pen=pg.mkPen("y", width=3), name="Upper Bound (%)"
        )
        self.rb_perc_lower_boundary = self.rb_perc_plot.plot(
            pen=pg.mkPen("y", width=3, style=Qt.DashLine),
            name="Lower Bound (%)",
        )
        layout.addWidget(self.rb_perc_plot, 2, 1)

        for plot in (
            self.prog_plot,
            self.rb_plot,
            self.prog_perc_plot,
            self.rb_perc_plot,
        ):
            plot.showGrid(x=True, y=True, alpha=0.25)
            plot.setLabel("bottom", "Measurement Point")

        self.setLayout(layout)
        self._setup_hover_tools()

    @staticmethod
    def _status_style(background):
        return (
            "QLabel { "
            f"background:{background}; color:white; padding:8px; "
            "font-weight:bold; border-radius:4px; }"
        )

    def update_test_state(self, state):
        self.run_state = state.upper()
        if self._last_measurement_text:
            self.status_label.setText(
                f"{self.run_state} | {self._last_measurement_text}"
            )
        else:
            self.status_label.setText(f"Status: {self.run_state}")
        if state in {"paused", "pausing", "stopping"}:
            self.status_label.setStyleSheet(self._status_style("#b36b00"))
        elif state in {"failed", "aborted"}:
            self.status_label.setStyleSheet(self._status_style("#b22222"))
        elif state == "completed":
            self.status_label.setStyleSheet(self._status_style("#1b7f3a"))

    def update_measurement_status(self, measurement, point_number):
        status = "PASS" if measurement.passed else "FAIL"
        background = "#1b7f3a" if measurement.passed else "#b22222"
        self._last_measurement_text = (
            f"{status} | Point {point_number} | "
            f"Set {measurement.set_voltage:.6g} V, "
            f"{measurement.set_current:.6g} A | "
            f"Measured {measurement.programming_voltage:.6g} V | "
            f"Readback {measurement.readback_voltage:.6g} V, "
            f"{measurement.readback_current:.6g} A"
        )
        self._last_measurement_passed = measurement.passed
        self.status_label.setText(
            f"{self.run_state} | {self._last_measurement_text}"
        )
        self.status_label.setStyleSheet(self._status_style(background))

    def _setup_hover_tools(self):
        plot_series = (
            (
                self.prog_plot,
                (
                    ("Programming Error", self.prog_data),
                    ("Upper Bound", self.prog_up_data),
                    ("Lower Bound", self.prog_low_data),
                ),
            ),
            (
                self.rb_plot,
                (
                    ("Readback Error", self.rb_data),
                    ("Upper Bound", self.rb_up_data),
                    ("Lower Bound", self.rb_low_data),
                ),
            ),
            (
                self.prog_perc_plot,
                (
                    ("Programming Error (%)", self.prog_perc_data),
                    ("Upper Bound (%)", self.perc_up_data),
                    ("Lower Bound (%)", self.perc_low_data),
                ),
            ),
            (
                self.rb_perc_plot,
                (
                    ("Readback Error (%)", self.rb_perc_data),
                    ("Upper Bound (%)", self.perc_up_data),
                    ("Lower Bound (%)", self.perc_low_data),
                ),
            ),
        )

        for plot, series in plot_series:
            label = pg.TextItem(
                color="w",
                fill=pg.mkBrush(30, 30, 30, 220),
                anchor=(0, 1),
            )
            label.setZValue(100)
            label.hide()
            plot.addItem(label, ignoreBounds=True)

            vertical_line = pg.InfiniteLine(
                angle=90,
                movable=False,
                pen=pg.mkPen(180, 180, 180, 150),
            )
            horizontal_line = pg.InfiniteLine(
                angle=0,
                movable=False,
                pen=pg.mkPen(180, 180, 180, 150),
            )
            vertical_line.hide()
            horizontal_line.hide()
            plot.addItem(vertical_line, ignoreBounds=True)
            plot.addItem(horizontal_line, ignoreBounds=True)

            controls = (plot, series, label, vertical_line, horizontal_line)
            proxy = pg.SignalProxy(
                plot.scene().sigMouseMoved,
                rateLimit=60,
                slot=lambda event, controls=controls: self._update_hover(
                    event,
                    *controls,
                ),
            )
            self._hover_controls.append(controls)
            self._hover_proxies.append(proxy)

    @staticmethod
    def _format_hover_text(point_index, x_value, series):
        values = [f"Point: {x_value:g}"]
        for name, data in series:
            if point_index < len(data):
                values.append(f"{name}: {float(data[point_index]):.6g}")
        return "<br>".join(values)

    def _update_hover(
        self,
        event,
        plot,
        series,
        label,
        vertical_line,
        horizontal_line,
    ):
        scene_position = event[0] if isinstance(event, (tuple, list)) else event
        if (
            scene_position is None
            or not self.x
            or not plot.sceneBoundingRect().contains(scene_position)
        ):
            label.hide()
            vertical_line.hide()
            horizontal_line.hide()
            return

        view_box = plot.plotItem.vb
        nearest = None
        for point_index, x_value in enumerate(self.x):
            for _name, data in series:
                if point_index >= len(data):
                    continue
                y_value = float(data[point_index])
                point_position = view_box.mapViewToScene(
                    QPointF(float(x_value), y_value)
                )
                distance = (
                    (point_position.x() - scene_position.x()) ** 2
                    + (point_position.y() - scene_position.y()) ** 2
                ) ** 0.5
                if nearest is None or distance < nearest[0]:
                    nearest = (distance, point_index, float(x_value), y_value)

        if nearest is None or nearest[0] > 14:
            label.hide()
            vertical_line.hide()
            horizontal_line.hide()
            return

        _, point_index, x_value, y_value = nearest
        label.setHtml(self._format_hover_text(point_index, x_value, series))
        label.setPos(x_value, y_value)
        label.show()
        vertical_line.setPos(x_value)
        horizontal_line.setPos(y_value)
        vertical_line.show()
        horizontal_line.show()


    @pyqtSlot(float, float, float, float, float, float, float, float, float, float)
    def popup_plot(self, prog_err, rb_err, prog_up_bound, prog_low_bound, rb_up_bound, rb_low_bound, prog_percent, read_percent, perc_up_bound, perc_low_bound):
        i = len(self.x)
        self.x.append(i)
        self.prog_data.append(prog_err)
        self.prog_up_data.append(prog_up_bound)
        self.prog_low_data.append(prog_low_bound)
        self.rb_data.append(rb_err)
        self.rb_up_data.append(rb_up_bound)
        self.rb_low_data.append(rb_low_bound)
        self.prog_perc_data.append(prog_percent)
        self.rb_perc_data.append(read_percent)
        self.perc_up_data.append(perc_up_bound)
        self.perc_low_data.append(perc_low_bound)

        self.programming_curve.setData(self.x, self.prog_data)
        self.prog_upper_boundary.setData(self.x, self.prog_up_data)
        self.prog_lower_boundary.setData(self.x, self.prog_low_data)
        self.readback_curve.setData(self.x, self.rb_data)
        self.rb_upper_boundary.setData(self.x, self.rb_up_data)
        self.rb_lower_boundary.setData(self.x, self.rb_low_data)
        self.programming_percentage_curve.setData(self.x, self.prog_perc_data)
        self.prog_perc_upper_boundary.setData(self.x, self.perc_up_data)
        self.prog_perc_lower_boundary.setData(self.x, self.perc_low_data)
        self.readback_percentage_curve.setData(self.x, self.rb_perc_data)
        self.rb_perc_upper_boundary.setData(self.x, self.perc_up_data)
        self.rb_perc_lower_boundary.setData(self.x, self.perc_low_data)

class AdvancedSettings(QDialog):
    """This class is to configure the Advanced Settings when conducting voltage measurements,
    It prompts a secondary dialogue for users to customize more advanced parametes such as
    aperture, range, AutoZero, input impedance etc.
    """

    def __init__(self,parameters):
        """Method defining the signals, slots and widgets for Advaced Settings of Voltage Measurements"""
        super().__init__()
        self.params = parameters

        self.setWindowTitle("Advanced Window (Voltage)")

        # Create a font with the desired size
        desp_font = QFont("Arial", 20)  # Set font to Arial with size 12
        input_font = QFont("Arial", 15)  # Set font for input fields (smaller size)

        QPushButton_Widget = QPushButton()
        QPushButton_Widget.setText("Confirm")
        layout1 = QFormLayout()

        Desp1 = QLabel("DMM Settings:")
        Desp2 = QLabel("PSU Settings:")

        # Apply font size to the labels
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)

        QLabel_Range = QLabel("DC Voltage Range")
        QLabel_Aperture = QLabel("NPLC / PLC")
        QLabel_AutoZero = QLabel("Auto Zero Function")
        QLabel_InputZ = QLabel("Input Impedance")
        QLabel_UpTime = QLabel("Programming Settling Time (UP) (in ms)")
        QLabel_DownTime = QLabel("Programming Setting Time (Down) (in ms)")

        # Apply font to the other labels
        QLabel_Range.setFont(desp_font)
        QLabel_Aperture.setFont(desp_font)
        QLabel_AutoZero.setFont(desp_font)
        QLabel_InputZ.setFont(desp_font)
        QLabel_UpTime.setFont(desp_font)
        QLabel_DownTime.setFont(desp_font)

        self.QComboBox_Range = QComboBox()
        self.QComboBox_Aperture = QComboBox()
        self.QComboBox_AutoZero = QComboBox()
        self.QComboBox_InputZ = QComboBox()
        self.QLineEdit_UpTime = QLineEdit()
        self.QLineEdit_DownTime = QLineEdit()

        self.QComboBox_Range.addItems(["Auto", "100mV", "1V", "10V", "100V", "1kV"])
        # Time Value: "0.001", "0.002", "0.006", 
        self.QComboBox_Aperture.addItems(["0.02", "0.06", "0.2", "1", "10", "100"])
        self.QComboBox_AutoZero.addItems(["ON", "OFF"])
        self.QComboBox_InputZ.addItems(["10M", "Auto"])

        # Apply font size to combo boxes
        self.QComboBox_Range.setFont(input_font)
        self.QComboBox_Aperture.setFont(input_font)
        self.QComboBox_AutoZero.setFont(input_font)
        self.QComboBox_InputZ.setFont(input_font)

        # Apply font size to line edits
        self.QLineEdit_UpTime.setFont(input_font)
        self.QLineEdit_DownTime.setFont(input_font)

        layout1.addRow(Desp1)
        layout1.addRow(QLabel_Range, self.QComboBox_Range)
        layout1.addRow(QLabel_Aperture, self.QComboBox_Aperture)
        layout1.addRow(QLabel_AutoZero, self.QComboBox_AutoZero)
        layout1.addRow(QLabel_InputZ, self.QComboBox_InputZ)
        layout1.addRow(Desp2)
        layout1.addRow(QLabel_UpTime, self.QLineEdit_UpTime)
        layout1.addRow(QLabel_DownTime, self.QLineEdit_DownTime)

        # Adding the button at the bottom
        layout1.addRow(QPushButton_Widget)

        self.setLayout(layout1)

        self.QComboBox_Range.setCurrentText(self.params.Range)
        self.QComboBox_Aperture.setCurrentText(self.params.Aperture)
        self.QComboBox_AutoZero.setCurrentText(self.params.AutoZero)
        self.QComboBox_InputZ.setCurrentText(self.params.inputZ)
        #Uptime and Downtime Not Setting Yet
        self.QLineEdit_UpTime.setText(self.params.UpTime)
        self.QLineEdit_DownTime.setText(self.params.DownTime)

        # Connect the button to close the window
        # Accept variable change and close using super.accept() instead of self.close()
        QPushButton_Widget.clicked.connect(self.on_ok)

        # Connect the signals for changes in the fields (if necessary)
        self.QComboBox_Range.currentTextChanged.connect(self.RangeChanged)
        self.QComboBox_Aperture.currentTextChanged.connect(self.ApertureChanged)
        self.QComboBox_AutoZero.currentTextChanged.connect(self.AutoZeroChanged)
        self.QComboBox_InputZ.currentTextChanged.connect(self.InputZChanged)
        self.QLineEdit_UpTime.textEdited.connect(self.UpTimeChanged)
        self.QLineEdit_DownTime.textEdited.connect(self.DownTimeChanged)

    def RangeChanged(self, s):
        self.params.Range = s

    def ApertureChanged(self, s):
        self.params.Aperture = s

    def AutoZeroChanged(self, s):
        self.params.AutoZero = s

    def InputZChanged(self, s):
        self.params.inputZ = s

    def UpTimeChanged(self, s):
        self.params.UpTime = s

    def DownTimeChanged(self, s):
        self.params.DownTime = s

    def on_ok(self):
        super().accept()

class ACSourceSetting(QDialog):

    """Collect AC-source settings without energizing the hardware."""

    def __init__(self,parameters):
        super().__init__()

        self.params = parameters

        self.setWindowTitle("AC Source Configuration")

        self.QPushButton_RunAC_Widget = QPushButton("Save Settings")

        QLabel_ACSource_VisaAddress = QLabel()
        QLabel_AC_CurrentLimit = QLabel()
        QLabel_AC_VoltageOutput = QLabel()
        QLabel_Frequency = QLabel()

        QLabel_ACSource_VisaAddress.setText("Visa Address (AC):")
        QLabel_AC_CurrentLimit.setText("AC Current Limit")
        QLabel_AC_VoltageOutput.setText("AC Voltage Output to DUT")
        QLabel_Frequency.setText("AC Frequency Output")

        self.QComboBox_ACSource_VisaAddress = QComboBox()
        self.QLineEdit_AC_CurrentLimit = QLineEdit(str(self.params.AC_CurrentLimit))
        self.QLineEdit_AC_VoltageOutput = QLineEdit(str(self.params.AC_VoltageOutput))
        self.QLineEdit_Frequency = QLineEdit(str(self.params.Frequency))

        self.QComboBox_ACSource_VisaAddress.clear()
        discovery = GetVisaSCPIResources()
        self.visaIdList = discovery.addresses
        self.nameList = discovery.identities
        instrument_roles = discovery.roles
        self.QComboBox_ACSource_VisaAddress.addItems(
            [str(address) for address in self.visaIdList]
        )
        configured_address = str(self.params.ACSource or "").strip()
        if configured_address and configured_address not in self.visaIdList:
            self.QComboBox_ACSource_VisaAddress.addItem(configured_address)

        if 'ACSource' in instrument_roles:
            configured_address = instrument_roles['ACSource']
        if configured_address:
            self.QComboBox_ACSource_VisaAddress.setCurrentText(configured_address)
    
        AC_Setting_Widget = QWidget()
        AC_Setting_Layout = QFormLayout(AC_Setting_Widget)
        AC_Setting_Layout.addRow(QLabel_ACSource_VisaAddress, self.QComboBox_ACSource_VisaAddress)
        AC_Setting_Layout.addRow(QLabel_AC_CurrentLimit, self.QLineEdit_AC_CurrentLimit)
        AC_Setting_Layout.addRow(QLabel_AC_VoltageOutput, self.QLineEdit_AC_VoltageOutput)
        AC_Setting_Layout.addRow(QLabel_Frequency, self.QLineEdit_Frequency)
        AC_Setting_Layout.addRow(self.QPushButton_RunAC_Widget)

        Main_Layout = QHBoxLayout()
        Main_Layout.addWidget(AC_Setting_Widget)
        self.setLayout(Main_Layout)
        
        self.QPushButton_RunAC_Widget.clicked.connect(self.save_settings)

    def save_settings(self):
        address = self.QComboBox_ACSource_VisaAddress.currentText().strip()
        if not address:
            QMessageBox.warning(self, "AC Source", "Select an AC source VISA address")
            return
        values = {}
        for name, field in (
            ("current limit", self.QLineEdit_AC_CurrentLimit),
            ("output voltage", self.QLineEdit_AC_VoltageOutput),
            ("frequency", self.QLineEdit_Frequency),
        ):
            try:
                value = float(field.text())
            except ValueError:
                QMessageBox.warning(self, "AC Source", f"{name.title()} must be numeric")
                return
            if value <= 0:
                QMessageBox.warning(
                    self,
                    "AC Source",
                    f"{name.title()} must be greater than zero",
                )
                return
            values[name] = value

        self.params.ACSource = address
        self.params.AC_CurrentLimit = values["current limit"]
        self.params.AC_VoltageOutput = values["output voltage"]
        self.params.Frequency = values["frequency"]
        self.accept()
