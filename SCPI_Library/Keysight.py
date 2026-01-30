"""Library containing all the SCPI Commands used by the program that is compatible with Keysight Instruments.

    SCPI Commands are organized in an inverse tree layer where the commands are categorized by Subsystems. Hence,
    different commands are written into methods of child classes based on the Subsystem they belong in. However,
    documentation for each exact method will not be written in this documentation. For further details, please 
    refer to the Programming Manual of those separate instruments or :
    https://rfmw.em.keysight.com/wireless/helpfiles/e5080a/programming/gp-ib_command_finder/scpi_command_tree.htm


"""

import pyvisa
from time import sleep


class Subsystem(object):
    """Parent Class for every SCPI Commands Subsystem

    Attributes:
        VISA_ADDRESS: The string which contains the VISA Address of an Instrument.
        Channel_Number: An integer which contains the Channel Number of Instrument.
        value: An integer which represents the value of certain parameters (e.g. Voltage, Current, Frequency).
        state: A boolean representing if the function should be enabled or disabled.
    """

    def __init__(self, VISA_ADDRESS, timeout=20000):
        """Initialize the instance where the Instrument is ready to receive commands

        Object rm is created where the backend will find the shared VISA Library. VISA_Address is given as
        an argument to declare which resources (in this case, the instruments) to use.

        Args:
            VISA_ADDRESS: String Literal of VISA Address of the Instrument.
            timeout: The timeout value for VISA communication in milliseconds (default is 20000 ms).
        """
        self.VISA_ADDRESS = VISA_ADDRESS
        self.timeout = timeout  # Store the timeout value

        # ResourceManager Setup
        rm = pyvisa.ResourceManager()
        try:
            # Visa Address is found under Keysight Connection Expert
            self.instr = rm.open_resource(self.VISA_ADDRESS)
            self.instr.timeout = self.timeout  # Set the timeout for the instrument
        except pyvisa.VisaIOError as e:
            print(f"VISA IO Error: {e.args}")
            self.instr = None  # Ensure instr is set to None if there's an error


class Abort(Subsystem):
    """Child Class for Abort Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def abort_acquire(self, Channel_Number):
        self.instr.write(f"ABOR:ACQ (@{Channel_Number})")

    def abort_dlog(self):
        self.instr.write("ABOR:DLOG")

    def abort(self, Channel_Number):
        self.instr.write(f"ABOR (@{Channel_Number})")


class Apply(Subsystem):
    """Child Class for Apply Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def write(self, Voltage, Current):
        self.instr.write(f"{Voltage},{Current}")


class Current(Subsystem):
    """Child Class for Current Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setOutputCurrent(self, Current):
        self.instr.write(f"CURR {Current}")
        
    def SourceCurrentLevel(self):
        return self.instr.query("CURR?")

    def OutputCurrentStepSize(self, Current, ChannelNumber):
        self.instr.write(f"CURR:STEP {Current},(@{ChannelNumber})")

    def setTriggeredCurrent(self, Current, ChannelNumber):
        self.instr.write(f"CURR:TRIG {Current},(@{ChannelNumber})")

    def setCurrentLimit(self, Current, ChannelNumber):
        self.instr.write(f"CURR:TRIG {Current},(@{ChannelNumber})")

    def setCurrentMode(self, Mode, ChannelNumber):
        self.instr.write(f"CURR:MODE {Mode},(@{ChannelNumber})")

    def CLECurrentProtection(self, ChannelNumber):
        self.instr.write(f"CURR:PROT:CLE (@{ChannelNumber})")

    def setCurrentProtectionDelay(self, delay_time, ChannelNumber):
        self.instr.write(f"CURR:PROT:DEL {delay_time},(@{ChannelNumber})")

    def enableCurrentProtection(self, state, ChannelNumber):
        self.instr.write(f"CURR:PROT:STAT {state},(@{ChannelNumber})")

    def setTripCurrentQuery(self, ChannelNumber):
        return self.instr.query(f"CURR:PROT:TRIP? (@{ChannelNumber})")
    
    def setDelayStartCondition(self, Condition, ChannelNumber):
        self.instr.write(f"CURR:PROT:DEL:STAR {Condition},(@{ChannelNumber})")

    def setCurrentRange(self, range, ChannelNumber):
        self.instr.write(f"CURR:RANG {range},(@{ChannelNumber})")

    def enableLowRangeCurrent(self, mode):
        self.instr.write(f"CURR:SENS:LOW {mode}")

    def setPositiveSlew(self, Current, ChannelNumber):
        self.instr.write(f"CURR:SLEW {Current},(@{ChannelNumber})")

    def setNegativeSlew(self, Current, ChannelNumber):
        self.instr.write(f"CURR:SLEW:NEG {Current},(@{ChannelNumber})")

    def setTransInput(self, Current, ChannelNumber):
        self.instr.write(f"CURR:TLEV {Current},(@{ChannelNumber})")

    def setTerminal(self, terminal):
        self.instr.write(f"CURR:TERM {terminal}")

    def setApertureTime(self, seconds):
        self.instr.write(f"CURR:DC:APER {seconds}")

    def setNPLC(self, value):
        self.instr.write(f"CURR:DC:NPLC {value}")

    def setAutoZeroMode(self, mode):
        self.instr.write(f"CURR:ZERO:AUTO {mode}")


class Calculate(Subsystem):
    """Child Class for Calculate Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def function(self, mode):
        self.instr.write(f"CALC:FUNC {mode}")

    def state(self, mode):
        self.instr.write(f"CALC:STAT {mode}")

    def limit_lower(self, value):
        self.instr.write(f"CALC:LIM:LOW {value}")

    def limit_upper(self, value):
        self.instr.write(f"CALC:LIM:UPP {value}")

    def Average(self, value):
        return self.instr.query(f"CALC:AVER: {value}?")

    def DBref(self, value):
        self.instr.write(f"CALC:DBV:REF {value}")

    def offset(self, value):
        self.instr.write(f"CALC:NULL:OFFS {value}")

    def query(self, ans):
        return self.instr.query(ans)


