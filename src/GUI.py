"""Main Module that runs the Graphical User Interface (GUI) that is the main point of interaction between user and the program"""

import sys
import  shutil
import traceback
import os
import pyvisa
from io import StringIO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

from tkinter import Tk, filedialog
import tkinter as tk
from tkinter import ttk
from time import sleep

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore  import *

#Add this to point to project folder -> To read the Library folder files inside DUT_Test.py, data.py...
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from DUT_Test_Scripts.DUT_Test import (
    dictGenerator,
    VisaResourceManager,
    LoadRegulation,
    RiseFallTime,
    PowerMeasurement,
    OVP_Test,
    NewVoltageMeasurement,
    NewCurrentMeasurement,
    NewLoadRegulation,
    LineRegulation,
    ProgrammingResponse,
    OCP_Activation_Time,
    OCP_Accuracy,
    ActivateAC,
    RESET,
)

from DUT_Test_Scripts.DUT_screenshot import ScreenShotDialog


from DUT_Test_Scripts.Hornbill_DUT_Test_With_ELoad import (
    HornbillVoltageMeasurementwithELoad,)

from DUT_Test_Scripts.Hornbill_DUT_Test_No_ELoad import (
    HornbillVoltageMeasurementNoELoad,)

from DUT_Test_Scripts.EDU36311A_DUT_Test_No_Load import (
    EDU36311AVoltageMeasurementNoELoad,)
#########################################################################################
from DUT_Test_Scripts.Dolphin_DUT_Test_With_ELoad_With_DMM import *

from DUT_Test_Scripts.Dolphin_DUT_Test_No_ELoad_With_DMM import *

from DUT_Test_Scripts.Dolphin_DUT_Test_With_ELoad_No_DMM import *

from DUT_Test_Scripts.Dolphin_DUT_Test_No_ELoad_No_DMM import *
##########################################################################################

from data import *
from xlreport import *
from xlreportpower import*

from External_Auxiliary_Equipment.Relay_Control import *

desp_font = QFont("Times New Roman", 14, QFont.Bold) 
AdvancedSettingsList = []

#############################################################################
def show_error_dialog(parent, e, traceback_str=None):
    from PyQt5.QtWidgets import QMessageBox, QFileDialog

    if traceback_str is None:
        import traceback
        traceback_str = traceback.format_exc()

    print("=== CRASH LOG ===")
    print(traceback_str)

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("Error")
    msg_box.setText(str(e))
    msg_box.setInformativeText("Do you want to save the crash log?")
    msg_box.setDetailedText(traceback_str)
    msg_box.setStandardButtons(QMessageBox.Save | QMessageBox.Close)

    ret = msg_box.exec_()

    if ret == QMessageBox.Save:
        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Save Crash Log",
            "crash_log.txt",
            "Text Files (*.txt)"
        )
        if file_path:
            with open(file_path, "w") as f:
                f.write(traceback_str)

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller exe."""
    if hasattr(sys, "_MEIPASS"):  # Running in exe
        return str(Path(sys._MEIPASS) / relative_path)
    return str(Path(__file__).resolve().parent.parent / relative_path)

"""def GetVisaSCPIResources():
    # Enumerate all resources VISA finds
    rm = pyvisa.ResourceManager()
    resourceList = rm.list_resources()
    availableVisaIdList = []
    availableNameList = []

    # Go through the list and query *IDN? to identify the instruments
    for i in range(len(resourceList)):
        resourceReply = ''
        try:
            if resourceList[i][:4] == 'ASRL':  # Check for serial resource
                instrument = rm.open_resource(
                    resourceList[i],
                    timeout=20000,  # Set timeout directly here
                    access_mode=1   # Optional: Lock access to the resource
                )
            else:
                instrument = rm.open_resource(resourceList[i])
                instrument.timeout = 20000  # Set timeout for other resources

            # Query the *IDN? command to identify the instrument
            resourceReply = instrument.query('*IDN?').upper()

            if resourceReply:  # Add to the lists if response is valid
                availableVisaIdList.append(resourceList[i])
                availableNameList.append(resourceReply)
        except Exception as e:
            print(f"Error querying resource {resourceList[i]}: {e}")
            pass  # Ignore errors and continue to the next resource

    return availableVisaIdList, availableNameList"""

"""def GetVisaSCPIResources():
    # Return a list of only *connected* USB VISA instruments.
    rm = pyvisa.ResourceManager()
    resource_list = rm.list_resources()

    available_visa_ids = []
    available_names = []

    for resource in resource_list:
        # Only look for USB instruments (skip GPIB, TCPIP, etc.)
        if not resource.startswith("USB"):
            continue

        try:
            # Try to open the resource
            instrument = rm.open_resource(resource)
            instrument.timeout = 2000  # shorter timeout for faster scanning

            # Check connectivity with *IDN? (identify command)
            idn = instrument.query("*IDN?").strip().upper()

            # Only add if response looks valid
            if idn and "," in idn:
                available_visa_ids.append(resource)
                available_names.append(idn)

        except pyvisa.errors.VisaIOError as e:
            # Filter out common errors for disconnected devices
            if e.error_code in (-1073807343, -1073807339, -1073807298):
                # -1073807343: Resource not found
                # -1073807339: Timeout
                # -1073807298: I/O error
                continue  # Skip silently
            else:
                print(f"VISA I/O Error ({e.error_code}) on {resource}: {e}")
                continue
        except Exception as e:
            print(f"Unexpected error with {resource}: {e}")
            continue

    return available_visa_ids, available_names"""


def load_model_role_map(filename="instrument_role.txt"):
    """Read instrument model-role pairs from a text file."""
    model_role_map = {}
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(base_dir)
        filepath = os.path.join(parent_dir, "Instrument_Config_Files", "instrument_role.txt")

        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # skip comments or blank lines
                if ":" in line:
                    model, role = [x.strip() for x in line.split(":", 1)]
                    model_role_map[model] = role
                    print(f"   {model} → {role}")
    except Exception as e:
        print(f"Error reading {filename}: {e}")

    return model_role_map
    
def GetVisaSCPIResources():
    """Return connected USB VISA instruments and map them to roles."""
    rm = pyvisa.ResourceManager()
    resource_list = rm.list_resources()

    available_visa_ids = []
    available_names = []
    instrument_roles = {}

    model_role_map = load_model_role_map()

    for resource in resource_list:
        # Only look for USB instruments (skip GPIB, TCPIP, etc.)
        if not resource.startswith("USB"):
            continue

        try:
            # Try to open the resource
            instrument = rm.open_resource(resource)
            instrument.timeout = 2000  # shorter timeout for faster scanning

            # Identify instrument
            idn = instrument.query("*IDN?").strip().upper()

            if idn and "," in idn:
                available_visa_ids.append(resource)
                available_names.append(idn)

                # Match model to role
                for model, role in model_role_map.items():
                    if model in idn:
                        instrument_roles[role] = resource
                        break

        except pyvisa.errors.VisaIOError as e:
            if e.error_code in (-1073807343, -1073807339, -1073807298):
                continue  # Ignore common disconnect/timeout errors
            else:
                print(f"VISA I/O Error ({e.error_code}) on {resource}: {e}")
                continue
        except Exception as e:
            print(f"Unexpected error with {resource}: {e}")
            continue

    return available_visa_ids, available_names, instrument_roles
def NewGetVisaSCPIResources():
    """Use to auto sort the Visa Address to PSU, ELoad... when it match the name in model_role_map"""
    # Initialize VISA resource manager
    rm = pyvisa.ResourceManager()
    resourceList = rm.list_resources()

    model_role_map = load_model_role_map()  # Load mapping from file
    availableVisaIdList = []
    availableNameList = []
    instrument_roles = {}

    # Go through each connected resource and query *IDN?
    for res in resourceList:
        try:
            if res[:4] == 'ASRL':  # For serial resources (e.g., RS-232)
                instrument = rm.open_resource(res, timeout=2000, access_mode=1)
                resourceReply = instrument.query('*IDN?').upper()
            else:  # Other resource types (GPIB, USB, etc.)
                instrument = rm.open_resource(res)
                resourceReply = instrument.query('*IDN?').upper()

            # If there’s a response, we check against the known model-to-role map
            if resourceReply:
                availableVisaIdList.append(res)
                availableNameList.append(resourceReply)

                # Try to match the *IDN? response with a known model
                for model, role in model_role_map.items():
                    if model in resourceReply:
                        instrument_roles[role] = res
                        break  # Stop after matching the first role

        except Exception as e:
            #print(f"Error with resource {res}: {e}")
            continue  # Continue checking the next resource if there's an error

    return availableVisaIdList, availableNameList, instrument_roles

# Scroll Area
def scroll_area(self,layout):
    # Create a QWidget that will be the content inside the QScrollArea
    content_widget = QWidget()
    content_widget.setLayout(layout)

    # Create the QScrollArea
    scroll_area = QScrollArea()
    scroll_area.setWidget(content_widget)
    scroll_area.setWidgetResizable(True)

    self.setLayout(QVBoxLayout())
    self.layout().addWidget(scroll_area)

    return scroll_area

# Disable wheel move when hover over combobox
class ComboBoxWheelFilter(QObject):
    def eventFilter(self, obj, event):
        if isinstance(obj, QComboBox) and event.type() == event.Wheel:
            if not obj.view().isVisible():  # Prevent scroll if dropdown is closed
                return True  # Block the event
        return super().eventFilter(obj, event)

###########################################################################
#------------------------- Main GUI window with three tab (Bundled Test, Screenshot and List of Standalone Test)--------------
class MainWindow(QMainWindow):
    """Main window with controls for displaying DUT tests."""
    
    def __init__(self):
        super().__init__()
        self.params = Parameters() 
        
        # Initialization/Font Set-Up
        self.setWindowTitle("DUT TEST GUI")
        self.resize(1000, 700) 
        self.image_window = None
        self.setWindowFlags(Qt.Window)
        window_font = QFont("Arial", 12)
        self.setFont(window_font)

        # Track current tab index
        self.CurrentTab = 0

        # Add test options for the test list
        self.test_options = [
            ("Voltage Measurement", "Precise voltage measurement dialog"),
            ("Current Measurement", "Precise current measurement dialog"),
            ("CV Load Regulation", "Constant Voltage load regulation testing"),
            ("CC Load Regulation", "Constant Current load regulation testing"),
            ("Transient Recovery Time", "Measure transient response recovery time"),
            ("Transient Recovery Time Using Current Probe", "Measure transient response recovery time using current probe"),
            ("Programming Speed", "Test programming speed capabilities"),
            ("Power Measurement", "Comprehensive power measurement dialog"),
            ("Bundle Measurement - Voltage", "Specialized bundle voltage measurement"),
            ("Bundle Measurement - Current/Power", "Bundle current and power measurement"),
            ("AC Source Settings", "Simple Configuration of AC Source")
        ]

        #Add qdialog to be opened when test list selected
        self.dialog_names = [
            "Voltage Measurement Dialog",
            "Current Measurement Dialog",
            "CV Load Regulation Dialog",
            "CC Load Regulation Dialog", 
            "Transient Recovery Time Dialog",
            "Transient Recovery Time Using Current Probe Dialog",
            "Programming Speed Dialog",
            "Power Measurement Dialog",
            "Bundle Measurement Voltage Dialog",
            "Bundle Measurement Current/Power Dialog",
            "AC Source Setting Dialog"
        ]
        
        #Show the tab on the Main Window
        self.initTabs()

        # Main layout components
        QLabel_Widget = QLabel("Choose Test:")
        QLabel_Widget.setFont(QFont("Arial", 14, QFont.Bold))
        QLabel_Widget.setStyleSheet("color: #2c3e50; margin: 10px;")
        
        self.QButton_Widget = QPushButton("Confirm Selection")
        self.QButton_Widget.setFont(QFont("Arial", 14, QFont.Bold))
        self.QButton_Widget.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)

        Main_Window_Layout = QVBoxLayout()
        Main_Window_Layout.addWidget(QLabel_Widget)
        Main_Window_Layout.addWidget(self.tab_widget)
        Main_Window_Layout.addWidget(self.QButton_Widget)
        Main_Window_Layout.setSpacing(10)
        Main_Window_Layout.setContentsMargins(20, 20, 20, 20)

        # Main page
        self.page_home = QWidget()
        self.page_home.setLayout(Main_Window_Layout)
        self.page_home.setStyleSheet("background-color: #f8f9fa;")
        self.setCentralWidget(self.page_home)
        
        self.tab_widget.currentChanged.connect(self.currentTabChanged)
        self.QButton_Widget.clicked.connect(self.PushBtnClicked)

    def initTabs(self):
        """Initialize tab widgets - merged from tab class"""
        # Create the main tab widget
        self.tab_widget = QTabWidget()
        
        # Initialize tab widgets
        self.tab_NewBundle = QWidget()
        self.tab_ScreenShot = QWidget()
        self.tab_TestList = QWidget()

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.tab_NewBundle, "Bundle Test")
        self.tab_widget.addTab(self.tab_ScreenShot, "Screenshot")
        self.tab_widget.addTab(self.tab_TestList, "Test Selection")

        # Set larger font for tab labels
        tab_font = QFont("Arial", 14)
        self.tab_widget.setFont(tab_font)

        # Initialize UI for each tab
        self.NewBundleUI()
        self.ScreenShotUI()
        self.TestListUI()
  
    #################UI Settings for three tabs#########################
    def setupTabUI(self, tab, image_path, description, tab_index, tab_text, label_size=(800, 600)):
        """Setup UI for image-based tabs"""
        # Create a placeholder for image
        try:
            pixmap = QPixmap(image_path).scaled(*label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pixmap = pixmap.scaled(1280, 720, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except:
            # Create a placeholder pixmap if image doesn't exist
            pixmap = QPixmap(800, 600)
            pixmap.fill(Qt.lightGray)

        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("border: 2px solid gray; background-color: #f0f0f0;")
        label.setText(f"Image Placeholder\n{image_path}" if pixmap.isNull() else "")

        # Set font for the description label
        description_font = QFont("Arial", 16)
        description_label = QLabel(description)
        description_label.setFont(description_font)
        description_label.setAlignment(Qt.AlignCenter)
        description_label.setWordWrap(True)
    
        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(description_label)
        tab.setLayout(layout)
        
        self.tab_widget.setTabText(tab_index, tab_text)

    def NewBundleUI(self):
        """Setup Bundle Test tab"""
        self.setupTabUI(
            self.tab_NewBundle,
            "setup_images/2.png", 
            "Test GUI for Bundle Measurement\n\nThis tab provides voltage and current testing capabilities for DUT bundles.",
            0,
            "Bundle Test (Voltage/Current)"
        )

    def ScreenShotUI(self):
        """Setup Screenshot tab"""
        self.setupTabUI(
            self.tab_ScreenShot,
            "setup_images/7.png",
            "Instrument Display Capture\n\nCapture screenshots of the DUT instrument display for documentation and analysis.",
            1,
            "Instrument ScreenShot"
        )

    def TestListUI(self):
        """Create the third tab with a list of available test dialogs"""
        layout = QVBoxLayout()
        
        # Title label
        title_label = QLabel("Available Test Dialogs")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        
        # Description label
        desc_label = QLabel("Select from the list below to open different test dialogs:")
        desc_label.setFont(QFont("Arial", 12))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #34495e; margin: 5px;")
        
        # Create list widget
        self.test_list = QListWidget()
        self.test_list.setFont(QFont("Arial", 11))
        self.test_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #6145FF;
            }
        """)
        
        for i, (title, description) in enumerate(self.test_options):
            item = QListWidgetItem()
            item.setText(f"{title}\n{description}")
            item.setData(Qt.UserRole, i + 2)  # Store the tab index
            self.test_list.addItem(item)
        
        # Connect double-click signal
        self.test_list.itemDoubleClicked.connect(self.on_test_selected)
        
        # Add select button
        select_btn = QPushButton("Open Selected Test")
        select_btn.setFont(QFont("Arial", 12, QFont.Bold))
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        select_btn.clicked.connect(self.on_select_button_clicked)
        
        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addWidget(self.test_list)
        layout.addWidget(select_btn)
        
        self.tab_TestList.setLayout(layout)
        self.tab_widget.setTabText(2, "Test Selection")

    ##################Interactive Action #################################
    def on_test_selected(self, item):
        """Handle test selection from list"""
        test_index = item.data(Qt.UserRole)
        self.open_test_dialog(test_index)

    def on_select_button_clicked(self):
        """Handle select button click"""
        current_item = self.test_list.currentItem()
        if current_item:
            self.on_test_selected(current_item)

    def open_test_dialog(self, test_index):
        """Open the selected test dialog"""
        self.open_test_by_index(test_index)
    
    def currentTabChanged(self, index):
        """Slot to update the current tab index."""
        self.CurrentTab = index
        print(f"Current tab changed to: {index}")

    def PushBtnClicked(self):
        """Open the appropriate dialog based on the selected tab."""
        if self.CurrentTab < 2:  # For first two tabs, use existing logic
            self.open_test_by_index(self.CurrentTab)
        else:  # For third tab, get selection from list
            if hasattr(self, 'test_list'):
                current_item = self.test_list.currentItem()
                if current_item:
                    test_index = current_item.data(Qt.UserRole)
                    self.open_test_by_index(test_index)
                else:
                    print("Please select a test from the list first.")

    def open_test_by_index(self, index):
        """Open dialog based on index - placeholder for actual dialog implementations"""

        if 0 <= index < 13:

            # Handle different dialog types based on index
            if index == 0:  # Bundle Test
                self.bundle_dialog = AllTestMeasurement()
                self.bundle_dialog.show()
            elif index == 1:  # Screenshot Dialog
                self.screenshot_dialog = ScreenShotDialog(self)
                self.screenshot_dialog.show()
            elif index == 2:  # Voltage Measurement Dialog
                self.voltage_dialog = VoltageMeasurementDialog()# Create voltage dialog instance
                self.voltage_dialog.show()  # Use exec_() for modal dialog or show() for non-modal
            elif index == 3:  # Current Measurement Dialog
                self.current_dialog = CurrentMeasurementDialog()
                self.current_dialog.show()
            elif index == 4:  # CV Load Regulation Dialog
                self.CV_load_dialog = CV_LoadRegulationDialog()
                self.CV_load_dialog.show()
            elif index == 5:  # CC Load Regulation Dialog
                self.CC_load_dialog = CC_LoadRegulationDialog()
                self.CC_load_dialog.show()
            elif index == 6:  # Transient Recovery Time Dialog
                self.transient_load_dialog = TransientRecoveryTime()
                self.transient_load_dialog.show()
            elif index == 7:  # Transient Recovery Time Using Current Probe Dialog
                self.transient_current_probe_dialog = TransientRecoveryTimeWithCurrentSensor()
                self.transient_current_probe_dialog.show()
            elif index == 8:  # Programming Speed Dialog
                self.programming_speed_dialog = ProgrammingSpeed()
                self.programming_speed_dialog.show()
            elif index == 9:  # Power Measurement Dialog
                self.power_dialog = PowerMeasurementDialog()
                self.power_dialog.show()
            elif index == 10:  # Bundle Measurement Voltage Dialog
                self.bundle_voltage_dialog = BundleMeasurementVoltageDialog()
                self.bundle_voltage_dialog.show()
            elif index == 11:  # Bundle Measurement Current/Power Dialog
                self.bundle_current_dialog = BundleMeasurementCurrentandPowerDialog()
                self.bundle_current_dialog.show()
            elif index == 12:  # AC Source Dialog
                self.ac_source_dialog = ACSourceSetting(self.params)
                self.ac_source_dialog.show()
        else:
            print(f"Invalid dialog index: {index}")

#######------------------------Standalone Test Scripts in Tab 3-----------------------------#####################
class VoltageMeasurementDialog(QDialog):
    """Class for configuring the voltage measurement DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py


    """
    def __init__(self):
        """Method where Widgets, Signals and Slots are defined in the GUI for Voltage Measurement"""
        super().__init__()
        self.DATA_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/data.csv"  # or use a dynamic path if needed
        self.IMAGE_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/images/Chart.png"
        self.ERROR_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/error.csv"
        self.image_dialog = None
        

        self.Power_Rating = "6000"
        self.Current_Rating = "24"
        self.Voltage_Rating = "800"
        self.Power = "2000"
        self.currloop = "1"
        self.voltloop = "1"
        self.estimatetime = "0"
        self.readbackvoltage = "0"
        self.readbackcurrent = "0"
        self.savelocation = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"
        self.noofloop = "1"
        self.updatedelay = "3.0"
        self.unit = "VOLTAGE"
        self.Programming_Error_Offset = "0.0003"
        self.Programming_Error_Gain = "0.0003"
        self.Readback_Error_Offset = "0.0003"
        self.Readback_Error_Gain = "0.0003"
        self.minCurrent = "0"
        self.maxCurrent = "24"
        self.current_step_size = "1"
        self.minVoltage = "0"
        self.maxVoltage = "800"
        self.voltage_step_size = "80"
        self.PSU = "USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"
        self.OSC = "USB0::0x0957::0x17B0::MY52060151::0::INSTR"
        self.DMM = "USB0::0x2A8D::0x1601::MY60094787::0::INSTR"
        self.ELoad = "USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"
        self.OSC_Channel = "1"
        self.DMM_Instrument = "Keysight"
        self.DUT = "Others"

        self.PSU_Channel = "1"
        self.ELoad_Channel = "1"
        self.setFunction = "Current" #Set Eload in CC Mode
        self.VoltageRes = "DEF"
        self.VoltageSense = "INT"
        self.SPOperationMode = "Independent"

        self.relay_voltage = "None"

        self.checkbox_data_Report = 2
        self.checkbox_data_Image = 2
        self.checkbox_test_VoltageAccuracy = 2
        self.checkbox_test_VoltageLoadRegulation = 2
        self.checkbox_test_TransientRecovery = 2

        self.Range = "Auto"
        self.Aperture = "0.2"
        self.AutoZero = "ON"
        self.inputZ = "ON"
        self.UpTime = "50"
        self.DownTime = "50"

        self.Channel_CouplingMode = "AC"
        self.Trigger_CouplingMode = "DC"
        self.Trigger_Mode = "EDGE"
        self.Trigger_SweepMode = "NORMAL"
        self.Trigger_SlopeMode = "EITHer"
        self.TimeScale = "0.01"
        self.VerticalScale = "0.00001"
        self.I_Step = ""
        self.V_Settling_Band = "0.8"
        self.T_Settling_Band = "0.001"
        self.Probe_Setting = "X10"
        self.Acq_Type = "AVERage"

        self.checkbox_SpecialCase = 2
        self.checkbox_NormalCase = 2
        
        #Create Voltage Window
        self.setWindowTitle("Voltage Measurement")
        self.image_window = None
        self.setWindowFlags(Qt.Window)

        #Create find button 
        QPushButton_Widget0 = QPushButton()
        QPushButton_Widget0.setText("Save Path")
        QPushButton_Widget1 = QPushButton()
        QPushButton_Widget1.setText("Execute Test")
        QPushButton_Widget2 = QPushButton()
        QPushButton_Widget2.setText("Advanced Settings")
        QPushButton_Widget3 = QPushButton()
        QPushButton_Widget3.setText("Estimate Data Collection Time")
        QPushButton_Widget4 = QPushButton()
        QPushButton_Widget4.setText("Find Instruments")
        self.QCheckBox_Report_Widget = QCheckBox()
        self.QCheckBox_Report_Widget.setText("Generate Excel Report")
        self.QCheckBox_Report_Widget.setCheckState(Qt.Checked)
        self.QCheckBox_Image_Widget = QCheckBox()
        self.QCheckBox_Image_Widget.setText("Show Graph")
        self.QCheckBox_Image_Widget.setCheckState(Qt.Checked)
        QCheckBox_Lock_Widget = QCheckBox()
        QCheckBox_Lock_Widget.setText("Lock Widget")

        #Output Display
        self.OutputBox = QTextBrowser()
        self.OutputBox.append(f"{my_result.getvalue()}")
        self.OutputBox.append("")  # Empty line after each append

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

        Desp0.setFont(desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp5.setFont(desp_font)
        Desp6.setFont(desp_font)
        Desp7.setFont(desp_font)
        Desp8.setFont(desp_font)

        Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Voltage Sweep:")
        Desp4.setText("Current Sweep:")
        Desp5.setText("No. of Collection:")
        Desp6.setText("Rated Power [W]")
        Desp7.setText("Maximum Current")
        Desp8.setText("External Auxiliary Equipment:")

        #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location/Output Wndow:")

        # Connections section
        QLabel_PSU_VisaAddress = QLabel()
        QLabel_DMM_VisaAddress = QLabel()
        QLabel_ELoad_VisaAddress = QLabel()
        QLabel_DMM_Instrument = QLabel()
        QLabel_DUT = QLabel()
        QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        QLabel_DMM_VisaAddress.setText("Visa Address (DMM):")
        QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DMM_Instrument.setText("Instrument Type (DMM):")
        QLabel_DUT.setText("DUT:")

        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_DMM_VisaAddress = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        self.QComboBox_DMM_Instrument = QComboBox()
        self.QComboBox_DUT = QComboBox()

        # General Settings
        QLabel_Voltage_Res = QLabel()
        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
        QLabel_Programming_Error_Gain = QLabel()
        QLabel_Programming_Error_Offset = QLabel()
        QLabel_Readback_Error_Gain = QLabel()
        QLabel_Readback_Error_Offset = QLabel()

        QLabel_Voltage_Res.setText("Voltage Resolution (DMM):")
        QLabel_set_PSU_Channel.setText("Set PSU Channel:")
        QLabel_set_ELoad_Channel.setText("Set Eload Channel:")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        QLabel_Programming_Error_Gain.setText("Programming Desired Specification (Gain):")
        QLabel_Programming_Error_Offset.setText("Programming Desired Specification (Offset):")
        QLabel_Readback_Error_Gain.setText("Readback Desired Specification (Gain):")
        QLabel_Readback_Error_Offset.setText("Readback Desired Specification (Offset):")

        # External Auxiliary Equipment section
        QLabel_External_Auxiliary_Equipment = QLabel()
        QLabel_External_Auxiliary_Equipment.setText("Relay")
        self.QComboBox_External_Auxiliary_Equipment = QComboBox()
        self.QComboBox_External_Auxiliary_Equipment.addItems(["None", "RELAY"])

        self.QComboBox_Voltage_Res = QComboBox()
        self.QComboBox_set_PSU_Channel = QComboBox()
        self.QComboBox_set_ELoad_Channel = QComboBox()
        self.QComboBox_set_Function = QComboBox()
        self.QComboBox_Voltage_Sense = QComboBox()
        self.QLineEdit_Programming_Error_Gain = QLineEdit()
        self.QLineEdit_Programming_Error_Offset = QLineEdit()
        self.QLineEdit_Readback_Error_Gain = QLineEdit()
        self.QLineEdit_Readback_Error_Offset = QLineEdit()

        self.QLineEdit_PSU_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"])
        self.QLineEdit_DMM_VisaAddress.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_ELoad_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"])
        self.QComboBox_DUT.addItems(["Others", "Excavator", "EDU36311A", "Dolphin", "Hornbill", "SMU"])

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
        self.QComboBox_set_PSU_Channel.addItems(["1", "2", "3", "4"])
        self.QComboBox_set_PSU_Channel.setEnabled(True)
        self.QComboBox_set_ELoad_Channel.addItems(["None", "1", "2"])
        self.QComboBox_set_ELoad_Channel.setEnabled(True)
        self.QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])
        self.QComboBox_Voltage_Sense.setEnabled(True)

        #Power
        QLabel_Power = QLabel()
        QLabel_Power.setText("Rated Power (W):")
        self.QLineEdit_Power = QLineEdit()

        # Current Sweep
        QLabel_minCurrent = QLabel()
        QLabel_maxCurrent = QLabel()
        QLabel_current_step_size = QLabel()
        QLabel_minCurrent.setText("Initial Current (A):")
        QLabel_maxCurrent.setText("Final Current (A):")
        QLabel_current_step_size.setText("Step Size:")
        self.QLineEdit_minCurrent = QLineEdit()
        self.QLineEdit_maxCurrent = QLineEdit()
        self.QLineEdit_current_stepsize = QLineEdit()

        # Voltage Sweep
        QLabel_minVoltage = QLabel()
        QLabel_maxVoltage = QLabel()
        QLabel_voltage_step_size = QLabel()
        QLabel_minVoltage.setText("Initial Voltage (V):")
        QLabel_maxVoltage.setText("Final Voltage (V):")
        QLabel_voltage_step_size.setText("Step Size:")

        self.QLineEdit_minVoltage = QLineEdit()
        self.QLineEdit_maxVoltage = QLineEdit()
        self.QLineEdit_voltage_stepsize = QLineEdit()

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
        save_path_layout.addWidget(QLabel_Save_Path)  # QLabel for "Save Path"
        #save_path_layout.addWidget(QLineEdit_Save_Path)  # QLineEdit for the path
        save_path_layout.addWidget(self.QCheckBox_Report_Widget)  # Checkbox for "Generate Excel Report"
        save_path_layout.addWidget(self.QCheckBox_Image_Widget)  # Checkbox for "Show Graph"
        save_path_layout.addWidget(QCheckBox_Lock_Widget)  # Checkbox for "Show Graph"

        #Execute Layout + Outputbox in Right Container
        Right_container = QVBoxLayout()
        exec_layout_box = QHBoxLayout()
        exec_layout = QFormLayout()

        #exec_layout.addRow(Desp0)
        exec_layout.addWidget(self.OutputBox)
        exec_layout.addRow(QPushButton_Widget0)

        exec_layout.addRow(QPushButton_Widget3)
        exec_layout.addRow(QPushButton_Widget2)
        exec_layout.addRow(QPushButton_Widget1)   

        exec_layout_box.addLayout(exec_layout)
 
        Right_container.addLayout(save_path_layout)
        Right_container.addLayout(exec_layout_box)

        #Setting Form Layout with Left Container
        Left_container = QHBoxLayout()
        setting_layout = QFormLayout()

        setting_layout.addRow(Desp1)
        setting_layout.addRow(QPushButton_Widget4)
        setting_layout.addRow(QLabel_DUT, self.QComboBox_DUT)
        setting_layout.addRow(QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        setting_layout.addRow(QLabel_DMM_VisaAddress, self.QLineEdit_DMM_VisaAddress)
        setting_layout.addRow(QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        setting_layout.addRow(QLabel_DMM_Instrument, self.QComboBox_DMM_Instrument)
        setting_layout.addRow(Desp2)
        setting_layout.addRow(QLabel_set_PSU_Channel, self.QComboBox_set_PSU_Channel)
        setting_layout.addRow(QLabel_set_ELoad_Channel, self.QComboBox_set_ELoad_Channel)
        setting_layout.addRow(QLabel_set_Function, self.QComboBox_set_Function)
        setting_layout.addRow(QLabel_Voltage_Sense, self.QComboBox_Voltage_Sense)
        setting_layout.addRow(QLabel_Programming_Error_Gain, self.QLineEdit_Programming_Error_Gain)
        setting_layout.addRow(QLabel_Programming_Error_Offset, self.QLineEdit_Programming_Error_Offset)
        setting_layout.addRow(QLabel_Readback_Error_Gain, self.QLineEdit_Readback_Error_Gain)
        setting_layout.addRow(QLabel_Readback_Error_Offset, self.QLineEdit_Readback_Error_Offset)
        setting_layout.addRow(Desp8)
        setting_layout.addRow(QLabel_External_Auxiliary_Equipment, self.QComboBox_External_Auxiliary_Equipment)
        setting_layout.addRow(Desp6)
        setting_layout.addRow(QLabel_Power, self.QLineEdit_Power)
        setting_layout.addRow(Desp3)
        setting_layout.addRow(QLabel_minVoltage, self.QLineEdit_minVoltage)
        setting_layout.addRow(QLabel_maxVoltage, self.QLineEdit_maxVoltage)
        setting_layout.addRow(QLabel_voltage_step_size, self.QLineEdit_voltage_stepsize)
        setting_layout.addRow(Desp4)
        setting_layout.addRow(QLabel_minCurrent, self.QLineEdit_minCurrent)
        setting_layout.addRow(QLabel_maxCurrent, self.QLineEdit_maxCurrent)
        setting_layout.addRow(QLabel_current_step_size, self.QLineEdit_current_stepsize)
        setting_layout.addRow(Desp5)
        setting_layout.addRow(QLabel_noofloop, self.QComboBox_noofloop)
        setting_layout.addRow(QLabel_updatedelay, self.QComboBox_updatedelay)

        Left_container.addLayout(setting_layout)

        #Main Layout
        Main_Layout = QHBoxLayout()
        Main_Layout.addLayout(Left_container,stretch= 2)
        Main_Layout.addLayout(Right_container,stretch = 1)
        self.setLayout(Main_Layout)
        scroll_area(self,Main_Layout)

        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_DMM_VisaAddress.currentTextChanged.connect(self.DMM_VisaAddress_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)
        
        self.QComboBox_DUT.currentTextChanged.connect(self.DUT_changed)
        self.QLineEdit_Programming_Error_Gain.textEdited.connect(self.Programming_Error_Gain_changed)
        self.QLineEdit_Programming_Error_Offset.textEdited.connect(self.Programming_Error_Offset_changed)
        self.QLineEdit_Readback_Error_Gain.textEdited.connect(self.Readback_Error_Gain_changed)
        self.QLineEdit_Readback_Error_Offset.textEdited.connect(self.Readback_Error_Offset_changed)

        self.QComboBox_External_Auxiliary_Equipment.currentTextChanged.connect(self.External_Auxiliary_Equipment_changed)

        self.QLineEdit_Power.textEdited.connect(self.Power_changed)
        self.QComboBox_DUT.currentIndexChanged.connect(self.on_current_index_changed)

        self.QLineEdit_minVoltage.textEdited.connect(self.minVoltage_changed)
        self.QLineEdit_maxVoltage.textEdited.connect(self.maxVoltage_changed)
        self.QLineEdit_minCurrent.textEdited.connect(self.minCurrent_changed)
        self.QLineEdit_maxCurrent.textEdited.connect(self.maxCurrent_changed)
        self.QLineEdit_voltage_stepsize.textEdited.connect(self.voltage_step_size_changed)
        self.QLineEdit_current_stepsize.textEdited.connect(self.current_step_size_changed)
        self.QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)
        self.QComboBox_set_PSU_Channel.currentTextChanged.connect(self.PSU_Channel_changed)
        self.QComboBox_set_ELoad_Channel.currentTextChanged.connect(self.ELoad_Channel_changed)
        self.QComboBox_Voltage_Res.currentTextChanged.connect(self.set_VoltageRes_changed)
        self.QComboBox_Voltage_Sense.currentTextChanged.connect(self.set_VoltageSense_changed)

        self.QComboBox_noofloop.currentTextChanged.connect(self.noofloop_changed)
        self.QComboBox_updatedelay.currentTextChanged.connect(self.updatedelay_changed)

        self.QComboBox_DMM_Instrument.currentTextChanged.connect(self.DMM_Instrument_changed)
        self.QCheckBox_Report_Widget.stateChanged.connect(self.checkbox_state_Report)
        self.QCheckBox_Image_Widget.stateChanged.connect(self.checkbox_state_Image)
        QCheckBox_Lock_Widget.stateChanged.connect(self.checkbox_state_lock)

        QPushButton_Widget0.clicked.connect(self.savepath)
        QPushButton_Widget1.clicked.connect(self.executeTest)
        QPushButton_Widget2.clicked.connect(self.openDialog)
        QPushButton_Widget3.clicked.connect(self.estimateTime)
        QPushButton_Widget4.clicked.connect(self.doFind)

        AdvancedSettingsList.append(self.Range)
        AdvancedSettingsList.append(self.Aperture)
        AdvancedSettingsList.append(self.AutoZero)
        AdvancedSettingsList.append(self.inputZ)
        AdvancedSettingsList.append(self.UpTime)
        AdvancedSettingsList.append(self.DownTime)

    def External_Auxiliary_Equipment_changed(self, s):
        if s == "None":
            self.relay_voltage = "None"
        else:
            self.relay_voltage = "RELAY"

    def on_current_index_changed(self):
        selected_text = self.QComboBox_DUT.currentText()
        self.update_selection(selected_text)
 
        self.QLineEdit_Programming_Error_Gain.setText(self.Programming_Error_Gain)
        self.QLineEdit_Programming_Error_Gain.setText(self.Programming_Error_Gain)
        self.QLineEdit_Programming_Error_Offset.setText(self.Programming_Error_Offset)
        self.QLineEdit_Readback_Error_Gain.setText(self.Readback_Error_Gain)
        self.QLineEdit_Readback_Error_Offset.setText(self.Readback_Error_Offset)
        self.QLineEdit_Power.setText(self.Power)
        """self.QLineEdit_rshunt.setText(self.rshunt)"""
        self.QLineEdit_minVoltage.setText(self.minVoltage)
        self.QLineEdit_maxVoltage.setText(self.maxVoltage)
        self.QLineEdit_voltage_stepsize.setText(self.voltage_step_size)
        self.QLineEdit_minCurrent.setText(self.minCurrent)
        self.QLineEdit_maxCurrent.setText(self.maxCurrent)
        self.QLineEdit_current_stepsize.setText(self.current_step_size)

        self.QComboBox_set_PSU_Channel.setCurrentIndex(int(self.PSU_Channel))
        self.QComboBox_set_ELoad_Channel.setCurrentIndex(int(self.ELoad_Channel))
        self.QComboBox_Voltage_Sense.setCurrentText("4 Wire" if self.VoltageSense == "EXT" else "2 Wire")
        self.QComboBox_noofloop.setCurrentText(self.noofloop)
        self.QComboBox_updatedelay.setCurrentText(self.updatedelay)

    def update_selection(self, selected_text):
        """Update selected text and reload config file"""
        self.selected_text = selected_text
        self.load_data()

    def load_data(self):
        """Reads configuration file and returns a dictionary of key-value pairs."""
        config_data = {}
        if self.selected_text =="Excavator":
            self.config_file = os.path.join(config_folder,"config_Excavator.txt")
            
        elif self.selected_text =="Dolphin":
            self.config_file = os.path.join(config_folder,"config_Dolphin.txt")
            
        elif self.selected_text =="SMU":
            self.config_file = os.path.join(config_folder,"config_SMU.txt")
        
        elif self.selected_text =="Hornbill":
            self.config_file = os.path.join(config_folder,"config_Hornbill.txt")

        else:
            self.config_file = os.path.join(config_folder,"config_Others.txt")

        try:
            with open(self.config_file, "r") as file: 
                for line in file:

                    if not line or line.startswith("#") or line.startswith("//"):
                        continue 

                    if "=" in line:
                        key, value = line.strip().split("=")
                        config_data[key.strip()] = value.strip()

            for key, value in config_data.items():
                if key == "savelocation":
                    # If savelocation has a valid value, do not overwrite it
                    if self.savelocation and self.savelocation != "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
                        continue 
                    else:
                        setattr(self, key, value)
                else:
                    setattr(self, key, value)

        except FileNotFoundError:
            print("Config file not found. Using default values.")

        return config_data
    def Power_changed(self, value):
        self.Power = value

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_DMM_VisaAddress.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()
            
            self.visaIdList, self.nameList = GetVisaSCPIResources()
            
            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])
            
            # Add "None" option at the end
            self.QLineEdit_PSU_VisaAddress.addItem("None")
            self.QLineEdit_DMM_VisaAddress.addItem("None")
            self.QLineEdit_ELoad_VisaAddress.addItem("None")
                    
        except:
            self.OutputBox.append("No Devices Found!!!")
        return   


    def updatedelay_changed(self, value):
        self.updatedelay = value
        #self.OutputBox.append(str(self.updatedelay))

    def noofloop_changed(self, value):
        self.noofloop = value
        #self.OutputBox.append(str(self.noofloop))

    def DMM_Instrument_changed(self, s):
        self.DMM_Instrument = s

    def PSU_VisaAddress_changed(self, s):
        self.PSU = s    

    def DMM_VisaAddress_changed(self, s):
        self.DMM = s

    def ELoad_VisaAddress_changed(self, s):
        self.ELoad = s

    def DUT_changed(self, s):
        self.DUT = s

    def ELoad_Channel_changed(self, s):
       self.ELoad_Channel = s

    def PSU_Channel_changed(self, s):
       self.PSU_Channel = s

    def Programming_Error_Gain_changed(self, s):
        self.Programming_Error_Gain = s

    def Programming_Error_Offset_changed(self, s):
        self.Programming_Error_Offset = s

    def Readback_Error_Gain_changed(self, s):
        self.Readback_Error_Gain = s

    def Readback_Error_Offset_changed(self, s):
        self.Readback_Error_Offset = s

    def minVoltage_changed(self, s):
        self.minVoltage = s

    def maxVoltage_changed(self, s):
        self.maxVoltage = s

    def minCurrent_changed(self, s):
        self.minCurrent = s

    def maxCurrent_changed(self, s):
        self.maxCurrent = s

    def voltage_step_size_changed(self, s):
        self.voltage_step_size = s

    def current_step_size_changed(self, s):
        self.current_step_size = s

    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.setFunction = "Voltage"

        elif s == "Current Priority":
            self.setFunction = "Current"

        elif s == "Resistance Priority":
            self.setFunction = "Resistance"

    def set_VoltageRes_changed(self, s):
        self.VoltageRes = s

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.VoltageSense = "INT"
        elif s == "4 Wire":
            self.VoltageSense = "EXT"

    def setRange(self, value):
        AdvancedSettingsList[0] = value

    def setAperture(self, value):
        AdvancedSettingsList[1] = value

    def setAutoZero(self, value):
        AdvancedSettingsList[2] = value

    def setInputZ(self, value):
        AdvancedSettingsList[3] = value

    def checkbox_state_Report(self, s):
        self.checkbox_data_Report = s

    def checkbox_state_Image(self, s):
        self.checkbox_data_Image = s

    def checkbox_state_lock(self, state):
        lockable_widgets = (QPushButton, QLineEdit, QTextEdit, QComboBox)

        for widget in self.findChildren(lockable_widgets):
            widget.setDisabled(state == 2)  # Disable if checkbox is checked

    def setUpTime(self, value):
        AdvancedSettingsList[4] = value

    def setDownTime(self, value):
        AdvancedSettingsList[5] = value

    def openDialog(self):
        dlg = AdvancedSetting_Voltage()
        dlg.exec()

    def estimateTime(self):
        
        #self.OutputBox.append(str(self.updatedelay))
        try:
            self.currloop = ((float(self.maxCurrent) - float(self.minCurrent))/ float(self.current_step_size)) + 1
            self.voltloop = ((float(self.maxVoltage) - float(self.minVoltage))/ float(self.voltage_step_size)) + 1

            if self.updatedelay == 0.0:
                constant = 0
                    
            else:
                constant = 1

            self.estimatetime = (self.currloop * self.voltloop *(0.2 + 0.8 + (float(self.updatedelay) * constant) )) * float(self.noofloop)
            self.OutputBox.append(f"{self.estimatetime} seconds")
            self.OutputBox.append("") 
        except Exception as e:
            QMessageBox.warning(self, "Warning", "Input cannot be empty!")
            return

    def savepath(self):  
        # Create a Tkinter root window
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open a directory dialog and return the selected directory path
        directory = filedialog.askdirectory()
        self.savelocation = directory
        self.OutputBox.append(str(self.savelocation))

    def check_missing_params(self, param_dict):
        """Check which parameters are None or empty and return them."""
        missing = []
        for key, value in param_dict.items():
            # Check for None or empty string
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing.append(key)
        return missing

    def executeTest(self):
        global globalvv
        try:
            for x in range (int(self.noofloop)):

                """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
                then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
                will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
                begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
                begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
                are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
                optionally export all the details into a CSV file or display a graph after the test is completed.

                """
            self.infoList = []
            self.dataList = []
            self.dataList2 = []
            self.setEnabled(False)

            dict = dictGenerator.input(
                V_Rating=self.Voltage_Rating,
                power=self.Power,
                estimatetime=self.estimatetime,
                updatedelay=self.updatedelay,
                readbackvoltage=self.readbackvoltage,
                readbackcurrent=self.readbackcurrent,
                noofloop=self.noofloop,
                Instrument=self.DMM_Instrument,
                Programming_Error_Gain=self.Programming_Error_Gain,
                Programming_Error_Offset=self.Programming_Error_Offset,
                Readback_Error_Gain=self.Readback_Error_Gain,
                Readback_Error_Offset=self.Readback_Error_Offset,
                relay_voltage=self.relay_voltage,
                unit=self.unit,
                minCurrent=self.minCurrent,
                maxCurrent=self.maxCurrent,
                current_step_size=self.current_step_size,
                minVoltage=self.minVoltage,
                maxVoltage=self.maxVoltage,
                voltage_step_size=self.voltage_step_size,
                selected_DUT=self.selected_text,
                PSU=self.PSU,
                OperationMode=self.SPOperationMode,
                OSC=self.OSC,
                DMM=self.DMM,
                ELoad=self.ELoad,
                ELoad_Channel=self.ELoad_Channel,
                PSU_Channel=self.PSU_Channel,
                VoltageSense=self.VoltageSense,
                VoltageRes=self.VoltageRes,
                setFunction=self.setFunction,
                Range=AdvancedSettingsList[0],
                Aperture=AdvancedSettingsList[1],
                AutoZero=AdvancedSettingsList[2],
                InputZ=AdvancedSettingsList[3],
                UpTime=AdvancedSettingsList[4],
                DownTime=AdvancedSettingsList[5],
            )

            # Check for missing parameters
            missing = self.check_missing_params(dict)
            if missing:
                print(f"The following parameters are missing or empty: {missing}")
                return

            """# Visa Address Check & Run Test
            A = VisaResourceManager()

            # Collect only valid addresses
            addresses = [addr for addr in [self.ELoad, self.PSU, self.DMM] if addr not in (None, "None")]

            # Optional: keep only USB addresses
            addresses = [addr for addr in addresses if str(addr).upper().startswith("USB")]

            if not addresses:
                self.OutputBox.append("No valid VISA addresses selected.")
                return

            flag, args = A.openRM(*addresses)
            if flag == 0:
                string = ", ".join(map(str, args))
                QMessageBox.warning(self, "VISA IO ERROR", string)
                return
            """
            QMessageBox.warning(
            self,
            "In Progress",
            "Measurement will start now , please do not close the main window until test is completed",
                                )
            # globalvv = dict["estimatetime"]
            # loading_thread = threading.Thread(target=self.tkinter_loading_screen, args=(globalvv,))
            # loading_thread.start()

            #Execute Voltage Measurement
            relay_voltage = RelayController_Voltage()
            if self.relay_voltage == "RELAY":
                
                relay_voltage.relay_on()
            else:
                relay_voltage.relay_off()

            if self.DMM_Instrument == "Keysight":

                if self.selected_text == "Dolphin":
                    if self.ELoad != "None" and self.DMM != "None":
                        print("ELoad connected and DMM connected") #All connected
                        try:(
                            self.infoList,
                            self.dataList,
                            self.dataList2
                            ) = DolphinNewVoltageMeasurementwithELoad.Execute_Voltage_Accuracy(self, dict, self.PSU_Channel)
                    
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return

                    elif self.ELoad == "None" and self.DMM != "None":
                        print("No ELoad connected and DMM connected") #No Eload connected but DMM connected
                        try:(
                            self.infoList,
                            self.dataList,
                            self.dataList2
                            ) = DolphinNewVoltageMeasurementNoELoadWithDMM.Execute_Voltage_Accuracy(self, dict, self.PSU_Channel)
                          
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return
                    
                    elif self.ELoad != "None" and self.DMM == "None":
                        print("ELoad connected and No DMM connected") #Eload connected but no DMM connected
                        try:(
                            self.infoList,
                            self.dataList,
                            self.dataList2
                            ) = DolphinNewVoltageMeasurementwithELoadNoDMM.Execute_Voltage_Accuracy(self, dict, self.PSU_Channel)
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return
                    else :
                        print("No ELoad connected and No DMM connected") #No Eload connected and
                        try:(
                            self.infoList,
                            self.dataList,
                            self.dataList2
                            ) = DolphinNewVoltageMeasurementNoELoadNoDMM.Execute_Voltage_Accuracy(self, dict, self.PSU_Channel)
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return
                                            
                if self.selected_text == "EDU36311A":
                    try:(
                        infoList,
                        dataList,
                        dataList2  
                    ) = EDU36311AVoltageMeasurementNoELoad.Execute_Voltage_Accuracy(self, dict)
                  
                    except Exception as e:
                        QMessageBox.warning(self, "Error", str(e))
                        return
                    
                        """   elif self.selected_text == "Excavator":
                                try:(
                                    infoList,
                                    dataList,
                                    dataList2
                                ) = ExcavatorVoltageMeasurement.Execute_Voltage_Accuracy(self, dict)

                                except Exception as e:
                                    QMessageBox.warning(self, "Error", str(e))
                                    return
                            elif self.selected_text == "SMU":
                                try:(
                                    infoList, 
                                    dataList,
                                    dataList2
                                ) = SMUVoltageMeasurement.Execute_Voltage_Accuracy(self, dict)
                                except Exception as e:
                                    QMessageBox.warning(self, "Error", str(e))  
                                    return"""
                
                elif self.selected_text == "Hornbill":
                    if self.ELoad != "None":
                        try:(
                            infoList,   
                            dataList,
                            dataList2
                        ) = HornbillVoltageMeasurementwithELoad.Execute_Voltage_Accuracy(self, dict)
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return
                    else:
                        try:(
                            infoList,   
                            dataList,
                            dataList2
                        ) = HornbillVoltageMeasurementNoELoad.Execute_Voltage_Accuracy(self, dict)
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return

            relay_voltage.relay_off()
        
            #Measurement Completion
            if x == (int(self.noofloop) - 1):   
                self.OutputBox.append("Measurement is complete !")
        
                #Export Data to CSV
                if self.QCheckBox_Report_Widget.isChecked():
                    instrumentData(self.PSU, self.DMM, self.ELoad)
                    datatoCSV_Accuracy(self.infoList, self.dataList, self.dataList2)
                    datatoGraph(self.infoList, self.dataList, self.dataList2)
                    datatoGraph.scatterCompareVoltage(self, float(self.Programming_Error_Gain), float(self.Programming_Error_Offset), float(self.Readback_Error_Gain), float(self.Readback_Error_Offset), str(self.unit), float(self.Voltage_Rating))

                    A = xlreport(save_directory=self.savelocation, file_name=str(self.unit))
                    A.run()
                    df = pd.DataFrame.from_dict(dict, orient="index")
                    df.to_csv(os.path.join(csv_folder,"config.csv"))
                
                #Show Graph Image
                if self.QCheckBox_Image_Widget.isChecked():
                    self.image_dialog = image_Window()
                    self.image_dialog.setModal(True)
                    self.image_dialog.show()


        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

            return
        finally:
            self.setEnabled(True)

class CurrentMeasurementDialog(QDialog):
    """Class for configuring the current measurement DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py
    """

    def __init__(self):
        """Method where Widgets, Signals and Slots are defined in the GUI for Current Measurement"""
        super().__init__()
         # Initialize default CSV path
        self.DATA_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/data.csv"  # or use a dynamic path if needed
        self.IMAGE_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/images/Chart.png"
        self.ERROR_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/error.csv"
        self.image_dialog = None
        self.POWER_DATA_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powerdata.csv"  # or use a dynamic path if needed
        self.POWER_IMAGE_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/images/powerChart.png"
        self.POWER_ERROR_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powererror.csv"

        # Default Values
        #self.PSU_VisaAddress = "USB0::0x2A8D::0xCC04::MY00000037::0::INSTR"
        #self.DMM_VisaAddress = "USB0::0x2A8D::0x1601::MY60094787::0::INSTR"
        #self.ELoad_VisaAddress = "USB0::0x2A8D::0x3902::MY60260005::0::INSTR"
        self.rshunt = "0.05"
        self.Power_Rating = "6000"
        self.Current_Rating = "24"
        self.Voltage_Rating = "800"
        self.Power = "2000"
        self.powerfin = self.Power
        self.powerini = "0"
        self.power_step_size = "60"
        self.currloop = "1"
        self.voltloop = "1"
        self.estimatetime = "0"
        self.readbackvoltage = "0"
        self.readbackcurrent = "0"
        self.savelocation = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"
        self.noofloop = "1"
        self.updatedelay = "0.0"
        self.unit = "CURRENT"
        self.Programming_Error_Offset = "0.001"
        self.Programming_Error_Gain = "0.001"
        self.Readback_Error_Offset = "0.001"
        self.Readback_Error_Gain = "0.001"

        self.Power_Programming_Error_Offset = "0.005"
        self.Power_Programming_Error_Gain = "0.005"
        self.Power_Readback_Error_Offset = "0.005"
        self.Power_Readback_Error_Gain = "0.005"

        self.relay_current = "None"

        self.minCurrent = "1"
        self.maxCurrent = "1"
        self.current_step_size = "1"
        self.minVoltage = "1"
        self.maxVoltage = "10"
        self.voltage_step_size = "1"

        self.PSU = "USB0::0x2A8D::0xDA04::CN24350083::0::INSTR"
        self.DMM = "USB0::0x2A8D::0x0201::MY57702128::0::INSTR"
        self.DMM2 = "USB0::0x2A8D::0x0201::MY54701197::0::INSTR"
        self.ELoad = "USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"
        self.ELoad_Channel = "1"
        self.PSU_Channel = "1"
        self.DMM_Instrument = "Keysight"

        self.setFunction = "Voltage" #Set Eload in CV Mode
        self.VoltageRes = "DEF"
        self.VoltageSense = "INT"
        self.SPOperationMode = "Independent"

        self.checkbox_data_Report = 2
        self.checkbox_data_Image = 2
        self.checkbox_test_CurrentAccuracy = 2
        self.checkbox_test_CurrentLoadRegulation = 2
        self.checkbox_test_PowerAccuracy = 2

        self.Range = "Auto"
        self.Aperture = "0.2"
        self.AutoZero = "ON"
        self.inputZ = "ON"
        self.UpTime = "50"
        self.DownTime = "50"
        
        # Ensure DATA_CSV_PATH is defined before use
        if not hasattr(self, 'DATA_CSV_PATH') or not self.DATA_CSV_PATH:
            QMessageBox.warning(self, "Error", "CSV path is not set.")

        if not hasattr(self, 'POWER_DATA_CSV_PATH') or not self.POWER_DATA_CSV_PATH:
            QMessageBox.warning(self, "Error", "POWER CSV path is not set.")

        #Create Voltage Window
        self.setWindowTitle("Current Measurement")
        self.image_window = None
        self.setWindowFlags(Qt.Window)

        #Create find button 
        QPushButton_Widget0 = QPushButton()
        QPushButton_Widget0.setText("Save Path")
        QPushButton_Widget1 = QPushButton()
        QPushButton_Widget1.setText("Execute Test")
        QPushButton_Widget2 = QPushButton()
        QPushButton_Widget2.setText("Advanced Settings")
        QPushButton_Widget3 = QPushButton()
        QPushButton_Widget3.setText("Estimate Data Collection Time")
        QPushButton_Widget4 = QPushButton()
        QPushButton_Widget4.setText("Find Instruments")
        self.QCheckBox_Report_Widget = QCheckBox()
        self.QCheckBox_Report_Widget.setText("Generate Excel Report")
        self.QCheckBox_Report_Widget.setCheckState(Qt.Checked)
        self.QCheckBox_Image_Widget = QCheckBox()
        self.QCheckBox_Image_Widget.setText("Show Graph")
        self.QCheckBox_Image_Widget.setCheckState(Qt.Checked)
        QCheckBox_Lock_Widget = QCheckBox()
        QCheckBox_Lock_Widget.setText("Lock Widget")

        #Output Display
        self.OutputBox = QTextBrowser()
        self.OutputBox.append(f"{my_result.getvalue()}")
        self.OutputBox.append("")  # Empty line after each append

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

        Desp0.setFont(desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp5.setFont(desp_font)
        Desp6.setFont(desp_font)
        Desp7.setFont(desp_font)
        Desp8.setFont(desp_font)

        Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Voltage Sweep:")
        Desp4.setText("Current Sweep:")
        Desp5.setText("No. of Collection:")
        Desp6.setText("Rated Power [W]")
        Desp7.setText("Maximum Current")
        Desp8.setText("External Auxiliary Equipment:")

        #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location/Output Wndow:")

        # Connections section
        QLabel_PSU_VisaAddress = QLabel()
        QLabel_DMM_VisaAddress = QLabel()
        QLabel_ELoad_VisaAddress = QLabel()
        QLabel_DMM_Instrument = QLabel()
        QLabel_DUT = QLabel()
        QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        QLabel_DMM_VisaAddress.setText("Visa Address (DMM):")
        QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DMM_Instrument.setText("Instrument Type (DMM):")
        QLabel_DUT.setText("DUT:")

        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_DMM_VisaAddress = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        self.QComboBox_DMM_Instrument = QComboBox()
        self.QComboBox_DUT = QComboBox()

        # General Settings
        QLabel_Voltage_Res = QLabel()
        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
        QLabel_Programming_Error_Gain = QLabel()
        QLabel_Programming_Error_Offset = QLabel()
        QLabel_Readback_Error_Gain = QLabel()
        QLabel_Readback_Error_Offset = QLabel()

        QLabel_Voltage_Res.setText("Voltage Resolution (DMM):")
        QLabel_set_PSU_Channel.setText("Set PSU Channel:")
        QLabel_set_ELoad_Channel.setText("Set Eload Channel:")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        QLabel_Programming_Error_Gain.setText("Programming Desired Specification (Gain):")
        QLabel_Programming_Error_Offset.setText("Programming Desired Specification (Offset):")
        QLabel_Readback_Error_Gain.setText("Readback Desired Specification (Gain):")
        QLabel_Readback_Error_Offset.setText("Readback Desired Specification (Offset):")

        # External Auxiliary Equipment section
        QLabel_External_Auxiliary_Equipment = QLabel()
        QLabel_External_Auxiliary_Equipment.setText("Relay")
        self.QComboBox_External_Auxiliary_Equipment = QComboBox()
        self.QComboBox_External_Auxiliary_Equipment.addItems(["None", "RELAY"])


        self.QComboBox_Voltage_Res = QComboBox()
        self.QComboBox_set_PSU_Channel = QComboBox()
        self.QComboBox_set_ELoad_Channel = QComboBox()
        self.QComboBox_set_Function = QComboBox()
        self.QComboBox_Voltage_Sense = QComboBox()
        self.QLineEdit_Programming_Error_Gain = QLineEdit()
        self.QLineEdit_Programming_Error_Offset = QLineEdit()
        self.QLineEdit_Readback_Error_Gain = QLineEdit()
        self.QLineEdit_Readback_Error_Offset = QLineEdit()

        self.QLineEdit_PSU_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"])
        self.QLineEdit_DMM_VisaAddress.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_ELoad_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"])
        self.QComboBox_DUT.addItems(["Others", "Excavator", "EDU36311A", "Dolphin", "Hornbill", "SMU"])

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
        self.QComboBox_set_PSU_Channel.addItems(["1", "2", "3", "4"])
        self.QComboBox_set_PSU_Channel.setEnabled(True)
        self.QComboBox_set_ELoad_Channel.addItems(["1", "2"])
        self.QComboBox_set_ELoad_Channel.setEnabled(True)
        self.QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])
        self.QComboBox_Voltage_Sense.setEnabled(True)

        #Power
        QLabel_Power = QLabel()
        QLabel_Power.setText("Rated Power (W):")
        self.QLineEdit_Power = QLineEdit()

        QLabel_rshunt = QLabel()
        QLabel_rshunt.setText("Shunt Resistance Value (ohm):")
        self.QLineEdit_rshunt = QLineEdit()

        # Current Sweep
        QLabel_minCurrent = QLabel()
        QLabel_maxCurrent = QLabel()
        QLabel_current_step_size = QLabel()
        QLabel_minCurrent.setText("Initial Current (A):")
        QLabel_maxCurrent.setText("Final Current (A):")
        QLabel_current_step_size.setText("Step Size:")
        self.QLineEdit_minCurrent = QLineEdit()
        self.QLineEdit_maxCurrent = QLineEdit()
        self.QLineEdit_current_stepsize = QLineEdit()

        # Voltage Sweep
        QLabel_minVoltage = QLabel()
        QLabel_maxVoltage = QLabel()
        QLabel_voltage_step_size = QLabel()
        QLabel_minVoltage.setText("Initial Voltage (V):")
        QLabel_maxVoltage.setText("Final Voltage (V):")
        QLabel_voltage_step_size.setText("Step Size:")

        self.QLineEdit_minVoltage = QLineEdit()
        self.QLineEdit_maxVoltage = QLineEdit()
        self.QLineEdit_voltage_stepsize = QLineEdit()

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
        save_path_layout.addWidget(QLabel_Save_Path)  # QLabel for "Save Path"
        #save_path_layout.addWidget(QLineEdit_Save_Path)  # QLineEdit for the path
        save_path_layout.addWidget(self.QCheckBox_Report_Widget)  # Checkbox for "Generate Excel Report"
        save_path_layout.addWidget(self.QCheckBox_Image_Widget)  # Checkbox for "Show Graph"
        save_path_layout.addWidget(QCheckBox_Lock_Widget)  # Checkbox for "Show Graph"

        #Execute Layout + Outputbox in Right Container
        Right_container = QVBoxLayout()
        exec_layout_box = QHBoxLayout()
        exec_layout = QFormLayout()

        #exec_layout.addRow(Desp0)
        exec_layout.addWidget(self.OutputBox)
        exec_layout.addRow(QPushButton_Widget0)

        exec_layout.addRow(QPushButton_Widget3)
        exec_layout.addRow(QPushButton_Widget2)
        exec_layout.addRow(QPushButton_Widget1)   

        exec_layout_box.addLayout(exec_layout)
 
        Right_container.addLayout(save_path_layout)
        Right_container.addLayout(exec_layout_box)

        #Setting Form Layout with Left Container
        Left_container = QHBoxLayout()
        setting_layout = QFormLayout()

        setting_layout.addRow(Desp1)
        setting_layout.addRow(QPushButton_Widget4)
        setting_layout.addRow(QLabel_DUT, self.QComboBox_DUT)
        setting_layout.addRow(QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        setting_layout.addRow(QLabel_DMM_VisaAddress, self.QLineEdit_DMM_VisaAddress)
        setting_layout.addRow(QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        setting_layout.addRow(QLabel_DMM_Instrument, self.QComboBox_DMM_Instrument)
        setting_layout.addRow(Desp2)
        setting_layout.addRow(QLabel_set_PSU_Channel, self.QComboBox_set_PSU_Channel)
        setting_layout.addRow(QLabel_set_ELoad_Channel, self.QComboBox_set_ELoad_Channel)
        setting_layout.addRow(QLabel_set_Function, self.QComboBox_set_Function)
        setting_layout.addRow(QLabel_Voltage_Sense, self.QComboBox_Voltage_Sense)
        setting_layout.addRow(QLabel_Programming_Error_Gain, self.QLineEdit_Programming_Error_Gain)
        setting_layout.addRow(QLabel_Programming_Error_Offset, self.QLineEdit_Programming_Error_Offset)
        setting_layout.addRow(QLabel_Readback_Error_Gain, self.QLineEdit_Readback_Error_Gain)
        setting_layout.addRow(QLabel_Readback_Error_Offset, self.QLineEdit_Readback_Error_Offset)
        setting_layout.addRow(Desp8)
        setting_layout.addRow(QLabel_External_Auxiliary_Equipment, self.QComboBox_External_Auxiliary_Equipment)
        setting_layout.addRow(Desp6)
        setting_layout.addRow(QLabel_Power, self.QLineEdit_Power)
        setting_layout.addRow(QLabel_rshunt, self.QLineEdit_rshunt)
        setting_layout.addRow(Desp3)
        setting_layout.addRow(QLabel_minVoltage, self.QLineEdit_minVoltage)
        setting_layout.addRow(QLabel_maxVoltage, self.QLineEdit_maxVoltage)
        setting_layout.addRow(QLabel_voltage_step_size, self.QLineEdit_voltage_stepsize)
        setting_layout.addRow(Desp4)
        setting_layout.addRow(QLabel_minCurrent, self.QLineEdit_minCurrent)
        setting_layout.addRow(QLabel_maxCurrent, self.QLineEdit_maxCurrent)
        setting_layout.addRow(QLabel_current_step_size, self.QLineEdit_current_stepsize)
        setting_layout.addRow(Desp5)
        setting_layout.addRow(QLabel_noofloop, self.QComboBox_noofloop)
        setting_layout.addRow(QLabel_updatedelay, self.QComboBox_updatedelay)

        Left_container.addLayout(setting_layout)

        #Main Layout
        Main_Layout = QHBoxLayout()
        Main_Layout.addLayout(Left_container,stretch= 2)
        Main_Layout.addLayout(Right_container,stretch = 1)
        self.setLayout(Main_Layout)
        scroll_area(self,Main_Layout)

        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_DMM_VisaAddress.currentTextChanged.connect(self.DMM_VisaAddress_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)
        
        self.QComboBox_DUT.currentTextChanged.connect(self.DUT_changed)
        self.QLineEdit_Programming_Error_Gain.textEdited.connect(self.Programming_Error_Gain_changed)
        self.QLineEdit_Programming_Error_Offset.textEdited.connect(self.Programming_Error_Offset_changed)
        self.QLineEdit_Readback_Error_Gain.textEdited.connect(self.Readback_Error_Gain_changed)
        self.QLineEdit_Readback_Error_Offset.textEdited.connect(self.Readback_Error_Offset_changed)

        self.QComboBox_External_Auxiliary_Equipment.currentTextChanged.connect(self.External_Auxiliary_Equipment_changed)

        self.QLineEdit_Power.textEdited.connect(self.Power_changed)
        self.QLineEdit_rshunt.textEdited.connect(self.rshunt_changed)
        self.QComboBox_DUT.currentIndexChanged.connect(self.on_current_index_changed)

        self.QLineEdit_minVoltage.textEdited.connect(self.minVoltage_changed)
        self.QLineEdit_maxVoltage.textEdited.connect(self.maxVoltage_changed)
        self.QLineEdit_minCurrent.textEdited.connect(self.minCurrent_changed)
        self.QLineEdit_maxCurrent.textEdited.connect(self.maxCurrent_changed)
        self.QLineEdit_voltage_stepsize.textEdited.connect(self.voltage_step_size_changed)
        self.QLineEdit_current_stepsize.textEdited.connect(self.current_step_size_changed)
        self.QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)
        self.QComboBox_set_PSU_Channel.currentTextChanged.connect(self.PSU_Channel_changed)
        self.QComboBox_set_ELoad_Channel.currentTextChanged.connect(self.ELoad_Channel_changed)
        self.QComboBox_Voltage_Res.currentTextChanged.connect(self.set_VoltageRes_changed)
        self.QComboBox_Voltage_Sense.currentTextChanged.connect(self.set_VoltageSense_changed)

        self.QComboBox_noofloop.currentTextChanged.connect(self.noofloop_changed)
        self.QComboBox_updatedelay.currentTextChanged.connect(self.updatedelay_changed)

        self.QComboBox_DMM_Instrument.currentTextChanged.connect(self.DMM_Instrument_changed)
        self.QCheckBox_Report_Widget.stateChanged.connect(self.checkbox_state_Report)
        self.QCheckBox_Image_Widget.stateChanged.connect(self.checkbox_state_Image)
        QCheckBox_Lock_Widget.stateChanged.connect(self.checkbox_state_lock)

        QPushButton_Widget0.clicked.connect(self.savepath)
        QPushButton_Widget1.clicked.connect(self.executeTest)
        QPushButton_Widget2.clicked.connect(self.openDialog)
        QPushButton_Widget3.clicked.connect(self.estimateTime)
        QPushButton_Widget4.clicked.connect(self.doFind)

        AdvancedSettingsList.append(self.Range)
        AdvancedSettingsList.append(self.Aperture)
        AdvancedSettingsList.append(self.AutoZero)
        AdvancedSettingsList.append(self.inputZ)
        AdvancedSettingsList.append(self.UpTime)
        AdvancedSettingsList.append(self.DownTime)

    def External_Auxiliary_Equipment_changed(self, s):
        if s == "None":
            self.relay_current = "None"
        else:
            self.relay_current = "RELAY"

    def on_current_index_changed(self):
        selected_text = self.QComboBox_DUT.currentText()
        self.update_selection(selected_text)
 
        self.QLineEdit_Programming_Error_Gain.setText(self.Programming_Error_Gain)
        self.QLineEdit_Programming_Error_Gain.setText(self.Programming_Error_Gain)
        self.QLineEdit_Programming_Error_Offset.setText(self.Programming_Error_Offset)
        self.QLineEdit_Readback_Error_Gain.setText(self.Readback_Error_Gain)
        self.QLineEdit_Readback_Error_Offset.setText(self.Readback_Error_Offset)
        self.QLineEdit_Power.setText(self.Power)
        self.QLineEdit_rshunt.setText(self.rshunt)
        self.QLineEdit_minVoltage.setText(self.minVoltage)
        self.QLineEdit_maxVoltage.setText(self.maxVoltage)
        self.QLineEdit_voltage_stepsize.setText(self.voltage_step_size)
        self.QLineEdit_minCurrent.setText(self.minCurrent)
        self.QLineEdit_maxCurrent.setText(self.maxCurrent)
        self.QLineEdit_current_stepsize.setText(self.current_step_size)

        self.QComboBox_set_PSU_Channel.setCurrentIndex(int(self.PSU_Channel))
        self.QComboBox_set_ELoad_Channel.setCurrentIndex(int(self.ELoad_Channel))
        self.QComboBox_Voltage_Sense.setCurrentText("4 Wire" if self.VoltageSense == "EXT" else "2 Wire")
        self.QComboBox_noofloop.setCurrentText(self.noofloop)
        self.QComboBox_updatedelay.setCurrentText(self.updatedelay)

    def update_selection(self, selected_text):
        """Update selected text and reload config file"""
        self.selected_text = selected_text
        self.load_data()

    def load_data(self):
        """Reads configuration file and returns a dictionary of key-value pairs."""
        config_data = {}
        if self.selected_text =="Excavator":
            self.config_file = os.path.join(config_folder,"config_Excavator.txt")
            
        elif self.selected_text =="Dolphin":
            self.config_file = os.path.join(config_folder,"config_Dolphin.txt")
            
        elif self.selected_text =="SMU":
            self.config_file = os.path.join(config_folder,"config_SMU.txt")

        else:
            self.config_file = os.path.join(config_folder,"config_Others.txt")

        try:
            with open(self.config_file, "r") as file: 
                for line in file:

                    if not line or line.startswith("#") or line.startswith("//"):
                        continue 

                    if "=" in line:
                        key, value = line.strip().split("=")
                        config_data[key.strip()] = value.strip()

            for key, value in config_data.items():
                if key == "savelocation":
                    # If savelocation has a valid value, do not overwrite it
                    if self.savelocation and self.savelocation != "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
                        continue 
                    else:
                        setattr(self, key, value)
                else:
                    setattr(self, key, value)

        except FileNotFoundError:
            print("Config file not found. Using default values.")

        return config_data
    
    def rshunt_changed(self, value):
        self.rshunt = value

    def Power_changed(self, value):
        self.Power = value

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_DMM_VisaAddress.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()
            
            self.visaIdList, self.nameList = GetVisaSCPIResources()
            
            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])
            
            # Add "None" option at the end
            self.QLineEdit_PSU_VisaAddress.addItem("None")
            self.QLineEdit_DMM_VisaAddress.addItem("None")
            self.QLineEdit_ELoad_VisaAddress.addItem("None")
                
        except:
            self.OutputBox.append("No Devices Found!!!")
        return   


    def updatedelay_changed(self, value):
        self.updatedelay = value
        #self.OutputBox.append(str(self.updatedelay))

    def noofloop_changed(self, value):
        self.noofloop = value
        #self.OutputBox.append(str(self.noofloop))

    def DMM_Instrument_changed(self, s):
        self.DMM_Instrument = s

    def PSU_VisaAddress_changed(self, s):
        self.PSU = s    

    def DMM_VisaAddress_changed(self, s):
        self.DMM2 = s

    def ELoad_VisaAddress_changed(self, s):
        self.ELoad = s

    def DUT_changed(self, s):
        self.DUT = s

    def ELoad_Channel_changed(self, s):
       self.ELoad_Channel = s

    def PSU_Channel_changed(self, s):
       self.PSU_Channel = s

    def Programming_Error_Gain_changed(self, s):
        self.Programming_Error_Gain = s

    def Programming_Error_Offset_changed(self, s):
        self.Programming_Error_Offset = s

    def Readback_Error_Gain_changed(self, s):
        self.Readback_Error_Gain = s

    def Readback_Error_Offset_changed(self, s):
        self.Readback_Error_Offset = s

    def minVoltage_changed(self, s):
        self.minVoltage = s

    def maxVoltage_changed(self, s):
        self.maxVoltage = s

    def minCurrent_changed(self, s):
        self.minCurrent = s

    def maxCurrent_changed(self, s):
        self.maxCurrent = s

    def voltage_step_size_changed(self, s):
        self.voltage_step_size = s

    def current_step_size_changed(self, s):
        self.current_step_size = s

    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.setFunction = "Voltage"

        elif s == "Current Priority":
            self.setFunction = "Current"

        elif s == "Resistance Priority":
            self.setFunction = "Resistance"

    def set_VoltageRes_changed(self, s):
        self.VoltageRes = s

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.VoltageSense = "INT"
        elif s == "4 Wire":
            self.VoltageSense = "EXT"

    def setRange(self, value):
        AdvancedSettingsList[0] = value

    def setAperture(self, value):
        AdvancedSettingsList[1] = value

    def setAutoZero(self, value):
        AdvancedSettingsList[2] = value

    def setInputZ(self, value):
        AdvancedSettingsList[3] = value

    def checkbox_state_Report(self, s):
        self.checkbox_data_Report = s

    def checkbox_state_Image(self, s):
        self.checkbox_data_Image = s

    def checkbox_state_lock(self, state):
        lockable_widgets = (QPushButton, QLineEdit, QTextEdit, QComboBox)

        for widget in self.findChildren(lockable_widgets):
            widget.setDisabled(state == 2)  # Disable if checkbox is checked

    def setUpTime(self, value):
        AdvancedSettingsList[4] = value

    def setDownTime(self, value):
        AdvancedSettingsList[5] = value

    def openDialog(self):
        dlg = AdvancedSetting_Current()
        dlg.exec()

    def estimateTime(self):
        
        #self.OutputBox.append(str(self.updatedelay))
        try:
            self.currloop = ((float(self.maxCurrent) - float(self.minCurrent))/ float(self.current_step_size)) + 1
            self.voltloop = ((float(self.maxVoltage) - float(self.minVoltage))/ float(self.voltage_step_size)) + 1

            if self.updatedelay == 0.0:
                constant = 0
                    
            else:
                constant = 1

            self.estimatetime = (self.currloop * self.voltloop *(0.2 + 0.8 + (float(self.updatedelay) * constant) )) * float(self.noofloop)
            self.OutputBox.append(f"{self.estimatetime} seconds")
            self.OutputBox.append("") 
        except Exception as e:
            QMessageBox.warning(self, "Warning", "Input cannot be empty!")
            return

    def savepath(self):  
        # Create a Tkinter root window
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open a directory dialog and return the selected directory path
        directory = filedialog.askdirectory()
        self.savelocation = directory
        self.OutputBox.append(str(self.savelocation))

    def executeTest(self):
        global globalvv
        try:
            for x in range (int(self.noofloop)):

                """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
                then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
                will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
                begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
                begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
                are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
                optionally export all the details into a CSV file or display a graph after the test is completed.

                """
            self.infoList = []
            self.dataList = []
            self.dataList2 = []
            self.setEnabled(False)

            dict = dictGenerator.input(
                V_Rating=self.Voltage_Rating,
 		        rshunt=self.rshunt,
                power=self.Power,
                estimatetime=self.estimatetime,
                updatedelay=self.updatedelay,
                readbackvoltage=self.readbackvoltage,
                readbackcurrent=self.readbackcurrent,
                noofloop=self.noofloop,
                Instrument=self.DMM_Instrument,
                Programming_Error_Gain=self.Programming_Error_Gain,
                Programming_Error_Offset=self.Programming_Error_Offset,
                Readback_Error_Gain=self.Readback_Error_Gain,
                Readback_Error_Offset=self.Readback_Error_Offset,
                unit=self.unit,
                minCurrent=self.minCurrent,
                maxCurrent=self.maxCurrent,
                current_step_size=self.current_step_size,
                minVoltage=self.minVoltage,
                maxVoltage=self.maxVoltage,
                voltage_step_size=self.voltage_step_size,
                selected_DUT=self.selected_text,
                PSU=self.PSU,
                DMM2=self.DMM2,
                OperationMode=self.SPOperationMode,
                ELoad=self.ELoad,
                ELoad_Channel=self.ELoad_Channel,
                PSU_Channel=self.PSU_Channel,
                VoltageSense=self.VoltageSense,
                VoltageRes=self.VoltageRes,
                setFunction=self.setFunction,
                Range=AdvancedSettingsList[0],
                Aperture=AdvancedSettingsList[1],
                AutoZero=AdvancedSettingsList[2],
                InputZ=AdvancedSettingsList[3],
                UpTime=AdvancedSettingsList[4],
                DownTime=AdvancedSettingsList[5],
            )

            """ # Check for missing parameters
            missing = self.check_missing_params(dict)
            if missing:
                print(f"The following parameters are missing or empty: {missing}")
                return"""

            """#Function: Visa Address Check & Run Test
            A = VisaResourceManager()
            flag, args = A.openRM(self.ELoad, self.PSU, self.DMM)
            if flag == 0:
                string = ""
                for item in args:
                    string = string + item

                QMessageBox.warning(self, "VISA IO ERROR", string)
                return"""
            
            QMessageBox.warning(
            self,
            "In Progress",
            "Measurement will start now , please do not close the main window until test is completed",
                                )
            # globalvv = dict["estimatetime"]
            # loading_thread = threading.Thread(target=self.tkinter_loading_screen, args=(globalvv,))
            # loading_thread.start()

            #Execute Voltage Measurement
            relay_current = RelayController_Current()
            if self.relay_current == "RELAY":

                relay_current.relay_on()
            else:
                relay_current.relay_off()

            if self.DMM_Instrument == "Keysight":

                if self.selected_text == "Dolphin":
                    if self.ELoad != "None" and self.DMM2 != "None":
                        print("ELoad connected and DMM connected") #All connected
                        try:(
                            self.infoList,
                            self.dataList,
                            self.dataList2
                            ) = DolphinNewCurrentMeasurementwithELoad.executeCurrentMeasurementA(self, dict, self.PSU_Channel)
                    
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return

                    elif self.ELoad == "None" and self.DMM2 != "None":
                        print("No ELoad connected and DMM connected") #No Eload connected but DMM connected
                        try:(
                            self.infoList,
                            self.dataList,
                            self.dataList2
                            ) = DolphinNewCurrentMeasurementNoELoadWithDMM.executeCurrentMeasurementA(self, dict, self.PSU_Channel)
                          
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return
                    
                    elif self.ELoad != "None" and self.DMM2 == "None":
                        print("ELoad connected and No DMM connected") #Eload connected but no DMM connected
                        try:(
                            self.infoList,
                            self.dataList,
                            self.dataList2
                            ) = DolphinNewCurrentMeasurementwithELoadNoDMM.executeCurrentMeasurementA(self, dict, self.PSU_Channel)
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return
                    else :
                        print("No ELoad connected and No DMM connected") #No Eload connected and
                        try:(
                            self.infoList,
                            self.dataList,
                            self.dataList2
                            ) = DolphinNewCurrentMeasurementNoELoadNoDMM.executeCurrentMeasurementA(self, dict, self.PSU_Channel)
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return
                        
            relay_current.relay_off()
                        
            if x == (int(self.noofloop) - 1):   
                self.OutputBox.append(my_result.getvalue())
                self.OutputBox.append("Measurement is complete !")


                if self.checkbox_data_Report == 2:
                    instrumentData(self.PSU, self.DMM2, self.ELoad)
                    datatoCSV_Accuracy(self.infoList, self.dataList, self.dataList2)
                    datatoGraph2(self.infoList, self.dataList, self.dataList2)
                    datatoGraph2.scatterCompareCurrent2(self, float(self.Programming_Error_Gain), float(self.Programming_Error_Offset), float(self.Readback_Error_Gain), float(self.Readback_Error_Offset), str(self.unit), float(self.Current_Rating))

                    A = xlreport(save_directory=self.savelocation, file_name=str(self.unit))
                    A.run()
                    df = pd.DataFrame.from_dict(dict, orient="index")
                    df.to_csv(os.path.join(csv_folder,"config.csv"))

           
                if self.checkbox_data_Image == 2:
                    self.image_dialog = image_Window()
                    self.image_dialog.setModal(True)
                    self.image_dialog.show()    



        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

            return
        finally:
            self.setEnabled(True)

class CV_LoadRegulationDialog(QDialog):
    """Class for configuring the Load Regulation under CV Mode DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py


    """

    def __init__(self):
        """ "Method declaring the Widgets, Signals & Slots for Load Regulation under CV Mode."""
        super().__init__()
         # Default Values
        self.Power_Rating = "2200"
        self.Current_Rating = "120"
        self.Voltage_Rating = "80"
        self.PSU = ""
        self.DMM = ""
        self.ELoad = ""
        self.ELoad_Channel = "1"
        self.PSU_Channel = "1"
        self.DMM_Instrument = "Keysight"
        self.Programming_Error_Offset = "0.0001"
        self.Programming_Error_Gain = "0.0001"
        self.Readback_Error_Offset = "0.0001"
        self.Readback_Error_Gain = "0.0001"
        
        self.SPOperationMode = "Independent"
        self.relay_voltage = "None"

        self.updatedelay = "5"
        self.savelocation = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"

        self.setFunction = "Current"
        self.VoltageRes = "SLOW"
        self.VoltageSense = "EXT"
        self.checkbox_data_Report = 2
        self.checkbox_data_Image = 2
        self.Range = "Auto"
        self.Aperture = "10"
        self.AutoZero = "ON"
        self.inputZ = "ON"
        self.UpTime = "50"
        self.DownTime = "50"

        self.setWindowTitle("Load Regulation (CV)")
        self.image_window = None
        self.setWindowFlags(Qt.Window)

        QPushButton_Widget0 = QPushButton()
        QPushButton_Widget0.setText("Save Path")
        QPushButton_Widget1 = QPushButton()
        QPushButton_Widget1.setText("Execute Test")
        QPushButton_Widget2 = QPushButton()
        QPushButton_Widget2.setText("Advanced Settings")
        QPushButton_Widget4 = QPushButton()
        QPushButton_Widget4.setText("Find Instruments")
         #Output Display
        self.OutputBox = QTextBrowser()
        self.OutputBox.append(f"{my_result.getvalue()}")
        self.OutputBox.append("")  # Empty line after each append

        Desp0 = QLabel()
        Desp1 = QLabel()
        Desp2 = QLabel()
        Desp3 = QLabel()
        Desp4 = QLabel()
        Desp8 = QLabel()

        Desp0.setFont (desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp8.setFont(desp_font)

        Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Specification:")
        Desp8.setText("External Auxiliary Equipment:")

        #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location/Output Wndow:")

       # Connections section
        QLabel_PSU_VisaAddress = QLabel()
        QLabel_DMM_VisaAddress = QLabel()
        QLabel_ELoad_VisaAddress = QLabel()
        QLabel_DMM_Instrument = QLabel()
        QLabel_DUT = QLabel()
        QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        QLabel_DMM_VisaAddress.setText("Visa Address (DMM):")
        QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DMM_Instrument.setText("Instrument Type (DMM):")
        QLabel_DUT.setText("DUT:")
        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_DMM_VisaAddress = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        self.QComboBox_DMM_Instrument = QComboBox()
        self.QComboBox_DUT = QComboBox()

        # General Settings
        QLabel_Voltage_Res = QLabel()
        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
        QLabel_Power_Rating = QLabel()
        QLabel_Max_Voltage = QLabel()
        QLabel_Max_Current = QLabel()
        QLabel_Programming_Error_Gain = QLabel()
        QLabel_Programming_Error_Offset = QLabel()
        QLabel_Readback_Error_Gain = QLabel()
        QLabel_Readback_Error_Offset = QLabel()

        QLabel_Voltage_Res.setText("Voltage Resolution (DMM):")
        QLabel_set_PSU_Channel.setText("Set PSU Channel:")
        QLabel_set_ELoad_Channel.setText("Set Eload Channel:")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        QLabel_Power_Rating.setText("Power Rating (W):")
        QLabel_Max_Voltage.setText("Maximum Voltage (V):")
        QLabel_Max_Current.setText("Maximum Current (A):")
        QLabel_Programming_Error_Gain.setText("Programming Desired Specification (Gain):")
        QLabel_Programming_Error_Offset.setText("Programming Desired Specification (Offset):")
        QLabel_Readback_Error_Gain.setText("Readback Desired Specification (Gain):")
        QLabel_Readback_Error_Offset.setText("Readback Desired Specification (Offset):")

        # External Auxiliary Equipment section
        QLabel_External_Auxiliary_Equipment = QLabel()
        QLabel_External_Auxiliary_Equipment.setText("Relay")
        self.QComboBox_External_Auxiliary_Equipment = QComboBox()
        self.QComboBox_External_Auxiliary_Equipment.addItems(["None", "RELAY"])

        self.QComboBox_Voltage_Res = QComboBox()
        self.QComboBox_set_PSU_Channel = QComboBox()
        self.QComboBox_set_ELoad_Channel = QComboBox()
        self.QComboBox_Voltage_Sense = QComboBox()
        self.QComboBox_set_Function = QComboBox()
        self.QLineEdit_Power_Rating = QLineEdit()
        self.QLineEdit_Max_Voltage = QLineEdit()
        self.QLineEdit_Max_Current = QLineEdit()
        self.QLineEdit_Programming_Error_Gain = QLineEdit()
        self.QLineEdit_Programming_Error_Offset = QLineEdit()
        self.QLineEdit_Readback_Error_Gain = QLineEdit()
        self.QLineEdit_Readback_Error_Offset = QLineEdit()

        self.QLineEdit_PSU_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"])
        self.QLineEdit_DMM_VisaAddress.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_ELoad_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"])
        self.QComboBox_DUT.addItems(["Others", "Excavator", "EDU36311A", "Dolphin", "Hornbill", "SMU"])

        self.QComboBox_DMM_Instrument.addItems(["Keysight", "Keithley"])
        self.QComboBox_Voltage_Res.addItems(["SLOW", "MEDIUM", "FAST"])
        self.QComboBox_set_Function.addItems(
            [
                "Current Priority✅",
                "Voltage Priority",
                "Resistance Priority",
            ]
        )

        self.QComboBox_set_Function.setEnabled(False)
        self.QComboBox_set_PSU_Channel.addItems(["1", "2", "3", "4"])
        self.QComboBox_set_PSU_Channel.setEnabled(True)
        self.QComboBox_set_ELoad_Channel.addItems(["1", "2"])
        self.QComboBox_set_ELoad_Channel.setEnabled(True)
        self.QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])
        self.QComboBox_Voltage_Sense.setEnabled(True)

        #Create a horizontal layout for the "Save Path" and checkboxes
        save_path_layout = QVBoxLayout()
        save_path_layout.addWidget(QLabel_Save_Path)  # QLabel for "Save Path"
    
        #Execute Layout + Outputbox in Right Container
        Right_container = QVBoxLayout()
        exec_layout_box = QHBoxLayout()
        exec_layout = QFormLayout()

        #exec_layout.addRow(Desp0)
        exec_layout.addWidget(self.OutputBox)
        exec_layout.addRow(QPushButton_Widget0)

        exec_layout.addRow(QPushButton_Widget2)
        exec_layout.addRow(QPushButton_Widget1)   

        exec_layout_box.addLayout(exec_layout)
 
        Right_container.addLayout(save_path_layout)
        Right_container.addLayout(exec_layout_box)

        #Setting Form Layout with Left Container
        Left_container = QHBoxLayout()
        setting_layout = QFormLayout()

        setting_layout .addRow(Desp0)
        setting_layout.addRow(QPushButton_Widget0)

        setting_layout.addRow(Desp1)
        setting_layout.addRow(QPushButton_Widget4)
        setting_layout.addRow(QLabel_DUT, self.QComboBox_DUT)
        setting_layout.addRow(QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        setting_layout.addRow(QLabel_DMM_VisaAddress, self.QLineEdit_DMM_VisaAddress)
        setting_layout.addRow(QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        setting_layout.addRow(QLabel_DMM_Instrument, self.QComboBox_DMM_Instrument)
        setting_layout.addRow(Desp2)
        setting_layout.addRow(QLabel_set_PSU_Channel, self.QComboBox_set_PSU_Channel)
        setting_layout.addRow(QLabel_set_ELoad_Channel, self.QComboBox_set_ELoad_Channel)
        setting_layout.addRow(QLabel_set_Function, self.QComboBox_set_Function)
        setting_layout.addRow(QLabel_Voltage_Sense, self.QComboBox_Voltage_Sense)
        setting_layout.addRow(Desp8)
        setting_layout.addRow(QLabel_External_Auxiliary_Equipment, self.QComboBox_External_Auxiliary_Equipment)
        setting_layout.addRow(Desp3)
        setting_layout.addRow(QLabel_Power_Rating, self.QLineEdit_Power_Rating)
        setting_layout.addRow(QLabel_Max_Voltage, self.QLineEdit_Max_Voltage)
        setting_layout.addRow(QLabel_Max_Current, self.QLineEdit_Max_Current)
        setting_layout.addRow(QLabel_Programming_Error_Gain, self.QLineEdit_Programming_Error_Gain)
        setting_layout.addRow(QLabel_Programming_Error_Offset, self.QLineEdit_Programming_Error_Offset)
        setting_layout.addRow(QLabel_Readback_Error_Gain, self.QLineEdit_Readback_Error_Gain)
        setting_layout.addRow(QLabel_Readback_Error_Offset, self.QLineEdit_Readback_Error_Offset)
        setting_layout.addRow(QPushButton_Widget2)
        setting_layout.addRow(QPushButton_Widget1)
        setting_layout.addRow(self.OutputBox)
        Left_container.addLayout(setting_layout)
        #Main Layout
        Main_Layout = QHBoxLayout()
        Main_Layout.addLayout(Left_container,stretch= 2)
        Main_Layout.addLayout(Right_container,stretch = 1)
        self.setLayout(Main_Layout)
        scroll_area(self,Main_Layout)

       
        AdvancedSettingsList.append(self.Range)
        AdvancedSettingsList.append(self.Aperture)
        AdvancedSettingsList.append(self.AutoZero)
        AdvancedSettingsList.append(self.inputZ)
        AdvancedSettingsList.append(self.UpTime)
        AdvancedSettingsList.append(self.DownTime)
        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_DMM_VisaAddress.currentTextChanged.connect(self.DMM_VisaAddress_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)
        self.QComboBox_DUT.currentTextChanged.connect(self.DUT_changed)
        self.QComboBox_set_PSU_Channel.currentTextChanged.connect(self.PSU_Channel_changed)
        self.QComboBox_set_ELoad_Channel.currentTextChanged.connect(self.ELoad_Channel_changed)
        self.QComboBox_External_Auxiliary_Equipment.currentTextChanged.connect(self.External_Auxiliary_Equipment_changed)
        self.QComboBox_DUT.currentIndexChanged.connect(self.on_current_index_changed)
        self.QComboBox_Voltage_Res.currentTextChanged.connect(self.set_VoltageRes_changed)
        self.QLineEdit_Power_Rating.textEdited.connect(self.Power_Rating_changed)
        self.QLineEdit_Max_Current.textEdited.connect(self.Max_Current_changed)
        self.QLineEdit_Max_Voltage.textEdited.connect(self.Max_Voltage_changed)
        self.QLineEdit_Programming_Error_Gain.textEdited.connect(self.Programming_Error_Gain_changed)
        self.QLineEdit_Programming_Error_Offset.textEdited.connect(self.Programming_Error_Offset_changed)
        self.QLineEdit_Readback_Error_Gain.textEdited.connect(self.Readback_Error_Gain_changed)
        self.QLineEdit_Readback_Error_Offset.textEdited.connect(self.Readback_Error_Offset_changed)
        self.QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)
        self.QComboBox_Voltage_Sense.currentTextChanged.connect(self.set_VoltageSense_changed)
        self.QComboBox_DMM_Instrument.currentTextChanged.connect(self.DMM_Instrument_changed)
        QPushButton_Widget4.clicked.connect(self.doFind)
        QPushButton_Widget1.clicked.connect(self.executeTest)
        QPushButton_Widget2.clicked.connect(self.openDialog)
        QPushButton_Widget0.clicked.connect(self.savepath)
    
    def External_Auxiliary_Equipment_changed(self, s):
        if s == "None":
            self.relay_voltage = "None"
        else:
            self.relay_voltage = "RELAY"

    def on_current_index_changed(self):
        selected_text = self.QComboBox_DUT.currentText()
        self.update_selection(selected_text)
        self.QLineEdit_Programming_Error_Gain.setText(self.Programming_Error_Gain)
        self.QLineEdit_Programming_Error_Offset.setText(self.Programming_Error_Offset)
        self.QLineEdit_Readback_Error_Gain.setText(self.Readback_Error_Gain)
        self.QLineEdit_Readback_Error_Offset.setText(self.Readback_Error_Offset)
        self.QLineEdit_Power_Rating.setText(self.Power_Rating)
        self.QLineEdit_Max_Voltage.setText(self.Voltage_Rating)
        self.QLineEdit_Max_Current.setText(self.Current_Rating)
        self.QComboBox_set_PSU_Channel.setCurrentIndex(int(self.PSU_Channel))
        self.QComboBox_set_ELoad_Channel.setCurrentIndex(int(self.ELoad_Channel))
        self.QComboBox_Voltage_Sense.setCurrentText("4 Wire" if self.VoltageSense == "EXT" else "2 Wire")


    
    def update_selection(self, selected_text):
        """Update selected text and reload config file"""
        self.selected_text = selected_text
        self.load_data()
    
    
    def load_data(self):
        """Reads configuration file and returns a dictionary of key-value pairs."""
        config_data = {}
        if self.selected_text =="Excavator":
            self.config_file = os.path.join(config_folder,"config_Excavator.txt")
            
        elif self.selected_text =="Dolphin":
            self.config_file = os.path.join(config_folder,"config_Dolphin.txt")
            
        elif self.selected_text =="SMU":
            self.config_file = os.path.join(config_folder,"config_SMU.txt")

        else:
            self.config_file = os.path.join(config_folder,"config_Others.txt")

        try:
            with open(self.config_file, "r") as file: 
                for line in file:

                    if not line or line.startswith("#") or line.startswith("//"):
                        continue 

                    if "=" in line:
                        key, value = line.strip().split("=")
                        config_data[key.strip()] = value.strip()

            for key, value in config_data.items():
                if key == "savelocation":
                    # If savelocation has a valid value, do not overwrite it
                    if self.savelocation and self.savelocation != "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
                        continue 
                    else:
                        setattr(self, key, value)
                else:
                    setattr(self, key, value)

        except FileNotFoundError:
            print("Config file not found. Using default values.")

        return config_data


    def DUT_changed(self, s):
        self.DUT = s
    
    def PSU_Channel_changed(self, s):
        self.PSU_Channel = s

    def ELoad_Channel_changed(self, s):
        self.ELoad_Channel = s

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_DMM_VisaAddress.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()
            
            self.visaIdList, self.nameList = GetVisaSCPIResources()
            
            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])
            
            # Add "None" option at the end
            self.QLineEdit_PSU_VisaAddress.addItem("None")
            self.QLineEdit_DMM_VisaAddress.addItem("None")
            self.QLineEdit_ELoad_VisaAddress.addItem("None")
                
        except:
            self.OutputBox.append("No Devices Found!!!")
        return 
    
    def updatedelay_changed(self, value):
        self.updatedelay = value
        self.OutputBox.append(str(self.updatedelay))

    def RangeChanged(self, s):
        AdvancedSettingsList[0] = s

    def ApertureChanged(self, s):
        AdvancedSettingsList[1] = s

    def AutoZeroChanged(self, s):
        AdvancedSettingsList[2] = s

    def InputZChanged(self, s):
        AdvancedSettingsList[3] = s

    def UpTimeChanged(self, s):
        AdvancedSettingsList[4] = s

    def DownTimeChanged(self, s):
        AdvancedSettingsList[5] = s

    def Programming_Error_Gain_changed(self, s):
        self.Programming_Error_Gain = s

    def Programming_Error_Offset_changed(self, s):
        self.Programming_Error_Offset = s

    def Readback_Error_Gain_changed(self, s):
        self.Readback_Error_Gain = s

    def Readback_Error_Offset_changed(self, s):
        self.Readback_Error_Offset = s

    def Power_Rating_changed(self, s):
        self.Power_Rating = s

    def Max_Current_changed(self, s):
        self.Current_Rating = s

    def Max_Voltage_changed(self, s):
        self.Voltage_Rating = s

    def DMM_Instrument_changed(self, s):
        self.DMM_Instrument = s

    def PSU_VisaAddress_changed(self, s):
        self.PSU = s

    def DMM_VisaAddress_changed(self, s):
        self.DMM = s

    def ELoad_VisaAddress_changed(self, s):
        self.ELoad = s

    #def ELoad_Channel_changed(self, s):
       # self.ELoad_Channel = s

    #def PSU_Channel_changed(self, s):
        #self.PSU_Channel = s

    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.setFunction = "Voltage"

        elif s == "Current Priority":
            self.setFunction = "Current"

        elif s == "Resistance Priority":
            self.setFunction = "Resistance"

    def set_VoltageRes_changed(self, s):
        self.VoltageRes = s

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.VoltageSense = "INT"
        elif s == "4 Wire":
            self.VoltageSense = "EXT"

    def setRange(self, value):
        AdvancedSettingsList[0] = value

    def setAperture(self, value):
        AdvancedSettingsList[1] = value

    def setAutoZero(self, value):
        AdvancedSettingsList[2] = value

    def setInputZ(self, value):
        AdvancedSettingsList[3] = value
    
    def checkbox_state_Report(self, s):
        self.checkbox_data_Report = s

    def checkbox_state_Image(self, s):
        self.checkbox_data_Image = s


    def setUpTime(self, value):
        AdvancedSettingsList[4] = value

    def setDownTime(self, value):
        AdvancedSettingsList[5] = value
    
    def savepath(self):  
        # Create a Tkinter root window
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open a directory dialog and return the selected directory path
        directory = filedialog.askdirectory()
        self.savelocation = directory
        self.OutputBox.append(str(self.savelocation))

    def executeTest(self):
        try:
            """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
            then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
            will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
            begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
            begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
            are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
            optionally export all the details into a CSV file or display a graph after the test is completed.

                """
            dict = dictGenerator.input(
                
                savedir=self.savelocation,
                Instrument=self.DMM_Instrument,
                #Error_Gain=self.Error_Gain,
                #Error_Offset=self.Error_Offset,
                updatedelay=self.updatedelay,
                Programming_Error_Gain=self.Programming_Error_Gain,
                Programming_Error_Offset=self.Programming_Error_Offset,
                Readback_Error_Gain=self.Readback_Error_Gain,
                Readback_Error_Offset=self.Readback_Error_Offset,
                V_Rating=self.Voltage_Rating,
                I_Rating=self.Current_Rating,
                P_Rating=self.Power_Rating,
                power = self.Power_Rating,
                maxVoltage=self.Voltage_Rating,
                maxCurrent=self.Current_Rating,
                Load_Programming_Error_Gain=self.Programming_Error_Gain,
                Load_Programming_Error_Offset=self.Programming_Error_Offset,
                Load_Readback_Error_Gain=self.Readback_Error_Gain,  
                PSU=self.PSU,
                DMM=self.DMM,
                ELoad=self.ELoad,
                ELoad_Channel=self.ELoad_Channel,
                PSU_Channel=self.PSU_Channel,
                OperationMode=self.SPOperationMode,
                VoltageSense=self.VoltageSense,
                VoltageRes=self.VoltageRes,
                setFunction=self.setFunction,
                Range=AdvancedSettingsList[0],
                Aperture=AdvancedSettingsList[1],
                AutoZero=AdvancedSettingsList[2],
                InputZ=AdvancedSettingsList[3],
                UpTime=AdvancedSettingsList[4],
                DownTime=AdvancedSettingsList[5],
            )
            QMessageBox.warning(
                self,
                "In Progress",
                "Measurement will start now , please do not close the main window until test is completed",
            )
            #Execute Voltage Measurement
            relay_voltage = RelayController_Voltage()
            if self.relay_voltage == "RELAY":

                relay_voltage.relay_on()
            else:
                relay_voltage.relay_off()

            if self.DMM_Instrument == "Keysight":
                if self.selected_text == "Dolphin":
                    if self.ELoad != "None" and self.DMM != "None":
                        try:
                            DolphinLoadRegulationwithELoad.executeCV_LoadRegulationA(self, dict)
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            exit()
                    elif self.ELoad == "None" and self.DMM != "None":
                        self.OutputBox.append("No ELoad connected and DMM connected") #No Eload connected but DMM connected)
                        return
                    elif self.ELoad != "None" and self.DMM == "None":
                        self.OutputBox.append("ELoad connected and No DMM connected") #Eload connected
                        return
                    else :
                        self.OutputBox.append("No ELoad connected and No DMM connected") #No Eload connected and No DMM connected
                        return

            relay_voltage.relay_off()
            self.OutputBox.append(my_result.getvalue())
            self.OutputBox.append("Measurement is complete !")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
    

    def openDialog(self):
        dlg = AdvancedSetting_Voltage()
        dlg.exec()

class CC_LoadRegulationDialog(QDialog):
    """Class for configuring the  Load Regulation under CC Mode DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py

    """

    def __init__(self):
        """ "Method declaring the Widgets, Signals & Slots for Load Regulation under CV Mode."""
        super().__init__()

        # Default Values
        self.rshunt = "0.01"
        self.Power_Rating = "2200"
        self.Power = self.Power_Rating
        self.Current_Rating = "100"
        self.Voltage_Rating = "80"
        self.maxCurrent = self.Current_Rating
        self.maxVoltage = self.Voltage_Rating
        self.PSU = ""
        self.DMM2 = ""
        self.ELoad = ""
        self.ELoad_Channel = ""
        self.PSU_Channel = ""
        self.DMM_Instrument = "Keysight"
        self.DMM_Instrument = "Keysight"
        self.Programming_Error_Offset = "0.0005"
        self.Programming_Error_Gain = "0.0005"
        self.Readback_Error_Offset = "0.0005"
        self.Readback_Error_Gain = "0.0005"

        self.SPOperationMode = "Independent"
        self.relay_current = "None"

        self.updatedelay = "4"
        self.savelocation = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"

        self.setFunction = "Voltage"
        self.VoltageRes = "SLOW"
        self.VoltageSense = "INT"
        self.checkbox_data_Report = 2
        self.checkbox_data_Image = 2
        self.Range = "Auto"
        self.Aperture = "10"
        self.AutoZero = "ON"
        self.inputZ = "ON"
        self.Terminal = "3A"
        self.UpTime = "50"
        self.DownTime = "50"

        self.setWindowTitle("Load Regulation (CC)")
        self.image_window = None
        self.setWindowFlags(Qt.Window)

        QPushButton_Widget0 = QPushButton()
        QPushButton_Widget0.setText("Save Path")
        QPushButton_Widget1 = QPushButton()
        QPushButton_Widget1.setText("Execute Test")
        QPushButton_Widget2 = QPushButton()
        QPushButton_Widget2.setText("Advanced Settings")
        QPushButton_Widget4 = QPushButton()
        QPushButton_Widget4.setText("Find Instruments")
        
         #Output Display
        self.OutputBox = QTextBrowser()
        self.OutputBox.append(f"{my_result.getvalue()}")
        self.OutputBox.append("")  # Empty line after each append

        Desp0 = QLabel()
        Desp1 = QLabel()
        Desp2 = QLabel()
        Desp3 = QLabel()
        Desp4 = QLabel()
        Desp8 = QLabel()
        
        Desp0.setFont (desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp8.setFont(desp_font)

        Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Specification:")
        Desp8.setText("External Auxiliary Equipment:")

         #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location:")

       # Connections section
        QLabel_PSU_VisaAddress = QLabel()
        QLabel_DMM_VisaAddress = QLabel()
        QLabel_ELoad_VisaAddress = QLabel()
        QLabel_DMM_Instrument = QLabel()
        QLabel_DUT = QLabel()
        QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        QLabel_DMM_VisaAddress.setText("Visa Address (DMM):")
        QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DMM_Instrument.setText("Instrument Type (DMM):")
        QLabel_DUT.setText("DUT:")
        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_DMM_VisaAddress = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        self.QComboBox_DMM_Instrument = QComboBox()
        self.QComboBox_DUT = QComboBox()

        # General Settings
        QLabel_Voltage_Res = QLabel()
        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
        QLabel_Power_Rating = QLabel()
        QLabel_Max_Voltage = QLabel()
        QLabel_Max_Current = QLabel()
        QLabel_Programming_Error_Gain = QLabel()
        QLabel_Programming_Error_Offset = QLabel()
        QLabel_Readback_Error_Gain = QLabel()
        QLabel_Readback_Error_Offset = QLabel()

        QLabel_Voltage_Res.setText("Voltage Resolution (DMM):")
        QLabel_set_PSU_Channel.setText("Set PSU Channel:")
        QLabel_set_ELoad_Channel.setText("Set Eload Channel:")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        QLabel_Power_Rating.setText("Power Rating (W):")
        QLabel_Max_Voltage.setText("Maximum Voltage (V):")
        QLabel_Max_Current.setText("Maximum Current (A):")
        QLabel_Programming_Error_Gain.setText("Programming Desired Specification (Gain):")
        QLabel_Programming_Error_Offset.setText("Programming Desired Specification (Offset):")
        QLabel_Readback_Error_Gain.setText("Readback Desired Specification (Gain):")
        QLabel_Readback_Error_Offset.setText("Readback Desired Specification (Offset):")

        #Shunt
        QLabel_rshunt = QLabel()
        QLabel_rshunt.setText("Shunt Resistance Value (ohm):")
        self.QLineEdit_rshunt = QLineEdit()

        # External Auxiliary Equipment section
        QLabel_External_Auxiliary_Equipment = QLabel()
        QLabel_External_Auxiliary_Equipment.setText("Relay")
        self.QComboBox_External_Auxiliary_Equipment = QComboBox()
        self.QComboBox_External_Auxiliary_Equipment.addItems(["None", "RELAY"])

        self.QComboBox_Voltage_Res = QComboBox()
        self.QComboBox_set_PSU_Channel = QComboBox()
        self.QComboBox_set_ELoad_Channel = QComboBox()
        self.QComboBox_Voltage_Sense = QComboBox()
        self.QComboBox_set_Function = QComboBox()
        self.QLineEdit_Power_Rating = QLineEdit()
        self.QLineEdit_Max_Voltage = QLineEdit()
        self.QLineEdit_Max_Current = QLineEdit()
        self.QLineEdit_Programming_Error_Gain = QLineEdit()
        self.QLineEdit_Programming_Error_Offset = QLineEdit()
        self.QLineEdit_Readback_Error_Gain = QLineEdit()
        self.QLineEdit_Readback_Error_Offset = QLineEdit()

        self.QLineEdit_PSU_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"])
        self.QLineEdit_DMM_VisaAddress.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_ELoad_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"])
        self.QComboBox_DUT.addItems(["Others", "Excavator", "EDU36311A", "Dolphin", "Hornbill", "SMU"])

        self.QComboBox_DMM_Instrument.addItems(["Keysight", "Keithley"])
        self.QComboBox_Voltage_Res.addItems(["SLOW", "MEDIUM", "FAST"])
        self.QComboBox_set_Function.addItems(
            [
                "Current Priority✅",
                "Voltage Priority",
                "Resistance Priority",
            ]
        )

        self.QComboBox_set_Function.setEnabled(False)
        self.QComboBox_set_PSU_Channel.addItems(["1", "2", "3", "4"])
        self.QComboBox_set_PSU_Channel.setEnabled(True)
        self.QComboBox_set_ELoad_Channel.addItems(["1", "2"])
        self.QComboBox_set_ELoad_Channel.setEnabled(True)
        self.QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])
        self.QComboBox_Voltage_Sense.setEnabled(True)
        
        #Create a horizontal layout for the "Save Path" and checkboxes
        save_path_layout = QVBoxLayout()
        save_path_layout.addWidget(QLabel_Save_Path)  # QLabel for "Save Path"
    
        #Execute Layout + Outputbox in Right Container
        Right_container = QVBoxLayout()
        exec_layout_box = QHBoxLayout()
        exec_layout = QFormLayout()

        #exec_layout.addRow(Desp0)
        exec_layout.addWidget(self.OutputBox)
        exec_layout.addRow(QPushButton_Widget0)

        exec_layout.addRow(QPushButton_Widget2)
        exec_layout.addRow(QPushButton_Widget1)   

        exec_layout_box.addLayout(exec_layout)
 
        Right_container.addLayout(save_path_layout)
        Right_container.addLayout(exec_layout_box)

        #Setting Form Layout with Left Container
        Left_container = QHBoxLayout()
        setting_layout = QFormLayout()

        setting_layout .addRow(Desp0)
        setting_layout.addRow(QPushButton_Widget0)

        setting_layout.addRow(Desp1)
        setting_layout.addRow(QPushButton_Widget4)
        setting_layout.addRow(QLabel_DUT, self.QComboBox_DUT)
        setting_layout.addRow(QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        setting_layout.addRow(QLabel_DMM_VisaAddress, self.QLineEdit_DMM_VisaAddress)
        setting_layout.addRow(QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        setting_layout.addRow(QLabel_DMM_Instrument, self.QComboBox_DMM_Instrument)
        setting_layout.addRow(Desp2)
        setting_layout.addRow(QLabel_set_PSU_Channel, self.QComboBox_set_PSU_Channel)
        setting_layout.addRow(QLabel_set_ELoad_Channel, self.QComboBox_set_ELoad_Channel)
        setting_layout.addRow(QLabel_set_Function, self.QComboBox_set_Function)
        setting_layout.addRow(QLabel_Voltage_Sense, self.QComboBox_Voltage_Sense)
        setting_layout.addRow(QLabel_rshunt, self.QLineEdit_rshunt)
        setting_layout.addRow(Desp8)
        setting_layout.addRow(QLabel_External_Auxiliary_Equipment, self.QComboBox_External_Auxiliary_Equipment)
        setting_layout.addRow(Desp3)
        setting_layout.addRow(QLabel_Power_Rating, self.QLineEdit_Power_Rating)
        setting_layout.addRow(QLabel_Max_Voltage, self.QLineEdit_Max_Voltage)
        setting_layout.addRow(QLabel_Max_Current, self.QLineEdit_Max_Current)
        setting_layout.addRow(QLabel_Programming_Error_Gain, self.QLineEdit_Programming_Error_Gain)
        setting_layout.addRow(QLabel_Programming_Error_Offset, self.QLineEdit_Programming_Error_Offset)
        setting_layout.addRow(QLabel_Readback_Error_Gain, self.QLineEdit_Readback_Error_Gain)
        setting_layout.addRow(QLabel_Readback_Error_Offset, self.QLineEdit_Readback_Error_Offset)
        setting_layout.addRow(QPushButton_Widget2)
        setting_layout.addRow(QPushButton_Widget1)
        setting_layout.addRow(self.OutputBox)
        Left_container.addLayout(setting_layout)
        #Main Layout
        Main_Layout = QHBoxLayout()
        Main_Layout.addLayout(Left_container,stretch= 2)
        Main_Layout.addLayout(Right_container,stretch = 1)
        self.setLayout(Main_Layout)
        scroll_area(self,Main_Layout)

        AdvancedSettingsList.append(self.Range)
        AdvancedSettingsList.append(self.Aperture)
        AdvancedSettingsList.append(self.AutoZero)
        AdvancedSettingsList.append(self.inputZ)
        AdvancedSettingsList.append(self.UpTime)
        AdvancedSettingsList.append(self.DownTime)
        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_DMM_VisaAddress.currentTextChanged.connect(self.DMM_VisaAddress_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)
        self.QComboBox_DUT.currentTextChanged.connect(self.DUT_changed)
        self.QComboBox_set_PSU_Channel.currentTextChanged.connect(self.PSU_Channel_changed)
        self.QComboBox_set_ELoad_Channel.currentTextChanged.connect(self.ELoad_Channel_changed)
        self.QLineEdit_rshunt.textEdited.connect(self.rshunt_changed)
        self.QComboBox_External_Auxiliary_Equipment.currentTextChanged.connect(self.External_Auxiliary_Equipment_changed)
        self.QComboBox_DUT.currentIndexChanged.connect(self.on_current_index_changed)
        self.QComboBox_Voltage_Res.currentTextChanged.connect(self.set_VoltageRes_changed)
        self.QLineEdit_Power_Rating.textEdited.connect(self.Power_Rating_changed)
        self.QLineEdit_Max_Current.textEdited.connect(self.Max_Current_changed)
        self.QLineEdit_Max_Voltage.textEdited.connect(self.Max_Voltage_changed)
        self.QLineEdit_Programming_Error_Gain.textEdited.connect(self.Programming_Error_Gain_changed)
        self.QLineEdit_Programming_Error_Offset.textEdited.connect(self.Programming_Error_Offset_changed)
        self.QLineEdit_Readback_Error_Gain.textEdited.connect(self.Readback_Error_Gain_changed)
        self.QLineEdit_Readback_Error_Offset.textEdited.connect(self.Readback_Error_Offset_changed)
        self.QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)
        self.QComboBox_Voltage_Sense.currentTextChanged.connect(self.set_VoltageSense_changed)
        self.QComboBox_DMM_Instrument.currentTextChanged.connect(self.DMM_Instrument_changed)
        QPushButton_Widget4.clicked.connect(self.doFind)
        QPushButton_Widget1.clicked.connect(self.executeTest)
        QPushButton_Widget2.clicked.connect(self.openDialog)
        QPushButton_Widget0.clicked.connect(self.savepath)
    
    def External_Auxiliary_Equipment_changed(self, s):
        if s == "None":
            self.relay_current = "None"
        else:
            self.relay_current = "RELAY"

    def on_current_index_changed(self):
        selected_text = self.QComboBox_DUT.currentText()
        self.update_selection(selected_text)
        self.QLineEdit_Programming_Error_Gain.setText(self.Programming_Error_Gain)
        self.QLineEdit_Programming_Error_Offset.setText(self.Programming_Error_Offset)
        self.QLineEdit_Readback_Error_Gain.setText(self.Readback_Error_Gain)
        self.QLineEdit_Readback_Error_Offset.setText(self.Readback_Error_Offset)
        self.QLineEdit_Power_Rating.setText(self.Power_Rating)
        self.QLineEdit_Max_Voltage.setText(self.Voltage_Rating)
        self.QLineEdit_Max_Current.setText(self.Current_Rating)
        self.QComboBox_set_PSU_Channel.setCurrentIndex(int(self.PSU_Channel))
        self.QComboBox_set_ELoad_Channel.setCurrentIndex(int(self.ELoad_Channel))
        self.QComboBox_Voltage_Sense.setCurrentText("4 Wire" if self.VoltageSense == "EXT" else "2 Wire")
        self.QLineEdit_rshunt.setText(self.rshunt)

    def rshunt_changed(self, value):
        self.rshunt = value

    def update_selection(self, selected_text):
        """Update selected text and reload config file"""
        self.selected_text = selected_text
        self.load_data()
    
    
    def load_data(self):
        """Reads configuration file and returns a dictionary of key-value pairs."""
        config_data = {}
        if self.selected_text =="Excavator":
            self.config_file = os.path.join(config_folder,"config_Excavator.txt")
            
        elif self.selected_text =="Dolphin":
            self.config_file = os.path.join(config_folder,"config_Dolphin.txt")
            
        elif self.selected_text =="SMU":
            self.config_file = os.path.join(config_folder,"config_SMU.txt")

        else:
            self.config_file = os.path.join(config_folder,"config_Others.txt")

        try:
            with open(self.config_file, "r") as file: 
                for line in file:

                    if not line or line.startswith("#") or line.startswith("//"):
                        continue 

                    if "=" in line:
                        key, value = line.strip().split("=")
                        config_data[key.strip()] = value.strip()

            for key, value in config_data.items():
                if key == "savelocation":
                    # If savelocation has a valid value, do not overwrite it
                    if self.savelocation and self.savelocation != "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
                        continue 
                    else:
                        setattr(self, key, value)
                else:
                    setattr(self, key, value)

        except FileNotFoundError:
            print("Config file not found. Using default values.")

        return config_data


    def DUT_changed(self, s):
        self.DUT = s
    
    def PSU_Channel_changed(self, s):
        self.PSU_Channel = s

    def ELoad_Channel_changed(self, s):
        self.ELoad_Channel = s
    
    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_DMM_VisaAddress.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()
            
            self.visaIdList, self.nameList = GetVisaSCPIResources()
            
            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])
            
            # Add "None" option at the end
            self.QLineEdit_PSU_VisaAddress.addItem("None")
            self.QLineEdit_DMM_VisaAddress.addItem("None")
            self.QLineEdit_ELoad_VisaAddress.addItem("None")
                
        except:
            self.OutputBox.append("No Devices Found!!!")
        return 
    
    def updatedelay_changed(self, value):
        self.updatedelay = value
        self.OutputBox.append(str(self.updatedelay))
    
    def Programming_Error_Gain_changed(self, s):
        self.Programming_Error_Gain = s

    def Programming_Error_Offset_changed(self, s):
        self.Programming_Error_Offset = s

    def Readback_Error_Gain_changed(self, s):
        self.Readback_Error_Gain = s

    def Readback_Error_Offset_changed(self, s):
        self.Readback_Error_Offset = s


    def Power_Rating_changed(self, s):
        self.Power_Rating = s

    def Max_Current_changed(self, s):
        self.Current_Rating = s

    def Max_Voltage_changed(self, s):
        self.Voltage_Rating = s

    def DMM_Instrument_changed(self, s):
        self.DMM_Instrument = s

    def PSU_VisaAddress_changed(self, s):
        self.PSU = s

    def DMM_VisaAddress_changed(self, s):
        self.DMM2 = s

    def ELoad_VisaAddress_changed(self, s):
        self.ELoad = s

    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.setFunction = "Voltage"

        elif s == "Current Priority":
            self.setFunction = "Current"

        elif s == "Resistance Priority":
            self.setFunction = "Resistance"

    def set_VoltageRes_changed(self, s):
        self.CurrentRes = s

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.CurrentSense = "INT"
        elif s == "4 Wire":
            self.CurrentSense = "EXT"

    def setRange(self, value):
        AdvancedSettingsList[0] = value

    def setAperture(self, value):
        AdvancedSettingsList[1] = value

    def setAutoZero(self, value):
        AdvancedSettingsList[2] = value

    def setTerminal(self, value):
        AdvancedSettingsList[3] = value

    def setUpTime(self, value):
        AdvancedSettingsList[4] = value

    def setDownTime(self, value):
        AdvancedSettingsList[5] = value
    
    def savepath(self):  
        # Create a Tkinter root window
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open a directory dialog and return the selected directory path
        directory = filedialog.askdirectory()
        self.savelocation = directory
        self.OutputBox.append(str(self.savelocation))

    def executeTest(self):
        try:
            """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
            then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
            will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
            begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
            begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
            are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
            optionally export all the details into a CSV file or display a graph after the test is completed.

            """
            dict = dictGenerator.input(
                rshunt=self.rshunt,
                savedir=self.savelocation,
                Instrument=self.DMM_Instrument,
                #Error_Gain=self.Error_Gain,
                #Error_Offset=self.Error_Offset,
                updatedelay=self.updatedelay,
                Programming_Error_Gain=self.Programming_Error_Gain,
                Programming_Error_Offset=self.Programming_Error_Offset,
                Readback_Error_Gain=self.Readback_Error_Gain,
                Readback_Error_Offset=self.Readback_Error_Offset,
                V_Rating=self.Voltage_Rating,
                I_Rating=self.Current_Rating,
                P_Rating=self.Power_Rating,
                power=self.Power,
                maxVoltage=self.Voltage_Rating,
                maxCurrent=self.Current_Rating,
                PSU=self.PSU,
                DMM2=self.DMM2,
                ELoad=self.ELoad,
                ELoad_Channel=self.ELoad_Channel,
                PSU_Channel=self.PSU_Channel,
                OperationMode=self.SPOperationMode,
                #CurrentSense=self.CurrentSense,
                VoltageSense=self.VoltageSense,
                VoltageRes=self.VoltageRes,
                setFunction=self.setFunction,
                Range=AdvancedSettingsList[0],
                Aperture=AdvancedSettingsList[1],
                AutoZero=AdvancedSettingsList[2],
                InputZ=AdvancedSettingsList[3],
                #Terminal=AdvancedSettingsList[3],
                UpTime=AdvancedSettingsList[4],
                DownTime=AdvancedSettingsList[5],
            )
            QMessageBox.warning(
                self,
                "In Progress",
                "Measurement will start now , please do not close the main window until test is completed",
            )
            #Execute Voltage Measurement
            relay_current = RelayController_Current()
            if self.relay_current == "RELAY":

                relay_current.relay_on()
            else:
                relay_current.relay_off()

            if self.DMM_Instrument == "Keysight":
                if self.selected_text == "Dolphin":
                    if self.ELoad != "None" and self.DMM2 != "None":
                        try:
                            DolphinLoadRegulationwithELoad.executeCC_LoadRegulationA(self, dict)

                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            return

            relay_current.relay_off()
            self.OutputBox.append(my_result.getvalue())
            self.OutputBox.append("Measurement is complete !")

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return

    def openDialog(self):
        dlg = AdvancedSetting_Current()
        dlg.exec()

class TransientRecoveryTime(QDialog):

    """Class for configuring the Transient Recovery Time DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py

    """

    def __init__(self):
        """ "Method declaring the Widgets, Signals & Slots for Transient Recovery Time."""
        super().__init__()

        # Default Values
        self.selected_text = "Dolphin"
        self.PSU = "USB0::0x2A8D::0xCC04::MY00000037::0::INSTR"
        self.OSC = "USB0::0x0957::0x17B0::MY52060151::0::INSTR"
        self.ELoad = "USB0::0x2A8D::0x3902::MY60260005::0::INSTR"
        self.ELoad_Channel = "1"
        self.PSU_Channel = "1"
        self.OSC_Channel = "1"
        self.setFunction = "Current"
        self.relay_voltage = "None"

        self.VoltageSense = "EXT"
        self.Power_Rating = "160"
        self.Current_Rating = "120"
        self.Voltage_Rating = "80"
        self.maxCurrent = "10"
        self.maxVoltage = "80"

        self.Channel_CouplingMode = "AC"
        self.Trigger_CouplingMode = "DC"
        self.Trigger_Mode = "EDGE"
        self.Trigger_SweepMode = "NORMAL"
        self.Trigger_SlopeMode = "EITHer"
        self.TimeScale = "0.01"
        self.VerticalScale = "0.00001"
        self.I_Step = ""
        self.V_Settling_Band = "0.8"
        self.T_Settling_Band = "0.001"
        self.Probe_Setting = "X10"
        self.Acq_Type = "AVERage"

        self.checkbox_SpecialCase = 2
        self.checkbox_NormalCase = 2

        self.savelocation = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"


        self.setWindowTitle("Transient Recovery Time")

        QPushButton_Widget00 = QPushButton()
        QPushButton_Widget00.setText("Save Path")
        QPushButton_Widget0 = QPushButton()
        QPushButton_Widget0.setText("Find Instruments")
        QPushButton_Widget = QPushButton()
        QPushButton_Widget.setText("Execute Test")
        QCheckBox_SpecialCase_Widget = QCheckBox()
        QCheckBox_SpecialCase_Widget.setText("Special Case (0% <-> 100%)")
        QCheckBox_SpecialCase_Widget.setCheckState(Qt.Checked)
        QCheckBox_NormalCase_Widget = QCheckBox()
        QCheckBox_NormalCase_Widget.setText("Normal Case (50% <-> 100%)")
        QCheckBox_NormalCase_Widget.setCheckState(Qt.Checked)
        
        layout1 = QFormLayout()
        self.OutputBox = QTextBrowser()

        self.OutputBox.append(my_result.getvalue())

        Desp0 = QLabel()
        Desp1 = QLabel()
        Desp2 = QLabel()
        Desp3 = QLabel()
        Desp4 = QLabel()
        Desp5 = QLabel()

        Desp0.setFont (desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp5.setFont(desp_font)

        Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Specification:")
        Desp4.setText("Oscilloscope Settings:")
        Desp5.setText("Perform Test:")

        #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location/Output Wndow:")

        # Connections
        self.QLabel_PSU_VisaAddress = QLabel()
        self.QLabel_OSC_VisaAddress = QLabel()
        self.QLabel_ELoad_VisaAddress = QLabel()
 
        self.QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        self.QLabel_OSC_VisaAddress.setText("Visa Address (OSC):")
        self.QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")

        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_OSC_VisaAddress = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()

        # General Settings
        self.QLineEdit_PSU_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"])
        self.QLineEdit_OSC_VisaAddress.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_ELoad_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"])

        QLabel_OSC_Display_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
        QLabel_Power_Rating = QLabel()
        QLabel_maxVoltage = QLabel()
        QLabel_voltage_rated = QLabel()
        QLabel_current_rated = QLabel()
        QLabel_maxCurrent = QLabel()

        QLabel_V_Settling_Band = QLabel()
        QLabel_T_Settling_Band = QLabel()
        QLabel_Probe_Setting = QLabel()
        QLabel_Acq_Type = QLabel()


        """QLabel_ELoad_Display_Channel.setText("Display Channel (Eload):")
        QLabel_PSU_Display_Channel.setText("Display Channel (PSU):")"""
        QLabel_OSC_Display_Channel.setText("Display Channel (OSC)")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        QLabel_Power_Rating.setText("Power Rating (W):")
        QLabel_maxVoltage.setText("Testing Voltage (V):")
        QLabel_voltage_rated.setText("DUT Rated Voltage:")
        QLabel_current_rated.setText("DUT Rated Current:")
        QLabel_maxCurrent.setText("Testing Current (A):")
        
        QLabel_V_Settling_Band.setText("Settling Band Voltage (V) / Error Band:")
        QLabel_T_Settling_Band.setText("Settling Band Time (s):")
        QLabel_Probe_Setting.setText("Probe Setting Ratio:")
        QLabel_Acq_Type.setText("Acquire Mode:")


        """QLineEdit_ELoad_Display_Channel = QLineEdit()
        QLineEdit_PSU_Display_Channel = QLineEdit()"""
        QLineEdit_OSC_Display_Channel = QLineEdit()
        QComboBox_Voltage_Sense = QComboBox()
        QComboBox_set_Function = QComboBox()
        QLineEdit_Power_Rating = QLineEdit()
        QLineEdit_maxVoltage = QLineEdit()
        QLineEdit_voltage_rated = QLineEdit()
        QLineEdit_current_rated = QLineEdit()
        QLineEdit_maxCurrent = QLineEdit()
        
        QLineEdit_V_Settling_Band = QLineEdit()
        QLineEdit_T_Settling_Band = QLineEdit()
        QComboBox_Probe_Setting = QComboBox()
        QComboBox_Acq_Type = QComboBox()

        QComboBox_set_Function.addItems(
            [
                "Current Priority",
                "Voltage Priority",
                "Resistance Priority",
            ]
        )
        QComboBox_set_Function.setEnabled(False)
        QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])

        QComboBox_Probe_Setting.addItems(["X1", "X10", "X20", "X100"])
        QComboBox_Acq_Type.addItems(["NORMal", "PEAK", "AVERage", "HRESolution"])

        # Oscilloscope Settings
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

        QComboBox_Channel_CouplingMode = QComboBox()
        QComboBox_Trigger_Mode = QComboBox()
        QComboBox_Trigger_CouplingMode = QComboBox()
        QComboBox_Trigger_SweepMode = QComboBox()
        QComboBox_Trigger_SlopeMode = QComboBox()
        QLineEdit_TimeScale = QLineEdit()
        QLineEdit_VerticalScale = QLineEdit()

        QComboBox_Channel_CouplingMode.addItems(["AC", "DC"])
        QComboBox_Trigger_Mode.addItems(["EDGE", "IIC", "EBUR"])
        QComboBox_Trigger_CouplingMode.addItems(["AC", "DC"])
        QComboBox_Trigger_SweepMode.addItems(["NORMAL", "AUTO"])
        QComboBox_Trigger_SlopeMode.addItems(["ALT", "POS", "NEG", "EITH"])

        QComboBox_Channel_CouplingMode.setEnabled(True)
        QComboBox_Trigger_Mode.setEnabled(True)
        QComboBox_Trigger_CouplingMode.setEnabled(True)
        QComboBox_Trigger_SweepMode.setEnabled(True)
        QComboBox_Trigger_SlopeMode.setEnabled(True)
        QComboBox_Probe_Setting.setEnabled(True)
        QComboBox_Acq_Type.setEnabled(True)

        # Create a horizontal layout for the "Save Path" and checkboxes
        performtest_layout = QHBoxLayout()
        performtest_layout.addWidget(Desp5)  # QLabel for "Save Path"
        performtest_layout.addWidget(QCheckBox_SpecialCase_Widget)  # Checkbox for "Generate Excel Report"
        performtest_layout.addWidget(QCheckBox_NormalCase_Widget)  # Checkbox for "Show Graph"

        layout1.addRow(Desp0)
        layout1.addRow(QPushButton_Widget00)
        layout1.addRow(self.OutputBox)
        layout1.addRow(QPushButton_Widget0)
        layout1.addRow(Desp1)
        layout1.addRow(self.QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        layout1.addRow(self.QLabel_OSC_VisaAddress, self.QLineEdit_OSC_VisaAddress)
        layout1.addRow(self.QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        layout1.addRow(Desp2)
        """layout1.addRow(QLabel_ELoad_Display_Channel, QLineEdit_ELoad_Display_Channel)
        layout1.addRow(QLabel_PSU_Display_Channel, QLineEdit_PSU_Display_Channel)"""
        layout1.addRow(QLabel_OSC_Display_Channel, QLineEdit_OSC_Display_Channel)
        layout1.addRow(QLabel_set_Function, QComboBox_set_Function)
        layout1.addRow(QLabel_Voltage_Sense, QComboBox_Voltage_Sense)
        layout1.addRow(Desp3)
        layout1.addRow(QLabel_Power_Rating, QLineEdit_Power_Rating)
        layout1.addRow(QLabel_voltage_rated, QLineEdit_voltage_rated)
        layout1.addRow(QLabel_current_rated, QLineEdit_current_rated)
        layout1.addRow(QLabel_maxVoltage, QLineEdit_maxVoltage)
        layout1.addRow(QLabel_maxCurrent, QLineEdit_maxCurrent)
        
        layout1.addRow(QLabel_V_Settling_Band, QLineEdit_V_Settling_Band)
        layout1.addRow(QLabel_T_Settling_Band, QLineEdit_T_Settling_Band)
        layout1.addRow(Desp4)
        layout1.addRow(QLabel_Probe_Setting, QComboBox_Probe_Setting)
        layout1.addRow(QLabel_Acq_Type, QComboBox_Acq_Type)
        layout1.addRow(QLabel_Channel_CouplingMode, QComboBox_Channel_CouplingMode)
        layout1.addRow(QLabel_Trigger_CouplingMode, QComboBox_Trigger_CouplingMode)
        layout1.addRow(QLabel_Trigger_Mode, QComboBox_Trigger_Mode)
        layout1.addRow(QLabel_Trigger_SweepMode, QComboBox_Trigger_SweepMode)
        layout1.addRow(QLabel_Trigger_SlopeMode, QComboBox_Trigger_SlopeMode)
        layout1.addRow(QLabel_TimeScale, QLineEdit_TimeScale)
        layout1.addRow(QLabel_VerticalScale, QLineEdit_VerticalScale)
        layout1.addRow(performtest_layout)
        layout1.addRow(QPushButton_Widget)
        self.setLayout(layout1)

        
        QPushButton_Widget0.clicked.connect(self.doFind)
        QPushButton_Widget.clicked.connect(self.executeTest)
        

        QLineEdit_V_Settling_Band.textEdited.connect(self.V_Settling_Band_changed)
        QLineEdit_T_Settling_Band.textEdited.connect(self.T_Settling_Band_changed)

        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_OSC_VisaAddress.currentTextChanged.connect(self.OSC_VisaAddress_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)
        """QLineEdit_ELoad_Display_Channel.textEdited.connect(self.ELoad_Channel_changed)
        QLineEdit_PSU_Display_Channel.textEdited.connect(self.PSU_Channel_changed)"""
        QLineEdit_OSC_Display_Channel.textEdited.connect(self.OSC_Channel_changed)

        QLineEdit_Power_Rating.textEdited.connect(self.Power_Rating_changed)
        QLineEdit_voltage_rated.textEdited.connect(self.Voltage_Rating_changed)
        QLineEdit_current_rated.textEdited.connect(self.Current_Rating_changed)

        QLineEdit_maxCurrent.textEdited.connect(self.maxCurrent_changed)
        QLineEdit_maxVoltage.textEdited.connect(self.maxVoltage_changed)
        QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)
        QComboBox_Voltage_Sense.currentTextChanged.connect(
            self.set_VoltageSense_changed
        )
        QComboBox_Channel_CouplingMode.currentTextChanged.connect(
            self.Channel_CouplingMode_changed
        )
        QComboBox_Trigger_CouplingMode.currentTextChanged.connect(
            self.Trigger_CouplingMode_changed
        )
        QComboBox_Trigger_Mode.currentTextChanged.connect(self.Trigger_Mode_changed)
        QComboBox_Trigger_SweepMode.currentTextChanged.connect(
            self.Trigger_SweepMode_changed
        )
        QComboBox_Trigger_SlopeMode.currentTextChanged.connect(
            self.Trigger_SlopeMode_changed
        )
        QComboBox_Probe_Setting.currentTextChanged.connect(
            self.Probe_Setting_changed
        )
        QComboBox_Acq_Type.currentTextChanged.connect(
            self.Acq_Type_changed
        )
        QLineEdit_TimeScale.textEdited.connect(self.TimeScale_changed)
        QLineEdit_VerticalScale.textEdited.connect(self.VerticalScale_changed)

        QCheckBox_SpecialCase_Widget.stateChanged.connect(self.checkbox_state_SpecialCase)
        QCheckBox_NormalCase_Widget.stateChanged.connect(self.checkbox_state_NormalCase)

        QPushButton_Widget00.clicked.connect(self.savepath)

    def Voltage_Rating_changed(self, value):
        self.Voltage_Rating = value
    
    def Current_Rating_changed(self, value):
        self.Current_Rating = value

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_OSC_VisaAddress.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()
            
            self.visaIdList, self.nameList = GetVisaSCPIResources()
            
            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_OSC_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])
            
            # Add "None" option at the end
            self.QLineEdit_PSU_VisaAddress.addItem("None")
            self.QLineEdit_OSC_VisaAddress.addItem("None")
            self.QLineEdit_ELoad_VisaAddress.addItem("None")

        except:
            self.OutputBox.append("No Devices Found!!!")
        return 
    
    def checkbox_state_SpecialCase(self, s):
        self.checkbox_SpecialCase = s

    def checkbox_state_NormalCase(self, s):
        self.checkbox_NormalCase = s
    
    def PSU_VisaAddress_changed(self, s):
        self.PSU = s

    def OSC_VisaAddress_changed(self, s):
        self.OSC = s

    def ELoad_VisaAddress_changed(self, s):
        self.ELoad = s
    
    def ELoad_Channel_changed(self, s):
        self.ELoad_Channel = s

    def PSU_Channel_changed(self, s):
        self.PSU_Channel = s

    def OSC_Channel_changed(self, s):
        self.OSC_Channel = s

    def Power_Rating_changed(self, s):
        self.Power_Rating = s

    def maxCurrent_changed(self, s):
        self.maxCurrent = s

    def maxVoltage_changed(self, s):
        self.maxVoltage = s

    def I_Step_changed(self, s):
        self.I_Step = s

    def T_Settling_Band_changed(self, s):
        self.T_Settling_Band = s

    def V_Settling_Band_changed(self, s):
        self.V_Settling_Band = s

    def Channel_CouplingMode_changed(self, s):
        self.Channel_CouplingMode = s

    def Trigger_CouplingMode_changed(self, s):
        self.Trigger_CouplingMode = s

    def Trigger_Mode_changed(self, s):
        self.Trigger_Mode = s

    def Trigger_SweepMode_changed(self, s):
        self.Trigger_SweepMode = s

    def Trigger_SlopeMode_changed(self, s):
        self.Trigger_SlopeMode = s
    
    def Probe_Setting_changed(self, s):
        self.Probe_Setting = s
    
    def Acq_Type_changed(self, s):
        self.Acq_Type = s

    def TimeScale_changed(self, s):
        self.TimeScale = s

    def VerticalScale_changed(self, s):
        self.VerticalScale = s

    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.setFunction = "Voltage"

        elif s == "Current Priority":
            self.setFunction = "Current"

        elif s == "Resistance Priority":
            self.setFunction = "Resistance"

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.VoltageSense = "INT"
        elif s == "4 Wire":
            self.VoltageSense = "EXT"

    def savepath(self):  
        # Create a Tkinter root window
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open a directory dialog and return the selected directory path
        directory = filedialog.askdirectory()
        self.savelocation = directory
        self.OutputBox.append(str(self.savelocation))


    def executeTest(self):
        """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
        then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
        will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
        begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
        begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
        are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
        optionally export all the details into a CSV file or display a graph after the test is completed.

        """
        dict = dictGenerator.input(
            savedir=self.savelocation,
            Instrument="Keysight",
            PSU=self.PSU,
            OSC=self.OSC,
            ELoad=self.ELoad,
            V_Rating=self.Voltage_Rating,
            I_Rating=self.Current_Rating,
            P_Rating=self.Power_Rating,
            power = self.Power_Rating,
            maxCurrent=self.maxCurrent,
            maxVoltage=self.maxVoltage,
            ELoad_Channel=self.ELoad_Channel,
            PSU_Channel=self.PSU_Channel,
            OSC_Channel=self.OSC_Channel,
            VoltageSense=self.VoltageSense,
            setFunction=self.setFunction,
            Channel_CouplingMode=self.Channel_CouplingMode,
            Trigger_Mode=self.Trigger_Mode,
            Trigger_CouplingMode=self.Trigger_CouplingMode,
            Trigger_SweepMode=self.Trigger_SweepMode,
            Trigger_SlopeMode=self.Trigger_SlopeMode,
            Probe_Setting=self.Probe_Setting,
            Acq_Type=self.Acq_Type,
            TimeScale=self.TimeScale,
            VerticalScale=self.VerticalScale,
            
            V_Settling_Band=self.V_Settling_Band,
            T_Settling_Band=self.T_Settling_Band,
        )
        QMessageBox.warning(
            self,
            "In Progress",
            "Measurement will start now , please do not close the main window until test is completed",
        )

        #Execute Voltage Measurement
        relay_voltage = RelayController_Voltage()
        if self.relay_voltage == "RELAY":
            relay_voltage.relay_on()
        else:
            relay_voltage.relay_off()

        
        if self.selected_text == "Dolphin":
            if self.ELoad != "None" and self.OSC != "None":
                print("ELoad connected and DMM connected") #All connected 
                try:
                    if self.checkbox_SpecialCase == 2:
                        DolphinRiseFallTimewithELoad.executeA(self, dict)
                    
                    if self.checkbox_NormalCase == 2:
                        DolphinRiseFallTimewithELoad.executeB(self, dict)

                
                except Exception as e:
                    print(e)
                    QMessageBox.warning(self, "Error", str(e))
                    exit()

        self.OutputBox.append(my_result.getvalue())
        self.OutputBox.append("Measurement is complete !")

class TransientRecoveryTimeWithCurrentSensor(QDialog):

    """Class for configuring the Transient Recovery Time DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py

    """

    def __init__(self):
        """ "Method declaring the Widgets, Signals & Slots for Transient Recovery Time."""
        super().__init__()

        # Default Values
        self.PSU = "USB0::0x2A8D::0xCC04::MY00000037::0::INSTR"
        self.OSC = "USB0::0x0957::0x17B0::MY52060151::0::INSTR"
        self.ELoad = "USB0::0x2A8D::0x3902::MY60260005::0::INSTR"
        self.ELoad_Channel = "1"
        self.PSU_Channel = "2"
        self.DUT_OSC_Channel = "CHANNEL1"
        self.CurrentTrigger_OSC_Channel = "CHANNEL2"
        self.TriggerSource = "CHANNEL2"
        self.setFunction = "Current"

        self.VoltageSense = "EXT"
        self.Power_Rating = "160"
        self.Current_Rating = "120"
        self.Voltage_Rating = "80"
        self.maxCurrent = "10"
        self.maxVoltage = "80"

        self.relay_voltage = "RELAY"
        
        #From OSC view
        self.DUT_Channel_Unit = "VOLT"
        self.DUT_Channel_Offset = "0"
    
        self.DUT_Channel_CouplingMode = "AC"
        self.DUT_Trigger_CouplingMode = "DC"
        self.DUT_Trigger_Mode = "EDGE"
        self.DUT_Trigger_SweepMode = "NORMAL"
        self.DUT_Trigger_SlopeMode = "EITHer"
        self.DUT_TimeScale = "0.01"
        self.DUT_VerticalScale = "0.00001"
        self.DUT_V_Settling_Band = "0.8"
        self.DUT_T_Settling_Band = "0.001"
        self.DUT_Probe_Setting = "X10"
        self.DUT_Acq_Type = "AVERage"
        self.DUT_Unit = "VOLT"


        self.CurrentTrigger_Channel_Unit = "AMPere"
        self.CurrentTrigger_Channel_Offset = "20"
        self.CurrentTrigger_Channel_CouplingMode = "DC"
        self.CurrentTrigger_Trigger_CouplingMode = "DC"
        self.CurrentTrigger_Trigger_Mode = "EDGE"
        self.CurrentTrigger_Trigger_SweepMode = "NORMAL"
        self.CurrentTrigger_Trigger_SlopeMode = "EITHer"
        self.CurrentTrigger_TimeScale = "0.01"
        self.CurrentTrigger_VerticalScale = "20"
        self.CurrentTrigger_V_Settling_Band = "8"
        self.CurrentTrigger_T_Settling_Band = "0.001"
        self.CurrentTrigger_Probe_Setting = "X100"
        self.CurrentTrigger_Acq_Type = "AVERage"
        self.CurrentTrigger_Unit = "AMPere"


        self.I_Step = ""
        

        self.checkbox_SpecialCase = 0
        self.checkbox_NormalCase = 0
        self.checkbox_CurrentCase = 2

        self.savelocation = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"

        self.setWindowTitle("Transient Recovery Time with Current Probe")

        QPushButton_Widget00 = QPushButton()
        QPushButton_Widget00.setText("Save Path")
        QPushButton_Widget0 = QPushButton()
        QPushButton_Widget0.setText("Find Instruments")
        QPushButton_Widget = QPushButton()
        QPushButton_Widget.setText("Execute Test")
        QCheckBox_SpecialCase_Widget = QCheckBox()
        QCheckBox_SpecialCase_Widget.setText("Special Case (0% <-> 100%)")
        QCheckBox_SpecialCase_Widget.setCheckState(Qt.Unchecked)
        QCheckBox_NormalCase_Widget = QCheckBox()
        QCheckBox_NormalCase_Widget.setText("Normal Case without Current Probe (50% <-> 100%)")
        QCheckBox_NormalCase_Widget.setCheckState(Qt.Unchecked)
        QCheckBox_CurrentCase_Widget = QCheckBox()
        QCheckBox_CurrentCase_Widget.setText("Normal Case with Current Probe (50% <-> 100%)")
        QCheckBox_CurrentCase_Widget.setCheckState(Qt.Checked)

        
        layout1 = QFormLayout()
        self.OutputBox = QTextBrowser()

        self.OutputBox.append(my_result.getvalue())

        Desp0 = QLabel()
        Desp1 = QLabel()
        Desp2 = QLabel()
        Desp3 = QLabel()
        Desp4 = QLabel()
        Desp5 = QLabel()
        Desp6 = QLabel()
        Desp8 = QLabel()

        Desp0.setFont (desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp5.setFont(desp_font)
        Desp6.setFont(desp_font)
        Desp8.setFont(desp_font)

        Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Specification:")
        Desp4.setText("DUT Oscilloscope Settings:")
        Desp5.setText("Perform Test:")
        Desp6.setText("Current Trigger Oscilloscope Settings:")
        Desp8.setText("External Auxiliary Equipment:")

        #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location/Output Wndow:")

        # Connections

        QLabel_PSU_VisaAddress = QLabel()
        QLabel_OSC_VisaAddress = QLabel()
        QLabel_ELoad_VisaAddress = QLabel()
        QLabel_DUT = QLabel()

        QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        QLabel_OSC_VisaAddress.setText("Visa Address (OSC):")
        QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DUT.setText("DUT:")

        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_OSC_VisaAddress = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        self.QComboBox_DUT = QComboBox()

        # General Settings
        self.QLineEdit_PSU_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"])
        self.QLineEdit_OSC_VisaAddress.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_ELoad_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"])
        self.QComboBox_DUT.addItems(["Others", "Excavator", "EDU36311A", "Dolphin", "Hornbill", "SMU"])

        QLabel_OSC_DUT_Display_Channel = QLabel() #DUT Source 
        QLabel_OSC_CurrentTrigger_Display_Channel = QLabel() #Current Trigger
        QLabel_Trigger_Source_Display_Channel = QLabel()

        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
        QLabel_Power_Rating = QLabel()
        QLabel_maxVoltage = QLabel()
        QLabel_voltage_rated = QLabel()
        QLabel_current_rated = QLabel()
        QLabel_maxCurrent = QLabel()

        QLabel_DUT_V_Settling_Band = QLabel()
        QLabel_DUT_T_Settling_Band = QLabel()
        QLabel_DUT_Probe_Setting = QLabel()
        QLabel_DUT_Acq_Type = QLabel()

        QLabel_CurrentTrigger_V_Settling_Band = QLabel()
        QLabel_CurrentTrigger_T_Settling_Band = QLabel()
        QLabel_CurrentTrigger_Probe_Setting = QLabel()
        QLabel_CurrentTrigger_Acq_Type = QLabel()

        QLabel_OSC_DUT_Display_Channel.setText("DUT Display Channel (OSC)")
        QLabel_OSC_CurrentTrigger_Display_Channel.setText("Current Trigger Display Channel (OSC)")
        QLabel_Trigger_Source_Display_Channel.setText("Trigger Source Channel (OSC)")
        
        QLabel_set_PSU_Channel.setText("Set PSU Channel:")
        QLabel_set_ELoad_Channel.setText("Set Eload Channel:")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        QLabel_Power_Rating.setText("Power Rating (W):")
        QLabel_maxVoltage.setText("Testing Voltage (V):")
        QLabel_voltage_rated.setText("DUT Rated Voltage:")
        QLabel_current_rated.setText("DUT Rated Current:")
        QLabel_maxCurrent.setText("Testing Current (A):")
        
        QLabel_DUT_V_Settling_Band.setText("DUT Settling Band Voltage (V) / Error Band:")
        QLabel_DUT_T_Settling_Band.setText("DUT Settling Band Time (s):")
        QLabel_DUT_Probe_Setting.setText("DUT Probe Setting Ratio:")
        QLabel_DUT_Acq_Type.setText("DUT Acquire Mode:")

        QLabel_CurrentTrigger_V_Settling_Band.setText("CurrentTrigger Settling Band Voltage (V) / Error Band:")
        QLabel_CurrentTrigger_T_Settling_Band.setText("CurrentTrigger Settling Band Time (s):")
        QLabel_CurrentTrigger_Probe_Setting.setText("CurrentTrigger Probe Setting Ratio:")
        QLabel_CurrentTrigger_Acq_Type.setText("CurrentTrigger Acquire Mode:")

        self.QLineEdit_OSC_DUT_Display_Channel = QComboBox()
        self.QLineEdit_OSC_CurrentTrigger_Display_Channel = QComboBox()
        self.QComboBox_Trigger_Source_Display_Channel = QComboBox()

        self.QLineEdit_OSC_DUT_Display_Channel.addItems(["CHANNEL1", "CHANNEL2", "CHANNEL3", "CHANNEL4"])
        self.QLineEdit_OSC_CurrentTrigger_Display_Channel.addItems(["CHANNEL1", "CHANNEL2", "CHANNEL3", "CHANNEL4"])
        self.QComboBox_Trigger_Source_Display_Channel.addItems(["CHANNEL1", "CHANNEL2", "CHANNEL3", "CHANNEL4"])

        # External Auxiliary Equipment section
        QLabel_External_Auxiliary_Equipment = QLabel()
        QLabel_External_Auxiliary_Equipment.setText("Relay")
        self.QComboBox_External_Auxiliary_Equipment = QComboBox()
        self.QComboBox_External_Auxiliary_Equipment.addItems(["None", "RELAY"])

        self.QComboBox_set_PSU_Channel = QComboBox()
        self.QComboBox_set_ELoad_Channel = QComboBox()
        self.QComboBox_Voltage_Sense = QComboBox()
        self.QComboBox_set_Function = QComboBox()
        self.QLineEdit_Power_Rating = QLineEdit()
        self.QLineEdit_maxVoltage = QLineEdit()
        self.QLineEdit_voltage_rated = QLineEdit()
        self.QLineEdit_current_rated = QLineEdit()
        self.QLineEdit_maxCurrent = QLineEdit()

        self.QLineEdit_DUT_V_Settling_Band = QLineEdit()
        self.QLineEdit_DUT_T_Settling_Band = QLineEdit()
        self.QComboBox_DUT_Probe_Setting = QComboBox()
        self.QComboBox_DUT_Acq_Type = QComboBox()

        self.QLineEdit_CurrentTrigger_V_Settling_Band = QLineEdit()
        self.QLineEdit_CurrentTrigger_T_Settling_Band = QLineEdit()
        self.QComboBox_CurrentTrigger_Probe_Setting = QComboBox()
        self.QComboBox_CurrentTrigger_Acq_Type = QComboBox()

        self.QComboBox_set_Function.addItems(
            [
                "Current Priority",
                "Voltage Priority",
                "Resistance Priority",
            ]
        )
        self.QComboBox_set_Function.setEnabled(False)
        self.QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])

        self.QComboBox_set_PSU_Channel.addItems(["1", "2", "3", "4"])
        self.QComboBox_set_PSU_Channel.setEnabled(True)
        self.QComboBox_set_ELoad_Channel.addItems(["1", "2"])
        self.QComboBox_set_ELoad_Channel.setEnabled(True)

        self.QComboBox_DUT_Probe_Setting.addItems(["X1", "X10", "X20", "X100"])
        self.QComboBox_DUT_Acq_Type.addItems(["NORMal", "PEAK", "AVERage", "HRESolution"])

        self.QComboBox_CurrentTrigger_Probe_Setting.addItems(["X1", "X10", "X20", "X100"])
        self.QComboBox_CurrentTrigger_Acq_Type.addItems(["NORMal", "PEAK", "AVERage", "HRESolution"])

        # DUT Oscilloscope Settings
        QLabel_DUT_Channel_Unit = QLabel()
        QLabel_DUT_Channel_Offset = QLabel()
        QLabel_DUT_Channel_CouplingMode = QLabel()
        QLabel_DUT_Trigger_Mode = QLabel()
        QLabel_DUT_Trigger_CouplingMode = QLabel()
        QLabel_DUT_Trigger_SweepMode = QLabel()
        QLabel_DUT_Trigger_SlopeMode = QLabel()
        QLabel_DUT_TimeScale = QLabel()
        QLabel_DUT_VerticalScale = QLabel()

        QLabel_DUT_Channel_Unit.setText("Unit (DUT Channel)")
        QLabel_DUT_Channel_Offset.setText("Offset (DUT Channel)")
        QLabel_DUT_Channel_CouplingMode.setText("Coupling Mode (Channel)")
        QLabel_DUT_Trigger_Mode.setText("Trigger Mode:")
        QLabel_DUT_Trigger_CouplingMode.setText("Coupling Mode (Trigger):")
        QLabel_DUT_Trigger_SweepMode.setText("Trigger Sweep Mode:")
        QLabel_DUT_Trigger_SlopeMode.setText("Trigger Slope Mode:")
        QLabel_DUT_TimeScale.setText("Time Scale:")
        QLabel_DUT_VerticalScale.setText("Vertical Scale:(DUT(V))")
        
        self.QComboBox_DUT_Channel_Unit = QComboBox()
        self.QLineEdit_DUT_Channel_Offset = QLineEdit()
        self.QComboBox_DUT_Channel_CouplingMode = QComboBox()
        self.QComboBox_DUT_Trigger_Mode = QComboBox()
        self.QComboBox_DUT_Trigger_CouplingMode = QComboBox()
        self.QComboBox_DUT_Trigger_SweepMode = QComboBox()
        self.QComboBox_DUT_Trigger_SlopeMode = QComboBox()
        self.QLineEdit_DUT_TimeScale = QLineEdit()
        self.QLineEdit_DUT_VerticalScale = QLineEdit()

        self.QComboBox_DUT_Channel_Unit.addItems(["VOLT", "AMPere"])
        self.QComboBox_DUT_Channel_CouplingMode.addItems(["AC", "DC"])
        self.QComboBox_DUT_Trigger_Mode.addItems(["EDGE", "IIC", "EBUR"])
        self.QComboBox_DUT_Trigger_CouplingMode.addItems(["AC", "DC"])
        self.QComboBox_DUT_Trigger_SweepMode.addItems(["NORMAL", "AUTO"])
        self.QComboBox_DUT_Trigger_SlopeMode.addItems(["ALT", "POS", "NEG", "EITH"])

        self.QComboBox_DUT_Channel_Unit.setEnabled(True)
        self.QComboBox_DUT_Channel_CouplingMode.setEnabled(True)
        self.QComboBox_DUT_Trigger_Mode.setEnabled(False)
        self.QComboBox_DUT_Trigger_CouplingMode.setEnabled(False)
        self.QComboBox_DUT_Trigger_SweepMode.setEnabled(False)
        self.QComboBox_DUT_Trigger_SlopeMode.setEnabled(False)
        self.QComboBox_DUT_Probe_Setting.setEnabled(True)
        self.QComboBox_DUT_Acq_Type.setEnabled(False)

         # Current Trigger Oscilloscope Settings
        QLabel_CurrentTrigger_Channel_Unit = QLabel()
        QLabel_CurrentTrigger_Channel_Offset = QLabel()
        QLabel_CurrentTrigger_Channel_CouplingMode = QLabel()
        QLabel_CurrentTrigger_Trigger_Mode = QLabel()
        QLabel_CurrentTrigger_Trigger_CouplingMode = QLabel()
        QLabel_CurrentTrigger_Trigger_SweepMode = QLabel()
        QLabel_CurrentTrigger_Trigger_SlopeMode = QLabel()
        QLabel_CurrentTrigger_TimeScale = QLabel()
        QLabel_CurrentTrigger_VerticalScale = QLabel()

        QLabel_CurrentTrigger_Channel_Unit.setText("Unit (Current Trigger Channel)")
        QLabel_CurrentTrigger_Channel_Offset.setText("Offset (Current Trigger Channel)")
        QLabel_CurrentTrigger_Channel_CouplingMode.setText("Coupling Mode (Channel)")
        QLabel_CurrentTrigger_Trigger_Mode.setText("Trigger Mode:")
        QLabel_CurrentTrigger_Trigger_CouplingMode.setText("Coupling Mode (Trigger):")
        QLabel_CurrentTrigger_Trigger_SweepMode.setText("Trigger Sweep Mode:")
        QLabel_CurrentTrigger_Trigger_SlopeMode.setText("Trigger Slope Mode:")
        QLabel_CurrentTrigger_TimeScale.setText("Time Scale:")
        QLabel_CurrentTrigger_VerticalScale.setText("Vertical Scale:(Current(A))")

        self.QComboBox_CurrentTrigger_Channel_Unit = QComboBox()
        self.QLineEdit_CurrentTrigger_Channel_Offset = QLineEdit()
        self.QComboBox_CurrentTrigger_Channel_CouplingMode = QComboBox()
        self.QComboBox_CurrentTrigger_Trigger_Mode = QComboBox()
        self.QComboBox_CurrentTrigger_Trigger_CouplingMode = QComboBox()
        self.QComboBox_CurrentTrigger_Trigger_SweepMode = QComboBox()
        self.QComboBox_CurrentTrigger_Trigger_SlopeMode = QComboBox()
        self.QLineEdit_CurrentTrigger_TimeScale = QLineEdit()
        self.QLineEdit_CurrentTrigger_VerticalScale = QLineEdit()

        self.QComboBox_CurrentTrigger_Channel_Unit.addItems([ "AMPere","VOLT"])
        self.QComboBox_CurrentTrigger_Channel_CouplingMode.addItems(["DC","AC"])
        self.QComboBox_CurrentTrigger_Trigger_Mode.addItems(["EDGE", "IIC", "EBUR"])
        self.QComboBox_CurrentTrigger_Trigger_CouplingMode.addItems(["AC", "DC"])
        self.QComboBox_CurrentTrigger_Trigger_SweepMode.addItems(["NORMAL", "AUTO"])
        self.QComboBox_CurrentTrigger_Trigger_SlopeMode.addItems(["ALT", "POS", "NEG", "EITH"])

        self.QComboBox_CurrentTrigger_Channel_CouplingMode.setEnabled(False)
        self.QComboBox_CurrentTrigger_Trigger_Mode.setEnabled(True)
        self.QComboBox_CurrentTrigger_Trigger_CouplingMode.setEnabled(True)
        self.QComboBox_CurrentTrigger_Trigger_SweepMode.setEnabled(True)
        self.QComboBox_CurrentTrigger_Trigger_SlopeMode.setEnabled(True)
        self.QComboBox_CurrentTrigger_Probe_Setting.setEnabled(True)
        self.QComboBox_CurrentTrigger_Acq_Type.setEnabled(True)


        # Create a horizontal layout for the "Save Path" and checkboxes
        Rated_Power_Voltage_Current_Layout = QHBoxLayout()
        Rated_Power_Voltage_Current_Layout.addWidget(QLabel_Power_Rating)  # QLabel for "Save Path"
        Rated_Power_Voltage_Current_Layout.addWidget(self.QLineEdit_Power_Rating)  # Checkbox for "Generate Excel Report"
        Rated_Power_Voltage_Current_Layout.addWidget(QLabel_voltage_rated)  # Checkbox for "Show Graph"
        Rated_Power_Voltage_Current_Layout.addWidget(self.QLineEdit_voltage_rated)  # Checkbox for "Show Graph"
        Rated_Power_Voltage_Current_Layout.addWidget(QLabel_current_rated)  # QLabel for "Save Path"
        Rated_Power_Voltage_Current_Layout.addWidget(self.QLineEdit_current_rated)  # Checkbox for "Generate Excel Report"

        Test_Voltage_Current_Layout = QHBoxLayout()
        Test_Voltage_Current_Layout.addWidget(QLabel_maxVoltage)  # QLabel for "Save Path"
        Test_Voltage_Current_Layout.addWidget(self.QLineEdit_maxVoltage)  # Checkbox for "Generate Excel Report"
        Test_Voltage_Current_Layout.addWidget(QLabel_maxCurrent)  # Checkbox for "Show Graph"
        Test_Voltage_Current_Layout.addWidget(self.QLineEdit_maxCurrent)  # Checkbox for "Show Graph"

        DUT_Error_Band_layout = QHBoxLayout()
        DUT_Error_Band_layout.addWidget(QLabel_DUT_V_Settling_Band)  # QLabel for "Save Path"
        DUT_Error_Band_layout.addWidget(self.QLineEdit_DUT_V_Settling_Band)  # Checkbox for "Generate Excel Report"
        DUT_Error_Band_layout.addWidget(QLabel_DUT_T_Settling_Band)  # Checkbox for "Show Graph"
        DUT_Error_Band_layout.addWidget(self.QLineEdit_DUT_T_Settling_Band)  # Checkbox for "Show Graph"


        performtest_layout = QHBoxLayout()
        performtest_layout.addWidget(Desp5)  # QLabel for "Save Path"
        performtest_layout.addWidget(QCheckBox_SpecialCase_Widget)  # Checkbox for "Generate Excel Report"
        performtest_layout.addWidget(QCheckBox_NormalCase_Widget)  # Checkbox for "Show Graph"
        performtest_layout.addWidget(QCheckBox_CurrentCase_Widget)  # Checkbox for "Show Graph"

        Channel_CouplingMode_layout = QHBoxLayout()
        Channel_CouplingMode_layout.addWidget(QLabel_DUT_Channel_CouplingMode)  # QLabel for "Save Path"
        Channel_CouplingMode_layout.addWidget(self.QComboBox_DUT_Channel_CouplingMode)  # Checkbox for "Generate Excel Report"
        Channel_CouplingMode_layout.addWidget(QLabel_CurrentTrigger_Channel_CouplingMode)  # Checkbox for "Show Graph"
        Channel_CouplingMode_layout.addWidget(self.QComboBox_CurrentTrigger_Channel_CouplingMode)  # Checkbox for "Show Graph"

        Trigger_Mode_layout = QHBoxLayout()
        Trigger_Mode_layout.addWidget(QLabel_DUT_Trigger_Mode)  # Checkbox for "Show Graph"
        Trigger_Mode_layout.addWidget(self.QComboBox_DUT_Trigger_Mode)  # Checkbox for "Show Graph"
        Trigger_Mode_layout.addWidget(QLabel_CurrentTrigger_Trigger_Mode)  # QLabel for "Save Path"
        Trigger_Mode_layout.addWidget(self.QComboBox_CurrentTrigger_Trigger_Mode)  # Checkbox for "Generate Excel Report"

        Unit_Channel_layout = QHBoxLayout()
        Unit_Channel_layout.addWidget(QLabel_DUT_Channel_Unit)  # QLabel for "Save Path"
        Unit_Channel_layout.addWidget(self.QComboBox_DUT_Channel_Unit)  # Checkbox for "Generate Excel Report"
        Unit_Channel_layout.addWidget(QLabel_CurrentTrigger_Channel_Unit)  # Checkbox for "Show Graph"
        Unit_Channel_layout.addWidget(self.QComboBox_CurrentTrigger_Channel_Unit)  # Checkbox for "Show Graph"

        Offset_Channel_layout = QHBoxLayout()
        Offset_Channel_layout.addWidget(QLabel_DUT_Channel_Offset)  # Checkbox for "Show Graph"
        Offset_Channel_layout.addWidget(self.QLineEdit_DUT_Channel_Offset)  # Checkbox for "Show Graph"
        Offset_Channel_layout.addWidget(QLabel_CurrentTrigger_Channel_Offset)  # QLabel for "Save Path"
        Offset_Channel_layout.addWidget(self.QLineEdit_CurrentTrigger_Channel_Offset)  # Checkbox for "Generate Excel Report"

        Trigger_CouplingMode_layout = QHBoxLayout()
        Trigger_CouplingMode_layout.addWidget(QLabel_DUT_Trigger_CouplingMode)  # QLabel for "Save Path"
        Trigger_CouplingMode_layout.addWidget(self.QComboBox_DUT_Trigger_CouplingMode)  # Checkbox for "Generate Excel Report"
        Trigger_CouplingMode_layout.addWidget(QLabel_CurrentTrigger_Trigger_CouplingMode)  # Checkbox for "Show Graph"
        Trigger_CouplingMode_layout.addWidget(self.QComboBox_CurrentTrigger_Trigger_CouplingMode)  # Checkbox for "Show Graph"

        Trigger_SweepMode_layout = QHBoxLayout()
        Trigger_SweepMode_layout.addWidget(QLabel_DUT_Trigger_SweepMode)  # Checkbox for "Show Graph"  
        Trigger_SweepMode_layout.addWidget(self.QComboBox_DUT_Trigger_SweepMode)  # Checkbox for "Show Graph"
        Trigger_SweepMode_layout.addWidget(QLabel_CurrentTrigger_Trigger_SweepMode)  # QLabel for "Save Path"
        Trigger_SweepMode_layout.addWidget(self.QComboBox_CurrentTrigger_Trigger_SweepMode)  # Checkbox for "Generate Excel Report"

        Trigger_SlopeMode_layout = QHBoxLayout()
        Trigger_SlopeMode_layout.addWidget(QLabel_DUT_Trigger_SlopeMode)  # QLabel for "Save Path"
        Trigger_SlopeMode_layout.addWidget(self.QComboBox_DUT_Trigger_SlopeMode)  # Checkbox for "Generate Excel Report"
        Trigger_SlopeMode_layout.addWidget(QLabel_CurrentTrigger_Trigger_SlopeMode)  # Checkbox for "Show Graph"
        Trigger_SlopeMode_layout.addWidget(self.QComboBox_CurrentTrigger_Trigger_SlopeMode)  # Checkbox for "Show Graph"

        Probe_Setting_layout = QHBoxLayout()
        Probe_Setting_layout.addWidget(QLabel_DUT_Probe_Setting)  # QLabel for "Save Path"
        Probe_Setting_layout.addWidget(self.QComboBox_DUT_Probe_Setting)  # Checkbox for "Generate Excel Report"
        Probe_Setting_layout.addWidget(QLabel_CurrentTrigger_Probe_Setting)  # Checkbox for "Show Graph"
        Probe_Setting_layout.addWidget(self.QComboBox_CurrentTrigger_Probe_Setting)  # Checkbox for "Show Graph"

        TimeScale_layout = QHBoxLayout()
        TimeScale_layout.addWidget(QLabel_DUT_TimeScale)  # Checkbox for "Show Graph"
        TimeScale_layout.addWidget(self.QLineEdit_DUT_TimeScale)  # Checkbox for "Show Graph"
        #TimeScale_layout.addWidget(QLabel_CurrentTrigger_TimeScale)  # QLabel for "Save Path"
        #TimeScale_layout.addWidget(QLineEdit_CurrentTrigger_TimeScale)  # Checkbox for "Generate Excel Report"

        VerticalScale_layout = QHBoxLayout()
        VerticalScale_layout.addWidget(QLabel_DUT_VerticalScale)  # QLabel for "Save Path"
        VerticalScale_layout.addWidget(self.QLineEdit_DUT_VerticalScale)  # Checkbox for "Generate Excel Report"
        #VerticalScale_layout.addWidget(QLabel_CurrentTrigger_VerticalScale)  # Checkbox for "Show Graph"
        #VerticalScale_layout.addWidget(QLineEdit_CurrentTrigger_VerticalScale)  # Checkbox for "Show Graph"


        layout1.addRow(Desp0)
        layout1.addRow(QPushButton_Widget00)
        layout1.addRow(self.OutputBox)
        layout1.addRow(QPushButton_Widget0)
        layout1.addRow(Desp1)
        layout1.addRow(QLabel_DUT, self.QComboBox_DUT)
        layout1.addRow(QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        layout1.addRow(QLabel_OSC_VisaAddress, self.QLineEdit_OSC_VisaAddress)
        layout1.addRow(QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        layout1.addRow(Desp2)
        layout1.addRow(QLabel_set_Function, self.QComboBox_set_Function)
        layout1.addRow(QLabel_Voltage_Sense, self.QComboBox_Voltage_Sense)
        layout1.addRow(QLabel_set_PSU_Channel, self.QComboBox_set_PSU_Channel)
        layout1.addRow(QLabel_set_ELoad_Channel, self.QComboBox_set_ELoad_Channel)
        layout1.addRow(QLabel_OSC_DUT_Display_Channel, self.QLineEdit_OSC_DUT_Display_Channel)
        layout1.addRow(QLabel_OSC_CurrentTrigger_Display_Channel, self.QLineEdit_OSC_CurrentTrigger_Display_Channel)
        layout1.addRow(QLabel_Trigger_Source_Display_Channel, self.QComboBox_Trigger_Source_Display_Channel)
        layout1.addRow(Desp8)
        layout1.addRow(QLabel_External_Auxiliary_Equipment, self.QComboBox_External_Auxiliary_Equipment)
        layout1.addRow(Desp3)
        layout1.addRow(Rated_Power_Voltage_Current_Layout)
        layout1.addRow(Test_Voltage_Current_Layout)
        layout1.addRow(DUT_Error_Band_layout)
        layout1.addRow(QLabel_CurrentTrigger_V_Settling_Band, self.QLineEdit_CurrentTrigger_V_Settling_Band)

  
        layout1.addRow(Desp4)#DUT Oscilloscope Settings

        layout1.addRow(Unit_Channel_layout)
        layout1.addRow(Offset_Channel_layout)
        layout1.addRow(Channel_CouplingMode_layout)
        layout1.addRow(Trigger_Mode_layout)
        layout1.addRow(Trigger_CouplingMode_layout)
        layout1.addRow(Trigger_SweepMode_layout)
        layout1.addRow(Trigger_SlopeMode_layout)
        layout1.addRow(Probe_Setting_layout)
        layout1.addRow(TimeScale_layout)
        layout1.addRow(VerticalScale_layout)
        layout1.addRow(QLabel_CurrentTrigger_VerticalScale, self.QLineEdit_CurrentTrigger_VerticalScale)
        
        

        layout1.addRow(performtest_layout)
        layout1.addRow(QPushButton_Widget)
        self.setLayout(layout1)

        

        QPushButton_Widget0.clicked.connect(self.doFind)
        QPushButton_Widget.clicked.connect(self.executeTest)
    
        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_OSC_VisaAddress.currentTextChanged.connect(self.OSC_VisaAddress_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)
        self.QComboBox_DUT.currentTextChanged.connect(self.on_current_index_changed)
        self.QComboBox_set_PSU_Channel.currentTextChanged.connect(self.PSU_Channel_changed)
        self.QComboBox_set_ELoad_Channel.currentTextChanged.connect(self.ELoad_Channel_changed)
        self.QComboBox_External_Auxiliary_Equipment.currentTextChanged.connect(self.External_Auxiliary_Equipment_changed)
        """QLineEdit_ELoad_Display_Channel.textEdited.connect(self.ELoad_Channel_changed)
        QLineEdit_PSU_Display_Channel.textEdited.connect(self.PSU_Channel_changed)"""

        self.QLineEdit_OSC_DUT_Display_Channel.currentTextChanged.connect(self.DUT_OSC_Channel_changed)
        self.QLineEdit_OSC_CurrentTrigger_Display_Channel.currentTextChanged.connect(self.CurrentTrigger_OSC_Channel_changed)
        self.QComboBox_Trigger_Source_Display_Channel.currentTextChanged.connect(self.TriggerSource_changed)
        
        self.QLineEdit_Power_Rating.textEdited.connect(self.Power_Rating_changed)
        self.QLineEdit_voltage_rated.textEdited.connect(self.Voltage_Rating_changed)
        self.QLineEdit_current_rated.textEdited.connect(self.Current_Rating_changed)

        self.QLineEdit_maxCurrent.textEdited.connect(self.maxCurrent_changed)
        self.QLineEdit_maxVoltage.textEdited.connect(self.maxVoltage_changed)

        self.QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)

        self.QComboBox_Voltage_Sense.currentTextChanged.connect(
            self.set_VoltageSense_changed
        )
        #DUT Oscilloscope Settings
        self.QLineEdit_DUT_V_Settling_Band.textEdited.connect(self.DUT_V_Settling_Band_changed)
        self.QLineEdit_DUT_T_Settling_Band.textEdited.connect(self.DUT_T_Settling_Band_changed)
        self.QLineEdit_CurrentTrigger_V_Settling_Band.textEdited.connect(self.CurrentTrigger_V_Settling_Band_changed)
        #self.QLineEdit_CurrentTrigger_T_Settling_Band.textEdited.connect(self.T_Settling_Band_changed)

        self.QComboBox_DUT_Channel_Unit.currentTextChanged.connect(
            self.DUT_Channel_Unit_changed
        )

        self.QLineEdit_DUT_Channel_Offset.textEdited.connect(self.DUT_Channel_Offset_changed)

        self.QComboBox_DUT_Channel_CouplingMode.currentTextChanged.connect(
            self.DUT_Channel_CouplingMode_changed
        )
        self.QComboBox_DUT_Trigger_CouplingMode.currentTextChanged.connect(
            self.DUT_Trigger_CouplingMode_changed
        )
        self.QComboBox_DUT_Trigger_Mode.currentTextChanged.connect(self.DUT_Trigger_Mode_changed)
        self.QComboBox_DUT_Trigger_SweepMode.currentTextChanged.connect(
            self.DUT_Trigger_SweepMode_changed
        )
        self.QComboBox_DUT_Trigger_SlopeMode.currentTextChanged.connect(
            self.DUT_Trigger_SlopeMode_changed
        )
        self.QComboBox_DUT_Probe_Setting.currentTextChanged.connect(
            self.DUT_Probe_Setting_changed
        )
        self.QComboBox_DUT_Acq_Type.currentTextChanged.connect(
            self.DUT_Acq_Type_changed
        )
        self.QLineEdit_DUT_TimeScale.textEdited.connect(self.DUT_TimeScale_changed)

        self.QLineEdit_DUT_VerticalScale.textEdited.connect(self.DUT_VerticalScale_changed)

        ###Current Trigger
        self.QComboBox_CurrentTrigger_Channel_Unit.currentTextChanged.connect(
            self.CurrentTrigger_Channel_Unit_changed
        )

        self.QLineEdit_CurrentTrigger_Channel_Offset.textEdited.connect(self.CurrentTrigger_Channel_Offset_changed)

        self.QComboBox_CurrentTrigger_Channel_CouplingMode.currentTextChanged.connect(
            self.CurrentTrigger_Channel_CouplingMode_changed
        )
        self.QComboBox_CurrentTrigger_Trigger_CouplingMode.currentTextChanged.connect(
            self.CurrentTrigger_Trigger_CouplingMode_changed
        )
        self.QComboBox_CurrentTrigger_Trigger_Mode.currentTextChanged.connect(self.CurrentTrigger_Trigger_Mode_changed)
        self.QComboBox_CurrentTrigger_Trigger_SweepMode.currentTextChanged.connect(
            self.CurrentTrigger_Trigger_SweepMode_changed
        )
        self.QComboBox_CurrentTrigger_Trigger_SlopeMode.currentTextChanged.connect(
            self.CurrentTrigger_Trigger_SlopeMode_changed
        )   
        self.QComboBox_CurrentTrigger_Probe_Setting.currentTextChanged.connect(
            self.CurrentTrigger_Probe_Setting_changed
        )   
        self.QComboBox_CurrentTrigger_Acq_Type.currentTextChanged.connect(
            self.CurrentTrigger_Acq_Type_changed
        ) 
        

        self.QLineEdit_CurrentTrigger_VerticalScale.textEdited.connect(self.CurrentTrigger_VerticalScale_changed)

        QCheckBox_SpecialCase_Widget.stateChanged.connect(self.checkbox_state_SpecialCase)
        QCheckBox_NormalCase_Widget.stateChanged.connect(self.checkbox_state_NormalCase)
        QCheckBox_CurrentCase_Widget.stateChanged.connect(self.checkbox_state_CurrentCase)

        QPushButton_Widget00.clicked.connect(self.savepath)

    def External_Auxiliary_Equipment_changed(self, s):
        if s == "None":
            self.relay_voltage = "None"
        else:
            self.relay_voltage = "RELAY"

    def on_current_index_changed(self):
        selected_text = self.QComboBox_DUT.currentText()
        self.update_selection(selected_text)
        self.QLineEdit_PSU_VisaAddress.setCurrentText(self.PSU)
        self.QLineEdit_OSC_VisaAddress.setCurrentText(self.OSC)
        self.QLineEdit_ELoad_VisaAddress.setCurrentText(self.ELoad)
        self.QComboBox_Voltage_Sense.setCurrentText("4 Wire" if self.VoltageSense == "EXT" else "2 Wire")
        self.QComboBox_set_PSU_Channel.setCurrentIndex(int(self.PSU_Channel))
        self.QComboBox_set_ELoad_Channel.setCurrentIndex(int(self.ELoad_Channel))
        self.QLineEdit_OSC_DUT_Display_Channel.setCurrentText(self.DUT_OSC_Channel)
        self.QLineEdit_OSC_CurrentTrigger_Display_Channel.setCurrentText(self.CurrentTrigger_OSC_Channel)
        self.QComboBox_Trigger_Source_Display_Channel.setCurrentText(self.TriggerSource)
        self.QComboBox_External_Auxiliary_Equipment.setCurrentText(self.relay_voltage)
        self.QLineEdit_Power_Rating.setText(self.Power_Rating)
        self.QLineEdit_voltage_rated.setText(self.Voltage_Rating)
        self.QLineEdit_current_rated.setText(self.Current_Rating)
        self.QLineEdit_maxVoltage.setText(self.maxVoltage)
        self.QLineEdit_maxCurrent.setText(self.maxCurrent)
        self.QLineEdit_DUT_V_Settling_Band.setText(self.DUT_V_Settling_Band)
        self.QLineEdit_DUT_T_Settling_Band.setText(self.DUT_T_Settling_Band)
        self.QLineEdit_CurrentTrigger_V_Settling_Band.setText(self.CurrentTrigger_V_Settling_Band)
        self.QComboBox_DUT_Channel_Unit.setCurrentText(self.DUT_Channel_Unit)
        self.QLineEdit_DUT_Channel_Offset.setText(self.DUT_Channel_Offset)
        self.QComboBox_DUT_Channel_CouplingMode.setCurrentText(self.DUT_Channel_CouplingMode)
        self.QComboBox_DUT_Trigger_Mode.setCurrentText(self.DUT_Trigger_Mode)
        self.QComboBox_DUT_Trigger_CouplingMode.setCurrentText(self.DUT_Trigger_CouplingMode)
        self.QComboBox_DUT_Trigger_SweepMode.setCurrentText(self.DUT_Trigger_SweepMode)
        self.QComboBox_DUT_Trigger_SlopeMode.setCurrentText(self.DUT_Trigger_SlopeMode)
        self.QComboBox_DUT_Probe_Setting.setCurrentText(self.DUT_Probe_Setting)
        self.QComboBox_DUT_Acq_Type.setCurrentText(self.DUT_Acq_Type)
        self.QLineEdit_DUT_TimeScale.setText(self.DUT_TimeScale)
        self.QLineEdit_DUT_VerticalScale.setText(self.DUT_VerticalScale)
        self.QComboBox_CurrentTrigger_Channel_Unit.setCurrentText(self.CurrentTrigger_Channel_Unit)
        self.QLineEdit_CurrentTrigger_Channel_Offset.setText(self.CurrentTrigger_Channel_Offset)
        self.QComboBox_CurrentTrigger_Channel_CouplingMode.setCurrentText(self.CurrentTrigger_Channel_CouplingMode)
        self.QComboBox_CurrentTrigger_Trigger_Mode.setCurrentText(self.CurrentTrigger_Trigger_Mode)
        self.QComboBox_CurrentTrigger_Trigger_CouplingMode.setCurrentText(self.CurrentTrigger_Trigger_CouplingMode)
        self.QComboBox_CurrentTrigger_Trigger_SweepMode.setCurrentText(self.CurrentTrigger_Trigger_SweepMode)
        self.QComboBox_CurrentTrigger_Trigger_SlopeMode.setCurrentText(self.CurrentTrigger_Trigger_SlopeMode)
        self.QComboBox_CurrentTrigger_Probe_Setting.setCurrentText(self.CurrentTrigger_Probe_Setting)
        self.QComboBox_CurrentTrigger_Acq_Type.setCurrentText(self.CurrentTrigger_Acq_Type)
        self.QLineEdit_CurrentTrigger_VerticalScale.setText(self.CurrentTrigger_VerticalScale)


    def update_selection(self, selected_text):
        """Update selected text and reload config file"""
        self.selected_text = selected_text
        self.load_data()
    
    
    def load_data(self):
        """Reads configuration file and returns a dictionary of key-value pairs."""
        config_data = {}
        if self.selected_text =="Excavator":
            self.config_file = os.path.join(config_folder,"config_Excavator.txt")
            
        elif self.selected_text =="Dolphin":
            self.config_file = os.path.join(config_folder,"config_Dolphin.txt")
            
        elif self.selected_text =="SMU":
            self.config_file = os.path.join(config_folder,"config_SMU.txt")

        else:
            self.config_file = os.path.join(config_folder,"config_Others.txt")

        try:
            with open(self.config_file, "r") as file: 
                for line in file:

                    if not line or line.startswith("#") or line.startswith("//"):
                        continue 

                    if "=" in line:
                        key, value = line.strip().split("=")
                        config_data[key.strip()] = value.strip()

            for key, value in config_data.items():
                if key == "savelocation":
                    # If savelocation has a valid value, do not overwrite it
                    if self.savelocation and self.savelocation != "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
                        continue 
                    else:
                        setattr(self, key, value)
                else:
                    setattr(self, key, value)

        except FileNotFoundError:
            print("Config file not found. Using default values.")

        return config_data


    def DUT_changed(self, s):
        self.DUT = s
    
    def CurrentTrigger_VerticalScale_changed(self, s):
        self.CurrentTrigger_VerticalScale = s

    def checkbox_state_CurrentCase(self, s):
        self.checkbox_CurrentCase = s
    
    def DUT_Channel_Offset_changed(self, s):
        self.DUT_Channel_Offset = s
    
    def CurrentTrigger_Channel_Offset_changed(self, s):
        self.CurrentTrigger_Channel_Offset = s

    def DUT_Channel_Unit_changed(self, s):
        self.DUT_Channel_Unit = s
    
    def CurrentTrigger_Channel_Unit_changed(self, s):
        self.CurrentTrigger_Channel_Unit = s

    def TriggerSource_changed(self, s):
        self.TriggerSource = s

    def Voltage_Rating_changed(self, value):
        self.Voltage_Rating = value
    
    def Current_Rating_changed(self, value):
        self.Current_Rating = value

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_OSC_VisaAddress.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()

            self.visaIdList, self.nameList, instrument_roles = NewGetVisaSCPIResources()

            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_OSC_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])

            if 'PSU' in instrument_roles:
                psu_index = self.visaIdList.index(instrument_roles['PSU'])
                self.QLineEdit_PSU_VisaAddress.setCurrentIndex(psu_index)

            if 'ELOAD' in instrument_roles:
                eload_index = self.visaIdList.index(instrument_roles['ELOAD'])
                self.QLineEdit_ELoad_VisaAddress.setCurrentIndex(eload_index)

            if 'SCOPE' in instrument_roles:
                osc_index = self.visaIdList.index(instrument_roles['SCOPE'])
                self.QLineEdit_OSC_VisaAddress.setCurrentIndex(osc_index)
            
           
        except:
            self.OutputBox.append("No Devices Found!!!")
        return   
    
    def checkbox_state_SpecialCase(self, s):
        self.checkbox_SpecialCase = s

    def checkbox_state_NormalCase(self, s):
        self.checkbox_NormalCase = s
    
    def PSU_VisaAddress_changed(self, s):
        self.PSU = s

    def OSC_VisaAddress_changed(self, s):
        self.OSC = s

    def ELoad_VisaAddress_changed(self, s):
        self.ELoad = s
    
    def ELoad_Channel_changed(self, s):
        self.ELoad_Channel = s

    def PSU_Channel_changed(self, s):
        self.PSU_Channel = s

    def DUT_OSC_Channel_changed(self, s):
        self.DUT_OSC_Channel = s
    
    def CurrentTrigger_OSC_Channel_changed(self, s):
        self.CurrentTrigger_OSC_Channel = s

    def Power_Rating_changed(self, s):
        self.Power_Rating = s

    def maxCurrent_changed(self, s):
        self.maxCurrent = s

    def maxVoltage_changed(self, s):
        self.maxVoltage = s

    def I_Step_changed(self, s):
        self.I_Step = s

    def CurrentTrigger_T_Settling_Band_changed(self, s):
        self.CurrentTrigger_T_Settling_Band = s
    
    def CurrentTrigger_V_Settling_Band_changed(self, s):
        self.CurrentTrigger_V_Settling_Band = s
    
    def CurrentTrigger_Channel_CouplingMode_changed(self, s):
        self.CurrentTrigger_Channel_CouplingMode = s
    
    def CurrentTrigger_Trigger_CouplingMode_changed(self, s):
        self.CurrentTrigger_Trigger_CouplingMode = s
    
    def CurrentTrigger_Trigger_Mode_changed(self, s):
        self.CurrentTrigger_Trigger_Mode = s

    def CurrentTrigger_Trigger_SweepMode_changed(self, s):
        self.CurrentTrigger_Trigger_SweepMode = s
    
    def CurrentTrigger_Trigger_SlopeMode_changed(self, s):
        self.CurrentTrigger_Trigger_SlopeMode = s
    
    def CurrentTrigger_Probe_Setting_changed(self, s):
        self.CurrentTrigger_Probe_Setting = s
    
    def CurrentTrigger_Acq_Type_changed(self, s):
        self.CurrentTrigger_Acq_Type = s

#########################################################

    def DUT_T_Settling_Band_changed(self, s):
        self.DUT_T_Settling_Band = s

    def DUT_V_Settling_Band_changed(self, s):
        self.DUT_V_Settling_Band = s

    def DUT_Channel_CouplingMode_changed(self, s):
        self.DUT_Channel_CouplingMode = s

    def DUT_Trigger_CouplingMode_changed(self, s):
        self.DUT_Trigger_CouplingMode = s

    def DUT_Trigger_Mode_changed(self, s):
        self.DUT_Trigger_Mode = s

    def DUT_Trigger_SweepMode_changed(self, s):
        self.DUT_Trigger_SweepMode = s

    def DUT_Trigger_SlopeMode_changed(self, s):
        self.DUT_Trigger_SlopeMode = s
    
    def DUT_Probe_Setting_changed(self, s):
        self.DUT_Probe_Setting = s
    
    def DUT_Acq_Type_changed(self, s):
        self.DUT_Acq_Type = s

    def DUT_TimeScale_changed(self, s):
        self.DUT_TimeScale = s

    def DUT_VerticalScale_changed(self, s):
        self.DUT_VerticalScale = s



    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.setFunction = "Voltage"

        elif s == "Current Priority":
            self.setFunction = "Current"

        elif s == "Resistance Priority":
            self.setFunction = "Resistance"

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.VoltageSense = "INT"
        elif s == "4 Wire":
            self.VoltageSense = "EXT"

    def savepath(self):  
        # Create a Tkinter root window
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open a directory dialog and return the selected directory path
        directory = filedialog.askdirectory()
        self.savelocation = directory
        self.OutputBox.append(str(self.savelocation))


    def executeTest(self):
        """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
        then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
        will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
        begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
        begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
        are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
        optionally export all the details into a CSV file or display a graph after the test is completed.

        """
        dict = dictGenerator.input(
            savedir=self.savelocation,
            Instrument="Keysight",
            PSU=self.PSU,
            OSC=self.OSC,
            ELoad=self.ELoad,
            V_Rating=self.Voltage_Rating,
            I_Rating=self.Current_Rating,
            P_Rating=self.Power_Rating,
            power=self.Power_Rating,
            maxCurrent=self.maxCurrent,
            maxVoltage=self.maxVoltage,
            ELoad_Channel=self.ELoad_Channel,
            PSU_Channel=self.PSU_Channel,

            DUT_OSC_Channel=self.DUT_OSC_Channel,
            CurrentTrigger_OSC_Channel=self.CurrentTrigger_OSC_Channel,

            TriggerSource=self.TriggerSource,

            VoltageSense=self.VoltageSense,
            setFunction=self.setFunction,
            
            CurrentTrigger_Channel_Unit=self.CurrentTrigger_Channel_Unit,
            CurrentTrigger_Channel_Offset=self.CurrentTrigger_Channel_Offset,
            CurrentTrigger_Channel_CouplingMode=self.CurrentTrigger_Channel_CouplingMode,
            CurrentTrigger_Trigger_Mode=self.CurrentTrigger_Trigger_Mode,
            CurrentTrigger_Trigger_CouplingMode=self.CurrentTrigger_Trigger_CouplingMode,
            CurrentTrigger_Trigger_SweepMode=self.CurrentTrigger_Trigger_SweepMode,
            CurrentTrigger_Trigger_SlopeMode=self.CurrentTrigger_Trigger_SlopeMode,
            CurrentTrigger_Probe_Setting=self.CurrentTrigger_Probe_Setting,
            CurrentTrigger_Acq_Type=self.CurrentTrigger_Acq_Type,
            CurrentTrigger_VerticalScale=self.CurrentTrigger_VerticalScale,
           
            DUT_Channel_Unit=self.DUT_Channel_Unit,
            DUT_Channel_Offset=self.DUT_Channel_Offset,
            DUT_Channel_CouplingMode=self.DUT_Channel_CouplingMode,
            DUT_Trigger_Mode=self.DUT_Trigger_Mode,
            DUT_Trigger_CouplingMode=self.DUT_Trigger_CouplingMode,
            DUT_Trigger_SweepMode=self.DUT_Trigger_SweepMode,
            DUT_Trigger_SlopeMode=self.DUT_Trigger_SlopeMode,
            DUT_Probe_Setting=self.DUT_Probe_Setting,
            DUT_Acq_Type=self.DUT_Acq_Type,
            DUT_TimeScale=self.DUT_TimeScale,
            DUT_VerticalScale=self.DUT_VerticalScale,
            
            DUT_V_Settling_Band=self.DUT_V_Settling_Band,
            DUT_T_Settling_Band=self.DUT_T_Settling_Band,
            CurrentTrigger_V_Settling_Band=self.CurrentTrigger_V_Settling_Band,
        )
        QMessageBox.warning(
            self,
            "In Progress",
            "Measurement will start now , please do not close the main window until test is completed",
        )

        #Execute Voltage Measurement
        relay_voltage = RelayController_Voltage()
        if self.relay_voltage == "RELAY":
            relay_voltage.relay_on()
        else:
            relay_voltage.relay_off()
        try:
            """if self.checkbox_SpecialCase == 2:
                RiseFallTime.executeA(self, dict)
            
            if self.checkbox_NormalCase == 2:
                RiseFallTime.executeB(self, dict)"""

            if self.checkbox_CurrentCase == 2:
                DolphinRiseFallTimewithELoad.executeC(self, dict)

        except Exception as e:
            print(e)
            QMessageBox.warning(self, "Error", str(e))
            exit()

        self.OutputBox.append(my_result.getvalue())
        self.OutputBox.append("Measurement is complete !")

class ProgrammingSpeed(QDialog):
    """Class for configuring the Programming Speed DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py

    """

    def __init__(self):
        """ "Method declaring the Widgets, Signals & Slots for Programming Speed."""
        super().__init__()

        self.setWindowTitle("Programming Speed")

        QPushButton_Widget = QPushButton()
        QPushButton_Widget.setText("Execute Test")
        layout1 = QFormLayout()
        self.OutputBox = QTextBrowser()
        self.OutputBox.append(my_result.getvalue())

        Desp1 = QLabel()
        Desp2 = QLabel()
        Desp3 = QLabel()
        Desp4 = QLabel()

        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)

        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Test Settings:")
        Desp4.setText("Oscilloscope Settings:")

        QLabel_PSU_VisaAddress = QLabel()
        QLabel_OSC_VisaAddress = QLabel()
        QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        QLabel_OSC_VisaAddress.setText("Visa Address (OSC):")
        QLineEdit_PSU_VisaAddress = QLineEdit()
        QLineEdit_OSC_VisaAddress = QLineEdit()

        QLabel_PSU_Display_Channel = QLabel()
        QLabel_OSC_Display_Channel = QLabel()
        QLabel_Voltage_Sense = QLabel()

        QComboBox_Voltage_Sense = QComboBox()

        QComboBox_Voltage_Sense.addItems(["4 Wire", "2 Wire"])

        QLabel_PSU_Display_Channel.setText("Display Channel (PSU):")
        QLabel_OSC_Display_Channel.setText("Display Channel (OSC)")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        QLineEdit_PSU_Display_Channel = QLineEdit()
        QLineEdit_OSC_Display_Channel = QLineEdit()

        # Specifications
        QLabel_V_Upper = QLabel()
        QLabel_V_Lower = QLabel()
        QLabel_Upper_Bound = QLabel()
        QLabel_Lower_Bound = QLabel()

        QLabel_V_Upper.setText("Max Voltage (V):")
        QLabel_V_Lower.setText("Min Voltage (V):")
        QLabel_Upper_Bound.setText("Percentage of upper bound (%)")
        QLabel_Lower_Bound.setText("Percentage of lower bound (%)")

        QLineEdit_V_Upper = QLineEdit()
        QLineEdit_V_Lower = QLineEdit()
        QLineEdit_Upper_Bound = QLineEdit()
        QLineEdit_Lower_Bound = QLineEdit()

        # Oscilloscope Settings
        QLabel_Trigger_Mode = QLabel()
        QLabel_Trigger_CouplingMode = QLabel()
        QLabel_Trigger_SweepMode = QLabel()
        QLabel_Trigger_SlopeMode = QLabel()

        QLabel_Trigger_Mode.setText("Trigger Mode:")
        QLabel_Trigger_CouplingMode.setText("Coupling Mode (Trigger):")
        QLabel_Trigger_SweepMode.setText("Trigger Sweep Mode:")
        QLabel_Trigger_SlopeMode.setText("Trigger Slope Mode:")

        QComboBox_Trigger_Mode = QComboBox()
        QComboBox_Trigger_CouplingMode = QComboBox()
        QComboBox_Trigger_SweepMode = QComboBox()
        QComboBox_Trigger_SlopeMode = QComboBox()

        QComboBox_Trigger_Mode.addItems(["EDGE", "IIC", "EBUR"])
        QComboBox_Trigger_CouplingMode.addItems(["DC", "AC"])
        QComboBox_Trigger_SweepMode.addItems(["NORMAL", "AUTO"])
        QComboBox_Trigger_SlopeMode.addItems(["ALT", "POS", "NEG", "EITH"])

        QComboBox_Trigger_Mode.setEnabled(False)
        QComboBox_Trigger_CouplingMode.setEnabled(False)
        QComboBox_Trigger_SweepMode.setEnabled(False)
        QComboBox_Trigger_SlopeMode.setEnabled(False)

        layout1.addRow(Desp1)
        layout1.addRow(QLabel_PSU_VisaAddress, QLineEdit_PSU_VisaAddress)
        layout1.addRow(QLabel_OSC_VisaAddress, QLineEdit_OSC_VisaAddress)

        layout1.addRow(Desp2)
        layout1.addRow(QLabel_PSU_Display_Channel, QLineEdit_PSU_Display_Channel)
        layout1.addRow(QLabel_OSC_Display_Channel, QLineEdit_OSC_Display_Channel)
        layout1.addRow(QLabel_Voltage_Sense, QComboBox_Voltage_Sense)

        layout1.addRow(Desp3)
        layout1.addRow(QLabel_V_Lower, QLineEdit_V_Lower)
        layout1.addRow(QLabel_V_Upper, QLineEdit_V_Upper)
        layout1.addRow(QLabel_Lower_Bound, QLineEdit_Lower_Bound)
        layout1.addRow(QLabel_Upper_Bound, QLineEdit_Upper_Bound)

        layout1.addRow(Desp4)
        layout1.addRow(QLabel_Trigger_CouplingMode, QComboBox_Trigger_CouplingMode)
        layout1.addRow(QLabel_Trigger_Mode, QComboBox_Trigger_Mode)
        layout1.addRow(QLabel_Trigger_SweepMode, QComboBox_Trigger_SweepMode)
        layout1.addRow(QLabel_Trigger_SlopeMode, QComboBox_Trigger_SlopeMode)

        layout1.addRow(self.OutputBox)
        layout1.addRow(QPushButton_Widget)
        self.setLayout(layout1)

        # Default Values
        self.PSU = ""
        self.OSC = ""
        self.PSU_Channel = ""
        self.OSC_Channel = ""
        self.V_Upper = ""
        self.V_Lower = ""
        self.Upper_Bound = ""
        self.Lower_Bound = ""
        self.Trigger_CouplingMode = "DC"
        self.Trigger_Mode = "EDGE"
        self.Trigger_SweepMode = "NORMAL"
        self.Trigger_SlopeMode = "EITH"
        self.VoltageSense = "EXT"

        QLineEdit_PSU_VisaAddress.textEdited.connect(self.PSU_VisaAddress_changed)
        QLineEdit_OSC_VisaAddress.textEdited.connect(self.OSC_VisaAddress_changed)
        QLineEdit_PSU_Display_Channel.textEdited.connect(self.PSU_Channel_changed)
        QLineEdit_OSC_Display_Channel.textEdited.connect(self.OSC_Channel_changed)
        QComboBox_Voltage_Sense.currentTextChanged.connect(
            self.set_VoltageSense_changed
        )
        QLineEdit_V_Upper.textEdited.connect(self.V_Upper_changed)
        QLineEdit_V_Lower.textEdited.connect(self.V_Lower_changed)
        QLineEdit_Upper_Bound.textEdited.connect(self.Upper_Bound_changed)
        QLineEdit_Lower_Bound.textEdited.connect(self.Lower_Bound_changed)
        QComboBox_Trigger_CouplingMode.currentTextChanged.connect(
            self.Trigger_CouplingMode_changed
        )
        QComboBox_Trigger_Mode.currentTextChanged.connect(self.Trigger_Mode_changed)
        QComboBox_Trigger_SweepMode.currentTextChanged.connect(
            self.Trigger_SweepMode_changed
        )
        QComboBox_Trigger_SlopeMode.currentTextChanged.connect(
            self.Trigger_SlopeMode_changed
        )
        QPushButton_Widget.clicked.connect(self.executeTest)

    def executeTest(self):
        """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
        then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
        will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
        begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
        begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
        are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
        optionally export all the details into a CSV file or display a graph after the test is completed.

        """
        dict = dictGenerator.input(
            Instrument="Keysight",
            PSU=self.PSU,
            OSC=self.OSC,
            PSU_Channel=self.PSU_Channel,
            OSC_Channel=self.OSC_Channel,
            VoltageSense=self.VoltageSense,
            Trigger_Mode=self.Trigger_Mode,
            Trigger_CouplingMode=self.Trigger_CouplingMode,
            Trigger_SweepMode=self.Trigger_SweepMode,
            Trigger_SlopeMode=self.Trigger_SlopeMode,
            Upper_Bound=self.Upper_Bound,
            Lower_Bound=self.Lower_Bound,
            V_Upper=self.V_Upper,
            V_Lower=self.V_Lower,
        )
        QMessageBox.warning(
            self,
            "In Progress",
            "Measurement will start now , please do not close the main window until test is completed",
        )

        for i in [dict]:
            if i == "":
                QMessageBox.warning(
                    self, "Error", "One of the parameters are not filled in"
                )
                break

        else:
            A = VisaResourceManager()
            flag, args = A.openRM(self.PSU, self.OSC)

            if flag == 0:
                string = ""
                for item in args:
                    string = string + item

                QMessageBox.warning(self, "VISA IO ERROR", string)
                exit()

            try:
               # ProgrammingSpeedTest.execute(self, dict)
                pass
            except Exception as e:
                print(e)
                QMessageBox.warning(self, "Error", str(e))
                exit()

        self.OutputBox.append(my_result.getvalue())
        self.OutputBox.append("Measurement is complete !")

    def V_Upper_changed(self, s):
        self.V_Upper = s

    def V_Lower_changed(self, s):
        self.V_Lower = s

    def Upper_Bound_changed(self, s):
        self.Upper_Bound = s

    def Lower_Bound_changed(self, s):
        self.Lower_Bound = s

    def Trigger_CouplingMode_changed(self, s):
        self.Trigger_CouplingMode = s

    def Trigger_Mode_changed(self, s):
        self.Trigger_Mode = s

    def Trigger_SweepMode_changed(self, s):
        self.Trigger_SweepMode = s

    def Trigger_SlopeMode_changed(self, s):
        self.Trigger_SlopeMode = s

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.VoltageSense = "INT"
        elif s == "4 Wire":
            self.VoltageSense = "EXT"

    def PSU_VisaAddress_changed(self, s):
        self.PSU = s

    def OSC_VisaAddress_changed(self, s):
        self.OSC = s

    def PSU_Channel_changed(self, s):
        self.PSU_Channel = s

    def OSC_Channel_changed(self, s):
        self.OSC_Channel = s

class PowerMeasurementDialog(QDialog):
    """Class for configuring the voltage measurement DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py


    """

    def __init__(self):
        """Method where Widgets, Signals and Slots are defined in the GUI for Voltage Measurement"""
        super().__init__()
        # Initialize default CSV path
        self.DATA_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powerdata.csv"  # or use a dynamic path if needed
        self.IMAGE_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/images/powerChart.png"
        self.ERROR_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powererror.csv"
        self.image_dialog = None

        
        # Default Values
        #self.PSU_VisaAddress = "USB0::0x2A8D::0xCC04::MY00000037::0::INSTR"
        #self.DMM_VisaAddress = "USB0::0x2A8D::0x1601::MY60094787::0::INSTR"
        #self.ELoad_VisaAddress = "USB0::0x2A8D::0x3902::MY60260005::0::INSTR"
        self.Power = "2200"
        self.Power_Rating = "6000"
        self.powerini = "0"
        self.powerfin = "60"
        self.power_step_size = "10"

        self.rshunt = "0.01"
        self.powerloop = "1"
        self.currloop = "1"
        self.voltloop = "1"
        self.estimatetime = "0"
        self.readbackvoltage = "0"
        self.readbackcurrent = "0"
        self.savelocation = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"
        self.noofloop = "1"
        self.updatedelay = "1"
        self.unit = "VOLTAGE"
        self.Programming_Error_Offset = "0.005"
        self.Programming_Error_Gain = "0.005"
        self.Readback_Error_Offset = "0.005"
        self.Readback_Error_Gain = "0.005"

        self.minCurrent = "1"
        self.maxCurrent = "10"
        self.current_step_size = "1"
        self.minVoltage = "1"
        self.maxVoltage = "80"
        self.voltage_step_size = "1"

        self.PSU = "USB0::0x2A8D::0xDA04::CN24350083::0::INSTR"
        self.DMM = "USB0::0x2A8D::0x0201::MY57702128::0::INSTR"
        self.DMM2 = "USB0::0x2A8D::0x0201::MY54701197::0::INSTR"
        self.ELoad = "USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"

        self.ELoad_Channel = "0"
        self.PSU_Channel = "1"
        self.DMM_Instrument = "Keysight"

        self.setFunction = "Current" #ELoad In CC Mode
        self.VoltageRes = "SLOW"
        self.VoltageSense = "INT"
        self.checkbox_data_Report = 2
        self.checkbox_data_Image = 2
        self.Range = "Auto"
        self.Aperture = "10"
        self.AutoZero = "ON"
        self.inputZ = "ON"
        self.UpTime = "50"
        self.DownTime = "50"

        # Ensure DATA_CSV_PATH is defined before use
        if not hasattr(self, 'DATA_CSV_PATH') or not self.DATA_CSV_PATH:
            QMessageBox.warning(self, "Error", "CSV path is not set.")

        self.setWindowTitle("Power Measurement")
        self.image_window = None
        self.setWindowFlags(Qt.Window)

        # create find button 
        QPushButton_Widget0 = QPushButton()
        QPushButton_Widget0.setText("Save Path")
        QPushButton_Widget1 = QPushButton()
        QPushButton_Widget1.setText("Execute Test")
        QPushButton_Widget2 = QPushButton()
        QPushButton_Widget2.setText("Advanced Settings")
        QPushButton_Widget3 = QPushButton()
        QPushButton_Widget3.setText("Estimate Data Collection Time")
        QPushButton_Widget4 = QPushButton()
        QPushButton_Widget4.setText("Find Instruments")
        QCheckBox_Report_Widget = QCheckBox()
        QCheckBox_Report_Widget.setText("Generate Excel Report")
        QCheckBox_Report_Widget.setCheckState(Qt.Checked)
        QCheckBox_Image_Widget = QCheckBox()
        QCheckBox_Image_Widget.setText("Show Graph")
        QCheckBox_Image_Widget.setCheckState(Qt.Checked)

        layout1 = QFormLayout()
        self.OutputBox = QTextBrowser()
        self.OutputBox.setFixedSize(800, 20)  # Set width to 200 and height to 100
        self.OutputBox.append(my_result.getvalue())

        Desp0 = QLabel()
        Desp1 = QLabel()
        Desp2 = QLabel()
        Desp3 = QLabel()
        Desp4 = QLabel()
        Desp5 = QLabel()
        Desp6 = QLabel()
        Desp7 = QLabel()

        Desp0.setFont (desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp5.setFont(desp_font)
        Desp6.setFont(desp_font)
        Desp7.setFont(desp_font)


        Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Source Voltage Limit")
        Desp4.setText("Source Current Limit")
        Desp5.setText("No. of Collection:")
        Desp6.setText("Source Power Limit [W]")
        Desp7.setText("Resistive Shunt Value Setting")

        #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location/Output Wndow:")

        # Connections
        self.QLabel_PSU_VisaAddress = QLabel()
        self.QLabel_DMM_VisaAddressforVoltage = QLabel()
        self.QLabel_DMM_VisaAddressforCurrent = QLabel()
        self.QLabel_ELoad_VisaAddress = QLabel()
        QLabel_DMM_Instrument = QLabel()
        self.QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        self.QLabel_DMM_VisaAddressforVoltage.setText("Visa Address (DMM for Measure Voltage):")
        self.QLabel_DMM_VisaAddressforCurrent.setText("Visa Address (DMM for Measure Current Shunt):")
        self.QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DMM_Instrument.setText("Instrument Type (DMM):")
        #QLineEdit_PSU_VisaAddress = QLineEdit()
        #QLineEdit_DMM_VisaAddress = QLineEdit()
        #QLineEdit_ELoad_VisaAddress = QLineEdit()

        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_DMM_VisaAddressforVoltage = QComboBox()
        self.QLineEdit_DMM_VisaAddressforCurrent = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        QComboBox_DMM_Instrument = QComboBox()

        # General Settings
        QLabel_Voltage_Res = QLabel()
        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
        QLabel_Programming_Error_Gain = QLabel()
        QLabel_Programming_Error_Offset = QLabel()
        QLabel_Readback_Error_Gain = QLabel()
        QLabel_Readback_Error_Offset = QLabel()

        QLabel_Voltage_Res.setText("Voltage Resolution (DMM):")
        QLabel_set_PSU_Channel.setText("Mode(PSU):")
        QLabel_set_ELoad_Channel.setText("Mode(Eload):")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        QLabel_Programming_Error_Gain.setText("Programming Desired Specification (Gain):")
        QLabel_Programming_Error_Offset.setText("Programming Desired Specification (Offset):")
        QLabel_Readback_Error_Gain.setText("Readback Desired Specification (Gain):")
        QLabel_Readback_Error_Offset.setText("Readback Desired Specification (Offset):")

        QComboBox_Voltage_Res = QComboBox()
        #QLineEdit_ELoad_Display_Channel = QLineEdit()
        #QLineEdit_PSU_Display_Channel = QLineEdit()
        QComboBox_set_PSU_Channel = QComboBox()
        QComboBox_set_ELoad_Channel = QComboBox()
        QComboBox_set_Function = QComboBox()
        QComboBox_Voltage_Sense = QComboBox()
        QLineEdit_Programming_Error_Gain = QLineEdit()
        QLineEdit_Programming_Error_Offset = QLineEdit()
        QLineEdit_Readback_Error_Gain = QLineEdit()
        QLineEdit_Readback_Error_Offset = QLineEdit()

        self.QLineEdit_PSU_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"])
        self.QLineEdit_DMM_VisaAddressforVoltage.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_DMM_VisaAddressforCurrent.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_ELoad_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"])


        QComboBox_DMM_Instrument.addItems(["Keysight", "Keithley"])
        QComboBox_Voltage_Res.addItems(["SLOW", "MEDIUM", "FAST"])
        QComboBox_set_Function.addItems(
            [
                "Current Priority",
                "Voltage Priority",
                "Resistance Priority",
                "Power Priority,"
            ]
        )
        QComboBox_set_Function.setEnabled(True)

        QComboBox_set_PSU_Channel.addItems(["1", "2", "3", "4"])
        QComboBox_set_PSU_Channel.setEnabled(True)

        QComboBox_set_ELoad_Channel.addItems(["1", "2"])
        QComboBox_set_ELoad_Channel.setEnabled(True)
        
        QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])
        QComboBox_Voltage_Sense.setEnabled(True)

        #Power
        QLabel_Power = QLabel()
        QLabel_Power.setText("Rated Power (W):")
        QLineEdit_Power = QLineEdit()
        
        QLabel_PowerINI = QLabel()
        QLabel_PowerINI.setText("Initial Power (W):")
        QLineEdit_PowerINI = QLineEdit()

        QLabel_PowerFIN = QLabel()
        QLabel_PowerFIN.setText("Final Power (W):")
        QLineEdit_PowerFIN = QLineEdit()


        QLabel_power_step_size = QLabel()
        QLabel_power_step_size.setText("Step Size:")
        QLineEdit_power_step_size = QLineEdit()
        
        QLabel_rshunt = QLabel()
        QLabel_rshunt.setText("Shunt Resistance Value (ohm):")
        QLineEdit_rshunt = QLineEdit()



        # Current Sweep
        QLabel_minCurrent = QLabel()
        QLabel_maxCurrent = QLabel()
        QLabel_current_step_size = QLabel()
        QLabel_minCurrent.setText("Initial Current (A):")
        QLabel_maxCurrent.setText("Final Current (A):")
        QLabel_current_step_size.setText("Step Size:")

        QLineEdit_minCurrent = QLineEdit()
        QLineEdit_maxCurrent = QLineEdit()
        QLineEdit_current_stepsize = QLineEdit()

        # Voltage Sweep
        QLabel_minVoltage = QLabel()
        QLabel_maxVoltage = QLabel()
        QLabel_voltage_step_size = QLabel()
        #QLabel_minVoltage.setText("Initial Voltage (V):")
        QLabel_maxVoltage.setText("Final Voltage (V): By default VMAX")
        #QLabel_voltage_step_size.setText("Step Size:")

        QLineEdit_minVoltage = QLineEdit()
        QLineEdit_maxVoltage = QLineEdit()
        QLineEdit_voltage_stepsize = QLineEdit()

        #Loop
        QLabel_noofloop = QLabel()
        QLabel_noofloop.setText("No. of Data Collection:")
        QComboBox_noofloop = QComboBox()
        QComboBox_noofloop.addItems(["1","2","3","4","5","6","7","8","9","10"])

        QLabel_updatedelay = QLabel()
        QLabel_updatedelay.setText("Delay Time (second) :(Default=50ms)")
        QComboBox_updatedelay = QComboBox()
        QComboBox_updatedelay.addItems(["0.0","0.8","1.0","2.0","3.0", "4.0"])
        
        # Create a horizontal layout for the "Save Path" and checkboxes
        save_path_layout = QHBoxLayout()
        save_path_layout.addWidget(QLabel_Save_Path)  # QLabel for "Save Path"
        #save_path_layout.addWidget(QLineEdit_Save_Path)  # QLineEdit for the path
        save_path_layout.addWidget(QCheckBox_Report_Widget)  # Checkbox for "Generate Excel Report"
        save_path_layout.addWidget(QCheckBox_Image_Widget)  # Checkbox for "Show Graph"

        # Add the combined layout to the main layout
        layout1.addRow(save_path_layout)

        # Rest of your layout remains unchanged
        layout1.addRow(self.OutputBox)
        #layout1.addRow(Desp0)
        layout1.addRow(QPushButton_Widget0)

        layout1.addRow(Desp1)
        layout1.addRow(QPushButton_Widget4)
        layout1.addRow(self.QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        layout1.addRow(self.QLabel_DMM_VisaAddressforVoltage, self.QLineEdit_DMM_VisaAddressforVoltage)
        layout1.addRow(self.QLabel_DMM_VisaAddressforCurrent, self.QLineEdit_DMM_VisaAddressforCurrent)
        layout1.addRow(self.QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        layout1.addRow(QLabel_DMM_Instrument, QComboBox_DMM_Instrument)
        layout1.addRow(Desp2)
        layout1.addRow(QLabel_set_PSU_Channel, QComboBox_set_PSU_Channel)
        layout1.addRow(QLabel_set_ELoad_Channel, QComboBox_set_ELoad_Channel)
        layout1.addRow(QLabel_set_Function, QComboBox_set_Function)
        layout1.addRow(QLabel_Voltage_Sense, QComboBox_Voltage_Sense)
        layout1.addRow(QLabel_Programming_Error_Gain, QLineEdit_Programming_Error_Gain)
        layout1.addRow(QLabel_Programming_Error_Offset, QLineEdit_Programming_Error_Offset)
        layout1.addRow(QLabel_Readback_Error_Gain, QLineEdit_Readback_Error_Gain)
        layout1.addRow(QLabel_Readback_Error_Offset, QLineEdit_Readback_Error_Offset)

        layout1.addRow(Desp6)
        layout1.addRow(QLabel_Power, QLineEdit_Power)
        layout1.addRow(QLabel_PowerINI, QLineEdit_PowerINI)
        layout1.addRow(QLabel_PowerFIN, QLineEdit_PowerFIN)
        layout1.addRow(QLabel_power_step_size, QLineEdit_power_step_size)

        layout1.addRow(Desp7)
        layout1.addRow(QLabel_rshunt, QLineEdit_rshunt)

        layout1.addRow(Desp3)
        #layout1.addRow(QLabel_minVoltage, QLineEdit_minVoltage)
        layout1.addRow(QLabel_maxVoltage, QLineEdit_maxVoltage)
        #layout1.addRow(QLabel_voltage_step_size, QLineEdit_voltage_stepsize)
        layout1.addRow(Desp4)
        #layout1.addRow(QLabel_minCurrent, QLineEdit_minCurrent)
        layout1.addRow(QLabel_maxCurrent, QLineEdit_maxCurrent)
        #layout1.addRow(QLabel_current_step_size, QLineEdit_current_stepsize)
        layout1.addRow(Desp5)
        layout1.addRow(QLabel_noofloop, QComboBox_noofloop)
        layout1.addRow(QLabel_updatedelay, QComboBox_updatedelay)

        layout1.addRow(QPushButton_Widget3)
        layout1.addRow(QPushButton_Widget2)
        layout1.addRow(QPushButton_Widget1)        
        
        AdvancedSettingsList.append(self.Range)
        AdvancedSettingsList.append(self.Aperture)
        AdvancedSettingsList.append(self.AutoZero)
        AdvancedSettingsList.append(self.inputZ)
        AdvancedSettingsList.append(self.UpTime)
        AdvancedSettingsList.append(self.DownTime)

        #Set window and scroll area
        self.setLayout(layout1)
        scroll_area(self,layout1)
        
        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_DMM_VisaAddressforVoltage.currentTextChanged.connect(self.DMM_VisaAddressforVoltage_changed)
        self.QLineEdit_DMM_VisaAddressforCurrent.currentTextChanged.connect(self.DMM_VisaAddressforCurrent_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)

        #QLineEdit_ELoad_Display_Channel.textEdited.connect(self.ELoad_Channel_changed)
        #QLineEdit_PSU_Display_Channel.textEdited.connect(self.PSU_Channel_changed)
        QLineEdit_Programming_Error_Gain.textEdited.connect(self.Programming_Error_Gain_changed)
        QLineEdit_Programming_Error_Offset.textEdited.connect(self.Programming_Error_Offset_changed)
        QLineEdit_Readback_Error_Gain.textEdited.connect(self.Readback_Error_Gain_changed)
        QLineEdit_Readback_Error_Offset.textEdited.connect(self.Readback_Error_Offset_changed)

        QLineEdit_Power.textEdited.connect(self.Power_changed)
        QLineEdit_PowerINI.textEdited.connect(self.PowerINI_changed)
        QLineEdit_PowerFIN.textEdited.connect(self.PowerFIN_changed)
        QLineEdit_power_step_size.textEdited.connect(self.power_step_size_changed)

        QLineEdit_rshunt.textEdited.connect(self.rshunt_changed)

        QLineEdit_minVoltage.textEdited.connect(self.minVoltage_changed)
        QLineEdit_maxVoltage.textEdited.connect(self.maxVoltage_changed)
        QLineEdit_minCurrent.textEdited.connect(self.minCurrent_changed)
        QLineEdit_maxCurrent.textEdited.connect(self.maxCurrent_changed)
        QLineEdit_voltage_stepsize.textEdited.connect(self.voltage_step_size_changed)
        QLineEdit_current_stepsize.textEdited.connect(self.current_step_size_changed)
        
        QComboBox_set_PSU_Channel.currentTextChanged.connect(self.set_PSU_Channel_changed)
        QComboBox_set_ELoad_Channel.currentTextChanged.connect(self.ELoad_Channel_changed)
        QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)
        QComboBox_Voltage_Res.currentTextChanged.connect(self.set_VoltageRes_changed)
        QComboBox_Voltage_Sense.currentTextChanged.connect(self.set_VoltageSense_changed)

        QComboBox_noofloop.currentTextChanged.connect(self.noofloop_changed)
        QComboBox_updatedelay.currentTextChanged.connect(self.updatedelay_changed)

        QComboBox_DMM_Instrument.currentTextChanged.connect(self.DMM_Instrument_changed)
        QCheckBox_Report_Widget.stateChanged.connect(self.checkbox_state_Report)
        QCheckBox_Image_Widget.stateChanged.connect(self.checkbox_state_Image)

        QPushButton_Widget0.clicked.connect(self.savepath)
        QPushButton_Widget1.clicked.connect(self.executeTest)
        QPushButton_Widget2.clicked.connect(self.openDialog)
        QPushButton_Widget3.clicked.connect(self.estimateTime)
        QPushButton_Widget4.clicked.connect(self.doFind)
     

    def set_PSU_Channel_changed(self, s):
        self.PSU_Channel = s

    def ELoad_Channel_changed(self, s):
       self.ELoad_Channel = s 

    def Power_changed(self, value):
        self.Power = value
    
    def PowerINI_changed(self, value):
        self.powerini= value
    
    def PowerFIN_changed(self, value):
        self.powerfin = value

    def power_step_size_changed(self, value):
        self.power_step_size = value

    def rshunt_changed(self, value):
        self.rshunt = value

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_DMM_VisaAddressforVoltage.clear()
            self.QLineEdit_DMM_VisaAddressforCurrent.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()
            
            self.visaIdList, self.nameList = GetVisaSCPIResources()
            
            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddressforVoltage.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddressforCurrent.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])
                
        except:
            self.OutputBox.append("No Devices Found!!!")
        return   



    def updatedelay_changed(self, value):
        self.updatedelay = value
        self.OutputBox.append(str(self.updatedelay))

    def noofloop_changed(self, value):
        self.noofloop = value
        self.OutputBox.append(str(self.noofloop))

    def DMM_Instrument_changed(self, s):
        self.DMM_Instrument = s

    def PSU_VisaAddress_changed(self, s):
        self.PSU = s    

    def DMM_VisaAddressforVoltage_changed(self, s):
        self.DMM = s
    
    def DMM_VisaAddressforCurrent_changed(self, s):
        self.DMM2 = s

    def ELoad_VisaAddress_changed(self, s):
        self.ELoad = s

    def Programming_Error_Gain_changed(self, s):
        self.Programming_Error_Gain = s

    def Programming_Error_Offset_changed(self, s):
        self.Programming_Error_Offset = s

    def Readback_Error_Gain_changed(self, s):
        self.Readback_Error_Gain = s

    def Readback_Error_Offset_changed(self, s):
        self.Readback_Error_Offset = s

    def minVoltage_changed(self, s):
        self.minVoltage = s

    def maxVoltage_changed(self, s):
        self.maxVoltage = s

    def minCurrent_changed(self, s):
        self.minCurrent = s

    def maxCurrent_changed(self, s):
        self.maxCurrent = s

    def voltage_step_size_changed(self, s):
        self.voltage_step_size = s

    def current_step_size_changed(self, s):
        self.current_step_size = s

    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.setFunction = "Voltage"

        elif s == "Current Priority":
            self.setFunction = "Current"

        elif s == "Resistance Priority":
            self.setFunction = "Resistance"
        
        elif s == "Resistance Priority":
            self.setFunction = "Resistance"

    def set_VoltageRes_changed(self, s):
        self.VoltageRes = s

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.VoltageSense = "INT"
        elif s == "4 Wire":
            self.VoltageSense = "EXT"

    def setRange(self, value):
        AdvancedSettingsList[0] = value

    def setAperture(self, value):
        AdvancedSettingsList[1] = value

    def setAutoZero(self, value):
        AdvancedSettingsList[2] = value

    def setInputZ(self, value):
        AdvancedSettingsList[3] = value

    def checkbox_state_Report(self, s):
        self.checkbox_data_Report = s

    def checkbox_state_Image(self, s):
        self.checkbox_data_Image = s

    def setUpTime(self, value):
        AdvancedSettingsList[4] = value

    def setDownTime(self, value):
        AdvancedSettingsList[5] = value

    def openDialog(self):
        dlg = AdvancedSetting_Voltage()
        dlg.exec()

    def estimateTime(self):
        
        self.OutputBox.append(str(self.updatedelay))
           
        self.powerloop = ((float(self.powerfin) - float(self.powerini))/ float(self.power_step_size)) + 1

        if self.updatedelay == 0.0:
            constant = 0
                
        else:
            constant = 1

        self.estimatetime = (self.powerloop *(0.2 + 0.8 + (float(self.updatedelay) * constant) )) * float(self.noofloop)
        self.OutputBox.append(str(self.estimatetime) + "seconds")
    

    def savepath(self):  
        # Create a Tkinter root window
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open a directory dialog and return the selected directory path
        directory = filedialog.askdirectory()
        self.savelocation = directory
        self.OutputBox.append(str(self.savelocation))

         

    def executeTest(self):
        global globalvv

        for x in range (int(self.noofloop)):

            """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
            then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
            will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
            begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
            begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
            are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
            optionally export all the details into a CSV file or display a graph after the test is completed.

            """
            self.infoList = []
            self.dataList = []
            self.dataList2 = []

            dict = dictGenerator.input(
                P_Rating=self.Power_Rating,
                power=self.Power,
                rshunt = self.rshunt,
                powerini=self.powerini,
                powerfin=self.powerfin,
                power_step_size = self.power_step_size,

                estimatetime=self.estimatetime,
                updatedelay=self.updatedelay,
                readbackvoltage=self.readbackvoltage,
                readbackcurrent=self.readbackcurrent,
                noofloop=self.noofloop,
                Instrument=self.DMM_Instrument,
                Programming_Error_Gain=self.Programming_Error_Gain,
                Programming_Error_Offset=self.Programming_Error_Offset,
                Readback_Error_Gain=self.Readback_Error_Gain,
                Readback_Error_Offset=self.Readback_Error_Offset,
                unit=self.unit,
                #minCurrent=self.minCurrent,
                maxCurrent=self.maxCurrent,
                #current_step_size=self.current_step_size,
                #minVoltage=self.minVoltage,
                maxVoltage=self.maxVoltage,
                #voltage_step_size=self.voltage_step_size,

                PSU=self.PSU,
                DMM=self.DMM,
                DMM2=self.DMM2,
                ELoad=self.ELoad,

                ELoad_Channel=self.ELoad_Channel,
                PSU_Channel=self.PSU_Channel,
                VoltageSense=self.VoltageSense,
                VoltageRes=self.VoltageRes,
                setFunction=self.setFunction,
                Range=AdvancedSettingsList[0],
                Aperture=AdvancedSettingsList[1],
                AutoZero=AdvancedSettingsList[2],
                InputZ=AdvancedSettingsList[3],
                UpTime=AdvancedSettingsList[4],
                DownTime=AdvancedSettingsList[5],
            )

            if x == 0:
                QMessageBox.warning(
                self,
                "In Progress",
                "Measurement will start now , please do not close the main window until test is completed",
                                    )
                """globalvv = dict["estimatetime"]
                loading_thread = threading.Thread(target=self.tkinter_loading_screen, args=(globalvv,))
                loading_thread.start()"""
                
                
                                      
            for i in [dict]:
                if i == "":
                    QMessageBox.warning(
                        self, "Error", "One of the parameters are not filled in"
                    )
                    break
            else:
                A = VisaResourceManager()
                flag, args = A.openRM(self.ELoad, self.PSU, self.DMM, self.DMM2)

                if flag == 0:
                    string = ""
                    for item in args:
                        string = string + item

                    QMessageBox.warning(self, "VISA IO ERROR", string)
                    exit()

                if self.setFunction == "Current":
                    try:(
                        infoList,
                        dataList,
                        dataList2
                        ) = PowerMeasurement.executePowerMeasurementA(self, dict)
                    
                    
                    except Exception as e:
                        QMessageBox.warning(self, "Error", str(e))
                        exit()

                if self.setFunction == "Voltage":
                    try:(
                        infoList,
                        dataList,
                        dataList2
                        ) = PowerMeasurement.executePowerMeasurementB(self, dict)
                    
                    
                    except Exception as e:
                        QMessageBox.warning(self, "Error", str(e))
                        exit()

                if x == (int(self.noofloop) - 1):   
                    self.OutputBox.append(my_result.getvalue())
                    self.OutputBox.append("Measurement is complete !")


                if self.checkbox_data_Report == 2:
                    powerinstrumentData(self.PSU, self.DMM, self.DMM2, self.ELoad)
                    datatoCSV_PowerAccuracy(infoList, dataList, dataList2)
                    datatoGraph3(infoList, dataList,dataList2)
                    datatoGraph3.scatterComparePower(self, float(self.Programming_Error_Gain), float(self.Programming_Error_Offset), float(self.Readback_Error_Gain), float(self.Readback_Error_Offset), str(self.setFunction), float(self.Power_Rating) )

                    if self.setFunction == "Current":
                        A = xlreportpower(save_directory=self.savelocation, file_name="Power_CC")
                        A.run()
                        df = pd.DataFrame.from_dict(dict, orient="index")
                        df.to_csv("C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powerconfig.csv")

                    elif self.setFunction == "Voltage":
                        A = xlreportpower(save_directory=self.savelocation, file_name="Power_CV")
                        A.run()
                        df = pd.DataFrame.from_dict(dict, orient="index")
                        df.to_csv("C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powerconfig.csv")


                if x == (int(self.noofloop) - 1):  
                    if self.checkbox_data_Image == 2:
                        self.image_dialog = image_Window2()
                        self.image_dialog.setModal(True)
                        self.image_dialog.show()
    
    def tkinter_loading_screen(self, x):
            def stop_loading():
                progress_bar.stop()
                loading_label.config(text="Loading Complete!")

            def update_countdown(remaining_time):
                if remaining_time > 0:
                    loading_label.config(text=f"Loading... {remaining_time} seconds remaining")
                    root.after(1000, update_countdown, remaining_time - 1)
                else:
                    stop_loading()

            def start_loading():
                progress_bar.start()
                update_countdown(float(x))  # Start the countdown

            sleep(2)
            root = tk.Tk()
            root.title("Loading Screen")

            loading_label = tk.Label(root, text="Loading...", font=("Helvetica", 16))
            loading_label.pack(pady=20)

            progress_bar = ttk.Progressbar(root, orient="horizontal", mode="indeterminate", length=280)
            progress_bar.pack(pady=20)
            start_loading()

            root.mainloop()

class BundleMeasurementVoltageDialog(QDialog):
    """Class for configuring the voltage measurement DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py


    """

    def __init__(self):
        """Method where Widgets, Signals and Slots are defined in the GUI for Voltage Measurement"""
        super().__init__()
        # Initialize default CSV path
        self.DATA_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/data.csv"  # or use a dynamic path if needed
        self.IMAGE_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/images/Chart.png"
        self.ERROR_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/error.csv"
        self.image_dialog = None
        
        # Default Values
        #self.PSU_VisaAddress = "USB0::0x2A8D::0xCC04::MY00000037::0::INSTR"
        #self.DMM_VisaAddress = "USB0::0x2A8D::0x1601::MY60094787::0::INSTR"
        #self.ELoad_VisaAddress = "USB0::0x2A8D::0x3902::MY60260005::0::INSTR"
        
        self.Power_Rating = "6000"
        self.Current_Rating = "24"
        self.Voltage_Rating = "800"
        self.Power = "2000"
        self.currloop = "1"
        self.voltloop = "1"
        self.estimatetime = "0"
        self.readbackvoltage = "0"
        self.readbackcurrent = "0"
        self.savelocation = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"
        self.noofloop = "1"
        self.updatedelay = "3.0"
        self.unit = "VOLTAGE"
        self.Programming_Error_Offset = "0.0003"
        self.Programming_Error_Gain = "0.0003"
        self.Readback_Error_Offset = "0.0003"
        self.Readback_Error_Gain = "0.0003"
        self.minCurrent = "0"
        self.maxCurrent = "24"
        self.current_step_size = "1"
        self.minVoltage = "0"
        self.maxVoltage = "800"
        self.voltage_step_size = "80"
        self.PSU = "USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"
        self.OSC = "USB0::0x0957::0x17B0::MY52060151::0::INSTR"
        self.DMM = "USB0::0x2A8D::0x1601::MY60094787::0::INSTR"
        self.ELoad = "USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"
        self.OSC_Channel = "1"
        self.DMM_Instrument = "Keysight"
        self.DUT = "Others"

        self.PSU_Channel = "1"
        self.ELoad_Channel = "1"
        self.setFunction = "Current" #Set Eload in CC Mode
        self.VoltageRes = "SLOW"
        self.VoltageSense = "INT"

        self.checkbox_data_Report = 2
        self.checkbox_data_Image = 2
        self.checkbox_test_VoltageAccuracy = 2
        self.checkbox_test_VoltageLoadRegulation = 2
        self.checkbox_test_TransientRecovery = 2

        self.Range = "Auto"
        self.Aperture = "0.2"
        self.AutoZero = "ON"
        self.inputZ = "ON"
        self.UpTime = "50"
        self.DownTime = "50"

        self.Channel_CouplingMode = "AC"
        self.Trigger_CouplingMode = "DC"
        self.Trigger_Mode = "EDGE"
        self.Trigger_SweepMode = "NORMAL"
        self.Trigger_SlopeMode = "EITHer"
        self.TimeScale = "0.01"
        self.VerticalScale = "0.00001"
        self.I_Step = ""
        self.V_Settling_Band = "0.8"
        self.T_Settling_Band = "0.001"
        self.Probe_Setting = "X10"
        self.Acq_Type = "AVERage"

        self.checkbox_SpecialCase = 2
        self.checkbox_NormalCase = 2
        
        # Ensure DATA_CSV_PATH is defined before use
        if not hasattr(self, 'DATA_CSV_PATH') or not self.DATA_CSV_PATH:
            QMessageBox.warning(self, "Error", "CSV path is not set.")

        self.setWindowTitle("Bundle Measurement")
        # Enable maximize button
        self.setWindowFlags(Qt.Window)

        # Allow resizing
        # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.setMinimumSize(800, 600)
        self.image_window = None
        self.setStyleSheet("font-size: 15px;")

        # create find button 
        QPushButton_Widget0 = QPushButton()
        QPushButton_Widget0.setText("Save Path")
        QPushButton_Widget1 = QPushButton()
        QPushButton_Widget1.setText("Execute Test")
        QPushButton_Widget2 = QPushButton()
        QPushButton_Widget2.setText("Advanced Settings")
        QPushButton_Widget3 = QPushButton()
        QPushButton_Widget3.setText("Estimate Data Collection Time")
        QPushButton_Widget4 = QPushButton()
        QPushButton_Widget4.setText("Find Instruments")
        QCheckBox_Report_Widget = QCheckBox()
        QCheckBox_Report_Widget.setText("Generate Excel Report")
        QCheckBox_Report_Widget.setCheckState(Qt.Checked)
        QCheckBox_Image_Widget = QCheckBox()
        QCheckBox_Image_Widget.setText("Show Graph")
        QCheckBox_Image_Widget.setCheckState(Qt.Checked)
        QCheckBox_SpecialCase_Widget = QCheckBox()
        QCheckBox_SpecialCase_Widget.setText("Special Case (0% <-> 100%)")
        QCheckBox_SpecialCase_Widget.setCheckState(Qt.Checked)
        QCheckBox_NormalCase_Widget = QCheckBox()
        QCheckBox_NormalCase_Widget.setText("Normal Case (50% <-> 100%)")
        QCheckBox_NormalCase_Widget.setCheckState(Qt.Checked)

        #Test checkbox
        QCheckBox_VoltageAccuracy_Widget = QCheckBox()
        QCheckBox_VoltageAccuracy_Widget.setText("Voltage Accuracy")
        QCheckBox_VoltageAccuracy_Widget.setCheckState(Qt.Checked)
        QCheckBox_VoltageLoadRegulation_Widget = QCheckBox()
        QCheckBox_VoltageLoadRegulation_Widget.setText("Voltage Load Regulation")
        QCheckBox_VoltageLoadRegulation_Widget.setCheckState(Qt.Checked)
        QCheckBox_TransientRecovery_Widget = QCheckBox()
        QCheckBox_TransientRecovery_Widget.setText("Transient Recovery")
        QCheckBox_TransientRecovery_Widget.setCheckState(Qt.Checked)

        layout1 = QFormLayout()
        self.OutputBox = QTextBrowser()
        self.OutputBox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.OutputBox.setMinimumHeight(50)  # Start small
        self.OutputBox.setMaximumHeight(200)
        self.OutputBox.append(my_result.getvalue())
        self.setLayout(layout1)

        Desp0 = QLabel()
        Desp1 = QLabel()
        Desp2 = QLabel()
        Desp3 = QLabel()
        Desp4 = QLabel()
        Desp5 = QLabel()
        Desp6 = QLabel()
        Desp7 = QLabel()
        PerformTest = QLabel()
        OscilloscopeSetting = QLabel()
        Desp8 = QLabel()

        Desp0.setFont (desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp5.setFont(desp_font)
        Desp6.setFont(desp_font)
        Desp7.setFont(desp_font)
        PerformTest.setFont(desp_font)
        OscilloscopeSetting.setFont(desp_font)
        #Desp8.setFont(desp_font)

        Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Voltage Sweep:")
        Desp4.setText("Current Sweep:")
        Desp5.setText("No. of Collection:")
        Desp6.setText("Rated Power of DUT Setting [W]:")
        Desp7.setText("Maximum Testing Current")
        PerformTest.setText("Perform Test:")
        OscilloscopeSetting.setText("Oscilloscope Setting:")
        #Desp8.setText("Testing Selection:")

        #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location/Output Wndow:")

        #Testing Selection
        QLabel_Testing_Selection = QLabel()
        QLabel_Testing_Selection.setFont(desp_font)
        QLabel_Testing_Selection.setText("Test:")

        #Find Instruments
        # Connections
        self.QLabel_PSU_VisaAddress = QLabel()
        self.QLabel_DMM_VisaAddress = QLabel()
        self.QLabel_OSC_VisaAddress = QLabel()
        self.QLabel_ELoad_VisaAddress = QLabel()
        self.QLabel_DUT = QLabel()
        QLabel_DMM_Instrument = QLabel()
        self.QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        self.QLabel_DMM_VisaAddress.setText("Visa Address (DMM):")
        self.QLabel_OSC_VisaAddress.setText("Visa Address (OSC):")
        self.QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DMM_Instrument.setText("Instrument Type (DMM):")
        self.QLabel_DUT.setText("DUT:")

        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_DMM_VisaAddress = QComboBox()
        self.QLineEdit_OSC_VisaAddress = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        QComboBox_DMM_Instrument = QComboBox()
        self.QLineEdit_DUT = QComboBox()

        # General Settings
        QLabel_Voltage_Res = QLabel()
        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel() #PSU
        QLabel_Programming_Error_Gain = QLabel()
        QLabel_Programming_Error_Offset = QLabel()
        QLabel_Readback_Error_Gain = QLabel()
        QLabel_Readback_Error_Offset = QLabel()

        QLabel_Voltage_Res.setText("Voltage Resolution (DMM):")
        QLabel_set_PSU_Channel.setText("Set PSU Channel:")
        QLabel_set_ELoad_Channel.setText("Set Eload Channel:")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")
        QLabel_Programming_Error_Gain.setText("Programming Desired Specification (Gain):")
        QLabel_Programming_Error_Offset.setText("Programming Desired Specification (Offset):")
        QLabel_Readback_Error_Gain.setText("Readback Desired Specification (Gain):")
        QLabel_Readback_Error_Offset.setText("Readback Desired Specification (Offset):")

        QComboBox_Voltage_Res = QComboBox()  
        QComboBox_set_PSU_Channel = QComboBox()
        QComboBox_set_ELoad_Channel = QComboBox()
        QComboBox_set_Function = QComboBox()
        QComboBox_Voltage_Sense = QComboBox()
        self.QLineEdit_Programming_Error_Gain = QLineEdit()
        self.QLineEdit_Programming_Error_Offset = QLineEdit()
        self.QLineEdit_Readback_Error_Gain = QLineEdit()
        self.QLineEdit_Readback_Error_Offset = QLineEdit()

        self.QLineEdit_PSU_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"])
        self.QLineEdit_OSC_VisaAddress.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_DMM_VisaAddress.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_ELoad_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"])
        self.QLineEdit_DUT.addItems(["Others", "Excavator"])

        QComboBox_DMM_Instrument.addItems(["Keysight", "Keithley"])
        QComboBox_DMM_Instrument.setEnabled(False)
        QComboBox_Voltage_Res.addItems(["SLOW", "MEDIUM", "FAST"])
        QComboBox_set_Function.addItems(
            [
                "Current Priority",
                "Voltage Priority",
                "Resistance Priority",
            ]
        )
        QComboBox_set_Function.setEnabled(False)
        QComboBox_set_PSU_Channel.addItems(["1", "2", "3", "4"])
        QComboBox_set_PSU_Channel.setEnabled(True)
        QComboBox_set_ELoad_Channel.addItems(["1", "2"])
        QComboBox_set_ELoad_Channel.setEnabled(True)
        QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])
        QComboBox_Voltage_Sense.setEnabled(True)

        #Power for test
        QLabel_Power = QLabel()
        QLabel_Power.setText("Power Set for Test(W):")
        self.QLineEdit_Power = QLineEdit()

        #Rated Power
        QLabel_power_rated = QLabel()
        QLabel_power_rated.setText("Rated Power of DUT (W):")
        self.QLineEdit_power_rated = QLineEdit()

        # Current Sweep
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
        self.QLineEdit_voltage_rated.setFixedSize(100, 40)  # Set fixed size

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
        QLineEdit_OSC_Display_Channel = QLineEdit()
        QLineEdit_V_Settling_Band = QLineEdit()
        QLineEdit_T_Settling_Band = QLineEdit()
        QComboBox_Probe_Setting = QComboBox()
        QComboBox_Acq_Type = QComboBox()
        QComboBox_Probe_Setting.addItems(["X1", "X10", "X20", "X100"])
        QComboBox_Acq_Type.addItems(["NORMal", "PEAK", "AVERage", "HRESolution"])
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

        QComboBox_Channel_CouplingMode = QComboBox()
        QComboBox_Trigger_Mode = QComboBox()
        QComboBox_Trigger_CouplingMode = QComboBox()
        QComboBox_Trigger_SweepMode = QComboBox()
        QComboBox_Trigger_SlopeMode = QComboBox()
        QLineEdit_TimeScale = QLineEdit()
        QLineEdit_VerticalScale = QLineEdit()

        QComboBox_Channel_CouplingMode.addItems(["AC", "DC"])
        QComboBox_Trigger_Mode.addItems(["EDGE", "IIC", "EBUR"])
        QComboBox_Trigger_CouplingMode.addItems(["AC", "DC"])
        QComboBox_Trigger_SweepMode.addItems(["NORMAL", "AUTO"])
        QComboBox_Trigger_SlopeMode.addItems(["ALT", "POS", "NEG", "EITH"])

        QComboBox_Channel_CouplingMode.setEnabled(True)
        QComboBox_Trigger_Mode.setEnabled(True)
        QComboBox_Trigger_CouplingMode.setEnabled(True)
        QComboBox_Trigger_SweepMode.setEnabled(True)
        QComboBox_Trigger_SlopeMode.setEnabled(True)
        QComboBox_Probe_Setting.setEnabled(True)
        QComboBox_Acq_Type.setEnabled(True)

        #Num of Loop/Delay Time
        QLabel_noofloop = QLabel()
        QLabel_noofloop.setText("No. of Data Collection:")
        QComboBox_noofloop = QComboBox()
        QComboBox_noofloop.addItems(["1","2","3","4","5","6","7","8","9","10"])
        QLabel_updatedelay = QLabel()
        QLabel_updatedelay.setText("Delay Time (second) :(Default=50ms)")
        QComboBox_updatedelay = QComboBox()
        QComboBox_updatedelay.addItems(["0.0","0.8","1.0","2.0","3.0", "4.0"])
            
        # Create a horizontal layout for the "Save Path" and checkboxes
        save_path_layout = QHBoxLayout()
        save_path_layout.addWidget(QLabel_Save_Path)  # QLabel for "Save Path"
        #save_path_layout.addWidget(QLineEdit_Save_Path)  # QLineEdit for the path
        save_path_layout.addWidget(QCheckBox_Report_Widget)  # Checkbox for "Generate Excel Report"
        save_path_layout.addWidget(QCheckBox_Image_Widget)  # Checkbox for "Show Graph"

        # Create a horizontal layout for the "Save Path" and checkboxes
        testing_selection_layout = QHBoxLayout()
        testing_selection_layout.addWidget(QLabel_Testing_Selection)  # QLabel for "Save Path"
        testing_selection_layout.addWidget(QCheckBox_VoltageAccuracy_Widget)  # Checkbox for "Generate Excel Report"
        testing_selection_layout.addWidget(QCheckBox_VoltageLoadRegulation_Widget)  # Checkbox for "Show Graph"
        testing_selection_layout.addWidget(QCheckBox_TransientRecovery_Widget) 

        voltage_sweep_layout = QHBoxLayout()
        voltage_sweep_layout.addWidget(Desp3)  # QLabel for "Save Path"
        voltage_sweep_layout.addWidget(QLabel_voltage_rated)  # Checkbox for "Generate Excel Report"
        voltage_sweep_layout.addWidget(self.QLineEdit_voltage_rated )  # Checkbox for "Show Graph"

        current_sweep_layout = QHBoxLayout()
        current_sweep_layout.addWidget(Desp4)  # QLabel for "Save Path"
        current_sweep_layout.addWidget(QLabel_current_rated)  # Checkbox for "Generate Excel Report"
        current_sweep_layout.addWidget(self.QLineEdit_current_rated )  # Checkbox for "Show Graph"

        power_sweep_layout = QHBoxLayout()
        power_sweep_layout.addWidget(Desp6)  # QLabel for "Save Path"
        power_sweep_layout.addWidget(QLabel_power_rated)  # Checkbox for "Generate Excel Report"
        power_sweep_layout.addWidget(self.QLineEdit_power_rated)  # Checkbox for "Show Graph"

        voltage_inifin_layout = QHBoxLayout()
        voltage_inifin_layout.addWidget(QLabel_minVoltage)  # QLabel for "Save Path"
        voltage_inifin_layout.addWidget(self.QLineEdit_minVoltage)  # Checkbox for "Generate Excel Report"
        voltage_inifin_layout.addWidget(QLabel_maxVoltage)  # Checkbox for "Show Graph"
        voltage_inifin_layout.addWidget(self.QLineEdit_maxVoltage)  # Checkbox for "Show Graph"

        current_inifin_layout = QHBoxLayout()
        current_inifin_layout.addWidget(QLabel_minCurrent)  # QLabel for "Save Path"
        current_inifin_layout.addWidget(self.QLineEdit_minCurrent)  # Checkbox for "Generate Excel Report"
        current_inifin_layout.addWidget(QLabel_maxCurrent)  # Checkbox for "Show Graph"
        current_inifin_layout.addWidget(self.QLineEdit_maxCurrent)  # Checkbox for "Show Graph"

        programming_error_layout = QHBoxLayout()
        programming_error_layout.addWidget(QLabel_Programming_Error_Gain)  # QLabel for "Save Path"
        programming_error_layout.addWidget(self.QLineEdit_Programming_Error_Gain)  # Checkbox for "Generate Excel Report"
        programming_error_layout.addWidget(QLabel_Programming_Error_Offset)  # Checkbox for "Show Graph"
        programming_error_layout.addWidget(self.QLineEdit_Programming_Error_Offset)  # Checkbox for "Show Graph"

        readback_error_layout = QHBoxLayout()
        readback_error_layout.addWidget(QLabel_Readback_Error_Gain)  # QLabel for "Save Path"
        readback_error_layout.addWidget(self.QLineEdit_Readback_Error_Gain)  # Checkbox for "Generate Excel Report"
        readback_error_layout.addWidget(QLabel_Readback_Error_Offset)  # Checkbox for "Show Graph"
        readback_error_layout.addWidget(self.QLineEdit_Readback_Error_Offset)  # Checkbox for "Show Graph"

        performtest_layout = QHBoxLayout()
        performtest_layout.addWidget(Desp5)  # QLabel for "Save Path"
        performtest_layout.addWidget(QCheckBox_SpecialCase_Widget)  # Checkbox for "Generate Excel Report"
        performtest_layout.addWidget(QCheckBox_NormalCase_Widget)  # Checkbox for "Show Graph"
    

        layout1.setSpacing(5)  # Reduce spacing
        layout1.setContentsMargins(10, 10, 10, 10)  # Reduce margins
        # Add the combined layout to the main layout
        layout1.addRow(save_path_layout)

        # Rest of your layout remains unchanged
        layout1.addRow(self.OutputBox)
        #layout1.addRow(Desp0)
        layout1.addRow(QPushButton_Widget0)
        layout1.addRow(Desp1)
        layout1.addRow(QPushButton_Widget4)
        layout1.addRow(self.QLabel_DUT, self.QLineEdit_DUT)
        layout1.addRow(self.QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        layout1.addRow(self.QLabel_DMM_VisaAddress, self.QLineEdit_DMM_VisaAddress)
        layout1.addRow(self.QLabel_OSC_VisaAddress, self.QLineEdit_OSC_VisaAddress)
        layout1.addRow(self.QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        layout1.addRow(QLabel_DMM_Instrument, QComboBox_DMM_Instrument)
        layout1.addRow(Desp2)
        layout1.addRow(QLabel_set_PSU_Channel, QComboBox_set_PSU_Channel)
        layout1.addRow(QLabel_set_ELoad_Channel, QComboBox_set_ELoad_Channel)
        layout1.addRow(QLabel_set_Function, QComboBox_set_Function)
        layout1.addRow(QLabel_Voltage_Sense, QComboBox_Voltage_Sense)
        layout1.addRow(programming_error_layout)
        layout1.addRow(readback_error_layout)
        #layout1.addRow(QLabel_Programming_Error_Gain, QLineEdit_Programming_Error_Gain)
        #layout1.addRow(QLabel_Programming_Error_Offset, QLineEdit_Programming_Error_Offset)
        #layout1.addRow(QLabel_Readback_Error_Gain, QLineEdit_Readback_Error_Gain)
        #layout1.addRow(QLabel_Readback_Error_Offset, QLineEdit_Readback_Error_Offset)
        #layout1.addRow(Desp6)
        layout1.addRow(power_sweep_layout)
        layout1.addRow(QLabel_Power, self.QLineEdit_Power)
        layout1.addRow(voltage_sweep_layout)
        layout1.addRow(voltage_inifin_layout)
        #layout1.addRow(QLabel_minVoltage, QLineEdit_minVoltage)
        #layout1.addRow(QLabel_maxVoltage, QLineEdit_maxVoltage)
        layout1.addRow(QLabel_voltage_step_size, self.QLineEdit_voltage_stepsize)
        layout1.addRow(current_sweep_layout)
        layout1.addRow(current_inifin_layout)
        #layout1.addRow(QLabel_minCurrent, QLineEdit_minCurrent)
        #layout1.addRow(QLabel_maxCurrent, QLineEdit_maxCurrent)
        layout1.addRow(QLabel_current_step_size, self.QLineEdit_current_stepsize)
        #layout1.addRow(Desp5)

        layout1.addRow(OscilloscopeSetting)
        layout1.addRow(QLabel_OSC_Display_Channel, QLineEdit_OSC_Display_Channel)
        layout1.addRow(QLabel_V_Settling_Band, QLineEdit_V_Settling_Band)
        layout1.addRow(QLabel_T_Settling_Band, QLineEdit_T_Settling_Band)
        layout1.addRow(QLabel_Probe_Setting, QComboBox_Probe_Setting)
        layout1.addRow(QLabel_Acq_Type, QComboBox_Acq_Type)
        layout1.addRow(QLabel_Channel_CouplingMode, QComboBox_Channel_CouplingMode)
        layout1.addRow(QLabel_Trigger_CouplingMode, QComboBox_Trigger_CouplingMode)
        layout1.addRow(QLabel_Trigger_Mode, QComboBox_Trigger_Mode)
        layout1.addRow(QLabel_Trigger_SweepMode, QComboBox_Trigger_SweepMode)
        layout1.addRow(QLabel_Trigger_SlopeMode, QComboBox_Trigger_SlopeMode)
        layout1.addRow(QLabel_TimeScale, QLineEdit_TimeScale)
        layout1.addRow(QLabel_VerticalScale, QLineEdit_VerticalScale)
        layout1.addRow(performtest_layout)
        layout1.addRow(QLabel_noofloop, QComboBox_noofloop)
        layout1.addRow(QLabel_updatedelay, QComboBox_updatedelay)
        layout1.addRow(testing_selection_layout)
        layout1.addRow(QPushButton_Widget3)
        layout1.addRow(QPushButton_Widget2)
        layout1.addRow(QPushButton_Widget1)        

        AdvancedSettingsList.append(self.Range)
        AdvancedSettingsList.append(self.Aperture)
        AdvancedSettingsList.append(self.AutoZero)
        AdvancedSettingsList.append(self.inputZ)
        AdvancedSettingsList.append(self.UpTime)
        AdvancedSettingsList.append(self.DownTime)

        #Set window and scroll area
        self.setLayout(layout1)
        scroll_area(self,layout1)

        QLineEdit_V_Settling_Band.textEdited.connect(self.V_Settling_Band_changed)
        QLineEdit_T_Settling_Band.textEdited.connect(self.T_Settling_Band_changed)
        QLineEdit_OSC_Display_Channel.textEdited.connect(self.OSC_Channel_changed)
        QComboBox_Channel_CouplingMode.currentTextChanged.connect(self.Channel_CouplingMode_changed )
        QComboBox_Trigger_CouplingMode.currentTextChanged.connect(
            self.Trigger_CouplingMode_changed
        )
        QComboBox_Trigger_Mode.currentTextChanged.connect(self.Trigger_Mode_changed)
        QComboBox_Trigger_SweepMode.currentTextChanged.connect(
            self.Trigger_SweepMode_changed
        )
        QComboBox_Trigger_SlopeMode.currentTextChanged.connect(
            self.Trigger_SlopeMode_changed
        )
        QComboBox_Probe_Setting.currentTextChanged.connect(
            self.Probe_Setting_changed
        )
        QComboBox_Acq_Type.currentTextChanged.connect(
            self.Acq_Type_changed
        )
        QLineEdit_TimeScale.textEdited.connect(self.TimeScale_changed)
        QLineEdit_VerticalScale.textEdited.connect(self.VerticalScale_changed)

        QCheckBox_SpecialCase_Widget.stateChanged.connect(self.checkbox_state_SpecialCase)
        QCheckBox_NormalCase_Widget.stateChanged.connect(self.checkbox_state_NormalCase)

        self.QLineEdit_DUT.currentTextChanged.connect(self.DUT_changed)
        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_DMM_VisaAddress.currentTextChanged.connect(self.DMM_VisaAddress_changed)
        self.QLineEdit_OSC_VisaAddress.currentTextChanged.connect(self.OSC_VisaAddress_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)

        self.QLineEdit_Programming_Error_Gain.textEdited.connect(self.Programming_Error_Gain_changed)
        self.QLineEdit_Programming_Error_Offset.textEdited.connect(self.Programming_Error_Offset_changed)
        self.QLineEdit_Readback_Error_Gain.textEdited.connect(self.Readback_Error_Gain_changed)
        self.QLineEdit_Readback_Error_Offset.textEdited.connect(self.Readback_Error_Offset_changed)

        self.QLineEdit_Power.textEdited.connect(self.Power_changed)
        self.QLineEdit_power_rated.textEdited.connect(self.Power_Rating_changed)
        self.QLineEdit_current_rated.textEdited.connect(self.Current_Rating_changed)
        self.QLineEdit_voltage_rated.textEdited.connect(self.Voltage_Rating_changed)
        self.QLineEdit_minVoltage.textEdited.connect(self.minVoltage_changed)
        self.QLineEdit_maxVoltage.textEdited.connect(self.maxVoltage_changed)
        self.QLineEdit_minCurrent.textEdited.connect(self.minCurrent_changed)
        self.QLineEdit_maxCurrent.textEdited.connect(self.maxCurrent_changed)
        self.QLineEdit_voltage_stepsize.textEdited.connect(self.voltage_step_size_changed)
        self.QLineEdit_current_stepsize.textEdited.connect(self.current_step_size_changed)
        
        QComboBox_set_PSU_Channel.currentTextChanged.connect(self.set_PSU_Channel_changed)
        QComboBox_set_ELoad_Channel.currentTextChanged.connect(self.ELoad_Channel_changed)
        QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)
        QComboBox_Voltage_Res.currentTextChanged.connect(self.set_VoltageRes_changed)
        QComboBox_Voltage_Sense.currentTextChanged.connect(self.set_VoltageSense_changed)

        QComboBox_noofloop.currentTextChanged.connect(self.noofloop_changed)
        QComboBox_updatedelay.currentTextChanged.connect(self.updatedelay_changed)

        QComboBox_DMM_Instrument.currentTextChanged.connect(self.DMM_Instrument_changed)
        self.QLineEdit_DUT.currentIndexChanged.connect(self.on_current_index_changed)

        QCheckBox_Report_Widget.stateChanged.connect(self.checkbox_state_Report)
        QCheckBox_Image_Widget.stateChanged.connect(self.checkbox_state_Image)
        QCheckBox_VoltageAccuracy_Widget.stateChanged.connect(self.checkbox_state_VoltageAccuracy)
        QCheckBox_VoltageLoadRegulation_Widget.stateChanged.connect(self.checkbox_state_VoltageLoadRegulation)
        QCheckBox_TransientRecovery_Widget.stateChanged.connect(self.checkbox_state_TransientRecovery)
  
        QPushButton_Widget0.clicked.connect(self.savepath)
        QPushButton_Widget1.clicked.connect(self.executeTest)
        QPushButton_Widget2.clicked.connect(self.openDialog)
        QPushButton_Widget3.clicked.connect(self.estimateTime)
        QPushButton_Widget4.clicked.connect(self.doFind)

    def on_current_index_changed(self):
        selected_text = self.QLineEdit_DUT.currentText()
        if selected_text == "Excavator":
            self.QLineEdit_Programming_Error_Gain.setText(self.Programming_Error_Gain)
            self.QLineEdit_Programming_Error_Offset.setText(self.Programming_Error_Offset)
            self.QLineEdit_Readback_Error_Gain.setText(self.Readback_Error_Gain)
            self.QLineEdit_Readback_Error_Offset.setText(self.Readback_Error_Offset)
            self.QLineEdit_power_rated.setText(self.Power_Rating)
            self.QLineEdit_Power.setText(self.Power)
            self.QLineEdit_voltage_rated.setText(self.Voltage_Rating)
            self.QLineEdit_minVoltage.setText(self.minVoltage)
            self.QLineEdit_maxVoltage.setText(self.maxVoltage)
            self.QLineEdit_voltage_stepsize.setText(self.voltage_step_size)
            self.QLineEdit_current_rated.setText(self.Current_Rating)
            self.QLineEdit_minCurrent.setText(self.minCurrent)
            self.QLineEdit_maxCurrent.setText(self.maxCurrent)
            self.QLineEdit_current_stepsize.setText(self.current_step_size)
            # self.QLineEdit_OSC_Display_Channel.setText(self.OSC_Channel)
            # self.QLineEdit_V_Settling_Band.setText(self.V_Settling_Band)
            # self.QLineEdit_T_Settling_Band.setText(self.T_Settling_Band)
            # self.QComboBox_Probe_Setting.setCurrentText(self.Probe_Setting)
            # self.QComboBox_Acq_Type.setCurrentText(self.Acq_Type)
            # self.QComboBox_Channel_CouplingMode.setCurrentText(self.Channel_CouplingMode)
            # self.QComboBox_Trigger_Mode.setCurrentText(self.Trigger_Mode)
            # self.QComboBox_Trigger_CouplingMode.setCurrentText(self.Trigger_CouplingMode)
            # self.QComboBox_Trigger_SweepMode.setCurrentText(self.Trigger_SweepMode)
            # self.QComboBox_Trigger_SlopeMode.setCurrentText(self.Trigger_SlopeMode)
            # self.QLineEdit_TimeScale.setText(self.TimeScale)
            # self.QLineEdit_VerticalScale.setText(self.VerticalScale)
            # self.QComboBox_updatedelay.setCurrentText(self.updatedelay)
        
    def set_PSU_Channel_changed(self, s):
        self.PSU_Channel = s

    def ELoad_Channel_changed(self, s):
        self.ELoad_Channel = s

    def Voltage_Rating_changed(self, value):
        self.Voltage_Rating = value

    def Current_Rating_changed(self, value):
        self.Current_Rating = value

    def Power_Rating_changed(self, value):
        self.Power_Rating = value
     
    def Power_changed(self, value):
        self.Power = value

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_DMM_VisaAddress.clear()
            self.QLineEdit_OSC_VisaAddress.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()
            self.visaIdList, self.nameList = NewGetVisaSCPIResources()
                
            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_OSC_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])

        except:
            self.OutputBox.append("No Devices Found!!!")
        return 

  

    def checkbox_state_SpecialCase(self, s):
        self.checkbox_SpecialCase = s

    def checkbox_state_NormalCase(self, s):
        self.checkbox_NormalCase = s

    def updatedelay_changed(self, value):
        self.updatedelay = value
        self.OutputBox.append(str(self.updatedelay))

    def noofloop_changed(self, value):
        self.noofloop = value
        self.OutputBox.append(str(self.noofloop))

    def DMM_Instrument_changed(self, s):
        self.DMM_Instrument = s

    def DUT_changed(self, s):
        self.DUT = s

    def PSU_VisaAddress_changed(self, s):
        self.PSU = s    

    def DMM_VisaAddress_changed(self, s):
        self.DMM = s

    def ELoad_VisaAddress_changed(self, s):
        self.ELoad = s
    
    def OSC_VisaAddress_changed(self, s):
        self.OSC = s

    def OSC_Channel_changed(self, s):
        self.OSC_Channel = s

    def Programming_Error_Gain_changed(self, s):
        self.Programming_Error_Gain = s

    def Programming_Error_Offset_changed(self, s):
        self.Programming_Error_Offset = s

    def Readback_Error_Gain_changed(self, s):
        self.Readback_Error_Gain = s

    def Readback_Error_Offset_changed(self, s):
        self.Readback_Error_Offset = s

    def minVoltage_changed(self, s):
        self.minVoltage = s

    def maxVoltage_changed(self, s):
        self.maxVoltage = s

    def minCurrent_changed(self, s):
        self.minCurrent = s

    def maxCurrent_changed(self, s):
        self.maxCurrent = s

    def voltage_step_size_changed(self, s):
        self.voltage_step_size = s

    def current_step_size_changed(self, s):
        self.current_step_size = s

    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.setFunction = "Voltage"

        elif s == "Current Priority":
            self.setFunction = "Current"

        elif s == "Resistance Priority":
            self.setFunction = "Resistance"

    def set_VoltageRes_changed(self, s):
        self.VoltageRes = s

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.VoltageSense = "INT"
        elif s == "4 Wire":
            self.VoltageSense = "EXT"

    def setRange(self, value):
        AdvancedSettingsList[0] = value

    def setAperture(self, value):
        AdvancedSettingsList[1] = value

    def setAutoZero(self, value):
        AdvancedSettingsList[2] = value

    def setInputZ(self, value):
        AdvancedSettingsList[3] = value

    def checkbox_state_Report(self, s):
        self.checkbox_data_Report = s

    def checkbox_state_Image(self, s):
        self.checkbox_data_Image = s
    
    def checkbox_state_VoltageAccuracy(self, s):
        self.checkbox_test_VoltageAccuracy = s

    def checkbox_state_VoltageLoadRegulation(self, s):
        self.checkbox_test_VoltageLoadRegulation = s
    
    def checkbox_state_TransientRecovery(self, s):
        self.checkbox_test_TransientRecovery = s

    def setUpTime(self, value):
        AdvancedSettingsList[4] = value

    def setDownTime(self, value):
        AdvancedSettingsList[5] = value

    def openDialog(self):
        dlg = AdvancedSetting_Voltage()
        dlg.exec()
    
    def T_Settling_Band_changed(self, s):
        self.T_Settling_Band = s

    def V_Settling_Band_changed(self, s):
        self.V_Settling_Band = s

    def Channel_CouplingMode_changed(self, s):
        self.Channel_CouplingMode = s

    def Trigger_CouplingMode_changed(self, s):
        self.Trigger_CouplingMode = s

    def Trigger_Mode_changed(self, s):
        self.Trigger_Mode = s

    def Trigger_SweepMode_changed(self, s):
        self.Trigger_SweepMode = s

    def Trigger_SlopeMode_changed(self, s):
        self.Trigger_SlopeMode = s
    
    def Probe_Setting_changed(self, s):
        self.Probe_Setting = s
    
    def Acq_Type_changed(self, s):
        self.Acq_Type = s

    def TimeScale_changed(self, s):
        self.TimeScale = s

    def VerticalScale_changed(self, s):
        self.VerticalScale = s

    def estimateTime(self):
        
        self.OutputBox.append(str(self.updatedelay))
           
        self.currloop = ((float(self.maxCurrent) - float(self.minCurrent))/ float(self.current_step_size)) + 1
        self.voltloop = ((float(self.maxVoltage) - float(self.minVoltage))/ float(self.voltage_step_size)) + 1

        if self.updatedelay == 0.0:
            constant = 0
                
        else:
            constant = 1

        self.estimatetime = (self.currloop * self.voltloop *(0.2 + 0.8 + (float(self.updatedelay) * constant) )) * float(self.noofloop)
        self.OutputBox.append(str(self.estimatetime) + "seconds")
    


    def savepath(self):  
        # Create a Tkinter root window
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open a directory dialog and return the selected directory path
        directory = filedialog.askdirectory()
        self.savelocation = directory
        self.OutputBox.append(str(self.savelocation))

         
    

    def executeTest(self):
        global globalvv

        for x in range (int(self.noofloop)):

            """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
            then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
            will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
            begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
            begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
            are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
            optionally export all the details into a CSV file or display a graph after the test is completed.

            """
            self.infoList = []
            self.dataList = []
            self.dataList2 = []

            dict = dictGenerator.input(
                savedir=self.savelocation,
                V_Rating=self.Voltage_Rating,
                I_Rating=self.Current_Rating,
                P_Rating=self.Power_Rating,
                power=self.Power,
                estimatetime=self.estimatetime,
                updatedelay=self.updatedelay,
                readbackvoltage=self.readbackvoltage,
                readbackcurrent=self.readbackcurrent,
                noofloop=self.noofloop,
                Instrument=self.DMM_Instrument,
                Programming_Error_Gain=self.Programming_Error_Gain,
                Programming_Error_Offset=self.Programming_Error_Offset,
                Readback_Error_Gain=self.Readback_Error_Gain,
                Readback_Error_Offset=self.Readback_Error_Offset,
                unit=self.unit,
                minCurrent=self.minCurrent,
                maxCurrent=self.maxCurrent,
                current_step_size=self.current_step_size,
                minVoltage=self.minVoltage,
                maxVoltage=self.maxVoltage,
                voltage_step_size=self.voltage_step_size,
                PSU=self.PSU,
                DMM=self.DMM,
                OSC=self.OSC,
                ELoad=self.ELoad,
                ELoad_Channel=self.ELoad_Channel,
                PSU_Channel=self.PSU_Channel,
                VoltageSense=self.VoltageSense,
                VoltageRes=self.VoltageRes,
                setFunction=self.setFunction,
                Range=AdvancedSettingsList[0],
                Aperture=AdvancedSettingsList[1],
                AutoZero=AdvancedSettingsList[2],
                InputZ=AdvancedSettingsList[3],
                UpTime=AdvancedSettingsList[4],
                DownTime=AdvancedSettingsList[5],

                OSC_Channel=self.OSC_Channel,
                Channel_CouplingMode=self.Channel_CouplingMode,
                Trigger_Mode=self.Trigger_Mode,
                Trigger_CouplingMode=self.Trigger_CouplingMode,
                Trigger_SweepMode=self.Trigger_SweepMode,
                Trigger_SlopeMode=self.Trigger_SlopeMode,
                Probe_Setting=self.Probe_Setting,
                Acq_Type=self.Acq_Type,
                TimeScale=self.TimeScale,
                VerticalScale=self.VerticalScale,
                
                V_Settling_Band=self.V_Settling_Band,
                T_Settling_Band=self.T_Settling_Band,
            )

            #Function: Check if any of the parameters are empty
            if not self.check_missing_params(dict):
                return

            if self.checkbox_test_TransientRecovery != 2 and self.checkbox_test_VoltageAccuracy != 2 and self.checkbox_test_VoltageLoadRegulation != 2:
                QMessageBox.warning(
                    self,
                    "Test is not selected !!!",
                    "Please select the required tests before proceeding."
                )
                break

            if x == 0:
                QMessageBox.warning(
                self,
                "In Progress",
                "Measurement will start now , please do not close the main window until test is completed",
                                    )
                """ globalvv = dict["estimatetime"]
                loading_thread = threading.Thread(target=self.tkinter_loading_screen, args=(globalvv,))
                loading_thread.start()
                """
                
                                      
            for i in [dict]:
                if i == "":
                    QMessageBox.warning(
                        self, "Error", "One of the parameters are not filled in"
                    )
                    break

            else:
                A = VisaResourceManager()
                flag, args = A.openRM(self.ELoad, self.PSU, self.DMM)

                if flag == 0:
                    string = ""
                    for item in args:
                        string = string + item

                    QMessageBox.warning(self, "VISA IO ERROR", string)
                    exit()

                if self.checkbox_test_VoltageAccuracy == 2:
                    if self.DMM_Instrument == "Keysight":
                        try:(
                            infoList,
                            dataList,
                            dataList2
                            ) = NewVoltageMeasurement.Execute_Voltage_Accuracy(self, dict)
                        
                        
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            exit()


                    if x == (int(self.noofloop) - 1):   
                        self.OutputBox.append(my_result.getvalue())
                        self.OutputBox.append("Measurement is complete !")


                    if self.checkbox_data_Report == 2:
                        instrumentData(self.PSU, self.DMM, self.ELoad)
                        datatoCSV_Accuracy(infoList, dataList, dataList2)
                        datatoGraph(infoList, dataList,dataList2)
                        datatoGraph.scatterCompareVoltage(self, float(self.Programming_Error_Gain), float(self.Programming_Error_Offset), float(self.Readback_Error_Gain), float(self.Readback_Error_Offset), str(self.unit), float(self.Voltage_Rating))

                        A = xlreport(save_directory=self.savelocation, file_name=str(self.unit))
                        A.run()
                        df = pd.DataFrame.from_dict(dict, orient="index")
                        df.to_csv("C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/config.csv")

                    if x == (int(self.noofloop) - 1):  
                        if self.checkbox_data_Image == 2:
                            self.image_dialog = image_Window()
                            self.image_dialog.setModal(True)
                            self.image_dialog.show()

                if self.checkbox_test_VoltageLoadRegulation == 2:
                    if self.DMM_Instrument == "Keysight":
                        try:
                            LoadRegulation.executeCV_LoadRegulationA(self, dict)

                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            exit()

                
                    self.OutputBox.append(my_result.getvalue())
                    self.OutputBox.append("Measurement is complete !")
                
                if self.checkbox_test_TransientRecovery == 2:
                    try:
                        if self.checkbox_SpecialCase == 2:
                            RiseFallTime.executeA(self, dict)
                        
                        if self.checkbox_NormalCase == 2:
                            RiseFallTime.executeB(self, dict)

                    except Exception as e:
                        print(e)
                        QMessageBox.warning(self, "Error", str(e))
                        exit()

                    self.OutputBox.append(my_result.getvalue())
                    self.OutputBox.append("Measurement is complete !")                   
   
class BundleMeasurementCurrentandPowerDialog(QDialog):
    """Class for configuring the voltage measurement DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py


    """

    def __init__(self):
        """Method where Widgets, Signals and Slots are defined in the GUI for Voltage Measurement"""
        super().__init__()
        # Initialize default CSV path
        self.DATA_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/data.csv"  # or use a dynamic path if needed
        self.IMAGE_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/images/Chart.png"
        self.ERROR_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/error.csv"
        self.image_dialog = None
        self.POWER_DATA_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powerdata.csv"  # or use a dynamic path if needed
        self.POWER_IMAGE_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/images/powerChart.png"
        self.POWER_ERROR_CSV_PATH = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powererror.csv"

        # Default Values
        #self.PSU_VisaAddress = "USB0::0x2A8D::0xCC04::MY00000037::0::INSTR"
        #self.DMM_VisaAddress = "USB0::0x2A8D::0x1601::MY60094787::0::INSTR"
        #self.ELoad_VisaAddress = "USB0::0x2A8D::0x3902::MY60260005::0::INSTR"
        self.rshunt = "0.05"
        self.Power_Rating = "6000"
        self.Current_Rating = "24"
        self.Voltage_Rating = "800"
        self.Power = "2000"
        self.powerfin = self.Power
        self.powerini = "0"
        self.power_step_size = "60"
        self.currloop = "1"
        self.voltloop = "1"
        self.estimatetime = "0"
        self.readbackvoltage = "0"
        self.readbackcurrent = "0"
        self.savelocation = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing"
        self.noofloop = "1"
        self.updatedelay = "0.0"
        self.unit = "CURRENT"
        self.Programming_Error_Offset = "0.001"
        self.Programming_Error_Gain = "0.001"
        self.Readback_Error_Offset = "0.001"
        self.Readback_Error_Gain = "0.001"

        self.Power_Programming_Error_Offset = "0.005"
        self.Power_Programming_Error_Gain = "0.005"
        self.Power_Readback_Error_Offset = "0.005"
        self.Power_Readback_Error_Gain = "0.005"

        self.minCurrent = "1"
        self.maxCurrent = "1"
        self.current_step_size = "1"
        self.minVoltage = "1"
        self.maxVoltage = "10"
        self.voltage_step_size = "1"

        self.PSU = "USB0::0x2A8D::0xDA04::CN24350083::0::INSTR"
        self.DMM = "USB0::0x2A8D::0x0201::MY57702128::0::INSTR"
        self.DMM2 = "USB0::0x2A8D::0x0201::MY54701197::0::INSTR"
        self.ELoad = "USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"
        self.ELoad_Channel = "1"
        self.PSU_Channel = "1"
        self.DMM_Instrument = "Keysight"

        self.setFunction = "Current" #Set Eload in CC Mode
        self.VoltageRes = "DEF"
        self.VoltageSense = "INT"

        self.checkbox_data_Report = 2
        self.checkbox_data_Image = 2
        self.checkbox_test_CurrentAccuracy = 2
        self.checkbox_test_CurrentLoadRegulation = 2
        self.checkbox_test_PowerAccuracy = 2

        self.Range = "Auto"
        self.Aperture = "0.2"
        self.AutoZero = "ON"
        self.inputZ = "ON"
        self.UpTime = "50"
        self.DownTime = "50"
        
        # Ensure DATA_CSV_PATH is defined before use
        if not hasattr(self, 'DATA_CSV_PATH') or not self.DATA_CSV_PATH:
            QMessageBox.warning(self, "Error", "CSV path is not set.")

        if not hasattr(self, 'POWER_DATA_CSV_PATH') or not self.POWER_DATA_CSV_PATH:
            QMessageBox.warning(self, "Error", "POWER CSV path is not set.")

        self.setWindowTitle("Bundle Measurement Current, Load Regulation and Power")

        self.image_window = None
        self.setWindowFlags(Qt.Window)

        # Allow resizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(800, 600)
        self.image_window = None
        self.setStyleSheet("font-size: 18px;")

        # create find button 
        QPushButton_Widget0 = QPushButton()
        QPushButton_Widget0.setText("Save Path")
        QPushButton_Widget1 = QPushButton()
        QPushButton_Widget1.setText("Execute Test")
        QPushButton_Widget2 = QPushButton()
        QPushButton_Widget2.setText("Advanced Settings")
        QPushButton_Widget3 = QPushButton()
        QPushButton_Widget3.setText("Estimate Data Collection Time")
        QPushButton_Widget4 = QPushButton()
        QPushButton_Widget4.setText("Find Instruments")
        QCheckBox_Report_Widget = QCheckBox()
        QCheckBox_Report_Widget.setText("Generate Excel Report")
        QCheckBox_Report_Widget.setCheckState(Qt.Checked)
        QCheckBox_Image_Widget = QCheckBox()
        QCheckBox_Image_Widget.setText("Show Graph")
        QCheckBox_Image_Widget.setCheckState(Qt.Checked)

          #Test checkbox
        QCheckBox_CurrentAccuracy_Widget = QCheckBox()
        QCheckBox_CurrentAccuracy_Widget.setText("Current Accuracy")
        QCheckBox_CurrentAccuracy_Widget.setCheckState(Qt.Checked)
        QCheckBox_CurrentLoadRegulation_Widget = QCheckBox()
        QCheckBox_CurrentLoadRegulation_Widget.setText("Current Load Regulation")
        QCheckBox_CurrentLoadRegulation_Widget.setCheckState(Qt.Checked)
        QCheckBox_PowerAccuracy_Widget = QCheckBox()
        QCheckBox_PowerAccuracy_Widget.setText("Power Accuracy")
        QCheckBox_PowerAccuracy_Widget.setCheckState(Qt.Checked)

        layout1 = QFormLayout()
        self.OutputBox = QTextBrowser()

        self.OutputBox.append(my_result.getvalue())

        
        Desp0 = QLabel()
        Desp1 = QLabel()
        Desp2 = QLabel()
        Desp3 = QLabel()
        Desp4 = QLabel()
        Desp5 = QLabel()
        Desp6 = QLabel()
        Desp7 = QLabel()
        Desp8 = QLabel()



        #Desp0.setFont (desp_font)
        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        Desp3.setFont(desp_font)
        Desp4.setFont(desp_font)
        Desp5.setFont(desp_font)
        Desp6.setFont(desp_font)
        Desp7.setFont(desp_font)
        #Desp8.setFont(desp_font)


        #Desp0.setText("Save Path:")
        Desp1.setText("Connections:")
        Desp2.setText("General Settings:")
        Desp3.setText("Voltage Sweep:")
        Desp4.setText("Current Sweep:")
        Desp5.setText("No. of Collection:")
        Desp6.setText("Rated Power of DUT Setting [W]:")
        Desp7.setText("Maximum Testing Current")
        #Desp8.setText("Testing Selection:")



        #Save Path
        QLabel_Save_Path = QLabel()
        QLabel_Save_Path.setFont(desp_font)
        QLabel_Save_Path.setText("Drive Location/Output Wndow:")

        #Testing Selection
        QLabel_Testing_Selection = QLabel()
        QLabel_Testing_Selection.setFont(desp_font)
        QLabel_Testing_Selection.setText("Test:")


        #Find Instruments
        # Connections
        self.QLabel_PSU_VisaAddress = QLabel()
        self.QLabel_DMM_VisaAddressforVoltage = QLabel()
        self.QLabel_DMM_VisaAddressforCurrent = QLabel()
        self.QLabel_ELoad_VisaAddress = QLabel()
        QLabel_DMM_Instrument = QLabel()
        self.QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        self.QLabel_DMM_VisaAddressforVoltage.setText("Visa Address (DMM for Measure Voltage):")
        self.QLabel_DMM_VisaAddressforCurrent.setText("Visa Address (DMM for Measure Current Shunt):")
        self.QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DMM_Instrument.setText("Instrument Type (DMM):")
        #QLineEdit_PSU_VisaAddress = QLineEdit()
        #QLineEdit_DMM_VisaAddress = QLineEdit()
        #QLineEdit_ELoad_VisaAddress = QLineEdit()

        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_DMM_VisaAddressforVoltage = QComboBox()
        self.QLineEdit_DMM_VisaAddressforCurrent = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        QComboBox_DMM_Instrument = QComboBox()

        # General Settings
        QLabel_Voltage_Res = QLabel()
        #QLabel_ELoad_Display_Channel = QLabel()
        #QLabel_PSU_Display_Channel = QLabel()
        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
    
        QLabel_Programming_Error_Gain = QLabel()
        QLabel_Programming_Error_Offset = QLabel()
        QLabel_Readback_Error_Gain = QLabel()
        QLabel_Readback_Error_Offset = QLabel()

        QLabel_Power_Programming_Error_Gain = QLabel()
        QLabel_Power_Programming_Error_Offset = QLabel()
        QLabel_Power_Readback_Error_Gain = QLabel()
        QLabel_Power_Readback_Error_Offset = QLabel()

        QLabel_Voltage_Res.setText("Voltage Resolution (DMM):")
        #QLabel_ELoad_Display_Channel.setText("Display Channel (Eload):")
        #QLabel_PSU_Display_Channel.setText("Display Channel (PSU):")

        QLabel_set_PSU_Channel.setText("PSU Channel:")
        QLabel_set_ELoad_Channel.setText("Eload Channel:")
        QLabel_set_Function.setText("Mode(Eload):")
        QLabel_Voltage_Sense.setText("Voltage Sense:")

        QLabel_Programming_Error_Gain.setText("Current_Programming Desired Specification (Gain):")
        QLabel_Programming_Error_Offset.setText("Current_Programming Desired Specification (Offset):")
        QLabel_Readback_Error_Gain.setText("Current_Readback Desired Specification (Gain):")
        QLabel_Readback_Error_Offset.setText("Current_Readback Desired Specification (Offset):")

        QLabel_Power_Programming_Error_Gain.setText("Power_Programming Desired Specification (Gain):")
        QLabel_Power_Programming_Error_Offset.setText("Power_Programming Desired Specification (Offset):")
        QLabel_Power_Readback_Error_Gain.setText("Power_Readback Desired Specification (Gain):")
        QLabel_Power_Readback_Error_Offset.setText("Power_Readback Desired Specification (Offset):")

        QComboBox_Voltage_Res = QComboBox()
        QComboBox_set_PSU_Channel = QComboBox()
        QComboBox_set_ELoad_Channel = QComboBox()
        QComboBox_set_Function = QComboBox()
        QComboBox_Voltage_Sense = QComboBox()

        QLineEdit_Programming_Error_Gain = QLineEdit()
        QLineEdit_Programming_Error_Offset = QLineEdit()
        QLineEdit_Readback_Error_Gain = QLineEdit()
        QLineEdit_Readback_Error_Offset = QLineEdit()

        QLineEdit_Power_Programming_Error_Gain = QLineEdit()
        QLineEdit_Power_Programming_Error_Offset = QLineEdit()
        QLineEdit_Power_Readback_Error_Gain = QLineEdit()
        QLineEdit_Power_Readback_Error_Offset = QLineEdit()

        self.QLineEdit_PSU_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350097::0::INSTR"])
        self.QLineEdit_DMM_VisaAddressforVoltage.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_DMM_VisaAddressforCurrent.addItems(["USB0::0x2A8D::0x1601::MY60094787::0::INSTR"])
        self.QLineEdit_ELoad_VisaAddress.addItems(["USB0::0x2A8D::0xDA04::CN24350105::0::INSTR"])

        QComboBox_DMM_Instrument.addItems(["Keysight", "Keithley"])
        QComboBox_DMM_Instrument.setEnabled(False)
        QComboBox_Voltage_Res.addItems(["SLOW", "MEDIUM", "FAST"])
        QComboBox_set_Function.addItems(
            [
                "Current Priority",
                "Voltage Priority",
                "Resistance Priority",
            ]
        )
        QComboBox_set_PSU_Channel.addItems(["1", "2", "3", "4"])
        QComboBox_set_PSU_Channel.setEnabled(True)

        QComboBox_set_ELoad_Channel.addItems(["1", "2"])
        QComboBox_set_ELoad_Channel.setEnabled(True)

        QComboBox_set_Function.setEnabled(False)
        QComboBox_Voltage_Sense.addItems(["2 Wire", "4 Wire"])

        #Power for test
        QLabel_Power = QLabel()
        QLabel_Power.setText("Power Set for Test(W):")
        QLineEdit_Power = QLineEdit()

        #Rated Power
        QLabel_power_rated = QLabel()
        QLabel_power_rated.setText("Rated Power of DUT (W):")
        QLineEdit_power_rated = QLineEdit()

        QLabel_PowerINI = QLabel()
        QLabel_PowerINI.setText("Initial Power (W):")
        QLineEdit_PowerINI = QLineEdit()

        QLabel_PowerFIN = QLabel()
        QLabel_PowerFIN.setText("Final Power (W):")
        QLineEdit_PowerFIN = QLineEdit()

        QLabel_power_step_size = QLabel()
        QLabel_power_step_size.setText("Step Size:")
        QLineEdit_power_step_size = QLineEdit()

        # Current Sweep
        QLabel_minCurrent = QLabel()
        QLabel_maxCurrent = QLabel()
        QLabel_current_step_size = QLabel()
        QLabel_current_rated = QLabel()
        QLabel_minCurrent.setText("Initial Current (A):")
        QLabel_maxCurrent.setText("Final Current (A):")
        QLabel_current_step_size.setText("Step Size:")
        QLabel_current_rated.setText("DUT Rated Current:")

        QLineEdit_minCurrent = QLineEdit()
        QLineEdit_maxCurrent = QLineEdit()
        QLineEdit_current_stepsize = QLineEdit()
        QLineEdit_current_rated = QLineEdit()

        # Voltage Sweep
        QLabel_minVoltage = QLabel()
        QLabel_maxVoltage = QLabel()
        QLabel_voltage_step_size = QLabel()
        QLabel_voltage_rated = QLabel()
        QLabel_minVoltage.setText("Initial Voltage (V):")
        QLabel_maxVoltage.setText("Final Voltage (V):")
        QLabel_voltage_step_size.setText("Step Size:")
        QLabel_voltage_rated.setText("DUT Rated Voltage:")

        QLineEdit_minVoltage = QLineEdit()
        QLineEdit_maxVoltage = QLineEdit()
        QLineEdit_voltage_stepsize = QLineEdit()
        QLineEdit_voltag_rated = QLineEdit()
        QLineEdit_voltag_rated.setFixedSize(100, 40)  # Set fixed size

        QLabel_rshunt = QLabel()
        QLabel_rshunt.setText("Shunt Resistance Value (ohm):")
        QLineEdit_rshunt = QLineEdit()

        #Loop
        QLabel_noofloop = QLabel()
        QLabel_noofloop.setText("No. of Data Collection:")
        QComboBox_noofloop = QComboBox()
        QComboBox_noofloop.addItems(["1","2","3","4","5","6","7","8","9","10"])


        QLabel_updatedelay = QLabel()
        QLabel_updatedelay.setText("Delay Time (second) :(Default=50ms)")
        QComboBox_updatedelay = QComboBox()
        QComboBox_updatedelay.addItems(["0.0","0.8","1.0","2.0","3.0", "4.0"])
        
        # Create a horizontal layout for the "Save Path" and checkboxes
        save_path_layout = QHBoxLayout()
        save_path_layout.addWidget(QLabel_Save_Path)  # QLabel for "Save Path"
        #save_path_layout.addWidget(QLineEdit_Save_Path)  # QLineEdit for the path
        save_path_layout.addWidget(QCheckBox_Report_Widget)  # Checkbox for "Generate Excel Report"
        save_path_layout.addWidget(QCheckBox_Image_Widget)  # Checkbox for "Show Graph"

        # Create a horizontal layout for the "Save Path" and checkboxes
        testing_selection_layout = QHBoxLayout()
        testing_selection_layout.addWidget(QLabel_Testing_Selection)  # QLabel for "Save Path"
        testing_selection_layout.addWidget(QCheckBox_CurrentAccuracy_Widget)  # Checkbox for "Generate Excel Report"
        testing_selection_layout.addWidget(QCheckBox_CurrentLoadRegulation_Widget)  # Checkbox for "Show Graph"
        testing_selection_layout.addWidget(QCheckBox_PowerAccuracy_Widget) 

        voltage_sweep_layout = QHBoxLayout()
        voltage_sweep_layout.addWidget(Desp3)  # QLabel for "Save Path"
        voltage_sweep_layout.addWidget(QLabel_voltage_rated)  # Checkbox for "Generate Excel Report"
        voltage_sweep_layout.addWidget( QLineEdit_voltag_rated )  # Checkbox for "Show Graph"

        current_sweep_layout = QHBoxLayout()
        current_sweep_layout.addWidget(Desp4)  # QLabel for "Save Path"
        current_sweep_layout.addWidget(QLabel_current_rated)  # Checkbox for "Generate Excel Report"
        current_sweep_layout.addWidget( QLineEdit_current_rated )  # Checkbox for "Show Graph"

        power_sweep_layout = QHBoxLayout()
        power_sweep_layout.addWidget(Desp6)  # QLabel for "Save Path"
        power_sweep_layout.addWidget(QLabel_power_rated)  # Checkbox for "Generate Excel Report"
        power_sweep_layout.addWidget( QLineEdit_power_rated)  # Checkbox for "Show Graph"

        voltage_inifin_layout = QHBoxLayout()
        voltage_inifin_layout.addWidget(QLabel_minVoltage)  # QLabel for "Save Path"
        voltage_inifin_layout.addWidget(QLineEdit_minVoltage)  # Checkbox for "Generate Excel Report"
        voltage_inifin_layout.addWidget(QLabel_maxVoltage)  # Checkbox for "Show Graph"
        voltage_inifin_layout.addWidget(QLineEdit_maxVoltage)  # Checkbox for "Show Graph"

        current_inifin_layout = QHBoxLayout()
        current_inifin_layout.addWidget(QLabel_minCurrent)  # QLabel for "Save Path"
        current_inifin_layout.addWidget(QLineEdit_minCurrent)  # Checkbox for "Generate Excel Report"
        current_inifin_layout.addWidget(QLabel_maxCurrent)  # Checkbox for "Show Graph"
        current_inifin_layout.addWidget(QLineEdit_maxCurrent)  # Checkbox for "Show Graph"

        programming_error_layout = QHBoxLayout()
        programming_error_layout.addWidget(QLabel_Programming_Error_Gain)  # QLabel for "Save Path"
        programming_error_layout.addWidget(QLineEdit_Programming_Error_Gain)  # Checkbox for "Generate Excel Report"
        programming_error_layout.addWidget(QLabel_Programming_Error_Offset)  # Checkbox for "Show Graph"
        programming_error_layout.addWidget(QLineEdit_Programming_Error_Offset)  # Checkbox for "Show Graph"

        readback_error_layout = QHBoxLayout()
        readback_error_layout.addWidget(QLabel_Readback_Error_Gain)  # QLabel for "Save Path"
        readback_error_layout.addWidget(QLineEdit_Readback_Error_Gain)  # Checkbox for "Generate Excel Report"
        readback_error_layout.addWidget(QLabel_Readback_Error_Offset)  # Checkbox for "Show Graph"
        readback_error_layout.addWidget(QLineEdit_Readback_Error_Offset)  # Checkbox for "Show Graph"

        power_programming_error_layout = QHBoxLayout()
        power_programming_error_layout.addWidget(QLabel_Power_Programming_Error_Gain)  # QLabel for "Save Path"
        power_programming_error_layout.addWidget(QLineEdit_Power_Programming_Error_Gain)  # Checkbox for "Generate Excel Report"
        power_programming_error_layout.addWidget(QLabel_Power_Programming_Error_Offset)  # Checkbox for "Show Graph"
        power_programming_error_layout.addWidget(QLineEdit_Power_Programming_Error_Offset)  # Checkbox for "Show Graph"

        power_readback_error_layout = QHBoxLayout()
        power_readback_error_layout.addWidget(QLabel_Power_Readback_Error_Gain)  # QLabel for "Save Path"
        power_readback_error_layout.addWidget(QLineEdit_Power_Readback_Error_Gain)  # Checkbox for "Generate Excel Report"
        power_readback_error_layout.addWidget(QLabel_Power_Readback_Error_Offset)  # Checkbox for "Show Graph"
        power_readback_error_layout.addWidget(QLineEdit_Power_Readback_Error_Offset)  # Checkbox for "Show Graph"

        # Add the combined layout to the main layout
        layout1.addRow(save_path_layout)

        # Rest of your layout remains unchanged
        layout1.addRow(self.OutputBox)
        #layout1.addRow(Desp0)
        layout1.addRow(QPushButton_Widget0)
        layout1.addRow(Desp1)
        layout1.addRow(QPushButton_Widget4)
        layout1.addRow(self.QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        layout1.addRow(self.QLabel_DMM_VisaAddressforVoltage, self.QLineEdit_DMM_VisaAddressforVoltage)
        layout1.addRow(self.QLabel_DMM_VisaAddressforCurrent, self.QLineEdit_DMM_VisaAddressforCurrent)
        layout1.addRow(self.QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        layout1.addRow(QLabel_DMM_Instrument, QComboBox_DMM_Instrument)
        layout1.addRow(Desp2)
        layout1.addRow(QLabel_set_PSU_Channel, QComboBox_set_PSU_Channel)
        layout1.addRow(QLabel_set_ELoad_Channel, QComboBox_set_ELoad_Channel)
        layout1.addRow(QLabel_set_Function, QComboBox_set_Function)
        layout1.addRow(QLabel_Voltage_Sense, QComboBox_Voltage_Sense)
        layout1.addRow(programming_error_layout)
        layout1.addRow(readback_error_layout)
        layout1.addRow(power_programming_error_layout)
        layout1.addRow(power_readback_error_layout)
        layout1.addRow(Desp6)
        layout1.addRow(power_sweep_layout)
        layout1.addRow(QLabel_Power, QLineEdit_Power)
        layout1.addRow(QLabel_PowerINI, QLineEdit_PowerINI)
        layout1.addRow(QLabel_PowerFIN, QLineEdit_PowerFIN)
        layout1.addRow(QLabel_power_step_size, QLineEdit_power_step_size)
        layout1.addRow(voltage_sweep_layout)
        layout1.addRow(voltage_inifin_layout)
        #layout1.addRow(QLabel_minVoltage, QLineEdit_minVoltage)
        #layout1.addRow(QLabel_maxVoltage, QLineEdit_maxVoltage)
        layout1.addRow(QLabel_voltage_step_size, QLineEdit_voltage_stepsize)
        layout1.addRow(Desp4)
        layout1.addRow(current_sweep_layout)
        layout1.addRow(current_inifin_layout)
        #layout1.addRow(QLabel_minCurrent, QLineEdit_minCurrent)
        #layout1.addRow(QLabel_maxCurrent, QLineEdit_maxCurrent)
        layout1.addRow(QLabel_current_step_size, QLineEdit_current_stepsize)
        layout1.addRow(Desp5)
        layout1.addRow(QLabel_rshunt, QLineEdit_rshunt)
        layout1.addRow(QLabel_noofloop, QComboBox_noofloop)
        layout1.addRow(QLabel_updatedelay, QComboBox_updatedelay)
        layout1.addRow(testing_selection_layout)
        layout1.addRow(QPushButton_Widget3)
        layout1.addRow(QPushButton_Widget2)
        layout1.addRow(QPushButton_Widget1)        

        AdvancedSettingsList.append(self.Range)
        AdvancedSettingsList.append(self.Aperture)
        AdvancedSettingsList.append(self.AutoZero)
        AdvancedSettingsList.append(self.inputZ)
        AdvancedSettingsList.append(self.UpTime)
        AdvancedSettingsList.append(self.DownTime)

        #Set window and scroll area
        self.setLayout(layout1)
        scroll_area(self,layout1)

        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_DMM_VisaAddressforVoltage.currentTextChanged.connect(self.DMM_VisaAddressforVoltage_changed)
        self.QLineEdit_DMM_VisaAddressforCurrent.currentTextChanged.connect(self.DMM_VisaAddressforCurrent_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)
        #QLineEdit_ELoad_Display_Channel.textEdited.connect(self.ELoad_Channel_changed)
        #QLineEdit_PSU_Display_Channel.textEdited.connect(self.PSU_Channel_changed)
        QLineEdit_Programming_Error_Gain.textEdited.connect(self.Programming_Error_Gain_changed)
        QLineEdit_Programming_Error_Offset.textEdited.connect(self.Programming_Error_Offset_changed)
        QLineEdit_Readback_Error_Gain.textEdited.connect(self.Readback_Error_Gain_changed)
        QLineEdit_Readback_Error_Offset.textEdited.connect(self.Readback_Error_Offset_changed)

        QLineEdit_Power_Programming_Error_Gain.textEdited.connect(self.Power_Programming_Error_Gain_changed)
        QLineEdit_Power_Programming_Error_Offset.textEdited.connect(self.Power_Programming_Error_Offset_changed)
        QLineEdit_Power_Readback_Error_Gain.textEdited.connect(self.Power_Readback_Error_Gain_changed)
        QLineEdit_Power_Readback_Error_Offset.textEdited.connect(self.Power_Readback_Error_Offset_changed)

        QLineEdit_Power.textEdited.connect(self.Power_changed)
        QLineEdit_PowerINI.textEdited.connect(self.PowerINI_changed)
        QLineEdit_PowerFIN.textEdited.connect(self.PowerFIN_changed)
        QLineEdit_power_rated.textEdited.connect(self.Power_Rating_changed)
        QLineEdit_power_step_size.textEdited.connect(self.power_step_size_changed)
        QLineEdit_rshunt.textEdited.connect(self.rshunt_changed)

        QLineEdit_minVoltage.textEdited.connect(self.minVoltage_changed)
        QLineEdit_maxVoltage.textEdited.connect(self.maxVoltage_changed)
        QLineEdit_minCurrent.textEdited.connect(self.minCurrent_changed)
        QLineEdit_maxCurrent.textEdited.connect(self.maxCurrent_changed)
        QLineEdit_voltag_rated.textEdited.connect(self.Volatge_Rating_changed)
        QLineEdit_current_rated.textEdited.connect(self.Current_Rating_changed)
        QLineEdit_voltage_stepsize.textEdited.connect(self.voltage_step_size_changed)
        QLineEdit_current_stepsize.textEdited.connect(self.current_step_size_changed)

        QComboBox_set_PSU_Channel.currentTextChanged.connect(self.set_PSU_Channel_changed)
        QComboBox_set_ELoad_Channel.currentTextChanged.connect(self.set_ELoad_Channel_changed)
        QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)
        QComboBox_Voltage_Res.currentTextChanged.connect(self.set_VoltageRes_changed)
        QComboBox_Voltage_Sense.currentTextChanged.connect(self.set_VoltageSense_changed)

        QComboBox_noofloop.currentTextChanged.connect(self.noofloop_changed)
        QComboBox_updatedelay.currentTextChanged.connect(self.updatedelay_changed)

        QComboBox_DMM_Instrument.currentTextChanged.connect(self.DMM_Instrument_changed)

        QCheckBox_Report_Widget.stateChanged.connect(self.checkbox_state_Report)
        QCheckBox_Image_Widget.stateChanged.connect(self.checkbox_state_Image)
        QCheckBox_CurrentAccuracy_Widget.stateChanged.connect(self.checkbox_state_CurrentAccuracy)
        QCheckBox_CurrentLoadRegulation_Widget.stateChanged.connect(self.checkbox_state_CurrentLoadRegulation)
        QCheckBox_PowerAccuracy_Widget.stateChanged.connect(self.checkbox_state_PowerAccuracy)
    

        QPushButton_Widget0.clicked.connect(self.savepath)
        QPushButton_Widget1.clicked.connect(self.executeTest)
        QPushButton_Widget2.clicked.connect(self.openDialog)
        QPushButton_Widget3.clicked.connect(self.estimateTime)
        QPushButton_Widget4.clicked.connect(self.doFind)
    
    def Current_Rating_changed(self, value):
        self.Current_Rating = value
    
    def Volatge_Rating_changed(self, value):
        self.Voltage_Rating = value

    def set_PSU_Channel_changed(self, s):
        self.PSU_Channel = s
    
    def set_ELoad_Channel_changed(self, s):
        self.ELoad_Channel = s

    def rshunt_changed(self, value):
        self.rshunt = value

    def Power_Rating_changed(self, value):
        self.Power_Rating = value
     
    def Power_changed(self, value):
        self.Power = value
    
    def PowerINI_changed(self, value):
        self.powerini= value
    
    def PowerFIN_changed(self, value):
        self.powerfin = value
    
    def power_step_size_changed(self, value):
        self.power_step_size = value

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_DMM_VisaAddressforVoltage.clear()
            self.QLineEdit_DMM_VisaAddressforCurrent.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()
            
            self.visaIdList, self.nameList = GetVisaSCPIResources()
            
            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddressforVoltage.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddressforCurrent.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])
                
        except:
            self.OutputBox.append("No Devices Found!!!")
        return   



    def updatedelay_changed(self, value):
        self.updatedelay = value
        self.OutputBox.append(str(self.updatedelay))

    def noofloop_changed(self, value):
        self.noofloop = value
        self.OutputBox.append(str(self.noofloop))

    def DMM_Instrument_changed(self, s):
        self.DMM_Instrument = s

    def PSU_VisaAddress_changed(self, s):
        self.PSU = s    

    def DMM_VisaAddressforVoltage_changed(self, s):
        self.DMM = s
    
    def DMM_VisaAddressforCurrent_changed(self, s):
        self.DMM2 = s

    def ELoad_VisaAddress_changed(self, s):
        self.ELoad = s

    def Programming_Error_Gain_changed(self, s):
        self.Programming_Error_Gain = s

    def Programming_Error_Offset_changed(self, s):
        self.Programming_Error_Offset = s

    def Readback_Error_Gain_changed(self, s):
        self.Readback_Error_Gain = s

    def Readback_Error_Offset_changed(self, s):
        self.Readback_Error_Offset = s

    def Power_Programming_Error_Gain_changed(self, s):
        self.Power_Programming_Error_Gain = s

    def Power_Programming_Error_Offset_changed(self, s):
        self.Power_Programming_Error_Offset = s

    def Power_Readback_Error_Gain_changed(self, s):
        self.Power_Readback_Error_Gain = s

    def Power_Readback_Error_Offset_changed(self, s):
        self.Power_Readback_Error_Offset = s

    def minVoltage_changed(self, s):
        self.minVoltage = s

    def maxVoltage_changed(self, s):
        self.maxVoltage = s

    def minCurrent_changed(self, s):
        self.minCurrent = s

    def maxCurrent_changed(self, s):
        self.maxCurrent = s

    def voltage_step_size_changed(self, s):
        self.voltage_step_size = s

    def current_step_size_changed(self, s):
        self.current_step_size = s

    def set_Function_changed(self, s):
        if s == "Voltage Priority":
            self.setFunction = "Voltage"

        elif s == "Current Priority":
            self.setFunction = "Current"

        elif s == "Resistance Priority":
            self.setFunction = "Resistance"

    def set_VoltageRes_changed(self, s):
        self.VoltageRes = s

    def set_VoltageSense_changed(self, s):
        if s == "2 Wire":
            self.VoltageSense = "INT"
        elif s == "4 Wire":
            self.VoltageSense = "EXT"

    def setRange(self, value):
        AdvancedSettingsList[0] = value

    def setAperture(self, value):
        AdvancedSettingsList[1] = value

    def setAutoZero(self, value):
        AdvancedSettingsList[2] = value

    def setInputZ(self, value):
        AdvancedSettingsList[3] = value

    def checkbox_state_Report(self, s):
        self.checkbox_data_Report = s

    def checkbox_state_Image(self, s):
        self.checkbox_data_Image = s
    
    def checkbox_state_CurrentAccuracy(self, s):
        self.checkbox_test_CurrentAccuracy = s

    def checkbox_state_CurrentLoadRegulation(self, s):
        self.checkbox_test_CurrentLoadRegulation = s
    
    def checkbox_state_PowerAccuracy(self, s):
        self.checkbox_test_PowerAccuracy = s

    def setUpTime(self, value):
        AdvancedSettingsList[4] = value

    def setDownTime(self, value):
        AdvancedSettingsList[5] = value

    def openDialog(self):
        dlg = AdvancedSetting_Voltage()
        dlg.exec()

    def estimateTime(self):
        
        self.OutputBox.append(str(self.updatedelay))
           
        self.currloop = ((float(self.maxCurrent) - float(self.minCurrent))/ float(self.current_step_size)) + 1
        self.voltloop = ((float(self.maxVoltage) - float(self.minVoltage))/ float(self.voltage_step_size)) + 1

        if self.updatedelay == 0.0:
            constant = 0
                
        else:
            constant = 1

        self.estimatetime = (self.currloop * self.voltloop *(0.2 + 0.8 + (float(self.updatedelay) * constant) )) * float(self.noofloop)
        self.OutputBox.append(str(self.estimatetime) + "seconds")
    



    def savepath(self):  
        # Create a Tkinter root window
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open a directory dialog and return the selected directory path
        directory = filedialog.askdirectory()
        self.savelocation = directory
        self.OutputBox.append(str(self.savelocation))

         
    

    def executeTest(self):
        global globalvv

        for x in range (int(self.noofloop)):

            """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
            then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
            will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
            begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
            begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
            are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
            optionally export all the details into a CSV file or display a graph after the test is completed.

            """
            self.infoList = []
            self.dataList = []
            self.dataList2 = []

            dict = dictGenerator.input(
                rshunt = self.rshunt,
                savedir=self.savelocation,
                V_Rating=self.Voltage_Rating,
                I_Rating=self.Current_Rating,
                P_Rating=self.Power_Rating,

                power=self.Power,
                powerini=self.powerini,
                powerfin=self.powerfin,
                power_step_size = self.power_step_size,

                estimatetime=self.estimatetime,
                updatedelay=self.updatedelay,
                readbackvoltage=self.readbackvoltage,
                readbackcurrent=self.readbackcurrent,
                noofloop=self.noofloop,
                Instrument=self.DMM_Instrument,
                Programming_Error_Gain=self.Programming_Error_Gain,
                Programming_Error_Offset=self.Programming_Error_Offset,
                Readback_Error_Gain=self.Readback_Error_Gain,
                Readback_Error_Offset=self.Readback_Error_Offset,

                PowerProgramming_Error_Gain=self.Power_Programming_Error_Gain,
                PowerProgramming_Error_Offset=self.Power_Programming_Error_Offset,
                PowerReadback_Error_Gain=self.Power_Readback_Error_Gain,
                PowerReadback_Error_Offset=self.Power_Readback_Error_Offset,

                unit=self.unit,
                minCurrent=self.minCurrent,
                maxCurrent=self.maxCurrent,
                current_step_size=self.current_step_size,
                minVoltage=self.minVoltage,
                maxVoltage=self.maxVoltage,
                voltage_step_size=self.voltage_step_size,
                

                PSU=self.PSU,
                DMM=self.DMM,
                DMM2=self.DMM2,
                ELoad=self.ELoad,
                ELoad_Channel=self.ELoad_Channel,
                PSU_Channel=self.PSU_Channel,
                VoltageSense=self.VoltageSense,
                VoltageRes=self.VoltageRes,
                setFunction=self.setFunction,
                Range=AdvancedSettingsList[0],
                Aperture=AdvancedSettingsList[1],
                AutoZero=AdvancedSettingsList[2],
                InputZ=AdvancedSettingsList[3],
                UpTime=AdvancedSettingsList[4],
                DownTime=AdvancedSettingsList[5],
            )

            #Function: Check if any of the parameters are empty
            if not self.check_missing_params(dict):
                return

            #Function: Check if any test selected
            if self.checkbox_test_CurrentAccuracy != 2 and self.checkbox_test_CurrentLoadRegulation != 2 and self.checkbox_test_PowerAccuracy != 2:
                QMessageBox.warning(
                    self,
                    "Test is not selected !!!",
                    "Please select the required tests before proceeding."
                )
                break
            
            if x == 0:
                QMessageBox.warning(
                self,
                "In Progress",
                "Measurement will start now , please do not close the main window until test is completed",
                                    )
                """globalvv = dict["estimatetime"]
                loading_thread = threading.Thread(target=self.tkinter_loading_screen, args=(globalvv,))
                loading_thread.start()"""
                
                
                                      
            for i in [dict]:
                if i == "":
                    QMessageBox.warning(
                        self, "Error", "One of the parameters are not filled in"
                    )
                    break

            else:
                A = VisaResourceManager()
                flag, args = A.openRM(self.ELoad, self.PSU, self.DMM, self.DMM2)

                if flag == 0:
                    string = ""
                    for item in args:
                        string = string + item

                    QMessageBox.warning(self, "VISA IO ERROR", string)
                    break

                if self.checkbox_test_CurrentAccuracy == 2:
                    if self.DMM_Instrument == "Keysight":
                        try:
                        # Clear existing values before assigning new ones

                        # Execute measurement and assign new values
                            infoList, dataList, dataList2 = NewCurrentMeasurement.executeCurrentMeasurementA(self, dict)
                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            exit()


                    if self.checkbox_data_Report == 2:
                        instrumentData(self.PSU, self.DMM, self.ELoad)
                        datatoCSV_Accuracy2(infoList, dataList, dataList2)
                        datatoGraph2(infoList, dataList,dataList2)
                        datatoGraph2.scatterCompareCurrent2(self, float(self.Programming_Error_Gain), float(self.Programming_Error_Offset), float(self.Readback_Error_Gain), float(self.Readback_Error_Offset), str(self.unit), float(self.Current_Rating))
                        

                        # Create DataFrame from dictionary
                        df = pd.DataFrame.from_dict(dict, orient="index")
                        
                        # Rename the index to a custom name, e.g., 'Index'
                        df = df.rename_axis('Test Condition')

                        # Save to CSV with the renamed index
                        df.to_csv("C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/config.csv")

                        # Create report
                        A = xlreport(save_directory=self.savelocation, file_name=str(self.unit))
                        A.run()
                        

                    if x == (int(self.noofloop) - 1):  
                        if self.checkbox_data_Image == 2:
                            self.image_dialog = image_Window()
                            self.image_dialog.setModal(True)
                            self.image_dialog.show()

                if self.checkbox_test_CurrentLoadRegulation == 2:
                    if self.DMM_Instrument == "Keysight":
                        try:
                            LoadRegulation.executeCC_LoadRegulationA(self, dict)

                            """ A = xlreport(save_directory=self.savelocation, file_name=str(self.unit))
                            A.run()
                            df = pd.DataFrame.from_dict(dict, orient="index")
                            df.to_csv("csv/config.csv")"""

                        except Exception as e:
                            QMessageBox.warning(self, "Error", str(e))
                            exit()

                
                    self.OutputBox.append(my_result.getvalue())
                    self.OutputBox.append("Measurement is complete !")
                
                if self.checkbox_test_PowerAccuracy == 2:
                    try:
                        if self.checkbox_test_CurrentAccuracy == 2:
                            # Clear existing values before assigning new ones
                            infoList.clear()
                            dataList.clear()
                            dataList2.clear()
                            infoList, dataList, dataList2 = PowerMeasurement.executePowerMeasurementA(self, dict)  # Power CC
                        else:
                            # Execute measurement and assign new values
                            infoList, dataList, dataList2 = PowerMeasurement.executePowerMeasurementA(self, dict)  # Power CC

                    except Exception as e:
                        QMessageBox.warning(self, "Error", str(e))
                        exit()

                    if self.checkbox_data_Report == 2:
                        powerinstrumentData(self.PSU, self.DMM, self.DMM2, self.ELoad)
                        datatoCSV_PowerAccuracy(infoList, dataList, dataList2)
                        datatoGraph3(infoList, dataList,dataList2)
                        self.setFunction="Current"
                        datatoGraph3.scatterComparePower(self, float(self.Power_Programming_Error_Gain), float(self.Power_Programming_Error_Offset), float(self.Power_Readback_Error_Gain), float(self.Power_Readback_Error_Offset), str(self.setFunction), float(self.Power_Rating) )
                        A = xlreportpower(save_directory=self.savelocation, file_name="Power_CC")
                        A.run()
                        df = pd.DataFrame.from_dict(dict, orient="index")
                        df.to_csv("C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powerconfig.csv")
                    
        
                    try:
                        # Clear existing values before assigning new ones
                        infoList.clear()
                        dataList.clear()
                        dataList2.clear()

                        # Execute measurement and assign new values
                        infoList, dataList, dataList2 = PowerMeasurement.executePowerMeasurementB(self, dict)  # Power CC

                    except Exception as e:
                        QMessageBox.warning(self, "Error", str(e))
                        exit()

                    if self.checkbox_data_Report == 2:   
                        powerinstrumentData(self.PSU, self.DMM, self.DMM2, self.ELoad)
                        datatoCSV_PowerAccuracy(infoList, dataList, dataList2)
                        datatoGraph3(infoList, dataList,dataList2)
                        self.setFunction="Voltage"
                        datatoGraph3.scatterComparePower(self, float(self.Power_Programming_Error_Gain), float(self.Power_Programming_Error_Offset), float(self.Power_Readback_Error_Gain), float(self.Power_Readback_Error_Offset), str(self.setFunction), float(self.Power_Rating) )
                        A = xlreportpower(save_directory=self.savelocation, file_name="Power_CV")
                        A.run()
                        df = pd.DataFrame.from_dict(dict, orient="index")
                        df.to_csv("C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Executable/GUI/powerconfig.csv")
        
                    if x == (int(self.noofloop) - 1):   
                        self.OutputBox.append(my_result.getvalue())
                        self.OutputBox.append("Measurement is complete !")

                    if x == (int(self.noofloop) - 1):  
                        if self.checkbox_data_Image == 2:
                            self.image_dialog = image_Window2()
                            self.image_dialog.setModal(True)
                            self.image_dialog.show()
                        
  
########----------------------- Advanced Setting for Standalone Code ----------------#####################
class AdvancedSetting_Voltage(QDialog):
    """This class is to configure the Advanced Settings when conducting voltage measurements,
    It prompts a secondary dialogue for users to customize more advanced parametes such as
    aperture, range, AutoZero, input impedance etc.
    """

    def __init__(self):
        """Method defining the signals, slots and widgets for Advaced Settings of Voltage Measurements"""
        super().__init__()

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

        self.QComboBox_Range.setCurrentText(self.Range)
        self.QComboBox_Aperture.setCurrentText(self.Aperture)
        self.QComboBox_AutoZero.setCurrentText(self.AutoZero)
        self.QComboBox_InputZ.setCurrentText(self.inputZ)
        #Uptime and Downtime Not Setting Yet
        self.QLineEdit_UpTime.setText(self.UpTime)
        self.QLineEdit_DownTime.setText(self.DownTime)

        # Connect the button to close the window
        QPushButton_Widget.clicked.connect(self.close)

        # Connect the signals for changes in the fields (if necessary)
        self.QComboBox_Range.currentTextChanged.connect(self.RangeChanged)
        self.QComboBox_Aperture.currentTextChanged.connect(self.ApertureChanged)
        self.QComboBox_AutoZero.currentTextChanged.connect(self.AutoZeroChanged)
        self.QComboBox_InputZ.currentTextChanged.connect(self.InputZChanged)
        self.QLineEdit_UpTime.textEdited.connect(self.UpTimeChanged)
        self.QLineEdit_DownTime.textEdited.connect(self.DownTimeChanged)


    def RangeChanged(self, s):
        self.Range = s

    def ApertureChanged(self, s):
        self.Aperture = s

    def AutoZeroChanged(self, s):
        self.AutoZero = s

    def InputZChanged(self, s):
        self.inputZ = s

    def UpTimeChanged(self, s):
        self.UpTime = s

    def DownTimeChanged(self, s):
        self.DownTime = s

class AdvancedSetting_Current(QDialog):
    """This class is to configure the Advanced Settings when conducting current measurements,
    It prompts a secondary dialogue for users to customize more advanced parametes such as
    aperture, range, AutoZero, input impedance etc.
    """

    def __init__(self):
        """Method defining the signals, slots and widgets for Advaced Settings of Voltage Measurements"""
        super().__init__()
        self.setWindowTitle("Advanced Window (Current)")
        QPushButton_Widget = QPushButton()

        QPushButton_Widget.setText("Confirm")
        layout1 = QFormLayout()

        Desp1 = QLabel()
        Desp1.setText("DMM Settings:")
        Desp2 = QLabel()
        Desp2.setText("PSU Settings:")

        Desp1.setFont(desp_font)
        Desp2.setFont(desp_font)
        QLabel_Range = QLabel()
        QLabel_Aperture = QLabel()
        QLabel_AutoZero = QLabel()
        QLabel_Terminal = QLabel()
        QLabel_UpTime = QLabel()
        QLabel_DownTime = QLabel()

        QLabel_Range.setText("DC Voltage Range")
        QLabel_Aperture.setText("NPLC / PLC")
        QLabel_AutoZero.setText("Auto Zero Function")
        QLabel_Terminal.setText("Current Terminal:")
        QLabel_UpTime.setText("Programming Settling Time (UP) (in ms)")
        QLabel_DownTime.setText("Programming Setting Time (Down) (in ms)")

        QComboBox_Range = QComboBox()
        QComboBox_Aperture = QComboBox()
        QComboBox_AutoZero = QComboBox()
        QComboBox_Terminal = QComboBox()
        QLineEdit_UpTime = QLineEdit()
        QLineEdit_DownTime = QLineEdit()

        QComboBox_Range.addItems(["Auto", "0.001", "0.01", "0.1", "1", "3"])
        QComboBox_Aperture.addItems(
            ["0.001", "0.002", "0.006", "0.02", "0.06", "0.2", "1", "10", "100"]
        )
        QComboBox_AutoZero.addItems(["ON", "OFF"])
        QComboBox_Terminal.addItems(["3A", "10A"])

        layout1.addRow(Desp1)
        layout1.addRow(QLabel_Range, QComboBox_Range)
        layout1.addRow(QLabel_Aperture, QComboBox_Aperture)
        layout1.addRow(QLabel_AutoZero, QComboBox_AutoZero)
        layout1.addRow(QLabel_Terminal, QComboBox_Terminal)
        layout1.addRow(Desp2)
        layout1.addRow(QLabel_UpTime, QLineEdit_UpTime)
        layout1.addRow(QLabel_DownTime, QLineEdit_DownTime)
        layout1.addRow(QPushButton_Widget)
        self.setLayout(layout1)

        QPushButton_Widget.clicked.connect(self.close)
        QComboBox_Range.currentTextChanged.connect(self.RangeChanged)
        QComboBox_Aperture.currentTextChanged.connect(self.ApertureChanged)
        QComboBox_AutoZero.currentTextChanged.connect(self.AutoZeroChanged)
        QComboBox_Terminal.currentTextChanged.connect(self.TerminalChanged)
        QLineEdit_UpTime.textEdited.connect(self.UpTimeChanged)
        QLineEdit_DownTime.textEdited.connect(self.DownTimeChanged)

        self.QComboBox_Range = QComboBox_Range

    def RangeChanged(self, s):
        self.Range = s
        CurrentMeasurementDialog.setRange(self, self.Range)
        CC_LoadRegulationDialog.setRange(self, self.Range)

    def ApertureChanged(self, s):
        self.Aperture = s
        CurrentMeasurementDialog.setAperture(self, self.Aperture)
        CC_LoadRegulationDialog.setAperture(self, self.Aperture)

    def AutoZeroChanged(self, s):
        self.AutoZero = s
        CurrentMeasurementDialog.setAutoZero(self, self.AutoZero)
        CC_LoadRegulationDialog.setAutoZero(self, self.AutoZero)

    def TerminalChanged(self, s):
        self.Terminal = s
        CurrentMeasurementDialog.setTerminal(self, self.Terminal)
        CC_LoadRegulationDialog.setTerminal(self, self.Terminal)
        if self.Terminal == "10A":
            self.QComboBox_Range.setEnabled(False)

        else:
            self.QComboBox_Range.setEnabled(True)

    def UpTimeChanged(self, s):
        self.UpTime = s
        CurrentMeasurementDialog.setUpTime(self, self.UpTime)
        CC_LoadRegulationDialog.setUpTime(self, self.UpTime)

    def DownTimeChanged(self, s):
        self.DownTime = s
        CurrentMeasurementDialog.setDownTime(self, self.DownTime)
        CC_LoadRegulationDialog.setDownTime(self, self.DownTime)


#########----------------------- Image Graph Display ---------------------------------####################
class image_Window(QDialog):
    """Class to display graph of DUT Test results"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image")
        self.im = QPixmap(IMAGE_PATH)
        
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
class Parameters:
    def __init__(self):
        super().__init__() 

        # Initialize default CSV path
        self.image_dialog = None
        self.DATA_CSV_PATH = DATA_CSV_PATH
        self.IMAGE_PATH = IMAGE_PATH
        self.ERROR_CSV_PATH = ERROR_CSV_PATH
        self.POWER_DATA_CSV_PATH = POWER_DATA_CSV_PATH
        self.POWER_IMAGE_PATH = POWER_IMAGE_PATH 
        self.POWER_ERROR_CSV_PATH = POWER_ERROR_CSV_PATH
        self.CONFIG_PATH = config_folder

        # Ensure DATA_CSV_PATH is defined before use
        if not hasattr(self, 'DATA_CSV_PATH') or not self.DATA_CSV_PATH:
            QMessageBox.warning(self, "Error", "CSV path is not set.")

        if not hasattr(self, 'POWER_DATA_CSV_PATH') or not self.POWER_DATA_CSV_PATH:
            QMessageBox.warning(self, "Error", "POWER CSV path is not set.")

        #Image Setup
        self.image_connections_path = {
            "VoltageAccuracy": os.path.join(setup_img_folder , "1.png"),
            "CurrentAccuracy": os.path.join(setup_img_folder , "2.png"),
            "VoltageLoadRegulation": os.path.join(setup_img_folder , "3.png"),
            "CurrentLoadRegulation": os.path.join(setup_img_folder , "4.png"),
            "PowerAccuracy": os.path.join(setup_img_folder , "5.png"),
            "TransientRecovery": os.path.join(setup_img_folder , "6.png"),
            "OVP_Test": os.path.join(setup_img_folder , "7.png"),
            "TestB": os.path.join(setup_img_folder , "8.png"),
            "TestC": os.path.join(setup_img_folder , "9.png"),
        }

        #Initial Values
        self.Voltage_Rating = None
        self.Current_Rating = None
        self.Power_Rating = None
        self.Power =  None
        self.currloop = None
        self.voltloop =  None
        self.estimatetime =  None
        self.readbackvoltage =  None
        self.readbackcurrent =  None
        self.savelocation =  None
        self.noofloop =  None
        self.updatedelay =  None
        self.unit =  None

        self.Programming_Error_Offset =  None
        self.Programming_Error_Gain =  None
        self.Readback_Error_Offset =  None
        self.Readback_Error_Gain =  None
        self.Load_Programming_Error_Offset =  None
        self.Load_Programming_Error_Gain =  None

        self.Programming_Response_Up_NoLoad = None
        self.Programming_Response_Up_FullLoad = None
        self.Programming_Response_Down_NoLoad = None
        self.Programming_Response_Down_FullLoad = None

        self.OVP_ErrorGain = None
        self.OVP_ErrorOffset = None

        self.minCurrent = 0
        self.maxCurrent = 0
        self.current_step_size =  0
        self.minVoltage =  0
        self.maxVoltage =  0
        self.voltage_step_size =  0

        self.powerfin = self.Power
        self.powerini = None
        self.power_step_size = None
        self.Power_Programming_Error_Offset = None
        self.Power_Programming_Error_Gain = None
        self.Power_Readback_Error_Offset = None
        self.Power_Readback_Error_Gain = None

        self.PSU =  None
        self.OSC = None
        self.DMM =  None
        self.DMM2 = None
        self.ELoad =  None
        self.ELoad_Channel = None
        self.PSU_Channel =  None
        self.OSC_Channel = None
        self.DMM_Instrument =  None
        self.rshunt = None
        self.OVP_Level = None
        self.OCP_Level = None
        self.OCPActivationTime = None
        self.SPOperationMode = "Independent"

        self.setFunction =  None
        self.VoltageRes =  None
        self.VoltageSense =  None

        self.Range = None
        self.Aperture = None
        self.AutoZero = None
        self.inputZ = None
        self.UpTime = None
        self.DownTime = None
        self.selected_text = "Others"

        self.Channel_CouplingMode = None
        self.Trigger_CouplingMode = None
        self.Trigger_Mode = None
        self.Trigger_SweepMode = None
        self.Trigger_SlopeMode = None
        self.TimeScale = None
        self.VerticalScale = None
        self.I_Step = None
        self.V_Settling_Band = None
        self.T_Settling_Band = None
        self.Probe_Setting = None
        self.Acq_Type = None

        self.ACSource= None
        self.AC_CurrentLimit= 10
        self.AC_VoltageOutput= 230
        self.Frequency= 50
        self.AC_Supply_Type= "Plug"
        self.Line_Reg_Range= [100,115,230]

        self.load_data()

        #Disable wheel move when hover over combobox
        self.filter = ComboBoxWheelFilter()
        QApplication.instance().installEventFilter(self.filter)
    
        # === NEW ADDITIONS ===
    def __getitem__(self, key):
        """Allow dictionary-style access (self.params['key'])"""
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"'{key}' not found in Parameters")

    def __setitem__(self, key, value):
        """Allow dictionary-style assignment (self.params['key'] = value)"""
        setattr(self, key, value)
    
    def update_selection(self, selected_text):
        """Update selected text and reload config file"""
        self.selected_text = selected_text
        self.load_data()

    def load_data(self):
        """Reads configuration file and returns a dictionary of key-value pairs."""
        config_data = {}
        if self.selected_text =="Excavator":
            self.config_file = os.path.join(config_folder,"config_Excavator.txt")
            
        elif self.selected_text =="Dolphin":
            self.config_file = os.path.join(config_folder,"config_Dolphin.txt")
            
        elif self.selected_text =="SMU":
            self.config_file = os.path.join(config_folder,"config_SMU.txt")

        else:
            self.config_file = os.path.join(config_folder,"config_Others.txt")

        try:
            with open(self.config_file, "r") as file: 
                for line in file:

                    if not line or line.startswith("#") or line.startswith("//"):
                        continue 

                    if "=" in line:
                        key, value = line.strip().split("=")
                        config_data[key.strip()] = value.strip()

            for key, value in config_data.items():
                if key == "savelocation":
                    # If savelocation has a valid value, do not overwrite it
                    if self.savelocation and self.savelocation != "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
                        continue 
                    else:
                        setattr(self, key, value)
                else:
                    setattr(self, key, value)

        except FileNotFoundError:
            print("Config file not found. Using default values.")

        return config_data


class AllTestMeasurement(QDialog):
    """Class for configuring the voltage measurement DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguements, please refer to DUT_Test.py


    """
    def __init__(self):
        super().__init__()
        self.params = Parameters()

        #Create find button 
        self.QPushButton_Widget0 = QPushButton()
        self.QPushButton_Widget0.setText("Save Path")
        self.QPushButton_Widget1 = QPushButton()
        self.QPushButton_Widget1.setText("Execute Test")
        QPushButton_Widget2 = QPushButton()
        QPushButton_Widget2.setText("Advanced Settings")
        QPushButton_Widget3 = QPushButton()
        QPushButton_Widget3.setText("Estimate Data Collection Time")
        QPushButton_Widget4 = QPushButton()
        QPushButton_Widget4.setText("Find Instruments")
        QPushButton_Widget5 = QPushButton()
        QPushButton_Widget5.setText("Return Home")
        
        self.QPushButton_Voltage_Widget = QPushButton()
        self.QPushButton_Voltage_Widget.setText("Voltage")
        self.QPushButton_Current_Widget = QPushButton()
        self.QPushButton_Current_Widget.setText("Current/Power")
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
        self.QCheckBox_SpecialCase_Widget = QCheckBox()
        self.QCheckBox_SpecialCase_Widget.setText("Special Case (0% <-> 100%)")
        self.QCheckBox_SpecialCase_Widget.setCheckState(Qt.Checked)
        self.QCheckBox_NormalCase_Widget = QCheckBox()
        self.QCheckBox_NormalCase_Widget.setText("Normal Case (50% <-> 100%)")
        self.QCheckBox_NormalCase_Widget.setCheckState(Qt.Checked)
        QCheckBox_Lock_Widget = QCheckBox()
        QCheckBox_Lock_Widget.setText("🔒Lock Widget")

        #Test Selection checkbox
        self.QCheckBox_VoltageAccuracy_Widget = QCheckBox()
        self.QCheckBox_VoltageAccuracy_Widget.setText("Voltage Accuracy")
        self.QCheckBox_VoltageAccuracy_Widget.setCheckState(Qt.Checked)
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

        # Abort button
        self.abort_button = QPushButton("Abort")
        self.abort_button.clicked.connect(self.abort_test)
        self.abort_button.setVisible(False)
        self.abort_button.setEnabled(False)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)

        #Output Display
        self.OutputBox = QTextBrowser()
        self.OutputBox.append(f"{my_result.getvalue()}")
        self.OutputBox.append("")  # Empty line after each append

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
        QLabel_PSU_VisaAddress = QLabel()
        QLabel_DMM_VisaAddressforVoltage = QLabel()
        self.QLabel_DMM_VisaAddressforCurrent = QLabel()
        self.QLabel_OSC_VisaAddress = QLabel()
        QLabel_ELoad_VisaAddress = QLabel()
        QLabel_DMM_Instrument = QLabel()
        QLabel_DUT = QLabel()
        QLabel_AC_Supply_Type = QLabel()

        QLabel_PSU_VisaAddress.setText("Visa Address (PSU):")
        QLabel_DMM_VisaAddressforVoltage.setText("Visa Address (DMM-Voltage):")
        self.QLabel_DMM_VisaAddressforCurrent.setText("Visa Address (DMM-Current Shunt):")
        self.QLabel_OSC_VisaAddress.setText("Visa Address (OSC):")
        QLabel_ELoad_VisaAddress.setText("Visa Address (ELoad):")
        QLabel_DMM_Instrument.setText("Instrument Type (DMM):")
        QLabel_DUT.setText("DUT:")
        QLabel_AC_Supply_Type.setText("AC Supply:")

        self.QLineEdit_PSU_VisaAddress = QComboBox()
        self.QLineEdit_DMM_VisaAddressforVoltage = QComboBox()
        self.QLineEdit_DMM_VisaAddressforCurrent = QComboBox()
        self.QLineEdit_OSC_VisaAddress = QComboBox()
        self.QLineEdit_ELoad_VisaAddress = QComboBox()
        self.QComboBox_DMM_Instrument = QComboBox()
        self.QComboBox_DUT = QComboBox()
        self.QComboBox_AC_Supply_Type = QComboBox()

        # General Settings
        QLabel_Voltage_Res = QLabel()
        QLabel_set_PSU_Channel = QLabel()
        QLabel_set_ELoad_Channel = QLabel()
        QLabel_set_Function = QLabel()
        QLabel_Voltage_Sense = QLabel()
        QLabel_OVP_Level = QLabel()
        QLabel_OCP_Level = QLabel()
        QLabel_OCP_Activation_Time = QLabel()
        QLabel_SPOperationMode = QLabel()
        QLabel_Line_Reg_Range = QLabel()

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

        self.QComboBox_DUT.addItems(["Others", "Excavator", "Dolphin", "SMU"])
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
        self.QComboBox_SPOperationMode.setEnabled(True)
        self.QComboBox_SPOperationMode.addItems(["Independent","Series","Parallel"])
        self.QComboBox_Line_Reg_Range.addItems(["100-115-230","100"])
        self.QComboBox_Line_Reg_Range.setEnabled(False)

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
        save_path_layout.addWidget(QLabel_Save_Path)  # QLabel for "Save Path"
        #save_path_layout.addWidget(QLineEdit_Save_Path)  # QLineEdit for the path
        save_path_layout.addWidget(self.QCheckBox_Report_Widget)  # Checkbox for "Generate Excel Report"
        save_path_layout.addWidget(self.QCheckBox_Image_Widget)  # Checkbox for "Show Graph"
        save_path_layout.addWidget(QCheckBox_Lock_Widget)  # Checkbox for "Show Graph"

#+++++++++++++++++++++++++Layout Organization Part --(Organize Layout of GUI here)++++++++++++++++++++++++++++++++++++++++++++++++++++
        Voltage_Current_Selection_Layout = QVBoxLayout()
        Voltage_Current_Selection_Layout.addWidget(self.QPushButton_Voltage_Widget)
        Voltage_Current_Selection_Layout.addWidget(self.QPushButton_Current_Widget)
        
        self.Current_Test_group = QGroupBox()
        Current_Testing_Selection_Layout = QFormLayout(self.Current_Test_group )
        Current_Testing_Selection_Layout.addWidget(QLabel_Testing_Selection)  
        Current_Testing_Selection_Layout.addWidget(self.QCheckBox_CurrentAccuracy_Widget)
        Current_Testing_Selection_Layout.addWidget(self.QCheckBox_CurrentLoadRegulation_Widget)
        Current_Testing_Selection_Layout.addWidget(self.QCheckBox_PowerAccuracy_Widget)
        Current_Testing_Selection_Layout.addWidget(self.QCheckBox_CurrentLineRegulation_Widget)
        Current_Testing_Selection_Layout.addWidget(self.QCheckBox_OCP_Test_Widget)

        self.Voltage_Test_group = QGroupBox()
        Voltage_Testing_Selection_Layout = QFormLayout(self.Voltage_Test_group)
        Voltage_Testing_Selection_Layout.addWidget(QLabel_Testing_Selection)  
        Voltage_Testing_Selection_Layout.addWidget(self.QCheckBox_VoltageAccuracy_Widget)  
        Voltage_Testing_Selection_Layout.addWidget(self.QCheckBox_VoltageLoadRegulation_Widget) 
        Voltage_Testing_Selection_Layout.addWidget(self.QCheckBox_TransientRecovery_Widget) 
        Voltage_Testing_Selection_Layout.addWidget(self.QCheckBox_OVP_Test_Widget)
        Voltage_Testing_Selection_Layout.addWidget(self.QCheckBox_VoltageLineRegulation_Widget)
        Voltage_Testing_Selection_Layout.addWidget(self.QCheckBox_ProgrammingSpeed_Widget)

        #Connections Layout
        self.Connection_group = QGroupBox()
        Connection_layout = QFormLayout(self.Connection_group)
        Connection_layout.addRow(QPushButton_Widget4)
        Connection_layout.addRow(QLabel_DUT, self.QComboBox_DUT)
        Connection_layout.addRow(QLabel_AC_Supply_Type, self.QComboBox_AC_Supply_Type)
        Connection_layout.addRow(QLabel_PSU_VisaAddress, self.QLineEdit_PSU_VisaAddress)
        Connection_layout.addRow(QLabel_DMM_VisaAddressforVoltage, self.QLineEdit_DMM_VisaAddressforVoltage)
        Connection_layout.addRow(self.QLabel_DMM_VisaAddressforCurrent, self.QLineEdit_DMM_VisaAddressforCurrent)
        Connection_layout.addRow(QLabel_ELoad_VisaAddress, self.QLineEdit_ELoad_VisaAddress)
        Connection_layout.addRow(self.QLabel_OSC_VisaAddress, self.QLineEdit_OSC_VisaAddress)
        Connection_layout.addRow(QLabel_DMM_Instrument, self.QComboBox_DMM_Instrument)

        #General Setting Layout
        self.General_group = QGroupBox()
        General_Setting_layout = QFormLayout(self.General_group)
        General_Setting_layout.addRow(QLabel_set_PSU_Channel, self.QComboBox_set_PSU_Channel)
        General_Setting_layout.addRow(QLabel_set_ELoad_Channel, self.QComboBox_set_ELoad_Channel)
        General_Setting_layout.addRow(QLabel_set_Function, self.QComboBox_set_Function)
        General_Setting_layout.addRow(self.QLabel_rshunt, self.QLineEdit_rshunt)
        General_Setting_layout.addRow(QLabel_Voltage_Sense, self.QComboBox_Voltage_Sense)
        General_Setting_layout.addRow(QLabel_OVP_Level, self.QLineEdit_OVP_Level)
        General_Setting_layout.addRow(QLabel_OCP_Level, self.QLineEdit_OCP_Level)
        General_Setting_layout.addRow(QLabel_OCP_Activation_Time, self.QLineEdit_OCP_ActivationTime_Error)
        General_Setting_layout.addRow(QLabel_SPOperationMode, self.QComboBox_SPOperationMode)
        General_Setting_layout.addRow(QLabel_Line_Reg_Range, self.QComboBox_Line_Reg_Range)

        #Test Ratings (Current/Voltage/Power)
        self.power_setting_widget = QWidget()
        power_init_step_layout = QFormLayout(self.power_setting_widget)
        power_init_step_layout
        power_init_step_layout.addRow(self.QLabel_PowerINI, self.QLineEdit_PowerINI)
        power_init_step_layout.addRow(self.QLabel_power_step_size, self.QLineEdit_power_step_size)
        power_group = QGroupBox()
        power_sweep_layout = QFormLayout(power_group)
        power_sweep_layout.addRow(Desp4) 
        power_sweep_layout.addRow(QLabel_power_rated, self.QLineEdit_power_rated)  
        power_sweep_layout.addRow(QLabel_Power, self.QLineEdit_Power)
        power_sweep_layout.addRow("",self.power_setting_widget)
        voltage_group = QGroupBox()
        voltage_inifin_layout = QFormLayout(voltage_group)
        voltage_inifin_layout.addRow(Desp5)
        voltage_inifin_layout.addRow(QLabel_voltage_rated, self.QLineEdit_voltage_rated)
        voltage_inifin_layout.addRow(QLabel_minVoltage, self.QLineEdit_minVoltage) 
        voltage_inifin_layout.addRow(QLabel_maxVoltage, self.QLineEdit_maxVoltage) 
        voltage_inifin_layout.addRow(QLabel_voltage_step_size, self.QLineEdit_voltage_stepsize)
        current_group = QGroupBox()
        current_inifin_layout = QFormLayout(current_group)
        current_inifin_layout.addRow(Desp6)  
        current_inifin_layout.addRow(QLabel_current_rated, self.QLineEdit_current_rated )  
        current_inifin_layout.addRow(QLabel_minCurrent, self.QLineEdit_minCurrent) 
        current_inifin_layout.addRow(QLabel_maxCurrent, self.QLineEdit_maxCurrent)
        current_inifin_layout.addRow(QLabel_current_step_size, self.QLineEdit_current_stepsize)
        self.Ratings_Widget = QGroupBox()
        Ratings_Layout = QHBoxLayout(self.Ratings_Widget)
        Ratings_Layout.addWidget(power_group)
        Ratings_Layout.addWidget(voltage_group)
        Ratings_Layout.addWidget(current_group)

        #Gain Error Settings
        self.programming_error_widget = QGroupBox()
        programming_error_layout = QFormLayout(self.programming_error_widget)
        programming_error_layout.addRow(QLabel_Programming_Error_Gain, self.QLineEdit_Programming_Error_Gain)
        programming_error_layout.addRow(QLabel_Programming_Error_Offset, self.QLineEdit_Programming_Error_Offset)
        programming_error_layout.addRow(QLabel_Readback_Error_Gain, self.QLineEdit_Readback_Error_Gain)
        programming_error_layout.addRow(QLabel_Readback_Error_Offset, self.QLineEdit_Readback_Error_Offset)

        self.load_error_widget = QGroupBox()
        load_error_layout = QFormLayout(self.load_error_widget)
        load_error_layout.addRow(QLabel_Load_Programming_Error_Gain, self.QLineEdit_Load_Programming_Error_Gain)
        load_error_layout.addRow(QLabel_Load_Programming_Error_Offset, self.QLineEdit_Load_Programming_Error_Offset)

        self.power_programming_error_widget = QGroupBox()
        power_programming_error_layout = QFormLayout(self.power_programming_error_widget)
        power_programming_error_layout.addRow(self.QLabel_Power_Programming_Error_Gain, self.QLineEdit_Power_Programming_Error_Gain)
        power_programming_error_layout.addRow(self.QLabel_Power_Programming_Error_Offset, self.QLineEdit_Power_Programming_Error_Offset)
        power_programming_error_layout.addRow(self.QLabel_Power_Readback_Error_Gain, self.QLineEdit_Power_Readback_Error_Gain)
        power_programming_error_layout.addRow(self.QLabel_Power_Readback_Error_Offset, self.QLineEdit_Power_Readback_Error_Offset)

        self.Programming_Response_widget = QGroupBox()
        programming_response_error_layout = QFormLayout(self.Programming_Response_widget)
        programming_response_error_layout.addRow( QLabel_Programming_Response_Up_NoLoad, self.QLineEdit_Programming_Response_Up_NoLoad)
        programming_response_error_layout.addRow( QLabel_Programming_Response_Up_FullLoad, self.QLineEdit_Programming_Response_Up_FullLoad)
        programming_response_error_layout.addRow(QLabel_Programming_Response_Down_NoLoad, self.QLineEdit_Programming_Response_Down_NoLoad)
        programming_response_error_layout.addRow( QLabel_Programming_Response_Down_FullLoad, self.QLineEdit_Programming_Response_Down_FullLoad)

        self.OVP_error_widget = QGroupBox()
        OVP_error_layout = QFormLayout(self.OVP_error_widget)
        OVP_error_layout.addRow(QLabel_OVP_Error_Gain, self.QLineEdit_OVP_Error_Gain)
        OVP_error_layout.addRow(QLabel_OVP_Error_Offset, self.QLineEdit_OVP_Error_Offset)
   
        #Oscilloscope Settings
        self.oscilloscope_settings_widget = QGroupBox()
        self.oscilloscope_form = QFormLayout(self.oscilloscope_settings_widget)
        self.oscilloscope_form.addRow(OscilloscopeSetting)
        self.oscilloscope_form.addRow(QLabel_OSC_Display_Channel, self.QLineEdit_OSC_Display_Channel)
        self.oscilloscope_form.addRow(QLabel_V_Settling_Band, self.QLineEdit_V_Settling_Band)
        self.oscilloscope_form.addRow(QLabel_T_Settling_Band, self.QLineEdit_T_Settling_Band)
        self.oscilloscope_form.addRow(QLabel_Probe_Setting, self.QComboBox_Probe_Setting)
        self.oscilloscope_form.addRow(QLabel_Acq_Type, self.QComboBox_Acq_Type)
        self.oscilloscope_form.addRow(QLabel_Channel_CouplingMode, self.QComboBox_Channel_CouplingMode)
        self.oscilloscope_form.addRow(QLabel_Trigger_CouplingMode, self.QComboBox_Trigger_CouplingMode)
        self.oscilloscope_form.addRow(QLabel_Trigger_Mode, self.QComboBox_Trigger_Mode)
        self.oscilloscope_form.addRow(QLabel_Trigger_SweepMode, self.QComboBox_Trigger_SweepMode)
        self.oscilloscope_form.addRow(QLabel_Trigger_SlopeMode, self.QComboBox_Trigger_SlopeMode)
        self.oscilloscope_form.addRow(QLabel_TimeScale, self.QLineEdit_TimeScale)
        self.oscilloscope_form.addRow(QLabel_VerticalScale, self.QLineEdit_VerticalScale)

        #Transient Recovery Test conditions
        self.performtest_widget = QGroupBox()
        self.performtest_layout = QFormLayout(self.performtest_widget)
        self.performtest_layout.addRow(self.QCheckBox_SpecialCase_Widget)
        self.performtest_layout.addRow(self.QCheckBox_NormalCase_Widget)

        #Collection and Delay
        self.collection_group = QGroupBox()
        self.collection_group_layout = QFormLayout(self.collection_group)
        self.collection_group_layout.addRow(QLabel_noofloop, self.QComboBox_noofloop)
        self.collection_group_layout.addRow(QLabel_updatedelay, self.QComboBox_updatedelay)

        #Execute Layout + Outputbox in Right Container
        Right_container = QVBoxLayout()
        exec_layout_box = QHBoxLayout()
        exec_layout = QFormLayout()

        #exec_layout.addRow(Desp0)
        exec_layout.addWidget(self.OutputBox)
        exec_layout.addRow(self.QPushButton_Widget0)

        exec_layout.addRow(QPushButton_Widget3)
        exec_layout.addRow(QPushButton_Widget2)
        exec_layout.addRow(self.QPushButton_Widget1)  
        exec_layout.addRow(self.abort_button) 

        exec_layout_box.addLayout(exec_layout)
 
        Right_container.addLayout(save_path_layout)
        Right_container.addLayout(exec_layout_box)

        #Setting Form Layout with Left Container
        top_widget = QWidget()
        top_layout_left = QVBoxLayout()  # Using QVBoxLayout for stacking the left items vertically
        top_layout_left.addLayout(Voltage_Current_Selection_Layout)
        top_layout_left.addWidget(self.image_label)

        top_layout_right = QVBoxLayout()  # Using QVBoxLayout for stacking the right items vertically
        top_layout_right.addWidget(self.Voltage_Test_group )
        top_layout_right.addWidget(self.Current_Test_group )

        Left_container = QVBoxLayout()
        
        #Configuration Layout Setting (Put every groupbox inside left main layout)
        setting_widget = QWidget()
        setting_layout = QFormLayout(setting_widget)
        setting_layout.addRow(Desp1)
        setting_layout.addRow(self.Connection_group)
        setting_layout.addRow(Desp2)
        setting_layout.addRow(self.General_group)
        setting_layout.addRow(Desp3)
        setting_layout.addRow(self.programming_error_widget)
        setting_layout.addRow(self.load_error_widget)
        setting_layout.addRow(self.Programming_Response_widget)
        setting_layout.addRow(self.power_programming_error_widget)
        setting_layout.addRow(self.OVP_error_widget)
        setting_layout.addRow(self.Ratings_Widget)
        setting_layout.addRow(self.oscilloscope_settings_widget)
        setting_layout.addRow(self.performtest_widget)
        setting_layout.addRow(Desp7)
        setting_layout.addRow(self.collection_group)

        top_combined = QHBoxLayout()
        top_combined.addLayout(top_layout_left)
        top_combined.addLayout(top_layout_right)
        top_widget.setLayout(top_combined)
        top_combined.setStretchFactor(top_layout_left, 2) 
        top_combined.setStretchFactor(top_layout_right, 1) 

        scroll_area = QScrollArea()
        scroll_area.setWidget(setting_widget)  # Set the widget inside scroll area
        scroll_area.setWidgetResizable(True)  # Allow resizing

        Left_container.addWidget(top_widget, stretch =1)
        Left_container.addWidget(scroll_area, stretch =3)

        #Main Layout
        Main_Layout = QHBoxLayout()
        Main_Layout.addWidget(self.progress_label)
        Main_Layout.addWidget(self.progress_bar)
        Main_Layout.addLayout(Left_container,stretch= 2)
        Main_Layout.addLayout(Right_container,stretch = 1)
        self.setLayout(Main_Layout)

        #Action when values changed-------------------------------------------------------------------------------------------------------
        self.QPushButton_Voltage_Widget.clicked.connect(self.select_button)
        self.QPushButton_Current_Widget.clicked.connect(self.select_button)

        #Oscilloscope
        self.QLineEdit_V_Settling_Band.textEdited.connect(self.V_Settling_Band_changed)
        self.QLineEdit_T_Settling_Band.textEdited.connect(self.T_Settling_Band_changed)
        self.QLineEdit_OSC_Display_Channel.textEdited.connect(self.OSC_Channel_changed)
        self.QComboBox_Channel_CouplingMode.currentTextChanged.connect(self.Channel_CouplingMode_changed )
        self.QComboBox_Trigger_CouplingMode.currentTextChanged.connect(
            self.Trigger_CouplingMode_changed
        )
        self.QComboBox_Trigger_Mode.currentTextChanged.connect(self.Trigger_Mode_changed)
        self.QComboBox_Trigger_SweepMode.currentTextChanged.connect(
            self.Trigger_SweepMode_changed
        )
        self.QComboBox_Trigger_SlopeMode.currentTextChanged.connect(
            self.Trigger_SlopeMode_changed
        )
        self.QComboBox_Probe_Setting.currentTextChanged.connect(
            self.Probe_Setting_changed
        )
        self.QComboBox_Acq_Type.currentTextChanged.connect(
            self.Acq_Type_changed
        )
        self.QLineEdit_TimeScale.textEdited.connect(self.TimeScale_changed)
        self.QLineEdit_VerticalScale.textEdited.connect(self.VerticalScale_changed)

        #Visa Address / DUT changed
        self.QComboBox_DUT.currentTextChanged.connect(self.DUT_changed)
        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_DMM_VisaAddressforVoltage.currentTextChanged.connect(self.DMM_VisaAddressforVoltage_changed)
        self.QLineEdit_DMM_VisaAddressforCurrent.currentTextChanged.connect(self.DMM_VisaAddressforCurrent_changed)
        self.QLineEdit_OSC_VisaAddress.currentTextChanged.connect(self.OSC_VisaAddress_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)
        self.QComboBox_DMM_Instrument.currentTextChanged.connect(self.DMM_Instrument_changed)
        self.QComboBox_DUT.currentIndexChanged.connect(self.on_current_index_changed)
        self.QComboBox_AC_Supply_Type.currentTextChanged.connect(self.AC_Supply_Type_changed)

        #Gain changed
        self.QLineEdit_Programming_Error_Gain.textEdited.connect(self.Programming_Error_Gain_changed)
        self.QLineEdit_Programming_Error_Offset.textEdited.connect(self.Programming_Error_Offset_changed)
        self.QLineEdit_Readback_Error_Gain.textEdited.connect(self.Readback_Error_Gain_changed)
        self.QLineEdit_Readback_Error_Offset.textEdited.connect(self.Readback_Error_Offset_changed)
        self.QLineEdit_Load_Programming_Error_Gain.textEdited.connect(self.Load_Programming_Error_Gain_changed)
        self.QLineEdit_Load_Programming_Error_Offset.textEdited.connect(self.Load_Programming_Error_Offset_changed)
        self.QLineEdit_Power_Programming_Error_Gain.textEdited.connect(self.Power_Programming_Error_Gain_changed)
        self.QLineEdit_Power_Programming_Error_Offset.textEdited.connect(self.Power_Programming_Error_Offset_changed)
        self.QLineEdit_Power_Readback_Error_Gain.textEdited.connect(self.Power_Readback_Error_Gain_changed)
        self.QLineEdit_Power_Readback_Error_Offset.textEdited.connect(self.Power_Readback_Error_Offset_changed)
        self.QLineEdit_Programming_Response_Up_NoLoad.textEdited.connect(self.Programming_Response_Up_NoLoad_changed)
        self.QLineEdit_Programming_Response_Up_FullLoad.textEdited.connect(self.Programming_Response_Up_FullLoad_changed)
        self.QLineEdit_Programming_Response_Down_NoLoad.textEdited.connect(self.Programming_Response_Down_NoLoad_changed)
        self.QLineEdit_Programming_Response_Down_FullLoad.textEdited.connect(self.Programming_Response_Down_FullLoad_changed)

        #Oscilloscope Settings
        
        #Voltage/Current/Power changed
        self.QLineEdit_current_rated.textEdited.connect(self.Current_Rating_changed)
        self.QLineEdit_voltage_rated.textEdited.connect(self.Voltage_Rating_changed)
        self.QLineEdit_minVoltage.textEdited.connect(self.minVoltage_changed)
        self.QLineEdit_maxVoltage.textEdited.connect(self.maxVoltage_changed)
        self.QLineEdit_minCurrent.textEdited.connect(self.minCurrent_changed)
        self.QLineEdit_maxCurrent.textEdited.connect(self.maxCurrent_changed)
        self.QLineEdit_voltage_stepsize.textEdited.connect(self.voltage_step_size_changed)
        self.QLineEdit_current_stepsize.textEdited.connect(self.current_step_size_changed)
        
        #Power changed
        self.QLineEdit_Power.textEdited.connect(self.Power_changed)
        self.QLineEdit_power_rated.textEdited.connect(self.Power_Rating_changed)
        self.QLineEdit_power_step_size.textEdited.connect(self.power_step_size_changed)
        self.QLineEdit_PowerINI.textEdited.connect(self.PowerINI_changed)
        self.QLineEdit_rshunt.textEdited.connect(self.rshunt_changed)

        #DUT channel/ Function changed
        self.QComboBox_set_PSU_Channel.currentTextChanged.connect(self.set_PSU_Channel_changed)
        self.QComboBox_set_ELoad_Channel.currentTextChanged.connect(self.ELoad_Channel_changed)
        self.QComboBox_set_Function.currentTextChanged.connect(self.set_Function_changed)
        self.QComboBox_Voltage_Res.currentTextChanged.connect(self.set_VoltageRes_changed)
        self.QComboBox_Voltage_Sense.currentTextChanged.connect(self.set_VoltageSense_changed)

        self.QLineEdit_OVP_Level.textEdited.connect(self.OVP_Level_changed)
        self.QLineEdit_OCP_Level.textEdited.connect(self.OCP_Level_changed)
        self.QLineEdit_OCP_ActivationTime_Error.textEdited.connect(self.OCP_Activation_Time_changed)
        self.QComboBox_SPOperationMode.currentTextChanged.connect(self.SPOperationMode_changed)

        self.QComboBox_Line_Reg_Range.currentTextChanged.connect(self.Line_Reg_Range_changed)

        #No of collection / Checkbox changed
        self.QComboBox_noofloop.currentTextChanged.connect(self.noofloop_changed)
        self.QComboBox_updatedelay.currentTextChanged.connect(self.updatedelay_changed)
        self.QCheckBox_SpecialCase_Widget.stateChanged.connect(self.checkbox_state_SpecialCase)
        self.QCheckBox_NormalCase_Widget.stateChanged.connect(self.checkbox_state_NormalCase)
        self.QCheckBox_Report_Widget.stateChanged.connect(self.checkbox_state_Report)
        QCheckBox_Lock_Widget.stateChanged.connect(self.checkbox_state_lock)
        self.QCheckBox_Image_Widget.stateChanged.connect(self.checkbox_state_Image)
        self.QCheckBox_VoltageAccuracy_Widget.stateChanged.connect(self.checkbox_state_VoltageAccuracy)
        self.QCheckBox_VoltageLoadRegulation_Widget.stateChanged.connect(self.checkbox_state_VoltageLoadRegulation)
        self.QCheckBox_TransientRecovery_Widget.stateChanged.connect(self.checkbox_state_TransientRecovery)
        self.QCheckBox_CurrentAccuracy_Widget.stateChanged.connect(self.checkbox_state_CurrentAccuracy)
        self.QCheckBox_CurrentLoadRegulation_Widget.stateChanged.connect(self.checkbox_state_CurrentLoadRegulation)
        self.QCheckBox_PowerAccuracy_Widget.stateChanged.connect(self.checkbox_state_PowerAccuracy)
        self.QCheckBox_OVP_Test_Widget.stateChanged.connect(self.checkbox_state_OVP_Test)
        self.QCheckBox_CurrentLineRegulation_Widget.stateChanged.connect(self.checkbox_state_VoltageLine)
        self.QCheckBox_VoltageLineRegulation_Widget.stateChanged.connect(self.checkbox_state_CurrentLine)
        self.QCheckBox_ProgrammingSpeed_Widget.stateChanged.connect(self.checkbox_state_ProgrammingSpeed_Test)

        #Push Button Action
        self.QPushButton_Widget0.clicked.connect(self.savepath)
        self.QPushButton_Widget1.clicked.connect(self.executeTest)
        QPushButton_Widget2.clicked.connect(self.openDialog)
        QPushButton_Widget3.clicked.connect(self.estimateTime)
        QPushButton_Widget4.clicked.connect(self.doFind)

        #Voltage/Current Test Selection with Enable/Disable Input Fields
        self.select_button()
        self.InteractiveAction()
        self.Image_Label_Setup()
 
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
 
        self.QLineEdit_Programming_Error_Gain.setText(self.params.Programming_Error_Gain)
        self.QLineEdit_Programming_Error_Gain.setText(self.params.Programming_Error_Gain)
        self.QLineEdit_Programming_Error_Offset.setText(self.params.Programming_Error_Offset)
        self.QLineEdit_Readback_Error_Gain.setText(self.params.Readback_Error_Gain)
        self.QLineEdit_Readback_Error_Offset.setText(self.params.Readback_Error_Offset)
        self.QLineEdit_Load_Programming_Error_Gain.setText(self.params.Load_Programming_Error_Gain)
        self.QLineEdit_Load_Programming_Error_Offset.setText(self.params.Load_Programming_Error_Offset)
        self.QLineEdit_Power.setText(self.params.Power)
        self.QLineEdit_minVoltage.setText(self.params.minVoltage)
        self.QLineEdit_maxVoltage.setText(self.params.maxVoltage)
        self.QLineEdit_voltage_stepsize.setText(self.params.voltage_step_size)
        self.QLineEdit_minCurrent.setText(self.params.minCurrent)
        self.QLineEdit_maxCurrent.setText(self.params.maxCurrent)
        self.QLineEdit_current_stepsize.setText(self.params.current_step_size)
        self.QLineEdit_current_rated.setText(self.params.Current_Rating)
        self.QLineEdit_voltage_rated.setText(self.params.Voltage_Rating)
        self.QLineEdit_power_rated.setText(self.params.Power_Rating)
        self.QLineEdit_power_step_size.setText(self.params.power_step_size)
        self.QLineEdit_PowerINI.setText(self.params.powerini)
        self.QLineEdit_rshunt.setText(self.params.rshunt)
        self.QLineEdit_OVP_Level.setText(self.params.OVP_Level)

        self.QLineEdit_Power_Programming_Error_Gain.setText(self.params.Power_Programming_Error_Gain)
        self.QLineEdit_Power_Programming_Error_Offset.setText(self.params.Power_Programming_Error_Offset)
        self.QLineEdit_Power_Readback_Error_Gain.setText(self.params.Power_Readback_Error_Gain)
        self.QLineEdit_Power_Readback_Error_Offset.setText(self.params.Power_Readback_Error_Offset)

        #Oscilloscope
        self.QLineEdit_OSC_Display_Channel.setText(self.params.OSC_Channel)
        self.QLineEdit_V_Settling_Band.setText(self.params.V_Settling_Band)
        self.QLineEdit_T_Settling_Band.setText(self.params.T_Settling_Band)
        self.QComboBox_Probe_Setting.setCurrentText(self.params.Probe_Setting)
        self.QComboBox_Acq_Type.setCurrentText(self.params.Acq_Type)
        self.QComboBox_Channel_CouplingMode.setCurrentText(self.params.Channel_CouplingMode)
        self.QComboBox_Trigger_Mode.setCurrentText(self.params.Trigger_Mode)
        self.QComboBox_Trigger_CouplingMode.setCurrentText(self.params.Trigger_CouplingMode)
        self.QComboBox_Trigger_SweepMode.setCurrentText(self.params.Trigger_SweepMode)
        self.QComboBox_Trigger_SlopeMode.setCurrentText(self.params.Trigger_SlopeMode)
        self.QLineEdit_TimeScale.setText(self.params.TimeScale)
        self.QLineEdit_VerticalScale.setText(self.params.VerticalScale)
        self.QComboBox_updatedelay.setCurrentText(self.params.updatedelay)
        
        self.QComboBox_set_PSU_Channel.setCurrentIndex(int(self.params.PSU_Channel)-1)
        self.QComboBox_set_ELoad_Channel.setCurrentIndex(int(self.params.ELoad_Channel)-1)
        self.QComboBox_SPOperationMode.setCurrentText(self.params.SPOperationMode)
        self.QComboBox_Voltage_Sense.setCurrentText("4 Wire" if self.params.VoltageSense == "EXT" else "2 Wire")
        self.QComboBox_noofloop.setCurrentText(self.params.noofloop)
        self.QComboBox_updatedelay.setCurrentText(self.params.updatedelay)

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

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_DMM_VisaAddressforVoltage.clear()
            self.QLineEdit_DMM_VisaAddressforCurrent.clear()
            self.QLineEdit_OSC_VisaAddress.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()

            self.visaIdList, self.nameList, instrument_roles = NewGetVisaSCPIResources()

            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_OSC_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddressforVoltage.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddressforCurrent.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])

            if 'PSU' in instrument_roles:
                psu_index = self.visaIdList.index(instrument_roles['PSU'])
                self.QLineEdit_PSU_VisaAddress.setCurrentIndex(psu_index)

            if 'ELOAD' in instrument_roles:
                eload_index = self.visaIdList.index(instrument_roles['ELOAD'])
                self.QLineEdit_ELoad_VisaAddress.setCurrentIndex(eload_index)

            if 'DMM' in instrument_roles:
                dmm_index = self.visaIdList.index(instrument_roles['DMM'])
                self.QLineEdit_DMM_VisaAddressforVoltage.setCurrentIndex(dmm_index)

            if 'DMM2' in instrument_roles:
                dmm2_index = self.visaIdList.index(instrument_roles['DMM2'])
                self.QLineEdit_DMM_VisaAddressforCurrent.setCurrentIndex(dmm2_index)

            if 'SCOPE' in instrument_roles:
                osc_index = self.visaIdList.index(instrument_roles['SCOPE'])
                self.QLineEdit_OSC_VisaAddress.setCurrentIndex(osc_index)
            
            if 'ACSource' in instrument_roles:
                AC_index = self.visaIdList.index(instrument_roles['ACSource'])
                self.QComboBox_AC_Supply_Type.setCurrentIndex(1)
           
        except:
            self.OutputBox.append("No Devices Found!!!")
        return   

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

    def OSC_Channel_changed(self, s):
        self.params.OSC_Channel = s

    def DUT_changed(self, s):
        self.params.DUT = s
        self.doFind()

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

    def OVP_Level_changed(self, s):
        self.params.OVP_Level = s
        self.OutputBox.setPlainText("OVP Level Set to: " + str(self.params.OVP_Level))
    
    def OCP_Level_changed(self, s):
        self.OCP_Level = s
        self.params.OutputBox.setPlainText("OCP Level Set to: " + str(self.params.OCP_Level))
    
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

        if self.params.AC_Supply_Type == "AC Source":
            dialogAC = ACSourceSetting(self.params)
            dialogAC.exec()
        else:
            pass
    
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

    def checkbox_state_VoltageLine (self):
        self.InteractiveAction()
        self.Image_Label_Setup()

    def checkbox_state_CurrentLine (self):
        self.InteractiveAction()
        self.Image_Label_Setup()

    def checkbox_state_ProgrammingSpeed_Test(self, s):
        self.checkbox_test_OVP_Test = s
        self.InteractiveAction()

    def openDialog(self):
        dlg = AdvancedSettings(self.params)
        dlg.exec()

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
                scaled_pixmap = self.pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio)

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
        
        #Check Voltage or Current Measurement
        if self.QPushButton_Current_Widget.isChecked():
           
            self.QComboBox_set_Function.setCurrentText("Voltage Priority")
            self.set_Function_changed("Voltage Priority")
            self.params.unit = "CURRENT"

            self.Voltage_Test_group.setVisible(False)
            self.Current_Test_group.setVisible(True)

            self.QLabel_DMM_VisaAddressforCurrent.setVisible(True)
            self.QLineEdit_DMM_VisaAddressforCurrent.setVisible(True)
            self.QLineEdit_rshunt.setEnabled(True)

        elif self.QPushButton_Voltage_Widget.isChecked():
            
            self.QComboBox_set_Function.setCurrentText("Current Priority")
            self.set_Function_changed("Current Priority")
            self.params.unit = "VOLTAGE"

            self.Voltage_Test_group.setVisible(True)
            self.Current_Test_group.setVisible(False)

            self.QLabel_DMM_VisaAddressforCurrent.setVisible(False)
            self.QLineEdit_DMM_VisaAddressforCurrent.setVisible(False)
            self.QLineEdit_rshunt.setEnabled(False)
        else:
            pass

        #Voltage/Current Accuracy Test Selected
        if not self.QCheckBox_CurrentAccuracy_Widget.isChecked() and \
            not self.QCheckBox_VoltageAccuracy_Widget.isChecked():
            self.programming_error_widget.setVisible(False)
        else:
            self.programming_error_widget.setVisible(True)

        #OVP Test Selected
        if not self.QCheckBox_OVP_Test_Widget.isChecked():
            self.QLineEdit_OVP_Level.setEnabled(False)
            self.OVP_error_widget.setVisible(False)
        else:
            self.QLineEdit_OVP_Level.setEnabled(True)
            self.OVP_error_widget.setVisible(True)

        #OCP Test Selected
        if not self.QCheckBox_OCP_Test_Widget.isChecked():
            self.QLineEdit_OCP_Level.setEnabled(False)
        else:
            self.QLineEdit_OCP_Level.setEnabled(True)
            self.oscilloscope_settings_widget.setVisible(True)

        #Power Accuracy Test Selected
        if self.QCheckBox_PowerAccuracy_Widget.isChecked():
            self.QComboBox_set_Function.setEnabled(True)
            self.power_programming_error_widget.setVisible(True)
            self.power_setting_widget.setVisible(True)
        else:
            self.QComboBox_set_Function.setEnabled(False)
            self.power_programming_error_widget.setVisible(False)
            self.power_setting_widget.setVisible(False)

        #Load Regulation Test Selected
        if not self.QCheckBox_VoltageLoadRegulation_Widget.isChecked() and \
            not self.QCheckBox_CurrentLoadRegulation_Widget.isChecked() and \
            not self.QCheckBox_VoltageLineRegulation_Widget.isChecked() and \
            not self.QCheckBox_CurrentLineRegulation_Widget.isChecked():
            self.load_error_widget.setVisible(False)
        else:
            self.load_error_widget.setVisible(True)

        #Transient Test Selected
        if not self.QCheckBox_TransientRecovery_Widget.isChecked():
            self.QLabel_OSC_VisaAddress.setVisible(False)
            self.QLineEdit_OSC_VisaAddress.setVisible(False)
        else:
            self.QLabel_OSC_VisaAddress.setVisible(True)
            self.QLineEdit_OSC_VisaAddress.setVisible(True)
            self.oscilloscope_settings_widget.setVisible(True)

        #Programming Speed Test Selected
        if not self.QCheckBox_ProgrammingSpeed_Widget.isChecked():
            self.QLabel_OSC_VisaAddress.setVisible(False)
            self.QLineEdit_OSC_VisaAddress.setVisible(False)
            self.Programming_Response_widget.setVisible(False)
        else:
            self.QLabel_OSC_VisaAddress.setVisible(True)
            self.QLineEdit_OSC_VisaAddress.setVisible(True)
            self.oscilloscope_settings_widget.setVisible(True)
            self.Programming_Response_widget.setVisible(True)
        
        #Check Directory Change
        if str(self.params.savelocation) != "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
            self.QPushButton_Widget0.setStyleSheet("color: darkgreen")
            self.QPushButton_Widget0.setText("Save Path Selected ✅")
        elif str(self.params.savelocation) == "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
            self.QPushButton_Widget0.setStyleSheet("color: orange")
        else:
            self.QPushButton_Widget0.setStyleSheet("color: red")
    
    def estimateTime(self):
        try:
            self.params.currloop = ((float(self.params.maxCurrent) - float(self.params.minCurrent))/ float(self.params.current_step_size)) + 1
            self.params.voltloop = ((float(self.params.maxVoltage) - float(self.params.minVoltage))/ float(self.params.voltage_step_size)) + 1

            if self.params.updatedelay == 0.0:
                constant = 0
            else:
                constant = 1

            self.params.estimatetime = (self.params.currloop * self.params.voltloop *(0.2 + 0.8 + (float(self.params.updatedelay) * constant) )) * float(self.params.noofloop)
            self.OutputBox.append(f"{self.params.estimatetime} seconds")
            self.OutputBox.append("") 
        except Exception as e:
            QMessageBox.warning(self, "Warning", "Input cannot be empty!")
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
    
    def pre_test_check(self, dict):

        self.checkbox_states = {
            "Voltage_Test": self.QPushButton_Voltage_Widget.isChecked(),
            "Current_Test": self.QPushButton_Current_Widget.isChecked(),
            "SpecialCase": self.QCheckBox_SpecialCase_Widget.isChecked(),
            "NormalCase": self.QCheckBox_NormalCase_Widget.isChecked(),
            "DataReport": self.QCheckBox_Report_Widget.isChecked(),
            "DataImage": self.QCheckBox_Image_Widget.isChecked(),
            "TransientRecovery": self.QCheckBox_TransientRecovery_Widget.isChecked(),
            "VoltageAccuracy": self.QCheckBox_VoltageAccuracy_Widget.isChecked(),
            "VoltageLoadRegulation": self.QCheckBox_VoltageLoadRegulation_Widget.isChecked(),
            "CurrentAccuracy": self.QCheckBox_CurrentAccuracy_Widget.isChecked(),
            "CurrentLoadRegulation": self.QCheckBox_CurrentLoadRegulation_Widget.isChecked(),
            "PowerAccuracy": self.QCheckBox_PowerAccuracy_Widget.isChecked(),
            "OVP_Test": self.QCheckBox_OVP_Test_Widget.isChecked(),
            "VoltageLineRegulation": self.QCheckBox_VoltageLineRegulation_Widget.isChecked(),
            "CurrentLineRegulation": self.QCheckBox_CurrentLineRegulation_Widget.isChecked(),
            "ProgrammingSpeed": self.QCheckBox_ProgrammingSpeed_Widget.isChecked(),
            "OCP_Test": self.QCheckBox_OCP_Test_Widget.isChecked(),
        }

        #Function: Check if any test was selected
        if not any(self.checkbox_states.values()):
            self.OutputBox.append("Please select the required tests before proceeding.")
            QMessageBox.warning(
                self,
                "Test is not selected !!!",
                "Please select the required tests before proceeding."
            )
            return False

        #Function: Check if any of the parameters are empty
        if not self.check_missing_params(dict):
            return False
        
        #Function: Visa Address Check & Run Test
        A = VisaResourceManager()
        flag, args = A.openRM(self.params.ELoad, self.params.PSU, self.params.DMM, self.params.DMM2)
        if flag == 0:
            string = ""
            for item in args:
                string = string + item

            QMessageBox.warning(self, "VISA IO ERROR", string)
            return False

        return True
    
    def executeTest(self):
        global globalvv
        try:
            for x in range (int(self.params.noofloop)):

                """The method begins by compiling all the parameters in a dictionary for ease of storage and calling,
                then the parameters are looped through to check if any of them are empty or return NULL, a warning dialogue
                will appear if the statement is true, and the users have to troubleshoot the issue. After so, the tests will
                begin right after another warning dialogue prompting the user that the tests will begin very soon. When test
                begins, the VISA_Addresses of the Instruments are passed through the VISA Resource Manager to make sure there
                are connected. Then the actual DUT Tests will commence. Depending on the users selection, the method can
                optionally export all the details into a CSV file or display a graph after the test is completed.

                """
            self.setEnabled(False)
            self.OutputBox.clear()

            #Default parameters to be check before test start
            params = {
                "savedir":self.params.savelocation,
                "V_Rating":self.params.Voltage_Rating,
                "I_Rating":self.params.Current_Rating,
                "P_Rating":self.params.Power_Rating,
                "power":self.params.Power,
                "estimatetime":self.params.estimatetime,
                "updatedelay":self.params.updatedelay,
                "readbackvoltage":self.params.readbackvoltage,
                "readbackcurrent":self.params.readbackcurrent,
                "noofloop":self.params.noofloop,
                "Instrument":self.params.DMM_Instrument,
                "Programming_Error_Gain":self.params.Programming_Error_Gain,
                "Programming_Error_Offset":self.params.Programming_Error_Offset,
                "Readback_Error_Gain":self.params.Readback_Error_Gain,
                "Readback_Error_Offset":self.params.Readback_Error_Offset,

                "unit":self.params.unit,
                "minCurrent":self.params.minCurrent,
                "maxCurrent":self.params.maxCurrent,
                "current_step_size":self.params.current_step_size,
                "minVoltage":self.params.minVoltage,
                "maxVoltage":self.params.maxVoltage,
                "voltage_step_size":self.params.voltage_step_size,

                "selected_DUT": self.params.selected_text,
                "PSU":self.params.PSU,
                "DMM":self.params.DMM,
                "ELoad":self.params.ELoad,
                "ELoad_Channel":self.params.ELoad_Channel,
                "PSU_Channel":self.params.PSU_Channel,
                "VoltageSense":self.params.VoltageSense,
                "VoltageRes":self.params.VoltageRes,
                "setFunction":self.params.setFunction,
                "OperationMode":self.params.SPOperationMode,

                "Range":self.params.Range,
                "Aperture":self.params.Aperture,
                "AutoZero":self.params.AutoZero,
                "InputZ":self.params.inputZ,
                "UpTime":self.params.UpTime,
                "DownTime":self.params.DownTime,
            }

            #Parameters to be check if specific test was selected
            checkbox_param_list = [
                # Add more checkboxes as needed
                (self.QPushButton_Current_Widget, "rshunt", self.params.rshunt),
                (self.QPushButton_Current_Widget, "DMM2", self.params.DMM2),
                (self.QPushButton_Current_Widget, "powerfin", self.params.Power),

                (self.QCheckBox_OCP_Test_Widget, "OCP_Level", self.params.OCP_Level),
                (self.QCheckBox_OCP_Test_Widget, "OCPActivationTime", self.params.OCPActivationTime),

                (self.QCheckBox_OVP_Test_Widget, "OVP_Level", self.params.OVP_Level),
                (self.QCheckBox_OVP_Test_Widget, "OVP_ErrorGain", self.params.OVP_ErrorGain),
                (self.QCheckBox_OVP_Test_Widget, "OVP_ErrorOffset", self.params.OVP_ErrorOffset),

                (self.QCheckBox_TransientRecovery_Widget, "OSC_Channel", self.params.OSC_Channel),
                (self.QCheckBox_TransientRecovery_Widget, "Channel_CouplingMode", self.params.Channel_CouplingMode),
                (self.QCheckBox_TransientRecovery_Widget, "Trigger_Mode", self.params.Trigger_Mode),
                (self.QCheckBox_TransientRecovery_Widget, "Trigger_CouplingMode", self.params.Trigger_CouplingMode),
                (self.QCheckBox_TransientRecovery_Widget, "Trigger_SweepMode", self.params.Trigger_SweepMode),
                (self.QCheckBox_TransientRecovery_Widget, "Trigger_SlopeMode", self.params.Trigger_SlopeMode),
                (self.QCheckBox_TransientRecovery_Widget, "Probe_Setting", self.params.Probe_Setting),
                (self.QCheckBox_TransientRecovery_Widget, "Acq_Type", self.params.Acq_Type),
                (self.QCheckBox_TransientRecovery_Widget, "TimeScale", self.params.TimeScale),
                (self.QCheckBox_TransientRecovery_Widget, "VerticalScale", self.params.VerticalScale),
                (self.QCheckBox_TransientRecovery_Widget, "DUT_V_Settling_Band", self.params.V_Settling_Band),
                (self.QCheckBox_TransientRecovery_Widget, "DUT_T_Settling_Band", self.params.T_Settling_Band),
                (self.QCheckBox_TransientRecovery_Widget, "OSC", self.params.OSC),
                (self.QCheckBox_TransientRecovery_Widget, "CurrentTrigger_Probe_Setting", 100),
                (self.QCheckBox_TransientRecovery_Widget, "CurrentTrigger_OSC_Channel", 2),
                (self.QCheckBox_TransientRecovery_Widget, "CurrentTrigger_V_Settling_Band", 6),

                (self.QCheckBox_ProgrammingSpeed_Widget, "OSC_Channel", self.params.OSC_Channel),
                (self.QCheckBox_ProgrammingSpeed_Widget, "Channel_CouplingMode", self.params.Channel_CouplingMode),
                (self.QCheckBox_ProgrammingSpeed_Widget, "Trigger_Mode", self.params.Trigger_Mode),
                (self.QCheckBox_ProgrammingSpeed_Widget, "Trigger_CouplingMode", self.params.Trigger_CouplingMode),
                (self.QCheckBox_ProgrammingSpeed_Widget, "Trigger_SweepMode", self.params.Trigger_SweepMode),
                (self.QCheckBox_ProgrammingSpeed_Widget, "Trigger_SlopeMode", self.params.Trigger_SlopeMode),
                (self.QCheckBox_ProgrammingSpeed_Widget, "Probe_Setting", self.params.Probe_Setting),
                (self.QCheckBox_ProgrammingSpeed_Widget, "Acq_Type", self.params.Acq_Type),
                (self.QCheckBox_ProgrammingSpeed_Widget, "TimeScale", self.params.TimeScale),
                (self.QCheckBox_ProgrammingSpeed_Widget, "VerticalScale", self.params.VerticalScale),
                (self.QCheckBox_ProgrammingSpeed_Widget, "V_Settling_Band", self.params.V_Settling_Band),
                (self.QCheckBox_ProgrammingSpeed_Widget, "T_Settling_Band", self.params.T_Settling_Band),
                (self.QCheckBox_ProgrammingSpeed_Widget, "OSC", self.params.OSC),

                (self.QCheckBox_OCP_Test_Widget, "OSC_Channel", self.params.OSC_Channel),
                (self.QCheckBox_OCP_Test_Widget, "Channel_CouplingMode", self.params.Channel_CouplingMode),
                (self.QCheckBox_OCP_Test_Widget, "Trigger_Mode", self.params.Trigger_Mode),
                (self.QCheckBox_OCP_Test_Widget, "Trigger_CouplingMode", self.params.Trigger_CouplingMode),
                (self.QCheckBox_OCP_Test_Widget, "Trigger_SweepMode", self.params.Trigger_SweepMode),
                (self.QCheckBox_OCP_Test_Widget, "Trigger_SlopeMode", self.params.Trigger_SlopeMode),
                (self.QCheckBox_OCP_Test_Widget, "Probe_Setting", self.params.Probe_Setting),
                (self.QCheckBox_OCP_Test_Widget, "Acq_Type", self.params.Acq_Type),
                (self.QCheckBox_OCP_Test_Widget, "TimeScale", self.params.TimeScale),
                (self.QCheckBox_OCP_Test_Widget, "VerticalScale", self.params.VerticalScale),
                (self.QCheckBox_OCP_Test_Widget, "V_Settling_Band", self.params.V_Settling_Band),
                (self.QCheckBox_OCP_Test_Widget, "T_Settling_Band", self.params.T_Settling_Band),
                (self.QCheckBox_OCP_Test_Widget, "OSC", self.params.OSC),

                (self.QCheckBox_VoltageLoadRegulation_Widget, "Load_Programming_Error_Gain", self.params.Load_Programming_Error_Gain),
                (self.QCheckBox_VoltageLoadRegulation_Widget, "Load_Programming_Error_Offset", self.params.Load_Programming_Error_Offset),
                (self.QCheckBox_CurrentLoadRegulation_Widget, "Load_Programming_Error_Gain", self.params.Load_Programming_Error_Gain),
                (self.QCheckBox_CurrentLoadRegulation_Widget, "Load_Programming_Error_Offset", self.params.Load_Programming_Error_Offset),
                (self.QCheckBox_VoltageLineRegulation_Widget, "Load_Programming_Error_Gain", self.params.Load_Programming_Error_Gain),
                (self.QCheckBox_VoltageLineRegulation_Widget, "Load_Programming_Error_Offset", self.params.Load_Programming_Error_Offset),
                (self.QCheckBox_CurrentLineRegulation_Widget, "Load_Programming_Error_Gain", self.params.Load_Programming_Error_Gain),
                (self.QCheckBox_CurrentLineRegulation_Widget, "Load_Programming_Error_Offset", self.params.Load_Programming_Error_Offset),

                (self.QCheckBox_PowerAccuracy_Widget, "Power_Programming_Error_Gain", self.params.Power_Programming_Error_Gain),
                (self.QCheckBox_PowerAccuracy_Widget, "Power_Programming_Error_Offset", self.params.Power_Programming_Error_Offset),
                (self.QCheckBox_PowerAccuracy_Widget, "Power_Readback_Error_Gain", self.params.Power_Readback_Error_Gain),
                (self.QCheckBox_PowerAccuracy_Widget, "Power_Readback_Error_Offset", self.params.Power_Readback_Error_Offset),
                (self.QCheckBox_PowerAccuracy_Widget, "powerini", self.params.powerini),
                (self.QCheckBox_PowerAccuracy_Widget, "power_step_size", self.params.power_step_size),

                (self.QCheckBox_VoltageLineRegulation_Widget,"ACSource", self.params.ACSource),
                (self.QCheckBox_VoltageLineRegulation_Widget,"AC_CurrentLimit", self.params.AC_CurrentLimit),
                (self.QCheckBox_VoltageLineRegulation_Widget,"AC_VoltageOutput", self.params.AC_VoltageOutput),
                (self.QCheckBox_VoltageLineRegulation_Widget,"Frequency", self.params.Frequency),
                (self.QCheckBox_VoltageLineRegulation_Widget,"AC_Supply_Type", self.params.AC_Supply_Type),
                (self.QCheckBox_VoltageLineRegulation_Widget,"Line_Reg_Range", self.params.Line_Reg_Range),
                (self.QCheckBox_CurrentLineRegulation_Widget,"ACSource", self.params.ACSource),
                (self.QCheckBox_CurrentLineRegulation_Widget,"AC_CurrentLimit", self.params.AC_CurrentLimit),
                (self.QCheckBox_CurrentLineRegulation_Widget,"AC_VoltageOutput", self.params.AC_VoltageOutput),
                (self.QCheckBox_CurrentLineRegulation_Widget,"Frequency", self.params.Frequency),
                (self.QCheckBox_CurrentLineRegulation_Widget,"AC_Supply_Type", self.params.AC_Supply_Type),
                (self.QCheckBox_CurrentLineRegulation_Widget,"Line_Reg_Range", self.params.Line_Reg_Range),

                (self.QCheckBox_ProgrammingSpeed_Widget,"Response_Up_NoLoad", self.params.Programming_Response_Up_NoLoad),
                (self.QCheckBox_ProgrammingSpeed_Widget,"Response_Up_FullLoad", self.params.Programming_Response_Up_FullLoad),
                (self.QCheckBox_ProgrammingSpeed_Widget,"Response_Down_NoLoad", self.params.Programming_Response_Down_NoLoad),
                (self.QCheckBox_ProgrammingSpeed_Widget,"Response_Down_FullLoad", self.params.Programming_Response_Down_FullLoad),

            ]

            for checkbox, key, value in checkbox_param_list:
                if checkbox.isChecked():
                    params[key] = value

            #Send the parameters to the dictionary in DUT_Test
            dict = dictGenerator.input(**params)
            self.dict_reset = dict

            #Run Qthread after pre-test check
            if self.pre_test_check(dict):
                reply = QMessageBox.question(
                    self,
                    "Test Running",
                    "Test will be started.\nDo you still want to continue?",
                    QMessageBox.Yes | QMessageBox.Cancel,
                    QMessageBox.Cancel  # Default button
                )

                if reply == QMessageBox.Yes:
                    # Show progress elements
                    self.progress_bar.setVisible(True)
                    self.progress_bar.setValue(0)
                    self.progress_label.setVisible(True)
                    self.abort_button.setVisible(True)
                    self.abort_button.setEnabled(True)
                    self.QPushButton_Widget1.setEnabled(False)
                                            
                    # Create and start worker
                    self.worker = None
                    self.was_aborted = False 
                    self.worker = TestWorker(self.checkbox_states, dict, self.params)
                    self.worker.progress.connect(self.update_output)
                    self.worker.progress_value.connect(self.update_progress_bar)
                    self.worker.finished.connect(self.test_finished)
                    self.worker.aborted.connect(self.test_aborted)
                    self.worker.error.connect(lambda e, tb: show_error_dialog(self, e, tb))
                    self.worker.start()
                else:
                    print("Test canceled by user")

        except Exception as e:
            show_error_dialog(self, e)
            return
                    
        finally:
            self.setEnabled(True)

    # Slot to update OutputBox safely
    def update_output(self, msg):
        self.OutputBox.append(msg)
        print(msg)

    def update_progress_bar(self, value):
        """Update the progress bar value"""
        self.progress_bar.setValue(value)

    # MODIFIED - Simplified abort function
    def abort_test(self):
        if self.worker and self.worker.isRunning():
            # Set abort flag
            self.was_aborted = True
            self.worker.was_aborted = True

        reply = QMessageBox.question(
            self,
            'Confirm Abort',
            'Are you sure you want to force stop the current operation?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
            )

        if reply == QMessageBox.Yes:
            self.update_output("Force terminating operation...")
            self.abort_button.setEnabled(False)
            self.abort_button.setText("Terminating...")

            self.worker.terminate()
            self.worker.wait(2000)
            self.test_aborted()


    def test_finished(self):
        """Called when the test finishes (completed or aborted)"""
        # Hide progress elements
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.abort_button.setVisible(False)
        self.abort_button.setText("Abort")
        self.abort_button.setEnabled(False)
        self.QPushButton_Widget1.setEnabled(True)
                 
        self.OutputBox.append("Test finished ✅")
                                                                     
        # Show Graph Image (only if completed successfully and not aborted)
        if not self.was_aborted:
            self.OutputBox.append("Test completed successfully ✅")
            
            # Show Graph Image only if completed successfully
            if self.checkbox_states.get("DataImage", False):
                try:
                    self.image_dialog = image_Window()
                    self.image_dialog.setModal(True)
                    self.image_dialog.show()
                except:
                    pass  # Handle case where image window fails

        # Clean up worker
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
                 
        print("Test operation finished")

    def test_aborted(self):
        """Called when the test is aborted"""
        # Hide progress elements
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.abort_button.setVisible(False)
        self.abort_button.setText("Abort")
        self.abort_button.setEnabled(False)
        self.QPushButton_Widget1.setEnabled(True)
        
        # Show abort message
        self.OutputBox.append("Test operation aborted ❌")

        RESET.ResetInstrument(self,self.dict_reset)

        # Clean up worker
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        
        print("Test operation aborted")

class TestWorker(QThread):
    progress = pyqtSignal(str)
    progress_value = pyqtSignal(int) 
    finished = pyqtSignal()
    error = pyqtSignal(Exception, str)
    aborted = pyqtSignal() 

    def __init__(self, checkbox_state, dict, params):
        super().__init__()
        self.params = params  # shared Parameters object
        self.checkbox_states = checkbox_state
        self.dict = dict

        self.infoList = []
        self.dataList = []
        self.dataList2 = []
        self.results = []
        self.results2 = []
        self.currenttime = None

        self.was_aborted = False
        self.force_exit = False   # ✅ Add this line

    def run(self):
        try:
            #Execute Voltage Measurement for each test checked---------------
            #Voltage Accuracy Test
            if self.checkbox_states["Voltage_Test"]:
                #Voltage Accuracy
                if self.checkbox_states.get("VoltageAccuracy"):
                    if self.dict["Instrument"] == "Keysight":
                        for ch in self.dict["PSU_Channel"]:
                            (infoList,
                            dataList,
                            dataList2)= NewVoltageMeasurement.Execute_Voltage_Accuracy(self, self.dict, ch)

                            #Measurement Completion
                            if (int(self.params["noofloop"]) - 1) <= 0:
                                self.progress.emit("✅Measurement is complete !")

                                #Export Data to CSV
                                if self.checkbox_states["DataReport"]:

                                    #Export data to CSV and Graph (Refer data.py for details)
                                    instrumentData(self.params["PSU"], self.params["DMM"], self.params["ELoad"])
                                    datatoCSV_Accuracy(infoList, dataList, dataList2)
                                    datatoGraph(infoList, dataList,dataList2)
                                    datatoGraph.scatterCompareVoltage(self, float(self.params["Programming_Error_Gain"]), float(self.params["Programming_Error_Offset"]), float(self.params["Readback_Error_Gain"]), float(self.params["Readback_Error_Offset"]), str(self.params["unit"]), float(self.params["Voltage_Rating"]))

                                    #Export to config.csv from dict (Refer pandas.py for details)
                                    df = pd.DataFrame.from_dict(self.dict, orient="index")
                                    df.index.name = "Parameter"
                                    df.columns = ["Value"]
                                    df.to_csv(os.path.join(csv_folder,"config.csv"))

                                    #Read error,config and instrumentData files, then combine to (self.unit) file (Refer xlreport for details)
                                    A = xlreport(save_directory=self.params["savelocation"], file_name=str(self.params["unit"]))
                                    A.run()
                                    self.progress.emit("Excel Report Saved: " + str(self.params["savelocation"]))
                                    self.progress.emit("")

                #Voltage Load Regulation
                if self.checkbox_states.get("VoltageLoadRegulation"):
                    if self.params["Instrument"] == "Keysight":
                        for ch in self.params["PSU_Channel"]:
                            self.results = NewLoadRegulation.executeCV_LoadRegulation(self, self.dict)
                            os.system('cls')
                            datatoCSV_LoadRegulation(self.results, self.params)

                #Transient Recovery       
                if self.checkbox_states.get("TransientRecovery"):
                    if self.checkbox_states["SpecialCase"]:
                        RiseFallTime.executeC(self, self.dict)
                    
                    if self.checkbox_states["NormalCase"]:
                        RiseFallTime.executeC(self, self.dict)
                
                #OVP Accuracy Test
                if self.checkbox_states.get("OVP_Test"):
                    self.results = OVP_Test.Execute_OVP(self,self.dict)
                    os.system('cls')
                    datatoCSV_OVP_Accuracy(self.results, self.params)
                    
                #Voltage Line RegulationW
                if self.checkbox_states.get("VoltageLineRegulation"):
                    self.results = LineRegulation.executeCV_LoadRegulation(self, self.dict)
                    #os.system('cls')
                    datatoCSV_Line_Regulation(self.results, self.params)
                
                #Programming Responses
                if self.checkbox_states.get("ProgrammingSpeed"):
                    test = ProgrammingResponse()
                    self.results, self.currenttime = test.execute(self.dict)
                    os.system('cls')    
                    datatoCSV_Programming_Response(self.results,self.currenttime,self.params)
                
            elif self.checkbox_states["Current_Test"]:
                #Current Accuracy Test
                if self.checkbox_states.get("CurrentAccuracy"):
                    if self.params["Instrument"] == "Keysight":
                        for ch in self.params["PSU_Channel"]:
                            (infoList,
                            dataList,
                            dataList2) = NewCurrentMeasurement.executeCurrentMeasurementA(self, self.dict, ch)

                            #Measurement Completion
                            if x == (int(self.params["noofloop"]) - 1):   
                                self.progress.emit("✅Measurement is complete !")

                                #Export Data to CSV
                                if self.checkbox_states["DataReport"]:

                                    #Export data to CSV and Graph (Refer data.py for details)
                                    instrumentData(self.params.PSU, self.params.DMM, self.params.ELoad)
                                    datatoCSV_Accuracy2(infoList, dataList, dataList2)
                                    datatoGraph2(infoList, dataList,dataList2)
                                    datatoGraph2.scatterCompareCurrent2(self, float(self.params["Programming_Error_Gain"]), float(self.params["Programming_Error_Offset"]), float(self.params["Readback_Error_Gain"]), float(self.params["Readback_Error_Offset"]), str(self.params["unit"]), float(self.params["I_Rating"]))

                                    #Export to config.csv from dict (Refer pandas.py for details)
                                    df = pd.DataFrame.from_dict(self.dict, orient="index")
                                    df.index.name = "Parameter"
                                    df.columns = ["Value"]
                                    df.to_csv(os.path.join(csv_folder,"config.csv"))

                                    #Read error,config and instrumentData files, then combine to (self.params.unit) file (Refer xlreport for details)
                                    A = xlreport(save_directory=self.params["savedir"], file_name=str(self.params["unit"]))
                                    A.run()
                                    self.progress.emit("Excel Report Saved: " + str(self.params["savedir"]))
                                    self.progress.emit("")

                            if self.force_exit:
                                self.progress.emit("Operation aborted")
                                return  # Exit immediately                         

                #Current Load Regulation Test
                if self.checkbox_states.get("CurrentLoadRegulation"):
                    if self.params["Instrument"] == "Keysight":
                        for ch in self.params["PSU_Channel"]:
                            self.results = NewLoadRegulation.executeCC_LoadRegulation(self, self.dict)
                            os.system('cls')
                            datatoCSV_LoadRegulation(self.results, self.params)

                #Power Accuracy Test
                if self.checkbox_states.get("PowerAccuracy"):
                    if self.checkbox_states["Voltage_Test"]:
                        infoList, dataList, dataList2 = PowerMeasurement.executePowerMeasurementB(self, self.dict)  # Power CC
                        
                    elif self.checkbox_states["Current_Test"]:
                        infoList, dataList, dataList2 = PowerMeasurement.executePowerMeasurementA(self, self.dict)  # Power CV
                    
                    #Measurement Completion
                    if x == (int(self.params["noofloop"]) - 1):   
                        self.progress.emit("✅Measurement is complete !")

                        #Export Data to CSV
                        if self.checkbox_states["DataReport"]:

                            #Export data to CSV and Graph (Refer data.py for details)
                            powerinstrumentData(self.params["PSU"], self.params["DMM"], self.params["DMM2"], self.params["ELoad"])
                            datatoCSV_PowerAccuracy(infoList, dataList, dataList2)
                            datatoGraph3(infoList, dataList,dataList2)
                            datatoGraph3.scatterComparePower(self, float(self.params["Power_Programming_Error_Gain"]), float(self.params["Power_Programming_Error_Offset"]), float(self.params["Power_Readback_Error_Gain"]), float(self.params["Power_Readback_Error_Offset"]), str(self.params["setFunction"]), float(self.params["P_Rating"]))
                            
                            #Export to config.csv from dict (Refer pandas.py for details)
                            df = pd.DataFrame.from_dict(self.dict, orient="index")
                            df.index.name = "Parameter"
                            df.columns = ["Value"]
                            df.to_csv(os.path.join(csv_folder,"powerconfig.csv"))

                            #Read error,config and instrumentData files, then combine to (self.unit) file (Refer xlreport for details)
                            file_name = "Power_CV" if self.params["setFunction"] == "Current" else "Power_CC"
                            A = xlreportpower(save_directory=self.params["savedir"], file_name=file_name)
                            A.run()
                            
                            self.progress.emit("Excel Report Saved: " + str(self.params["savedir"]))
                            self.progress.emit("")

                #Current Line Regulation
                if self.checkbox_states.get("CurrentLineRegulation"):
                    self.results = LineRegulation.executeCC_LoadRegulation(self, self.dict)
                    datatoCSV_Line_Regulation(self.results, self.params)
                    
                #OCP Accuracy Test
                if self.checkbox_states.get("OCP_Test"):
                    
                    #Accuracy Test 1st
                    #OCP_test = OCP_Accuracy()
                    #self.results = OCP_test.Execute_OCP(dict)
                    #os.system('cls')
                    # OCP_data_export = datatoCSV_OCP_Test(params)
                    #OCP_data_export.AccuracyTest(self.results)

                    self.results =[]
                    
                    #Activation Time Test
                    OCP_test2 = OCP_Activation_Time()
                    self.results = OCP_test2.Execute_OCP(self.dict)
                    OCP_data_export2 = datatoCSV_OCP_Test(self.params)
                    OCP_data_export2.ActivationTime(self.results)

            # Final progress (only if completed)
            if not self.force_exit:
                self.progress_value.emit(100)
                self.progress.emit("All measurements completed!")
                                   
        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(e, tb)
        finally:
            self.finished.emit()

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

    """This class is to configure the AC Source Supply to DUT if the selected AC Supply is External."""

    def __init__(self,parameters):
        super().__init__()

        self.params = parameters

        self.setWindowTitle("AC Source Configuration")

        self.QPushButton_RunAC_Widget = QPushButton()
        self.QPushButton_RunAC_Widget.setText("Confirm")

        QLabel_ACSource_VisaAddress = QLabel()
        QLabel_AC_CurrentLimit = QLabel()
        QLabel_AC_VoltageOutput = QLabel()
        QLabel_Frequency = QLabel()

        QLabel_ACSource_VisaAddress.setText("Visa Address (AC):")
        QLabel_AC_CurrentLimit.setText("AC Current Limit")
        QLabel_AC_VoltageOutput.setText("AC Voltage Output to DUT")
        QLabel_Frequency.setText("AC Frequency Output")

        self.QComboBox_ACSource_VisaAddress = QComboBox()
        self.QLineEdit_AC_CurrentLimit =  QLineEdit()
        self.QLineEdit_AC_VoltageOutput =  QLineEdit()
        self.QLineEdit_Frequency =  QLineEdit()

        self.QComboBox_ACSource_VisaAddress.clear()
        self.visaIdList, self.nameList, instrument_roles = NewGetVisaSCPIResources()
        for i in range(len(self.nameList)):
            self.QComboBox_ACSource_VisaAddress.addItems([str(self.visaIdList[i])])
        
        if 'ACSource' in instrument_roles:
            AC_index = self.visaIdList.index(instrument_roles['ACSource'])
            self.QComboBox_ACSource_VisaAddress.setCurrentIndex(AC_index)
    
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
        
        self.QComboBox_ACSource_VisaAddress.currentTextChanged.connect(self.ACSource_VisaAddress_changed)
        self.QLineEdit_AC_CurrentLimit.textEdited.connect(self.AC_CurrentLimit_changed)
        self.QLineEdit_AC_VoltageOutput.textEdited.connect(self.AC_VoltageOutput_changed)
        self.QLineEdit_Frequency.textEdited.connect(self.Frequency_changed) 

        self.QPushButton_RunAC_Widget.clicked.connect(self.ActivateACPower)


    def ACSource_VisaAddress_changed (self,s):
        self.params.ACSource = s
        print(self.params.ACSource)

    def AC_CurrentLimit_changed (self,s):
        self.params.AC_CurrentLimit = s
        print(self.params.AC_CurrentLimit)

    def AC_VoltageOutput_changed (self,s):
        self.params.AC_VoltageOutput = s
        print(self.params.AC_VoltageOutput)
    
    def Frequency_changed (self,s):
        self.params.Frequency = s
        print(self.params.Frequency)

    def ActivateACPower(self):
        global globalvv
        params ={
            "Instrument": "Keysight",
            "ACSource": self.params.ACSource,
            "AC_CurrentLimit": self.params.AC_CurrentLimit,
            "AC_VoltageOutput": self.params.AC_VoltageOutput,
            "Frequency": self.params.Frequency,
        }
        dict = dictGenerator.input(**params)

        A = VisaResourceManager()
        flag, args = A.openRM(self.params.ACSource)
        if flag == 0:
            string = ""
            for item in args:
                string = string + item

            QMessageBox.warning(self, "VISA IO ERROR", string)
            return
        try:
            ActivateAC.PowerStart(self, dict)
            super.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return
 

if __name__ == "__main__":
    original_stdout = sys.stdout
    my_result = StringIO()
    sys.stdout = my_result

    # # Create the application
    app = QApplication(sys.argv)

    win = MainWindow()
    win.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
    win.show()  # Start the window in full screen mode

    sys.stdout = original_stdout
    sys.exit(app.exec())
