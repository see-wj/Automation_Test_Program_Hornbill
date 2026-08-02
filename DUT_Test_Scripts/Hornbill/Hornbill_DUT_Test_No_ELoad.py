"""Hornbill voltage-accuracy measurement without an electronic load."""

import math
from datetime import datetime
from pathlib import Path

from DUT_Test_Scripts.execution_control import sleep
from DUT_Test_Scripts.scpi_runtime import (
    HornbillDimport as Dimport,
    execution_checkpoint,
)
from DUT_Test_Scripts.Hornbill.Hornbill_DUT_Test_With_ELoad import (
    _measure_hornbill_readback,
)
from SCPI_Library.IEEEStandard import RST, TRG, WAI


def _percentage_of_limit(error, upper_limit):
    if upper_limit == 0:
        return 0.0 if error == 0 else float("inf")
    return (error / upper_limit) * 100.0


class HornbillVoltageMeasurementNoELoad:
    """Run the Hornbill voltage sweep at the natural no-load current."""

    def __init__(self):
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    @staticmethod
    def _configure_dmm(configuration, classes):
        Sense = classes[7]
        DMM_344XXA = classes[22]
        DMM_3458A = classes[23]
        model = configuration["DMM_Model"]
        if model == "344xxA":
            dmm = DMM_344XXA(configuration["DMM"])
            dmm.setNPLC(configuration["Aperture"])
            dmm.setAutoZeroMode(configuration["AutoZero"])
            dmm.setAutoImpedanceMode(configuration["InputZ"])
            dmm.setConfiguration("VOLT")
            dmm.setTriggerSource("BUS")
            dmm.setVoltageResolutionDC("HIGH")
            if configuration["Range"] == "Auto":
                Sense(configuration["DMM"]).setVoltageRangeDCAuto()
            else:
                Sense(configuration["DMM"]).setVoltageRangeDC(
                    configuration["Range"]
                )
            return dmm
        if model == "3458A":
            dmm = DMM_3458A(configuration["DMM"])
            dmm.setDCV(configuration["Range"])
            dmm.setTriggerArm()
            dmm.setNPLC(configuration["Aperture"])
            dmm.setNumberOfReadings()
            dmm.disableMemory()
            dmm.setEndCondition()
            dmm.setDigits()
            dmm.setAutoZeroMode(configuration["AutoZero"])
            dmm.enableDisplay()
            return dmm
        raise ValueError(f"Unsupported DMM model: {model}")

    @staticmethod
    def _measure_dmm(configuration, dmm, worker):
        if configuration["DMM_Model"] == "3458A":
            return float(dmm.queryMeasurement())

        dmm.initiate()
        TRG(configuration["DMM"])
        while True:
            execution_checkpoint(worker)
            status = float(dmm.operationCondition())
            if status in {512.0, 8192.0, 8704.0}:
                return float(dmm.instr.query("FETC?"))
            sleep(0.05)

    @staticmethod
    def _close_wrapper(instrument):
        try:
            if instrument is not None and getattr(instrument, "instr", None) is not None:
                instrument.instr.close()
        except Exception:
            pass

    @staticmethod
    def _capture_scope_screenshot(
        oscilloscope,
        configuration,
        channel,
        set_voltage,
        set_current,
    ):
        oscilloscope.run()
        sleep(1)
        oscilloscope.stop()
        image_data = bytes(oscilloscope.read_binary_data())
        if image_data.startswith(b"#") and len(image_data) >= 2:
            header_digits = int(image_data[1:2])
            payload_start = 2 + header_digits
            image_data = image_data[payload_start:]

        output_directory = Path(configuration["savedir"])
        output_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
        image_path = output_directory / (
            f"CH{channel}_{set_voltage:g}V_{set_current:g}A_"
            f"NO_ELOAD_{timestamp}.png"
        )
        image_path.write_bytes(image_data)
        return image_path

    def Execute_Voltage_Accuracy_Current_Static(
        self,
        configuration,
        channel,
        worker=None,
        capture_oscilloscope=False,
    ):
        """Sweep voltage once per loop with no programmed load current."""
        classes = Dimport.getClasses_Keysight(configuration["Instrument"])
        Hornbill = classes[20]
        psu = None
        dmm = None
        oscilloscope = None
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

        programming_gain = float(configuration["Programming_Error_Gain"])
        programming_offset = float(configuration["Programming_Error_Offset"])
        readback_gain = float(configuration["Readback_Error_Gain"])
        readback_offset = float(configuration["Readback_Error_Offset"])
        minimum_voltage = float(configuration["minVoltage"])
        maximum_voltage = float(configuration["maxVoltage"])
        voltage_step = float(configuration["voltage_step_size"])
        updatedelay = float(configuration["updatedelay"])
        voltage_iterations = math.ceil(
            ((maximum_voltage - minimum_voltage) / voltage_step) + 1
        )
        no_load_current = 0.0

        try:
            psu = Hornbill(configuration["PSU"])
            psu.setMode("VOLTAGE", channel)
            psu.setVoltageSweepPoints(
                channel,
                configuration.get(
                    "SweepPoints", Hornbill.DEFAULT_VOLTAGE_SAMPLE_COUNT
                ),
            )
            psu.senseVoltageSource(configuration["VoltageSense"], channel)
            psu.sourCurrentLimitPOS("MAXimum", channel)
            psu.sourCurrentLimitNEG("MINimum", channel)
            psu.outputState("ON", channel)
            dmm = HornbillVoltageMeasurementNoELoad._configure_dmm(
                configuration, classes
            )
            if capture_oscilloscope:
                Oscilloscope = classes[17]
                oscilloscope = Oscilloscope(configuration["OSC"])

            print(f"Channel {channel} No-ELoad Test Running\n")
            for point_index in range(voltage_iterations):
                execution_checkpoint(worker)
                set_voltage = min(
                    minimum_voltage + point_index * voltage_step,
                    maximum_voltage,
                )
                psu.sourVoltageLevelImmediateAmplitude(set_voltage, channel)
                WAI(configuration["PSU"])
                sleep(updatedelay)

                voltage_monitor, current_monitor, voltage_local = (
                    _measure_hornbill_readback(psu, configuration, channel)
                )
                measured_voltage = HornbillVoltageMeasurementNoELoad._measure_dmm(
                    configuration, dmm, worker
                )
                programming_error = measured_voltage - set_voltage
                readback_error = voltage_monitor - measured_voltage
                programming_upper = (
                    set_voltage * programming_gain + programming_offset
                )
                readback_upper = set_voltage * readback_gain + readback_offset

                self.infoList.append(
                    [set_voltage, no_load_current, point_index]
                )
                self.dataList.append([measured_voltage, 0])
                self.dataList2.append(
                    [voltage_monitor, current_monitor, voltage_local]
                )

                if oscilloscope is not None:
                    execution_checkpoint(worker)
                    screenshot = (
                        HornbillVoltageMeasurementNoELoad._capture_scope_screenshot(
                            oscilloscope,
                            configuration,
                            channel,
                            set_voltage,
                            no_load_current,
                        )
                    )
                    print(f"Screenshot saved at: {screenshot}")

                if worker is not None:
                    programming_percent = _percentage_of_limit(
                        programming_error, programming_upper
                    )
                    readback_percent = _percentage_of_limit(
                        readback_error, programming_upper
                    )
                    worker.new_data.emit(
                        set_voltage,
                        no_load_current,
                        voltage_monitor,
                        measured_voltage,
                        current_monitor,
                        programming_error,
                        readback_error,
                        programming_percent,
                        readback_percent,
                        programming_upper,
                        -programming_upper,
                        readback_upper,
                        -readback_upper,
                        100.0,
                        -100.0,
                    )

            return self.infoList, self.dataList, self.dataList2
        finally:
            if psu is not None:
                try:
                    psu.sourVoltageLevelImmediateAmplitude(0, channel)
                    psu.sourCurrentLimitPOS("MIN", channel)
                    psu.outputState("OFF", channel)
                except Exception:
                    pass
            if dmm is not None:
                try:
                    RST(configuration["DMM"])
                except Exception:
                    pass
            HornbillVoltageMeasurementNoELoad._close_wrapper(dmm)
            HornbillVoltageMeasurementNoELoad._close_wrapper(psu)
            HornbillVoltageMeasurementNoELoad._close_wrapper(oscilloscope)

    def Execute_Voltage_Accuracy(self, configuration, channel, worker=None):
        """Backward-compatible entry point for the original no-load script."""
        return self.Execute_Voltage_Accuracy_Current_Static(
            configuration, channel, worker=worker
        )


class HornbillVoltageMeasurementNoELoadWithOscilloscope:
    """No-load Hornbill voltage sweep with a screenshot at every point."""

    def Execute_Voltage_Accuracy_Current_Static(
        self, configuration, channel, worker=None
    ):
        return HornbillVoltageMeasurementNoELoad.Execute_Voltage_Accuracy_Current_Static(
            self,
            configuration,
            channel,
            worker=worker,
            capture_oscilloscope=True,
        )
