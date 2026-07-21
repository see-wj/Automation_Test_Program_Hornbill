import math
import os
import tempfile


TEST_KEYS = {
    "VoltageAccuracy",
    "CurrentAccuracy",
    "VoltageLoadRegulation",
    "CurrentLoadRegulation",
    "PowerAccuracy",
    "TransientRecovery",
    "OVP_Test",
    "OCP_Test",
    "VoltageLineRegulation",
    "CurrentLineRegulation",
    "ProgrammingSpeed",
}


TEST_INSTRUMENT_REQUIREMENTS = {
    "VoltageAccuracy": {"PSU", "DMM", "ELoad"},
    "CurrentAccuracy": {"PSU", "DMM2", "ELoad"},
    "VoltageLoadRegulation": {"PSU", "DMM", "ELoad"},
    "CurrentLoadRegulation": {"PSU", "DMM2", "ELoad"},
    "PowerAccuracy": {"PSU", "DMM", "DMM2", "ELoad"},
    "TransientRecovery": {"PSU", "ELoad", "OSC"},
    "OVP_Test": {"PSU", "ELoad"},
    "OCP_Test": {"PSU", "ELoad", "OSC"},
    "VoltageLineRegulation": {"PSU", "DMM", "ELoad"},
    "CurrentLineRegulation": {"PSU", "DMM2", "ELoad"},
    "ProgrammingSpeed": {"PSU", "ELoad", "OSC"},
}


SWEEP_TESTS = {
    "VoltageAccuracy",
    "CurrentAccuracy",
    "VoltageLoadRegulation",
    "CurrentLoadRegulation",
    "PowerAccuracy",
}


def selected_tests(checkbox_states):
    return {
        test_name
        for test_name in TEST_KEYS
        if checkbox_states.get(test_name, False)
    }


def required_instruments(checkbox_states, parameters):
    requirements = set()
    for test_name in selected_tests(checkbox_states):
        requirements.update(TEST_INSTRUMENT_REQUIREMENTS[test_name])

    if (
        checkbox_states.get("VoltageAccuracy")
        and checkbox_states.get("CurrentStatic(VoltageChange)withOscilloscope")
    ):
        requirements.add("OSC")

    if (
        checkbox_states.get("VoltageLineRegulation")
        or checkbox_states.get("CurrentLineRegulation")
    ) and parameters.get("AC_Supply_Type") == "AC Source":
        requirements.add("ACSource")

    if checkbox_states.get("Temperature"):
        requirements.add("DAQ")

    return requirements


def _number(parameters, key, errors, *, minimum=None, positive=False):
    value = parameters.get(key)
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{key} must be numeric")
        return None

    if not math.isfinite(number):
        errors.append(f"{key} must be finite")
    elif positive and number <= 0:
        errors.append(f"{key} must be greater than zero")
    elif minimum is not None and number < minimum:
        errors.append(f"{key} must be at least {minimum}")
    return number


def _validate_output_directory(path, errors):
    if not path:
        errors.append("savedir is required")
        return
    if not os.path.isdir(path):
        errors.append(f"Output directory does not exist: {path}")
        return

    try:
        with tempfile.NamedTemporaryFile(dir=path, prefix="hornbill_", delete=True):
            pass
    except OSError as exception:
        errors.append(f"Output directory is not writable: {exception}")


def _validate_channel(parameters, key, errors):
    value = parameters.get(key)
    values = value if isinstance(value, (range, list, tuple)) else [value]
    if not values:
        errors.append(f"{key} must contain at least one channel")
        return

    for channel in values:
        try:
            channel_number = int(channel)
        except (TypeError, ValueError):
            errors.append(f"{key} must be a positive channel number")
            return
        if channel_number <= 0:
            errors.append(f"{key} must be a positive channel number")
            return


