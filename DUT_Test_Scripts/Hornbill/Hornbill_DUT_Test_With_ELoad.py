""" Module containing all of the test options available in this program. 

    The tests are categorized into different classes. 
    Notes: Tests RiseFallTime & ProgrammingSpeed are only compatible with
    certain Oscilloscopes using the Keysight Library. Hence, the default 
    library is only set to Keysight

"""
import numpy as np
import os
import pyvisa 
from pyvisa import VisaIOError
import sys
import csv
import pandas as pd
from datetime import datetime
from time import time
from DUT_Test_Scripts.execution_control import sleep
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SCPI_Library.IEEEStandard import OPC, WAI, TRG, RST, CLS
from SCPI_Library.Keysight import *
from SCPI_Library.Chroma import *
from DUT_Test_Scripts.scpi_runtime import (
    DictGenerator as dictGenerator,
    HornbillDimport as Dimport,
    VisaResourceManager,
    execution_checkpoint as _execution_checkpoint,
)


def _measure_hornbill_readback(psu, configuration, channel, current_input="FULL"):
    command_mode = configuration.get("Hornbill_Measurement_Command", "DIAG")
    voltage = psu.measureReadbackVoltage(channel, mode=command_mode)
    current = psu.measureReadbackCurrent(
        channel,
        mode=command_mode,
        diagnostic_input=current_input,
    )
    return voltage, current


def _start_keysight_eload(eload, configuration):
    initial_current = max(0.0, float(configuration["minCurrent"]))
    eload.setOutputCurrent(initial_current)
    WAI(configuration["ELoad"])
    eload.setOutputState("ON")
    WAI(configuration["ELoad"])