class Calibration(Subsystem):
    """Child Class for Calibration Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def calibration(self):
        return self.instr.query("CAL?")

    def calibrationCount(self):
        return self.instr.query("CAL:COUN?")

    def setSecureCode(self, new_code):
        self.instr.write(f"CAL:SEC:CODE {new_code}")

    def setSecureState(self, state):
        self.instr.write(f"CAL:SEC:STAT {state}")

    def querySecureState(self):
        return self.instr.query("CAL:SEC:STAT?")

    def calibrationString(self, string):
        self.instr.write(f'CAL:STR "' + {string} + '"')

    def calibrationValue(self, value):
        self.instr.write(f"CAL:VAL {value}")

    def calibrationStore(self):
        self.instr.write("CAL:STOR")


class Configure(Subsystem):
    """Child Class for Configure Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def write(self, *args):
        if len(args) == 1:
            self.instr.write(f"CONF:{args[0]}")

        elif len(args) == 2:
            self.instr.write(f"CONF:{args[0]}:{args[1]}")

        elif len(args) == 3:
            self.instr.write(f"CONF:{args[0]}:{args[1]}:{args[2]}")

    def query(self, *args):
        if len(args) == 1:
            return self.instr.query(f"CONF: {args[0]}?")

        elif len(args) == 2:
            return self.instr.query(f"CONF: {args[0]}:{args[1]}?")

        elif len(args) == 3:
            return self.instr.query(f"CONF: {args[0]}:{args[1]}:{args[2]}?")


class Data(Subsystem):
    """Child Class for Data Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def data(self):
        return self.instr.query("DATA:DATA? NVMEM")

    def delete(self):
        return self.instr.query("DATA:DEL NVMEM")

    def last(self):
        return self.instr.query("DATA:LAST?")

    def datapoints(self):
        return self.instr.query("DATA:POIN? NVMEM")


class Display(Subsystem):
    """Child Class for Display Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def displayState(self, state):
        self.instr.write(f"DISP:CHAN {state}")

    def displayText(self, string):
        self.instr.write(f'DISP:TEXT "{string}"')

    def clearDisplayText(self):
        self.instr.write("DISP:TEXT:CLE")


class Emul(Subsystem):
    """Child Class for Emul Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def Emulate(self, mode):
        self.instr.write(f"EMUL {mode}")


class Fetch(Subsystem):
    """Child Class for Fetch Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def query(self):
        return self.instr.query("FETC?")

    def query2(self, ChannelNumber, *args):
        if len(args) == 1:
            return self.instr.query(f"FETC:{args[0]}? (@{ChannelNumber})")

        elif len(args) == 2:
            return self.instr.query(f"FETC:{args[0]}:{args[1]}? (@{ChannelNumber})")


class Function(Subsystem):
    """Child Class for Function Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setMode(self, MODE):
        self.instr.write(f"FUNC {MODE}")

class Frequency(Subsystem):
    """Child Class for Frequency Subsystem (Designed for AC Source)"""
    
    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setOutputFrequency (self, Value):
        self.instr.write(f"FREQ {Value}")
        
class Format(Subsystem):
    """Child Class for Format Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def query(self):
        return self.instr.query("*FORM:OUTP?")

    def write(self, mode):
        self.instr.write(f"FORM:OUTP {mode}")


