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
from time import sleep, time
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from SCPI_Library.IEEEStandard import OPC, WAI, TRG, RST, CLS
from SCPI_Library.Keysight import *

#Dictionary
class dictGenerator(object):
    """Accept the Parameters Input from GUI"""
    def __init__():
        pass

    def input(**kwargs):
        return kwargs

#Import SCPI command list
class Dimport:
    """Import SCPI Library py class to DUT_Test"""

    def __init__():
        pass

    def getClasses(module_name):
        """Declare the module based on the module name given

        Args:
            module_name: Determines which library will the program import from

        Returns:
            Returns a set of Modules imported from a library
        """

        module_full_name = f"SCPI_Library.{module_name}"
        module = __import__(module_full_name, fromlist=["*"])
        Read = getattr(module, "Read")
        Apply = getattr(module, "Apply")
        Display = getattr(module, "Display")
        Function = getattr(module, "Function")
        Frequency = getattr(module, "Frequency")
        Output = getattr(module, "Output")
        Measure = getattr(module, "Measure")
        Sense = getattr(module, "Sense")
        Configure = getattr(module, "Configure")
        Delay = getattr(module, "Delay")
        Trigger = getattr(module, "Trigger")
        Sample = getattr(module, "Sample")
        Initiate = getattr(module, "Initiate")
        Fetch = getattr(module, "Fetch")
        Status = getattr(module, "Status")
        Voltage = getattr(module, "Voltage")
        Current = getattr(module, "Current")
        Oscilloscope = getattr(module, "Oscilloscope")
        Excavator = getattr(module, "Excavator")
        SMU = getattr(module, "SMU")
        Power = getattr(module, "Power")

        return (
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
        )

#Check Visa IO address
class VisaResourceManager:
    """Manage the VISA Resources

    Attributes:
        args: args should contain one or multiple string containing the Visa Address of an dict["Instrument"]

    """

    def __init__(self):
        """Initiate the object rm as Resource Manager"""
        rm = pyvisa.ResourceManager()
        self.rm = rm

    def openRM(self, *args):
        """Open the VISA Resources to be used

        The program also initiates and standardize certain specifications such as the baud rate.

            Args:
                *args: to declare single or multiple VISA Resources

            Returns:
                Return a Boolean to the program whether there were any errors encountered.

            Raises:
                VisaIOError: An error occured when opening PyVisa Resources

        """
        try:
            for i in range(len(args)):
                instr = self.rm.open_resource(args[i])
                instr.baud_rate = 9600

            return 1, None
        except pyvisa.VisaIOError as e:
            print(e.args)
            return 0, e.args

    def closeRM(self):
        """Closes the Visa Resources when not in used"""
        self.rm.close()

######################################################################
class NewVoltageMeasurement:

    def __init__(self):
        self.results = []
        self.infoList = []
        self.dataList = []
        self.dataList2 = []
        self.running = True #Shamman changes

    def Execute_Voltage_Accuracy(self, dict, channel, worker=None):
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
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")
        
        #New Command 
        """ Excavator(dict["PSU"]).setSYSTEMEMULationMode("SOUR")
        WAI(dict["PSU"])
        Excavator(dict["ELoad"]).setSYSTEMEMULationMode("LOAD")
        WAI(dict["ELoad"])"""
        #offset
        sleep(3)

        # Instrument Initialization
        Configure(dict["DMM"]).write("Voltage")
        Trigger(dict["DMM"]).setSource("BUS")
        Sense(dict["DMM"]).setVoltageResDC(dict["VoltageRes"])
        Function(dict["ELoad"]).setMode("Current")
        Function(dict["PSU"]).setMode("Voltage")

        #Instrument Channel Set
        Voltage(dict["PSU"]).setInstrumentChannel(ch)
        Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
        sleep(2)

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

        #Set Current and Sense Mode
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
        Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])

        #DMM Mode
        Voltage(dict["DMM"]).setNPLC(dict["Aperture"])
        Voltage(dict["DMM"]).setAutoZeroMode(dict["AutoZero"])
        Voltage(dict["DMM"]).setAutoImpedanceMode(dict["InputZ"])

        if dict["Range"] == "Auto":
            Sense(dict["DMM"]).setVoltageRangeDCAuto()
        else:
            Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])

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
        I_fixedOS = 0                               #Offset Current (Manually Added)
        I_fixed = float(dict["minCurrent"])         #Min Current
        V = float(dict["minVoltage"])
        I = float(dict["maxVoltage"]) + 1

        temp_values = 0
        temp_values2 = 0

        current_iter = (
            (float(dict["maxCurrent"]) - float(dict["minCurrent"]))
            / float(dict["current_step_size"])
        ) + 1
        voltage_iter = (
            (float(dict["maxVoltage"]) - float(dict["minVoltage"]))
            / float(dict["voltage_step_size"])
        ) + 1
        sleep(1)

        #Current LIMIT (Max for Voltage Accuracy)
        Current(dict["PSU"]).setOutputCurrent("MAXimum")
        WAI(dict["PSU"])
        
        #Turn On the PSU and Eload
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("ON")
        WAI(dict["ELoad"])

        #Clear the Error Status
        CLS(dict["PSU"])
        WAI(dict["PSU"])
        CLS(dict["ELoad"])
        WAI(dict["ELoad"])
        CLS(dict["DMM"])
        WAI(dict["DMM"])
        
        #Run Test (Voltage Loop in Current Loop)
        while i < current_iter:
            j = 0
            V = float(dict["minVoltage"])
            Iset = float(Current(dict["PSU"]).SourceCurrentLevel()) #Query Current Level

            if I_fixed > float(dict["maxCurrent"]):
                I_fixed = float(dict["maxCurrent"])

            #If minimum current is 0, set to 1A
            if I_fixed == 0:           
                I_fixedOS = 1
                I_fixed = I_fixed + I_fixedOS

            #If PSU MAX I = ELOAD MAX I (Reduce Eload I by 0.1 - Prevent Overload)
            if I_fixed == float(dict["maxCurrent"]) and Iset == float(dict["maxCurrent"]):
                Current(dict["ELoad"]).setOutputCurrent(I_fixed - 0.1)
                WAI(dict["ELoad"])
            else:
                Current(dict["ELoad"]).setOutputCurrent(I_fixed)
                WAI(dict["ELoad"])

            sleep(1)

            #Voltage Iteration
            while j < voltage_iter:

                #Set Voltage and Current
                if V > float(dict["maxVoltage"]):
                    V = float(dict["maxVoltage"])
                    
                Voltage(dict["PSU"]).setOutputVoltage( V )
                WAI(dict["PSU"])
                self.infoList.insert(k, [V, I_fixed, i])

                #Timeout/Delay-----------------------------------------?
                #Delay(dict["PSU"]).write(dict["UpTime"])
                #WAI(dict["PSU"])
                sleep(0.2)
                sleep(float(self.updatedelay))

                #Readback Voltage and Current
                temp_values = float(Measure(dict["PSU"]).multipleChannelQuery(ch,"VOLT"))
                WAI(dict["PSU"])
                temp_values2 = float(Measure(dict["PSU"]).multipleChannelQuery(ch,"CURR"))
                WAI(dict["PSU"])
                sleep(1)
                self.dataList2.insert(k, [float(temp_values), float(temp_values2)])
                
                #INIT DMM (Trigger Measurement)
                Initiate(dict["DMM"]).initiate()
                status = float(Status(dict["DMM"]).operationCondition())
                sleep(1)
                #print(status)
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

                if worker is not None:
                    prog_percent = (voltagemeasured - V)/V*100
                    read_percent = (temp_values - voltagemeasured)/voltagemeasured*100
                    prog_upper_bound = (V*self.param1) + self.param2
                    prog_lower_bound = -prog_upper_bound
                    read_upper_bound = (V*self.param3) + self.param4
                    read_lower_bound = -read_upper_bound
                    perc_up_bound = 100
                    perc_low_bound = -100
                    worker.new_data.emit(V, I_fixed, temp_values, voltagemeasured, temp_values2, voltagemeasured - V, temp_values - voltagemeasured, prog_percent, read_percent, prog_upper_bound, prog_lower_bound, read_upper_bound, read_lower_bound, perc_up_bound, perc_low_bound)
                    worker.popup_data.emit(voltagemeasured - V, temp_values - voltagemeasured, prog_upper_bound, prog_lower_bound, read_upper_bound, read_lower_bound, prog_percent, read_percent, perc_up_bound, perc_low_bound)

                WAI(dict["DMM"])

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

        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent("MIN")
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])

        return self.infoList, self.dataList, self.dataList2

class NewCurrentMeasurement:
    def __init__(self):
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    def executeCurrentMeasurementA(self, dict, channel, worker=None):
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
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        #New Command 
        """ Excavator(dict["PSU"]).setSYSTEMEMULationMode("SOUR")
        WAI(dict["PSU"])
        Excavator(dict["ELoad"]).setSYSTEMEMULationMode("LOAD")
        WAI(dict["ELoad"])"""
        #offset
        sleep(3)

        # Instrument Initialization
        Configure(dict["DMM2"]).write("Voltage")
        Trigger(dict["DMM2"]).setSource("BUS")
        Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])
        #Display(dict["ELoad"]).displayState(dict["ELoad_Channel"])
        Function(dict["ELoad"]).setMode("Voltage")
        Function(dict["PSU"]).setMode("Current")

        #Instrument Channel Set         #Shamman changes
        Voltage(dict["PSU"]).setInstrumentChannel(ch)
        Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
        sleep(2)

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
        #V = float(dict["maxCurrent"]) + 1
        I = float(dict["minCurrent"])

        temp_values = 0 #V_programming
        temp_values2 = 0 #I_readback

        if self.rshunt == 0.01: #(100A) (1V + cable loss)
            VshuntdropMax = 2
        elif self.rshunt == 0.05:#(50A) (2.5V + cable loss)
            VshuntdropMax = 3.5
        elif self.rshunt == 1: #(10A)  (10V + cable loss)
            VshuntdropMax == 11

        current_iter = (
            (float(dict["maxCurrent"]) - float(dict["minCurrent"]))
            / float(dict["current_step_size"])
        ) + 1
        voltage_iter = (
            (float(dict["maxVoltage"]) - float(dict["minVoltage"]))
            / float(dict["voltage_step_size"])
        ) + 1
        sleep(1)

        Voltage(dict["PSU"]).setOutputVoltage("MAXimum") #Set Vmax at PSU
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent("MINimum")
        WAI(dict["PSU"])

        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("ON")
        WAI(dict["ELoad"])

        #Clear the Error Status
        CLS(dict["PSU"])
        WAI(dict["PSU"])
        CLS(dict["ELoad"])
        WAI(dict["ELoad"])
        CLS(dict["DMM"])
        WAI(dict["DMM"])
        
        while i < voltage_iter:

            j = 0
            I = float(dict["minCurrent"])
            Vset = float(Voltage(dict["PSU"]).SourceVoltageLevel())  #Shamman changes
            
            if V_fixed > float(dict["maxVoltage"]):
                V_fixed = float(dict["maxVoltage"])

            # Setting to prevent draw to much voltage
            if V_fixed == 0:
                Voltage(dict["ELoad"]).setOutputVoltage(1)
                WAI(dict["ELoad"])

            elif V_fixed == float(dict["maxVoltage"]) and Vset == float(dict["maxVoltage"]):   #Shamman changes
                Voltage(dict["ELoad"]).setOutputVoltage(V_fixed-VshuntdropMax)
                WAI(dict["ELoad"])
            else:
                Voltage(dict["ELoad"]).setOutputVoltage(V_fixed)
                WAI(dict["ELoad"])

            '''Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])'''
            sleep(1)

            while j < current_iter:

                if I> float(dict["maxCurrent"]):
                    I = float(dict["maxCurrent"])
                    
                Current(dict["PSU"]).setOutputCurrent(I)
                WAI(dict["PSU"])
                
                #print("Voltage: ", V_fixed, "Current: ", I)
                self.infoList.insert(k, [V_fixed, I, i])
                #offset
                sleep(0.2)
                sleep(float(self.updatedelay))

                #PSU ReadBack
                temp_values = float(Measure(dict["PSU"]).multipleChannelQuery(ch,"VOLT"))
                WAI(dict["PSU"])
                temp_values2 = float(Measure(dict["PSU"]).multipleChannelQuery(ch,"CURR"))
                WAI(dict["PSU"])
                sleep(1)
                self.dataList2.insert(k, [float(temp_values), float(temp_values2)])
                
                #DMM Condition & Measurements
                Initiate(dict["DMM2"]).initiate()
                status = float(Status(dict["DMM2"]).operationCondition())
                sleep(1)
                TRG(dict["DMM2"])

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

                if worker is not None:
                    worker.new_data.emit(V_fixed, I, temp_values, currentmeasured, temp_values2, currentmeasured - I, temp_values - currentmeasured)
                
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
                powermeasure = float(V_fixed * I)       

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