######################################################################
class HornbillVoltageMeasurementwithELoad:

    def __init__(self):
        self.results = []
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    def Execute_Voltage_Accuracy_Current_Static(self,dict,channel, worker=None):
        (
            Read,
            Apply,
            Display,
            Function,
            Frequency,
            Output,
            Measure,
            Sense,
            Configure,
            Delay,
            Trigger,
            Sample,
            Initiate,
            Fetch,
            Status,
            Voltage,
            Current,
            Oscilloscope,
            Excavator,
            Power,
            Hornbill,
            SMU_N67XX,
            DMM_344XXA,
            DMM_3458A,
            ELOAD_E367XXA,
        ) = Dimport.getClasses_Keysight(dict["Instrument"])

        (
            Channel,
            Mode,
            Voltage,
        ) = Dimport.getClasses_Chroma("Chroma")

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #Assign Instrument Object and Initialize the Instrument based on the VISA Address given in GUI
        psu = Hornbill(dict["PSU"])
        psu.setMode("VOLTAGE", ch)
        psu.senseVoltageSource(dict["VoltageSense"], ch)
        psu.sourCurrentLimitPOS("MAXimum", ch)         #Current LIMIT (Max for Voltage Accuracy)
        psu.sourCurrentLimitNEG("MINimum", ch)         #Current LIMIT (Max for Voltage Accuracy)
        psu.outputState("ON", ch) #Turn On the PSU and Eload
       
       
        #Set Series/Parallel Mode
        if dict["OperationMode"] == "Series":
            Output(dict["PSU"]).SPModeConnection("SER")
            WAI(dict["PSU"])
        elif dict["OperationMode"] == "Parallel":
            Output(dict["PSU"]).SPModeConnection("PAR")
            WAI(dict["PSU"])
        else:
            Output(dict["PSU"]).SPModeConnection("OFF")
            WAI(dict["PSU"])

        if dict["DMM_Model"] == "344xxA":
            dmm = DMM_344XXA(dict["DMM"])
            dmm.setNPLC(dict["Aperture"])
            dmm.setAutoZeroMode(dict["AutoZero"])
            dmm.setAutoImpedanceMode(dict["InputZ"])
            dmm.setConfiguration("VOLT")
            dmm.setTriggerSource("BUS")
            dmm.setVoltageResolutionDC("HIGH")

            if dict["Range"] == "Auto":
                Sense(dict["DMM"]).setVoltageRangeDCAuto()
            else:
                Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])

        elif dict["DMM_Model"] == "3458A":
            dmm = DMM_3458A(dict["DMM"])
            dmm.setDCV("AUTO")
            dmm.setTriggerArm()
            dmm.setNPLC(dict["Aperture"])
            dmm.setNumberOfReadings()
            dmm.disableMemory()
            dmm.setEndCondition()
            dmm.setDigits()
            dmm.enableAutoZero()
            dmm.enableDisplay()
        
        if dict["ELoad_Model"] == "E367XXA":
            eload = ELOAD_E367XXA(dict["ELoad"])
            _start_keysight_eload(eload, dict)
            
            
        elif dict["ELoad_Model"] == "Chroma":
            eload = ELOAD_E63200A(dict["ELoad"])

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        #Programming Parameters
        self.param1 = float(dict["Programming_Error_Gain"])
        self.param2 = float(dict["Programming_Error_Offset"])
        self.param3 = float(dict["Readback_Error_Gain"])
        self.param4 = float(dict["Readback_Error_Offset"])
        self.unit = dict["unit"]
        self.updatedelay = float(dict["updatedelay"])

        #Set Program Loop Using Step Size
        self.Power = float(dict["power"])
        i = 0   #Current Iteration
        j = 0   #Voltage Iteration
        k = 0   #Step of Iteration
        I_fixed = float(dict["minCurrent"])         #Min Current
        V = float(dict["minVoltage"])
        I = float(dict["maxVoltage"]) + 1
        current_iter = (
            (float(dict["maxCurrent"]) - float(dict["minCurrent"]))
            / float(dict["current_step_size"])
        ) + 1
        voltage_iter = (
            (float(dict["maxVoltage"]) - float(dict["minVoltage"]))
            / float(dict["voltage_step_size"])
        ) + 1
  

        #Run Test (Voltage Loop in Current Loop)
        while i < current_iter:
            _execution_checkpoint(worker)
            j = 0
            V = float(dict["minVoltage"])
            psu.sourVoltageLevelImmediateAmplitude(float(dict["minVoltage"]), ch)
            Iset = dict["maxCurrent"]
            WAI(dict["PSU"])

            if I_fixed > float(dict["maxCurrent"]):
                I_fixed= float(dict["maxCurrent"])

            #If PSU MAX I = ELOAD MAX I (Reduce Eload I by 0.1 - Prevent Overload)
            if I_fixed == float(dict["maxCurrent"]) and Iset == float(dict["maxCurrent"]):
                if dict["ELoad_Model"] == "E367XXA":
                    eload.setOutputCurrent(I_fixed - 0.1)
                    WAI(dict["ELoad"])
                elif dict["ELoad_Model"] == "Chroma":
                    eload.setOutputCurrent(I_fixed - 0.1)
                    WAI(dict["ELoad"])
            else:
                if dict["ELoad_Model"] == "E367XXA":
                    eload.setOutputCurrent(I_fixed)
                    WAI(dict["ELoad"])
                elif dict["ELoad_Model"] == "Chroma":
                    eload.setOutputCurrent(I_fixed)
                    WAI(dict["ELoad"])


            #Voltage Iteration
            while j < voltage_iter:
                _execution_checkpoint(worker)
                #Set Voltage and Current
                if V > float(dict["maxVoltage"]):
                    V = float(dict["maxVoltage"])
                    
                psu.sourVoltageLevelImmediateAmplitude(V, ch)
                WAI(dict["PSU"])
                self.infoList.insert(k, [V, I_fixed, i])

                sleep(float(self.updatedelay))

                #Readback Voltage and Current
                cleandiagVmon, cleandiagImon = _measure_hornbill_readback(
                    psu, dict, ch
                )
                print("Voltage Monitor Reading =", cleandiagVmon)
                print("Current Monitor Reading =", cleandiagImon)

                self.dataList2.insert(k, [float(cleandiagVmon), float(cleandiagImon)])
               
                
                if dict["DMM_Model"] == "344xxA":
                    #INIT DMM (Trigger Measurement)
                    dmm.initiate()
                    status = float(dmm.operationCondition())
                    TRG(dict["DMM"])
                    while 1:
                        _execution_checkpoint(worker)
                        status = float(Status(dict["DMM"]).operationCondition())
                        
                        #Measure Voltage with Error Flag Rised
                        if status == 8704.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break
                        
                        #Measrue Voltage with Normal Condition
                        elif status == 512.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break
                        elif status == 8192.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break

                elif dict["DMM_Model"] == "3458A":
                    # Read current from 3485A DMM
                    voltagemeasured = float(dmm.queryMeasurement())
                    self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                    )
                
                if worker is not None:
                    prog_percent = (voltagemeasured - V)/V*100
                    read_percent = (cleandiagVmon - voltagemeasured)/voltagemeasured*100
                    prog_upper_bound = (V*self.param1) + self.param2
                    prog_lower_bound = -prog_upper_bound
                    read_upper_bound = (V*self.param3) + self.param4
                    read_lower_bound = -read_upper_bound
                    perc_up_bound = 100
                    perc_low_bound = -100
                    worker.new_data.emit(V, I_fixed, cleandiagVmon, voltagemeasured, cleandiagImon, voltagemeasured - V, \
                                         cleandiagVmon - voltagemeasured, prog_percent, read_percent, prog_upper_bound, prog_lower_bound, \
                                        read_upper_bound, read_lower_bound, perc_up_bound, perc_low_bound)
                    worker.popup_data.emit(voltagemeasured - V, cleandiagVmon - voltagemeasured, prog_upper_bound, prog_lower_bound, \
                                           read_upper_bound, read_lower_bound, prog_percent, read_percent, perc_up_bound, perc_low_bound)
                

                #Increment of Steps
                #Delay(dict["PSU"]).write(dict["DownTime"])
                V += float(dict["voltage_step_size"])
                j += 1
                k += 1

                #Ensure the DUT won't exceed the power limit set
                powermeasure = float (V * I_fixed)
                if powermeasure > self.Power:
                    break

            I_fixed += float(dict["current_step_size"])
            i += 1


        psu.sourVoltageLevelImmediateAmplitude(3, ch)
        WAI(dict["PSU"])
        psu.sourCurrentLimitPOS("MIN", ch)
        WAI(dict["PSU"])
       
        RST(dict["ELoad"])
        RST(dict["DMM"])
        RST(dict["PSU"])


        # Wrapper classes hold the real PyVISA session in .instr
        for instrument in (psu, dmm, eload):
            try:
                if instrument is not None and hasattr(instrument, "instr") and instrument.instr is not None:
                    instrument.instr.close()
            except Exception:
                pass


        return self.infoList, self.dataList, self.dataList2
    
    def Execute_Voltage_Accuracy_Current_Change(self,dict,channel, worker=None):
        (
            Read,
            Apply,
            Display,
            Function,
            Frequency,
            Output,
            Measure,
            Sense,
            Configure,
            Delay,
            Trigger,
            Sample,
            Initiate,
            Fetch,
            Status,
            Voltage,
            Current,
            Oscilloscope,
            Excavator,
            Power,
            Hornbill,
            SMU_N67XX,
            DMM_344XXA,
            DMM_3458A,
            ELOAD_E367XXA,
        ) = Dimport.getClasses_Keysight(dict["Instrument"])

        (
            Channel,
            Mode,
            Voltage,
        ) = Dimport.getClasses_Chroma("Chroma")

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #Assign Instrument Object and Initialize the Instrument based on the VISA Address given in GUI
        psu = Hornbill(dict["PSU"])
        psu.setMode("VOLTAGE", ch)
        psu.senseVoltageSource(dict["VoltageSense"], ch)
        psu.sourCurrentLimitPOS("MAXimum", ch)         #Current LIMIT (Max for Voltage Accuracy)
        psu.outputState("ON", ch) #Turn On the PSU and Eload

        #Set Series/Parallel Mode
        if dict["OperationMode"] == "Series":
            Output(dict["PSU"]).SPModeConnection("SER")
            WAI(dict["PSU"])
        elif dict["OperationMode"] == "Parallel":
            Output(dict["PSU"]).SPModeConnection("PAR")
            WAI(dict["PSU"])
        else:
            Output(dict["PSU"]).SPModeConnection("OFF")
            WAI(dict["PSU"])

        if dict["DMM_Model"] == "344xxA":
            dmm = DMM_344XXA(dict["DMM"])
            dmm.setNPLC(dict["Aperture"])
            dmm.setAutoZeroMode(dict["AutoZero"])
            dmm.setAutoImpedanceMode(dict["InputZ"])
            dmm.setConfiguration("VOLT")
            dmm.setTriggerSource("BUS")
            dmm.setVoltageResolutionDC("HIGH")

            if dict["Range"] == "Auto":
                Sense(dict["DMM"]).setVoltageRangeDCAuto()
            else:
                Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])

        elif dict["DMM_Model"] == "3458A":
            dmm = DMM_3458A(dict["DMM"])
            dmm.setDCV("AUTO")
            dmm.setTriggerArm()
            dmm.setNPLC(dict["Aperture"])
            dmm.setNumberOfReadings()
            dmm.disableMemory()
            dmm.setEndCondition()
            dmm.setDigits()
            dmm.enableAutoZero()
            dmm.enableDisplay()
        
        if dict["ELoad_Model"] == "E367XXA":
            eload = ELOAD_E367XXA(dict["ELoad"])
            _start_keysight_eload(eload, dict)
            
            
        elif dict["ELoad_Model"] == "Chroma":
            eload = ELOAD_E63200A(dict["ELoad"])

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        #Programming Parameters
        self.param1 = float(dict["Programming_Error_Gain"])
        self.param2 = float(dict["Programming_Error_Offset"])
        self.param3 = float(dict["Readback_Error_Gain"])
        self.param4 = float(dict["Readback_Error_Offset"])
        self.unit = dict["unit"]
        self.updatedelay = float(dict["updatedelay"])

        #Set Program Loop Using Step Size
        self.Power = float(dict["power"])
        i = 0   #Current Iteration
        j = 0   #Voltage Iteration
        k = 0   #Step of Iteration
        I_fixed = float(dict["minCurrent"])         #Min Current
        V = float(dict["minVoltage"])
        I = float(dict["maxVoltage"]) + 1
        current_iter = (
            (float(dict["maxCurrent"]) - float(dict["minCurrent"]))
            / float(dict["current_step_size"])
        ) + 1
        voltage_iter = (
            (float(dict["maxVoltage"]) - float(dict["minVoltage"]))
            / float(dict["voltage_step_size"])
        ) + 1
        sleep(1)
        
    
        #Voltage Iteration
        while j < voltage_iter:
            _execution_checkpoint(worker)
            i=0
            I_fixed = float(dict["minCurrent"])
            eload.setOutputCurrent(I_fixed)

            WAI(dict["ELoad"])
            #Set Voltage and Current
            if V > float(dict["maxVoltage"]):
                V = float(dict["maxVoltage"])
            psu.sourVoltageLevelImmediateAmplitude(V, ch)
            WAI(dict["PSU"])
            self.infoList.insert(k, [V, I_fixed, i])

            sleep(float(self.updatedelay))

            #Readback Voltage and Current
            cleandiagVmon, cleandiagImon = _measure_hornbill_readback(
                psu, dict, ch
            )
            print("Voltage Monitor Reading =", cleandiagVmon)
            print("Current Monitor Reading =", cleandiagImon)

            sleep(1)
            self.dataList2.insert(k, [float(cleandiagVmon), float(cleandiagImon)])
            
        
            while i < current_iter:
                _execution_checkpoint(worker)
                Iset = dict["maxCurrent"]
                sleep(2)
                WAI(dict["PSU"])

                if I_fixed > float(dict["maxCurrent"]):
                    I_fixed= float(dict["maxCurrent"])

                if dict["ELoad_Model"] == "E367XXA":
                    #If PSU MAX I = ELOAD MAX I (Reduce Eload I by 0.1 - Prevent Overload)
                    if I_fixed == float(dict["maxCurrent"]) and Iset == float(dict["maxCurrent"]):
                        eload.setOutputCurrent(I_fixed - 0.1)
                        WAI(dict["ELoad"])

                    else:
                        eload.setOutputCurrent(max(0.0, I_fixed - 0.001))
                        WAI(dict["ELoad"])

                elif dict["ELoad_Model"] == "Chroma":
                    #If PSU MAX I = ELOAD MAX I (Reduce Eload I by 0.1 - Prevent Overload)
                    if I_fixed == float(dict["maxCurrent"]) and Iset == float(dict["maxCurrent"]):
                        Current(dict["ELoad"]).setOutputCurrent(I_fixed - 0.001)
                        WAI(dict["ELoad"])

                    else:
                        Current(dict["ELoad"]).setOutputCurrent(
                            max(0.0, I_fixed - 0.001)
                        )
                        WAI(dict["ELoad"])

                sleep(1)

                if dict["DMM_Model"] == "344xxA":
                    #INIT DMM (Trigger Measurement)
                    dmm.initiate()
                    status = float(dmm.operationCondition())
                    TRG(dict["DMM"])
                    while 1:
                        _execution_checkpoint(worker)
                        status = float(Status(dict["DMM"]).operationCondition())
                        
                        #Measure Voltage with Error Flag Rised
                        if status == 8704.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break
                        
                        #Measrue Voltage with Normal Condition
                        elif status == 512.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break
                        elif status == 8192.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break

                elif dict["DMM_Model"] == "3458A":
                    # Read current from 3485A DMM
                    voltagemeasured = float(dmm.queryMeasurement())
                    self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                    )
                
                if worker is not None:
                    prog_percent = (voltagemeasured - V)/V*100
                    read_percent = (cleandiagVmon - voltagemeasured)/voltagemeasured*100
                    prog_upper_bound = (V*self.param1) + self.param2
                    prog_lower_bound = -prog_upper_bound
                    read_upper_bound = (V*self.param3) + self.param4
                    read_lower_bound = -read_upper_bound
                    perc_up_bound = 100
                    perc_low_bound = -100
                    worker.new_data.emit(V, I_fixed, cleandiagVmon, voltagemeasured, cleandiagImon, voltagemeasured - V, \
                                         cleandiagVmon - voltagemeasured, prog_percent, read_percent, prog_upper_bound, prog_lower_bound, \
                                        read_upper_bound, read_lower_bound, perc_up_bound, perc_low_bound)
                    worker.popup_data.emit(voltagemeasured - V, cleandiagVmon - voltagemeasured, prog_upper_bound, prog_lower_bound, \
                                           read_upper_bound, read_lower_bound, prog_percent, read_percent, perc_up_bound, perc_low_bound)
                
                I_fixed += float(dict["current_step_size"])
                i += 1
            
                #Ensure the DUT won't exceed the power limit set
                powermeasure = float (V * I_fixed)
                if powermeasure > self.Power:
                    break
                
            #Increment of Steps
            #Delay(dict["PSU"]).write(dict["DownTime"])
            V += float(dict["voltage_step_size"])
            j += 1
            k += 1
        

        psu.sourVoltageLevelImmediateAmplitude(0, ch)
        WAI(dict["PSU"])
        psu.sourCurrentLimitPOS("MIN", ch)
        WAI(dict["PSU"])
        
        RST(dict["ELoad"])
        RST(dict["DMM"])

        # Wrapper classes hold the real PyVISA session in .instr
        for instrument in (psu, dmm, eload):
            try:
                if instrument is not None and hasattr(instrument, "instr") and instrument.instr is not None:
                    instrument.instr.close()
            except Exception:
                pass

        return self.infoList, self.dataList, self.dataList2

