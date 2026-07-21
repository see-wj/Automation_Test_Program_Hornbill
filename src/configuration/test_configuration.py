"""Build immutable worker configuration from GUI parameters and selections."""

from copy import deepcopy
from dataclasses import dataclass


class ParameterSnapshot(dict):
    __getattr__ = dict.get

    def __setattr__(self, name, value):
        self[name] = value


@dataclass(frozen=True)
class RunSubmission:
    selections: dict
    configuration: dict
    parameters: ParameterSnapshot
    label: str


def snapshot_parameters(parameters):
    snapshot = ParameterSnapshot()
    source = parameters if isinstance(parameters, dict) else vars(parameters)
    for key, value in source.items():
        if key in {"filter", "image_dialog"}:
            continue
        try:
            snapshot[key] = deepcopy(value)
        except Exception:
            snapshot[key] = value
    return snapshot


BASE_FIELDS = {
    "DUT": "DUT",
    "savedir": "savelocation",
    "V_Rating": "Voltage_Rating",
    "I_Rating": "Current_Rating",
    "P_Rating": "Power_Rating",
    "power": "Power",
    "estimatetime": "estimatetime",
    "updatedelay": "updatedelay",
    "readbackvoltage": "readbackvoltage",
    "readbackcurrent": "readbackcurrent",
    "noofloop": "noofloop",
    "Instrument": "DMM_Instrument",
    "Programming_Error_Gain": "Programming_Error_Gain",
    "Programming_Error_Offset": "Programming_Error_Offset",
    "Readback_Error_Gain": "Readback_Error_Gain",
    "Readback_Error_Offset": "Readback_Error_Offset",
    "unit": "unit",
    "minCurrent": "minCurrent",
    "maxCurrent": "maxCurrent",
    "current_step_size": "current_step_size",
    "minVoltage": "minVoltage",
    "maxVoltage": "maxVoltage",
    "voltage_step_size": "voltage_step_size",
    "selected_DUT": "selected_text",
    "PSU": "PSU",
    "DMM": "DMM",
    "ELoad": "ELoad",
    "DAQ": "DAQ",
    "ELoad_Channel": "ELoad_Channel",
    "PSU_Channel": "PSU_Channel",
    "VoltageSense": "VoltageSense",
    "VoltageRes": "VoltageRes",
    "setFunction": "setFunction",
    "OperationMode": "SPOperationMode",
    "DMM_Model": "DMM_Model",
    "ELoad_Model": "ELoad_Model",
    "Hornbill_Measurement_Command": "Hornbill_Measurement_Command",
    "Relay_Control": "Relay_Control",
    "Range": "Range",
    "Aperture": "Aperture",
    "AutoZero": "AutoZero",
    "InputZ": "inputZ",
    "UpTime": "UpTime",
    "DownTime": "DownTime",
}

OSCILLOSCOPE_FIELDS = {
    "OSC_Channel": "OSC_Channel",
    "Channel_CouplingMode": "Channel_CouplingMode",
    "Trigger_Mode": "Trigger_Mode",
    "Trigger_CouplingMode": "Trigger_CouplingMode",
    "Trigger_SweepMode": "Trigger_SweepMode",
    "Trigger_SlopeMode": "Trigger_SlopeMode",
    "Probe_Setting": "Probe_Setting",
    "Acq_Type": "Acq_Type",
    "TimeScale": "TimeScale",
    "VerticalScale": "VerticalScale",
    "V_Settling_Band": "V_Settling_Band",
    "T_Settling_Band": "T_Settling_Band",
    "OSC": "OSC",
}


def _value(parameters, attribute):
    if isinstance(parameters, dict):
        return parameters.get(attribute)
    return getattr(parameters, attribute)


def _add_fields(result, parameters, fields):
    result.update({key: _value(parameters, attribute) for key, attribute in fields.items()})


