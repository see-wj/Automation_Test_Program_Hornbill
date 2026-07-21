"""Measurement CSV, graph, configuration, and workbook export service."""

import os

import pandas as pd

from common.path import csv_folder
from reporting.data import (
    datatoCSV_Accuracy,
    datatoCSV_Accuracy2,
    datatoCSV_PowerAccuracy,
    datatoGraph,
    datatoGraph2,
    datatoGraph3,
    instrumentData,
    powerinstrumentData,
)
from reporting.xlreport import xlreport
from reporting.xlreportpower import xlreportpower
from SCPI_Library.simulation import is_simulation_mode, raise_for_simulation_fault


class MeasurementReportExporter:
    def __init__(self, worker):
        self.worker = worker

    def write_config_csv(self, file_name):
        worker = self.worker
        config_frame = pd.DataFrame.from_dict(worker.dict, orient="index")
        config_frame.index.name = "Parameter"
        config_frame.columns = ["Value"]
        output_directory = (
            worker.run_context.storage.raw if worker.run_context else csv_folder
        )
        config_frame.to_csv(os.path.join(output_directory, file_name))

    @staticmethod
    def _check_report_fault():
        if is_simulation_mode():
            raise_for_simulation_fault("report")

    def export_voltage_accuracy(
        self,
        info_list,
        data_list,
        readback_list,
    ):
        worker = self.worker
        worker._execute_checkpointed(
            instrumentData,
            worker.params["PSU"],
            worker.params["DMM"],
            worker.params["ELoad"],
        )
        worker._execute_checkpointed(
            datatoCSV_Accuracy,
            info_list,
            data_list,
            readback_list,
        )
        graph = worker._execute_checkpointed(
            datatoGraph,
            info_list,
            data_list,
            readback_list,
        )
        worker._execute_checkpointed(
            graph.scatterCompareVoltage,
            float(worker.params["Programming_Error_Gain"]),
            float(worker.params["Programming_Error_Offset"]),
            float(worker.params["Readback_Error_Gain"]),
            float(worker.params["Readback_Error_Offset"]),
            str(worker.params["unit"]),
            float(worker.params["Voltage_Rating"]),
        )
        worker._execute_checkpointed(self.write_config_csv, "config.csv")
        worker._execute_checkpointed(self.save_voltage_report)

    def export_current_accuracy(
        self,
        info_list,
        data_list,
        readback_list,
    ):
        worker = self.worker
        worker._execute_checkpointed(
            instrumentData,
            worker.params["PSU"],
            worker.params["DMM2"],
            worker.params["ELoad"],
        )
        worker._execute_checkpointed(
            datatoCSV_Accuracy2,
            info_list,
            data_list,
            readback_list,
        )
        graph = worker._execute_checkpointed(
            datatoGraph2,
            info_list,
            data_list,
            readback_list,
        )
        worker._execute_checkpointed(
            graph.scatterCompareCurrent2,
            float(worker.params["Programming_Error_Gain"]),
            float(worker.params["Programming_Error_Offset"]),
            float(worker.params["Readback_Error_Gain"]),
            float(worker.params["Readback_Error_Offset"]),
            str(worker.params["unit"]),
            float(worker.params["Current_Rating"]),
        )
        worker._execute_checkpointed(self.write_config_csv, "config.csv")

        report = xlreport(
            save_directory=worker.params["savelocation"],
            file_name=str(worker.params["unit"]),
        )
        self._check_report_fault()
        worker._execute_checkpointed(report.run)
        worker.progress.emit("Excel Report Saved: " + str(worker.params["savedir"]))
        worker.progress.emit("")

    def export_power_accuracy(
        self,
        info_list,
        data_list,
        readback_list,
    ):
        worker = self.worker
        worker._execute_checkpointed(
            powerinstrumentData,
            worker.params["PSU"],
            worker.params["DMM"],
            worker.params["DMM2"],
            worker.params["ELoad"],
        )
        worker._execute_checkpointed(
            datatoCSV_PowerAccuracy,
            info_list,
            data_list,
            readback_list,
        )
        graph = worker._execute_checkpointed(
            datatoGraph3,
            info_list,
            data_list,
            readback_list,
        )
        worker._execute_checkpointed(
            graph.scatterComparePower,
            float(worker.params["Power_Programming_Error_Gain"]),
            float(worker.params["Power_Programming_Error_Offset"]),
            float(worker.params["Power_Readback_Error_Gain"]),
            float(worker.params["Power_Readback_Error_Offset"]),
            str(worker.params["setFunction"]),
            float(worker.params["Power_Rating"]),
        )
        worker._execute_checkpointed(self.write_config_csv, "powerconfig.csv")
        worker._execute_checkpointed(self.save_power_report)

    def save_voltage_report(self):
        worker = self.worker
        file_name = str(worker.params["unit"])
        if is_simulation_mode():
            file_name = f"SIMULATED_{file_name}"
        report = xlreport(
            save_directory=worker.params["savelocation"],
            file_name=file_name,
        )
        self._check_report_fault()
        report.run()
        worker.progress.emit(
            "Excel Report Saved: " + str(worker.params["savelocation"])
        )
        worker.progress.emit("")

    def save_power_report(self):
        worker = self.worker
        file_name = (
            "Power_CV"
            if worker.params["setFunction"] == "Current"
            else "Power_CC"
        )
        if is_simulation_mode():
            file_name = f"SIMULATED_{file_name}"
        report = xlreportpower(
            save_directory=worker.params["savedir"],
            file_name=file_name,
        )
        self._check_report_fault()
        report.run()
        worker.progress.emit("Excel Report Saved: " + str(worker.params["savedir"]))
        worker.progress.emit("")