class HornbillVoltageMeasurementwithELoadwithOscilloscope:

    def __init__(self):
        self.results = []
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    def Execute_Voltage_Accuracy_Current_Static(self,dict,channel, worker=None):
        (
            Read,
            Apply,
            Display,
            Function,
            Frequency,
            Output,
            Measure,
            Sense,
            Configure,
            Delay,
            Trigger,
            Sample,
            Initiate,
            Fetch,
            Status,
            Voltage,
            Current,
            Oscilloscope,
            Excavator,
            Power,
            Hornbill,
            SMU_N67XX,
            DMM_344XXA,
            DMM_3458A,
            ELOAD_E367XXA,
        ) = Dimport.getClasses_Keysight(dict["Instrument"])

        (
            Channel,
            Mode,
            Voltage,
        ) = Dimport.getClasses_Chroma("Chroma")

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #Assign Instrument Object and Initialize the Instrument based on the VISA Address given in GUI
        psu = Hornbill(dict["PSU"])
        psu.setMode("VOLTAGE", ch)
        psu.senseVoltageSource(dict["VoltageSense"], ch)
        psu.sourCurrentLimitPOS("MAXimum", ch)         #Current LIMIT (Max for Voltage Accuracy)
        psu.sourCurrentLimitNEG("MINimum", ch)         #Current LIMIT (Max for Voltage Accuracy)
        psu.outputState("ON", ch) #Turn On the PSU and Eload
       
       
        #Set Series/Parallel Mode
        if dict["OperationMode"] == "Series":
            Output(dict["PSU"]).SPModeConnection("SER")
            WAI(dict["PSU"])
        elif dict["OperationMode"] == "Parallel":
            Output(dict["PSU"]).SPModeConnection("PAR")
            WAI(dict["PSU"])
        else:
            Output(dict["PSU"]).SPModeConnection("OFF")
            WAI(dict["PSU"])

        if dict["DMM_Model"] == "344xxA":
            dmm = DMM_344XXA(dict["DMM"])
            dmm.setNPLC(dict["Aperture"])
            dmm.setAutoZeroMode(dict["AutoZero"])
            dmm.setAutoImpedanceMode(dict["InputZ"])
            dmm.setConfiguration("VOLT")
            dmm.setTriggerSource("BUS")
            dmm.setVoltageResolutionDC("HIGH")

            if dict["Range"] == "Auto":
                Sense(dict["DMM"]).setVoltageRangeDCAuto()
            else:
                Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])

        elif dict["DMM_Model"] == "3458A":
            dmm = DMM_3458A(dict["DMM"])
            dmm.setDCV("AUTO")
            dmm.setTriggerArm()
            dmm.setNPLC(dict["Aperture"])
            dmm.setNumberOfReadings()
            dmm.disableMemory()
            dmm.setEndCondition()
            dmm.setDigits()
            dmm.enableAutoZero()
            dmm.enableDisplay()
        
        if dict["ELoad_Model"] == "E367XXA":
            eload = ELOAD_E367XXA(dict["ELoad"])
            _start_keysight_eload(eload, dict)
            
            
        elif dict["ELoad_Model"] == "Chroma":
            eload = ELOAD_E63200A(dict["ELoad"])

        oscilloscope = Oscilloscope(dict["OSC"])

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        #Programming Parameters
        self.param1 = float(dict["Programming_Error_Gain"])
        self.param2 = float(dict["Programming_Error_Offset"])
        self.param3 = float(dict["Readback_Error_Gain"])
        self.param4 = float(dict["Readback_Error_Offset"])
        self.unit = dict["unit"]
        self.updatedelay = float(dict["updatedelay"])

        #Set Program Loop Using Step Size
        self.Power = float(dict["power"])
        i = 0   #Current Iteration
        j = 0   #Voltage Iteration
        k = 0   #Step of Iteration
        I_fixed = float(dict["minCurrent"])         #Min Current
        V = float(dict["minVoltage"])
        I = float(dict["maxVoltage"]) + 1
        current_iter = (
            (float(dict["maxCurrent"]) - float(dict["minCurrent"]))
            / float(dict["current_step_size"])
        ) + 1
        voltage_iter = (
            (float(dict["maxVoltage"]) - float(dict["minVoltage"]))
            / float(dict["voltage_step_size"])
        ) + 1
  

        #Run Test (Voltage Loop in Current Loop)
        while i < current_iter:
            _execution_checkpoint(worker)
            j = 0
            V = float(dict["minVoltage"])
            psu.sourVoltageLevelImmediateAmplitude(float(dict["minVoltage"]), ch)
            Iset = dict["maxCurrent"]
            WAI(dict["PSU"])

            if I_fixed > float(dict["maxCurrent"]):
                I_fixed= float(dict["maxCurrent"])

            #If PSU MAX I = ELOAD MAX I (Reduce Eload I by 0.1 - Prevent Overload)
            if I_fixed == float(dict["maxCurrent"]) and Iset == float(dict["maxCurrent"]):
                if dict["ELoad_Model"] == "E367XXA":
                    eload.setOutputCurrent(I_fixed - 0.1)
                    WAI(dict["ELoad"])
                elif dict["ELoad_Model"] == "Chroma":
                    eload.setOutputCurrent(I_fixed - 0.1)
                    WAI(dict["ELoad"])
            else:
                if dict["ELoad_Model"] == "E367XXA":
                    eload.setOutputCurrent(I_fixed)
                    WAI(dict["ELoad"])
                elif dict["ELoad_Model"] == "Chroma":
                    eload.setOutputCurrent(I_fixed)
                    WAI(dict["ELoad"])


            #Voltage Iteration
            while j < voltage_iter:
                _execution_checkpoint(worker)
                #Set Voltage and Current
                if V > float(dict["maxVoltage"]):
                    V = float(dict["maxVoltage"])
                    
                psu.sourVoltageLevelImmediateAmplitude(V, ch)
                WAI(dict["PSU"])
                self.infoList.insert(k, [V, I_fixed, i])

                sleep(float(self.updatedelay))

                #Readback Voltage and Current
                cleandiagVmon, cleandiagImon = _measure_hornbill_readback(
                    psu, dict, ch
                )
                print("Voltage Monitor Reading =", cleandiagVmon)
                print("Current Monitor Reading =", cleandiagImon)

                self.dataList2.insert(k, [float(cleandiagVmon), float(cleandiagImon)])
               
                #DMM Measurement
                if dict["DMM_Model"] == "344xxA":
                    #INIT DMM (Trigger Measurement)
                    dmm.initiate()
                    status = float(dmm.operationCondition())
                    TRG(dict["DMM"])
                    while 1:
                        status = float(Status(dict["DMM"]).operationCondition())
                        
                        #Measure Voltage with Error Flag Rised
                        if status == 8704.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break
                        
                        #Measrue Voltage with Normal Condition
                        elif status == 512.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break
                        elif status == 8192.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break

                elif dict["DMM_Model"] == "3458A":
                    # Read current from 3485A DMM
                    voltagemeasured = float(dmm.queryMeasurement())
                    self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                    )
                
                #Oscilloscope Measurement
                _execution_checkpoint(worker)
                oscilloscope.run()
                sleep(1)
                oscilloscope.stop()
                try:
                    displayData = oscilloscope.read_binary_data()
                    print("Data retrieved successfully:", displayData)
                except VisaIOError as e:
                    print(f"Timeout or communication error: {e}")
                    raise

                if displayData.startswith(b"#"):
                    header_length = int(displayData[1:2])  # Get header size length
                    num_digits = int(displayData[2:2 + header_length])  # Extract data length
                    displayData = displayData[2 + header_length:]  # Extract actual image data

                # Define save path with timestamp
                save_path = str(dict["savedir"])
                current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                png_file = os.path.join(save_path, f"{V}_{I_fixed}_{current_time}.png")

                # Save PNG file as binary
                with open(png_file, "wb") as file:
                    file.write(displayData)

                print(f"Screenshot saved at: {png_file}")


                if worker is not None:
                    prog_percent = (voltagemeasured - V)/V*100
                    read_percent = (cleandiagVmon - voltagemeasured)/voltagemeasured*100
                    prog_upper_bound = (V*self.param1) + self.param2
                    prog_lower_bound = -prog_upper_bound
                    read_upper_bound = (V*self.param3) + self.param4
                    read_lower_bound = -read_upper_bound
                    perc_up_bound = 100
                    perc_low_bound = -100
                    worker.new_data.emit(V, I_fixed, cleandiagVmon, voltagemeasured, cleandiagImon, voltagemeasured - V, \
                                         cleandiagVmon - voltagemeasured, prog_percent, read_percent, prog_upper_bound, prog_lower_bound, \
                                        read_upper_bound, read_lower_bound, perc_up_bound, perc_low_bound)
                    worker.popup_data.emit(voltagemeasured - V, cleandiagVmon - voltagemeasured, prog_upper_bound, prog_lower_bound, \
                                           read_upper_bound, read_lower_bound, prog_percent, read_percent, perc_up_bound, perc_low_bound)
                

                #Increment of Steps
                #Delay(dict["PSU"]).write(dict["DownTime"])
                V += float(dict["voltage_step_size"])
                j += 1
                k += 1

                #Ensure the DUT won't exceed the power limit set
                powermeasure = float (V * I_fixed)
                if powermeasure > self.Power:
                    break

            I_fixed += float(dict["current_step_size"])
            i += 1


        psu.sourVoltageLevelImmediateAmplitude(3, ch)
        WAI(dict["PSU"])
        psu.sourCurrentLimitPOS("MIN", ch)
        WAI(dict["PSU"])
       
        RST(dict["ELoad"])
        RST(dict["DMM"])
        RST(dict["PSU"])


        # Wrapper classes hold the real PyVISA session in .instr
        for instrument in (psu, dmm, eload, oscilloscope):
            try:
                if instrument is not None and hasattr(instrument, "instr") and instrument.instr is not None:
                    instrument.instr.close()
            except Exception:
                pass


        return self.infoList, self.dataList, self.dataList2
    
    def Execute_Voltage_Accuracy_Current_Change(self,dict,channel, worker=None):
        (
            Read,
            Apply,
            Display,
            Function,
            Frequency,
            Output,
            Measure,
            Sense,
            Configure,
            Delay,
            Trigger,
            Sample,
            Initiate,
            Fetch,
            Status,
            Voltage,
            Current,
            Oscilloscope,
            Excavator,
            Power,
            Hornbill,
            SMU_N67XX,
            DMM_344XXA,
            DMM_3458A,
            ELOAD_E367XXA,
        ) = Dimport.getClasses_Keysight(dict["Instrument"])

        (
            Channel,
            Mode,
            Voltage,
        ) = Dimport.getClasses_Chroma("Chroma")

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #Assign Instrument Object and Initialize the Instrument based on the VISA Address given in GUI
        psu = Hornbill(dict["PSU"])
        psu.setMode("VOLTAGE", ch)
        psu.senseVoltageSource(dict["VoltageSense"], ch)
        psu.sourCurrentLimitPOS("MAXimum", ch)         #Current LIMIT (Max for Voltage Accuracy)
        psu.outputState("ON", ch) #Turn On the PSU and Eload

        #Set Series/Parallel Mode
        if dict["OperationMode"] == "Series":
            Output(dict["PSU"]).SPModeConnection("SER")
            WAI(dict["PSU"])
        elif dict["OperationMode"] == "Parallel":
            Output(dict["PSU"]).SPModeConnection("PAR")
            WAI(dict["PSU"])
        else:
            Output(dict["PSU"]).SPModeConnection("OFF")
            WAI(dict["PSU"])

        if dict["DMM_Model"] == "344xxA":
            dmm = DMM_344XXA(dict["DMM"])
            dmm.setNPLC(dict["Aperture"])
            dmm.setAutoZeroMode(dict["AutoZero"])
            dmm.setAutoImpedanceMode(dict["InputZ"])
            dmm.setConfiguration("VOLT")
            dmm.setTriggerSource("BUS")
            dmm.setVoltageResolutionDC("HIGH")

            if dict["Range"] == "Auto":
                Sense(dict["DMM"]).setVoltageRangeDCAuto()
            else:
                Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])

        elif dict["DMM_Model"] == "3458A":
            dmm = DMM_3458A(dict["DMM"])
            dmm.setDCV("AUTO")
            dmm.setTriggerArm()
            dmm.setNPLC(dict["Aperture"])
            dmm.setNumberOfReadings()
            dmm.disableMemory()
            dmm.setEndCondition()
            dmm.setDigits()
            dmm.enableAutoZero()
            dmm.enableDisplay()
        
        if dict["ELoad_Model"] == "E367XXA":
            eload = ELOAD_E367XXA(dict["ELoad"])
            _start_keysight_eload(eload, dict)
            
            
        elif dict["ELoad_Model"] == "Chroma":
            eload = ELOAD_E63200A(dict["ELoad"])

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        #Programming Parameters
        self.param1 = float(dict["Programming_Error_Gain"])
        self.param2 = float(dict["Programming_Error_Offset"])
        self.param3 = float(dict["Readback_Error_Gain"])
        self.param4 = float(dict["Readback_Error_Offset"])
        self.unit = dict["unit"]
        self.updatedelay = float(dict["updatedelay"])

        #Set Program Loop Using Step Size
        self.Power = float(dict["power"])
        i = 0   #Current Iteration
        j = 0   #Voltage Iteration
        k = 0   #Step of Iteration
        I_fixed = float(dict["minCurrent"])         #Min Current
        V = float(dict["minVoltage"])
        I = float(dict["maxVoltage"]) + 1
        current_iter = (
            (float(dict["maxCurrent"]) - float(dict["minCurrent"]))
            / float(dict["current_step_size"])
        ) + 1
        voltage_iter = (
            (float(dict["maxVoltage"]) - float(dict["minVoltage"]))
            / float(dict["voltage_step_size"])
        ) + 1
        sleep(1)
        
    
        #Voltage Iteration
        while j < voltage_iter:
            i=0
            I_fixed = float(dict["minCurrent"])
            eload.setOutputCurrent(I_fixed)

            WAI(dict["ELoad"])
            #Set Voltage and Current
            if V > float(dict["maxVoltage"]):
                V = float(dict["maxVoltage"])
            psu.sourVoltageLevelImmediateAmplitude(V, ch)
            WAI(dict["PSU"])
            self.infoList.insert(k, [V, I_fixed, i])

            sleep(float(self.updatedelay))

            #Readback Voltage and Current
            cleandiagVmon, cleandiagImon = _measure_hornbill_readback(
                psu, dict, ch
            )
            print("Voltage Monitor Reading =", cleandiagVmon)
            print("Current Monitor Reading =", cleandiagImon)

            sleep(1)
            self.dataList2.insert(k, [float(cleandiagVmon), float(cleandiagImon)])
            
        
            while i < current_iter:
                Iset = dict["maxCurrent"]
                sleep(2)
                WAI(dict["PSU"])

                if I_fixed > float(dict["maxCurrent"]):
                    I_fixed= float(dict["maxCurrent"])

                if dict["ELoad_Model"] == "E367XXA":
                    #If PSU MAX I = ELOAD MAX I (Reduce Eload I by 0.1 - Prevent Overload)
                    if I_fixed == float(dict["maxCurrent"]) and Iset == float(dict["maxCurrent"]):
                        eload.setOutputCurrent(I_fixed - 0.1)
                        WAI(dict["ELoad"])

                    else:
                        eload.setOutputCurrent(max(0.0, I_fixed - 0.001))
                        WAI(dict["ELoad"])

                elif dict["ELoad_Model"] == "Chroma":
                    #If PSU MAX I = ELOAD MAX I (Reduce Eload I by 0.1 - Prevent Overload)
                    if I_fixed == float(dict["maxCurrent"]) and Iset == float(dict["maxCurrent"]):
                        Current(dict["ELoad"]).setOutputCurrent(I_fixed - 0.001)
                        WAI(dict["ELoad"])

                    else:
                        Current(dict["ELoad"]).setOutputCurrent(
                            max(0.0, I_fixed - 0.001)
                        )
                        WAI(dict["ELoad"])

                sleep(1)

                if dict["DMM_Model"] == "344xxA":
                    #INIT DMM (Trigger Measurement)
                    dmm.initiate()
                    status = float(dmm.operationCondition())
                    TRG(dict["DMM"])
                    while 1:
                        status = float(Status(dict["DMM"]).operationCondition())
                        
                        #Measure Voltage with Error Flag Rised
                        if status == 8704.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break
                        
                        #Measrue Voltage with Normal Condition
                        elif status == 512.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break
                        elif status == 8192.0:
                            voltagemeasured = float(Fetch(dict["DMM"]).query())
                            self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                            )
                            break

                elif dict["DMM_Model"] == "3458A":
                    # Read current from 3485A DMM
                    voltagemeasured = float(dmm.queryMeasurement())
                    self.dataList.insert(
                                
                                k, [voltagemeasured , 0]
                    )
                
                if worker is not None:
                    prog_percent = (voltagemeasured - V)/V*100
                    read_percent = (cleandiagVmon - voltagemeasured)/voltagemeasured*100
                    prog_upper_bound = (V*self.param1) + self.param2
                    prog_lower_bound = -prog_upper_bound
                    read_upper_bound = (V*self.param3) + self.param4
                    read_lower_bound = -read_upper_bound
                    perc_up_bound = 100
                    perc_low_bound = -100
                    worker.new_data.emit(V, I_fixed, cleandiagVmon, voltagemeasured, cleandiagImon, voltagemeasured - V, \
                                         cleandiagVmon - voltagemeasured, prog_percent, read_percent, prog_upper_bound, prog_lower_bound, \
                                        read_upper_bound, read_lower_bound, perc_up_bound, perc_low_bound)
                    worker.popup_data.emit(voltagemeasured - V, cleandiagVmon - voltagemeasured, prog_upper_bound, prog_lower_bound, \
                                           read_upper_bound, read_lower_bound, prog_percent, read_percent, perc_up_bound, perc_low_bound)
                
                I_fixed += float(dict["current_step_size"])
                i += 1
            
                #Ensure the DUT won't exceed the power limit set
                powermeasure = float (V * I_fixed)
                if powermeasure > self.Power:
                    break
                
            #Increment of Steps
            #Delay(dict["PSU"]).write(dict["DownTime"])
            V += float(dict["voltage_step_size"])
            j += 1
            k += 1
        

        psu.sourVoltageLevelImmediateAmplitude(0, ch)
        WAI(dict["PSU"])
        psu.sourCurrentLimitPOS("MIN", ch)
        WAI(dict["PSU"])
        
        RST(dict["ELoad"])
        RST(dict["DMM"])

        # Wrapper classes hold the real PyVISA session in .instr
        for instrument in (psu, dmm, eload):
            try:
                if instrument is not None and hasattr(instrument, "instr") and instrument.instr is not None:
                    instrument.instr.close()
            except Exception:
                pass

        return self.infoList, self.dataList, self.dataList2

