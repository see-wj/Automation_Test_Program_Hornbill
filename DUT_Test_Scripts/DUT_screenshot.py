import sys
import  shutil
import os
import pyvisa
from PIL import Image, ImageDraw, ImageFont
from time import sleep

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem,
                           QSplitter, QFrame, QGroupBox, QGridLayout, QWidget, QApplication, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap

# --------------------------------------------------------------------------- #
# globals                                                                     #
# --------------------------------------------------------------------------- #
hadU2004AReset  = False                     # so U2004A reset is done only once.
rm              = pyvisa.ResourceManager()

# *************************************************************************** #
# functions                                                                   #
# *************************************************************************** #

# =========================================================================== #
# infer the instrument type class from the instrument name                    #
# =========================================================================== #
def GetInstrumentTypeFromName(instrName):
    
    # do this by a loaded dictionary. hardcoded for the moment.
    
    instrDict = {'DSOS604A':'Scope Keysight',                       # scopes
                 'MSO1104Z':'Scope Rigol',
                 'DSOX1204G':'Scope Keysight', 
                 'MSO-X 4104A':'Scope Agilent',
                 'DS1054Z':'Scope Rigol',
                 'DS1104Z':'Scope Rigol',
                 'DPO2014':'Scope Tektronix',
                 'MSO1014':'Scope Tektronix',
                 'MSO4104':'Scope Tektronix',
                 'MSO7104B':'Scope Agilent',
                 'MSO6104A':'Scope Agilent',
                 'GDS-3354':'Scope GW Instek',
                 
                 'E5071C':'VNA Keysight',                           # VNAs
                 'BODE100':'VNA Omicron Labs',
                 'MS2036A/25/27/10/15':'VNA Anritsu',
                 
                 'N5171B':'RF Signal Generator Keysight',           # signal generators
                 'N5172B':'RF Signal Generator Keysight',
                 
                 'N9000A':'Spectrum Analyzer Keysight',             # spectrum analyzers
                 'DSA815':'Spectrum Analyzer Rigol',
                 
                 'FSWP-26':'Signal Analyzer R&S',                   # signal analyzers
                 
                 '34401A':'Digital Multimeter Keysight',            # multimeters
                 '34461A':'Digital Multimeter Keysight',
                 '34460A':'Digital Multimeter Keysight',
                 '34465A':'Digital Multimeter Keysight',
                 '34470A':'Digital Multimeter Keysight',
                 
                 'B2962A':'Source Measure Unit Keysight',           # SMUs
                 'B2902A':'Source Measure Unit Keysight',
                 
                 'DP832A':'Power Supply Rigol',                     # power supplies
                 'DP832':'Power Supply Rigol',
                 'DP831A':'Power Supply Rigol',                     
                 'DP831':'Power Supply Rigol',
                 'E36441A':'Power Supply Keysight',

                 'DG1022Z':'Function Generator Rigol 1000Z',        # AFGs
                 'DG1032Z':'Function Generator Rigol 1000Z',
                 'DG1062Z':'Function Generator Rigol 1000Z',
                 'DG4062':'Function Generator Rigol 4000',
                 'DG4102':'Function Generator Rigol 4000',
                 'DG4162':'Function Generator Rigol 4000',
                 'DG4202':'Function Generator Rigol 4000',
                 'AFG3252':'Function Generator Tektronix',
                 '33509B':'Function Generator Keysight 3Series',
                 '33510B':'Function Generator Keysight 3Series',
                 '33511B':'Function Generator Keysight 3Series',
                 '33512B':'Function Generator Keysight 3Series',
                 '33519B':'Function Generator Keysight 3Series',
                 '33520B':'Function Generator Keysight 3Series',
                 '33521B':'Function Generator Keysight 3Series',
                 '33522B':'Function Generator Keysight 3Series',
                 '33611A':'Function Generator Keysight 3Series',
                 '33612A':'Function Generator Keysight 3Series',
                 '33621A':'Function Generator Keysight 3Series',
                 '33622A':'Function Generator Keysight 3Series',
                 
                 '53230A':'Counter Keysight',                       # frequency counters

                 'U2004A':'USB Power Sensor Keysight',              # power sensors
                 
                 'M300':'Datalogger Rigol',                         # data logger
                 
                 'DL3021A':'Electronic Load Rigol',
                 'EL34243A':'Electronic Load Keysight',                 # electronic load

                 'ARSW6RF':'6Way Rf Relay DL1DWG',                  # my own Arduino SCPI devices
                 'ARSW6DO':'6 Digital Outputs DL1DWG',
                 'ARSW2RP':'2 Power Relays DL1DWG',
                 'ARSW3RBNC':'3 Rf BNC Relays DL1DWG',
                 'ARADIO':'Analog Digital IO DL1DWG',
                 'ARPOWOC':'Power Outlet Controller DL1DWG',
                 'ARCALCO':'Calibration Controller DL1DWG',
                 'ARSWTRAN':'Transfer Switch DL1DWG'
               }  
    try:
        result = instrDict[instrName]
    except:
        result = ''
    return result

