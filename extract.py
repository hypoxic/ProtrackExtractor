#!/usr/bin/env python

# ProtrackII jump data extractor. 
# Trunk 2024

# Based on code from 
#   https://github.com/damjandakic93/ProtrackReader
#   and "Skydive Logbook" from Freefall Bits
#   Thank you to Daniel Gomez for the special help on calculating LB's SAS

import csv
import os
import sys
import re
import math
from datetime import datetime

# Constants
TimeStep = 0.25
TimeInitial = -2.0
TimeSpeedStarts = 6.0
TimeIncForSpeedInFF = 6.0
TimeIncForSpeedCanopy = 3.0
IndexExit = (int)((0.0 - TimeInitial) / TimeStep)
IndexIncForSpeedInFF = 24
IndexIncForSpeedCanopy = 12 
A_GRAVITY   = 9.80665     # Standard acceleration due to gravity (m/s^2)
SL_PRESSURE = 101325      # Sea level pessure (Pa)
SL_PRESSURE_DPA = 10132.5
BARO_POWER  = 0.190263
STANDARD_TEMP_k = 44330.8

SL_DENSITY  = 1.225       # Sea level density (kg/m^3)
LAPSE_RATE  = 0.0065      # Temperature lapse rate (K/m)
SL_TEMP     = 288.15      # Sea level temperature (K)
MM_AIR      = 0.0289644   # Molar mass of dry air (kg/mol)
GAS_CONST   = 8.31447     # Universal gas constant (J/mol/K)

# From Mike Cooper's post at
#  https://groups.google.com/g/flysight-devs/c/-J4KIcQ5ELs?pli=1
def AirPressure(alti):
    airPressure = SL_PRESSURE * pow(1 - LAPSE_RATE * alti / SL_TEMP, A_GRAVITY * MM_AIR / GAS_CONST / LAPSE_RATE)
    return airPressure
    
def TempAtAltitude(alti):
    temperature = SL_TEMP - LAPSE_RATE * alti
    return temperature
    
def AirDensity(alti):
    airDensity = AirPressure(alti) / (GAS_CONST / MM_AIR) / TempAtAltitude(alti)
    return airDensity
    
#     
def TasToEas4K(alti, speed):
    Eas = float(speed) * math.sqrt(AirDensity(alti) / 0.934)  # 4000ft, 7.080, 875.3, 25 dewpoint
    return Eas
    
def TasToEas(alti, speed):
    Eas = float(speed) * math.sqrt(AirDensity(alti) / SL_DENSITY)
    return Eas    
    
# From flysite 
# https://github.com/flysight/flysight-viewer-qt/blob/9427b7d33abf6343a38f637f83da8797d6635472/src/ubx.cpp#L23
mSasTable = [1024, 1077, 1135, 1197, 1265, 1338, 1418, 1505, 1600, 1704, 1818, 1944]
   
def SpeedMultiplier(hMSL):    
    if (hMSL < 0):
        speed_mul = mSasTable[0]
    elif hMSL >= 11534336:
        speed_mul = mSasTable[11]
    else:
        h = hMSL / 1024
        i = int(h / 1024)
        j = h % 1024
        y1 = mSasTable[i]
        y2 = mSasTable[i + 1]
        speed_mul = y1 + ((y2 - y1) * j) / 1024
    return speed_mul    
    
def TasToSas(alti, speed):    
    speed = speed * SpeedMultiplier(alti) / 1000
    return speed

####
def IndexToTime(i):
    return TimeStep * float(i) + TimeInitial;

def TimeToIndex(time):
    return (int)((time - TimeInitial) / TimeStep);

def TimeMSToIndex(time):
    return (int)((time - TimeInitial) / (TimeStep * 1000.0));

IndexSpeedStart = TimeToIndex(TimeSpeedStarts)
    
def MiliBarToDecaPa(p):
    return p * 10.0    

def DecaPaToMiliBar(p):
    return p / 10.0    

def MsecTokmh(m):
    return round(m * 3.6)
    
def MsecTomph(m):
    return round(m * 2.23694)

def MToft(m):
    return round(m * 3.28084)   
    
def MsecToftsec(m):
    return round(m * 3.28084)
    
def MsecToMsec(m):
    return round(m) 
       
def PressureToMeter(p, GroundLevelMeter):
	return STANDARD_TEMP_k * (1.0 - pow(p / SL_PRESSURE_DPA, BARO_POWER)) - GroundLevelMeter

# Based on LB's Calculation. Assume 15C at sea level
def PressureToTemp15C(p, GroundLeveldPa):
    return (15 - (p + GroundLeveldPa)*0.0065)