class Initiate(Subsystem):
    """Child Class for Initiate Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def initiate(self):
        self.instr.write("INIT")

    def initiateAcquire(self, ChannelNumber):
        self.instr.write(f"INIT:ACQ (@{ChannelNumber})")

    def initiateDLog(self, filename):
        self.instr.write(f"INIT:DLOG {filename}")

    def initiateContinuous(self, state, ChannelNumber):
        self.instr.write(f"INIT:CONT:TRAN {state},(@{ChannelNumber})")


class Output(Subsystem):
    """Child Class for Output Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setOutputState(self, state):
        self.instr.write(f"OUTP {state}")

    def setOutputStateChannel(self, state, ChannelNumber):
        self.instr.write(f"OUTP {state},(@{ChannelNumber})")

    def coupleChannel(self, ChannelNumber):
        self.instr.write(f"OUTP:COUP:CHAN CH{ChannelNumber}")

    def setDelayOn(self, delay_time, ChannelNumber):
        self.instr.write(f"OUTP:DEL:FALL {delay_time},(@{ChannelNumber})")

    def setDelayOff(self, delay_time, ChannelNumber):
        self.instr.write(f"OUTP:DEL:RISE {delay_time},(@{ChannelNumber})")

    def setOutputMode(self, Mode, ChannelNumber):
        self.instr.write(f"OUTP:PMOD {Mode},(@{ChannelNumber})")

    def setInhibMode(self, Mode):
        self.instr.write(f"OUTP:INH:MODE {Mode}")

    def setPowerOnState(self, state):
        self.instr.write(f"OUTP:PON:STAT " + str(state))

    def clearLatchProtection(self, ChannelNumber):
        self.instr.write(f"INP:PRO:CLE (@{ChannelNumber})")

    def setRelayState(self, state):
        self.instr.write(f"OUTP:REL {state}")

    def shortInput(self, state):
        self.instr.write(f"INP:SHOR {state}")
    
    #Series Parallel Mode
    def SPModeConnectionQuery(self):
        return self.instr.query("OUTP:PAIR:EXT:CONN?")
    
    def SPModeConnection(self, state):
        self.instr.write(f"OUTP:PAIR {state}")

class List(Subsystem):
    """Child Class for List Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setListCount(self, range, ChannelNumber):
        self.instr.write(f"LIST:COUN {range},(@{ChannelNumber})")

    def setCurrentList(self, list, ChannelNumber):
        self.instr.write(f"LIST:CURR {list},(@{ChannelNumber})")

    def queryCurrentPoints(self, ChannelNumber):
        self.instr.write(f"LIST:CURR:POIN? (@{ChannelNumber})")


class LXI(Subsystem):
    """Child Class for LXI Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setIdentityState(self, state):
        self.instr.write(f"LXI:IDEN {state}")

    def queryIdentityState(self):
        return self.instr.query("LXI:IDEN?")

    def setMDNS(self, state):
        self.instr.write(f"LXI:MDNS:ENAB{state}")

    def queryMDNShost(self):
        return self.instr.query("LXI:MDNS:ENAB?")

    def resolvedMDNS(self):
        return self.instr.query("LXI:MDNS:HNAM:RES?")

    def setMDNSName(self, name):
        self.instr.write(f'LXI:MDNS:SNAM:DES "{name}"')

    def queryMDNSName(self):
        return self.instr.query("LXI:MDNS:SNAM:DES?")

    def queryMDSNservice(self):
        return self.instr.query("LAXI:MDNS:SNAM:RES?")

    def reset(self):
        self.dmm.write("LXI:RES")

    def restart(self):
        self.dmm.write("LXI:REST")


class Measure(Subsystem):
    """Child Class for Measure Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def singleChannelQuery(self, *args):
        if len(args) == 1:
            return self.instr.query(f"MEAS:{args[0]}?")

        elif len(args) == 2:
            return self.instr.query(f"MEAS:{args[0]}:{args[1]}?")

        elif len(args) == 3:
            return self.instr.query(f"MEAS:{args[0]}:{args[1]}:{args[2]}?")

    def multipleChannelQuery(self, ChannelNumber, *args):
        if len(args) == 1:
            return self.instr.query(f"MEAS:{args[0]}? (@{ChannelNumber})")

        elif len(args) == 2:
            return self.instr.query(f"MEAS:{args[0]}:{args[1]}?(@{ChannelNumber})")

class Memory(Subsystem):
    """Child Class for Memory Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def write(self, *args):
        if len(args) == 1:
            self.instr.write(f"MEM:STAT:{args}")

        elif len(args) == 2:
            self.instr.write(f"MEM:STAT:{args[0]}:{args[1]}")

    def query(self, *args):
        if len(args) == 1:
            return self.instr.query(f"MEM:STAT:{args}?")

        elif len(args) == 2:
            return self.instr.query(f"MEM:STAT:{args[0]}:{args[1]}?")