# =========================================================================== #
# get a screenshot depending on instrument type class                         #
# =========================================================================== #
def DeleteFile(fileName):
    try:
        os.remove(fileName)
    except OSError:
        pass
    return
    
def WriteFile(result,fileName):
    with open(fileName,'wb') as fileHandle:
        fileHandle.write(result)
        fileHandle.close()
    return

def GetScreenShot(instrType,visaId):
    # first connect to the instrument
    instr = rm.open_resource(visaId,chunk_size=8000,timeout=20000)
    # NO reset or something similar
    
    # delete eventually existing screenshot files 
    DeleteFile('SCREENSHOT.PNG')
    DeleteFile('SCREENSHOT.BMP')    
    DeleteFile('SCREENSHOT.JPG') 

    # set default filename
    fileName = 'SCREENSHOT.PNG'
    
    # rest of code depends on instrument class
    
    # SCOPES -----------------------------------------------------------------#
    if instrType == 'Scope GW Instek':
        try:
            instr.write(':STOP; *WAI')
            # Query the display output in PNG format
            result = instr.query_binary_values(':DISPlay:OUTPut? PNG', datatype='B', container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName

    if instrType == 'Scope Keysight': 
        try:
            instr.write(':STOP; *WAI')
            result = instr.query_binary_values(':DISP:DATA? PNG',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
    
    if instrType == 'Scope Agilent': 
        try:
            #instr.write(':STOP; *WAI')
            instr.write(':HARDcopy:INKSaver OFF')
            result = instr.query_binary_values(':DISP:DATA? PNG',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
            
    if instrType == 'Scope Rigol':
        try:
            instr.write(':STOP; *WAI')
            result = instr.query_binary_values(':DISP:DATA? PNG',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
        
    if instrType == 'Scope Tektronix':
        try:
            instr.write(':SAV:IMAG:FILEF PNG')
            instr.write(':HARDCOPY START')
            result = instr.read_raw()
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName

    # VNAs ---------------------------------------------------------------- #        
    if instrType == 'VNA Keysight':
        
        # Keysight ENA VNAs (E5071C) 
        try:
            instr.write(':MMEM:STOR:IMAG "D:\SCREENSHOT.PNG"\n')
            result = instr.query_binary_values(':MMEM:TRAN? "D:\SCREENSHOT.PNG"',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName

    if instrType == 'VNA Anritsu':
        
        # Anritsu Handheld VNA
        try:
            fileName = 'SCREENSHOT.JPG'
            instr.write(':MMEM:MSIS INT')
            instr.write(':MMEM:STOR:JPEG "SCREENSHOT.JPG" ')
            result = instr.query_binary_values(':MMEM:DATA? "SCREENSHOT.JPG"',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName

    # RF Signal Generators  ----------------------------------------------- #         
    if instrType == 'RF Signal Generator Keysight':
        
        # Keysight EXG RF Generators
        try:
            fileName = 'SCREENSHOT.BMP'
            result = instr.query_binary_values(':DISP:CAPT; :MEM:DATA? "DISPLAY.BMP"',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName

    # Spectrum Analyzers ------------------------------------------------- #         
    if instrType == 'Spectrum Analyzer Keysight':
        
        # Keysight N90XX spectrum analyzers
        try:
            instr.write(':MMEM:STOR:SCR "D:\SCREENSHOT.PNG"')
            result = instr.query_binary_values(':MMEM:DATA? "D:\SCREENSHOT.PNG"',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
        
    if instrType == 'Spectrum Analyzer Rigol':
        
        # Rigol DS800 spectrum analyzers
        try:
            fileName = 'SCREENSHOT.BMP'
            result = instr.query_binary_values(':PRIV:SNAP? BMP',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
        
    # Signal Analyzers ------------------------------------------------- #        
    elif instrType == 'Signal Analyzer R&S':
        
        # Rohde & Schwarz Signal Analyzers
        try:
            instr.write(':HCOP:DEV:LANG1 PNG; *WAI')
            instr.write(':MMEM:NAME \'C:\\R_S\\INSTR\\USER\\PRINT1.PNG\'; *WAI')
            instr.write(':HCOP:IMM1; *WAI')
            result = instr.query_binary_values(":MMEM:DATA? 'C:\\R_S\\INSTR\\USER\\PRINT1.PNG'",datatype='B',container=bytearray,delay=0.1)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
        
    # Digital Multimeters ---------------------------------------------- #         
    if instrType == 'Digital Multimeter Keysight':
        
        # All Keysight DMMs
        try:
            result = instr.query_binary_values(':HCOP:SDUM:DATA:FORM PNG; :HCOP:SDUM:DATA?',datatype='B',container=bytearray,delay=0.1)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
        

    # SMUs ------------------------------------------------------------- #          
    if instrType == 'Source Measure Unit Keysight':
        
        # Keysight B29XX Series SMUs
        try:
            instr.write(':HCOP:SDUM:FORM PNG; *WAI')
            result = instr.query_binary_values(':HCOP:SDUM:DATA?',datatype='B',container=bytearray,delay=0.2)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
        
    # Power Supplies --------------------------------------------------- #         
    if instrType == 'Power Supply Rigol':
        
        # RIGOL DP83X(A) PSUs - No fake needed anymore because there is a hidden command
        try:
            fileName = 'SCREENSHOT.BMP'
            result = instr.query_binary_values(':SYST:PRINT? BMP',datatype='B',container=bytearray,delay=0.2)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
    
    if instrType == 'Power Supply Keysight':
        
        # RIGOL DP83X(A) PSUs - No fake needed anymore because there is a hidden command
        try:
            instr.write(':HCOP:SDUM:FORM PNG; *WAI')
            result = instr.query_binary_values(':HCOP:SDUM:DATA?',datatype='B',container=bytearray,delay=0.2)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
    
    # Electronic Load Rigol -------------------------------------------- #         
    if instrType == 'Electronic Load Rigol':
        
        # RIGOL DL3021 - Not an official command, but IO trace found it
        try:
            result = instr.query_binary_values(':PROJ:WND:DATA?',datatype='B',container=bytearray,delay=0.2)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName

    if instrType == 'Electronic Load Keysight':
        
        # RIGOL DL3021 - Not an official command, but IO trace found it
        try:
            result = instr.query_binary_values(':HCOP:SDUM:DATA:FORM PNG; :HCOP:SDUM:DATA?',datatype='B',container=bytearray,delay=0.1)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
            
    # AFGs ------------------------------------------------------------- #
    if instrType == 'Function Generator Rigol 1000Z':
        
        # RIGOL DG1000Z Series
        try:
            fileName = 'SCREENSHOT.BMP'
            result = instr.query_binary_values(':DISP:DATA?',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
    
    if instrType == 'Function Generator Rigol 4000':
        
        # RIGOL DG4000 Series
        try:
            fileName = 'SCREENSHOT.BMP'
            result = instr.query_binary_values(':HCOP:SDUM:DATA?',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName

    if instrType == 'Arbitrary Function Generator Tektronix':
        
        # Tek AFG3000 Series - not working yet
        try:
            result = instr.query_binary_values(':DISP:DATA?',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
        
    if instrType == 'Function Generator Keysight 3Series':
        
        # Keysight 3Series
        try:
            instr.write(':HCOP:SDUM:DATA:FORM PNG; *WAI')
            result = instr.query_binary_values('HCOP:SDUM:DATA?',datatype='B',container=bytearray)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName
    # Power Sensors ------------------------------------------------------ #
    if instrType == 'USB Power Sensor Keysight':
        
        # Keysight USB Power Sensor - We have to fake this because there is no hardcopy command
        try:
            result = GetKeysightU2004ADeviceScreenShot(instr)
        except:
            fileName = ''
        return fileName
        
    # Counters ----------------------------------------------------------- #
    if instrType == 'Counter Keysight':
        
        # Keysight counter
        try:
            instr.write(':HCOP:SDUM:DATA:FORM PNG; *WAI')
            result = instr.query_binary_values(':HCOP:SDUM:DATA?',datatype='B',container=bytearray,delay=0.2)
            WriteFile(result,fileName)
        except:
            fileName = ''
        return fileName

    # My own ARDUINO SCPI Devices ---------------------------------------- #        
    if  (instrType == '6Way Rf Relay DL1DWG')               or \
        (instrType == '2 Power Relays DL1DWG')              or \
        (instrType == '6 Digital Outputs DL1DWG')           or \
        (instrType == 'Analog Digital IO DL1DWG')           or \
        (instrType == 'Power Outlet Controller DL1DWG')     or \
        (instrType == 'Calibration Controller DL1DWG')      or \
        (instrType == 'Transfer Switch DL1DWG')             or \
        (instrType == '3 Rf BNC Relays DL1DWG'):
        
        # DL1DWG ARDUINO APPLIANCES
        try:
            result = GetArDeviceScreenShot(instr)
            return fileName
        except:
            return ''

    return ''

# =========================================================================== #
# specialized screenshot routines for a device class go here                  #
# =========================================================================== #

# --------------------------------------------------------------------------- #
# get a screenshot from an ARDUINO SCPI device with a virtual display         #
# --------------------------------------------------------------------------- #
def GetArDeviceScreenShot(instr):

    # how many lines to read ?
    noOfLines = int(instr.query('*NLINES?',delay=0.2))
    
    # read all the lines
    lineList = []
    for i in range(noOfLines):
        scpiCommand = '*LTEXT? ' + str(i+1)
        lineReceived = instr.query(scpiCommand,delay=0.2).rstrip('\n').rstrip('\r')
        lineList.append(lineReceived)
        
    # OK, now we need to create a bitmap from the text. check line length
    maxLen = 0
    for i in range(noOfLines):
        maxLen = max(maxLen,len(lineList[i]))

    # some fitting heuristics
    fontSize  = 64
    imgSizeX  = int(maxLen * fontSize * 0.75) + 20
    imgSizeY  = int(noOfLines * fontSize * 1.3)
    textFont  = ImageFont.truetype("PythonScreenShotFont.ttf",fontSize)
    
    # create image and draw space, set origin    
    img       = Image.new('RGB', (imgSizeX,imgSizeY), color = (73, 109, 137))
    drawSpace = ImageDraw.Draw(img)
    dOriginX  = 20
    dOriginY  = 20
    
    # write the text, adjust line spacing
    for i in range(noOfLines):
        drawSpace.text((dOriginX,dOriginY + int(i*fontSize*1.2)),lineList[i],font=textFont,fill=(255,255,0))

    # save image
    img.save('SCREENSHOT.PNG')

# --------------------------------------------------------------------------- #
# forge a screenshot for a RIGOL DP832 power supply - not needed anymore      #
# --------------------------------------------------------------------------- #
def GetRigolDP832DeviceScreenShot(instr):

    # collect the status of all channels
    statusList      = []
    setVoltageList  = []
    setCurrentList  = []
    msrVoltageList  = []
    msrCurrentList  = []
    msrPowerList    = []
    for i in range(3):
      statusList.append(instr.query('OUTP? CH' + str(i+1),delay=0.2).rstrip('\n').rstrip('\r')) 
      result = instr.query('APPL? CH' + str(i+1),delay=0.2).rstrip('\n').rstrip('\r').split(',')
      setVoltageList.append(float(result[1]))
      setCurrentList.append(float(result[2]))
      result = instr.query('MEAS:ALL? CH' + str(i+1),delay=0.2).rstrip('\n').rstrip('\r').split(',')
      msrVoltageList.append(float(result[0]))
      msrCurrentList.append(float(result[1]))
      msrPowerList.append(float(result[2]))

    # OK, now we need to create a bitmap with some fitting heuristics
    fontSize  = 64
    maxLen    = 20
    noOfLines = 7
    imgSizeX  = int(maxLen * fontSize * 0.75) + 20
    imgSizeY  = int(noOfLines * fontSize * 1.3)
    textFont  = ImageFont.truetype("PythonScreenShotFont.ttf",fontSize)

    # create image and draw space, set origin    
    img       = Image.new('RGB', (imgSizeX,imgSizeY), color = (73, 109, 137))
    drawSpace = ImageDraw.Draw(img)
    dOriginX  = 20
    dOriginY  = 20
    dBlockShift = 5

    # write the text, adjust line spacing
    for i in range(3):
        drawSpace.text((dOriginX + int(i*dBlockShift*fontSize),dOriginY)             ,' CH' + str(i+1)                          ,font=textFont,fill=(255,255,0))
        drawSpace.text((dOriginX + int(i*dBlockShift*fontSize),dOriginY + 1*fontSize),' ' + statusList[i]                       ,font=textFont,fill=(255,255,0))
        drawSpace.text((dOriginX + int(i*dBlockShift*fontSize),dOriginY + 2*fontSize +30),str(round(setVoltageList[i],3)) + 'V' ,font=textFont,fill=(255,255,0))
        drawSpace.text((dOriginX + int(i*dBlockShift*fontSize),dOriginY + 3*fontSize +30),str(round(setCurrentList[i],3)) + 'A' ,font=textFont,fill=(255,255,0))
        drawSpace.text((dOriginX + int(i*dBlockShift*fontSize),dOriginY + 4*fontSize +60),str(round(msrVoltageList[i],3)) + 'V' ,font=textFont,fill=(255,255,0))
        drawSpace.text((dOriginX + int(i*dBlockShift*fontSize),dOriginY + 5*fontSize +60),str(round(msrCurrentList[i],3)) + 'A' ,font=textFont,fill=(255,255,0))
        drawSpace.text((dOriginX + int(i*dBlockShift*fontSize),dOriginY + 6*fontSize +90),str(round(msrPowerList[i],3))   + 'W' ,font=textFont,fill=(255,255,0))
    # save image
    img.save('SCREENSHOT.PNG')

# --------------------------------------------------------------------------- #
# forge a screenshot for a Keysight U2004A Power Sensor                       #
# --------------------------------------------------------------------------- #
def GetKeysightU2004ADeviceScreenShot(instr):

    global hadU2004AReset
    
    # this is a special part full of bugs and timeouts.
    if not hadU2004AReset: 
        instr.write('*RST')
        sleep(7.)
        instr.timeout = 25000.
        instr.write(':CAL')
        asnwer = instr.query('*OPC?')
        hadU2004AReset = True   
    try:
        instr.write('*CLS')
        instr.write(':INIT:CONT ON')
        sleep(1)        
        result = float(instr.query(':FETCH?',delay=1))
    except:
        # try again. this behaviour could be due to an autocalibration 
        try:
            instr.write('*CLS')
            instr.write(':INIT:CONT ON')
            sleep(1)
            result = float(instr.query(':FETCH?',delay=1))
        except:
            pass

    # OK, now we need to create a bitmap with some fitting heuristics
    fontSize  = 64
    maxLen    = 12
    noOfLines = 1
    imgSizeX  = int(maxLen * fontSize * 0.75) + 20
    imgSizeY  = int(noOfLines * fontSize * 1.3)
    textFont  = ImageFont.truetype("PythonScreenShotFont.ttf",fontSize)
    
    # create image and draw space, set origin    
    img       = Image.new('RGB', (imgSizeX,imgSizeY), color = (73, 109, 137))
    drawSpace = ImageDraw.Draw(img)
    dOriginX  = 20
    dOriginY  = 20
    
    # write the text
    drawSpace.text((dOriginX,dOriginY),str(round(result,5)) + ' dBm',font=textFont,fill=(255,255,0))
    
    # save image
    img.save('SCREENSHOT.PNG')

# =========================================================================== #
# VISA routines go here                                                       #
# =========================================================================== #

# --------------------------------------------------------------------------- #
# get all VISA resources responding to a *IDN? query                          #
# --------------------------------------------------------------------------- #
def GetVisaSCPIResources():

    # enumerate all resources VISA finds
    rm                  = pyvisa.ResourceManager()
    resourceList        = rm.list_resources()
    availableVisaIdList = []
    availableNameList   = []

    # go thru this list and ask an *IDN? to see what instrument it is
    for i in range(len(resourceList)):
        resourceReply = ''
        try:
            if (resourceList[i][:4] == 'ASRL'):         # serial resource
                instrument          = rm.open_resource(resourceList[i],
                                                        timeout=2000,
                                                        access_mode=1)
                # instrument.lock_excl()
                resourceReply       = instrument.query('*IDN?').upper()
            else:
                instrument          = rm.open_resource(resourceList[i])
                resourceReply       = instrument.query('*IDN?').upper()
            if (resourceReply != ''):
                availableVisaIdList.append(resourceList[i])
                availableNameList.append(resourceReply)
        except:
            pass
            
    return availableVisaIdList, availableNameList

# --------------------------------------------------------------------------- #
# send a SCPI command                                                         #
# --------------------------------------------------------------------------- #
def SendScpiCommand(visaId,commandString):

    # first connect to the instrument
    instr = rm.open_resource(visaId,chunk_size=8000,timeout=20000)

    try:
        instr.write(commandString)
        return 'OK'
    except:
        return 'SCPI Error'

# --------------------------------------------------------------------------- #
# send a SCPI query                                                           #
# --------------------------------------------------------------------------- #
def SendScpiQuery(visaId,commandString):

    # first connect to the instrument
    instr = rm.open_resource(visaId,chunk_size=8000,timeout=20000)

    try:
        result = instr.query(commandString,delay=0.5)
        return result
    except:
        return 'SCPI Error'

class ScreenShotDialog(QDialog):
    # static members
    pythonScreenShotVisaId1 = ''
    pythonScreenShot1       = ''
    visaIdList              = []
    nameList                = []
    imgFileName             = ''

    # ----------------------------------------------------------------------- #    
    def __init__(self, parent= None):
        super().__init__(parent)
        self.setWindowTitle("Screenshot Dialog")
        self.initUI()
        
    # ----------------------------------------------------------------------- #         
    def initUI(self):
         
        # init geometry
        xOrigin                     = 20
        yOrigin                     = 20
        spanLabelX                  = 20
        spanFieldX                  = 100
        spanLabelY                  = 20
        spanFieldY                  = 50
        fieldRows                   = 4
        fieldColumns                = 8
        xSpanGroup                  = 130

        # create top headers
        self.headerTopZ = QLabel('V1.3 2020/06',self);
        self.headerTopZ.move(10,10)
        self.headerTopZ.setFont(QFont("Tahoma",12, QFont.Bold))
        self.headerTopS = QLabel('PYTHON SCPI SCREENSHOT',self);
        self.headerTopS.move(xOrigin + xSpanGroup, yOrigin + 2)
        self.headerTopS.setFont(QFont("Tahoma",18, QFont.Bold))
        yOrigin = yOrigin + 60
 
        # create find button 
        self.doFindButton = QPushButton('Find Instruments', self)
        self.doFindButton.move(xOrigin + 0*xSpanGroup, yOrigin)
        self.doFindButton.clicked.connect(self.doFind)

        # create SCPI dino label
        self.scpiDinoLabel = QLabel('',self)
        self.scpiDinoLabel.move(xOrigin + 3*xSpanGroup, yOrigin-20)
        self.scpiDinoPixMap = QPixmap('SCPILogoDinosaur.png')
        self.scpiDinoLabel.setPixmap(self.scpiDinoPixMap)
        self.scpiDinoLabel.show()

        # create list box of all VISA instrument names found
        yOriginInstr = yOrigin + 50
        xOriginInstr = xOrigin
        self.labelStatic = QLabel('Available VISA Instruments',self)
        self.labelStatic.move(xOriginInstr, yOriginInstr)
        self.labelStatic.setFont(QFont("Tahoma",12, QFont.Bold))
        self.instrTable = QTableWidget(self)
        self.instrTable.setRowCount(0)
        self.instrTable.setColumnCount(4)
        self.instrTable.setHorizontalHeaderLabels(['Name','Description','Manufacturer','VISA ID'])
        self.instrTable.setEditTriggers(QTableWidget.NoEditTriggers)
        self.instrTable.setSelectionMode(QTableWidget.SingleSelection)
        self.instrTable.setSelectionBehavior(QTableWidget.SelectRows)
        # self.instrTable.setSortingEnabled(False)
        self.instrTable.move(xOriginInstr,yOriginInstr + 30)
        self.instrTable.setFixedSize(500,450)

        # create screenshot label
        xOriginGraph = xOrigin + 520
        yOriginGraph = yOrigin
        self.screenshotLabel = QLabel('',self)
        self.screenshotLabel.move(xOriginGraph, yOriginGraph - 50)
        pixMap = QPixmap(1024,800)
        self.screenshotLabel.setPixmap(pixMap)
        self.screenshotLabel.show()
     
        # create refresh button
        xOriginRefreshButtons = xOrigin
        yOriginRefreshButtons = yOrigin + 570
        self.doRefreshButton = QPushButton('Get Screen', self)
        self.doRefreshButton.move(xOriginRefreshButtons, yOriginRefreshButtons)
        self.doRefreshButton.clicked.connect(self.doSetRefresh)

        # create autorefresh button
        self.doAutoRefreshButton = QPushButton('Auto Refresh', self)
        self.doAutoRefreshButton.setCheckable(True)
        self.doAutoRefreshButton.setChecked(False)
        self.doAutoRefreshButton.move(xOriginRefreshButtons + xSpanGroup, yOriginRefreshButtons)
        self.doAutoRefreshButton.clicked.connect(self.doSetAutoRefresh)

        # create autorefresh period entry field
        self.labelAutoRefPeriod = QLabel('Auto Refresh Period (ms)',self)
        self.labelAutoRefPeriod.move(xOriginRefreshButtons + 2*xSpanGroup,yOriginRefreshButtons-15)
        self.autoRefPeriodEntry = QLineEdit(self);
        self.autoRefPeriodEntry.setText('1000')
        self.autoRefPeriodEntry.move(xOriginRefreshButtons + 2*xSpanGroup,yOriginRefreshButtons)

        # create save button
        self.doSaveButton = QPushButton('Save to ...', self)
        self.doSaveButton.move(xOriginRefreshButtons + 3*xSpanGroup + 30, yOriginRefreshButtons)
        self.doSaveButton.clicked.connect(self.doSave)
        
        # create clear button
        xOriginCmdButtons = xOrigin
        yOriginCmdButtons = yOriginRefreshButtons + 50
        self.doSendClearButton = QPushButton('Clear Error', self)
        self.doSendClearButton.move(xOriginCmdButtons, yOriginCmdButtons)
        self.doSendClearButton.clicked.connect(self.doSendClear)

        # create reset button
        self.doSendResetButton = QPushButton('Send Reset', self)
        self.doSendResetButton.move(xOriginCmdButtons + xSpanGroup, yOriginCmdButtons)
        self.doSendResetButton.clicked.connect(self.doSendReset)

        # create get last error button
        self.doGetLastErrorButton = QPushButton('Get Last Error', self)
        self.doGetLastErrorButton.move(xOriginCmdButtons + 2*xSpanGroup, yOriginCmdButtons)
        self.doGetLastErrorButton.clicked.connect(self.doSendGetLastError)
        
        # create RUN button
        self.doRunButton = QPushButton('Send Run', self)
        self.doRunButton.move(xOriginCmdButtons + 3*xSpanGroup + 30,yOriginCmdButtons)
        self.doRunButton.clicked.connect(self.doRun)
        
        # create send command button
        xOriginScpiButtons = xOrigin
        yOriginScpiButtons = yOriginCmdButtons + 50
        self.doSendCommandButton = QPushButton('Send Command', self)
        self.doSendCommandButton.move(xOriginScpiButtons, yOriginScpiButtons)
        self.doSendCommandButton.clicked.connect(self.doSendCommand)

        # create command entry field
        self.labelScpiCommand = QLabel('SCPI Command Text',self)
        self.labelScpiCommand.move(xOriginScpiButtons + xSpanGroup,yOriginScpiButtons-15)
        self.scpiCommandEntry = QLineEdit(self);
        self.scpiCommandEntry.setText('')
        self.scpiCommandEntry.move(xOriginScpiButtons + xSpanGroup,yOriginScpiButtons)
        self.scpiCommandEntry.resize(370,20)
        
        # create SCPI Reply field
        xOriginScpiReply = xOrigin
        yOriginScpiReply = yOriginScpiButtons + 50
        self.labelScpiReplyStatic = QLabel('Last SCPI Reply',self)
        self.labelScpiReplyStatic.move(xOriginScpiReply,yOriginScpiReply)
        self.labelScpiReply = QLabel('*None*',self)
        self.labelScpiReply.move(xOriginScpiReply + xSpanGroup,yOriginScpiReply)
        self.labelScpiReply.resize(370,20)
       
        # size main windows, show it      
        self.setGeometry(300, 300, 1600,850)
        self.setWindowTitle('DL1DWG Python Screenshot GUI V1.0 2020/04 (C) DL1DWG under GPL V3')
        self.show()

    # ----------------------------------------------------------------------- #
    def doFind(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.doAutoRefreshButton.setChecked(False)
        try:
            self.instrTable.clear()
            self.instrTable.setHorizontalHeaderLabels(['Name','Description','Manufacturer','VISA ID'])
            self.visaIdList, self.nameList = GetVisaSCPIResources()
            self.instrTable.setRowCount(len(self.nameList))
            for i in range(len(self.nameList)):
                nameListComps = self.nameList[i].split(',')
                mfgName       = nameListComps[0].strip()
                instrName     = nameListComps[1].strip()
                serialNo      = nameListComps[2].strip()
                versionText   = nameListComps[3].strip()
                instrType     = GetInstrumentTypeFromName(instrName)
                self.instrTable.setItem(i,0,QTableWidgetItem(instrName))
                self.instrTable.setItem(i,1,QTableWidgetItem(instrType))
                self.instrTable.setItem(i,2,QTableWidgetItem(mfgName))
                self.instrTable.setItem(i,3,QTableWidgetItem(self.visaIdList[i]))
            QApplication.restoreOverrideCursor()
        except:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("No Instruments  found.")
            msg.setInformativeText('See Log for More information')
            msg.setWindowTitle("Error")
            msg.exec_()            
        QApplication.restoreOverrideCursor()
        return    
   
    # ----------------------------------------------------------------------- #
    def doSetRefresh(self):
        itemList = self.instrTable.selectedItems()
        if len(itemList) == 0:
            self.doAutoRefreshButton.setChecked(False)
            return
        instrName = itemList[0].text().strip()
        instrType = itemList[1].text().strip()
        visaId    = itemList[3].text().strip()
        if instrType == '':
            # complain
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.imgFileName = GetScreenShot(instrType,visaId)
            self.screenshotPixMap = QPixmap(self.imgFileName)
            self.screenshotLabel.setPixmap(self.screenshotPixMap)
            self.screenshotLabel.show()
            QApplication.restoreOverrideCursor()
        except:
            self.doAutoRefreshButton.setChecked(False)
            QApplication.restoreOverrideCursor()
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("SCPI Error")
            msg.setInformativeText('See Log for More information')
            msg.setWindowTitle("Error")
            msg.exec_()            
        return

    # ----------------------------------------------------------------------- #
    def doSendClear(self):
        itemList = self.instrTable.selectedItems()
        if len(itemList) == 0:
            self.doAutoRefreshButton.setChecked(False)
            return
        instrName = itemList[0].text().strip()
        instrType = itemList[1].text().strip()
        visaId    = itemList[3].text().strip()
        if instrType == '':
            # complain
            return
        self.doAutoRefreshButton.setChecked(False)
        SendScpiCommand(visaId,'*CLS')
        self.labelScpiReply.setText('')
        return

    # ----------------------------------------------------------------------- #
    def doSendReset(self):
        itemList = self.instrTable.selectedItems()
        if len(itemList) == 0:
            self.doAutoRefreshButton.setChecked(False)
            return
        instrName = itemList[0].text().strip()
        instrType = itemList[1].text().strip()
        visaId    = itemList[3].text().strip()
        if instrType == '':
            # complain
            return
        self.doAutoRefreshButton.setChecked(False)
        SendScpiCommand(visaId,'*RST')
        self.labelScpiReply.setText('')
        return

    # ----------------------------------------------------------------------- #
    def doRun(self):
        itemList = self.instrTable.selectedItems()
        if len(itemList) == 0:
            self.doAutoRefreshButton.setChecked(False)
            return
        instrName = itemList[0].text().strip()
        instrType = itemList[1].text().strip()
        visaId    = itemList[3].text().strip()
        if instrType == '':
            # complain
            return
        result = SendScpiCommand(visaId,':RUN')
        return

    # ----------------------------------------------------------------------- #
    def doSendGetLastError(self):
        itemList = self.instrTable.selectedItems()
        if len(itemList) == 0:
            self.doAutoRefreshButton.setChecked(False)
            return
        instrName = itemList[0].text().strip()
        instrType = itemList[1].text().strip()
        visaId    = itemList[3].text().strip()
        if instrType == '':
            # complain
            return
        self.doAutoRefreshButton.setChecked(False)
        result = SendScpiQuery(visaId,':SYST:ERR?')
        self.labelScpiReply.setText(result)
        return

    # ----------------------------------------------------------------------- #
    def doSendCommand(self):
        itemList = self.instrTable.selectedItems()
        if len(itemList) == 0:
            self.doAutoRefreshButton.setChecked(False)
            return
        instrName = itemList[0].text().strip()
        instrType = itemList[1].text().strip()
        visaId    = itemList[3].text().strip()
        if instrType == '':
            # complain
            return
        self.doAutoRefreshButton.setChecked(False)
        cmdText = self.scpiCommandEntry.text().strip()
        if (len(cmdText) > 0):
            cmdTextParts = cmdText.split(' ')
            if cmdTextParts[0].endswith('?'):
                result = SendScpiQuery(visaId,cmdText)
                self.labelScpiReply.setText(result)
            else:
                result = SendScpiCommand(visaId,cmdText)
        return

    # ----------------------------------------------------------------------- #
    def doSetAutoRefresh(self):
        self.interval = min(10000.,max(200.,int(self.autoRefPeriodEntry.text())))
        if self.doAutoRefreshButton.isChecked():
            self.timer = QTimer()
            # self.timer.setSingleShot(True)
            self.timer.setInterval(self.interval)
            self.timer.timeout.connect(self.sendRefMsg)
            self.timer.start()            
        else:
            self.timer.stop()
        return

    def sendRefMsg(self):
        self.doSetRefresh()
        return

    # ----------------------------------------------------------------------- #
    def doSave(self):
        options         = QFileDialog.Options()
        newFileName, _  = QFileDialog.getSaveFileName(self,"Save Screenshot as ...","","Image Files (*.png *.bmp *.jpg)", options=options)
        if newFileName:
            # copy last file to the name and path specified
            shutil.copy(self.imgFileName,newFileName)
        return

if __name__ == "__main__":
    app = QApplication(sys.argv)

    win = ScreenShotDialog()
    win.setWindowFlags(
        Qt.Window
        | Qt.WindowMinimizeButtonHint
        | Qt.WindowMaximizeButtonHint
        | Qt.WindowCloseButtonHint
    )
    win.show()

    sys.exit(app.exec())