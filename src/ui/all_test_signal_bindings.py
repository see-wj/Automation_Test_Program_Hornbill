"""Declarative signal wiring for the production all-test dialog."""


TEXT_EDITED_BINDINGS = (
    ("QLineEdit_V_Settling_Band", "V_Settling_Band_changed"),
    ("QLineEdit_T_Settling_Band", "T_Settling_Band_changed"),
    ("QLineEdit_OSC_Display_Channel", "OSC_Channel_changed"),
    ("QLineEdit_TimeScale", "TimeScale_changed"),
    ("QLineEdit_VerticalScale", "VerticalScale_changed"),
    ("QLineEdit_Programming_Error_Gain", "Programming_Error_Gain_changed"),
    ("QLineEdit_Programming_Error_Offset", "Programming_Error_Offset_changed"),
    ("QLineEdit_Readback_Error_Gain", "Readback_Error_Gain_changed"),
    ("QLineEdit_Readback_Error_Offset", "Readback_Error_Offset_changed"),
    ("QLineEdit_Load_Programming_Error_Gain", "Load_Programming_Error_Gain_changed"),
    ("QLineEdit_Load_Programming_Error_Offset", "Load_Programming_Error_Offset_changed"),
    ("QLineEdit_Power_Programming_Error_Gain", "Power_Programming_Error_Gain_changed"),
    ("QLineEdit_Power_Programming_Error_Offset", "Power_Programming_Error_Offset_changed"),
    ("QLineEdit_Power_Readback_Error_Gain", "Power_Readback_Error_Gain_changed"),
    ("QLineEdit_Power_Readback_Error_Offset", "Power_Readback_Error_Offset_changed"),
    ("QLineEdit_Programming_Response_Up_NoLoad", "Programming_Response_Up_NoLoad_changed"),
    ("QLineEdit_Programming_Response_Up_FullLoad", "Programming_Response_Up_FullLoad_changed"),
    ("QLineEdit_Programming_Response_Down_NoLoad", "Programming_Response_Down_NoLoad_changed"),
    ("QLineEdit_Programming_Response_Down_FullLoad", "Programming_Response_Down_FullLoad_changed"),
    ("QLineEdit_current_rated", "Current_Rating_changed"),
    ("QLineEdit_voltage_rated", "Voltage_Rating_changed"),
    ("QLineEdit_minVoltage", "minVoltage_changed"),
    ("QLineEdit_maxVoltage", "maxVoltage_changed"),
    ("QLineEdit_minCurrent", "minCurrent_changed"),
    ("QLineEdit_maxCurrent", "maxCurrent_changed"),
    ("QLineEdit_voltage_stepsize", "voltage_step_size_changed"),
    ("QLineEdit_current_stepsize", "current_step_size_changed"),
    ("QLineEdit_Power", "Power_changed"),
    ("QLineEdit_power_rated", "Power_Rating_changed"),
    ("QLineEdit_power_step_size", "power_step_size_changed"),
    ("QLineEdit_PowerINI", "PowerINI_changed"),
    ("QLineEdit_rshunt", "rshunt_changed"),
    ("QLineEdit_OVP_Level", "OVP_Level_changed"),
    ("QLineEdit_OCP_Level", "OCP_Level_changed"),
    ("QLineEdit_OCP_ActivationTime_Error", "OCP_Activation_Time_changed"),
)