def build_test_parameters(parameters, selections):
    result = {}
    _add_fields(result, parameters, BASE_FIELDS)

    if (
        selections.get("VoltageAccuracy")
        and selections.get("CurrentStatic(VoltageChange)withOscilloscope")
    ):
        _add_fields(result, parameters, OSCILLOSCOPE_FIELDS)

    if selections.get("Current_Test"):
        _add_fields(result, parameters, {
            "rshunt": "rshunt", "DMM2": "DMM2", "powerfin": "Power"
        })
    if selections.get("OCP_Test"):
        _add_fields(result, parameters, {
            "OCP_Level": "OCP_Level", "OCPActivationTime": "OCPActivationTime"
        })
        _add_fields(result, parameters, OSCILLOSCOPE_FIELDS)
    if selections.get("OVP_Test"):
        _add_fields(result, parameters, {
            "OVP_Level": "OVP_Level",
            "OVP_ErrorGain": "OVP_ErrorGain",
            "OVP_ErrorOffset": "OVP_ErrorOffset",
        })
    if selections.get("TransientRecovery"):
        transient_fields = dict(OSCILLOSCOPE_FIELDS)
        transient_fields["DUT_V_Settling_Band"] = "V_Settling_Band"
        transient_fields["DUT_T_Settling_Band"] = "T_Settling_Band"
        _add_fields(result, parameters, transient_fields)
        result.update({
            "CurrentTrigger_Probe_Setting": 100,
            "CurrentTrigger_OSC_Channel": 2,
            "CurrentTrigger_V_Settling_Band": 6,
        })
    if selections.get("ProgrammingSpeed"):
        _add_fields(result, parameters, OSCILLOSCOPE_FIELDS)
        _add_fields(result, parameters, {
            "Response_Up_NoLoad": "Programming_Response_Up_NoLoad",
            "Response_Up_FullLoad": "Programming_Response_Up_FullLoad",
            "Response_Down_NoLoad": "Programming_Response_Down_NoLoad",
            "Response_Down_FullLoad": "Programming_Response_Down_FullLoad",
        })

    load_fields = {
        "Load_Programming_Error_Gain": "Load_Programming_Error_Gain",
        "Load_Programming_Error_Offset": "Load_Programming_Error_Offset",
    }
    if any(selections.get(name) for name in (
        "VoltageLoadRegulation", "CurrentLoadRegulation",
        "VoltageLineRegulation", "CurrentLineRegulation",
    )):
        _add_fields(result, parameters, load_fields)

    if selections.get("PowerAccuracy"):
        _add_fields(result, parameters, {
            "Power_Programming_Error_Gain": "Power_Programming_Error_Gain",
            "Power_Programming_Error_Offset": "Power_Programming_Error_Offset",
            "Power_Readback_Error_Gain": "Power_Readback_Error_Gain",
            "Power_Readback_Error_Offset": "Power_Readback_Error_Offset",
            "powerini": "powerini",
            "power_step_size": "power_step_size",
        })

    if selections.get("VoltageLineRegulation") or selections.get("CurrentLineRegulation"):
        _add_fields(result, parameters, {
            "ACSource": "ACSource",
            "AC_CurrentLimit": "AC_CurrentLimit",
            "AC_VoltageOutput": "AC_VoltageOutput",
            "Frequency": "Frequency",
            "AC_Supply_Type": "AC_Supply_Type",
            "Line_Reg_Range": "Line_Reg_Range",
        })

    return result


def prepare_run_submission(parameters, selections):
    selection_snapshot = dict(selections)
    parameter_snapshot = snapshot_parameters(parameters)
    configuration = build_test_parameters(parameter_snapshot, selection_snapshot)
    selected_names = [
        name
        for name, enabled in selection_snapshot.items()
        if enabled and name not in {"DataReport", "DataImage"}
    ]
    label = f"{parameter_snapshot.DUT}: " + ", ".join(selected_names)
    return RunSubmission(
        selections=selection_snapshot,
        configuration=configuration,
        parameters=parameter_snapshot,
        label=label,
    )
