"""Legacy multithread voltage experiment, excluded from production flow."""

from GUI import *

class TestWorker123(QThread):
    finished = pyqtSignal()          # Signal emitted when test is done
    progress = pyqtSignal(str)       # Signal to update OutputBox
    error = pyqtSignal(str)          # Signal to show errors via QMessageBox
    new_data = pyqtSignal(float, float)  # Programming V, Readback V

    def __init__(self, dialog_instance, params):
        super().__init__()
        self.dialog = dialog_instance
        self.params = params
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True

    def run(self):
        try:
            #self.dialog.setEnabled(False)
            self.progress.emit("Starting Test...")

            measurement = DolphinNewVoltageMeasurementwithELoad()

            for x in range(int(self.params['noofloop'])):
                self.progress.emit(
                    f"Running loop {x+1}/{self.params['noofloop']}..."
                )

                try:
                    (
                        self.infoList,
                        self.dataList,
                        self.dataList2,
                    ) = measurement.Execute_Voltage_Accuracy(
                        self.params,
                        self.dialog.PSU_Channel,
                        worker=self
              
                    )

                    self.progress.emit(f"Loop {x+1} complete.")


                except Exception as e:
                    self.error.emit(str(e))
                    return  # STOP on failure

            self.progress.emit("Measurement complete!")

        finally:
            self.dialog.setEnabled(True)
            self.finished.emit()

