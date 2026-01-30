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
class EDU36311AVoltageMeasurementNoELoad:

    def __init__(self):
        self.results = []
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    def Execute_Voltage_Accuracy(self,dict,channel):
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
            Hornbill,
        ) = Dimport.getClasses(dict["Instrument"])

        RST(dict["PSU"])
        WAI(dict["PSU"])
        """RST(dict["ELoad"])
        WAI(dict["ELoad"])"""
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
        """Function(dict["ELoad"]).setMode(dict["setFunction"])"""
        Function(dict["PSU"]).setMode("Voltage")

        #Instrument Channel Set
        Voltage(dict["PSU"]).setInstrumentChannel(ch)
        """Voltage(dict["ELoad"]).setInstrumentChannel(dict["ELoad_Channel"])"""
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
        """Voltage(dict["ELoad"]).setSenseModeMultipleChannel(dict["VoltageSense"], dict["ELoad_Channel"])"""

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
        """Output(dict["ELoad"]).setOutputState("ON")
        WAI(dict["ELoad"])"""

        #Clear the Error Status
        CLS(dict["PSU"])
        WAI(dict["PSU"])
        """CLS(dict["ELoad"])
        WAI(dict["ELoad"])"""
        CLS(dict["DMM"])
        WAI(dict["DMM"])
        
        #Run Test (Voltage Loop in Current Loop)
        while i < current_iter:
            j = 0
            V = float(dict["minVoltage"])
            Iset = float(Current(dict["PSU"]).SourceCurrentLevel()) #Query Current Level

            if I_fixed > float(dict["maxCurrent"]):
                I_fixed= float(dict["maxCurrent"])

            #If minimum current is 0, set to 1A
            if I_fixed == 0:           
                I_fixedOS = 1
                I_fixed = I_fixed + I_fixedOS

            #If PSU MAX I = ELOAD MAX I (Reduce Eload I by 0.1 - Prevent Overload)
            if I_fixed == float(dict["maxCurrent"]) and Iset == float(dict["maxCurrent"]):
                """Current(dict["ELoad"]).setOutputCurrent(I_fixed - 0.1)
                WAI(dict["ELoad"])"""
            else:
                """Current(dict["ELoad"]).setOutputCurrent(I_fixed)
                WAI(dict["ELoad"])"""

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
                temp_values = Measure(dict["PSU"]).multipleChannelQuery(ch,"VOLT")
                WAI(dict["PSU"])
                temp_values2 = Measure(dict["PSU"]).multipleChannelQuery(ch,"CURR")
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
        """Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])"""
        Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])
        Output(dict["PSU"]).setOutputState("OFF")
        WAI(dict["PSU"])
        """Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])"""
        RST(dict["DMM"])
        WAI(dict["DMM"])

        return self.infoList, self.dataList, self.dataList2