def validate_preflight(parameters, checkbox_states):
    errors = []
    tests = selected_tests(checkbox_states)
    if not tests:
        errors.append("Select at least one test")

    _validate_output_directory(parameters.get("savedir"), errors)

    loop_count = _number(parameters, "noofloop", errors, positive=True)
    if loop_count is not None and not loop_count.is_integer():
        errors.append("noofloop must be a whole number")
    _number(parameters, "updatedelay", errors, minimum=0)

    if tests & SWEEP_TESTS:
        minimum_voltage = _number(parameters, "minVoltage", errors, minimum=0)
        maximum_voltage = _number(parameters, "maxVoltage", errors, minimum=0)
        minimum_current = _number(parameters, "minCurrent", errors, minimum=0)
        maximum_current = _number(parameters, "maxCurrent", errors, minimum=0)
        _number(parameters, "voltage_step_size", errors, positive=True)
        _number(parameters, "current_step_size", errors, positive=True)

        if None not in (minimum_voltage, maximum_voltage) and minimum_voltage > maximum_voltage:
            errors.append("minVoltage cannot exceed maxVoltage")
        if None not in (minimum_current, maximum_current) and minimum_current > maximum_current:
            errors.append("minCurrent cannot exceed maxCurrent")

    if checkbox_states.get("CurrentAccuracy") or checkbox_states.get("PowerAccuracy"):
        _number(parameters, "rshunt", errors, positive=True)
    if checkbox_states.get("PowerAccuracy"):
        _number(parameters, "power_step_size", errors, positive=True)
    if checkbox_states.get("OVP_Test"):
        _number(parameters, "OVP_Level", errors, positive=True)
        _number(parameters, "OVP_ErrorGain", errors)
        _number(parameters, "OVP_ErrorOffset", errors)
    if checkbox_states.get("OCP_Test"):
        _number(parameters, "OCP_Level", errors, positive=True)
        _number(parameters, "OCPActivationTime", errors, positive=True)

    oscilloscope_tests = {
        "TransientRecovery",
        "ProgrammingSpeed",
        "OCP_Test",
    }
    if tests & oscilloscope_tests:
        _number(parameters, "TimeScale", errors, positive=True)
        _number(parameters, "VerticalScale", errors, positive=True)

    if checkbox_states.get("ProgrammingSpeed"):
        for key in (
            "Response_Up_NoLoad",
            "Response_Up_FullLoad",
            "Response_Down_NoLoad",
            "Response_Down_FullLoad",
        ):
            _number(parameters, key, errors, minimum=0)

    operational_limit_tests = oscilloscope_tests | {
        "VoltageLoadRegulation",
        "CurrentLoadRegulation",
        "VoltageLineRegulation",
        "CurrentLineRegulation",
    }
    if tests & (oscilloscope_tests | {"VoltageLineRegulation", "CurrentLineRegulation"}):
        _number(parameters, "maxVoltage", errors, positive=True)
        _number(parameters, "maxCurrent", errors, positive=True)
    if tests & operational_limit_tests:
        _number(parameters, "V_Rating", errors, positive=True)
        _number(parameters, "I_Rating", errors, positive=True)
        _number(parameters, "P_Rating", errors, positive=True)

    numeric_tolerances = set()
    if checkbox_states.get("VoltageAccuracy") or checkbox_states.get("CurrentAccuracy"):
        numeric_tolerances.update({
            "Programming_Error_Gain",
            "Programming_Error_Offset",
            "Readback_Error_Gain",
            "Readback_Error_Offset",
        })
    if tests & {
        "VoltageLoadRegulation",
        "CurrentLoadRegulation",
        "VoltageLineRegulation",
        "CurrentLineRegulation",
    }:
        numeric_tolerances.update({
            "Load_Programming_Error_Gain",
            "Load_Programming_Error_Offset",
        })
    if checkbox_states.get("PowerAccuracy"):
        numeric_tolerances.update({
            "Power_Programming_Error_Gain",
            "Power_Programming_Error_Offset",
            "Power_Readback_Error_Gain",
            "Power_Readback_Error_Offset",
        })
    for key in sorted(numeric_tolerances):
        _number(parameters, key, errors)

    requirements = required_instruments(checkbox_states, parameters)
    if "PSU" in requirements:
        _validate_channel(parameters, "PSU_Channel", errors)
    if "ELoad" in requirements:
        _validate_channel(parameters, "ELoad_Channel", errors)
    if "OSC" in requirements:
        _validate_channel(parameters, "OSC_Channel", errors)

    addresses = {}
    for role in sorted(requirements):
        address = parameters.get(role)
        if not isinstance(address, str) or not address.strip():
            errors.append(f"{role} VISA address is required")
            continue
        address = address.strip()
        if "::" not in address:
            errors.append(f"{role} VISA address is invalid: {address}")
        if address in addresses:
            errors.append(
                f"{role} and {addresses[address]} use the same VISA address"
            )
        else:
            addresses[address] = role

    return errors, requirements