class MMemory(Subsystem):
    """Child Class for MMemory Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def exportData(self, filename):
        self.instr.write(f"MMEM:EXP:DLOG {filename}")


class Power(Subsystem):
    """Child Class for Power Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setInputPower(self, value):
        self.instr.write(f"POW {value}")

    def setTrigPower(self, value, ChannelNumber):
        self.instr.write(f"POW:TRIG {value}(@{ChannelNumber})")
    
    def setPowerLimit(self, Power):
        self.instr.write(f"SOUR:POW:LEV:IMM:AMPL {Power}")

    def setPowerMode(self, mode, ChannelNumber):
        self.instr.write(f"POW:MODE {mode}(@{ChannelNumber})")

    def setProtectionDelay(self, delaytime, ChannelNumber):
        self.instr.write(f"POW:PROT:DEL {delaytime},(@{ChannelNumber})")

    def setProtectionState(self, state, ChannelNumber):
        self.instr.write(f"POW:PROT:STAT {state},(@{ChannelNumber})")

    def setPowerRange(self, range, ChannelNumber):
        self.instr.write(f"POW:RANG {range},(@{ChannelNumber})")

    def setPositiveSlew(self, rate, ChannelNumber):
        self.instr.write(f"POW:SLEW {rate},(@{ChannelNumber})")

    def setNegativeSlew(self, rate, ChannelNumber):
        self.instr.write(f"POW:SLEW:NEG {rate},(@{ChannelNumber})")

    def setSlewTracking(self, mode, ChannelNumber):
        self.instr.write(f"POW:SLEW COUP {mode},(@{ChannelNumber})")

    def setTransientPower(self, power, ChannelNumber):
        self.instr.write(f"POW:TLEV {power},(@{ChannelNumber})")

    def setPositiveSlewOverride(self, state, ChannelNumber):
        self.instr.write(f"POW:SLEW:MAX {state},(@{ChannelNumber})")

    def setNegativeSlewOverride(self, state, ChannelNumber):
        self.instr.write(f"POW:SLEW:NEG:MAX {state},(@{ChannelNumber})")


class Read(Subsystem):
    """Child Class for Read Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def query(self):
        return self.instr.query("READ?")


class Delay(Subsystem):
    """Child Class for Delay Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def write(self, time):
        self.instr.timeout = int(time)

    def inf(self):
        del self.instr.timeout


class Resistance(Subsystem):
    """Child Class for Resistance Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setInputResistance(self, value, ChannelNumber):
        self.instr.write(f"RES {value},(@{ChannelNumber})")

    def setTrigResistance(self, value, ChannelNumber):
        self.instr.write(f"RES:TRIG {value},(@{ChannelNumber})")

    def setResistanceMode(self, mode, ChannelNumber):
        self.instr.write(f"RES:MODE {mode},(@{ChannelNumber})")

    def setResistanceRange(self, range, ChannelNumber):
        self.instr.write(f"RES:RAN {range},(@{ChannelNumber})")

    def setPositiveSlew(self, rate, ChannelNumber):
        self.instr.write(f"RES:SLEW {rate},(@{ChannelNumber})")

    def setNegativeSlew(self, rate, ChannelNumber):
        self.instr.write(f"RES:SLEW:NEG {rate},(@{ChannelNumber})")

    def setSlewTracking(self, mode, ChannelNumber):
        self.instr.write(f"RES:SLEW:COUP {mode},(@{ChannelNumber})")

    def setTransientPower(self, power, ChannelNumber):
        self.instr.write(f"RES:TLEV {power},(@{ChannelNumber})")

    def setPositiveSlewOverride(self, state, ChannelNumber):
        self.instr.write(f"RES:SLEW:MAX {state},(@{ChannelNumber})")

    def setNegativeSlewOverride(self, state, ChannelNumber):
        self.instr.write(f"RES:SLEW:NEG:MAX {state},(@{ChannelNumber})")


class Sample(Subsystem):
    """Child Class for Sample Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def write(self, *args):
        self.instr.write(f"SAMP:{args[0]}")

    def query(self, *args):
        return self.instr.query(f"SAMP:{args[0]}?")

    def setSampleCount(self, num):
        self.instr.write(f"SAMP:COUN {num}")