CURRENT_TEXT_BINDINGS = (
    ("QComboBox_Channel_CouplingMode", "Channel_CouplingMode_changed"),
    ("QComboBox_Trigger_CouplingMode", "Trigger_CouplingMode_changed"),
    ("QComboBox_Trigger_Mode", "Trigger_Mode_changed"),
    ("QComboBox_Trigger_SweepMode", "Trigger_SweepMode_changed"),
    ("QComboBox_Trigger_SlopeMode", "Trigger_SlopeMode_changed"),
    ("QComboBox_Probe_Setting", "Probe_Setting_changed"),
    ("QComboBox_Acq_Type", "Acq_Type_changed"),
    ("QComboBox_DUT", "DUT_changed"),
    ("QLineEdit_PSU_VisaAddress", "PSU_VisaAddress_changed"),
    ("QLineEdit_DMM_VisaAddressforVoltage", "DMM_VisaAddressforVoltage_changed"),
    ("QLineEdit_DMM_VisaAddressforCurrent", "DMM_VisaAddressforCurrent_changed"),
    ("QLineEdit_OSC_VisaAddress", "OSC_VisaAddress_changed"),
    ("QLineEdit_ELoad_VisaAddress", "ELoad_VisaAddress_changed"),
    ("QLineEdit_DAQ_VisaAddress", "DAQ_VisaAddress_changed"),
    ("QComboBox_DMM_Instrument", "DMM_Instrument_changed"),
    ("QComboBox_AC_Supply_Type", "AC_Supply_Type_changed"),
    ("QComboBox_set_PSU_Channel", "set_PSU_Channel_changed"),
    ("QComboBox_set_ELoad_Channel", "ELoad_Channel_changed"),
    ("QComboBox_set_Function", "set_Function_changed"),
    ("QComboBox_Voltage_Res", "set_VoltageRes_changed"),
    ("QComboBox_Voltage_Sense", "set_VoltageSense_changed"),
    ("QComboBox_Hornbill_Measurement_Command", "Hornbill_Measurement_Command_changed"),
    ("QComboBox_Relay_Control", "Relay_Control_changed"),
    ("QComboBox_SPOperationMode", "SPOperationMode_changed"),
    ("QComboBox_Line_Reg_Range", "Line_Reg_Range_changed"),
    ("QComboBox_noofloop", "noofloop_changed"),
    ("QComboBox_updatedelay", "updatedelay_changed"),
)


STATE_CHANGED_BINDINGS = (
    ("QCheckBox_SpecialCase_Widget", "checkbox_state_SpecialCase"),
    ("QCheckBox_NormalCase_Widget", "checkbox_state_NormalCase"),
    ("QCheckBox_Report_Widget", "checkbox_state_Report"),
    ("QCheckBox_Lock_Widget", "checkbox_state_lock"),
    ("QCheckBox_Image_Widget", "checkbox_state_Image"),
    ("QCheckBox_Temperature_Widget", "checkbox_state_Temperature"),
    ("QCheckBox_VoltageAccuracy_Widget", "toggle_voltage_accuracy_branch"),
    ("QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget", "voltage_accuracy_mode_changed"),
    ("QCheckBox_Voltage_Accuracy_Current_Mode_Widget", "voltage_accuracy_mode_changed"),
    ("QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget", "voltage_accuracy_mode_changed"),
    ("QCheckBox_VoltageLoadRegulation_Widget", "checkbox_state_VoltageLoadRegulation"),
    ("QCheckBox_TransientRecovery_Widget", "checkbox_state_TransientRecovery"),
    ("QCheckBox_CurrentAccuracy_Widget", "toggle_current_accuracy_branch"),
    ("QCheckBox_CurrentLoadRegulation_Widget", "checkbox_state_CurrentLoadRegulation"),
    ("QCheckBox_PowerAccuracy_Widget", "checkbox_state_PowerAccuracy"),
    ("QCheckBox_OVP_Test_Widget", "checkbox_state_OVP_Test"),
    ("QCheckBox_OCP_Test_Widget", "checkbox_state_OCP_Test"),
    ("QCheckBox_CurrentLineRegulation_Widget", "checkbox_state_VoltageLine"),
    ("QCheckBox_VoltageLineRegulation_Widget", "checkbox_state_CurrentLine"),
    ("QCheckBox_ProgrammingSpeed_Widget", "checkbox_state_ProgrammingSpeed_Test"),
)


CLICKED_BINDINGS = (
    ("QPushButton_Voltage_Widget", "select_button"),
    ("QPushButton_Current_Widget", "select_button"),
    ("QPushButton_Widget0", "savepath"),
    ("QPushButton_Widget1", "executeTest"),
    ("QPushButton_Widget2", "openDialog"),
    ("QPushButton_Widget3", "estimateTime"),
    ("QPushButton_Widget4", "doFind"),
)


def _connect(dialog, bindings, signal_name):
    for widget_name, handler_name in bindings:
        widget = getattr(dialog, widget_name)
        signal = getattr(widget, signal_name)
        signal.connect(getattr(dialog, handler_name))


def connect_all_test_signals(dialog):
    _connect(dialog, TEXT_EDITED_BINDINGS, "textEdited")
    _connect(dialog, CURRENT_TEXT_BINDINGS, "currentTextChanged")
    _connect(dialog, STATE_CHANGED_BINDINGS, "stateChanged")
    _connect(dialog, CLICKED_BINDINGS, "clicked")
    dialog.QComboBox_DUT.currentIndexChanged.connect(
        dialog.on_current_index_changed
    )
    dialog.queue_test_button.clicked.connect(
        lambda: dialog.executeTest(queue_only=True)
    )
