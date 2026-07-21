"""Mutable production test parameters and UI input filtering."""

import os

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QComboBox, QMessageBox

from configuration.configuration_service import (
    apply_configuration,
    configuration_path,
    load_configuration,
)
from common.output_logging import print_console_safe
from common.path import (
    DATA_CSV_PATH,
    ERROR_CSV_PATH,
    IMAGE_PATH,
    POWER_DATA_CSV_PATH,
    POWER_ERROR_CSV_PATH,
    POWER_IMAGE_PATH,
    config_folder,
    setup_img_folder,
)


class ComboBoxWheelFilter(QObject):
    def eventFilter(self, obj, event):
        if (
            isinstance(obj, QComboBox)
            and event.type() == event.Wheel
            and not obj.view().isVisible()
        ):
            return True
        return super().eventFilter(obj, event)


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
        self.DAQ = None
        self.ELoad_Channel = None
        self.PSU_Channel =  None
        self.OSC_Channel = None
        self.DMM_Instrument =  None
        self.rshunt = None
        self.OVP_Level = None
        self.OCP_Level = None
        self.OCPActivationTime = None
        self.SPOperationMode = "Independent"

        self.DMM_Model = "3458A"
        self.ELoad_Model = "E367XXA"
        self.Hornbill_Measurement_Command = "DIAG"
        self.Relay_Control = "None"

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

        self.checkbox_SpecialCase = None
        self.checkbox_NormalCase = None

        self.ACSource= None
        self.AC_CurrentLimit= 10
        self.AC_VoltageOutput= 230
        self.Frequency= 50
        self.AC_Supply_Type= "Plug"
        self.Line_Reg_Range= [100,115,230]

        self.x_data = []
        self.prog_data = []
        self.read_data = []
        self.up_data = []
        self.low_data = []
        self.counter = 0

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

    def get(self, key, default=None):
        return getattr(self, key, default)
    
    def update_selection(self, selected_text):
        """Update selected text and reload config file"""
        self.selected_text = selected_text
        self.load_data()

    def load_data(self):
        """Load setup defaults for the selected DUT."""
        self.config_file = str(configuration_path(config_folder, self.selected_text))
        try:
            config_data = load_configuration(self.config_file)
        except FileNotFoundError:
            print_console_safe("Config file not found. Using default values.")
            return {}

        apply_configuration(self, config_data)
        return config_data