#
# Main
#     
def main():
    if len(sys.argv) < 2:
        print("Missing arguments: %s <input.txt> <output>" % sys.argv[0])
        sys.exit()
        
    inf= sys.argv[1]   
    if len(sys.argv) < 3: 
        outf = None
    else:
        outf = sys.argv[2]
    
    if(not os.path.isfile(inf)):
        print("Input file \"%s\" does not exist" % inf)
        sys.exit(1)
    
    # Reading in file
    lined = []
    with open(inf) as f:
        for line in f:
            line = line.replace('\n','')
            lined.append(line)
        
    lines = len(lined)   

    if not lines or not "JIB" in lined[0]:
        print("Error: Not ProTrackII file")
        sys.exit(1)
    if not "PIE" in lined[lines-1]:  
        print("Error: Not ProTrackII profile does not exist PIE \"%s\"" % lined[lines-1])
        sys.exit(1)  
    if not "JIE" in lined[33]:  
        print("Error: Not ProTrackII profile does not exist JIE \"%s\"" % lined[33])
        sys.exit(1)  
    if not "PIB" in lined[34]:  
        print("Error: Not ProTrackII profile does not exist JIE \"%s\"" % lined[34])
        sys.exit(1)  
        
    # Lists
    AltiMeterList   = []
    SpeedList       = []
    SasSpeedList    = []
    AccelList       = []   
    SasMeterList    = []
    i = 0
    DeploymentIndex = -1        
        
    # Extract information from protrackii txt file
    #  Data deliminted by line number.
    FileVersionFormat = lined[1]      # 1.00
    Device          = lined[2]                 # 1 - Device:1=PROTRACK2 or 2=UnKnown
    ProTrack2Version = lined[3]       # 1.00  # ProTrack2 firmware version format: XX.xx
    SerialNumber    = lined[4]          # ProTrack2 Serial Number: YYMMDDHHMMSS
    JumpNumber      = int(lined[5])     # JumpNumber: Range 0-99999 
    datestr         = str("%s%s" % (lined[6],lined[7]))
    datetime_object = datetime.strptime(datestr, '%Y%m%d%H%M%S')
    ExitAltitude    = int(lined[8])     # Exit Altitude: Range 0-99999 in metre
    DeploymentAltitude = int(lined[9])  # Deployment Altitude: Range 0-99999 in metre
    FreefallTime       = int(lined[10]) # Range 0-999 in seconds
    
    TASAverageSpeed    = int(lined[11]) # TAS Average Speed: Range 0-999 in m/s        
    TASMaxSpeed        = int(lined[12]) # TAS Max. Speed: Range 0-999 in m/s           
    TASMinSpeed        = int(lined[13]) # TAS Min. Speed: Range 0-999 in m/s           
    TASFirstHalfSpeed  = int(lined[14]) # TAS First Half Speed: Range 0-999 in m/s     
    TASSecondHalfSpeed = int(lined[15]) # TAS Second Half Speed: Range 0-999 in m/s    
    
    SASAverageSpeed    = int(lined[16]) # SAS Average Speed: Range 0-999 in m/s
    SASMaxSpeed        = int(lined[17]) # SAS Max. Speed: Range 0-999 in m/s
    SASMinSpeed        = int(lined[18]) # SAS Min. Speed: Range 0-999 in m/s
    SASFirstHalfSpeed  = int(lined[19]) # SAS First Half Speed: Range 0-999 in m/s
    SASSecondHalfSpeed = int(lined[20]) # SAS Second Half Speed: Range 0-999 in m/s
    
    TempC = int(lined[21])/10  # Temperature in Celsius (C)
    
    DiveType = int(lined[22])  # Dive Type: Range 0-20
    
    LL1 = int(lined[23]) # Lookup line 1: Range 0-999999
    LL2 = int(lined[24]) # Lookup line 2: Range 0-999999
    LL3 = int(lined[25]) # Lookup line 3: Range 0-999999
    LL4 = int(lined[26]) # Lookup line 4: Range 0-999999
    LL5 = int(lined[27]) # Lookup line 5: Range 0-999999
    
    RFU1 = int(lined[28]) # (Reserved Future Use)
    RFU2 = int(lined[29])
    RFU3 = int(lined[30])
    RFU4 = int(lined[31])
    RFU5 = int(lined[32])
    
    JIE = lined[33]  # JIE Jump Information End
    PIB = lined[34]  # Profile Information Begin:
    
    GroundLeveldPa  = int(lined[35])
    profileExists   = int(lined[36])     
    canopyDataInProfile = int(lined[37])  
    profilePoints   = int(lined[38]) 
    JumpData        = ''.join(lined[39:lines-1]).split(",")
    JumpData.pop()  # remove last element
    JumpDataInt     = list(map(int, JumpData)) # convert strings to meters
    
    GroundLevelmbar = DecaPaToMiliBar(GroundLeveldPa) # Pressure at ground level. 
    GroundLevelMeter = (int)(STANDARD_TEMP_k * (1.0 - pow(GroundLeveldPa / SL_PRESSURE_DPA, BARO_POWER)))    
    exit_dbar = JumpDataInt[IndexExit]
    
    #IcaoTempC = TempC-(6.5*ExitAltitude/1000)   # Convert temperature at DZ to Temp at SeaLevel 6.5C per 1000 meter 
    IcaoTempC = round(15-(STANDARD_TEMP_k*(1- pow((exit_dbar/SL_PRESSURE_DPA),BARO_POWER))*0.0065))
    
    icao_div = IcaoTempC # incase Fahrenheit
    hs = (STANDARD_TEMP_k*(1-pow((GroundLeveldPa/SL_PRESSURE_DPA),BARO_POWER)))
    ht = (STANDARD_TEMP_k*(1-pow((GroundLeveldPa/SL_PRESSURE_DPA),BARO_POWER)))*(1+((icao_div)*0.004))
    
    """
    print("exit_dbar: %0.1f dpa" % exit_dbar)
    print("hs: %0.1f meter" % hs)
    print("ht: %0.1f meter" % ht)
    print("IcaoTempC: %0.1fC" % IcaoTempC)
    print("TempC: %0.1fC" % TempC)
    """
        
    for readingDBar in JumpDataInt:
        alti = PressureToMeter(readingDBar, GroundLevelMeter)
        AltiMeterList.append(alti)
                
        # SAS meter table
        sasmeter = (STANDARD_TEMP_k*(1 - pow((readingDBar/SL_PRESSURE_DPA),BARO_POWER)))*(1+(icao_div*0.004))+(hs-ht)+GroundLevelMeter
        SasMeterList.append(sasmeter)
        
        #set deployment index
        if alti <= DeploymentAltitude and DeploymentIndex == -1:
            DeploymentIndex = i
        
        i+=1
    
    #speed calculations
    i = 0
    for i in range(IndexExit+IndexIncForSpeedInFF, len(AltiMeterList)): 
        if AltiMeterList[i] > DeploymentAltitude:
            timeinterval = TimeIncForSpeedInFF
            idxinc       = IndexIncForSpeedInFF
        else:
            timeinterval = TimeIncForSpeedCanopy
            idxinc       = IndexIncForSpeedCanopy

        # setup the contants for SAS as per LB's code                
        speed = (AltiMeterList[i -idxinc] - AltiMeterList[i]) / timeinterval
        SpeedList.append(speed)
        
        # Now calculate SAS
        SasSpeed = (SasMeterList[i -idxinc] - SasMeterList[i]) / timeinterval
        SasSpeedList.append(SasSpeed)    
        
    # Calculate acceleration             
    i = 0        
    for i in range(1,len(SpeedList)):
        AccelList.append( (MsecToMsec(SpeedList[i]) - MsecToMsec(SpeedList[i-1])) / TimeStep / A_GRAVITY )
        i+=1

    # print the data we don't care about
    print("Timestamp: %s" % str(datetime_object))
    print("JumpNumber: %d" % JumpNumber)
    print("SerialNumber: %s" % SerialNumber)
    print("ExitAltitude: %dm %dft" % (ExitAltitude, MToft(ExitAltitude)))
    print("DeploymentAltitude: %dm %dft" % (DeploymentAltitude,MToft(DeploymentAltitude)))
    print("FreefallTime: %dsec" % (FreefallTime))
    print("SAS AverageSpeed: %dmph" % MsecTomph(SASAverageSpeed))
    print("SAS MaxSpeed: %dmph" % MsecTomph(SASMaxSpeed))
    print("SAS FirstHalfSpeed: %dmph" % MsecTomph(SASFirstHalfSpeed))
    print("SAS SecondHalfSpeed: %dmph" % MsecTomph(SASSecondHalfSpeed))
    print("GroundLevelMeter: %0.1f" % GroundLevelMeter)
    
    # Write it out
    """
    if not outf:
        outf = str("%s.csv" % JumpNumber)
    with open(outf, 'w') as csvfile:     
        csvfile.write(str("Time(s),Altitude(ft),TAS(mph),SAS LB(mph),Comments\n") )
        for i in range(0,len(AltiMeterList)):               
            t       = IndexToTime(i)
            if t<0 or t > IndexToTime(DeploymentIndex):
                continue
            alti    = AltiMeterList[i]
            tas     = SpeedList[i]
            sas     = SasSpeedList[i]
            accel   = AccelList[i]
            sasmeter = SasMeterList[i]
                        
            if(i == DeploymentIndex):
                comment = "Deployment"
            elif( i == IndexExit ):
                comment = "Exit"
            elif(t == TimeSpeedStarts):
                comment = "Speed Accurate"
            else:
                comment = ""
            csvfile.write(str("%f,%d,%0.0f,%0.0f,%s\n" % (t, MToft(alti), MsecTomph(tas), MsecTomph(sas), comment))) 
    """
    if not outf:
        outf = str("%s.csv" % JumpNumber)
    with open(outf, 'w') as csvfile:     
        csvfile.write(str("Altitude(ft),SAS(mph)\n") )
        for i in range(0,len(SasSpeedList)):               
            exitidx = TimeToIndex(0)
            
            alti    = AltiMeterList[i+exitidx+IndexIncForSpeedInFF]
            if(alti <= DeploymentAltitude):
                break
            
            tas     = SpeedList[i]
            sas     = SasSpeedList[i]
                        
            csvfile.write(str("%d,%0.0f\n" % (MToft(alti), MsecTomph(sas)))) 
            
if __name__ == "__main__":
    main()