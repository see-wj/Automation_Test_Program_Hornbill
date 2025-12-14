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
        Hornbill = getattr(module, "Hornbill")

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
            Hornbill,
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
class HornbillVoltageMeasurementwithELoad:

    def __init__(self):
        self.results = []
        self.infoList = []
        self.dataList = []
        self.dataList2 = []

    def Execute_Voltage_Accuracy_Current_Static(self,dict,channel):
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

      
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])
        RST(dict["PSU"])
        WAI(dict["PSU"])

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")
        #offset
        sleep(3)

        # Instrument Initialization
        Configure(dict["DMM"]).write("Voltage")
        Trigger(dict["DMM"]).setSource("BUS")
        Sense(dict["DMM"]).setVoltageResDC(dict["VoltageRes"])
        Function(dict["ELoad"]).setMode("Current")
        Function(dict["PSU"]).setMode("Voltage")

        #Instrument Channel Set
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
        psu.sourCurrentLimitPOS("MAXimum", ch)
        WAI(dict["PSU"])
        
        #Turn On the PSU and Eload
        psu.outputState("ON", ch)
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
            psu.sourVoltageLevelImmediateAmplitude(float(dict["minVoltage"]), ch)
            sleep(3)
            Iset = dict["maxCurrent"]
            #Iset = float(psu.askSourCurrentLimitPOSImmediateAmplitude("MAX", ch)) #Query Current Level
            #Iset = float(psu.askSourCurrentLimitPOSImmediateAmplitude("MAX", ch)) #Query Current Level
            sleep(2)
            WAI(dict["PSU"])

            if I_fixed > float(dict["maxCurrent"]):
                I_fixed= float(dict["maxCurrent"])

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
                psu.sourVoltageLevelImmediateAmplitude(V, ch)
                WAI(dict["PSU"])
                self.infoList.insert(k, [V, I_fixed, i])

                #Timeout/Delay-----------------------------------------?
                #Delay(dict["PSU"]).write(dict["UpTime"])
                #WAI(dict["PSU"])
                sleep(0.2)
                sleep(float(self.updatedelay))

                #Readback Voltage and Current
                #temp_values = psu.measureVoltageDC(ch)
                diagVmon_raw = psu.diagVoltageReadback_VMON_100k()
                sleep(1)
                # Decode from bytes to string
                diagVmon_str = diagVmon_raw.decode().strip()
                print("Raw Response:", diagVmon_str)

                # Split into components
                values = diagVmon_str.split(',')
                cleandiagVmon = float(values[0])

                print("Voltage Monitor Reading =", cleandiagVmon)
                WAI(dict["PSU"])

                #temp_values2 = psu.measureCurrentDC(ch)
                diagImon_raw = psu.diagCurrentReadback_IMON_FULL_100k()
                sleep(1)
                # Decode from bytes to string
                diagImon_str = diagImon_raw.decode().strip()
                print("Raw Response:", diagImon_str)

                # Split into components
                diagImon_values = diagImon_str.split(',')
                cleandiagImon = float(diagImon_values[0])
                print("Current Monitor Reading =", cleandiagImon)
                WAI(dict["PSU"])

                sleep(1)
                #self.dataList2.insert(k, [float(temp_values), float(temp_values2)])
                self.dataList2.insert(k, [float(cleandiagVmon), float(cleandiagImon)])
                
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


        psu.sourVoltageLevelImmediateAmplitude(0, ch)
        WAI(dict["PSU"])
        psu.sourCurrentLimitPOS("MIN", ch)
        WAI(dict["PSU"])
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        """Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])"""
        psu.outputState("OFF", ch)
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])

        return self.infoList, self.dataList, self.dataList2
    
    def Execute_Voltage_Accuracy_Current_Change(self,dict,channel):
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

      
        RST(dict["ELoad"])
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])
        RST(dict["PSU"])
        WAI(dict["PSU"])

        #Channel Loop (For usage of All Channels, the channel is taken from Execute Function in GUI.py)
        ch = channel

        #Use ch for each individual channel
        print(f"Channel {ch} Test Running\n")
        print("")
        #offset
        sleep(3)

        # Instrument Initialization
        Configure(dict["DMM"]).write("Voltage")
        Trigger(dict["DMM"]).setSource("BUS")
        Sense(dict["DMM"]).setVoltageResDC(dict["VoltageRes"])
        Function(dict["ELoad"]).setMode("Current")
        Function(dict["PSU"]).setMode("Voltage")

        #Instrument Channel Set
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
        psu.sourCurrentLimitPOS("MAXimum", ch)
        WAI(dict["PSU"])
        
        #Turn On the PSU and Eload
        psu.outputState("ON", ch)
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
        
        
        j = 0
        V = float(dict["minVoltage"])
        #Voltage Iteration
        while j < voltage_iter:
            i=0
            I_fixed = float(dict["minCurrent"])
            Current(dict["ELoad"]).setOutputCurrent(I_fixed)

            WAI(dict["ELoad"])
            #Set Voltage and Current
            if V > float(dict["maxVoltage"]):
                V = float(dict["maxVoltage"])
            psu.sourVoltageLevelImmediateAmplitude(V, ch)
            WAI(dict["PSU"])
            self.infoList.insert(k, [V, I_fixed, i])

            #Timeout/Delay-----------------------------------------?
            #Delay(dict["PSU"]).write(dict["UpTime"])
            #WAI(dict["PSU"])
            sleep(0.2)
            sleep(float(self.updatedelay))

            #Readback Voltage and Current
            #temp_values = psu.measureVoltageDC(ch)
            diagVmon_raw = psu.diagVoltageReadback_VMON_100k()
            sleep(1)
            # Decode from bytes to string
            diagVmon_str = diagVmon_raw.decode().strip()
            print("Raw Response:", diagVmon_str)

            # Split into components
            values = diagVmon_str.split(',')
            cleandiagVmon = float(values[0])

            print("Voltage Monitor Reading =", cleandiagVmon)
            WAI(dict["PSU"])

            #temp_values2 = psu.measureCurrentDC(ch)
            diagImon_raw = psu.diagCurrentReadback_IMON_FULL_100k()
            sleep(1)
            # Decode from bytes to string
            diagImon_str = diagImon_raw.decode().strip()
            print("Raw Response:", diagImon_str)

            # Split into components
            diagImon_values = diagImon_str.split(',')
            cleandiagImon = float(diagImon_values[0])
            print("Current Monitor Reading =", cleandiagImon)
            WAI(dict["PSU"])

            sleep(1)
            #self.dataList2.insert(k, [float(temp_values), float(temp_values2)])
            self.dataList2.insert(k, [float(cleandiagVmon), float(cleandiagImon)])
            
            #INIT DMM (Trigger Measurement)
            Initiate(dict["DMM"]).initiate()
            status = float(Status(dict["DMM"]).operationCondition())
            sleep(1)
            #print(status)
            TRG(dict["DMM"])
            #Run Test (Voltage Loop in Current Loop)
            
            while i < current_iter:
                Iset = dict["maxCurrent"]
                #Iset = float(psu.askSourCurrentLimitPOSImmediateAmplitude("MAX", ch)) #Query Current Level
                #Iset = float(psu.askSourCurrentLimitPOSImmediateAmplitude("MAX", ch)) #Query Current Level
                sleep(2)
                WAI(dict["PSU"])

                if I_fixed > float(dict["maxCurrent"]):
                    I_fixed= float(dict["maxCurrent"])

                #If minimum current is 0, set to 1A
                if I_fixed == 0:           
                    I_fixedOS = 1
                    I_fixed = I_fixed + I_fixedOS

                #If PSU MAX I = ELOAD MAX I (Reduce Eload I by 0.1 - Prevent Overload)
                if I_fixed == float(dict["maxCurrent"]) and Iset == float(dict["maxCurrent"]):
                    Current(dict["ELoad"]).setOutputCurrent(I_fixed - 0.001)
                    WAI(dict["ELoad"])
                else:
                    Current(dict["ELoad"]).setOutputCurrent(I_fixed-0.001)
                    WAI(dict["ELoad"])

                sleep(1)

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
        Current(dict["ELoad"]).setOutputCurrent(0)
        WAI(dict["ELoad"])
        """Output(dict["PSU"]).SPModeConnection("OFF")
        WAI(dict["PSU"])"""
        psu.outputState("OFF", ch)
        WAI(dict["PSU"])
        Output(dict["ELoad"]).setOutputState("OFF")
        WAI(dict["ELoad"])
        RST(dict["DMM"])
        WAI(dict["DMM"])

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
                #temp_values = psu.measureVoltageDC(ch)
                diagVmon_raw = psu.diagVoltageReadback_VMON_100k()
                sleep(1)
                # Decode from bytes to string
                diagVmon_str = diagVmon_raw.decode().strip()
                print("Raw Response:", diagVmon_str)

                # Split into components
                values = diagVmon_str.split(',')
                cleandiagVmon = float(values[0])

                print("Voltage Monitor Reading =", cleandiagVmon)
                WAI(dict["PSU"])

                #temp_values2 = psu.measureCurrentDC(ch)
                diagImon_raw = psu.diagCurrentReadback_IMON_FULL_100k()
                sleep(1)
                # Decode from bytes to string
                diagImon_str = diagImon_raw.decode().strip()
                print("Raw Response:", diagImon_str)

                # Split into components
                diagImon_values = diagImon_str.split(',')
                cleandiagImon = float(diagImon_values[0])
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
                #temp_values = psu.measureVoltageDC(ch)
                diagVmon_raw = psu.diagVoltageReadback_VMON_100k()
                sleep(1)
                # Decode from bytes to string
                diagVmon_str = diagVmon_raw.decode().strip()
                print("Raw Response:", diagVmon_str)

                # Split into components
                values = diagVmon_str.split(',')
                cleandiagVmon = float(values[0])

                print("Voltage Monitor Reading =", cleandiagVmon)
                WAI(dict["PSU"])

                #temp_values2 = psu.measureCurrentDC(ch)
                diagImon_raw = psu.diagCurrentReadback_IMON_200uA_100k()
                sleep(1)
                # Decode from bytes to string
                diagImon_str = diagImon_raw.decode().strip()
                print("Raw Response:", diagImon_str)

                # Split into components
                diagImon_values = diagImon_str.split(',')
                cleandiagImon = float(diagImon_values[0])
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
                #temp_values = psu.measureVoltageDC(ch)
                diagVmon_raw = psu.diagVoltageReadback_VMON_100k()
                sleep(1)
                # Decode from bytes to string
                diagVmon_str = diagVmon_raw.decode().strip()
                print("Raw Response:", diagVmon_str)

                # Split into components
                values = diagVmon_str.split(',')
                cleandiagVmon = float(values[0])

                print("Voltage Monitor Reading =", cleandiagVmon)
                WAI(dict["PSU"])

                #temp_values2 = psu.measureCurrentDC(ch)
                diagImon_raw = psu.diagCurrentReadback_IMON_2mA_100k()
                sleep(1)
                # Decode from bytes to string
                diagImon_str = diagImon_raw.decode().strip()
                print("Raw Response:", diagImon_str)

                # Split into components
                diagImon_values = diagImon_str.split(',')
                cleandiagImon = float(diagImon_values[0])
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