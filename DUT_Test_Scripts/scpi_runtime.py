"""Shared SCPI import, VISA discovery, and execution-control helpers."""

from importlib import import_module

import pyvisa

from SCPI_Library.visa_config import configure_visa_resource


KEYSIGHT_BASE_CLASSES = (
    "Read", "Apply", "Display", "Function", "Frequency", "Output", "Measure",
    "Sense", "Configure", "Delay", "Trigger", "Sample", "Initiate", "Fetch",
    "Status", "Voltage", "Current", "Oscilloscope", "Excavator",
)
DOLPHIN_CLASSES = (*KEYSIGHT_BASE_CLASSES, "SMU", "Power")
HORNBILL_KEYSIGHT_CLASSES = (
    *KEYSIGHT_BASE_CLASSES,
    "Power",
    "Hornbill",
    "SMU_N67XX",
    "DMM_344XXA",
    "DMM_3458A",
    "ELOAD_E367XXA",
)
CHROMA_CLASSES = ("Channel", "Mode", "Voltage")


def load_scpi_classes(module_name, class_names):
    module = import_module(f"SCPI_Library.{module_name}")
    return tuple(getattr(module, class_name) for class_name in class_names)


class DictGenerator:
    @staticmethod
    def input(**kwargs):
        return kwargs


class DolphinDimport:
    @staticmethod
    def getClasses(module_name):
        return load_scpi_classes(module_name, DOLPHIN_CLASSES)


class HornbillDimport:
    @staticmethod
    def getClasses_Keysight(module_name):
        return load_scpi_classes(module_name, HORNBILL_KEYSIGHT_CLASSES)

    @staticmethod
    def getClasses(module_name):
        classes = HornbillDimport.getClasses_Keysight(module_name)
        return (*classes[:19], classes[21], classes[19], classes[20])

    @staticmethod
    def getClasses_Chroma(module_name):
        return load_scpi_classes(module_name, CHROMA_CLASSES)


class VisaResourceManager:
    def __init__(self, resource_manager_factory=None):
        factory = resource_manager_factory or pyvisa.ResourceManager
        self.rm = factory()

    def openRM(self, *addresses):
        try:
            for address in addresses:
                instrument = configure_visa_resource(
                    self.rm.open_resource(address)
                )
                instrument.baud_rate = 9600
            return 1, None
        except pyvisa.VisaIOError as exception:
            print(exception.args)
            return 0, exception.args

    def closeRM(self):
        self.rm.close()


def execution_checkpoint(worker):
    if worker is not None:
        worker.checkpoint()