class MultiThreadVoltageMeasurementDialog(QDialog):
    """Class for configuring the voltage measurement DUT Tests Dialog.
    A widget is declared for each parameter that can be customized by the user. These widgets can come in
    the form of QLineEdit, or QComboBox where user can select their preferred parameters. When the widgets
    detect changes, a signal will be transmitted to a designated slot which is a method in this class
    (e.g. [paramter_name]_changed). The parameter values will then be updated. At runtime execution of the
    DUT Test, the program will compile all the parameters into a dictionary which will be passed as an argument
    into the test methods and execute the DUT Tests accordingly.

    For more details regarding the arguments, see DUT_Test_Scripts/Dolphin/DUT_Test.py.


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
        self.Aperture = "MAX"
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

        self.simulation_mode = 0
        self.output_file = r"C:\Users\shamlee3\OneDrive - Keysight Technologies\Wei Jing See's files - Shamman Xian Jun Lee\Test Data\Monk3.xlsx"  
        self.selected_text  = "Hornbill"
        self.stop_requested = False

        
       
        self.plot_widget = pg.PlotWidget(title="Voltage Accuracy")
        #Two Curves : Programing V(red), Readback V(blue)
        self.programming_curve = self.plot_widget.plot(pen=pg.mkPen(color='r', width=5), name="Programming Voltage")
        self.readback_curve = self.plot_widget.plot(pen=pg.mkPen(color='b', width=5), name="Readback Voltage")
        self.prog_up_bound = self.plot_widget.plot(pen=pg.mkPen(color='y', width=5), name="Upper Boundary Limit")
        self.prog_low_bound = self.plot_widget.plot(pen=pg.mkPen(color='y', width=5), name="Lower Boundary Limit")

        self.x_data = []
        self.prog_data = []
        self.read_data = []
        self.counter = 0

        self.checkbox_SpecialCase = 2
        self.checkbox_NormalCase = 2

        self.checkbox_Voltage_Accuracy_Voltage_Mode = 2
        self.checkbox_Voltage_Accuracy_Current_Mode = 0
        
        #Create Voltage Window
        self.setWindowTitle("Voltage Measurement")
        self.image_window = None
        self.setWindowFlags(Qt.Window)
        font = QFont()
        font.setPointSize(16)   # Adjust size here
        self.setFont(font)

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
        QPushButton_Widget5 = QPushButton()
        QPushButton_Widget5.setText("Stop Test")
        self.QCheckBox_Report_Widget = QCheckBox()
        self.QCheckBox_Report_Widget.setText("Generate Excel Report")
        self.QCheckBox_Report_Widget.setCheckState(Qt.Checked)
        self.QCheckBox_Image_Widget = QCheckBox()
        self.QCheckBox_Image_Widget.setText("Show Graph")
        self.QCheckBox_Image_Widget.setCheckState(Qt.Checked)
        QCheckBox_Lock_Widget = QCheckBox()
        QCheckBox_Lock_Widget.setText("Lock Widget")

        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget = QCheckBox()
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget.setText("Current Static (Voltage Change)")
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget.setCheckState(Qt.Checked)
        
        self.QCheckBox_Voltage_Accuracy_Current_Mode_Widget = QCheckBox()
        self.QCheckBox_Voltage_Accuracy_Current_Mode_Widget.setText("Current Change(Load Change)")
        self.QCheckBox_Voltage_Accuracy_Current_Mode_Widget.setCheckState(Qt.Unchecked)

        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget = QCheckBox()
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget.setText("Current Static (Voltage Change) with Oscilloscope Capture") 
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget.setCheckState(Qt.Unchecked)

        self.QCheckbox_Simulation_Mode = QCheckBox()
        self.QCheckbox_Simulation_Mode.setText("Simulation Mode")
        self.QCheckbox_Simulation_Mode.setCheckState(Qt.Unchecked)
        

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

        #Voltage Accuracy Mode
        QLabel_Voltage_Accuracy_Mode = QLabel()
        QLabel_Voltage_Accuracy_Mode.setFont(desp_font)
        QLabel_Voltage_Accuracy_Mode.setText("Voltage Accuracy Test Mode Selection:")

        #Simulation Mode
        QLabel_Simulation_Mode =QLabel()    
        QLabel_Simulation_Mode.setFont(desp_font)
        QLabel_Simulation_Mode.setText("Enable Simulation Mode (No Instruments Connected):")

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
        QLabel_DUT.setText("DUT Test Profile:")

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
        self.QComboBox_set_PSU_Channel.addItems(["None", "1", "2", "3", "4"])
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
        exec_layout.addRow(QPushButton_Widget5)   

        exec_layout_box.addLayout(exec_layout)
 
        Right_container.addLayout(save_path_layout)
        Right_container.addLayout(exec_layout_box)
        Right_container.addWidget(self.plot_widget)

        #Setting Form Layout with Left Container
        Left_container = QHBoxLayout()
        setting_layout = QFormLayout()

        setting_layout.addRow(Desp1)
        setting_layout.addRow(self.QCheckbox_Simulation_Mode)
        setting_layout.addRow(QLabel_DUT, self.QComboBox_DUT)
        setting_layout.addRow(QLabel_Voltage_Accuracy_Mode)
        setting_layout.addRow(self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget)
        setting_layout.addRow(self.QCheckBox_Voltage_Accuracy_Current_Mode_Widget)
        setting_layout.addRow(self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget)
        setting_layout.addRow(QPushButton_Widget4)
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

        self.QCheckbox_Simulation_Mode.stateChanged.connect(self.simulation_mode_changed)   

        self.QLineEdit_PSU_VisaAddress.currentTextChanged.connect(self.PSU_VisaAddress_changed)
        self.QLineEdit_DMM_VisaAddress.currentTextChanged.connect(self.DMM_VisaAddress_changed)
        self.QLineEdit_ELoad_VisaAddress.currentTextChanged.connect(self.ELoad_VisaAddress_changed)

        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget.stateChanged.connect(self.checkbox_state_Voltage_Accuracy_Voltage_Mode)
        self.QCheckBox_Voltage_Accuracy_Current_Mode_Widget.stateChanged.connect(self.checkbox_state_Voltage_Accuracy_Current_Mode)
        self.QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget.stateChanged.connect(self.checkbox_state_Voltage_Accuracy_Voltage_Mode_Oscilloscope)
        
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
        QPushButton_Widget5.clicked.connect(self.stop_worker)

        AdvancedSettingsList.append(self.Range)
        AdvancedSettingsList.append(self.Aperture)
        AdvancedSettingsList.append(self.AutoZero)
        AdvancedSettingsList.append(self.inputZ)
        AdvancedSettingsList.append(self.UpTime)
        AdvancedSettingsList.append(self.DownTime)
    
    def stop_worker(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.request_stop()
            self.OutputBox.append("Stop requested, waiting for worker to finish...")

    def update_plot(self, programming_v, readback_v):
        self.counter += 1
        self.x_data.append(self.counter)
        self.prog_data.append(programming_v)
        self.read_data.append(readback_v)

        #keep only the latest 100 points for better performance
        if len(self.x_data) > 100:
            self.x_data = self.x_data[-100:]
            self.prog_data = self.prog_data[-100:]
            self.read_data = self.read_data[-100:]
        
        self.programming_curve.setData(self.x_data, self.prog_data)
        self.readback_curve.setData(self.x_data, self.read_data)
    
    def update_status(self, message):
        self.OutputBox.append(message)
    
    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def simulation_mode_changed(self, state):
        if state == Qt.Checked:
            self.simulation_mode = 2
        else:
            self.simulation_mode = 0
    
    def checkbox_state_Voltage_Accuracy_Voltage_Mode(self, state):
        if state == Qt.Checked:
            self.checkbox_Voltage_Accuracy_Voltage_Mode = 2
        else:
            self.checkbox_Voltage_Accuracy_Voltage_Mode = 0

    def checkbox_state_Voltage_Accuracy_Current_Mode(self, state):
        if state == Qt.Checked:
            self.checkbox_Voltage_Accuracy_Current_Mode = 2
        else:
            self.checkbox_Voltage_Accuracy_Current_Mode = 0

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

        channel_str = str(self.PSU_Channel)
        index = self.QComboBox_set_PSU_Channel.findText(channel_str)
        self.QComboBox_set_PSU_Channel.setCurrentIndex(index)
        self.QComboBox_set_PSU_Channel.setCurrentIndex(int(self.PSU_Channel))
        self.QComboBox_set_ELoad_Channel.setCurrentIndex(int(self.ELoad_Channel))
        self.QComboBox_Voltage_Sense.setCurrentText("4 Wire" if self.VoltageSense == "EXT" else "2 Wire")
        self.QComboBox_noofloop.setCurrentText(self.noofloop)
        self.QComboBox_updatedelay.setCurrentText(self.updatedelay)

    def update_selection(self, selected_text):
        """Update selected text and reload config file"""
        self.selected_text = selected_text
        self.load_data()

    """def load_data(self):
        Reads configuration file and returns a dictionary of key-value pairs.
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

        return config_data"""
    

    """def load_data(self):
        Reads configuration file and returns a dictionary of key-value pairs.
        config_data = {}

        # Determine base folder for configs
        if getattr(sys, "frozen", False):
            # Running as PyInstaller exe
            exe_folder = Path(sys.executable).parent
            # Configs should be in Executable/Instrument_Config_Files
            config_base = exe_folder / "Instrument_Config_Files"
        else:
            # Running as normal Python script
            project_root = Path(__file__).resolve().parent.parent  # <-- go up one level from src
            config_base = project_root / "Instrument_Config_Files"

        # Map selected_text to config filename
        file_map = {
            "Excavator": "config_Excavator.txt",
            "Dolphin": "config_Dolphin.txt",
            "SMU": "config_SMU.txt",
            "Hornbill": "config_Hornbill.txt"
        }
        config_filename = file_map.get(self.selected_text, "config_Others.txt")
        self.config_file = config_base / config_filename

        try:
            with open(self.config_file, "r") as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        config_data[key.strip()] = value.strip()

            for key, value in config_data.items():
                if key == "savelocation":
                    if self.savelocation and self.savelocation != "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
                        continue
                    else:
                        setattr(self, key, value)
                else:
                    setattr(self, key, value)

        except FileNotFoundError:
            print(f"⚠️ Config file not found: {self.config_file}. Using default values.")

        return config_data"""
    
    def load_data(self):
        """Reads configuration file and returns a dictionary of key-value pairs."""
        config_data = {}

        config_map = {
            "Excavator": "config_Excavator.txt",
            "Dolphin": "config_Dolphin.txt",
            "SMU": "config_SMU.txt",
            "Hornbill": "config_Hornbill.txt",
        }

        filename = config_map.get(self.selected_text, "config_Others.txt")

        # Ensure path is a string, avoids crashes
        self.config_file = str(config_folder / filename)

        if not os.path.exists(self.config_file):
            print(f"⚠ Config file not found: {self.config_file}")
            return {}

        try:
            with open(self.config_file, "r", encoding="utf-8-sig") as file:
                for line in file:
                    line = line.strip()

                    if not line or line.startswith("#") or line.startswith("//"):
                        continue

                    if "=" not in line:
                        print("⚠ Skipping invalid line:", repr(line))
                        continue

                    key, value = line.split("=", 1)
                    config_data[key.strip()] = value.strip()


            for key, value in config_data.items():
                if key == "savelocation":
                    if getattr(self, "savelocation", None) and \
                    self.savelocation != "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing":
                        continue
                    setattr(self, key, value)
                else:
                    setattr(self, key, value)

        except Exception as e:
            print(f"ERROR reading config: {e}")

        return config_data



    def Power_changed(self, value):
        self.Power = value

    def doFind(self):
        try:
            self.QLineEdit_PSU_VisaAddress.clear()
            self.QLineEdit_DMM_VisaAddress.clear()
            self.QLineEdit_ELoad_VisaAddress.clear()
            
            discovery = NewGetVisaSCPIResources()
            self.visaIdList = discovery.addresses
            self.nameList = discovery.identities
            instrument_roles = discovery.roles
            
            for i in range(len(self.nameList)):
                self.OutputBox.append(str(self.nameList[i]) + str(self.visaIdList[i]))
                self.QLineEdit_PSU_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_DMM_VisaAddress.addItems([str(self.visaIdList[i])])
                self.QLineEdit_ELoad_VisaAddress.addItems([str(self.visaIdList[i])])

            if 'PSU' in instrument_roles:
                psu_index = self.visaIdList.index(instrument_roles['PSU'])
                self.QLineEdit_PSU_VisaAddress.setCurrentIndex(psu_index)

            if 'ELOAD' in instrument_roles:
                eload_index = self.visaIdList.index(instrument_roles['ELOAD'])
                self.QLineEdit_ELoad_VisaAddress.setCurrentIndex(eload_index)

            if 'DMM' in instrument_roles:
                dmm_index = self.visaIdList.index(instrument_roles['DMM'])
                self.QLineEdit_DMM_VisaAddress.setCurrentIndex(dmm_index)
            
            # Add "None" option at the end
            self.QLineEdit_PSU_VisaAddress.addItem("TCPIP0::141.183.188.184::5025::SOCKET")
            self.QLineEdit_DMM_VisaAddress.addItem("None")
            self.QLineEdit_ELoad_VisaAddress.addItem("None")
            self.QLineEdit_PSU_VisaAddress.addItem("TCPIP0::141.183.188.184::inst0::INSTR")
                    
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
        try:
            # Generate your parameters dictionary as before
            dict_params = dictGenerator.input(
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
            missing = self.check_missing_params(dict_params)
            if missing:
                QMessageBox.warning(self, "Missing Params", f"The following parameters are missing: {missing}")
                return

            # Create the worker
            self.worker = TestWorker123(self, dict_params)
            self.worker.progress.connect(lambda msg: self.OutputBox.append(msg))
            self.worker.error.connect(lambda err: QMessageBox.warning(self, "Error", err))
            self.worker.finished.connect(lambda: self.OutputBox.append("Worker finished."))
            self.worker.new_data.connect(self.update_plot)
            self.worker.progress.connect(self.update_status)
            self.worker.error.connect(self.show_error)
            # Start the worker thread
            self.worker.start()

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))


    def stopTest(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop_requested = True
            self.OutputBox.append("Stop requested... waiting for current loop to finish.")