class Sense(Subsystem):
    """Child Class for Sense Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setVoltageRangeDC(self, range):
        self.instr.write(f"VOLT:RANG {range}")

    def setVoltageRangeDCAuto(self):
        self.instr.write("VOLT:RANG:AUTO ON")

    def setVoltageResDC(self, string):
        self.instr.write(f"SENSe:VOLTage:DC:RESolution {string}")

    def setVoltageRangeAC(self, range):
        self.instr.write(f"VOLT:AC:RANG {range}")

    def setVoltageResAC(self, string):
        self.instr.write(f"VOLT:AC:RES {string}")

    def setCurrentRangeDC(self, range):
        self.instr.write(f"CURR:RANG {range}")

    def setCurrentRangeDCAuto(self):
        self.instr.write("CURR:RANG:AUTO ON")

    def setCurrentResDC(self, string):
        self.instr.write(f"CURR:RES {string}")

    def setCurrentRangeAC(self, range):
        self.instr.write(f"CURR:AC:RANG {range}")

    def setCurrentResAC(self, string):
        self.instr.write(f"CURR:AC:RES {string}")

    def setResistanceRange(self, range):
        self.instr.write(f"RES:RANG {range}")

    def setResistanceRes(self, string):
        self.instr.write(f"RES:RES {string}")

    def setResistanceOCompensated(self, string):
        self.instr.write(f"RES:OCOM {string}")

    def setFResistanceRange(self, range):
        self.instr.write(f"FRES:RANG {range}")

    def setFResistanceRes(self, string):
        self.instr.write(f"FRES:RES {string}")

    def setFResistanceOCompensated(self, string):
        self.instr.write(f"FRES:OCOM {string}")

    def setFrequencyAperture(self, value):
        self.instr.write(f"FREQ:APER {value}")

    def setFrequencyVoltageRange(self, value):
        self.instr.write(f"FREQ:VOLT:RANG {value}")

    def setFrequencyCurrentRange(self, value):
        self.instr.write(f"FREQ:CURR:RANG {value}")

    def setThermsistorResistance(self, value):
        self.instr.write(f"TEMP:TRAN:THER:TYPE {value}")

    def setCapacitanceRange(self, range):
        self.instr.write(f"CAP:RANG {range}")

    def enableCurrentDataLogging(self, state, ChannelNumber):
        self.instr.write(f"SENS:DLOG:FUNC:VOLT {state},(@{ChannelNumber})")

    def enableCurrentDataLogging(self, state, ChannelNumber):
        self.instr.write(f"SENS:DLOG:FUNC:CURR {state},(@{ChannelNumber})")

    def enableMinMaxLogging(self, state):
        self.instr.write(f"SENS:DLOG:FUNC:MINM {state}")

    def setTriggerOffset(self, offset_percent):
        self.instr.write(f"SENS:DLOG:OFFS {offset_percent}")

    def setSamplePeriod(self, time):
        self.instr.write(f"SENS:DLOG:PER {time}")

    def setSampleDuration(self, time):
        self.instr.write(f"SENS:DLOG:TIME {time}")

    def enableCurrentMeasurement(self, state, ChannelNumber):
        self.instr.write(f"SENS:FUNC:CURR {state},(@{ChannelNumber})")

    def enableVoltageMeasurement(self, state, ChannelNumber):
        self.instr.write(f"SENS:FUNC:VOLT {state},(@{ChannelNumber})")

    def specifySweepPoint(self, data_points, ChannelNumber):
        self.instr.write(f"SENS:SWE:POIN {data_points},(@{ChannelNumber})")

    def specifyOffsetSweepPoint(self, data_points, ChannelNumber):
        self.instr.write(f"SENS:SWE:OFFS:POIN {data_points},(@{ChannelNumber})")

    def specifyIntervalPoints(self, time, ChannelNumber):
        self.instr.write(f"SENS:TINT {time},(@{ChannelNumber})")


class Status(Subsystem):
    """Child Class for Status Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def operationCondition(self):
        return self.instr.query("STAT:OPER:COND?")

    def operationEnable(self, *args):
        if len(*args) == 0:
            self.instr.write("STAT:OPER:ENAB")

        elif len(*args) == 1:
            self.instr.write(f"STAT:OPER:ENAB {args[0]}")

    def statusOperation(self):
        return self.instr.query("STAT:OPER?")

    def preset(self):
        return self.instr.query("STAT:PRES")

    def questionableCondition(self):
        return self.instr.query("STAT:QUES:COND?")

    def questionableEnable(self, *args):
        if len(*args) == 0:
            self.instr.write("STAT:QUES:ENAB")

        elif len(*args) == 1:
            self.instr.write(f"STAT:QUEST:ENAB {args[0]}")

    def questionableCondition(self):
        return self.instr.query("STAT:QUES?")
    
    def CV_CC_OperationModeQuery(self, ChannelNumber):
        return self.instr.query(f"STAT:QUES:INST:ISUM{ChannelNumber}:COND?")
    

class System(Subsystem):
    """Child Class for System Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def beeper(self):
        self.instr.write("SYST:BEEP")

    def beeperStatus(self, mode):
        self.instr.write(f"SYST:BEEP:STAT {mode}")

    def LANControl(self):
        return self.instr.query("SYST:COMM:LAN:CONT?")

    def LAN_DHCP(self, args):
        self.instr.write(f"SYST:COMM:DHCP {args}")

    def LAN_DNS(self, DNS_Address):
        self.instr.write(f'SYST:COMM:DNS "{DNS_Address}"')

    def LAN_Domain(self):
        return self.instr.query("SYST:COMM:LAM:DOM?")

    def LAN_DNS(self, DNS_Address):
        self.instr.write(f'SYST:COMM:DNS "{DNS_Address}"')

    def LAN_GATE(self, Gate_Address):
        self.instr.write(f'SYST:COMM:LAN:GATE "{Gate_Address}"')

    def LAN_Host(self, HostName):
        self.instr.write(f'SYST:COMM:LAN:HOST "{HostName}"')

    def LAN_IP(self, IP_Address):
        self.instr.write(f'SYST:COMM:LAN:IPAD "{IP_Address}"')

    def LAN_MAC(self):
        return self.instr.query("SYST:COMM:LAN:MAC?")

    def LAN_SMask(self, mask):
        self.instr.write(f'SYST:COMM:LAN:SMAS "{mask}"')

    def TELN_WMsg(self, string):
        self.instr.write(f'SYST:COMM:LAN:TELN:WMES "{string}"')

    def LAN_Update(self):
        self.instr.write("SYSTS:COMM:LAN:UPD")

    def TCP_Control(self):
        return self.instr.query("SYST:COMM:TCP:CONT?")

    def setDate(self, YYYY, MM, DD):
        self.instr.write(f"SYST:DATE {YYYY},{MM},{DD}")

    def queryDate(self):
        return self.instr.query("DATE?")

    def setLFrequency(self, delay_time):
        self.instr.write(f"SYST:LFR {delay_time}")

    def queryLFrequency(self):
        return self.instr.query("SYST:LFR?")

    def systemLocal(self):
        self.instr.write("SYST:LOC")

    def systemPreset(self):
        self.instr.write("SYST:PRES")

    def setSystemState(self, stateNo):
        self.instr.write(f"SYST:SET {stateNo}")

    def setTime(self, hh, mm, ss):
        self.instr.write(f"SYST:TIME {hh},{mm},{ss}")

    def queryTime(self):
        return self.instr.query("SYST:TIME?")

    def version(self):
        return self.instr.query("SYST:VERS?")


class Transient(Subsystem):
    """Child Class for Transient Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setTransientCount(self, value, ChannelNumber):
        self.instr.write(f"TRAN:COUN {value},(@{ChannelNumber})")

    def setDutyCycle(self, value, ChannelNumber):
        self.instr.write(f"TRAN:DCYC {value},(@{ChannelNumber})")

    def setTransientFrequency(self, value, ChannelNumber):
        self.instr.write(f"TRAN:FREQ {value},(@{ChannelNumber})")

    def setTransientMode(self, Mode, ChannelNumber):
        self.instr.write(f"TRAN:MODE {Mode},(@{ChannelNumber})")

    def setTransientPulseWidth(self, value, ChannelNumber):
        self.instr.write(f"TRAN:TWID {value},(@{ChannelNumber})")


