"""Test-selection state collected from the production dialog."""

from PyQt5.QtWidgets import QFormLayout, QGroupBox, QVBoxLayout, QWidget


SELECTION_WIDGETS = {
    "Voltage_Test": "QPushButton_Voltage_Widget",
    "VoltageAccuracy": "QCheckBox_VoltageAccuracy_Widget",
    "CurrentStatic(VoltageChange)": "QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget",
    "CurrentChange(LoadChange)": "QCheckBox_Voltage_Accuracy_Current_Mode_Widget",
    "CurrentStatic(VoltageChange)withOscilloscope": "QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget",
    "Current_Test": "QPushButton_Current_Widget",
    "CurrentAccuracy": "QCheckBox_CurrentAccuracy_Widget",
    "CurrentAccuracy_20A_Range": "QCheckBox_Current_Accuracy_20A_Range_Widget",
    "CurrentAccuracy_2A_Range": "QCheckBox_Current_Accuracy_2A_Range_Widget",
    "CurrentAccuracy_200mA_Range": "QCheckBox_Current_Accuracy_200mA_Range_Widget",
    "CurrentAccuracy_20mA_Range": "QCheckBox_Current_Accuracy_20mA_Range_Widget",
    "CurrentAccuracy_2mA_Range": "QCheckBox_Current_Accuracy_2mA_Range_Widget",
    "CurrentAccuracy_200uA_Range": "QCheckBox_Current_Accuracy_200uA_Range_Widget",
    "SpecialCase": "QCheckBox_SpecialCase_Widget",
    "NormalCase": "QCheckBox_NormalCase_Widget",
    "DataReport": "QCheckBox_Report_Widget",
    "DataImage": "QCheckBox_Image_Widget",
    "Temperature": "QCheckBox_Temperature_Widget",
    "TransientRecovery": "QCheckBox_TransientRecovery_Widget",
    "VoltageLoadRegulation": "QCheckBox_VoltageLoadRegulation_Widget",
    "CurrentLoadRegulation": "QCheckBox_CurrentLoadRegulation_Widget",
    "PowerAccuracy": "QCheckBox_PowerAccuracy_Widget",
    "OVP_Test": "QCheckBox_OVP_Test_Widget",
    "VoltageLineRegulation": "QCheckBox_VoltageLineRegulation_Widget",
    "CurrentLineRegulation": "QCheckBox_CurrentLineRegulation_Widget",
    "ProgrammingSpeed": "QCheckBox_ProgrammingSpeed_Widget",
    "OCP_Test": "QCheckBox_OCP_Test_Widget",
}


class TestSelectionModel:
    def __init__(self, dialog):
        self.dialog = dialog

    def collect(self):
        return {
            name: getattr(self.dialog, widget_name).isChecked()
            for name, widget_name in SELECTION_WIDGETS.items()
        }


def collect_test_selections(dialog):
    return TestSelectionModel(dialog).collect()


def create_current_selection_widget(dialog, heading):
    group = QGroupBox()
    layout = QFormLayout(group)
    layout.addWidget(heading)
    layout.addWidget(dialog.QCheckBox_CurrentAccuracy_Widget)

    branch = QWidget()
    branch_layout = QVBoxLayout(branch)
    branch_layout.setContentsMargins(30, 0, 0, 0)
    for widget_name in (
        "QCheckBox_Current_Accuracy_20A_Range_Widget",
        "QCheckBox_Current_Accuracy_2A_Range_Widget",
        "QCheckBox_Current_Accuracy_200mA_Range_Widget",
        "QCheckBox_Current_Accuracy_20mA_Range_Widget",
        "QCheckBox_Current_Accuracy_2mA_Range_Widget",
        "QCheckBox_Current_Accuracy_200uA_Range_Widget",
    ):
        branch_layout.addWidget(getattr(dialog, widget_name))
    layout.addWidget(branch)

    for widget_name in (
        "QCheckBox_CurrentLoadRegulation_Widget",
        "QCheckBox_PowerAccuracy_Widget",
        "QCheckBox_CurrentLineRegulation_Widget",
        "QCheckBox_OCP_Test_Widget",
    ):
        layout.addWidget(getattr(dialog, widget_name))
    return group, branch


def create_voltage_selection_widget(dialog, heading):
    group = QGroupBox()
    layout = QFormLayout(group)
    layout.addWidget(heading)
    layout.addWidget(dialog.QCheckBox_VoltageAccuracy_Widget)

    branch = QWidget()
    branch_layout = QVBoxLayout(branch)
    branch_layout.setContentsMargins(30, 0, 0, 0)
    for widget_name in (
        "QCheckBox_Voltage_Accuracy_Voltage_Mode_Widget",
        "QCheckBox_Voltage_Accuracy_Current_Mode_Widget",
        "QCheckBox_Voltage_Accuracy_Voltage_Mode_Oscilloscope_Widget",
    ):
        branch_layout.addWidget(getattr(dialog, widget_name))
    layout.addWidget(branch)

    for widget_name in (
        "QCheckBox_VoltageLoadRegulation_Widget",
        "QCheckBox_TransientRecovery_Widget",
        "QCheckBox_OVP_Test_Widget",
        "QCheckBox_VoltageLineRegulation_Widget",
        "QCheckBox_ProgrammingSpeed_Widget",
    ):
        layout.addWidget(getattr(dialog, widget_name))
    return group, branch