class LoadRegulation:
    def __init__(self):
        pass

    def executeCV_LoadRegulationA(self, dict):
        """Test for determining the Load Regulation of DUT under Constant Voltage (CV) Mode.

        The function first dynamically imports the library to be used. Next, settings for the
        Instruments will be initialized. The test begins by measuring the No Load Voltage when
        the PSU is turned on at max nominal settings but ELoad is turned off. Then, the ELoad is
        turned on to drive the DUT to full load, while measuring the V_FullLoad, Calculations
        are then done to check the load regulation under CV condition.

        The synchronization of Instruments here is done by reading the status of the event registry.
        The status determined from the Instrument can let the program determine if the Instrument is
        measuring. The program will only proceed to tell the Instrument to query the measured value
        after it is determined that the measurement has been completed. This method is suitable for
        operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
        more complicated than other methods. This method only can be implemented that have the specific
        commands that are used.

        Args:
            Instrument: String determining which library to be used.
            Error_Gain: Float determining the error gain of the Load Regulation Specifications.
            Error_Offset: Float determining the error offset of the Load Regulation Specifications.
            V_Rating: Float containing the Rated Voltage of the DUT.
            I_Rating: Float containing the Rated Current of the DUT.
            P_Rating: Float containing the Rated Power of the DUT.
            PSU: String containing the VISA Address of PSU used.
            DMM: String containing the VISA Address of dictDMM used.
            ELoad: String containing the VISA Address of ELoad used.
            PSU_Channel: Integer containing the channel number that the PSU is using.
            ELoad_Channel: Integer containing the channel number that the ELoad is using.
            setVoltage_Sense: String determining the Voltage Sense that is used.
            VoltageRes: String determining the Voltage Resolution that is used.
            setMode: String determining the Priority Mode of the ELoad.
            Range: String determining the measuring range of DMMshould be Auto or specified range.
            Apreture: String determining the NPLC to be used by DMM when measuring.
            AutoZero: String determining if AutoZero Mode on DMM should be enabled/disabled.
            InputZ: String determining the Input Impedance Mode of DMM.
            UpTime: Float containing details regarding the uptime delay.
            DownTime: Float containing details regarding the downtime delay.
            I_Max: Float storing the maximum nominal current value based on Power & Voltage Rating
            V_NL: Float storing the measured voltage during no load.
            V_FL: Float storing the measured voltage during full load.

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
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])

        #New Command 
        Excavator(dict["PSU"]).setSYSTEMEMULationMode("SOUR")
        WAI(dict["PSU"])
        Excavator(dict["ELoad"]).setSYSTEMEMULationMode("LOAD")
        WAI(dict["ELoad"])
        #offset
        sleep(3)

        # Instrument Initializations
        #Configure(dict["DMM"]).write("Voltage")
        Trigger(dict["DMM"]).setSource("BUS")
        Sense(dict["DMM"]).setVoltageResDC("DEF")
        #Display(dict["ELoad"]).displayState(dict["ELoad_Channel"])
        Function(dict["ELoad"]).setMode("Current")
        Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])

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
        
        Voltage(dict["PSU"]).setInstrumentChannel(dict["PSU_Channel"])
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["PSU_Channel"])

        Voltage(dict["DMM"]).setNPLC(dict["Aperture"])
        Voltage(dict["DMM"]).setAutoZeroMode(dict["AutoZero"])
        Voltage(dict["DMM"]).setAutoImpedanceMode(dict["InputZ"])

        if dict["Range"] == "Auto":
            Sense(dict["DMM"]).setVoltageRangeDCAuto()

        else:
            Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])

        self.V_Rating = float(dict["V_Rating"])
        self.I_Rating = float(dict["I_Rating"])
        self.P_Rating = float(dict["P_Rating"])

        self.powerfin = int(dict["power"])
        self.voltagemax = float(dict["maxVoltage"])
        self.currentmax = float(dict["maxCurrent"])
        
        self.param1 = float(dict["Load_Programming_Error_Gain"])
        self.param2 = float(dict["Load_Programming_Error_Offset"])
        self.updatedelay = float(dict["updatedelay"])

        IL_reducer = 0.05

###############################################################################################
        #High Voltage Low Current
        I_Max = round(self.powerfin / self.voltagemax, 2)
        Current(dict["PSU"]).setOutputCurrent(I_Max)
        WAI(dict["PSU"])
        Voltage(dict["PSU"]).setOutputVoltage(self.voltagemax)
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])

        sleep(self.updatedelay)

        #Apply(dict["PSU"]).write(dict["PSU_Channel"], self.V_Rating, self.I_Rating)
        #Output(dict["PSU"]).setOutputState("ON")

        # Reading for No Load - High Voltage Low Current
        Initiate(dict["DMM"]).initiate()
        TRG(dict["DMM"])
        V_NL_HighVoltage = float(Fetch(dict["DMM"]).query())

        #Reading for Full Load for High Voltage Low Current
        I_MaxL = round(I_Max - IL_reducer, 2)
        Current(dict["ELoad"]).setOutputCurrent(I_MaxL)
        WAI(dict["ELoad"])
        Output(dict["ELoad"]).setOutputState("ON")
        WAI(dict["ELoad"])

        sleep(self.updatedelay)

        Initiate(dict["DMM"]).initiate()
        TRG(dict["DMM"])
        V_FL_HighVoltage = float(Fetch(dict["DMM"]).query())
        
        sleep(self.updatedelay)

        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])

#################################################################################################################################
        #Low Voltage High Current
        V_Max = round(self.powerfin / self.currentmax,2)
        Current(dict["PSU"]).setOutputCurrent(self.currentmax)
        WAI(dict["PSU"])
        Voltage(dict["PSU"]).setOutputVoltage(V_Max)
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])

        sleep(float(self.updatedelay))

        #Apply(dict["PSU"]).write(dict["PSU_Channel"], self.V_Rating, self.I_Rating)
        #Output(dict["PSU"]).setOutputState("ON")

        # Reading for No Load - High Current Low voltage
        Initiate(dict["DMM"]).initiate()
        TRG(dict["DMM"])
        V_NL_LowVoltage = float(Fetch(dict["DMM"]).query())


        #Reading for Full Load for High Current Low voltage
        Current(dict["ELoad"]).setOutputCurrent(self.currentmax-IL_reducer)
        WAI(dict["ELoad"])
        Output(dict["ELoad"]).setOutputState("ON")
        WAI(dict["ELoad"])

        sleep(float(self.updatedelay))

        Initiate(dict["DMM"]).initiate()
        TRG(dict["DMM"])
        WAI(dict["ELoad"])
        V_FL_LowVoltage = float(Fetch(dict["DMM"]).query())
        
        sleep(float(self.updatedelay))

        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
        
        
        Voltage_Regulation_HighVoltage = (V_FL_HighVoltage - V_NL_HighVoltage)
        Voltage_Regulation_LowVoltage = (V_FL_LowVoltage - V_NL_LowVoltage)
        Desired_Voltage_Regulation_HighVoltage = ((float(self.voltagemax) * self.param1) + (float(self.V_Rating) * self.param2))
        Desired_Voltage_Regulation_LowVoltage = ((float(V_Max) * self.param1) + (float(self.V_Rating) * self.param2))

        print(" ")
        print("Voltage Regulation Configuration for High Voltage Low Current", self.voltagemax, "V @ ", I_Max, "A")
        print("V_NL_High Voltage Low Current: ", V_NL_HighVoltage, "V_FL_High Voltage Low Current: ", V_FL_HighVoltage)
        print("Desired Voltage Regulation for High Voltage (CV): (V)", Desired_Voltage_Regulation_HighVoltage)
        print("Calculated Voltage Regulation for High Voltage (V):", Voltage_Regulation_HighVoltage)

        print(" ")
        print("Voltage Regulation Configuration for Low Voltage High Current", V_Max, "V", self.currentmax, "A")
        print("V_NL_Low Voltage High Current: ", V_NL_LowVoltage, "V_FL_Low Voltage High Current: ", V_FL_LowVoltage)      
        print("Desired Voltage Regulation for Low Voltage (CV): (V)", Desired_Voltage_Regulation_LowVoltage)
        print("Calculated Voltage Regulation for Low Voltage (V):", Voltage_Regulation_LowVoltage)

        # Data to be saved
        data = [
            ["Load Regulation Voltage (CV)"],
            ["Voltage Regulation Configuration for High Voltage Low Current", self.voltagemax, "V", I_Max, "A"],
            ["V_No_Load_High Voltage Low Current", V_NL_HighVoltage], 
            ["V_Full_lLoad_High Voltage Low Current", V_FL_HighVoltage],
            ["Desired Voltage Regulation for High Voltage (CV) (V)", Desired_Voltage_Regulation_HighVoltage],
            ["Calculated Voltage Regulation for High Voltage (V)", Voltage_Regulation_HighVoltage],
            [""],
            ["Voltage Regulation Configuration for Low Voltage High Current", V_Max, "V", self.currentmax, "A"],
            ["V_No_Load_Low Voltage High Current", V_NL_LowVoltage],
            ["V_Full_Load_Low Voltage High Current", V_FL_LowVoltage],
            ["Desired Voltage Regulation for Low Voltage (CV) (V)", Desired_Voltage_Regulation_LowVoltage],
            ["Calculated Voltage Regulation for Low Voltage (V)", Voltage_Regulation_LowVoltage]
        ]

        # Save path
        #save_path = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing/"
        save_path = str(dict["savedir"])

        # Get current time to add to the file name
        current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

        # Save data to CSV file
        csv_file = save_path + f"/Voltage_Regulation_{current_time}.csv"
        with open(csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)

        """# Generate Excel sheet from CSV file
        excel_file = save_path + f"voltage_regulation_{current_time}.xlsx"
        df = pd.read_csv(csv_file)
        df.to_excel(excel_file, index=False)"""



    def executeCC_LoadRegulationA(self, dict):
        """Test for determining the Load Regulation of DUT under Constant Current (CC) Mode.

        The function first dynamically imports the library to be used. Next, settings for the
        Instrument will be initialized. The test begins by measuring the No Load Voltage when
        the PSU is turned on at max nominal settings but ELoad is turned off. Then, the ELoad is
        turned on to drive the DUT to full load, while measuring the V_FullLoad, Calculations
        are then done to check the load regulation under CC condition.

        The synchronization of Instrument here is done by reading the status of the event registry.
        The status determined from the Instrument can let the program determine if the Instrument is
        measuring. The program will only proceed to tell the Instrument to query the measured value
        after it is determined that the measurement has been completed. This method is suitable for
        operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
        more complicated than other methods. This method only can be implemented that have the specific
        commands that are used.

        Args:
            Instrument: String determining which library to be used.
            Error_Gain: Float determining the error gain of the Load Regulation Specifications.
            Error_Offset: Float determining the error offset of the Load Regulation Specifications.
            V_Rating: Float containing the Rated Voltage of the DUT.
            I_Rating: Float containing the Rated Current of the DUT.
            P_Rating: Float containing the Rated Power of the DUT.
            PSU: String containing the VISA Address of PSU used.
            DMM: String containing the VISA Address of DMM used.
            ELoad: String containing the VISA Address of ELoad used.
            PSU_Channel: Integer containing the channel number that the PSU is using.
            ELoad_Channel: Integer containing the channel number that the ELoad is using.
            setVoltage_Sense: String determining the Voltage Sense that is used.
            setCurrent_Res: String determining the Current Resolution that is used.
            setMode: String determining the Priority Mode of the ELoad.
            Range: String determining the measuring range of DMM should be Auto or specified range.
            Apreture: String determining the NPLC to be used by DMM when measuring.
            AutoZero: String determining if AutoZero Mode on DMM should be enabled/disabled.
            InputZ: String determining the Input Impedance Mode of DMM.
            UpTime: Float containing details regarding the uptime delay.
            DownTime: Float containing details regarding the downtime delay.
            V_Max: Float storing the maximum nominal voltage value based on Power & Voltage Rating
            I_NL: Float storing the measured current during no load.
            I_FL: Float storing the measured current during full load.

        Raises:
            VisaIOError: An error occured when opening PyVisa Resources.

        """
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
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM2"])
        WAI(dict["DMM2"])

        #New Command 
        Excavator(dict["PSU"]).setSYSTEMEMULationMode("SOUR")
        WAI(dict["PSU"])
        Excavator(dict["ELoad"]).setSYSTEMEMULationMode("LOAD")
        WAI(dict["ELoad"])
        #offset
        sleep(3)

        # Fixed Settings
        #Configure(dict["DMM2"]).write("Voltage")
        Trigger(dict["DMM2"]).setSource("BUS")
        Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])
        #Display(dict["ELoad"]).displayState(dict["ELoad_Channel"])
        #Function(dict["ELoad"]).setMode(dict["setFunction"])
        Function(dict["ELoad"]).setMode("Voltage")
        Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])

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
        
        Voltage(dict["PSU"]).setInstrumentChannel(dict["PSU_Channel"])
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["PSU_Channel"])
        Voltage(dict["DMM2"]).setNPLC(dict["Aperture"])
        Voltage(dict["DMM2"]).setAutoZeroMode(dict["AutoZero"])
        Voltage(dict["DMM2"]).setAutoImpedanceMode(dict["InputZ"])
        #Voltage(dict["DMM"]).setTerminal(dict["Terminal"])

        if dict["Range"] == "Auto":
            Sense(dict["DMM2"]).setCurrentRangeDCAuto()

        else:
            Sense(dict["DMM2"]).setCurrentRangeDC(dict["Range"])

        self.V_Rating = float(dict["V_Rating"])
        self.I_Rating = float(dict["I_Rating"])
        self.P_Rating = float(dict["P_Rating"])

        self.powerfin = int(dict["power"])
        self.voltagemax = float(dict["maxVoltage"])
        self.currentmax = float(dict["maxCurrent"])

        self.param1 = float(dict["Programming_Error_Gain"])
        self.param2 = float(dict["Programming_Error_Offset"])
        self.param3 = float(dict["Readback_Error_Gain"])
        self.param4 = float(dict["Readback_Error_Offset"])
        self.updatedelay = float(dict["updatedelay"])
        self.rshunt = float(dict["rshunt"])

        if self.rshunt == 0.01: #(100A) (1V + cable loss)
            VshuntdropMax = 2
        elif self.rshunt == 0.05:#(50A) (2.5V + cable loss)
            VshuntdropMax = 3.5
        elif self.rshunt == 1: #(10A)  (10V + cable loss)
            VshuntdropMax == 11

        ############################################################################################################
        #No Load Test (Light Load) - Test For High Current Low Voltage
        V_Max = round(self.powerfin / self.currentmax, 2)
        Voltage(dict["PSU"]).setOutputVoltage(V_Max) 
        Current(dict["PSU"]).setOutputCurrent(self.currentmax)
        #Apply(dict["PSU"]).write(dict["PSU_Channel"], self.V_Rating, self.I_Rating)
        Voltage(dict["ELoad"]).setOutputVoltage(1) #Acting Light Load
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("ON")
        WAI(dict["ELoad"])

        sleep(self.updatedelay)
        # Reading for No Load Voltage

        Initiate(dict["DMM2"]).initiate()
        TRG(dict["DMM2"])
        I_NL_HighCurrent = float(Fetch(dict["DMM2"]).query())/self.rshunt

        ###########################################################################
        #Full Load Test - High Current Low Voltage
        Voltage(dict["ELoad"]).setOutputVoltage(V_Max - VshuntdropMax)
        WAI(dict["ELoad"])
        sleep(self.updatedelay)

        Initiate(dict["DMM2"]).initiate()
        TRG(dict["DMM2"])
        I_FL_HighCurrent = float(Fetch(dict["DMM2"]).query())/self.rshunt

        sleep(self.updatedelay)

        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        sleep(self.updatedelay)

        ############################################################################################################
        #No Load Test (Light Load) - Test For Low Current High Voltage
        I_Max = round(self.powerfin / self.voltagemax, 2)
        Voltage(dict["PSU"]).setOutputVoltage(self.voltagemax) 
        Current(dict["PSU"]).setOutputCurrent(I_Max)
        #Apply(dict["PSU"]).write(dict["PSU_Channel"], self.V_Rating, self.I_Rating)
        Voltage(dict["ELoad"]).setOutputVoltage(1) #Acting Light Load
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("ON")
        WAI(dict["ELoad"])

        sleep(self.updatedelay)
        # Reading for No Load Voltage

        Initiate(dict["DMM2"]).initiate()
        TRG(dict["DMM2"])
        Delay(dict["PSU"]).write(dict["UpTime"])
        I_NL_LowCurrent = float(Fetch(dict["DMM2"]).query())/self.rshunt

        sleep(self.updatedelay)

        ###########################################################################
        #Full Load Test - Low Current High Voltage
        Voltage(dict["ELoad"]).setOutputVoltage(self.voltagemax - VshuntdropMax)
        WAI(dict["ELoad"])

        sleep(self.updatedelay)

        Initiate(dict["DMM2"]).initiate()
        TRG(dict["DMM2"])
        I_FL_LowCurrent = float(Fetch(dict["DMM2"]).query())/self.rshunt
           
        Voltage(dict["ELoad"]).setOutputVoltage(0)
        WAI(dict["ELoad"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])

        Current_Regulation_HighCurrent = (I_FL_HighCurrent - I_NL_HighCurrent) 
        Current_Regulation_LowCurrent = (I_FL_LowCurrent - I_NL_LowCurrent)
        Desired_Current_Regulation_HighCurrent =( float(self.I_Rating) * (self.param1 + self.param2))
        Desired_Current_Regulation_LowCurrent = ((I_Max * self.param1) + (self.I_Rating*self.param2))

        print(" ")
        print("Current Regulation for High Current ", V_Max, "V @ ", self.currentmax,"A")
        print("I_NL_High Current: ", I_NL_HighCurrent, "I_FL_High Current: ", I_FL_HighCurrent)
        print("Desired Load Regulation High Current (CC): (A)", Desired_Current_Regulation_HighCurrent)
        print("Calculated Load Regulation High Current (CC): (A)", Current_Regulation_HighCurrent)
        print(" ")
        print("Current Regulation for Low Current ", self.voltagemax, "V @ ", I_Max,"A")
        print("I_NL_Low Current: ", I_NL_LowCurrent, "I_FL_Low Current: ", I_FL_LowCurrent)
        print("Desired Load Regulation Low Current (CC): (A)", Desired_Current_Regulation_LowCurrent)
        print("Calculated Load Regulation Low Current (CC): (A)", Current_Regulation_LowCurrent)

        # Data to be saved
        data = [
            ["Load Regulation Current (CV)"],
            ["Current Regulation Configuration for High Current", V_Max, "V", self.currentmax, "A"],
            ["I_NL_High Current", I_NL_HighCurrent], 
            ["I_FL_High Current", I_FL_HighCurrent],
            ["Desired Load Regulation High Current (CC): (A)", Desired_Current_Regulation_HighCurrent],
            ["Calculated Load Regulation High Current (CC): (A)", Current_Regulation_HighCurrent],
            [""],
            ["Current Regulation Configuration for Low Current ", self.voltagemax, "V", I_Max, "A"],
            ["I_NL_Low Current ", I_NL_LowCurrent],
            ["I_FL_Low Current", I_FL_LowCurrent],
            ["Desired Load Regulation Low Current (CC): (A)", Desired_Current_Regulation_LowCurrent],
            ["Calculated Load Regulation Low Current (CC): (A)", Current_Regulation_LowCurrent]
        ]

        # Save path
        #save_path = "C:/PyVisa - Copy  - Excavator - Copy/PyVisa/Test Data/File Export Testing/"
        save_path = str(dict["savedir"])

        # Get current time to add to the file name
        current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

        # Save data to CSV file
        csv_file = save_path + f"/Current_Regulation_{current_time}.csv"
        with open(csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)
        
        """# Generate Excel sheet from CSV file
        excel_file = save_path + f"voltage_regulation_{current_time}.xlsx"
        df = pd.read_csv(csv_file)
        df.to_excel(excel_file, index=False)"""

class PowerMeasurement:
    def __init__(self):
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    def executePowerMeasurementA(self, dict):
            """Execution of Voltage Measurement for Programm / Readback Accuracy using Status Event Registry to synchronize Instrument

            The function first declares two lists, datalist & infolist that will be used to collect data.
            It then dynamically imports the library to be used. Next, the settings for all Instrument
            are initialized. The test loop begins where Voltage and Current Sweep is conducted and collect
            measured data.

            The synchronization of Instruments here is done by reading the status of the event registry.
            The status determined from the Instrument can let the program determine if the Instrument is
            measuring. The program will only proceed to tell the Instrument to query the measured value
            after it is determined that the measurement has been completed. This method is suitable for
            operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
            more complicated than other methods. This method only can be implemented that have the specific
            commands that are used.

            In line 260, where I_fixed - 0.001 * I_fixed is done to prevent the ELoad from causing the DUT
            to enter CC Mode.

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
                ELoad_Channel: Integer containing the channel number that the ELoad is using.
                PSU_Channel: Integer containing the channel number that the PSU is using.
                setVoltage_Sense: String determining the Voltage Sense that will be used.
                VoltageRes: String determining the Voltage Resoltion that will be used.
                setMode: String determining the Priority mode of the ELoad.
                Range: String determining the measuring range of the DMM  should be Auto or a specific range.
                Apreture: String determining the NPLC to be used by DMM  when measuring.
                AutoZero: String determining if AutoZero Mode on DMM  should be enabled/disabled.
                InputZ: String determining the Input Impedance Mode of DMM .
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
            ) = Dimport.getClasses(dict["Instrument"])

            RST(dict["PSU"])
            WAI(dict["PSU"])
            
            RST(dict["ELoad"])
            WAI(dict["ELoad"])
            
            RST(dict["DMM"])
            WAI(dict["DMM"])
            
            #offset
            sleep(3)

            # Instrument Initializations
            Configure(dict["DMM2"]).write("Voltage")
            Trigger(dict["DMM2"]).setSource("BUS")
            Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])
            Function(dict["ELoad"]).setMode("Voltage")
            sleep(0.5)

            #Instrument Channel Set
            Voltage(dict["PSU"]).setInstrumentChannel(dict["PSU_Channel"])
            Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["PSU_Channel"])
            Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])
            Function(dict["PSU"]).setMode("Current")
            sleep(0.5)

            # Instrument Initialization
            #Configure(dict["DMM"]).write("Voltage")
            Trigger(dict["DMM"]).setSource("BUS")
            #Configure(dict["DMM2"]).write("Voltage")
            Trigger(dict["DMM2"]).setSource("BUS")
            Sense(dict["DMM"]).setVoltageResDC(dict["VoltageRes"])
            Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])
            #Display(dict["ELoad"]).displayState(dict["ELoad_Channel"])

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

            Function(dict["PSU"]).setMode("Voltage")
            Voltage(dict["PSU"]).setInstrumentChannel(dict["PSU_Channel"])
            Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["PSU_Channel"])

            Function(dict["ELoad"]).setMode("Current")
            Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
            Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])

            Voltage(dict["DMM"]).setNPLC(dict["Aperture"])
            Voltage(dict["DMM"]).setAutoZeroMode(dict["AutoZero"])
            Voltage(dict["DMM"]).setAutoImpedanceMode(dict["InputZ"])

            Voltage(dict["DMM2"]).setNPLC(dict["Aperture"])
            Voltage(dict["DMM2"]).setAutoZeroMode(dict["AutoZero"])
            Voltage(dict["DMM2"]).setAutoImpedanceMode(dict["InputZ"])

            if dict["Range"] == "Auto":
                Sense(dict["DMM"]).setVoltageRangeDCAuto()
                Sense(dict["DMM2"]).setVoltageRangeDCAuto()

            else:
                Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])
                Sense(dict["DMM2"]).setVoltageRangeDC(dict["Range"])

            self.param1 = float(dict["Programming_Error_Gain"])    #power gain and offset
            self.param2 = float(dict["Programming_Error_Offset"])
            self.param3 = float(dict["Readback_Error_Gain"])
            self.param4 = float(dict["Readback_Error_Offset"])
            self.unit = dict["unit"]
            self.updatedelay = float(dict["updatedelay"])

            #self.Power = float(dict["power"])
            self.powerini = int(dict["powerini"])
            self.powerfin = int(dict["powerfin"])
            self.powerstepsize = int(dict["power_step_size"])
            powerchange = 0
            counter = 1
            k=1

            self.rshunt = float(dict["rshunt"])
            self.currentmax = float(dict["maxCurrent"])
        

            #Test Start
            #Set Source and Eload Output
       
            Power(dict["PSU"]).setInputPower(0)
            WAI(dict["PSU"])
            Voltage(dict["PSU"]).setOutputVoltage("MAXimum")
            WAI(dict["PSU"])
            Current(dict["PSU"]).setOutputCurrent("MAXimum")
            WAI(dict["PSU"])

            #fixed current
            Current(dict["ELoad"]).setOutputCurrent(self.currentmax)
            WAI(dict["ELoad"])

            Output(dict["PSU"]).setOutputState("ON")
            WAI(dict["PSU"])
            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])


            for powerchange in range (self.powerini, self.powerstepsize + self.powerfin, self.powerstepsize):

                Power(dict["PSU"]).setInputPower(powerchange)
                WAI(dict["PSU"])

                #Save Set Programming Power
                self.infoList.insert(k, [counter , powerchange])
                self.OutputBox.append(str(counter))


                #Readback Power
                sleep(self.updatedelay)

                readback_power_temp_values = Measure(dict["PSU"]).singleChannelQuery("POW")
                
                WAI(dict["PSU"])
               
                self.dataList.insert(k,[float(readback_power_temp_values)])
                
                #DMM for measuring Voltage
                Initiate(dict["DMM"]).initiate()
                TRG(dict["DMM"])
                voltagemeasured = float(Fetch(dict["DMM"]).query())
                
                #DMM for measuring Current
                Initiate(dict["DMM2"]).initiate()
                TRG(dict["DMM2"])
                currentmeasured = float(Fetch(dict["DMM2"]).query())/self.rshunt
    
                #Store Measured Vottage and Current Data
                powermeasured = voltagemeasured * currentmeasured
                self.dataList2.insert(k,[voltagemeasured, currentmeasured, powermeasured])
                counter +=1
                k+=1

            Voltage(dict["PSU"]).setOutputVoltage(0)
            WAI(dict["PSU"])
            Current(dict["PSU"]).setOutputCurrent(0)
            WAI(dict["PSU"])
            Current(dict["ELoad"]).setOutputCurrent(0)
            WAI(dict["ELoad"])
            Output(dict["PSU"]).setOutputState("OFF")
            WAI(dict["PSU"])
            Output(dict["ELoad"]).setOutputState("OFF")
            WAI(dict["ELoad"])
            Output(dict["PSU"]).SPModeConnection("OFF")
            WAI(dict["PSU"])

            return self.infoList, self.dataList, self.dataList2


    def executePowerMeasurementB(self, dict):
            """Execution of Voltage Measurement for Programm / Readback Accuracy using Status Event Registry to synchronize Instrument

            The function first declares two lists, datalist & infolist that will be used to collect data.
            It then dynamically imports the library to be used. Next, the settings for all Instrument
            are initialized. The test loop begins where Voltage and Current Sweep is conducted and collect
            measured data.

            The synchronization of Instruments here is done by reading the status of the event registry.
            The status determined from the Instrument can let the program determine if the Instrument is
            measuring. The program will only proceed to tell the Instrument to query the measured value
            after it is determined that the measurement has been completed. This method is suitable for
            operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
            more complicated than other methods. This method only can be implemented that have the specific
            commands that are used.

            In line 260, where I_fixed - 0.001 * I_fixed is done to prevent the ELoad from causing the DUT
            to enter CC Mode.

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
                ELoad_Channel: Integer containing the channel number that the ELoad is using.
                PSU_Channel: Integer containing the channel number that the PSU is using.
                setVoltage_Sense: String determining the Voltage Sense that will be used.
                VoltageRes: String determining the Voltage Resoltion that will be used.
                setMode: String determining the Priority mode of the ELoad.
                Range: String determining the measuring range of the DMM  should be Auto or a specific range.
                Apreture: String determining the NPLC to be used by DMM  when measuring.
                AutoZero: String determining if AutoZero Mode on DMM  should be enabled/disabled.
                InputZ: String determining the Input Impedance Mode of DMM .
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
            ) = Dimport.getClasses(dict["Instrument"])

            RST(dict["PSU"])
            WAI(dict["PSU"])
            RST(dict["ELoad"])
            WAI(dict["ELoad"])
            RST(dict["DMM"])
            WAI(dict["DMM"])
            RST(dict["DMM2"])
            WAI(dict["DMM2"])
            
            #offset
            sleep(3)
            
            # Instrument Initialization
            Configure(dict["DMM"]).write("Voltage")
            Trigger(dict["DMM"]).setSource("BUS")
            Configure(dict["DMM2"]).write("Voltage")
            Trigger(dict["DMM2"]).setSource("BUS")
            Sense(dict["DMM"]).setVoltageResDC(dict["VoltageRes"])
            Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])

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
            
            Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
            Function(dict["ELoad"]).setMode("Voltage")
            Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])

            Voltage(dict["PSU"]).setInstrumentChannel(dict["PSU_Channel"])
            Function(dict["PSU"]).setMode("Current")
            Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["PSU_Channel"])

            Voltage(dict["DMM"]).setNPLC(dict["Aperture"])
            Voltage(dict["DMM"]).setAutoZeroMode(dict["AutoZero"])
            Voltage(dict["DMM"]).setAutoImpedanceMode(dict["InputZ"])
            Voltage(dict["DMM2"]).setNPLC(dict["Aperture"])
            Voltage(dict["DMM2"]).setAutoZeroMode(dict["AutoZero"])
            Voltage(dict["DMM2"]).setAutoImpedanceMode(dict["InputZ"])

            if dict["Range"] == "Auto":
                Sense(dict["DMM"]).setVoltageRangeDCAuto()
                Sense(dict["DMM2"]).setVoltageRangeDCAuto()

            else:
                Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])
                Sense(dict["DMM2"]).setVoltageRangeDC(dict["Range"])

            #Programming Parameters
            self.param1 = float(dict["Programming_Error_Gain"])    #power gain and offset
            self.param2 = float(dict["Programming_Error_Offset"])
            self.param3 = float(dict["Readback_Error_Gain"])
            self.param4 = float(dict["Readback_Error_Offset"])
            self.unit = dict["unit"]
            self.updatedelay = float(dict["updatedelay"])

            #self.Power = float(dict["power"])
            self.powerini = int(dict["powerini"])
            self.powerfin = int(dict["powerfin"])
            self.powerstepsize = int(dict["power_step_size"])
            powerchange = 0
            counter = 1
            k=1
            self.rshunt = float(dict["rshunt"])
            self.voltagemax = float(dict["maxVoltage"])
            self.currentmax = float(dict["maxCurrent"])

            #Test Start
            #Set Source and Eload Output
       
            Power(dict["PSU"]).setInputPower(0)
            WAI(dict["PSU"])
            Voltage(dict["PSU"]).setOutputVoltage("MAXimum")
            WAI(dict["PSU"])
            Current(dict["PSU"]).setOutputCurrent("MAXimum")
            WAI(dict["PSU"])

            #fixed current
            Voltage(dict["ELoad"]).setOutputVoltage(self.voltagemax)
            WAI(dict["ELoad"])

            Output(dict["PSU"]).setOutputState("ON")
            WAI(dict["PSU"])
            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])
            
            sleep(self.updatedelay)

            for powerchange in range (self.powerini, self.powerstepsize + self.powerfin, self.powerstepsize):

                Power(dict["PSU"]).setInputPower(powerchange)
                WAI(dict["PSU"])

                #Save Set Programming Power
                self.infoList.insert(k, [counter , powerchange])

                #Readback Power
                sleep(self.updatedelay)

                readback_power_temp_values = Measure(dict["PSU"]).singleChannelQuery("POW")
                
                WAI(dict["PSU"])
               
                self.dataList.insert(k,[float(readback_power_temp_values)])
                
                #DMM for measuring Voltage
                Initiate(dict["DMM"]).initiate()
                TRG(dict["DMM"])
                #status = float(Status(dict["DMM"]).operationCondition())
                #if status == 8704.0:
                voltagemeasured = float(Fetch(dict["DMM"]).query())
                 

                Initiate(dict["DMM2"]).initiate()
                TRG(dict["DMM2"])
                currentmeasured = float(Fetch(dict["DMM2"]).query())/self.rshunt
                
                
                #Store Measured Vottage and Current Data
                powermeasured = voltagemeasured * currentmeasured
                self.dataList2.insert(k,[voltagemeasured, currentmeasured, powermeasured])
                counter +=1
                k+=1

            Voltage(dict["PSU"]).setOutputVoltage(0)
            WAI(dict["PSU"])
            Current(dict["PSU"]).setOutputCurrent(0)
            WAI(dict["PSU"])
            Current(dict["ELoad"]).setOutputCurrent(0)
            WAI(dict["ELoad"])
            Output(dict["PSU"]).setOutputState("OFF")
            WAI(dict["PSU"])
            Output(dict["ELoad"]).setOutputState("OFF")
            WAI(dict["ELoad"])
            Output(dict["PSU"]).SPModeConnection("OFF")
            WAI(dict["PSU"])

            return self.infoList, self.dataList, self.dataList2

class RiseFallTime:
    def __init__():
        pass

    def executeA(
        self,
        dict,
    ):
        """Test for determining the Transient Recovery Time of DUT

        The test begins by initializing all the settings for Oscilloscope and other Instrument.
        The PSU is then set to output full load followed by activating single mode on the oscilloscope.
        The Eload is then turned off, which would trigger the oscilloscope to show a transient wave. The
        transient wave is then measured using the built in functions. The transient time is caluclated by
        totalling the rise and fall time where the threshold is set manually depending on the voltage
        settling band.

        Args:
            ELoad: String determining the VISA Address of ELoad.
            PSU: String determining the VISA Address of PSU.
            OSC: String determining the VISA Address of Oscilloscope.
            ELoad_Channel: Integer containing the Channel Number used for ELoad.
            PSU_Channel: Integer containing the Channel Number used for PSU.
            OSC_Channel: Integer containing the Channel Number used for Oscilloscope.
            setMode: String determining the Priority Mode of the ELoad.
            setVoltageSense: String determining the Voltage Sense of the PSU.
            V_rating: Float containing the Voltage Rating of the PSU.
            I_rating: Float containing the Current Rating of the PSU.
            Channel_CouplingMode: String determining the Channel Coupling Mode.
            Trigger_Mode: String determining the Trigger Mode.
            Trigger_CouplingMode: String determining the Trigger Coupling Mode.
            Trigger_SweepMode: String determining the Trigger Sweep Mode.
            Trigger_SlopeMode: String determining the Trigger Slope Mode.
            TimeScale: Float determining the time scale of the oscilloscope display.
            VerticalScale: Float determining the vertical scale of the oscilloscope display.
            I_Step: Float determining the value of current step.
            V_settling_band: Float determining the desired voltage settling band.

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
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        
        RST(dict["OSC"])
        

        #New Command 
        Excavator(dict["PSU"]).setSYSTEMEMULationMode("SOUR")
        WAI(dict["PSU"])
        Excavator(dict["ELoad"]).setSYSTEMEMULationMode("LOAD")
        WAI(dict["ELoad"])

        self.V_Rating = float(dict["V_Rating"])
        self.I_Rating = float(dict["I_Rating"])
        self.P_Rating = float(dict["P_Rating"])
        self.power = float(dict["power"])
        self.V_Settling_Band = float(dict["V_Settling_Band"])
        self.T_Settling_Band = float(dict["T_Settling_Band"])

        
        self.currentmax = float(dict["maxCurrent"]) #100%
        self.voltagemax = float(dict["maxVoltage"])
        """I_half= self.currentmax/2 #50% Load """
        
        IMax = self.power/self.voltagemax # Limited by power

        # Instruments Settings
        Oscilloscope(dict["OSC"]).setProbeAttenuation(dict["Probe_Setting"], dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setAcquireType(dict["Acq_Type"])
        Oscilloscope(dict["OSC"]).setTriggerMode(dict["Trigger_Mode"])
        Oscilloscope(dict["OSC"]).setChannelCoupling(
            dict["OSC_Channel"], dict["Channel_CouplingMode"]
        )
        Oscilloscope(dict["OSC"]).setTriggerMode(dict["Trigger_Mode"])
        Oscilloscope(dict["OSC"]).setTriggerCoupling(dict["Trigger_CouplingMode"])
        Oscilloscope(dict["OSC"]).setTriggerSweepMode(dict["Trigger_SweepMode"])
        Oscilloscope(dict["OSC"]).setTriggerSlope(dict["Trigger_SlopeMode"])
        Oscilloscope(dict["OSC"]).setTimeScale(dict["TimeScale"])
        Oscilloscope(dict["OSC"]).setTriggerSource(dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setVerticalScale(
            dict["VerticalScale"], dict["OSC_Channel"]
        )
        Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.V_Settling_Band*-1, dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setTriggerHFReject(1)
        Oscilloscope(dict["OSC"]).setTriggerNoiseReject(1)
        Oscilloscope(dict["OSC"]).on_displaycursor()
        Oscilloscope(dict["OSC"]).hardcopy("OFF")
        Oscilloscope(dict["OSC"]).set_marker_Y1(0)

        #Display(dict["ELoad"]).displayState(dict["ELoad_Channel"])
        Function(dict["ELoad"]).setMode(dict["setFunction"])
        Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
        Voltage(dict["PSU"]).setInstrumentChannel(dict["PSU_Channel"])
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["PSU_Channel"])

        repetition=0
        stepini=0
        stepfin=2
        stepsize=1
        #Special case 80V (0 to 100%) High Voltage
        Voltage(dict["PSU"]).setOutputVoltage(self.voltagemax)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent("MAXimum")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        sleep(2)

        """Imax = self.P_Rating / self.voltagemax"""
        Current(dict["ELoad"]).setOutputCurrent(IMax)
        WAI(dict["ELoad"])
        #Special case 80V (100 to 0%) High Voltage        
        sleep(3)

        #(0<->100% Loading)
        for repetition in range (stepini, stepsize + stepfin, stepsize):
            #Falling Detect
            Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(-self.V_Settling_Band, dict["OSC_Channel"])
            Oscilloscope(dict["OSC"]).run()
            sleep(2)
            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])
            sleep(2)

            Oscilloscope(dict["OSC"]).stop()
            Vmin = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL1")
            Xmin=Oscilloscope(dict["OSC"]).measureXMIN("CHANNEL1")
            Fallingtime=Oscilloscope(dict["OSC"]).measureFallingtime("CHANNEL1")
            Xini = np.array(Xmin) - np.array(Fallingtime)
            print(Vmin[0])
            print(Xmin[0])
            print(Fallingtime[0])
            print(Xini[0])

            #Set marker
            Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
            Oscilloscope(dict["OSC"]).set_marker_X2(Xmin[0])
            Oscilloscope(dict["OSC"]).set_marker_Y1(0)
            Oscilloscope(dict["OSC"]).set_marker_Y2(Vmin[0])

            try:
                Oscilloscope(dict["OSC"]).displaydata()
                displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
            png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_Falling_{current_time}.png")

            # Save PNG file as binary
            with open(png_file, "wb") as file:
                file.write(displayData)

            print(f"Screenshot saved at: {png_file}")

            """if VMIN > self.V_Settling_Band:
            #Within Spec
                print("Test Pass")
            else:
            #Above Spec
                print("Test Fail")"""

            Oscilloscope(dict["OSC"]).run()
            Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.V_Settling_Band-0.05, dict["OSC_Channel"])
            sleep(2)

            Output(dict["ELoad"]).setOutputState("OFF")
            WAI(dict["ELoad"])
            sleep(2)

            #Rasing Detect
            Oscilloscope(dict["OSC"]).stop()
            Vmax=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL1")
            Xmax=Oscilloscope(dict["OSC"]).measureXMAX("CHANNEL1")
            Risingtime=Oscilloscope(dict["OSC"]).measureRisingtime("CHANNEL1")
            Xini = np.array(Xmax) - (np.array(Risingtime))

            #Set marker
            Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
            Oscilloscope(dict["OSC"]).set_marker_X2(Xmax[0])
            Oscilloscope(dict["OSC"]).set_marker_Y1(0)
            Oscilloscope(dict["OSC"]).set_marker_Y2(Vmax[0])

            try:
                Oscilloscope(dict["OSC"]).displaydata()
                displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
            png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_Rising_{current_time}.png")

            # Save PNG file as binary
            with open(png_file, "wb") as file:
                file.write(displayData)

            print(f"Screenshot saved at: {png_file}")


        #Low Voltage
        VMax = self.power/self.currentmax
        Voltage(dict["PSU"]).setOutputVoltage(VMax)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent("MAXimum")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        sleep(2)

        Current(dict["ELoad"]).setOutputCurrent(self.currentmax)
        WAI(dict["ELoad"])    
        
        #(0<->100% Loading)
        for repetition in range (stepini, stepsize + stepfin, stepsize):
            #Falling Detect
            Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(-self.V_Settling_Band, dict["OSC_Channel"])
            Oscilloscope(dict["OSC"]).run()
            sleep(2)
            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])
            sleep(2)

            Oscilloscope(dict["OSC"]).stop()
            Vmin = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL1")
            Xmin=Oscilloscope(dict["OSC"]).measureXMIN("CHANNEL1")
            Fallingtime=Oscilloscope(dict["OSC"]).measureFallingtime("CHANNEL1")
            Xini = np.array(Xmin) - np.array(Fallingtime)
            print(Vmin[0])
            print(Xmin[0])
            print(Fallingtime[0])
            print(Xini[0])

            #Set marker
            Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
            Oscilloscope(dict["OSC"]).set_marker_X2(Xmin[0])
            Oscilloscope(dict["OSC"]).set_marker_Y1(0)
            Oscilloscope(dict["OSC"]).set_marker_Y2(Vmin[0])

            try:
                Oscilloscope(dict["OSC"]).displaydata()
                displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
            png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_Falling_{current_time}.png")

            # Save PNG file as binary
            with open(png_file, "wb") as file:
                file.write(displayData)

            print(f"Screenshot saved at: {png_file}")

            """if VMIN > self.V_Settling_Band:
            #Within Spec
                print("Test Pass")
            else:
            #Above Spec
                print("Test Fail")"""

            Oscilloscope(dict["OSC"]).run()
            Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.V_Settling_Band-0.05, dict["OSC_Channel"])
            sleep(2)

            Output(dict["ELoad"]).setOutputState("OFF")
            WAI(dict["ELoad"])
            sleep(2)

            #Rasing Detect
            Oscilloscope(dict["OSC"]).stop()
            Vmax=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL1")
            Xmax=Oscilloscope(dict["OSC"]).measureXMAX("CHANNEL1")
            Risingtime=Oscilloscope(dict["OSC"]).measureRisingtime("CHANNEL1")
            Xini = np.array(Xmax) - (np.array(Risingtime))

            #Set marker
            Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
            Oscilloscope(dict["OSC"]).set_marker_X2(Xmax[0])
            Oscilloscope(dict["OSC"]).set_marker_Y1(0)
            Oscilloscope(dict["OSC"]).set_marker_Y2(Vmax[0])

            try:
                Oscilloscope(dict["OSC"]).displaydata()
                displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
            png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_Rising_{current_time}.png")

            # Save PNG file as binary
            with open(png_file, "wb") as file:
                file.write(displayData)

            print(f"Screenshot saved at: {png_file}")
    
    def executeB(
        self,
        dict,
    ):
        """Test for determining the Transient Recovery Time of DUT

        The test begins by initializing all the settings for Oscilloscope and other Instrument.
        The PSU is then set to output full load followed by activating single mode on the oscilloscope.
        The Eload is then turned off, which would trigger the oscilloscope to show a transient wave. The
        transient wave is then measured using the built in functions. The transient time is caluclated by
        totalling the rise and fall time where the threshold is set manually depending on the voltage
        settling band.

        Args:
            ELoad: String determining the VISA Address of ELoad.
            PSU: String determining the VISA Address of PSU.
            OSC: String determining the VISA Address of Oscilloscope.
            ELoad_Channel: Integer containing the Channel Number used for ELoad.
            PSU_Channel: Integer containing the Channel Number used for PSU.
            OSC_Channel: Integer containing the Channel Number used for Oscilloscope.
            setMode: String determining the Priority Mode of the ELoad.
            setVoltageSense: String determining the Voltage Sense of the PSU.
            V_rating: Float containing the Voltage Rating of the PSU.
            I_rating: Float containing the Current Rating of the PSU.
            Channel_CouplingMode: String determining the Channel Coupling Mode.
            Trigger_Mode: String determining the Trigger Mode.
            Trigger_CouplingMode: String determining the Trigger Coupling Mode.
            Trigger_SweepMode: String determining the Trigger Sweep Mode.
            Trigger_SlopeMode: String determining the Trigger Slope Mode.
            TimeScale: Float determining the time scale of the oscilloscope display.
            VerticalScale: Float determining the vertical scale of the oscilloscope display.
            I_Step: Float determining the value of current step.
            V_settling_band: Float determining the desired voltage settling band.

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
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        
        RST(dict["OSC"])
        

        #New Command 
        Excavator(dict["PSU"]).setSYSTEMEMULationMode("SOUR")
        WAI(dict["PSU"])
        Excavator(dict["ELoad"]).setSYSTEMEMULationMode("LOAD")
        WAI(dict["ELoad"])

        self.V_Rating = float(dict["V_Rating"])
        self.I_Rating = float(dict["I_Rating"])
        self.P_Rating = float(dict["P_Rating"])
        self.power = float(dict["power"])
        self.V_Settling_Band = float(dict["V_Settling_Band"])
        self.T_Settling_Band = float(dict["T_Settling_Band"])
        self.currentmax = float(dict["maxCurrent"]) #100%
        self.voltagemax = float(dict["maxVoltage"])


        # Instruments Settings
        Oscilloscope(dict["OSC"]).setProbeAttenuation(dict["Probe_Setting"], dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setAcquireType(dict["Acq_Type"])
        Oscilloscope(dict["OSC"]).setTriggerMode(dict["Trigger_Mode"])
        Oscilloscope(dict["OSC"]).setChannelCoupling(
            dict["OSC_Channel"], dict["Channel_CouplingMode"]
        )
        Oscilloscope(dict["OSC"]).setTriggerMode(dict["Trigger_Mode"])
        Oscilloscope(dict["OSC"]).setTriggerCoupling(dict["Trigger_CouplingMode"])
        Oscilloscope(dict["OSC"]).setTriggerSweepMode(dict["Trigger_SweepMode"])
        Oscilloscope(dict["OSC"]).setTriggerSlope(dict["Trigger_SlopeMode"])
        Oscilloscope(dict["OSC"]).setTimeScale(dict["TimeScale"])
        Oscilloscope(dict["OSC"]).setTriggerSource(dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setVerticalScale(
            dict["VerticalScale"], dict["OSC_Channel"]
        )
        Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.V_Settling_Band*-1, dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setTriggerHFReject(1)
        Oscilloscope(dict["OSC"]).setTriggerNoiseReject(1)
        Oscilloscope(dict["OSC"]).on_displaycursor()
        Oscilloscope(dict["OSC"]).hardcopy()
        Oscilloscope(dict["OSC"]).set_marker_Y1(0)

        #Display(dict["ELoad"]).displayState(dict["ELoad_Channel"])
        Function(dict["ELoad"]).setMode(dict["setFunction"])
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["PSU_Channel"])

        repetition=0
        stepini=0
        stepfin=2
        stepsize=1

        #Normal case (50 <-> 100%) High Voltage Condition
        #PSU Setting Voltage and Current
        Voltage(dict["PSU"]).setOutputVoltage(self.voltagemax)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent("MAXimum")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        sleep(2)

        #Eload Setting Current 
        IMax = self.power/self.voltagemax
        I_halfLoad = IMax/2 #50% Load 
        I_fullLoad = IMax - 1 #Minus 1A prevent PSU fall into CC mode

        #Begin with 50% Load
        Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
        WAI(dict["ELoad"])
        Output(dict["ELoad"]).setOutputState("ON")
        #Special case 80V (100 to 0%) High Voltage        
        sleep(3)

        #(50<->100% Loading)
        for repetition in range (stepini, stepsize + stepfin, stepsize):
            #Falling Detect
            Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(-self.V_Settling_Band, dict["OSC_Channel"])
            Oscilloscope(dict["OSC"]).run()
            sleep(2)
            #Begin with 50% Load
            Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
            WAI(dict["ELoad"])
            sleep(3)
            #Increase to 100% Current
            Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
            sleep(3)

            Oscilloscope(dict["OSC"]).stop()
            Vmin = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL1")
            Xmin=Oscilloscope(dict["OSC"]).measureXMIN("CHANNEL1")
            Fallingtime=Oscilloscope(dict["OSC"]).measureFallingtime("CHANNEL1")
            Xini = np.array(Xmin) - np.array(Fallingtime)
            print(Vmin[0])
            print(Xmin[0])
            print(Fallingtime[0])
            print(Xini[0])

            #Set marker
            Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
            Oscilloscope(dict["OSC"]).set_marker_X2(Xmin[0])
            Oscilloscope(dict["OSC"]).set_marker_Y1(0)
            Oscilloscope(dict["OSC"]).set_marker_Y2(Vmin[0])

            try:
                Oscilloscope(dict["OSC"]).displaydata()
                displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
            png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_HighVoltage_Falling_{self.voltagemax}@{I_halfLoad}to{I_fullLoad}{current_time}.png")

            # Save PNG file as binary
            with open(png_file, "wb") as file:
                file.write(displayData)

            print(f"Screenshot saved at: {png_file}")

            """if VMIN > self.V_Settling_Band:
            #Within Spec
                print("Test Pass")
            else:
            #Above Spec
                print("Test Fail")"""

            Oscilloscope(dict["OSC"]).run()
            Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.V_Settling_Band-0.05, dict["OSC_Channel"])
            sleep(2)

            #Increase to 100% Current
            Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
            sleep(3)
            Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
            WAI(dict["ELoad"])
            sleep(3)

            #Rasing Detect
            Oscilloscope(dict["OSC"]).stop()
            Vmax=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL1")
            Xmax=Oscilloscope(dict["OSC"]).measureXMAX("CHANNEL1")
            Risingtime=Oscilloscope(dict["OSC"]).measureRisingtime("CHANNEL1")
            Xini = np.array(Xmax) - (np.array(Risingtime))

            #Set marker
            Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
            Oscilloscope(dict["OSC"]).set_marker_X2(Xmax[0])
            Oscilloscope(dict["OSC"]).set_marker_Y1(0)
            Oscilloscope(dict["OSC"]).set_marker_Y2(Vmax[0])

            try:
                Oscilloscope(dict["OSC"]).displaydata()
                displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
            png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_HighVoltage_Rising_{self.voltagemax}@{I_halfLoad}to{I_fullLoad}{current_time}.png")

            # Save PNG file as binary
            with open(png_file, "wb") as file:
                file.write(displayData)

        print(f"Screenshot saved at: {png_file}")

        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])


        #Eload Setting Current
        VMax = self.power/self.currentmax
        I_halfLoad = self.currentmax/2 #50% Load 
        I_fullLoad = self.currentmax - 1 #Minus 1A prevent PSU fall into CC mode

        Voltage(dict["PSU"]).setOutputVoltage(VMax)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent("MAXimum")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])

        #Begin with 50% Load
        Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
        WAI(dict["ELoad"])
        Output(dict["ELoad"]).setOutputState("ON")
        #Special case 80V (100 to 0%) High Current     
        sleep(3)

        #(50<->100% Loading)
        for repetition in range (stepini, stepsize + stepfin, stepsize):
            #Falling Detect
            Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(-self.V_Settling_Band, dict["OSC_Channel"])
            Oscilloscope(dict["OSC"]).run()
            sleep(2)
            #Begin with 50% Load
            Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
            WAI(dict["ELoad"])
            sleep(3)
            #Increase to 100% Current
            Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
            sleep(3)

            Oscilloscope(dict["OSC"]).stop()
            Vmin = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL1")
            Xmin=Oscilloscope(dict["OSC"]).measureXMIN("CHANNEL1")
            Fallingtime=Oscilloscope(dict["OSC"]).measureFallingtime("CHANNEL1")
            Xini = np.array(Xmin) - np.array(Fallingtime)
            print(Vmin[0])
            print(Xmin[0])
            print(Fallingtime[0])
            print(Xini[0])

            #Set marker
            Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
            Oscilloscope(dict["OSC"]).set_marker_X2(Xmin[0])
            Oscilloscope(dict["OSC"]).set_marker_Y1(0)
            Oscilloscope(dict["OSC"]).set_marker_Y2(Vmin[0])

            try:
                Oscilloscope(dict["OSC"]).displaydata()
                displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
            png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_LowVoltage_Falling_{VMax}@{I_halfLoad}to{I_fullLoad}{current_time}{current_time}.png")

            # Save PNG file as binary
            with open(png_file, "wb") as file:
                file.write(displayData)

            print(f"Screenshot saved at: {png_file}")

            """if VMIN > self.V_Settling_Band:
            #Within Spec
                print("Test Pass")
            else:
            #Above Spec
                print("Test Fail")"""

            Oscilloscope(dict["OSC"]).run()
            Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.V_Settling_Band-0.05, dict["OSC_Channel"])
            sleep(2)

            #Increase to 100% Current
            Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
            sleep(3)
            Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
            WAI(dict["ELoad"])
            sleep(3)

            #Rasing Detect
            Oscilloscope(dict["OSC"]).stop()
            Vmax=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL1")
            Xmax=Oscilloscope(dict["OSC"]).measureXMAX("CHANNEL1")
            Risingtime=Oscilloscope(dict["OSC"]).measureRisingtime("CHANNEL1")
            Xini = np.array(Xmax) - (np.array(Risingtime))

            #Set marker
            Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
            Oscilloscope(dict["OSC"]).set_marker_X2(Xmax[0])
            Oscilloscope(dict["OSC"]).set_marker_Y1(0)
            Oscilloscope(dict["OSC"]).set_marker_Y2(Vmax[0])

            try:
                Oscilloscope(dict["OSC"]).displaydata()
                displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
            png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_LowVoltage_Rising_{VMax}@{I_halfLoad}to{I_fullLoad}{current_time}{current_time}.png")

            # Save PNG file as binary
            with open(png_file, "wb") as file:
                file.write(displayData)

        print(f"Screenshot saved at: {png_file}")

        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])

    def executeC(
        self,
        dict,
    ):
        
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
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        
        RST(dict["OSC"])
        
        sleep(5)

        #New Command 
        #Excavator(dict["PSU"]).setSYSTEMEMULationMode("SOUR")
        #WAI(dict["PSU"])
        #Excavator(dict["ELoad"]).setSYSTEMEMULationMode("LOAD")
        #WAI(dict["ELoad"])
        #Excavator(dict["ELoad"]).setPOSITIVECURRENTSLEW()
        #WAI(dict["ELoad"])
        #Excavator(dict["ELoad"]).setNEGATIVECURRENTSLEW()

        self.V_Rating = float(dict["V_Rating"])
        self.I_Rating = float(dict["I_Rating"])
        self.P_Rating = float(dict["P_Rating"])
        self.power = self.P_Rating

        self.DUT_V_Settling_Band = float(dict["DUT_V_Settling_Band"])
        self.DUT_T_Settling_Band = float(dict["DUT_T_Settling_Band"])
        self.CurrentTrigger_V_Settling_Band = float(dict["CurrentTrigger_V_Settling_Band"])
        dut_probe_setting = dict["DUT_Probe_Setting"]
        dut_channel = dict["DUT_OSC_Channel"]
        tri_probe_setting = dict["CurrentTrigger_Probe_Setting"]
        tri_channel = dict["CurrentTrigger_OSC_Channel"]

        self.currentmax = float(dict["maxCurrent"]) #100%
        self.voltagemax = float(dict["maxVoltage"])

        # Instruments Settings

        Oscilloscope(dict["OSC"]).setChannel_Display("1", dict["DUT_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setProbeAttenuation(dict["DUT_Probe_Setting"], dict["DUT_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelCoupling(dict["DUT_OSC_Channel"], dict["DUT_Channel_CouplingMode"]) #AC
        Oscilloscope(dict["OSC"]).setTimeScale(dict["DUT_TimeScale"])
        Oscilloscope(dict["OSC"]).setVerticalScale(dict["DUT_VerticalScale"], dict["DUT_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelOffest(dict["DUT_Channel_Offset"], dict["DUT_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelUnits(dict["DUT_Channel_Unit"], dict["DUT_OSC_Channel"])


        Oscilloscope(dict["OSC"]).setChannel_Display("1", dict["CurrentTrigger_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setProbeAttenuation(dict["CurrentTrigger_Probe_Setting"], dict["CurrentTrigger_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelCoupling(dict["CurrentTrigger_OSC_Channel"], dict["CurrentTrigger_Channel_CouplingMode"]) #AC
        Oscilloscope(dict["OSC"]).setVerticalScale(dict["CurrentTrigger_VerticalScale"], dict["CurrentTrigger_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelOffest(dict["CurrentTrigger_Channel_Offset"], dict["CurrentTrigger_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelUnits(dict["CurrentTrigger_Channel_Unit"], dict["CurrentTrigger_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setTriggerSource(dict["CurrentTrigger_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.CurrentTrigger_V_Settling_Band, dict["CurrentTrigger_OSC_Channel"])


        Oscilloscope(dict["OSC"]).setAcquireType(dict["CurrentTrigger_Acq_Type"])
        Oscilloscope(dict["OSC"]).setTriggerMode(dict["CurrentTrigger_Trigger_Mode"])
        Oscilloscope(dict["OSC"]).setChannelCoupling(dict["CurrentTrigger_OSC_Channel"], dict["CurrentTrigger_Channel_CouplingMode"])
        Oscilloscope(dict["OSC"]).setTriggerMode(dict["CurrentTrigger_Trigger_Mode"])
        Oscilloscope(dict["OSC"]).setTriggerCoupling(dict["CurrentTrigger_Trigger_CouplingMode"])
        Oscilloscope(dict["OSC"]).setTriggerSweepMode(dict["CurrentTrigger_Trigger_SweepMode"])
        Oscilloscope(dict["OSC"]).setTriggerSlope(dict["CurrentTrigger_Trigger_SlopeMode"])

        Oscilloscope(dict["OSC"]).setTriggerHFReject(1)
        Oscilloscope(dict["OSC"]).setTriggerNoiseReject(1)
        Oscilloscope(dict["OSC"]).on_displaycursor()
        Oscilloscope(dict["OSC"]).hardcopy("OFF")
        Oscilloscope(dict["OSC"]).set_marker_Y1(0)

        Oscilloscope(dict["OSC"]).setChannel_Display("0", dict["DUT_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannel_Display("1", dict["DUT_OSC_Channel"])


        Function(dict["ELoad"]).setMode(dict["setFunction"])
        Voltage(dict["PSU"]).setSenseMode(dict["VoltageSense"])


        #Normal case (50 <-> 100%) High Voltage Condition
        #PSU Setting Voltage and Current
        Voltage(dict["PSU"]).setOutputVoltage(self.voltagemax)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent("MAXimum")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        sleep(2)

        #Eload Setting Current 
        IMax = self.power/self.voltagemax
        I_halfLoad = IMax/2 #50% Load 
        I_reduction_based_on_rated_value = IMax * 0.01 #1% of Imax
        I_fullLoad = IMax - I_reduction_based_on_rated_value #Minus 1A prevent PSU fall into CC mode
        I_trigger = (I_fullLoad + I_halfLoad)/ 2
        self.CurrentTrigger_V_Settling_Band = round (I_trigger,2)

        Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.CurrentTrigger_V_Settling_Band, dict["CurrentTrigger_OSC_Channel"])
        
        #Begin with 50% Load
        Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
        WAI(dict["ELoad"])
        Output(dict["ELoad"]).setOutputState("ON")
        #Special case 80V (100 to 0%) High Voltage        
        sleep(3)

        
#####Set Channel 1 and Channel 2 Scale Based on Probe Setting ##########################
        #Probe Setting
        if dut_channel == "CHANNEL1":
            if dut_probe_setting == "X1":
                multiplier_scale_DUT = 1
            elif dut_probe_setting == "X10":
                multiplier_scale_DUT = 10
            elif dut_probe_setting == "X20":
                multiplier_scale_DUT = 20
            else:
                multiplier_scale_DUT = 100

        elif dut_channel == "CHANNEL2":
            if dut_probe_setting == "X1":
                multiplier_scale_DUT = 1
            elif dut_probe_setting == "X10":
                multiplier_scale_DUT = 10
            elif dut_probe_setting == "X20":
                multiplier_scale_DUT = 20
            else:
                multiplier_scale_DUT = 100
        
        if tri_channel == "CHANNEL1":
            if tri_probe_setting == "X1":
                multiplier_scale_TRI = 1
            elif tri_probe_setting == "X10":
                multiplier_scale_TRI = 10
            elif tri_probe_setting == "X20":
                multiplier_scale_TRI = 20
            else:
                multiplier_scale_TRI = 100
                
        elif tri_channel == "CHANNEL2":
            if tri_probe_setting == "X1":
                multiplier_scale_TRI = 1
            elif tri_probe_setting == "X10":
                multiplier_scale_TRI = 10
            elif tri_probe_setting == "X20":
                multiplier_scale_TRI = 20
            else:
                multiplier_scale_TRI = 100

#####Set Channel 1 Scale Based on Transient Spec##########################

        if self.DUT_V_Settling_Band >= 0 and self.DUT_V_Settling_Band <= 0.001: # 1mV
            VScale = 0.001 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        elif self.DUT_V_Settling_Band > 0.001 and self.DUT_V_Settling_Band <= 0.002: # 2mV
            VScale = 0.002 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
            
        elif self.DUT_V_Settling_Band >0.002 and self.DUT_V_Settling_Band<= 0.005: # 5mV
            VScale = 0.005 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

        elif self.DUT_V_Settling_Band >0.005 and self.DUT_V_Settling_Band<= 0.01: # 10mV
            VScale = 0.01 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        elif self.DUT_V_Settling_Band >0.01 and self.DUT_V_Settling_Band <= 0.02: # 20mV
            VScale = 0.02 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        elif self.DUT_V_Settling_Band >0.02 and self.DUT_V_Settling_Band <= 0.05: # 50mV
            VScale = 0.05 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        elif self.DUT_V_Settling_Band > 0.05 and self.DUT_V_Settling_Band<= 0.1: # 100mV
            VScale = 0.1 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        elif self.DUT_V_Settling_Band > 0.1 and self.DUT_V_Settling_Band<= 0.2: # 200mV
            VScale = 0.2 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

        elif self.DUT_V_Settling_Band > 0.2 and self.DUT_V_Settling_Band<= 0.5: # 500mV
            VScale = 0.5
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        elif self.DUT_V_Settling_Band > 0.5 and self.DUT_V_Settling_Band<= 1: # 1V
            VScale = 1 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        elif self.DUT_V_Settling_Band > 1 and self.DUT_V_Settling_Band<= 2: # 2V
            VScale = 2 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        elif self.DUT_V_Settling_Band > 2 and self.DUT_V_Settling_Band<= 5: # 5V
            VScale = 5 
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        elif self.DUT_V_Settling_Band > 5 and self.DUT_V_Settling_Band<= 10: # 10V
            VScale = 2
            Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        
        
        I_Offset_shift_factor = 4

        if self.CurrentTrigger_V_Settling_Band > 0 and self.CurrentTrigger_V_Settling_Band <= 0.001: # 1mA
            IScale = 0.001 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band > 0.001 and self.CurrentTrigger_V_Settling_Band<= 0.002: # 2mA
            IScale = 0.002 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band > 0.002 and self.CurrentTrigger_V_Settling_Band<= 0.005: # 5mA
            IScale = 0.005 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.005 and self.CurrentTrigger_V_Settling_Band<= 0.01: # 10mA
            IScale = 0.01 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.01 and self.CurrentTrigger_V_Settling_Band<= 0.02: # 20mA
            IScale = 0.02 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.02 and self.CurrentTrigger_V_Settling_Band<= 0.05: # 50mA
            IScale = 0.05 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.05 and self.CurrentTrigger_V_Settling_Band<= 0.1: # 100mA
            IScale = 0.1 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.1 and self.CurrentTrigger_V_Settling_Band<= 0.2: # 200mA
            IScale = 0.2 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.2 and self.CurrentTrigger_V_Settling_Band<= 0.5: # 500mA
            IScale = 0.5 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.5 and self.CurrentTrigger_V_Settling_Band<= 1: # 1A
            IScale = 1 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  >1 and self.CurrentTrigger_V_Settling_Band<= 2: # 2A
            IScale = 2 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 2 and self.CurrentTrigger_V_Settling_Band<= 5: # 5A  
            IScale = 5 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])
        
        elif self.CurrentTrigger_V_Settling_Band  > 5 and self.CurrentTrigger_V_Settling_Band<= 10: # 10A
            IScale = 2 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor , dict["CurrentTrigger_OSC_Channel"])
        
        elif self.CurrentTrigger_V_Settling_Band  > 10 and self.CurrentTrigger_V_Settling_Band<= 20: # 20A
            IScale = 15 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])
        
        elif self.CurrentTrigger_V_Settling_Band  > 20 and self.CurrentTrigger_V_Settling_Band<= 30: # 50A
            IScale = 25 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])
        
        Oscilloscope(dict["OSC"]).setChannel_Display("0", dict["DUT_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannel_Display("1", dict["DUT_OSC_Channel"])
        
        #########################################

        #(50<->100% Loading)
        #Falling Detect
        Oscilloscope(dict["OSC"]).run()
        sleep(2)
        #Begin with 50% Load
        Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
        WAI(dict["ELoad"])
        sleep(3)
        #Increase to 100% Current
        Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
        sleep(3)

        Oscilloscope(dict["OSC"]).stop()
        Vmin = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL1")
        Irise = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL2")

        """while abs(Vmin[0]) > (VScale*4):
            if abs(Vmin[0]) - (VScale*4) <= (0.001 * multiplier_scale_DUT):
                VScale = VScale + (0.001 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.002 * multiplier_scale_DUT):
                VScale = VScale + (0.002 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.005 * multiplier_scale_DUT):
                VScale = VScale + (0.005 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.01 * multiplier_scale_DUT):
                VScale = VScale + (0.01 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.02 * multiplier_scale_DUT):
                VScale = VScale + (0.02 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.05 * multiplier_scale_DUT):
                VScale = VScale + (0.05 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.1 * multiplier_scale_DUT):
                VScale = VScale +(0.1 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.2 * multiplier_scale_DUT):
                VScale = VScale + (0.2 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.5 * multiplier_scale_DUT):
                VScale = VScale + (0.5 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (1 * multiplier_scale_DUT):
                VScale = VScale + (1 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (2 * multiplier_scale_DUT):
                VScale = VScale + (2 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            else:
                VScale = VScale
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
            
            if abs(Irise[0]) > (IScale*4):
                if abs(Irise[0]) - (IScale*4) <= (0.001 * multiplier_scale_TRI):
                    IScale = IScale + (0.001 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])  
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.002 * multiplier_scale_TRI):
                    IScale = IScale + (0.002 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.005 * multiplier_scale_TRI):
                    IScale = IScale + (0.005 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.01 * multiplier_scale_TRI):
                    IScale = IScale + (0.01 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.02 * multiplier_scale_TRI):
                    IScale = IScale + (0.02 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.05 * multiplier_scale_TRI):
                    IScale = IScale + (0.05 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.1 * multiplier_scale_TRI): 
                    IScale = IScale + (0.1 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.2 * multiplier_scale_TRI):
                    IScale = IScale + (0.2 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.5 * multiplier_scale_TRI):
                    IScale = IScale + (0.5 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (1 * multiplier_scale_TRI):
                    IScale = IScale + (1 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (2 * multiplier_scale_TRI):
                    IScale = IScale + (2 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                else:
                    IScale = IScale
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
            
            #Rerun (50<->100% Loading)
            #Falling Detect
            Oscilloscope(dict["OSC"]).run()
            sleep(2)
            #Begin with 50% Load
            Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
            WAI(dict["ELoad"])
            sleep(3)
            #Increase to 100% Current
            Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
            sleep(3)

            Oscilloscope(dict["OSC"]).stop()
            Vmin = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL1")

            if abs(Vmin[0]) < (VScale*4):
                break"""
            
        Xmin=Oscilloscope(dict["OSC"]).measureXMIN("CHANNEL1")
        Fallingtime=Oscilloscope(dict["OSC"]).measureFallingtime("CHANNEL1")
        Xini = np.array(Xmin) - np.array(Fallingtime)
        print(Vmin[0])
        print(Xmin[0])
        print(Fallingtime[0])
        print(Xini[0])

        #Set marker
        Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
        Oscilloscope(dict["OSC"]).set_marker_X2(Xmin[0])
        Oscilloscope(dict["OSC"]).set_marker_Y1(0)
        Oscilloscope(dict["OSC"]).set_marker_Y2(Vmin[0])

        try:
            Oscilloscope(dict["OSC"]).displaydata()
            displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
        png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_HighVoltage_Falling_{self.voltagemax}@{I_halfLoad}to{I_fullLoad}{current_time}.png")

        # Save PNG file as binary
        with open(png_file, "wb") as file:
            file.write(displayData)

        print(f"Screenshot saved at: {png_file}")

        """if VMIN > self.V_Settling_Band:
        #Within Spec
            print("Test Pass")
        else:
        #Above Spec
            print("Test Fail")"""
        
        #100 to 50%
        Oscilloscope(dict["OSC"]).run()
        sleep(2)

        #Increase to 100% Current
        Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
        sleep(3)
        Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
        WAI(dict["ELoad"])
        sleep(3)

        #Rasing Detect
        Oscilloscope(dict["OSC"]).stop()
        Vmax=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL1")
        Ifall=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL2")

        """while abs(Vmax[0]) > (VScale*4):
            if abs(Vmax[0]) - (VScale*4) <= (0.001 * multiplier_scale_DUT):
                VScale = VScale + (0.001 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.002 * multiplier_scale_DUT): 
                VScale = VScale + (0.002 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.005 * multiplier_scale_DUT):
                VScale = VScale + (0.005 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.01 * multiplier_scale_DUT):
                VScale = VScale + (0.01 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.02 * multiplier_scale_DUT):
                VScale = VScale + (0.02 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.05 * multiplier_scale_DUT):
                VScale = VScale + (0.05 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
                
            elif abs(Vmax[0]) - (VScale*4) <= (0.1 * multiplier_scale_DUT):
                VScale = VScale + (0.1 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <=( 0.2 * multiplier_scale_DUT):
                VScale = VScale + (0.2 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.5 * multiplier_scale_DUT):
                VScale = VScale + (0.5 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (1 * multiplier_scale_DUT):
                VScale = VScale + (1 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (2 * multiplier_scale_DUT):  
                VScale = VScale +( 2 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            else:   
                VScale = VScale
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
            
            if abs(Ifall[0]) > (IScale*4):
                if abs(Ifall[0]) - (IScale*4) <= (0.001 * multiplier_scale_TRI):
                    IScale = IScale +( 0.001 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= (0.002 * multiplier_scale_TRI):
                    IScale = IScale + (0.002 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= (0.005 * multiplier_scale_TRI):
                    IScale = IScale +( 0.005 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.01 * multiplier_scale_TRI:
                    IScale = IScale + (0.01  * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.02 * multiplier_scale_TRI:
                    IScale = IScale + (0.02  * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.05 * multiplier_scale_TRI:
                    IScale = IScale + (0.05  * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.1  * multiplier_scale_TRI:
                    IScale = IScale + (0.1 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.2  * multiplier_scale_TRI:
                    IScale = IScale +( 0.2 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.5  * multiplier_scale_TRI:
                    IScale = IScale + (0.5 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 1 * multiplier_scale_TRI:
                    IScale = IScale + (1 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 2 * multiplier_scale_TRI:
                    IScale = IScale +( 2 * multiplier_scale_TRI  )
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                else:
                    IScale = IScale
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
            
            #Rerun (100<->50% Loading)
            #Rasing Detect
            Oscilloscope(dict["OSC"]).run()
            sleep(2)
            #Increase to 100% Current
            Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
            sleep(3)
            Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
            WAI(dict["ELoad"])
            sleep(3)

            Oscilloscope(dict["OSC"]).stop()
            Vmax=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL1")

            if abs(Vmax[0]) < (VScale*4):
                break"""

        Xmax=Oscilloscope(dict["OSC"]).measureXMAX("CHANNEL1")
        Risingtime=Oscilloscope(dict["OSC"]).measureRisingtime("CHANNEL1")
        Xini = np.array(Xmax) - (np.array(Risingtime))

        #Set marker
        Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
        Oscilloscope(dict["OSC"]).set_marker_X2(Xmax[0])
        Oscilloscope(dict["OSC"]).set_marker_Y1(0)
        Oscilloscope(dict["OSC"]).set_marker_Y2(Vmax[0])

        try:
            Oscilloscope(dict["OSC"]).displaydata()
            displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
        png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_HighVoltage_Rising_{self.voltagemax}@{I_halfLoad}to{I_fullLoad}{current_time}.png")

        # Save PNG file as binary
        with open(png_file, "wb") as file:
            file.write(displayData)

        print(f"Screenshot saved at: {png_file}")

        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])

##############################################################################################################
##########High Current Condition
        #Eload Setting Current
        VMax = self.power/self.currentmax
        I_halfLoad = self.currentmax/2 #50% Load 
        I_fullLoad = self.currentmax - I_reduction_based_on_rated_value #Minimum 1%
        I_trigger = (I_fullLoad + I_halfLoad)/ 2
        self.CurrentTrigger_V_Settling_Band = round (I_trigger,2)
        Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.CurrentTrigger_V_Settling_Band, dict["CurrentTrigger_OSC_Channel"])

        VScale = 0.5
        Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
        TScale = 0.3
        Oscilloscope(dict["OSC"]).setTimeScale(TScale)

         #PSU Setting Voltage and Current
        Voltage(dict["PSU"]).setOutputVoltage(VMax)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent("MAXimum")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        sleep(3)

        #Begin with 50% Load
        Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
        WAI(dict["ELoad"])
        Output(dict["ELoad"]).setOutputState("ON")
        #Special case 80V (100 to 0%) High Current     
        sleep(3)

        if self.CurrentTrigger_V_Settling_Band > 0 and self.CurrentTrigger_V_Settling_Band <= 0.001: # 1mA
            IScale = 0.001 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band > 0.001 and self.CurrentTrigger_V_Settling_Band<= 0.002: # 2mA
            IScale = 0.002 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band > 0.002 and self.CurrentTrigger_V_Settling_Band<= 0.005: # 5mA
            IScale = 0.005 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.005 and self.CurrentTrigger_V_Settling_Band<= 0.01: # 10mA
            IScale = 0.01 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.01 and self.CurrentTrigger_V_Settling_Band<= 0.02: # 20mA
            IScale = 0.02 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.02 and self.CurrentTrigger_V_Settling_Band<= 0.05: # 50mA
            IScale = 0.05 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.05 and self.CurrentTrigger_V_Settling_Band<= 0.1: # 100mA
            IScale = 0.1 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.1 and self.CurrentTrigger_V_Settling_Band<= 0.2: # 200mA
            IScale = 0.2 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.2 and self.CurrentTrigger_V_Settling_Band<= 0.5: # 500mA
            IScale = 0.5 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale, dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 0.5 and self.CurrentTrigger_V_Settling_Band<= 1: # 1A
            IScale = 1 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  >1 and self.CurrentTrigger_V_Settling_Band<= 2: # 2A
            IScale = 2 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])

        elif self.CurrentTrigger_V_Settling_Band  > 2 and self.CurrentTrigger_V_Settling_Band<= 10: # 5A  
            IScale = 5 
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale , dict["CurrentTrigger_OSC_Channel"])
        
        elif self.CurrentTrigger_V_Settling_Band  > 10 and self.CurrentTrigger_V_Settling_Band<= 20: # 10A
            IScale = 10
            Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
            Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor , dict["CurrentTrigger_OSC_Channel"])
        
    
        #########################################

        Oscilloscope(dict["OSC"]).setChannel_Display("0", dict["DUT_OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannel_Display("1", dict["DUT_OSC_Channel"])

        #(50<->100% Loading)
        #Falling Detect
        Oscilloscope(dict["OSC"]).run()
        sleep(2)
        #Begin with 50% Load
        Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
        WAI(dict["ELoad"])
        sleep(3)
        #Increase to 100% Current
        Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
        sleep(3)

        Oscilloscope(dict["OSC"]).stop()
        Vmin = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL1")
        Irise = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL2")

        """while abs(Vmin[0]) > (VScale*4):
            if abs(Vmin[0]) - (VScale*4) <= (0.001 * multiplier_scale_DUT):
                VScale = VScale + (0.001 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.002 * multiplier_scale_DUT):
                VScale = VScale + (0.002 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.005 * multiplier_scale_DUT):
                VScale = VScale + (0.005 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.01 * multiplier_scale_DUT):
                VScale = VScale + (0.01 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.02 * multiplier_scale_DUT):
                VScale = VScale + (0.02 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.05 * multiplier_scale_DUT):
                VScale = VScale + (0.05 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.1 * multiplier_scale_DUT):
                VScale = VScale +(0.1 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.2 * multiplier_scale_DUT):
                VScale = VScale + (0.2 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (0.5 * multiplier_scale_DUT):
                VScale = VScale + (0.5 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (1 * multiplier_scale_DUT):
                VScale = VScale + (1 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmin[0]) - (VScale*4) <= (2 * multiplier_scale_DUT):
                VScale = VScale + (2 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            else:
                VScale = VScale
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
            
            if abs(Irise[0]) > (IScale*4):
                if abs(Irise[0]) - (IScale*4) <= (0.001 * multiplier_scale_TRI):
                    IScale = IScale + (0.001 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])  
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.002 * multiplier_scale_TRI):
                    IScale = IScale + (0.002 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.005 * multiplier_scale_TRI):
                    IScale = IScale + (0.005 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.01 * multiplier_scale_TRI):
                    IScale = IScale + (0.01 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.02 * multiplier_scale_TRI):
                    IScale = IScale + (0.02 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.05 * multiplier_scale_TRI):
                    IScale = IScale + (0.05 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.1 * multiplier_scale_TRI): 
                    IScale = IScale + (0.1 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.2 * multiplier_scale_TRI):
                    IScale = IScale + (0.2 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (0.5 * multiplier_scale_TRI):
                    IScale = IScale + (0.5 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (1 * multiplier_scale_TRI):
                    IScale = IScale + (1 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Irise[0]) - (IScale*4) <= (2 * multiplier_scale_TRI):
                    IScale = IScale + (2 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                else:
                    IScale = IScale
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
            
            #Rerun (50<->100% Loading)
            #Falling Detect
            Oscilloscope(dict["OSC"]).run()
            sleep(2)
            #Begin with 50% Load
            Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
            WAI(dict["ELoad"])
            sleep(3)
            #Increase to 100% Current
            Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
            sleep(3)

            Oscilloscope(dict["OSC"]).stop()
            Vmin = Oscilloscope(dict["OSC"]).measureVMIN("CHANNEL1")

            if abs(Vmin[0]) < (VScale*4):
                break"""
            
        Xmin=Oscilloscope(dict["OSC"]).measureXMIN("CHANNEL1")
        Fallingtime=Oscilloscope(dict["OSC"]).measureFallingtime("CHANNEL1")
        Xini = np.array(Xmin) - np.array(Fallingtime)
        print(Vmin[0])
        print(Xmin[0])
        print(Fallingtime[0])
        print(Xini[0])

        #Set marker
        Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
        Oscilloscope(dict["OSC"]).set_marker_X2(Xmin[0])
        Oscilloscope(dict["OSC"]).set_marker_Y1(0)
        Oscilloscope(dict["OSC"]).set_marker_Y2(Vmin[0])

        try:
            Oscilloscope(dict["OSC"]).displaydata()
            displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
        png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_HighVoltage_Falling_{VMax}@{I_halfLoad}to{I_fullLoad}{current_time}.png")

        # Save PNG file as binary
        with open(png_file, "wb") as file:
            file.write(displayData)

        print(f"Screenshot saved at: {png_file}")

        """if VMIN > self.V_Settling_Band:
        #Within Spec
            print("Test Pass")
        else:
        #Above Spec
            print("Test Fail")"""
        
        #100 to 50%
        Oscilloscope(dict["OSC"]).run()
        sleep(2)

        #Increase to 100% Current
        Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
        sleep(3)
        Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
        WAI(dict["ELoad"])
        sleep(3)

        #Rasing Detect
        Oscilloscope(dict["OSC"]).stop()
        Vmax=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL1")
        Ifall=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL2")

        """while abs(Vmax[0]) > (VScale*4):
            if abs(Vmax[0]) - (VScale*4) <= (0.001 * multiplier_scale_DUT):
                VScale = VScale + (0.001 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.002 * multiplier_scale_DUT): 
                VScale = VScale + (0.002 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.005 * multiplier_scale_DUT):
                VScale = VScale + (0.005 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.01 * multiplier_scale_DUT):
                VScale = VScale + (0.01 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.02 * multiplier_scale_DUT):
                VScale = VScale + (0.02 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.05 * multiplier_scale_DUT):
                VScale = VScale + (0.05 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
                
            elif abs(Vmax[0]) - (VScale*4) <= (0.1 * multiplier_scale_DUT):
                VScale = VScale + (0.1 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <=( 0.2 * multiplier_scale_DUT):
                VScale = VScale + (0.2 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (0.5 * multiplier_scale_DUT):
                VScale = VScale + (0.5 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (1 * multiplier_scale_DUT):
                VScale = VScale + (1 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            elif abs(Vmax[0]) - (VScale*4) <= (2 * multiplier_scale_DUT):  
                VScale = VScale +( 2 * multiplier_scale_DUT)
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])

            else:   
                VScale = VScale
                Oscilloscope(dict["OSC"]).setVerticalScale(VScale, dict["DUT_OSC_Channel"])
                Oscilloscope(dict["OSC"]).setChannelOffest(-1*(VScale), dict["DUT_OSC_Channel"])
            
            if abs(Ifall[0]) > (IScale*4):
                if abs(Ifall[0]) - (IScale*4) <= (0.001 * multiplier_scale_TRI):
                    IScale = IScale +( 0.001 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= (0.002 * multiplier_scale_TRI):
                    IScale = IScale + (0.002 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= (0.005 * multiplier_scale_TRI):
                    IScale = IScale +( 0.005 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.01 * multiplier_scale_TRI:
                    IScale = IScale + (0.01  * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.02 * multiplier_scale_TRI:
                    IScale = IScale + (0.02  * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.05 * multiplier_scale_TRI:
                    IScale = IScale + (0.05  * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.1  * multiplier_scale_TRI:
                    IScale = IScale + (0.1 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.2  * multiplier_scale_TRI:
                    IScale = IScale +( 0.2 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 0.5  * multiplier_scale_TRI:
                    IScale = IScale + (0.5 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 1 * multiplier_scale_TRI:
                    IScale = IScale + (1 * multiplier_scale_TRI)
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                elif abs(Ifall[0]) - (IScale*4) <= 2 * multiplier_scale_TRI:
                    IScale = IScale +( 2 * multiplier_scale_TRI  )
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
                else:
                    IScale = IScale
                    Oscilloscope(dict["OSC"]).setVerticalScale(IScale, dict["CurrentTrigger_OSC_Channel"])
                    Oscilloscope(dict["OSC"]).setChannelOffest(IScale * I_Offset_shift_factor, dict["CurrentTrigger_OSC_Channel"])
            
            #Rerun (100<->50% Loading)
            #Rasing Detect
            Oscilloscope(dict["OSC"]).run()
            sleep(2)
            #Increase to 100% Current
            Current(dict["ELoad"]).setOutputCurrent(I_fullLoad)
            sleep(3)
            Current(dict["ELoad"]).setOutputCurrent(I_halfLoad)
            WAI(dict["ELoad"])
            sleep(3)

            Oscilloscope(dict["OSC"]).stop()
            Vmax=Oscilloscope(dict["OSC"]).measureVMAX("CHANNEL1")

            if abs(Vmax[0]) < (VScale*4):
                break"""

        Xmax=Oscilloscope(dict["OSC"]).measureXMAX("CHANNEL1")
        Risingtime=Oscilloscope(dict["OSC"]).measureRisingtime("CHANNEL1")
        Xini = np.array(Xmax) - (np.array(Risingtime))

        #Set marker
        Oscilloscope(dict["OSC"]).set_marker_X1(Xini[0])
        Oscilloscope(dict["OSC"]).set_marker_X2(Xmax[0])
        Oscilloscope(dict["OSC"]).set_marker_Y1(0)
        Oscilloscope(dict["OSC"]).set_marker_Y2(Vmax[0])

        try:
            Oscilloscope(dict["OSC"]).displaydata()
            displayData=Oscilloscope(dict["OSC"]).read_binary_data()
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
        png_file = os.path.join(save_path, f"Oscilloscope_Screenshot_HighVoltage_Rising_{VMax}@{I_halfLoad}to{I_fullLoad}{current_time}.png")

        # Save PNG file as binary
        with open(png_file, "wb") as file:
            file.write(displayData)

        print(f"Screenshot saved at: {png_file}")

        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Oscilloscope(dict["OSC"]).run()
        Oscilloscope(dict["OSC"]).setTriggerSweepMode("AUTO")

class NewLoadRegulation:
    def __init__(self):
        self.results= []
        pass

    def executeCV_LoadRegulation(self, dict):
        """Test for determining the Load Regulation of DUT under Constant Voltage (CV) Mode.

        The function first dynamically imports the library to be used. Next, settings for the
        Instruments will be initialized. The test begins by measuring the No Load Voltage when
        the PSU is turned on at max nominal settings but ELoad is turned off. Then, the ELoad is
        turned on to drive the DUT to full load, while measuring the V_FullLoad, Calculations
        are then done to check the load regulation under CV condition.

        The synchronization of Instruments here is done by reading the status of the event registry.
        The status determined from the Instrument can let the program determine if the Instrument is
        measuring. The program will only proceed to tell the Instrument to query the measured value
        after it is determined that the measurement has been completed. This method is suitable for
        operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
        more complicated than other methods. This method only can be implemented that have the specific
        commands that are used.

        Args:
            Instrument: String determining which library to be used.
            Error_Gain: Float determining the error gain of the Load Regulation Specifications.
            Error_Offset: Float determining the error offset of the Load Regulation Specifications.
            V_Rating: Float containing the Rated Voltage of the DUT.
            I_Rating: Float containing the Rated Current of the DUT.
            P_Rating: Float containing the Rated Power of the DUT.
            PSU: String containing the VISA Address of PSU used.
            DMM: String containing the VISA Address of dictDMM used.
            ELoad: String containing the VISA Address of ELoad used.
            PSU_Channel: Integer containing the channel number that the PSU is using.
            ELoad_Channel: Integer containing the channel number that the ELoad is using.
            setVoltage_Sense: String determining the Voltage Sense that is used.
            VoltageRes: String determining the Voltage Resolution that is used.
            setMode: String determining the Priority Mode of the ELoad.
            Range: String determining the measuring range of DMMshould be Auto or specified range.
            Apreture: String determining the NPLC to be used by DMM when measuring.
            AutoZero: String determining if AutoZero Mode on DMM should be enabled/disabled.
            InputZ: String determining the Input Impedance Mode of DMM.
            UpTime: Float containing details regarding the uptime delay.
            DownTime: Float containing details regarding the downtime delay.
            I_Max: Float storing the maximum nominal current value based on Power & Voltage Rating
            V_NL: Float storing the measured voltage during no load.
            V_FL: Float storing the measured voltage during full load.

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
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])

        self.results = []

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = dict["PSU_Channel"]
        self.updatedelay = float(dict["updatedelay"])
        sleep(3)
        sleep(self.updatedelay)

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        # Instrument Initializations
        Configure(dict["DMM"]).write("Voltage")
        Trigger(dict["DMM"]).setSource("BUS")
        Sense(dict["DMM"]).setVoltageResDC("DEF")
        Function(dict["ELoad"]).setMode("Current")
        sleep(0.5)

        #Instrument Channel Set
        Voltage(dict["PSU"]).setInstrumentChannel(ch)
        Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
        Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])
        sleep(0.5)

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
        
        #DMM Mode
        Voltage(dict["DMM"]).setNPLC(dict["Aperture"])
        Voltage(dict["DMM"]).setAutoZeroMode(dict["AutoZero"])
        Voltage(dict["DMM"]).setAutoImpedanceMode(dict["InputZ"])
        sleep(0.5)

        if dict["Range"] == "Auto":
            Sense(dict["DMM"]).setVoltageRangeDCAuto()

        else:
            Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])

        #Programming Parameters
        self.V_Rating = float(dict["V_Rating"])
        self.I_Rating = float(dict["I_Rating"])
        self.P_Rating = float(dict["P_Rating"])

        self.powerfin = int(dict["power"])          #power test
        self.voltagemax = float(dict["maxVoltage"])
        self.currentmax = float(dict["maxCurrent"])
        
        self.param1 = float(dict["Load_Programming_Error_Gain"])
        self.param2 = float(dict["Load_Programming_Error_Offset"])

        #Reducer to avoid CV->CC mode 
        IL_reducer = 0.05

        #Clear the Error Status
        CLS(dict["PSU"])
        WAI(dict["PSU"])
        CLS(dict["ELoad"])
        WAI(dict["ELoad"])
        CLS(dict["DMM"])
        WAI(dict["DMM"])
        sleep(0.5)

        try:
    ###############################################################################################
            #High Voltage Low Current
            I_Max = round(self.powerfin / self.voltagemax, 2)       #Current based on Vmax and Power Test

            #PSU ON, ELoad OFF
            Current(dict["PSU"]).setOutputCurrent("MAX")
            WAI(dict["PSU"])
            Voltage(dict["PSU"]).setOutputVoltage(self.voltagemax)
            WAI(dict["PSU"])
            Output(dict["PSU"]).setOutputState("ON")
            WAI(dict["PSU"])

            sleep(self.updatedelay)

            #Reading for No Load - High Voltage Low Current
            Initiate(dict["DMM"]).initiate()
            TRG(dict["DMM"])
            V_NL_HighVoltage = float(Fetch(dict["DMM"]).query())

            #PSU ON, ELoad ON
            Current(dict["ELoad"]).setOutputCurrent(I_Max)
            WAI(dict["ELoad"])
            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])

            sleep(self.updatedelay)

            #Reading for Full Load - High Voltage Low Current
            Initiate(dict["DMM"]).initiate()
            TRG(dict["DMM"])
            V_FL_HighVoltage = float(Fetch(dict["DMM"]).query())
            
            sleep(self.updatedelay)

            Output(dict["PSU"]).setOutputState("OFF")
            WAI(dict["PSU"])
            Output(dict["ELoad"]).setOutputState("OFF")
            WAI(dict["ELoad"])
            
    #################################################################################################################################
            #Low Voltage High Current
            V_Max = round(self.powerfin / self.currentmax,2)        #Voltage based on Imax and Power Test
            
            #PSU ON, ELoad OFF
            Current(dict["PSU"]).setOutputCurrent("MAX")
            WAI(dict["PSU"])
            Voltage(dict["PSU"]).setOutputVoltage(V_Max)
            WAI(dict["PSU"])
            Output(dict["PSU"]).setOutputState("ON")
            WAI(dict["PSU"])

            sleep(float(self.updatedelay))

            # Reading for No Load - High Current Low voltage
            Initiate(dict["DMM"]).initiate()
            TRG(dict["DMM"])
            V_NL_LowVoltage = float(Fetch(dict["DMM"]).query())
            
            #To reduce the current (maintain CV mode)
            while True:
                #PSU ON, ELoad ON
                Current(dict["ELoad"]).setOutputCurrent(self.currentmax)
                WAI(dict["ELoad"])

                Mode = int(Status(dict["PSU"]).CV_CC_OperationModeQuery(ch))
                sleep(3)

                #Dolphine 2-CC mode (CV mode required)
                if Mode != 1:
                    self.currentmax *= 0.95  # Decrease by 1%
                    print(f"Current max: {self.currentmax:.4f}")  # Optional: for debugging
                    sleep(2)
                else:
                    break

            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])

            sleep(float(self.updatedelay))

            #Reading for Full Load for High Current Low voltage
            Initiate(dict["DMM"]).initiate()
            TRG(dict["DMM"])
            WAI(dict["ELoad"])
            V_FL_LowVoltage = float(Fetch(dict["DMM"]).query())
            
            sleep(float(self.updatedelay))

        except:
            error_message = traceback.format_exc()  # Get the full error traceback
            print(error_message)
            
        #Load Regulation Calculation (CV)
        Voltage_Regulation_HighVoltage = (V_FL_HighVoltage - V_NL_HighVoltage)
        Voltage_Regulation_LowVoltage = (V_FL_LowVoltage - V_NL_LowVoltage)
        Desired_Voltage_Regulation_HighVoltage = ((float(self.voltagemax) * self.param1) + (float(self.V_Rating) * self.param2))
        Desired_Voltage_Regulation_LowVoltage = ((float(V_Max) * self.param1) + (float(self.V_Rating) * self.param2))
        
        #Data to be saved
        self.results.append([ch, self.voltagemax, I_Max, V_NL_HighVoltage, V_FL_HighVoltage, Desired_Voltage_Regulation_HighVoltage,
            Voltage_Regulation_HighVoltage, V_Max, self.currentmax, V_NL_LowVoltage, V_FL_LowVoltage, Desired_Voltage_Regulation_LowVoltage,
            Voltage_Regulation_LowVoltage])

        print("Channel {ch}")
        print(" ")
        print("Voltage Regulation Configuration for High Voltage Low Current", self.voltagemax, "V @ ", I_Max, "A")
        print("V_NL_High Voltage Low Current: ", V_NL_HighVoltage, "V_FL_High Voltage Low Current: ", V_FL_HighVoltage)
        print("Desired Voltage Regulation for High Voltage (CV): (V)", Desired_Voltage_Regulation_HighVoltage)
        print("Calculated Voltage Regulation for High Voltage (V):", Voltage_Regulation_HighVoltage)

        print(" ")
        print("Voltage Regulation Configuration for Low Voltage High Current", V_Max, "V", self.currentmax, "A")
        print("V_NL_Low Voltage High Current: ", V_NL_LowVoltage, "V_FL_Low Voltage High Current: ", V_FL_LowVoltage)      
        print("Desired Voltage Regulation for Low Voltage (CV): (V)", Desired_Voltage_Regulation_LowVoltage)
        print("Calculated Voltage Regulation for Low Voltage (V):", Voltage_Regulation_LowVoltage)
        print(" ")

        #Clear Status
        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
    
        return self.results

    def executeCC_LoadRegulation(self, dict):
        """Test for determining the Load Regulation of DUT under Constant Current (CC) Mode.

        The function first dynamically imports the library to be used. Next, settings for the
        Instrument will be initialized. The test begins by measuring the No Load Voltage when
        the PSU is turned on at max nominal settings but ELoad is turned off. Then, the ELoad is
        turned on to drive the DUT to full load, while measuring the V_FullLoad, Calculations
        are then done to check the load regulation under CC condition.

        The synchronization of Instrument here is done by reading the status of the event registry.
        The status determined from the Instrument can let the program determine if the Instrument is
        measuring. The program will only proceed to tell the Instrument to query the measured value
        after it is determined that the measurement has been completed. This method is suitable for
        operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
        more complicated than other methods. This method only can be implemented that have the specific
        commands that are used.

        Args:
            Instrument: String determining which library to be used.
            Error_Gain: Float determining the error gain of the Load Regulation Specifications.
            Error_Offset: Float determining the error offset of the Load Regulation Specifications.
            V_Rating: Float containing the Rated Voltage of the DUT.
            I_Rating: Float containing the Rated Current of the DUT.
            P_Rating: Float containing the Rated Power of the DUT.
            PSU: String containing the VISA Address of PSU used.
            DMM: String containing the VISA Address of DMM used.
            ELoad: String containing the VISA Address of ELoad used.
            PSU_Channel: Integer containing the channel number that the PSU is using.
            ELoad_Channel: Integer containing the channel number that the ELoad is using.
            setVoltage_Sense: String determining the Voltage Sense that is used.
            setCurrent_Res: String determining the Current Resolution that is used.
            setMode: String determining the Priority Mode of the ELoad.
            Range: String determining the measuring range of DMM should be Auto or specified range.
            Apreture: String determining the NPLC to be used by DMM when measuring.
            AutoZero: String determining if AutoZero Mode on DMM should be enabled/disabled.
            InputZ: String determining the Input Impedance Mode of DMM.
            UpTime: Float containing details regarding the uptime delay.
            DownTime: Float containing details regarding the downtime delay.
            V_Max: Float storing the maximum nominal voltage value based on Power & Voltage Rating
            I_NL: Float storing the measured current during no load.
            I_FL: Float storing the measured current during full load.

        Raises:
            VisaIOError: An error occured when opening PyVisa Resources.

        """
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
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM2"])
        WAI(dict["DMM2"])

        self.results = []

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = dict["PSU_Channel"]
        self.updatedelay = float(dict["updatedelay"])
        sleep(3)
        sleep(self.updatedelay)

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")

        # Instrument Initializations
        Configure(dict["DMM2"]).write("Voltage")
        Trigger(dict["DMM2"]).setSource("BUS")
        Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])
        Function(dict["ELoad"]).setMode("Voltage")
        sleep(0.5)

        #Instrument Channel Set
        Voltage(dict["PSU"]).setInstrumentChannel(ch)
        Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
        Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])
        Function(dict["PSU"]).setMode("Current")
        sleep(0.5)
        
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

        Voltage(dict["DMM2"]).setNPLC(dict["Aperture"])
        Voltage(dict["DMM2"]).setAutoZeroMode(dict["AutoZero"])
        Voltage(dict["DMM2"]).setAutoImpedanceMode(dict["InputZ"])
        #Voltage(dict["DMM"]).setTerminal(dict["Terminal"])

        if dict["Range"] == "Auto":
            Sense(dict["DMM2"]).setCurrentRangeDCAuto()

        else:
            Sense(dict["DMM2"]).setCurrentRangeDC(dict["Range"])

        #Programming Parameters
        self.V_Rating = float(dict["V_Rating"])
        self.I_Rating = float(dict["I_Rating"])
        self.P_Rating = float(dict["P_Rating"])

        self.powerfin = int(dict["power"])
        self.voltagemax = float(dict["maxVoltage"])
        self.currentmax = float(dict["maxCurrent"])

        self.param1 = float(dict["Load_Programming_Error_Gain"])
        self.param2 = float(dict["Load_Programming_Error_Offset"])

        self.updatedelay = float(dict["updatedelay"])
        self.rshunt = float(dict["rshunt"])

        #Shunt Voltage Drop
        if self.rshunt == 0.01: #(100A) (1V + cable loss)
            VshuntdropMax = 2
        elif self.rshunt == 0.05:#(50A) (2.5V + cable loss)
            VshuntdropMax = 3.5
        elif self.rshunt == 1: #(10A)  (10V + cable loss)
            VshuntdropMax == 11
    
        #Clear the Error Status
        CLS(dict["PSU"])
        WAI(dict["PSU"])
        CLS(dict["ELoad"])
        WAI(dict["ELoad"])
        CLS(dict["DMM"])
        WAI(dict["DMM"])
        sleep(0.5)

        try:
            ############################################################################################################
            #No Load Test (Light Load) - Test For High Current Low Voltage
            V_Max = round(self.powerfin / self.currentmax, 2)
            Voltage(dict["PSU"]).setOutputVoltage("MAX")
            Current(dict["PSU"]).setOutputCurrent(self.currentmax)
            #Voltage(dict["ELoad"]).setOutputVoltage(1) #Acting Light Load
            Voltage(dict["ELoad"]).setOutputVoltage(V_Max)
            Output(dict["ELoad"]).shortInput("ON")
            WAI(dict["ELoad"])
            Output(dict["PSU"]).setOutputState("ON")
            WAI(dict["PSU"])
            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])

            sleep(self.updatedelay)

            # Reading for No Load Voltage
            Initiate(dict["DMM2"]).initiate()
            TRG(dict["DMM2"])
            I_NL_HighCurrent = float(Fetch(dict["DMM2"]).query())/self.rshunt

            ###########################################################################
            #Full Load Test - High Current Low Voltage
            Output(dict["ELoad"]).shortInput("OFF")
            WAI(dict["ELoad"])
            Voltage(dict["ELoad"]).setOutputVoltage(V_Max - VshuntdropMax)
            WAI(dict["ELoad"])
            sleep(self.updatedelay)

            Initiate(dict["DMM2"]).initiate()
            TRG(dict["DMM2"])
            I_FL_HighCurrent = float(Fetch(dict["DMM2"]).query())/self.rshunt

            sleep(self.updatedelay)

            Output(dict["PSU"]).setOutputState("OFF")
            WAI(dict["PSU"])
            Output(dict["ELoad"]).setOutputState("OFF")
            WAI(dict["ELoad"])
            sleep(self.updatedelay)

            ############################################################################################################
            #No Load Test (Light Load) - Test For Low Current High Voltage
            I_Max = round(self.powerfin / self.voltagemax, 2)
            Voltage(dict["PSU"]).setOutputVoltage("MAX") 
            Current(dict["PSU"]).setOutputCurrent(I_Max)
            Voltage(dict["ELoad"]).setOutputVoltage(self.voltagemax)
            Output(dict["ELoad"]).shortInput("ON")
            WAI(dict["ELoad"])
            Output(dict["PSU"]).setOutputState("ON")
            WAI(dict["PSU"])
            Output(dict["ELoad"]).setOutputState("ON")
            WAI(dict["ELoad"])

            sleep(self.updatedelay)
            
            # Reading for No Load Voltage
            Initiate(dict["DMM2"]).initiate()
            TRG(dict["DMM2"])
            Delay(dict["PSU"]).write(dict["UpTime"])
            I_NL_LowCurrent = float(Fetch(dict["DMM2"]).query())/self.rshunt

            sleep(self.updatedelay)

            ###########################################################################
            #Full Load Test - Low Current High Voltage
            Output(dict["ELoad"]).shortInput("OFF")
            WAI(dict["ELoad"])
            Voltage(dict["ELoad"]).setOutputVoltage(self.voltagemax - VshuntdropMax)
            WAI(dict["ELoad"])

            sleep(self.updatedelay)

            Initiate(dict["DMM2"]).initiate()
            TRG(dict["DMM2"])
            I_FL_LowCurrent = float(Fetch(dict["DMM2"]).query())/self.rshunt

        except:
            error_message = traceback.format_exc()  # Get the full error traceback
            print(error_message)

        #Load Regulation Calculation (CC)
        Current_Regulation_HighCurrent = (I_FL_HighCurrent - I_NL_HighCurrent) 
        Current_Regulation_LowCurrent = (I_FL_LowCurrent - I_NL_LowCurrent)
        Desired_Current_Regulation_HighCurrent =( float(self.I_Rating) * (self.param1 + self.param2))
        Desired_Current_Regulation_LowCurrent = ((I_Max * self.param1) + (self.I_Rating*self.param2))

        #Data to be saved
        self.results.append([ch, V_Max, self.currentmax, I_NL_HighCurrent, I_FL_HighCurrent, Desired_Current_Regulation_HighCurrent,
            Current_Regulation_HighCurrent, self.voltagemax, I_Max, I_NL_LowCurrent, I_FL_LowCurrent, Desired_Current_Regulation_LowCurrent,
            Current_Regulation_LowCurrent])

        print("Channel {ch}")
        print(" ")
        print("Current Regulation for High Current ", V_Max, "V @ ", self.currentmax,"A")
        print("I_NL_High Current: ", I_NL_HighCurrent, "I_FL_High Current: ", I_FL_HighCurrent)
        print("Desired Load Regulation High Current (CC): (A)", Desired_Current_Regulation_HighCurrent)
        print("Calculated Load Regulation High Current (CC): (A)", Current_Regulation_HighCurrent)

        print(" ")
        print("Current Regulation for Low Current ", self.voltagemax, "V @ ", I_Max,"A")
        print("I_NL_Low Current: ", I_NL_LowCurrent, "I_FL_Low Current: ", I_FL_LowCurrent)
        print("Desired Load Regulation Low Current (CC): (A)", Desired_Current_Regulation_LowCurrent)
        print("Calculated Load Regulation Low Current (CC): (A)", Current_Regulation_LowCurrent)

        #Clear Status
        Voltage(dict["ELoad"]).setOutputVoltage(0)
        WAI(dict["ELoad"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])

        return self.results

class LineRegulation:
    def __init__(self):
        self.results= []
        pass

    def executeCV_LoadRegulation(self, dict):
        """Test for determining the Load Regulation of DUT under Constant Voltage (CV) Mode.

        The function first dynamically imports the library to be used. Next, settings for the
        Instruments will be initialized. The test begins by measuring the No Load Voltage when
        the PSU is turned on at max nominal settings but ELoad is turned off. Then, the ELoad is
        turned on to drive the DUT to full load, while measuring the V_FullLoad, Calculations
        are then done to check the load regulation under CV condition.

        The synchronization of Instruments here is done by reading the status of the event registry.
        The status determined from the Instrument can let the program determine if the Instrument is
        measuring. The program will only proceed to tell the Instrument to query the measured value
        after it is determined that the measurement has been completed. This method is suitable for
        operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
        more complicated than other methods. This method only can be implemented that have the specific
        commands that are used.

        Args:
            Instrument: String determining which library to be used.
            Error_Gain: Float determining the error gain of the Load Regulation Specifications.
            Error_Offset: Float determining the error offset of the Load Regulation Specifications.
            V_Rating: Float containing the Rated Voltage of the DUT.
            I_Rating: Float containing the Rated Current of the DUT.
            P_Rating: Float containing the Rated Power of the DUT.
            PSU: String containing the VISA Address of PSU used.
            DMM: String containing the VISA Address of dictDMM used.
            ELoad: String containing the VISA Address of ELoad used.
            PSU_Channel: Integer containing the channel number that the PSU is using.
            ELoad_Channel: Integer containing the channel number that the ELoad is using.
            setVoltage_Sense: String determining the Voltage Sense that is used.
            VoltageRes: String determining the Voltage Resolution that is used.
            setMode: String determining the Priority Mode of the ELoad.
            Range: String determining the measuring range of DMMshould be Auto or specified range.
            Apreture: String determining the NPLC to be used by DMM when measuring.
            AutoZero: String determining if AutoZero Mode on DMM should be enabled/disabled.
            InputZ: String determining the Input Impedance Mode of DMM.
            UpTime: Float containing details regarding the uptime delay.
            DownTime: Float containing details regarding the downtime delay.
            I_Max: Float storing the maximum nominal current value based on Power & Voltage Rating
            V_NL: Float storing the measured voltage during no load.
            V_FL: Float storing the measured voltage during full load.

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
        ) = Dimport.getClasses(dict["Instrument"])

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = dict["PSU_Channel"]
        self.updatedelay = float(dict["updatedelay"])
        AC_Voltage_Nominal = dict["Line_Reg_Range"]
        self.results = [[ch]]

        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])
        RST(dict["PSU"])
        WAI(dict["PSU"])

        sleep(3)
        sleep(self.updatedelay)
        
        for i in AC_Voltage_Nominal:

            AC_LowLine = round(float(i) * 0.9,1)
            AC_HighLine = round(float(i) * 1.1,1)
            print(float(i))

            Voltage(dict["ACSource"]).setOutputVoltage(float(i))
            WAI(dict["ACSource"])
            sleep(5)
            
            #Use ch for each individual channel
            print(f"Channel {ch} Test Running\n")
            print("")
            
            # Instrument Initializations
            Configure(dict["DMM"]).write("Voltage")
            Trigger(dict["DMM"]).setSource("BUS")
            Sense(dict["DMM"]).setVoltageResDC("DEF")
            Function(dict["ELoad"]).setMode("Current")
            sleep(0.5)

            #Instrument Channel Set
            Voltage(dict["PSU"]).setInstrumentChannel(ch)
            Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])
            Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
            Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])
            sleep(0.5)

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
            
            #DMM Mode
            Voltage(dict["DMM"]).setNPLC(dict["Aperture"])
            Voltage(dict["DMM"]).setAutoZeroMode(dict["AutoZero"])
            Voltage(dict["DMM"]).setAutoImpedanceMode(dict["InputZ"])
            sleep(0.5)

            if dict["Range"] == "Auto":
                Sense(dict["DMM"]).setVoltageRangeDCAuto()

            else:
                Sense(dict["DMM"]).setVoltageRangeDC(dict["Range"])

            #Programming Parameters
            self.V_Rating = float(dict["V_Rating"])
            self.I_Rating = float(dict["I_Rating"])
            self.P_Rating = float(dict["P_Rating"])

            self.powerfin = int(dict["power"])          #power test
            self.voltagemax = float(dict["maxVoltage"])
            self.currentmax = float(dict["maxCurrent"])
            
            self.param1 = float(dict["Load_Programming_Error_Gain"])
            self.param2 = float(dict["Load_Programming_Error_Offset"])

            #Reducer to avoid CV->CC mode 
            IL_reducer = 0.05

            #Clear the Error Status
            CLS(dict["PSU"])
            WAI(dict["PSU"])
            CLS(dict["ELoad"])
            WAI(dict["ELoad"])
            CLS(dict["DMM"])
            WAI(dict["DMM"])
            sleep(0.5)

            try:
        ###############################################################################################
                #High Voltage Low Current
                I_Max = round(self.powerfin / self.voltagemax, 2)       #Current based on Vmax and Power Test

                #PSU ON, ELoad OFF
                Current(dict["PSU"]).setOutputCurrent("MAX")
                WAI(dict["PSU"])
                Voltage(dict["PSU"]).setOutputVoltage(self.voltagemax)
                WAI(dict["PSU"])
                Output(dict["PSU"]).setOutputState("ON")
                WAI(dict["PSU"])
                Current(dict["ELoad"]).setOutputCurrent(I_Max)
                WAI(dict["ELoad"])
                Output(dict["ELoad"]).setOutputState("ON")
                WAI(dict["ELoad"])
                sleep(self.updatedelay)

                #Nominal Reading
                Initiate(dict["DMM"]).initiate()
                TRG(dict["DMM"])
                V_HighVolt_Nominal = float(Fetch(dict["DMM"]).query())
                sleep(1)

                #Low Line Reading
                Voltage(dict["ACSource"]).setOutputVoltage(AC_LowLine)
                WAI(dict["ACSource"])
                sleep(3)
                Initiate(dict["DMM"]).initiate()
                TRG(dict["DMM"])
                V_HighVolt_LowLine= float(Fetch(dict["DMM"]).query())
                sleep(1)

                #High Line Reading
                Voltage(dict["ACSource"]).setOutputVoltage(AC_HighLine)
                WAI(dict["ACSource"])
                sleep(3)
                Initiate(dict["DMM"]).initiate()
                TRG(dict["DMM"])
                V_HighVolt_HighLine= float(Fetch(dict["DMM"]).query())
                sleep(1)
                sleep(self.updatedelay)

                Output(dict["PSU"]).setOutputState("OFF")
                WAI(dict["PSU"])
                Output(dict["ELoad"]).setOutputState("OFF")
                WAI(dict["ELoad"])
                
        #################################################################################################################################
                #Low Voltage High Current
                V_Max = round(self.powerfin / self.currentmax,2)        #Voltage based on Imax and Power Test
                
                #PSU ON, ELoad OFF
                Voltage(dict["ACSource"]).setOutputVoltage(AC_Voltage_Nominal)
                WAI(dict["ACSource"])
                Current(dict["PSU"]).setOutputCurrent("MAX")
                WAI(dict["PSU"])
                Voltage(dict["PSU"]).setOutputVoltage(V_Max)
                WAI(dict["PSU"])
                Output(dict["PSU"]).setOutputState("ON")
                WAI(dict["PSU"])
                Current(dict["ELoad"]).setOutputCurrent(self.currentmax)
                WAI(dict["ELoad"])
                Output(dict["ELoad"]).setOutputState("ON")
                WAI(dict["ELoad"])

                sleep(float(self.updatedelay))

                #To reduce the current (maintain CV mode)
                """
                while True:
                    #PSU ON, ELoad ON
                    Current(dict["ELoad"]).setOutputCurrent(self.currentmax)
                    WAI(dict["ELoad"])

                    Mode = int(Status(dict["PSU"]).CV_CC_OperationModeQuery(ch))
                    sleep(3)

                    #Dolphine 2-CC mode (CV mode required)
                    if Mode != 1:
                        self.currentmax *= 0.95  # Decrease by 1%
                        print(f"Current max: {self.currentmax:.4f}")  # Optional: for debugging
                        sleep(2)
                    else:
                        break
                 """

                #Reading for Full Load for High Current Low voltage
                #Nominal Reading
                Initiate(dict["DMM"]).initiate()
                TRG(dict["DMM"])
                V_HighCurr_Nominal = float(Fetch(dict["DMM"]).query())
                sleep(1)

                #Low Line Reading
                Voltage(dict["ACSource"]).setOutputVoltage(AC_LowLine)
                WAI(dict["ACSource"])
                sleep(3)
                Initiate(dict["DMM"]).initiate()
                TRG(dict["DMM"])
                V_HighCurr_LowLine= float(Fetch(dict["DMM"]).query())
                sleep(1)

                #High Line Reading
                Voltage(dict["ACSource"]).setOutputVoltage(AC_HighLine)
                WAI(dict["ACSource"])
                sleep(3)
                Initiate(dict["DMM"]).initiate()
                TRG(dict["DMM"])
                V_HighCurr_HighLine= float(Fetch(dict["DMM"]).query())
                sleep(1)
                sleep(self.updatedelay)

                Output(dict["PSU"]).setOutputState("OFF")
                WAI(dict["PSU"])
                Output(dict["ELoad"]).setOutputState("OFF")
                WAI(dict["ELoad"])

            except:
                error_message = traceback.format_exc()  # Get the full error traceback
                print(error_message)
                
            #Load Regulation Calculation (CV)
            Voltage_Regulation_HighVoltage = (V_HighVolt_HighLine - V_HighVolt_LowLine)
            Voltage_Regulation_LowVoltage = (V_HighCurr_HighLine - V_HighCurr_LowLine)
            Desired_Voltage_Regulation_HighVoltage = ((float(self.voltagemax) * self.param1) + (float(self.V_Rating) * self.param2))
            Desired_Voltage_Regulation_LowVoltage = ((float(V_Max) * self.param1) + (float(self.V_Rating) * self.param2))
            
            if Voltage_Regulation_HighVoltage < Desired_Voltage_Regulation_HighVoltage:
                Status1 = "PASS"
            else:
                Status1 = "FAIL"

            if Voltage_Regulation_LowVoltage < Desired_Voltage_Regulation_LowVoltage:
                Status2 = "PASS"
            else:
                Status2 = "FAIL"

            #Data to be saved
            self.results.append([float(i), 
                self.voltagemax, I_Max, 
                V_HighVolt_LowLine, V_HighVolt_Nominal, V_HighVolt_HighLine, 
                Desired_Voltage_Regulation_HighVoltage,Voltage_Regulation_HighVoltage, Status1])
            self.results.append([float(i),
                V_Max, self.currentmax,
                V_HighCurr_LowLine, V_HighCurr_Nominal, V_HighCurr_HighLine, 
                Desired_Voltage_Regulation_LowVoltage,Voltage_Regulation_LowVoltage,Status2])

        #Clear Status
        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        Voltage(dict["ACSource"]).setOutputVoltage(230)
        WAI(dict["ACSource"])
        #Output(dict["ACSource"]).setOutputState("OFF")
        #WAI(dict["ACSource"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
    
        return self.results


    def executeCC_LoadRegulation(self, dict):
        """Test for determining the Load Regulation of DUT under Constant Current (CC) Mode.

        The function first dynamically imports the library to be used. Next, settings for the
        Instrument will be initialized. The test begins by measuring the No Load Voltage when
        the PSU is turned on at max nominal settings but ELoad is turned off. Then, the ELoad is
        turned on to drive the DUT to full load, while measuring the V_FullLoad, Calculations
        are then done to check the load regulation under CC condition.

        The synchronization of Instrument here is done by reading the status of the event registry.
        The status determined from the Instrument can let the program determine if the Instrument is
        measuring. The program will only proceed to tell the Instrument to query the measured value
        after it is determined that the measurement has been completed. This method is suitable for
        operations that require a longer time (e.g. 100 NPLC). However the implementation is slighty
        more complicated than other methods. This method only can be implemented that have the specific
        commands that are used.

        Args:
            Instrument: String determining which library to be used.
            Error_Gain: Float determining the error gain of the Load Regulation Specifications.
            Error_Offset: Float determining the error offset of the Load Regulation Specifications.
            V_Rating: Float containing the Rated Voltage of the DUT.
            I_Rating: Float containing the Rated Current of the DUT.
            P_Rating: Float containing the Rated Power of the DUT.
            PSU: String containing the VISA Address of PSU used.
            DMM: String containing the VISA Address of DMM used.
            ELoad: String containing the VISA Address of ELoad used.
            PSU_Channel: Integer containing the channel number that the PSU is using.
            ELoad_Channel: Integer containing the channel number that the ELoad is using.
            setVoltage_Sense: String determining the Voltage Sense that is used.
            setCurrent_Res: String determining the Current Resolution that is used.
            setMode: String determining the Priority Mode of the ELoad.
            Range: String determining the measuring range of DMM should be Auto or specified range.
            Apreture: String determining the NPLC to be used by DMM when measuring.
            AutoZero: String determining if AutoZero Mode on DMM should be enabled/disabled.
            InputZ: String determining the Input Impedance Mode of DMM.
            UpTime: Float containing details regarding the uptime delay.
            DownTime: Float containing details regarding the downtime delay.
            V_Max: Float storing the maximum nominal voltage value based on Power & Voltage Rating
            I_NL: Float storing the measured current during no load.
            I_FL: Float storing the measured current during full load.

        Raises:
            VisaIOError: An error occured when opening PyVisa Resources.

        """
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
        ) = Dimport.getClasses(dict["Instrument"])

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = dict["PSU_Channel"]
        self.updatedelay = float(dict["updatedelay"])
        AC_Voltage_Nominal = dict["Line_Reg_Range"]
        self.results = [[ch]]

        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM2"])
        WAI(dict["DMM2"])
        RST(dict["PSU"])
        WAI(dict["PSU"])

        sleep(3)
        sleep(self.updatedelay)

        for i in AC_Voltage_Nominal:

            AC_LowLine = round(float(i) * 0.9,1)
            AC_HighLine = round(float(i) * 1.1,1)
            print(float(i))
            
            Voltage(dict["ACSource"]).setOutputVoltage(float(i))
            WAI(dict["ACSource"])
            sleep(5)

            #Use ch for each individual channel
            print(f"Channel {ch} Test Running\n")
            print("")

            # Instrument Initializations
            Configure(dict["DMM2"]).write("Voltage")
            Trigger(dict["DMM2"]).setSource("BUS")
            Sense(dict["DMM2"]).setVoltageResDC(dict["VoltageRes"])
            Function(dict["ELoad"]).setMode("Voltage")
            sleep(0.5)

            #Instrument Channel Set
            Voltage(dict["PSU"]).setInstrumentChannel(ch)
            Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
            Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])
            Function(dict["PSU"]).setMode("Current")
            sleep(0.5)
            
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

            #DMM Mode
            Voltage(dict["DMM2"]).setNPLC(dict["Aperture"])
            Voltage(dict["DMM2"]).setAutoZeroMode(dict["AutoZero"])
            Voltage(dict["DMM2"]).setAutoImpedanceMode(dict["InputZ"])
            #Voltage(dict["DMM"]).setTerminal(dict["Terminal"])
            sleep(0.5)

            if dict["Range"] == "Auto":
                Sense(dict["DMM2"]).setCurrentRangeDCAuto()

            else:
                Sense(dict["DMM2"]).setCurrentRangeDC(dict["Range"])

            #Programming Parameters
            self.V_Rating = float(dict["V_Rating"])
            self.I_Rating = float(dict["I_Rating"])
            self.P_Rating = float(dict["P_Rating"])
            self.powerfin = int(dict["power"])
            self.voltagemax = float(dict["maxVoltage"])
            self.currentmax = float(dict["maxCurrent"])
            self.param1 = float(dict["Load_Programming_Error_Gain"])
            self.param2 = float(dict["Load_Programming_Error_Offset"])
            self.rshunt = float(dict["rshunt"])

            #Shunt Voltage Drop
            if self.rshunt == 0.01: #(100A) (1V + cable loss)
                VshuntdropMax = 2
            elif self.rshunt == 0.05:#(50A) (2.5V + cable loss)
                VshuntdropMax = 3.5
            elif self.rshunt == 1: #(10A)  (10V + cable loss)
                VshuntdropMax == 11
        
            #Clear the Error Status
            CLS(dict["PSU"])
            WAI(dict["PSU"])
            CLS(dict["ELoad"])
            WAI(dict["ELoad"])
            CLS(dict["DMM2"])
            WAI(dict["DMM2"])
            sleep(0.5)

            try:
                ############################################################################################################
                #No Load Test (Light Load) - Test For High Current Low Voltage
                V_Max = round(self.powerfin / self.currentmax, 2)
                
                Voltage(dict["PSU"]).setOutputVoltage("MAX")
                Current(dict["PSU"]).setOutputCurrent(self.currentmax)
                #Voltage(dict["ELoad"]).setOutputVoltage(V_Max)
                Voltage(dict["ELoad"]).setOutputVoltage(V_Max - VshuntdropMax)
                WAI(dict["ELoad"])
                Output(dict["PSU"]).setOutputState("ON")
                WAI(dict["PSU"])
                Output(dict["ELoad"]).setOutputState("ON")
                WAI(dict["ELoad"])
                sleep(self.updatedelay)

                #Nominal Reading (High Curr)
                Initiate(dict["DMM2"]).initiate()
                TRG(dict["DMM2"])
                I_HighCurr_Nominal = float(Fetch(dict["DMM2"]).query()) / self.rshunt
                sleep(1)

                #Low Line Reading
                Voltage(dict["ACSource"]).setOutputVoltage(AC_LowLine)
                WAI(dict["ACSource"])
                sleep(3)
                Initiate(dict["DMM2"]).initiate()
                TRG(dict["DMM2"])
                I_HighCurr_LowLine= float(Fetch(dict["DMM2"]).query()) / self.rshunt
                sleep(1)

                #High Line Reading
                Voltage(dict["ACSource"]).setOutputVoltage(AC_HighLine)
                WAI(dict["ACSource"])
                sleep(3)
                Initiate(dict["DMM2"]).initiate()
                print("DMM2 Initiated")
                TRG(dict["DMM2"])
                print("DMM2 Triggered")
                I_HighCurr_HighLine= float(Fetch(dict["DMM2"]).query()) / self.rshunt
                sleep(1)
                sleep(self.updatedelay)

                Output(dict["PSU"]).setOutputState("OFF")
                WAI(dict["PSU"])
                Output(dict["ELoad"]).setOutputState("OFF")
                WAI(dict["ELoad"])

                ############################################################################################################
                #Test For Low Current High Voltage

                I_Max = round(self.powerfin / self.voltagemax, 2)

                Voltage(dict["ACSource"]).setOutputVoltage(AC_Voltage_Nominal)
                WAI(dict["ACSource"])
                Voltage(dict["PSU"]).setOutputVoltage("MAX") 
                WAI(dict["PSU"])
                Current(dict["PSU"]).setOutputCurrent(I_Max)
                WAI(dict["PSU"])
                Voltage(dict["ELoad"]).setOutputVoltage(self.voltagemax - VshuntdropMax)
                WAI(dict["ELoad"])
                Output(dict["PSU"]).setOutputState("ON")
                WAI(dict["PSU"])
                Output(dict["ELoad"]).setOutputState("ON")
                WAI(dict["ELoad"])
                sleep(self.updatedelay)
                
                #Nominal (High Voltage)
                Initiate(dict["DMM2"]).initiate()
                TRG(dict["DMM2"])
                I_HighVolt_Nominal = float(Fetch(dict["DMM2"]).query())/self.rshunt
                sleep(1)

                #Low Line Reading
                Voltage(dict["ACSource"]).setOutputVoltage(AC_LowLine)
                WAI(dict["ACSource"])
                sleep(3)
                Initiate(dict["DMM2"]).initiate()
                TRG(dict["DMM2"])
                I_HighVolt_LowLine = float(Fetch(dict["DMM2"]).query())/self.rshunt
                sleep(1)

                #High Line Reading
                Voltage(dict["ACSource"]).setOutputVoltage(AC_HighLine)
                WAI(dict["ACSource"])
                sleep(3)
                Initiate(dict["DMM2"]).initiate()
                TRG(dict["DMM2"])
                I_HighVolt_HighLine = float(Fetch(dict["DMM2"]).query())/self.rshunt
                sleep(1)


            except:
                error_message = traceback.format_exc()  # Get the full error traceback
                print(error_message)

            #Load Regulation Calculation (CC)
            Current_Regulation_HighCurrent = (I_HighCurr_HighLine - I_HighCurr_LowLine) 
            Current_Regulation_LowCurrent = (I_HighVolt_HighLine - I_HighVolt_LowLine)
            Desired_Current_Regulation_HighCurrent =(float(self.I_Rating) * (self.param1 + self.param2))
            Desired_Current_Regulation_LowCurrent = ((I_Max * self.param1) + (self.I_Rating*self.param2))

            if Current_Regulation_HighCurrent < Desired_Current_Regulation_HighCurrent :
                Status1 = "PASS"
            else:
                Status1 = "FAIL"

            if Current_Regulation_LowCurrent < Desired_Current_Regulation_LowCurrent:
                Status2 = "PASS"
            else:
                Status2 = "FAIL"

            #Data to be saved
            self.results.append([float(i), 
                V_Max, self.currentmax,
                I_HighCurr_LowLine, I_HighCurr_Nominal, I_HighCurr_HighLine, 
                Desired_Current_Regulation_HighCurrent,Current_Regulation_HighCurrent, Status1])
            self.results.append([float(i),
                self.voltagemax, I_Max, 
                I_HighVolt_LowLine, I_HighVolt_Nominal, I_HighVolt_HighLine, 
                Desired_Current_Regulation_LowCurrent,Current_Regulation_LowCurrent,Status2])

        #Clear Status
        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Voltage(dict["ELoad"]).setOutputVoltage(0)
        WAI(dict["ELoad"])
        Voltage(dict["ACSource"]).setOutputVoltage(230)     # Maintain AC Source RUNNING
        WAI(dict["ACSource"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])

        return self.results

class ProgrammingResponse:
    def __init__(self):
        self.results= []
        pass
    
    def screenshot(self,dict,Image_Name):
        try:
            Oscilloscope(dict["OSC"]).displaydata()
            displayData= Oscilloscope(dict["OSC"]).read_binary_data()
            #print("Data retrieved successfully:", displayData)
        except VisaIOError as e:
            print(f"Timeout or communication error: {e}")
            raise

        if displayData.startswith(b"#"):
            header_length = int(displayData[1:2])  # Get header size length
            num_digits = int(displayData[2:2 + header_length])  # Extract data length
            displayData = displayData[2 + header_length:]  # Extract actual image data

        # Define save path with timestamp
        save_path = str(dict["savedir"])
        folder_path = os.path.join(save_path, f"ProgrammingSpeed_{self.current_time}")
        os.makedirs(folder_path, exist_ok = True)

        png_file = os.path.join(folder_path, f"{Image_Name}.png")

        # Save PNG file as binary
        with open(png_file, "wb") as file:
            file.write(displayData)
        print(f"Screenshot saved at: {png_file}")

    def No_Load_Test(self, dict, Vo, Vf):

        Image_NoLoad_Up = f"Rise_NoLoad_({Vo} to {Vf})"
        Image_NoLoad_Down = f"Fall_NoLoad_({Vf} to {Vo})"
        
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])
        sleep(2)

        Oscilloscope(dict["OSC"]).run()
        Oscilloscope(dict["OSC"]).setSingleMode()
        sleep(2)

        Voltage(dict["PSU"]).setOutputVoltage(Vf)
        WAI(dict["PSU"])
        sleep(5)

        Oscilloscope(dict["OSC"]).stop()
        Oscilloscope(dict["OSC"]).measureMode("MEAS")
        Oscilloscope(dict["OSC"]).setModeRiseTime("OSC_Channel")
        self.Risetime_no_load = float(Oscilloscope(dict["OSC"]).getRiseTime(dict["OSC_Channel"])) #10% to 90%
        self.screenshot(dict,Image_NoLoad_Up)
        sleep(5)

        Oscilloscope(dict["OSC"]).run()
        Oscilloscope(dict["OSC"]).setSingleMode()
        sleep(2)

        Voltage(dict["PSU"]).setOutputVoltage(Vo)
        WAI(dict["PSU"])
        sleep(5)

        Oscilloscope(dict["OSC"]).stop()
        Oscilloscope(dict["OSC"]).measureMode("MEAS")
        Oscilloscope(dict["OSC"]).setModeFallTime(dict["OSC_Channel"])
        self.Falltime_no_load = float(Oscilloscope(dict["OSC"]).getFallTime(dict["OSC_Channel"]))
        self.screenshot(dict,Image_NoLoad_Down)
        sleep(5)

    def Full_Load_Test(self, dict, Vo, Vf, FullLoad_I):

        Image_FullLoad_Up = f"Rise_FullLoad_({Vo} to {Vf})"
        Image_FullLoad_Down = f"Fall_FullLoad_({Vf} to {Vo})"

        Current(dict["ELoad"]).setOutputCurrent(FullLoad_I)
        WAI(dict["ELoad"])
        Output(dict["ELoad"]).setOutputState("ON")
        WAI(dict["ELoad"])
        sleep(2)

        Oscilloscope(dict["OSC"]).measureMode("MEAS")
        Oscilloscope(dict["OSC"]).run()
        Oscilloscope(dict["OSC"]).setSingleMode()
        sleep(2)

        Voltage(dict["PSU"]).setOutputVoltage(Vf)
        WAI(dict["PSU"])
        sleep(5)

        Oscilloscope(dict["OSC"]).stop()
        Oscilloscope(dict["OSC"]).setModeRiseTime(dict["OSC_Channel"])
        self.Risetime_fullload = float(Oscilloscope(dict["OSC"]).getRiseTime(dict["OSC_Channel"]))
        self.screenshot(dict,Image_FullLoad_Up)
        sleep(5)


        Oscilloscope(dict["OSC"]).run()
        Oscilloscope(dict["OSC"]).setSingleMode()
        sleep(2)
        
        Voltage(dict["PSU"]).setOutputVoltage(Vo)
        WAI(dict["PSU"])
        sleep(5)

        Oscilloscope(dict["OSC"]).stop()
        Oscilloscope(dict["OSC"]).setModeFallTime(dict["OSC_Channel"])
        self.Falltime_fullload= float(Oscilloscope(dict["OSC"]).getFallTime(dict["OSC_Channel"]))
        self.screenshot(dict,Image_FullLoad_Down)

    def execute(self, dict):
    
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
        ) = Dimport.getClasses(dict["Instrument"])

        ch = dict["PSU_Channel"]
        self.updatedelay = float(dict["updatedelay"])

        Desired_UP_Time_NoLoad = float(dict["Response_Up_NoLoad"])
        Desired_UP_Time_FullLoad = float(dict["Response_Up_FullLoad"])
        Desired_DOWN_Time_NoLoad = float(dict["Response_Down_NoLoad"])
        Desired_DOWN_Time_FullLoad = float(dict["Response_Down_FullLoad"])

        self.powerfin = int(dict["power"])          #power test
        self.Vf = float(dict["maxVoltage"])
        self.If = float(dict["maxCurrent"])
        self.Vo = 0
        self.Io = 0

        self.I_Max = round(self.powerfin / self.Vf, 2)       #Current based on Vmax and Power Test
        self.V_Max = round(self.powerfin / self.If, 2)

        self.MaxV_TriggerLevel = round(float((self.Vf - self.Vo)/2),1)
        self.MaxI_TriggerLevel = round(float((self.V_Max - self.Vo)/2),1)

        self.current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["OSC"])
        #OSC don't have WAI command

        sleep(3)
        sleep(self.updatedelay)

        #Initialization
        Oscilloscope(dict["OSC"]).setChannel_Display("1", dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setProbeAttenuation(dict["Probe_Setting"], dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelCoupling(dict["OSC_Channel"], "DC") #DC
        #Oscilloscope(dict["OSC"]).setChannelUnits(dict["OSC_Channel_Unit"], dict["OSC_Channel"])

        Oscilloscope(dict["OSC"]).setTriggerMode(dict["Trigger_Mode"])
        Oscilloscope(dict["OSC"]).setTriggerSource(dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.MaxV_TriggerLevel, dict["OSC_Channel"])

        Oscilloscope(dict["OSC"]).setTriggerHFReject(1)
        Oscilloscope(dict["OSC"]).setTriggerNoiseReject(1)
        #Oscilloscope(dict["OSC"]).on_displaycursor()
        Oscilloscope(dict["OSC"]).setTriggerSweepMode(dict["Trigger_SweepMode"])
        Oscilloscope(dict["OSC"]).setTriggerSlope(dict["Trigger_SlopeMode"])
        #Oscilloscope(dict["OSC"]).hardcopy("OFF")
        #Oscilloscope(dict["OSC"]).set_marker_Y1(0)
        Oscilloscope(dict["OSC"]).setTimeScale(dict["TimeScale"])
        Oscilloscope(dict["OSC"]).setVerticalScale(dict["VerticalScale"], dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelOffset(5, dict["OSC_Channel"])
        sleep(3)

        Voltage(dict["PSU"]).setSenseModeMultipleChannel("EXT", dict["PSU_Channel"])
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent("MAX")
        WAI(dict["PSU"])
        Function(dict["ELoad"]).setMode("CURR")

        #MAX Voltage (NoLoad-> Vinitial, VMaxfinal) (FullLoad -> Vinitial, VMaxFinal, Ifinal_calculated)
        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        self.No_Load_Test(dict, self.Vo, self.Vf)
        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        self.Full_Load_Test(dict, self.Vo, self.Vf, self.I_Max)

        Condition1 = "PASS" if self.Risetime_no_load < Desired_UP_Time_NoLoad else "FAIL"
        Condition2 = "PASS" if self.Risetime_fullload < Desired_UP_Time_FullLoad else "FAIL"
        Condition3 = "PASS" if self.Falltime_no_load < Desired_DOWN_Time_NoLoad else "FAIL"
        Condition4 = "PASS" if self.Falltime_fullload < Desired_DOWN_Time_FullLoad else "FAIL"

        self.results.append([ch, "MaxVoltage", "Up No Load",self.Vo, self.Vf, self.Io, 
                        self.Risetime_no_load, Desired_UP_Time_NoLoad, Condition1])
        self.results.append([ch, "MaxVoltage", "Up Full Load",self.Vo, self.Vf, self.I_Max, 
                        self.Risetime_fullload, Desired_UP_Time_FullLoad, Condition2])
        self.results.append([ch, "MaxVoltage", "Down No Load",self.Vo, self.Vf, self.Io, 
                        self.Falltime_no_load, Desired_DOWN_Time_NoLoad, Condition3])
        self.results.append([ch, "MaxVoltage", "Down Full Load",self.Vo, self.Vf, self.I_Max, 
                        self.Falltime_fullload, Desired_DOWN_Time_FullLoad, Condition4])

        sleep(2)

        #MAX Current (NoLoad-> Vinitial, Vfinal_calculated) (FullLoad -> Vinitial, Vfinal_calculated, IMaxFinal)
        VRange = abs(self.Vf - self.Vo)  
        available_scales = [1, 2, 5, 10]
        divisions = 9

        # Pick the smallest scale that still fits the range
        for scale in available_scales:
            if scale * divisions >= VRange:
                chosen_scale = scale
                break
        else:
            chosen_scale = max(available_scales)  # fallback if none fit (rare)

        # Only set if different from current setting
        if float(dict["VerticalScale"]) != chosen_scale:
            Oscilloscope(dict["OSC"]).setVerticalScale(chosen_scale, dict["OSC_Channel"])

        Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.MaxI_TriggerLevel, dict["OSC_Channel"])
        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        self.No_Load_Test(dict, self.Vo, self.V_Max)
        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        self.Full_Load_Test(dict, self.Vo, self.V_Max, self.If)
        
        Condition5 = "PASS" if self.Risetime_no_load < Desired_UP_Time_NoLoad else "FAIL"
        Condition6 = "PASS" if self.Risetime_fullload < Desired_UP_Time_FullLoad else "FAIL"
        Condition7 = "PASS" if self.Falltime_no_load < Desired_DOWN_Time_NoLoad else "FAIL"
        Condition8 = "PASS" if self.Falltime_fullload < Desired_DOWN_Time_FullLoad else "FAIL"

        self.results.append([ch, "MaxCurrent", "Up No Load", self.Vo, self.V_Max, self.Io, 
                        self.Risetime_no_load, Desired_UP_Time_NoLoad, Condition5])
        self.results.append([ch, "MaxCurrent", "Up Full Load",self.Vo, self.V_Max, self.If, 
                        self.Risetime_fullload, Desired_UP_Time_FullLoad, Condition6])
        self.results.append([ch, "MaxCurrent", "Down No Load",self.Vo, self.V_Max, self.Io, 
                        self.Falltime_no_load, Desired_DOWN_Time_NoLoad, Condition7])
        self.results.append([ch, "MaxCurrent", "Down Full Load",self.Vo, self.V_Max, self.If, 
                        self.Falltime_fullload, Desired_DOWN_Time_FullLoad, Condition8])

        sleep(2)

        #Clear Status
        Voltage(dict["PSU"]).setOutputVoltage(0)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(0)
        WAI(dict["PSU"])
        Voltage(dict["ELoad"]).setOutputVoltage(0)
        WAI(dict["ELoad"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])

        #Voltage(dict["ACSource"]).setOutputVoltage(230)     # Maintain AC Source RUNNING
        #WAI(dict["ACSource"])
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])

        print(self.results)

        return self.results, self.current_time

class OVP_Test:
    def __init__(self):
        self.results = []

    def Execute_OVP(self,dict):
        """Execution of OVP Test Program"""
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
        ) = Dimport.getClasses(dict["Instrument"])

        # Instrument Initialization (E-load was not used in this test)
        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])    
        sleep(3)

        #Channel Loop (For usage of All Channels)
        Channel_Loop = dict["PSU_Channel"]
        self.updatedelay = float(dict["updatedelay"])

        #Error Gain
        self.OVP_Gain = float(dict["OVP_ErrorGain"])
        self.OVP_Offset = float(dict["OVP_ErrorOffset"])

        #Use ch for each individual channel (It works in one channel, bcuz channel_loop is str, for ch in "2"--> ch will be 2)
        #for ch in [list] is better usage
        for ch in Channel_Loop: 
            print(f"Channel {ch} Test Running\n")
            print("")
            # Instrument Initialization
            Function(dict["ELoad"]).setMode(dict["setFunction"])
            Function(dict["PSU"]).setMode("Voltage")

            #Instrument Channel Set
            Voltage(dict["PSU"]).setInstrumentChannel(ch)
            Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])

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

            #Set Current and Sense Mode
            Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
            Current(dict["PSU"]).setOutputCurrent("MAX")
            WAI(dict["PSU"])
            Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])
            WAI(dict["ELoad"])

            #Set OVP Percentage
            Percentages = [0.25,0.5,1.0]
            print(f"Type of OVP_Level: {type(dict['OVP_Level'])}")
            print(f"Type of Percentages: {type(Percentages)}")

            try:
                for percentage in Percentages:
                    OVP_Level = float(dict["OVP_Level"]) * percentage

                    #Set Initial Voltage (110% and 90% of OVP Level)
                    OVP_VMax =  OVP_Level * 1.1
                    OVP_VMin = OVP_Level  * 0.9
                    Voltage(dict["PSU"]).setTripVoltage(OVP_Level , ch)
                    WAI(dict["PSU"])
                    Voltage(dict["PSU"]).setOutputVoltage(OVP_VMin)
                    WAI(dict["PSU"])

                    #Set Limit Boundary
                    Upper_Limit = round((OVP_Level * self.OVP_Gain) + self.OVP_Offset , 3)
                    Lower_Limit = round(-(OVP_Level * self.OVP_Gain) - self.OVP_Offset, 3)

                    #Triggering OVP Steps
                    V_deltaMin = 0.01
                    V_delta = OVP_VMax -  OVP_Level
                    V_set = OVP_VMin
                    Output(dict["PSU"]).setOutputState("ON")
                    WAI(dict["PSU"])

                    print(V_delta)
                    print(V_deltaMin)
                    prev_stat = None

                    while (V_delta > V_deltaMin):

                        # Limit V_set not exceed V_Ratings (Max Ratings)
                        if V_set > OVP_Level:
                            V_set = OVP_Level

                        Voltage(dict["PSU"]).setOutputVoltage(V_set)
                        sleep(1)
                        WAI(dict["PSU"]) 
                        Output(dict["PSU"]).setOutputState("ON")    
                        sleep(0.2)
                        sleep(self.updatedelay)
                        Vreadback = Measure(dict["PSU"]).multipleChannelQuery(ch,"VOLT")
                        print(f"Vreadback: {Vreadback}")
                        sleep(2)  

                        # Check OVP State
                        stat = int(Voltage(dict["PSU"]).setTripVoltageQuery(ch))
                        sleep(2)
                        print(stat)

                        # Dolphin (0-OFF, 1-Tripped)
                        if stat == 1:
                            print("CC/OVP Mode")

                            Output(dict["PSU"]).setOutputState("OFF")
                            WAI(dict["PSU"])
                            Voltage(dict["PSU"]).CLEVoltageProtection(ch)
                            WAI(dict["PSU"])

                            if prev_stat == 1:
                                V_delta *= 0.9
                                V_set -= V_delta
                            elif prev_stat == 0 or prev_stat == None:
                                V_delta *= 0.5
                                V_set -= V_delta

                            prev_stat == stat
                            Last_OVP_Reading = V_set

                        elif stat == 0:
                            print("CV Mode")

                            Output(dict["PSU"]).setOutputState("OFF")
                            WAI(dict["PSU"])
                            Voltage(dict["PSU"]).CLEVoltageProtection(ch)
                            WAI(dict["PSU"])

                            if prev_stat == 0  or prev_stat == None:
                                V_delta *= 0.9
                                V_set += V_delta
                            elif prev_stat == 1:
                                V_delta *= 0.5
                                V_set += V_delta

                            prev_stat == stat
                            Last_OVP_Reading = V_set

                        else:
                            print("Output OFF")

                            Output(dict["PSU"]).setOutputState("OFF")
                            WAI(dict["PSU"])
                            Voltage(dict["PSU"]).CLEVoltageProtection(ch)
                            WAI(dict["PSU"])

                    PSU_Channel = int(Voltage(dict["PSU"]).setInstrumentChannelQuery())
                    print(f"PSU Channel: {PSU_Channel}")
                    sleep(1)

                    #Append result in array for each voltage level
                    result = Last_OVP_Reading -  OVP_Level
                    
                    if result < Upper_Limit and result > Lower_Limit:
                        Condition = "PASS"
                    else:
                        Condition = "FAIL"

                    self.results.append([PSU_Channel,f"{percentage * 100}%", OVP_Level, \
                                         Last_OVP_Reading, Lower_Limit, result, Upper_Limit,Condition])

                Voltage(dict["PSU"]).setOutputVoltage(0)
                Voltage(dict["PSU"]).CLEVoltageProtection(ch)
                Output(dict["PSU"]).SPModeConnection("OFF")
                WAI(dict["PSU"])
                print(f"result: {self.results}")
                print(f"Last Volt: {Last_OVP_Reading}")
                sleep(3)
            except:
                error_message = traceback.format_exc()  # Get the full error traceback
                print(error_message)

        return self.results

class OCP_Accuracy:
    def __init__(self):
        self.results = []

    def Execute_OCP(self,dict):
        """Execution of OCP Test Program"""
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
        ) = Dimport.getClasses(dict["Instrument"])

        # Instrument Initialization (E-load was not used in this test)
        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])    
        sleep(3)

        self.V_Rating = float(dict["V_Rating"])
        self.I_Rating = float(dict["I_Rating"])
        self.P_Rating = float(dict["P_Rating"])

        self.powerfin = int(dict["power"])
        self.voltagemax = float(dict["maxVoltage"])
        self.currentmax = float(dict["maxCurrent"])
        self.OCP_Level = float(dict["OCP_Level"])
        self.delaytime = 5
        #self.OCP_Gain = float(dict["OVP_ErrorGain"])
        #self.OCP_Offset = float(dict["OVP_ErrorOffset"])

        #Channel Loop (For usage of All Channels)
        Channel_Loop = dict["PSU_Channel"]
        self.updatedelay = float(dict["updatedelay"])

        for ch in Channel_Loop: 
            print(f"Channel {ch} OCP Test Running\n")
            print("")

            # Instrument Initialization
            Function(dict["ELoad"]).setMode("CURR")

            #Instrument Channel Set
            Voltage(dict["PSU"]).setInstrumentChannel(ch)
            Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])

            Current(dict["PSU"]).CLECurrentProtection(ch)
            WAI(dict["PSU"])
            Current(dict["PSU"]).enableCurrentProtection("ON", ch)
            WAI(dict["PSU"])
            Current(dict["PSU"]).setDelayStartCondition("CCTR", ch)
            WAI(dict["PSU"])

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

            #Set Current and Sense Mode
            Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
            WAI(dict["PSU"])
            Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])
            WAI(dict["ELoad"])


            #Set OVP Percentage
            Percentages = [0.25, 0.5, 1]
            print(f"Type of OCP_Level: {type(dict['OCP_Level'])}")
            print(f"Type of Percentages: {type(Percentages)}")

            try:
                #Run OCP Accuracy First
                for percentage in Percentages:
                    Current_OCP_Level = float(dict["OCP_Level"]) * percentage
                    Current_Voltage = self.powerfin / Current_OCP_Level

                    #Set Initial Voltage (110% and 90% of OCP Level)
                    OCP_IMax =  Current_OCP_Level * 1.1
                    OCP_IMin = Current_OCP_Level  * 0.9

                    #Set Limit Boundary
                    #Upper_Limit = round((OCP_Level * self.OCP_Gain) + self.OCP_Offset , 3)
                    #Lower_Limit = round(-(OCP_Level * self.OCP_Gain) - self.OCP_Offset, 3)

                    #Triggering OCP Steps
                    I_deltaMin = 0.01
                    I_delta = OCP_IMax -  Current_OCP_Level
                    I_set = OCP_IMin
                    Output(dict["PSU"]).setOutputState("ON")
                    WAI(dict["PSU"])

                    prev_stat = None


                    while (I_delta > I_deltaMin):

                        #Check Vset based on power 
                        if Current_Voltage >= self.voltagemax:            
                            Voltage(dict["PSU"]).setOutputVoltage(self.voltagemax)
                            WAI(dict["PSU"]) 
                        elif Current_Voltage <self.voltagemax:
                            Voltage(dict["PSU"]).setOutputVoltage(Current_Voltage)
                            WAI(dict["PSU"]) 
                        else:
                            pass

                        # Limit I_set not Max I Ratings
                        if I_set >= self.OCP_Level:
                            Current(dict["PSU"]).setOutputCurrent("MAX")
                            WAI(dict["PSU"]) 
                        elif I_set < self.OCP_Level:
                            Current(dict["PSU"]).setOutputCurrent(I_set)
                            WAI(dict["PSU"]) 
                        else:
                            pass
                        
                        Current(dict["ELoad"]).setOutputCurrent(Current_OCP_Level)
                        WAI(dict["ELoad"])
                        Output(dict["PSU"]).setOutputState("ON")    
                        WAI(dict["PSU"])
                        sleep(1)
                        Output(dict["ELoad"]).setOutputState("ON")  
                        WAI(dict["ELoad"])
                        sleep(1)
                        sleep(self.updatedelay)
                        #Ireadback = Measure(dict["PSU"]).multipleChannelQuery(ch,"CURR")
                        #print(f"Ireadback: {Ireadback}")
                        sleep(2)  

                        # Check OCP State
                        stat = int(Current(dict["PSU"]).setTripCurrentQuery(ch))
                        sleep(2)
                        print(stat)

                        # Dolphin (0-OFF, 1-Tripped)
                        if stat == 0:

                            print("CV Mode")

                            Output(dict["PSU"]).setOutputState("OFF")
                            WAI(dict["PSU"])
                            Current(dict["PSU"]).CLECurrentProtection(ch)
                            WAI(dict["PSU"])
                            Output(dict["ELoad"]).setOutputState("OFF")  
                            WAI(dict["ELoad"])

                            if prev_stat == 1:
                                I_delta *= 0.9
                                I_set -= I_delta
                            elif prev_stat == 0 or prev_stat == None:
                                I_delta *= 0.5
                                I_set -= I_delta

                            prev_stat == stat
                            Last_OCP_Reading = I_set

                        elif stat == 1:

                            print("CC/OCP Mode")
                            
                            Output(dict["PSU"]).setOutputState("OFF")
                            WAI(dict["PSU"])
                            Current(dict["PSU"]).CLECurrentProtection(ch)
                            WAI(dict["PSU"])
                            Output(dict["ELoad"]).setOutputState("OFF")  
                            WAI(dict["ELoad"])
        
                            if prev_stat == 0  or prev_stat == None:
                                I_delta *= 0.9
                                I_set += I_delta
                            elif prev_stat == 1:
                                I_delta *= 0.5
                                I_set += I_delta

                            prev_stat == stat
                            Last_OCP_Reading = I_set

                        else:
                            print("Output OFF")

                            Output(dict["PSU"]).setOutputState("OFF")
                            WAI(dict["PSU"])
                            Current(dict["PSU"]).CLECurrentProtection(ch)
                            WAI(dict["PSU"])

                    PSU_Channel = int(Voltage(dict["PSU"]).setInstrumentChannelQuery())
                    print(f"PSU Channel: {PSU_Channel}")
                    sleep(1)

                    #Append result in array for each voltage level
                    result = Last_OCP_Reading -  Current_OCP_Level

                    self.results.append([PSU_Channel,f"{percentage * 100}%", Current_OCP_Level, \
                                        Last_OCP_Reading, result])
                
                Voltage(dict["PSU"]).setOutputVoltage(0)
                Current(dict["PSU"]).setOutputCurrent(0)
                Current(dict["PSU"]).CLECurrentProtection(ch)
                Current(dict["PSU"]).enableCurrentProtection("OFF", ch)
                Output(dict["PSU"]).SPModeConnection("OFF")

                Output(dict["PSU"]).setOutputState("OFF")
                WAI(dict["PSU"])
                Output(dict["ELoad"]).setOutputState("OFF")  
                WAI(dict["ELoad"])  
                WAI(dict["PSU"])
                sleep(3)

            except:
                error_message = traceback.format_exc()  # Get the full error traceback
                print(error_message)

        return self.results

    """
    #Continue with Activation Time
    for i in range(1):
        PSU_Current = 1
        PSU_Current_Lower = 1-0.1

        Voltage(dict["PSU"]).setOutputVoltage(self.voltagemax)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setOutputCurrent(PSU_Current)
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(self.OCP_Level)
        WAI(dict["ELoad"])

        Current(dict["PSU"]).CLECurrentProtection(ch)
        WAI(dict["PSU"])
        Current(dict["PSU"]).enableCurrentProtection("ON", ch)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setDelayStartCondition("CCTR", ch)
        WAI(dict["PSU"])
        Current(dict["PSU"]).setCurrentProtectionDelay(self.delaytime , ch)
        WAI(dict["PSU"])
        sleep(1)

        Output(dict["PSU"]).setOutputState("ON")
        WAI(dict["PSU"])


        Output(dict["ELoad"]).setOutputState("ON")  
        WAI(dict["ELoad"])  
        Initial_time = time.perf_counter()
        print(Initial_time)
        trigger_time = Initial_time + self.delaytime
        print(trigger_time)
        sleep(self.delaytime+0.01)

        if time.perf_counter() >= trigger_time:
            stat = int(Current(dict["PSU"]).setTripCurrentQuery(ch))

            if stat == 1:
                OCP_delay_time = time.perf_counter()
                print("OCP Detected")

            else:
                OCP_delay_time = 0
                print("OCP Not Detected")
                pass
        else:
                OCP_delay_time = 0
                print("Initial Time Not rEach")
                pass

        sleep(3)
        Voltage(dict["PSU"]).setOutputVoltage(0)
        Current(dict["PSU"]).setOutputCurrent(0)
        Current(dict["PSU"]).CLECurrentProtection(ch)
        Current(dict["PSU"]).enableCurrentProtection("OFF", ch)
        Output(dict["PSU"]).SPModeConnection("OFF")

        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")  
        WAI(dict["ELoad"])  
        WAI(dict["PSU"])

        Time_Limit =  float(dict["OCPActivationTime"])
        print(Time_Limit)
        Elapsed_delay_time = OCP_delay_time - Initial_time
        print(Elapsed_delay_time)
        #Elapsed_activation_time = Activation_Time - Initial_time
        #print(Elapsed_activation_time)
                
        #Activation_Time_error = Elapsed_activation_time - Elapsed_delay_time

        #if Activation_Time_error < Time_Limit:
            #Condition = "PASS"
        # else:
            #Condition = "FAIL"
        self.results2.append([1, self.delaytime, Initial_time, OCP_delay_time ,\
                            Elapsed_delay_time,  \
                                Time_Limit,])
        
        sleep(3)
        """

class OCP_Activation_Time:
    def __init__(self):
        self.results = []

    def screenshot(self,dict):
        self.current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        try:
            Oscilloscope(dict["OSC"]).displaydata()
            displayData= Oscilloscope(dict["OSC"]).read_binary_data()
            #print("Data retrieved successfully:", displayData)
        except VisaIOError as e:
            print(f"Timeout or communication error: {e}")
            raise

        if displayData.startswith(b"#"):
            header_length = int(displayData[1:2])  # Get header size length
            num_digits = int(displayData[2:2 + header_length])  # Extract data length
            displayData = displayData[2 + header_length:]  # Extract actual image data

        # Define save path with timestamp
        save_path = str(dict["savedir"])
        folder_path = os.path.join(save_path, f"OCPActivationTime_{self.current_time}")
        os.makedirs(folder_path, exist_ok = True)

        existing_images = [
            f for f in os.listdir(folder_path)
            if f.startswith("OCP_img") and f.endswith(".png") and f[3:-4].isdigit()
        ]

        next_number = len(existing_images) + 1  # start from 1

        filename = f"OCP_img{next_number}.png"
        png_file = os.path.join(folder_path, filename)

        # Save PNG file as binary
        with open(png_file, "wb") as file:
            file.write(displayData)
        print(f"Screenshot saved at: {png_file}")

    def Execute_OCP(self,dict):
        """Execution of OCP Test Program"""
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
        ) = Dimport.getClasses(dict["Instrument"])

        # Instrument Initialization (E-load was not used in this test)
        RST(dict["PSU"])
        WAI(dict["PSU"])
        RST(dict["ELoad"])
        WAI(dict["ELoad"])    
        RST(dict["OSC"])
        sleep(3)

        self.V_Rating = float(dict["V_Rating"])
        self.I_Rating = float(dict["I_Rating"])
        self.P_Rating = float(dict["P_Rating"])

        self.powerfin = int(dict["power"])
        self.voltagemax = float(dict["maxVoltage"])
        self.currentmax = float(dict["maxCurrent"])

        #OCP Data 
        self.OCP_Level = float(dict["OCP_Level"])
        self.PSU_Current = self.OCP_Level -1
        self.delaytime = 10
        self.PSU_Vset = self.powerfin/self.PSU_Current
        Time_Limit =  float(dict["OCPActivationTime"])
        #self.OCP_Gain = float(dict["OVP_ErrorGain"])
        #self.OCP_Offset = float(dict["OVP_ErrorOffset"])

        #Channel Loop (For usage of All Channels)
        Channel_Loop = dict["PSU_Channel"]
        self.updatedelay = float(dict["updatedelay"])

        self.OCP_TriggerLevel = round(float((self.OCP_Level)/2),1)
        
        #Initialization of OSC
        Oscilloscope(dict["OSC"]).setChannel_Display("1", dict["OSC_Channel"])

        if dict["OSC_Channel"] != "1":
            Oscilloscope(dict["OSC"]).setChannel_Display("0", "1")
        else:
            pass

        Oscilloscope(dict["OSC"]).setChannelUnits("AMP", dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setProbeAttenuation(dict["Probe_Setting"], dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelCoupling(dict["OSC_Channel"], "DC") #DC

        Oscilloscope(dict["OSC"]).setTriggerMode(dict["Trigger_Mode"])
        Oscilloscope(dict["OSC"]).setTriggerSource(dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setTriggerEdgeLevel(self.OCP_TriggerLevel, dict["OSC_Channel"])

        Oscilloscope(dict["OSC"]).setTriggerHFReject(1)
        Oscilloscope(dict["OSC"]).setTriggerNoiseReject(1)
        Oscilloscope(dict["OSC"]).setTriggerSweepMode(dict["Trigger_SweepMode"])
        Oscilloscope(dict["OSC"]).setTriggerSlope(dict["Trigger_SlopeMode"])
        Oscilloscope(dict["OSC"]).setTimeScale(dict["TimeScale"])
        Oscilloscope(dict["OSC"]).setVerticalScale(dict["VerticalScale"], dict["OSC_Channel"])
        Oscilloscope(dict["OSC"]).setChannelOffset(5,dict["OSC_Channel"])
        sleep(3)
        try:
            for ch in Channel_Loop: 
                print(f"Channel {ch} OCP Test Running\n")
                print("")

                # Instrument Initialization
                Function(dict["ELoad"]).setMode("CURR")

                #Instrument Channel Set
                Voltage(dict["PSU"]).setInstrumentChannel(ch)
                Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])

                Current(dict["PSU"]).CLECurrentProtection(ch)
                WAI(dict["PSU"])
                Current(dict["PSU"]).enableCurrentProtection("ON", ch)
                WAI(dict["PSU"])
                Current(dict["PSU"]).setDelayStartCondition("CCTR", ch)
                WAI(dict["PSU"])

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

                #Set Current and Sense Mode
                Voltage(dict["PSU"]).setSenseModeMultipleChannel(dict["VoltageSense"], ch)
                WAI(dict["PSU"])
                Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])
                WAI(dict["ELoad"])

                #Set Current/Voltage
                Voltage(dict["PSU"]).setOutputVoltage(self.PSU_Vset)
                WAI(dict["PSU"])
                Current(dict["PSU"]).setOutputCurrent(self.PSU_Current)
                WAI(dict["PSU"])
                Current(dict["ELoad"]).setOutputCurrent(self.OCP_Level)
                WAI(dict["ELoad"])

                #Set OCP Protection
                Current(dict["PSU"]).CLECurrentProtection(ch)
                WAI(dict["PSU"])
                Current(dict["PSU"]).enableCurrentProtection("ON", ch)
                WAI(dict["PSU"])
                Current(dict["PSU"]).setDelayStartCondition("CCTR", ch)
                WAI(dict["PSU"])
                Current(dict["PSU"]).setCurrentProtectionDelay(self.delaytime , ch)
                WAI(dict["PSU"])
                sleep(1)

                Output(dict["PSU"]).setOutputState("ON")
                WAI(dict["PSU"])
                sleep(2)
                Output(dict["ELoad"]).setOutputState("ON")  
                WAI(dict["ELoad"])  
                sleep(1)
                Oscilloscope(dict["OSC"]).run()
                Oscilloscope(dict["OSC"]).setSingleMode()
                sleep(self.delaytime - 1)

                while True:
                    stat = int(Current(dict["PSU"]).setTripCurrentQuery(ch))

                    if stat == 1:     
                        Oscilloscope(dict["OSC"]).stop()
                        Oscilloscope(dict["OSC"]).measureMode("MEAS")
                        Oscilloscope(dict["OSC"]).setModeFallTime(dict["OSC_Channel"])
                        self.FallActivationtime= float(Oscilloscope(dict["OSC"]).getFallTime(dict["OSC_Channel"]))
                        sleep(2)
                        self.screenshot(dict)
                        sleep(2)
                        break
                    else:
                        print("Error detecting OCP")
                        pass

                sleep(3)
                Voltage(dict["PSU"]).setOutputVoltage(0)
                Current(dict["PSU"]).setOutputCurrent(0)
                Current(dict["PSU"]).CLECurrentProtection(ch)
                Current(dict["PSU"]).enableCurrentProtection("OFF", ch)
                Output(dict["PSU"]).SPModeConnection("OFF")

                Output(dict["PSU"]).setOutputState("OFF")
                WAI(dict["PSU"])
                Output(dict["ELoad"]).setOutputState("OFF")  
                WAI(dict["ELoad"])  
                WAI(dict["PSU"])
                sleep(3)
                
                if self.FallActivationtime < Time_Limit:
                    Condition = "PASS"
                else:
                    Condition = "FAIL"

                self.results.append([ch, self.delaytime, self.PSU_Vset, self.OCP_Level,\
                                    self.FallActivationtime, Time_Limit, Condition])
                
        except:
            error_message = traceback.format_exc()  # Get the full error traceback
            print(error_message)

        return self.results

class ActivateAC:
    def __init__(self):
        self.results= []
        pass

    def PowerStart(self, dict):

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
        ) = Dimport.getClasses(dict["Instrument"])

        try:
            #Supply_Type = dict(["AC_Supply_Type"])
            CurrentLimit = dict["AC_CurrentLimit"]
            VoltageOutput = dict["AC_VoltageOutput"]
            FrequencySet = dict["Frequency"]

            #if Supply_Type == "AC Source":
            #RST(dict["ACSource"])
            #WAI(dict["ACSource"])
            CLS(dict["ACSource"])
            WAI(dict["ACSource"])

            #Initialize AC Source
            Voltage(dict["ACSource"]).setACTripVoltage(368)
            WAI(dict["ACSource"])
            Current(dict["ACSource"]).setOutputCurrent(CurrentLimit)
            WAI(dict["ACSource"])
            Voltage(dict["ACSource"]).setOutputVoltage(VoltageOutput)
            WAI(dict["ACSource"])
            Frequency(dict["ACSource"]).setOutputFrequency(FrequencySet)
            WAI(dict["ACSource"])
            Output(dict["ACSource"]).setOutputState("ON")

            print("AC Turned ON\n")
            print(f"Current Limit: {CurrentLimit} A")
            print(f"AC Output Voltage: {VoltageOutput} V")
            print(f"Frequency: {FrequencySet} Hz")

           # elif Supply_Type == "Plug":
                #print("External AC Not Connected for Test\n")
            
            #else:
               # print("Couldn't identify\n")
                #return

        except:
            error_message = traceback.format_exc()  # Get the full error traceback
            print(error_message)

class RESET:
    def __init__(self):
        pass

    def ResetInstrument(self,dict_reset):

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
        ) = Dimport.getClasses(dict_reset["Instrument"])

        try:

            instruments = ["ACSource", "ELoad", "PSU", "DMM", "OSC", "DMM2"]

            # CLS/WAI
            for name in instruments:
                if name in dict_reset:  # check if the instrument exists
                    CLS(dict_reset[name])
                    WAI(dict_reset[name])
                    RST(dict_reset[name])
                    WAI(dict_reset[name])

            Voltage(dict_reset["PSU"]).setOutputVoltage(0)
            WAI(dict_reset["PSU"])
            Current(dict_reset["PSU"]).setOutputCurrent(0)
            WAI(dict_reset["PSU"])
            Voltage(dict_reset["ELoad"]).setOutputVoltage(0)
            WAI(dict_reset["ELoad"])
            Output(dict_reset["PSU"]).setOutputState("OFF")
            WAI(dict_reset["PSU"])
            Output(dict_reset["ELoad"]).setOutputState("OFF")
            WAI(dict_reset["ELoad"])
            Output(dict_reset["PSU"]).SPModeConnection("OFF")
            WAI(dict_reset["PSU"])

            print("reset")
        except:
            pass