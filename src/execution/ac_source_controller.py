"""AC-input supply selection and Keysight 68xx lifecycle control."""

from SCPI_Library.Keysight import AC_Source_68xx


PLUG_SUPPLY = "Plug"
AC_SOURCE_SUPPLY = "AC Source"
SUPPORTED_AC_SUPPLIES = {PLUG_SUPPLY, AC_SOURCE_SUPPLY}


def normalized_ac_supply_type(configuration):
    value = str(configuration.get("AC_Supply_Type", PLUG_SUPPLY)).strip()
    return value or PLUG_SUPPLY


def uses_ac_source(configuration):
    return normalized_ac_supply_type(configuration) == AC_SOURCE_SUPPLY


class ACSourceController:
    def __init__(self, configuration, driver_factory=AC_Source_68xx):
        if not uses_ac_source(configuration):
            raise ValueError("ACSourceController requires AC Supply Type 'AC Source'")
        self.configuration = configuration
        self.driver = driver_factory(configuration["ACSource"])
        self.started = False

    def _check_error(self, operation):
        response = str(self.driver.queryError()).strip()
        code = response.split(",", 1)[0].strip()
        try:
            error_code = int(code)
        except ValueError as exception:
            raise RuntimeError(
                f"AC source returned an invalid error response after {operation}: "
                f"{response}"
            ) from exception
        if error_code != 0:
            raise RuntimeError(f"AC source error after {operation}: {response}")

    def _execute(self, operation, callback, *args):
        callback(*args)
        self._check_error(operation)

    def start(self):
        self.driver.clearStatus()
        self._execute("output disable", self.driver.setOutputState, "OFF")
        self._execute(
            "current limit",
            self.driver.setOutputCurrent,
            float(self.configuration["AC_CurrentLimit"]),
        )
        self._execute(
            "output voltage",
            self.driver.setOutputVoltage,
            float(self.configuration["AC_VoltageOutput"]),
        )
        self._execute(
            "frequency",
            self.driver.setFrequency,
            float(self.configuration["Frequency"]),
        )
        self._execute("output enable", self.driver.setOutputState, "ON")
        self.started = True

    def set_voltage(self, voltage):
        self._execute(
            f"set voltage to {float(voltage):g} V",
            self.driver.setOutputVoltage,
            float(voltage),
        )

    def stop(self):
        try:
            self.driver.setOutputState("OFF")
            self._check_error("output disable")
        finally:
            self.started = False


def set_ac_source_voltage(configuration, voltage):
    if not uses_ac_source(configuration):
        raise RuntimeError(
            "Automated line regulation requires AC Supply Type 'AC Source'"
        )
    controller = ACSourceController(configuration)
    controller.set_voltage(voltage)