class HornbillVoltageCalibration:
    def Execute_Voltage_Calibration(self,dict):

        self.psu_addr = dict["PSU_Visa"]
        self.dmm_addr = dict["DMM_Visa"]
        self.channel = dict["Channel"]
        self.cal_points = [
            dict["Cal_Point_1"],
            dict["Cal_Point_2"],
            dict["Cal_Point_3"],
            dict["Cal_Point_4"],
        ]
        
        try:
            self.log.emit("Opening VISA resources...")
            rm = pyvisa.ResourceManager()
            psu = None
            dmm = None
            try:
                psu = rm.open_resource(self.psu_addr)
                psu.timeout = 60000
                dmm = rm.open_resource(self.dmm_addr)
                dmm.timeout = 10000
            except Exception as e:
                raise RuntimeError(f"Failed to open instruments: {e}")

            # Step 1: CAL:STAT ON
            self.scpi(psu, 'OUTPUT:STATe ON, (@1)')  # Ensure output is ON"')
            time.sleep(2)
            self.log.emit('Step 1: CAL:STAT ON, "PP8000A"')
            self.scpi(psu, 'CAL:STAT ON,"PP8000A"')
            time.sleep(2)
            self.check_error(psu)
            if self._stop_requested:
                raise RuntimeError("Stopped by user")

            # Step 2: CAL:VOLT 60, (@1)
            self.log.emit(f"Step 2: CAL:VOLT 60, (@{self.channel})")
            self.scpi(psu, f"CAL:VOLT 60,(@{self.channel})")
            time.sleep(2)
            self.check_error(psu)
            if self._stop_requested:
                raise RuntimeError("Stopped by user")

            # Configure DMM
            self.log.emit("Configuring DMM...")
            dmm.write(":CONFigure:VOLTage:DC AUTO,MAXimum")
            dmm.write("TRIG:SOUR IMM")
            dmm.write("SAMP:COUN 1")
            time.sleep(2)

            # Steps 3-6: Loop through cal points
            for point in self.cal_points:
                if self._stop_requested:
                    raise RuntimeError("Stopped by user")

                self.log.emit(f"Step 3/5: CAL:LEV {point}")
                self.scpi(psu, f"CAL:LEV {point}")
                time.sleep(2)
                self.check_error(psu)
                time.sleep(30)

                self.log.emit("Measuring DMM...")
                val = dmm.query("MEAS:VOLT:DC?").strip()
                self.log.emit(f"DMM reading = {val}")

                self.log.emit(f"Step 4/6: CAL:DATA {val}")
                self.scpi(psu, f"CAL:DATA {val}")
                time.sleep(2)
                self.check_error(psu)
                time.sleep(2)

            # Step 7: CAL:SAVE
            self.log.emit("Step 7: CAL:SAVE")
            self.scpi(psu, "CAL:SAVE")
            time.sleep(2)
            self.check_error(psu)
            time.sleep(2.0)

            # Step 8: CAL:STAT OFF
            self.log.emit("Step 8: CAL:STAT OFF")
            self.scpi(psu, "CAL:STAT OFF")
            time.sleep(2)
            self.check_error(psu)

            self.log.emit("=== CALIBRATION COMPLETE ✅ ===")

        except Exception as e:
            tb = traceback.format_exc()
            self.log.emit(f"ERROR: {e}\n{tb}")
            self.error.emit(str(e))
        finally:
            try:
                if 'psu' in locals() and psu is not None:
                    psu.close()
                if 'dmm' in locals() and dmm is not None:
                    dmm.close()
            except Exception:
                pass
            self.finished.emit()

