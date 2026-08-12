"""Hornbill PSU voltage calibration using a Keysight 34470A DMM."""

from instruments.TestVolt_HB_3458 import (
    CalWorker as BaseCalibrationWorker,
    VoltageCalibrationDialog as BaseVoltageCalibrationDialog,
)


class CalWorker(BaseCalibrationWorker):
    """Run the Hornbill P1/P2 voltage calibration with modern SCPI."""

    DMM_LABEL = "34470A"

    def _configure_dmm(self, dmm):
        commands = (
            "*CLS",
            "*RST",
            "CONF:VOLT:DC 10",
            "SENS:VOLT:DC:NPLC 100",
            "SENS:VOLT:DC:ZERO:AUTO ON",
            "TRIG:SOUR IMM",
            "SAMP:COUN 1",
        )
        for command in commands:
            self._write(dmm, command, delay=0)

    def _set_dmm_range(self, dmm, dmm_range):
        self._write(dmm, f"SENS:VOLT:DC:RANG {dmm_range}", delay=0)

    def _measure_dmm(self, dmm):
        self._checkpoint()
        reading = dmm.query("READ?").strip()
        try:
            float(reading)
        except ValueError as exception:
            raise RuntimeError(
                f"Invalid 34470A reading: {reading!r}"
            ) from exception
        return reading


class VoltageCalibrationDialog(BaseVoltageCalibrationDialog):
    WORKER_CLASS = CalWorker
    DMM_LABEL = "34470A"
    DEFAULT_DMM_ADDRESS = "USB0::0x2A8D::0x0501::MY57702180::0::INSTR"