class Trigger(Subsystem):
    """Child Class for Trigger Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setCount(self, num):
        self.instr.write(f"TRIG:COUN {num}")

    def queryCount(self, args):
        return self.instr.query(f"TRIG:COUN? {args}")

    def setSource(self, args):
        self.instr.write(f"TRIG:SOUR {args}")

    def querySource(self):
        return self.instr.query("TRIG:SOUR?")

    def triggerAcquire(self, ChannelNumber):
        self.instr.write(f"TRIG:ACQ (@{ChannelNumber})")

    def setTriggeredCurrent(self, value, ChannelNumber):
        self.instr.write(f"TRIG:ACQ:CURR {value},(@{ChannelNumber})")

    def setCurrentSlope(self, state, ChannelNumber):
        self.instr.write(f"TRIG:ACQ:CURR:SLOP {state},(@{ChannelNumber})")

    def setTriggeredVoltage(self, value, ChannelNumber):
        self.instr.write(f"TRIG:ACQ:VOLT {value},(@{ChannelNumber})")

    def setVoltageSlope(self, state, ChannelNumber):
        self.instr.write(f"TRIG:ACQ:VOLT:SLOP {state},(@{ChannelNumber})")

    def setTriggerDelay(self, time):
        self.instr.write(f"TRIG:DEL {time}")


class Unit(Subsystem):
    """Child Class for Unit Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setTemp(self, units):
        self.instr.write("UNIT:TEMP " + self.strtoargs(units))

    def queryTemp(self):
        return self.instr.query("UNIT:TEMP?")


