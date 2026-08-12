"""Library for Kikusui PLZ334W DC Power Supply SCPI commands."""

import pyvisa
from time import sleep
from SCPI_Library.session_manager import get_visa_resource


class Subsystem(object):
    """Parent Class for every SCPI Commands Subsystem

    Attributes:
        VISA_ADDRESS: The string which contains the VISA Address of an Instrument.
        Channel_Number: An integer which contains the Channel Number of Instrument.
        value: An integer which represents the value of certain parameters (e.g. Voltage, Current, Frequency).
        state: A boolean representing if the function should be enabled or disabled.
    """

    ERROR_QUERY = "SYST:ERR?"

    def __init__(self, VISA_ADDRESS, timeout=None):
        """Initialize the VISA instrument with proper VXI-11 support."""
        self.VISA_ADDRESS = VISA_ADDRESS

        self.instr = get_visa_resource(self.VISA_ADDRESS, timeout)

        # --- Important for VXI-11 ---
        self.instr.write_termination = '\n'
        self.instr.read_termination  = '\n'

        # Recommended: increase buffer if reading large block data
        self.instr.read_buffer_size = 20000


class ELOAD_PLZ334W(Subsystem):
    """Class for Kikusui PLZ334W DC Power Supply SCPI commands."""

    def __init__(self, VISA_ADDRESS, timeout=None):
        """Initialize the VISA instrument with proper VXI-11 support."""
        super().__init__(VISA_ADDRESS, timeout)

    def set_Mode(self, mode):
        """Set the mode of the power supply.

        Args:
            mode: A string representing the mode of the power supply. Can be "CV" or "CC".
        """
        self.instr.write(f"FUNC {mode}")

    def set_Voltage(self, voltage):
        """Set the voltage of the power supply.

        Args:
            voltage: A float representing the voltage to set.
        """
        self.instr.write(f"VOLT {voltage}")

    def set_Current(self, current):
        """Set the current of the power supply.

        Args:
            current: A float representing the current to set.
        """
        self.instr.write(f"CURR {current}")

    def set_Output(self, state):
        """Set the output state of the power supply.

        Args:
            state: A boolean representing if the output should be enabled (True) or disabled (False).
        """
        self.instr.write(f"INP {'ON' if state else 'OFF'}")

    def clearStatus(self):
        self.instr.write("*CLS")

    def queryError(self):
        return self.instr.query("SYST:ERR?")