class HornbillCurrentMeasurementwithELoad_IMON_FULL :
    def __init__(self):
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    def Execute_Current_Accuracy_Current_Static(self, dict, channel):
        """Execution of Current Measurement for Programm / Readback Accuracy using Status Event Registry to synchronize Instrument

        The function first declares two lists, datalist & infolist that will be used to collect data.
        It then dynamically imports the library to be used. Next, the settings for all Instrument
        are initialized. The test loop begins where Voltage and Current Sweep is conducted and collect
        measured data.

        The synchronization of Instrument here is done by reading the status of the event registry.
        The status determined from the Instrument can let the program determine if the Instrument is
        measuring. The program will only proceed to tell the Instrument to query the measured value
        after it is determined that the measurement has been completed. This method is suitable for
        operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
        more complicated than other methods. This method only can be implemented that have the specific
        commands that are used.

        In line 605, where V_fixed - 0.001 * V_fixed is done to prevent the ELoad from causing the DUT
        to enter CV Mode.

        Args:
            Instrument: String determining which library to be used.
            Error_Gain: Float determining the error gain of the Readback Voltage Specification.
            Error_Offset: Float determining the error offset of the Readback Voltage Specification.
            minCurrent: Float determining the start current for Current Sweep.
            maxCurrent: Float determining the stop current for Current Sweep.
            current_stepsize: Float determining the step size during Current Sweep.
            minVoltage: Float determining the start voltage for Voltage Sweep.
            maxVoltage: Float determining the stop voltage for Voltage Sweep.
            voltage_stepsize: Float determining the step_size for Voltage_Sweep.
            PSU: String containing the VISA Address of the PSU used.
            DMM: String containing the VISA Address of the DMM used.
            ELoad: String containing the VISA Address of the ELoad used.
            "ELoad_Channel: Integer containing the channel number that the ELoad is using.
            PSU_Channel: Integer containing the channel number that the PSU is using.
            setCurrent_Sense: String determining the Current Sense that will be used.
            setCurrent_Res: String determining the Current Resolution that will be used.
            setMode: String determining the Priority mode of the ELoad.
            Range: String determining the measuring range of the DMM should be Auto or a specific range.
            Apreture: String determining the NPLC to be used by DMM when measuring.
            AutoZero: String determining if AutoZero Mode on DMM should be enabled/disabled.
            InputZ: String determining the Input Impedance Mode of DMM.
            UpTime: Float containing details regarding the uptime delay.
            DownTime: Float containing details regarding the downtime delay.
            current_iter: integer storing the number of iterations of current sweep.
            voltage_iter: integer storing the number of iterations of voltage sweep.
            status: float storing the value returned by the status event registry.
            infoList: List containing the programmed data that was set by Program.
            dataList: List containing the measured data that was queried from DUT.

        Returns:
            Returns two list, DataList & InfoList. Each containing the programmed & measured data individually.

        Raises:
            VisaIOError: An error occured when opening PyVisa Resources.
        """
        # Dynamic Library Import
        (
            Read,
            Apply,
            Display,
            Function,
            Frequency,
            Output,
            Measure,
            Sense,
            Configure,
            Delay,
            Trigger,
            Sample,
            Initiate,
            Fetch,
            Status,
            Voltage,
            Current,
            Oscilloscope,
            Excavator,
            SMU,
            Power,
            Hornbill
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM2"])
        WAI(dict["DMM2"])

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #delay
        

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        #offset
        sleep(3)

        # Instrument Initialization
        Configure(dict["DMM2"]).write("Voltage")
        Trigger(dict["DMM2"]).setSource("BUS")
        Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])
         #Instrument Channel Set
        Voltage(dict["PSU"]).setInstrumentChannel(ch)
        Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
        sleep(2)
        #Display(dict["ELoad"]).displayState(dict["ELoad_Channel"])
        Function(dict["ELoad"]).setMode("Voltage")
        Function(dict["PSU"]).setMode("Current")

        #Set Series/Parallel Mode
        if dict["OperationMode"] == "Series":
            Output(dict["PSU"]).SPModeConnection("SER")
            WAI(dict["PSU"])
        elif dict["OperationMode"] == "Parallel":
            Output(dict["PSU"]).SPModeConnection("PAR")
            WAI(dict["PSU"])
        else:
            Output(dict["PSU"]).SPModeConnection("OFF")
            WAI(dict["PSU"])
        
        #Set Channel, Sense
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
        Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])

        Voltage(dict["DMM2"]).setNPLC(dict["Aperture"])
        Voltage(dict["DMM2"]).setAutoZeroMode(dict["AutoZero"])
        Voltage(dict["DMM2"]).setAutoImpedanceMode(dict["InputZ"])
        #Current(dict["DMM"]).setTerminal(dict["Terminal"])

        if dict["Range"] == "Auto":
            Sense(dict["DMM2"]).setVoltageRangeDCAuto()
        else:
            Sense(dict["DMM2"]).setVoltageRangeDC(dict["Range"])
        
        self.param1 = float(dict["Programming_Error_Gain"])
        self.param2 = float(dict["Programming_Error_Offset"])
        self.param3 = float(dict["Readback_Error_Gain"])
        self.param4 = float(dict["Readback_Error_Offset"])
        self.unit = dict["unit"]
        self.updatedelay = float(dict["updatedelay"])

        # Test Loop
        self.Power = float(dict["power"])
        self.rshunt = float(dict["rshunt"])
        i = 0
        j = 0
        k = 0
        V_fixed = float(dict["minVoltage"])
        # V = float(dict["maxVoltage"]) + 1
        I = float(dict["minCurrent"])

        if self.rshunt == 0.01: #(100A) (1V + cable loss)
            VshuntdropMax = 2
        elif self.rshunt == 0.05:#(50A) (2.5V + cable loss)
            VshuntdropMax = 3.5
        elif self.rshunt == 1: #(10A)  (10V + cable loss)
            VshuntdropMax = 11

        current_iter = (
            (float(dict["maxCurrent"]) - float(dict["minCurrent"]))
            / float(dict["current_step_size"])
        ) + 1
        voltage_iter = (
            (float(dict["maxVoltage"]) - float(dict["minVoltage"]))
            / float(dict["voltage_step_size"])
        ) + 1
        sleep(1)

        psu = Hornbill(dict["PSU"])
        #Current LIMIT (Max for Voltage Accuracy)
        psu.sourVoltageLevelImmediateAmplitude("MAXimum", ch)
        WAI(dict["PSU"])

        #Turn On the PSU and Eload
        psu.outputState("ON", ch)
        WAI(dict["PSU"])
        sleep(3)

        while i < voltage_iter:

            j = 0
            I = float(dict["minCurrent"])

            if V_fixed> float(dict["maxVoltage"]):
                V_fixed = float(dict["maxVoltage"])

            # Setting to prevent draw to much voltage
            if V_fixed == 0:
                Voltage(dict["ELoad"]).setOutputVoltage(1)
                WAI(dict["ELoad"])
            elif V_fixed == float(dict["maxVoltage"]):
                Voltage(dict["ELoad"]).setOutputVoltage(V_fixed-VshuntdropMax)
                WAI(dict["ELoad"])
            else:
                Voltage(dict["ELoad"]).setOutputVoltage(V_fixed)
                WAI(dict["ELoad"])

            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])
            sleep(3)

            while j < current_iter:
                sleep()
                if I> float(dict["maxCurrent"]):
                    I = float(dict["maxCurrent"])
                    
                psu.sourCurrentLimitPOS(I, ch)
                WAI(dict["PSU"])
                
                #print("Voltage: ", V_fixed, "Current: ", I)
                self.infoList.insert(k, [V_fixed, I, i])
                #offset
                sleep(0.2)
                sleep(self.updatedelay)

                """#PSU ReadBack
                temp_values = Measure(dict["PSU"]).singleChannelQuery("VOLT")
                WAI(dict["PSU"])
                temp_values2 = Measure(dict["PSU"]).singleChannelQuery("CURR")
                WAI(dict["PSU"])

                self.dataList2.insert(k, [float(temp_values), float(temp_values2)])"""
                
                #Readback Voltage and Current
                cleandiagVmon, cleandiagImon = _measure_hornbill_readback(
                    psu, dict, ch, current_input="FULL"
                )
                print("Voltage Monitor Reading =", cleandiagVmon)
                WAI(dict["PSU"])
                print("Current Monitor Reading =", cleandiagImon)
                WAI(dict["PSU"])

                #DMM Condition & Measurements
                Initiate(dict["DMM2"]).initiate()
                status = float(Status(dict["DMM2"]).operationCondition())
                TRG(dict["DMM2"])

                sleep(1)
                #self.dataList2.insert(k, [float(temp_values), float(temp_values2)])
                self.dataList2.insert(k, [float(cleandiagVmon), float(cleandiagImon)])

                while 1:
                    status = float(Status(dict["DMM2"]).operationCondition())
                    
                    if status == 8704.0:
                        voltagemeasured = float(Fetch(dict["DMM2"]).query())
                        currentmeasured = voltagemeasured/self.rshunt
                        self.dataList.insert(

                            k, [0 , currentmeasured]
                        )
                        break

                    elif status == 512.0:
                        voltagemeasured = float(Fetch(dict["DMM2"]).query())
                        currentmeasured = voltagemeasured/self.rshunt
                        self.dataList.insert(
                            
                            k, [0 , currentmeasured]
                        )
                        break
                
                WAI(dict["DMM2"])

                #PSU Delay? (Up/Down Time -> Not yet configured)
                Delay(dict["PSU"]).write(dict["DownTime"])
                WAI(dict["PSU"])

                I += float(dict["current_step_size"])
                j += 1
                k += 1

                #if V_fixed == 0:
                #    powermeasure = float ((float(temp_values) + float(dict["voltage_step_size"]) ) * currentmeasured)
                #    I=0.001
                #else:
                #    powermeasure = float ((float(temp_values) + float(dict["voltage_step_size"]) ) * I)

                #Limit V/I if power test exceeded
                powermeasure = V_fixed * I       

                if powermeasure > self.Power:
                    break

            V_fixed += float(dict["voltage_step_size"])
            i += 1

        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Voltage(dict["ELoad"]).setOutputVoltage(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
        RST(dict["DMM2"])
        WAI(dict["DMM2"])

        return self.infoList, self.dataList, self.dataList2
    
class HornbillCurrentMeasurementwithELoad_IMON_200uA :
    def __init__(self):
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    def Execute_Current_Accuracy_Current_Static(self, dict, channel):
        """Execution of Current Measurement for Programm / Readback Accuracy using Status Event Registry to synchronize Instrument

        The function first declares two lists, datalist & infolist that will be used to collect data.
        It then dynamically imports the library to be used. Next, the settings for all Instrument
        are initialized. The test loop begins where Voltage and Current Sweep is conducted and collect
        measured data.

        The synchronization of Instrument here is done by reading the status of the event registry.
        The status determined from the Instrument can let the program determine if the Instrument is
        measuring. The program will only proceed to tell the Instrument to query the measured value
        after it is determined that the measurement has been completed. This method is suitable for
        operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
        more complicated than other methods. This method only can be implemented that have the specific
        commands that are used.

        In line 605, where V_fixed - 0.001 * V_fixed is done to prevent the ELoad from causing the DUT
        to enter CV Mode.

        Args:
            Instrument: String determining which library to be used.
            Error_Gain: Float determining the error gain of the Readback Voltage Specification.
            Error_Offset: Float determining the error offset of the Readback Voltage Specification.
            minCurrent: Float determining the start current for Current Sweep.
            maxCurrent: Float determining the stop current for Current Sweep.
            current_stepsize: Float determining the step size during Current Sweep.
            minVoltage: Float determining the start voltage for Voltage Sweep.
            maxVoltage: Float determining the stop voltage for Voltage Sweep.
            voltage_stepsize: Float determining the step_size for Voltage_Sweep.
            PSU: String containing the VISA Address of the PSU used.
            DMM: String containing the VISA Address of the DMM used.
            ELoad: String containing the VISA Address of the ELoad used.
            "ELoad_Channel: Integer containing the channel number that the ELoad is using.
            PSU_Channel: Integer containing the channel number that the PSU is using.
            setCurrent_Sense: String determining the Current Sense that will be used.
            setCurrent_Res: String determining the Current Resolution that will be used.
            setMode: String determining the Priority mode of the ELoad.
            Range: String determining the measuring range of the DMM should be Auto or a specific range.
            Apreture: String determining the NPLC to be used by DMM when measuring.
            AutoZero: String determining if AutoZero Mode on DMM should be enabled/disabled.
            InputZ: String determining the Input Impedance Mode of DMM.
            UpTime: Float containing details regarding the uptime delay.
            DownTime: Float containing details regarding the downtime delay.
            current_iter: integer storing the number of iterations of current sweep.
            voltage_iter: integer storing the number of iterations of voltage sweep.
            status: float storing the value returned by the status event registry.
            infoList: List containing the programmed data that was set by Program.
            dataList: List containing the measured data that was queried from DUT.

        Returns:
            Returns two list, DataList & InfoList. Each containing the programmed & measured data individually.

        Raises:
            VisaIOError: An error occured when opening PyVisa Resources.
        """
        # Dynamic Library Import
        (
            Read,
            Apply,
            Display,
            Function,
            Frequency,
            Output,
            Measure,
            Sense,
            Configure,
            Delay,
            Trigger,
            Sample,
            Initiate,
            Fetch,
            Status,
            Voltage,
            Current,
            Oscilloscope,
            Excavator,
            SMU,
            Power,
            Hornbill
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM2"])
        WAI(dict["DMM2"])

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #delay
        

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        #offset
        sleep(3)

        # Instrument Initialization
        Configure(dict["DMM2"]).write("Voltage")
        Trigger(dict["DMM2"]).setSource("BUS")
        Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])
         #Instrument Channel Set
        Voltage(dict["PSU"]).setInstrumentChannel(ch)
        Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
        sleep(2)
        #Display(dict["ELoad"]).displayState(dict["ELoad_Channel"])
        Function(dict["ELoad"]).setMode("Voltage")
        Function(dict["PSU"]).setMode("Current")

        #Set Series/Parallel Mode
        if dict["OperationMode"] == "Series":
            Output(dict["PSU"]).SPModeConnection("SER")
            WAI(dict["PSU"])
        elif dict["OperationMode"] == "Parallel":
            Output(dict["PSU"]).SPModeConnection("PAR")
            WAI(dict["PSU"])
        else:
            Output(dict["PSU"]).SPModeConnection("OFF")
            WAI(dict["PSU"])
        
        #Set Channel, Sense
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
        Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])

        Voltage(dict["DMM2"]).setNPLC(dict["Aperture"])
        Voltage(dict["DMM2"]).setAutoZeroMode(dict["AutoZero"])
        Voltage(dict["DMM2"]).setAutoImpedanceMode(dict["InputZ"])
        #Current(dict["DMM"]).setTerminal(dict["Terminal"])

        if dict["Range"] == "Auto":
            Sense(dict["DMM2"]).setVoltageRangeDCAuto()
        else:
            Sense(dict["DMM2"]).setVoltageRangeDC(dict["Range"])
        
        self.param1 = float(dict["Programming_Error_Gain"])
        self.param2 = float(dict["Programming_Error_Offset"])
        self.param3 = float(dict["Readback_Error_Gain"])
        self.param4 = float(dict["Readback_Error_Offset"])
        self.unit = dict["unit"]
        self.updatedelay = float(dict["updatedelay"])

        # Test Loop
        self.Power = float(dict["power"])
        self.rshunt = float(dict["rshunt"])
        i = 0
        j = 0
        k = 0
        V_fixed = float(dict["minVoltage"])
        # V = float(dict["maxVoltage"]) + 1
        I = float(dict["minCurrent"])

        if self.rshunt == 0.01: #(100A) (1V + cable loss)
            VshuntdropMax = 2
        elif self.rshunt == 0.05:#(50A) (2.5V + cable loss)
            VshuntdropMax = 3.5
        elif self.rshunt == 1: #(10A)  (10V + cable loss)
            VshuntdropMax = 11

        current_iter = (
            (float(dict["maxCurrent"]) - float(dict["minCurrent"]))
            / float(dict["current_step_size"])
        ) + 1
        voltage_iter = (
            (float(dict["maxVoltage"]) - float(dict["minVoltage"]))
            / float(dict["voltage_step_size"])
        ) + 1
        sleep(1)

        psu = Hornbill(dict["PSU"])
        #Current LIMIT (Max for Voltage Accuracy)
        psu.sourVoltageLevelImmediateAmplitude("MAXimum", ch)
        WAI(dict["PSU"])

        #Turn On the PSU and Eload
        psu.outputState("ON", ch)
        WAI(dict["PSU"])
        sleep(3)

        while i < voltage_iter:

            j = 0
            I = float(dict["minCurrent"])

            if V_fixed> float(dict["maxVoltage"]):
                V_fixed = float(dict["maxVoltage"])

            # Setting to prevent draw to much voltage
            if V_fixed == 0:
                Voltage(dict["ELoad"]).setOutputVoltage(1)
                WAI(dict["ELoad"])
            elif V_fixed == float(dict["maxVoltage"]):
                Voltage(dict["ELoad"]).setOutputVoltage(V_fixed-VshuntdropMax)
                WAI(dict["ELoad"])
            else:
                Voltage(dict["ELoad"]).setOutputVoltage(V_fixed)
                WAI(dict["ELoad"])

            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])
            sleep(3)

            while j < current_iter:
                sleep()
                if I> float(dict["maxCurrent"]):
                    I = float(dict["maxCurrent"])
                    
                psu.sourCurrentLimitPOS(I, ch)
                WAI(dict["PSU"])
                
                #print("Voltage: ", V_fixed, "Current: ", I)
                self.infoList.insert(k, [V_fixed, I, i])
                #offset
                sleep(0.2)
                sleep(self.updatedelay)

                """#PSU ReadBack
                temp_values = Measure(dict["PSU"]).singleChannelQuery("VOLT")
                WAI(dict["PSU"])
                temp_values2 = Measure(dict["PSU"]).singleChannelQuery("CURR")
                WAI(dict["PSU"])

                self.dataList2.insert(k, [float(temp_values), float(temp_values2)])"""
                
                #Readback Voltage and Current
                cleandiagVmon, cleandiagImon = _measure_hornbill_readback(
                    psu, dict, ch, current_input="200uA"
                )
                print("Voltage Monitor Reading =", cleandiagVmon)
                WAI(dict["PSU"])
                print("Current Monitor Reading =", cleandiagImon)
                WAI(dict["PSU"])

                #DMM Condition & Measurements
                Initiate(dict["DMM2"]).initiate()
                status = float(Status(dict["DMM2"]).operationCondition())
                TRG(dict["DMM2"])

                sleep(1)
                #self.dataList2.insert(k, [float(temp_values), float(temp_values2)])
                self.dataList2.insert(k, [float(cleandiagVmon), float(cleandiagImon)])

                while 1:
                    status = float(Status(dict["DMM2"]).operationCondition())
                    
                    if status == 8704.0:
                        voltagemeasured = float(Fetch(dict["DMM2"]).query())
                        currentmeasured = voltagemeasured/self.rshunt
                        self.dataList.insert(

                            k, [0 , currentmeasured]
                        )
                        break

                    elif status == 512.0:
                        voltagemeasured = float(Fetch(dict["DMM2"]).query())
                        currentmeasured = voltagemeasured/self.rshunt
                        self.dataList.insert(
                            
                            k, [0 , currentmeasured]
                        )
                        break
                
                WAI(dict["DMM2"])

                #PSU Delay? (Up/Down Time -> Not yet configured)
                Delay(dict["PSU"]).write(dict["DownTime"])
                WAI(dict["PSU"])

                I += float(dict["current_step_size"])
                j += 1
                k += 1

                #if V_fixed == 0:
                #    powermeasure = float ((float(temp_values) + float(dict["voltage_step_size"]) ) * currentmeasured)
                #    I=0.001
                #else:
                #    powermeasure = float ((float(temp_values) + float(dict["voltage_step_size"]) ) * I)

                #Limit V/I if power test exceeded
                powermeasure = V_fixed * I       

                if powermeasure > self.Power:
                    break

            V_fixed += float(dict["voltage_step_size"])
            i += 1

        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Voltage(dict["ELoad"]).setOutputVoltage(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
        RST(dict["DMM2"])
        WAI(dict["DMM2"])

        return self.infoList, self.dataList, self.dataList2
    
class HornbillCurrentMeasurementwithELoad_IMON_2mA :
    def __init__(self):
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    def Execute_Current_Accuracy_Current_Static(self, dict, channel):
        """Execution of Current Measurement for Programm / Readback Accuracy using Status Event Registry to synchronize Instrument

        The function first declares two lists, datalist & infolist that will be used to collect data.
        It then dynamically imports the library to be used. Next, the settings for all Instrument
        are initialized. The test loop begins where Voltage and Current Sweep is conducted and collect
        measured data.

        The synchronization of Instrument here is done by reading the status of the event registry.
        The status determined from the Instrument can let the program determine if the Instrument is
        measuring. The program will only proceed to tell the Instrument to query the measured value
        after it is determined that the measurement has been completed. This method is suitable for
        operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
        more complicated than other methods. This method only can be implemented that have the specific
        commands that are used.

        In line 605, where V_fixed - 0.001 * V_fixed is done to prevent the ELoad from causing the DUT
        to enter CV Mode.

        Args:
            Instrument: String determining which library to be used.
            Error_Gain: Float determining the error gain of the Readback Voltage Specification.
            Error_Offset: Float determining the error offset of the Readback Voltage Specification.
            minCurrent: Float determining the start current for Current Sweep.
            maxCurrent: Float determining the stop current for Current Sweep.
            current_stepsize: Float determining the step size during Current Sweep.
            minVoltage: Float determining the start voltage for Voltage Sweep.
            maxVoltage: Float determining the stop voltage for Voltage Sweep.
            voltage_stepsize: Float determining the step_size for Voltage_Sweep.
            PSU: String containing the VISA Address of the PSU used.
            DMM: String containing the VISA Address of the DMM used.
            ELoad: String containing the VISA Address of the ELoad used.
            "ELoad_Channel: Integer containing the channel number that the ELoad is using.
            PSU_Channel: Integer containing the channel number that the PSU is using.
            setCurrent_Sense: String determining the Current Sense that will be used.
            setCurrent_Res: String determining the Current Resolution that will be used.
            setMode: String determining the Priority mode of the ELoad.
            Range: String determining the measuring range of the DMM should be Auto or a specific range.
            Apreture: String determining the NPLC to be used by DMM when measuring.
            AutoZero: String determining if AutoZero Mode on DMM should be enabled/disabled.
            InputZ: String determining the Input Impedance Mode of DMM.
            UpTime: Float containing details regarding the uptime delay.
            DownTime: Float containing details regarding the downtime delay.
            current_iter: integer storing the number of iterations of current sweep.
            voltage_iter: integer storing the number of iterations of voltage sweep.
            status: float storing the value returned by the status event registry.
            infoList: List containing the programmed data that was set by Program.
            dataList: List containing the measured data that was queried from DUT.

        Returns:
            Returns two list, DataList & InfoList. Each containing the programmed & measured data individually.

        Raises:
            VisaIOError: An error occured when opening PyVisa Resources.
        """
        # Dynamic Library Import
        (
            Read,
            Apply,
            Display,
            Function,
            Frequency,
            Output,
            Measure,
            Sense,
            Configure,
            Delay,
            Trigger,
            Sample,
            Initiate,
            Fetch,
            Status,
            Voltage,
            Current,
            Oscilloscope,
            Excavator,
            SMU,
            Power,
            Hornbill
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM2"])
        WAI(dict["DMM2"])

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #delay
        

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        #offset
        sleep(3)

        # Instrument Initialization
        Configure(dict["DMM2"]).write("Voltage")
        Trigger(dict["DMM2"]).setSource("BUS")
        Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])
         #Instrument Channel Set
        Voltage(dict["PSU"]).setInstrumentChannel(ch)
        Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
        sleep(2)
        #Display(dict["ELoad"]).displayState(dict["ELoad_Channel"])
        Function(dict["ELoad"]).setMode("Voltage")
        Function(dict["PSU"]).setMode("Current")

        #Set Series/Parallel Mode
        if dict["OperationMode"] == "Series":
            Output(dict["PSU"]).SPModeConnection("SER")
            WAI(dict["PSU"])
        elif dict["OperationMode"] == "Parallel":
            Output(dict["PSU"]).SPModeConnection("PAR")
            WAI(dict["PSU"])
        else:
            Output(dict["PSU"]).SPModeConnection("OFF")
            WAI(dict["PSU"])
        
        #Set Channel, Sense
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
        Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])

        Voltage(dict["DMM2"]).setNPLC(dict["Aperture"])
        Voltage(dict["DMM2"]).setAutoZeroMode(dict["AutoZero"])
        Voltage(dict["DMM2"]).setAutoImpedanceMode(dict["InputZ"])
        #Current(dict["DMM"]).setTerminal(dict["Terminal"])

        if dict["Range"] == "Auto":
            Sense(dict["DMM2"]).setVoltageRangeDCAuto()
        else:
            Sense(dict["DMM2"]).setVoltageRangeDC(dict["Range"])
        
        self.param1 = float(dict["Programming_Error_Gain"])
        self.param2 = float(dict["Programming_Error_Offset"])
        self.param3 = float(dict["Readback_Error_Gain"])
        self.param4 = float(dict["Readback_Error_Offset"])
        self.unit = dict["unit"]
        self.updatedelay = float(dict["updatedelay"])

        # Test Loop
        self.Power = float(dict["power"])
        self.rshunt = float(dict["rshunt"])
        i = 0
        j = 0
        k = 0
        V_fixed = float(dict["minVoltage"])
        # V = float(dict["maxVoltage"]) + 1
        I = float(dict["minCurrent"])

        if self.rshunt == 0.01: #(100A) (1V + cable loss)
            VshuntdropMax = 2
        elif self.rshunt == 0.05:#(50A) (2.5V + cable loss)
            VshuntdropMax = 3.5
        elif self.rshunt == 1: #(10A)  (10V + cable loss)
            VshuntdropMax = 11

        current_iter = (
            (float(dict["maxCurrent"]) - float(dict["minCurrent"]))
            / float(dict["current_step_size"])
        ) + 1
        voltage_iter = (
            (float(dict["maxVoltage"]) - float(dict["minVoltage"]))
            / float(dict["voltage_step_size"])
        ) + 1
        sleep(1)

        psu = Hornbill(dict["PSU"])
        #Current LIMIT (Max for Voltage Accuracy)
        psu.sourVoltageLevelImmediateAmplitude("MAXimum", ch)
        WAI(dict["PSU"])

        #Turn On the PSU and Eload
        psu.outputState("ON", ch)
        WAI(dict["PSU"])
        sleep(3)

        while i < voltage_iter:

            j = 0
            I = float(dict["minCurrent"])

            if V_fixed> float(dict["maxVoltage"]):
                V_fixed = float(dict["maxVoltage"])

            # Setting to prevent draw to much voltage
            if V_fixed == 0:
                Voltage(dict["ELoad"]).setOutputVoltage(1)
                WAI(dict["ELoad"])
            elif V_fixed == float(dict["maxVoltage"]):
                Voltage(dict["ELoad"]).setOutputVoltage(V_fixed-VshuntdropMax)
                WAI(dict["ELoad"])
            else:
                Voltage(dict["ELoad"]).setOutputVoltage(V_fixed)
                WAI(dict["ELoad"])

            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])
            sleep(3)

            while j < current_iter:
                sleep()
                if I> float(dict["maxCurrent"]):
                    I = float(dict["maxCurrent"])
                    
                psu.sourCurrentLimitPOS(I, ch)
                WAI(dict["PSU"])
                
                #print("Voltage: ", V_fixed, "Current: ", I)
                self.infoList.insert(k, [V_fixed, I, i])
                #offset
                sleep(0.2)
                sleep(self.updatedelay)

                """#PSU ReadBack
                temp_values = Measure(dict["PSU"]).singleChannelQuery("VOLT")
                WAI(dict["PSU"])
                temp_values2 = Measure(dict["PSU"]).singleChannelQuery("CURR")
                WAI(dict["PSU"])

                self.dataList2.insert(k, [float(temp_values), float(temp_values2)])"""
                
                #Readback Voltage and Current
                cleandiagVmon, cleandiagImon = _measure_hornbill_readback(
                    psu, dict, ch, current_input="2mA"
                )
                print("Voltage Monitor Reading =", cleandiagVmon)
                WAI(dict["PSU"])
                print("Current Monitor Reading =", cleandiagImon)
                WAI(dict["PSU"])

                #DMM Condition & Measurements
                Initiate(dict["DMM2"]).initiate()
                status = float(Status(dict["DMM2"]).operationCondition())
                TRG(dict["DMM2"])

                sleep(1)
                #self.dataList2.insert(k, [float(temp_values), float(temp_values2)])
                self.dataList2.insert(k, [float(cleandiagVmon), float(cleandiagImon)])

                while 1:
                    status = float(Status(dict["DMM2"]).operationCondition())
                    
                    if status == 8704.0:
                        voltagemeasured = float(Fetch(dict["DMM2"]).query())
                        currentmeasured = voltagemeasured/self.rshunt
                        self.dataList.insert(

                            k, [0 , currentmeasured]
                        )
                        break

                    elif status == 512.0:
                        voltagemeasured = float(Fetch(dict["DMM2"]).query())
                        currentmeasured = voltagemeasured/self.rshunt
                        self.dataList.insert(
                            
                            k, [0 , currentmeasured]
                        )
                        break
                
                WAI(dict["DMM2"])

                #PSU Delay? (Up/Down Time -> Not yet configured)
                Delay(dict["PSU"]).write(dict["DownTime"])
                WAI(dict["PSU"])

                I += float(dict["current_step_size"])
                j += 1
                k += 1

                #if V_fixed == 0:
                #    powermeasure = float ((float(temp_values) + float(dict["voltage_step_size"]) ) * currentmeasured)
                #    I=0.001
                #else:
                #    powermeasure = float ((float(temp_values) + float(dict["voltage_step_size"]) ) * I)

                #Limit V/I if power test exceeded
                powermeasure = V_fixed * I       

                if powermeasure > self.Power:
                    break

            V_fixed += float(dict["voltage_step_size"])
            i += 1

        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Voltage(dict["ELoad"]).setOutputVoltage(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
        RST(dict["DMM2"])
        WAI(dict["DMM2"])

        return self.infoList, self.dataList, self.dataList2