class Voltage(Subsystem):
    """Child Class for Voltage Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setOutputVoltage(self, Value):
        self.instr.write(f"VOLT {Value}")

    def OutputVoltageStepSize(self, Value, ChannelNumber):
        self.instr.write(f"VOLT:STEP {Value},(@{ChannelNumber})")

    def setTriggeredVoltage(self, Value, ChannelNumber):
        self.instr.write(f"VOLT:TRIG {Value},(@{ChannelNumber})")

    def setVoltageLimit(self, Value, ChannelNumber):
        self.instr.write(f"VOLT:LIM {Value},(@{ChannelNumber})")

    def setVoltageMode(self, Mode, ChannelNumber):
        self.instr.write(f"VOLT:MODE {Mode},(@{ChannelNumber})")

    def CLEVoltageProtection(self, ChannelNumber):
        self.instr.write(f"VOLT:PROT:CLE (@{ChannelNumber})")

    def setProtectionDelay(self, delay_time, ChannelNumber):
        self.instr.write(f"VOLT:PROT:DEL {delay_time},(@{ChannelNumber})")

    def enableVoltageProtection(self, state, ChannelNumber):
        self.instr.write(f"VOLT:PROT:STAT {state},(@{ChannelNumber})")

    def setTripVoltage(self, voltage, ChannelNumber):
        self.instr.write(f"VOLT:PROT {voltage},(@{ChannelNumber})")
    
    def setACTripVoltage(self,voltage):
        self.instr.write(f"VOLT:PROT {voltage}")

    def setTripVoltageQuery(self, ChannelNumber):
        return self.instr.query(f"VOLT:PROT:TRIP? (@{ChannelNumber})")

    def setVoltageRange(self, range, ChannelNumber):
        self.instr.write(f"VOLT:RANG {range},(@{ChannelNumber})")

    def setPositiveSlew(self, Current, ChannelNumber):
        self.instr.write(f"VOLT:SLEW {Current},(@{ChannelNumber})")

    def setNegativeSlew(self, Current, ChannelNumber):
        self.instr.write(f"VOLT:SLEW:NEG {Current},(@{ChannelNumber})")

    def setTransInput(self, Current, ChannelNumber):
        self.instr.write(f"VOLT:TLEV {Current},(@{ChannelNumber})")

    def setSlewTracking(self, mode, ChannelNumber):
        self.instr.write(f"VOLT:SLEW COUP {mode},(@{ChannelNumber})")

    def setTransientPower(self, power, ChannelNumber):
        self.instr.write(f"VOLT:TLEV {power},(@{ChannelNumber})")

    def setPositiveSlewOverride(self, state, ChannelNumber):
        self.instr.write(f"VOLT:SLEW:MAX {state},(@{ChannelNumber})")

    def setNegativeSlewOverride(self, state, ChannelNumber):
        self.instr.write(f"VOLT:SLEW:NEG:MAX {state},(@{ChannelNumber})")

    def setSenseModeSingle(self, state):
        self.instr.write(f"VOLT:SENS:SOUR {state}")
    
    def setSenseModeMultipleChannel(self, state, ChannelNumber):
        self.instr.write(f"VOLT:SENS:SOUR {state},(@{ChannelNumber})")

    def setInstrumentChannel(self, ChannelNumber):
        self.instr.write(f"INSTrument:NSELect {ChannelNumber}")

    def setInstrumentChannelQuery(self):
        return self.instr.query(f"INSTrument:NSELect?")

    def specifyVoltageOn(self, Voltage, ChannelNumber):
        self.instr.write(f"VOLT:INH:VON {Voltage},(@{ChannelNumber})")

    def setInhibMode(self, mode, ChannelNumber):
        self.instr.write(f"VOLT:INH:VON:MODE {mode},(@{ChannelNumber})")

    def setApertureMode(self, mode):
        self.instr.write(f"VOLT:APER:ENAB {mode}")

    def setApertureTime(self, seconds):
        self.instr.write(f"VOLT:DC:APER {seconds}")
    #In NPLC
    def setNPLC(self, value):
        self.instr.write(f"SENSe:VOLTage:DC:NPLCycles {value}")

    def setApertureTime(self, value):
        self.instr.write(f"SENSe:VOLTage:DC:APERture {value}")

    def setAutoZeroMode(self, mode):
        self.instr.write(f"SENSe:VOLTage:DC:ZERO:AUTO {mode}")

    def setAutoImpedanceMode(self, mode):
        self.instr.write(f"SENSe:VOLTage:DC:IMPedance:AUTO {mode}")

class Excavator(Subsystem):
    
    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setSYSTEMEMULationMode(self, mode):
        self.instr.write(f"SYSTem:EMULation {mode}")

class SMU(Subsystem):
    
    def __init__(self,VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)
    
    def setCurrentComplianceLimit (self, Value):
        self.instr.write(f"SENSe:CURRent:DC:PROTection:LEVel {Value}")

    def setSMUSenseMode (self,state):
        self.instr.write(f"SENSe:REMote {state}")

    def setRange (self, Mode, Value):
        self.instr.write(f"SOURce:{Mode}:RANGe {Value}")


class Oscilloscope(Subsystem):
    """Child Class for Oscilloscope Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setChannelCoupling(self, ChannelNumber, Mode):
        #self.instr.write(f":{ChannelNumber}:COUPLING {Mode}")
        self.instr.write(f":{ChannelNumber}:COUPLING {Mode}")

    def setTriggerMode(self, Mode):
        self.instr.write(f"TRIGGER:MODE {Mode}")

    def setTriggerSource(self, ChannelNumber):
        self.instr.write(f"TRIGGER:EDGE:SOURCE {ChannelNumber}")

    def setTriggerEdgeLevel(self, value, ChannelNumber):
        self.instr.write(f"TRIGGER:EDGE:LEVEL {value},{ChannelNumber}")

    def setTriggerCoupling(self, mode):
        self.instr.write(f"TRIGGER:EDGE:COUPLING {mode}")

    def setTriggerSweepMode(self, mode):
        self.instr.write(f"TRIGGER:SWEEP {mode}")

    def setTriggerSlope(self, mode):
        self.instr.write(f"TRIGGER:EDGE:SLOPE {mode}")

    def FScale(self, value):
        self.instr.write(f"TIMEBASE:MAIN:SCALE {value}")
    
    def setTimeScale(self, value):
        self.instr.write(f":TIMebase:RANGe {value}")

    def setVerticalScale(self, value, ChannelNumber):
        self.instr.write(f":{ChannelNumber}:SCALE {value}")
        #self.instr.write(f":{ChannelNumber}:SCALE {value}")

    def setSingleMode(self):
        self.instr.write("SINGLE")

    def getRiseTime(self, ChannelNumber):
        return self.instr.query(f"MEAS:RIS? CHANNEL{ChannelNumber}")
    
    def setModeRiseTime(self, ChannelNumber):
        self.instr.write(f"MEAS:RIS CHANNEL{ChannelNumber}")

    def getFallTime(self, ChannelNumber):
        return self.instr.query(f"MEAS:FALL? CHANNEL{ChannelNumber}")

    def setModeFallTime(self, ChannelNumber):
        self.instr.write(f"MEAS:FALL CHANNEL{ChannelNumber}")

    def setTriggerHFReject(self, mode):
        self.instr.write(f"TRIGGER:HFREJECT {mode}")

    def setTriggerNoiseReject(self, mode):
        self.instr.write(f"TRIGGER:NREJECT {mode}")

    def getMaximumVoltage(self):
        return self.instr.query("MEASURE:VMAX?")

    def setUpperLimit(self, value):
        self.instr.write(f"MEASURE:UPPER {value}")

    def setLowerLimit(self, value):
        self.instr.write(f"MEASURE:LOWER {value}")

    def setThresholdMode(self, mode):
        self.instr.write(f"MEASURE:THRESHOLDS {mode}")

    def setVerticalOffset(self, value, ChannelNumber):
        self.instr.write(f"CHANNEL{ChannelNumber}:OFFSET {value}")
    
    def stop (self):
        self.instr.write(':STOP; *WAI')

    def run (self):
        self.instr.write(':RUN; *WAI')

    def hardcopy (self, state):
        self.instr.write(f':HARDcopy:INKSaver {state}')
    
    def displaydata(self):
        self.instr.write(":DISPlay:DATA? PNG")
        """ self.instr.query('*OPC?')
        sleep(5)
        return self.instr.read_raw()"""
    
    def read_binary_data(self):
        #return self.instr.read_raw()
        return self.instr.query_binary_values(':DISP:DATA? PNG',datatype='B',container=bytearray)
    
    def on_displaycursor(self):
        self.instr.write(":DISPlay:SIDebar CURSors")

    def measureVTOP(self, ChannelNumber):
        return self.instr.query_ascii_values(f":MEASure:VTOP? {ChannelNumber}")
    
    def measureVMIN(self, ChannelNumber):
        return self.instr.query_ascii_values(f":MEASure:VMIN? {ChannelNumber}")
    
    def measureVMAX(self, ChannelNumber):
        return self.instr.query_ascii_values(f":MEASure:VMAX? {ChannelNumber}")
    
    def measureFallingtime(self, ChannelNumber):
        return self.instr.query_ascii_values(f":MEASure:FALLtime? {ChannelNumber}")
    
    def measureRisingtime(self, ChannelNumber):
        return self.instr.query_ascii_values(f":MEASure:RISetime? {ChannelNumber}")
    
    def measureXMIN(self, ChannelNumber):
        return self.instr.query_ascii_values(f":MEASure:XMIN? {ChannelNumber}")
    
    def measureXMAX(self, ChannelNumber):
        return self.instr.query_ascii_values(f":MEASure:XMAX? {ChannelNumber}")
    
    def measureMode(self, state):
        self.instr.write(f":MARK:MODE {state}")

    def set_marker_X1(self, Position):
        self.instr.write(f"MARKer:X1Position {Position}")

    def set_marker_X2(self, Position):
        self.instr.write(f"MARKer:X2Position {Position}")
    
    def set_marker_Y1(self, Position):
        self.instr.write(f":MARKer:Y1Position {Position}")
    
    def set_marker_Y2(self, Position):
        self.instr.write(f":MARKer:Y2Position {Position}")

    def setProbeAttenuation (self, value, ChannelNumber):
        #self.instr.write(f":{ChannelNumber}:PROBe {value}")
        self.instr.write(f":{ChannelNumber}:PROB {value}")

    def setAcquireType (self, mode):
        self.instr.write(f"ACQuire:TYPE {mode}")

    def setTriggerSourceNew(self, ChannelX):
        self.instr.write(f"TRIG:TV:SOUR {ChannelX}")

    def setChannelOffset (self, value, ChannelNumber):
        self.instr.write(f":{ChannelNumber}:OFFSET {value}")
    
    def setChannelUnits (self, mode, ChannelNumber):
        self.instr.write(f":{ChannelNumber}:UNITs {mode}")
    
    def setChannel_Display(self, state, ChannelNumber):
        self.instr.write(f":{ChannelNumber}:DISP {state}")
    
    def setMarkerXY_Source(self, ChannelNumber):
        self.instr.write(f":MARK:X1Y1  {ChannelNumber}")



class Hornbill(Subsystem):
    """Child Class for Hornbill Subsystem"""

    def __init__(self, VISA_ADDRESS):
        super().__init__(VISA_ADDRESS)

    def setMode(self, mode):
        self.instr.write(f"FUNC:MODE {mode}")

    def setFrequency(self, frequency):
        self.instr.write(f"SOUR:FREQ {frequency}")

    def setPower(self, power):
        self.instr.write(f"SOUR:POW {power}")

    def outputOn(self):
        self.instr.write("OUTP ON")

    def outputOff(self):
        self.instr.write("OUTP OFF")

    def queryFrequency(self):
        return self.instr.query("SOUR:FREQ?")

    def queryPower(self):
        return self.instr.query("SOUR:POW?")

    def queryOutputState(self):
        return self.instr.query("OUTP?")

print ("Keysight SCPI command List Loaded.")