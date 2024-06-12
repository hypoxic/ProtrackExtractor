#!/usr/bin/env python

# ProtrackII jump data extractor. 
# Trunk 2023

# Based on code from 
#   https://github.com/damjandakic93/ProtrackReader
#   and "Skydive Logbook" from Freefall Bits

import csv
import os
import sys
import re
import math
from datetime import datetime

# Extracted from freefallbits Skydiver Logbook. 
#  Assuming they got some help from LB. Says open source, but 
#  was not able to find the repository. Extracted these 
#  constants from the .net files. 
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
	return 44330.8 * (1.0 - pow(p / 10132.5, 0.190263)) - GroundLevelMeter

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
        
    # Some data lines not deciphered. Perhaps protocol versions?   
    FileVersionFormat = lined[1]      # 1.00
    Device = lined[2]                 # 1 - Device:1=PROTRACK2 or 2=UnKnown
    ProTrack2Version = lined[3]       # 1.00  # ProTrack2 firmware version format: XX.xx
        
    # Extract information from protrackii txt file
    #  Data deliminted by line number.
    AltiMeterList   = []
    SpeedList       = []
    SasSpeedList    = []
    AccelList       = []   
    SasMeterList    = []
    SerialNumber    = lined[4]          # ProTrack2 Serial Number: YYMMDDHHMMSS
    JumpNumber      = int(lined[5])     # JumpNumber: Range 0-99999 
    datestr         = str("%s%s" % (lined[6],lined[7]))
    datetime_object = datetime.strptime(datestr, '%Y%m%d%H%M%S')
    ExitAltitude    = int(lined[8])
    DeploymentAltitude = int(lined[9])
    FreefallTime    = int(lined[10])
    AverageSpeed    = int(lined[11])
    MaxSpeed        = int(lined[12])
    FirstHalfSpeed  = int(lined[14])
    SecondHalfSpeed = int(lined[15])
    GroundLeveldPa  = int(lined[35])
    profileExists   = int(lined[36])     
    canopyDataInProfile = int(lined[37])  
    profilePoints   = int(lined[38]) 
    JumpData        = ''.join(lined[39:lines-1]).split(",")
    JumpData.pop()  # remove last element
    JumpDataInt     = list(map(int, JumpData)) # convert strings to meters
    GroundLevelmbar = DecaPaToMiliBar(GroundLeveldPa) # Pressure at ground level. 
    GroundLevelMeter = (int)(44330.8 * (1.0 - pow(GroundLeveldPa / 10132.5, 0.190263)))

    i = 0
    DeploymentIndex = -1
    
    exit_dbar = JumpDataInt[IndexSpeedStart]
    IcaoTempC = round(15-(44330.8*(1- pow((exit_dbar/10132.5),0.190263))*0.0065))
    icao_div = IcaoTempC # incase Fahrenheit
    hs = (44330.8*(1-pow((GroundLeveldPa/10132.5),0.190263)))
    ht = (44330.8*(1-pow((GroundLeveldPa/10132.5),0.190263)))*(1+((icao_div)*0.004));
    
    print("exit_dbar: %0.1f dpa" % exit_dbar)
    print("hs: %0.1f meter" % hs)
    print("ht: %0.1f meter" % ht)
    print("IcaoTempC: %0.1fC\n" % IcaoTempC)
        
    for readingDBar in JumpDataInt:
        alti = PressureToMeter(readingDBar, GroundLevelMeter)
        AltiMeterList.append(alti)
                
        # SAS meter table
        sasmeter = (44330.8*(1 - pow((readingDBar/10132.5),0.190263)))*(1+(icao_div*0.004))+(hs-ht)+GroundLevelMeter
        SasMeterList.append(sasmeter)
        
        #set deployment index
        if alti <= DeploymentAltitude and DeploymentIndex == -1:
            DeploymentIndex = i
        
        #speed calculations
        if i < IndexSpeedStart:    
            SpeedList.append(0.0)   
            SasSpeedList.append(0.0) 
        elif alti > DeploymentAltitude:
            # setup the contants for SAS as per LB's code                
            speed = (AltiMeterList[i -IndexIncForSpeedInFF] - alti) / TimeIncForSpeedInFF
            SpeedList.append(speed)
            
            # Now calculate SAS
            SasSpeed = (SasMeterList[i -IndexIncForSpeedInFF] - sasmeter) / TimeIncForSpeedInFF
            SasSpeedList.append(SasSpeed)
        else:
            speed = (AltiMeterList[i -IndexIncForSpeedCanopy] - alti) / TimeIncForSpeedCanopy
            SpeedList.append(speed)
            
            SasSpeed = (SasMeterList[i -IndexIncForSpeedCanopy] - sasmeter) / TimeIncForSpeedCanopy
            SasSpeedList.append(SasSpeed)
        i+=1
        
    # Calculate acceleration             
    i = 0        
    for alti in AltiMeterList:
        if i < IndexSpeedStart:
            AccelList.append(0.0)
        elif round(AltiMeterList[i]) == 0:
            AccelList.append(0.0)
        else:        
            AccelList.append( (MsecToMsec(SpeedList[i]) - MsecToMsec(SpeedList[i-1])) / TimeStep / A_GRAVITY )
        i+=1

    # print the data we don't care about
    print("Timestamp: %s" % str(datetime_object))
    print("JumpNumber: %d" % JumpNumber)
    print("SerialNumber: %s" % SerialNumber)
    print("ExitAltitude: %dm %dft" % (ExitAltitude, MToft(ExitAltitude)))
    print("DeploymentAltitude: %dm %dft" % (DeploymentAltitude,MToft(DeploymentAltitude)))
    print("FreefallTime: %dsec" % (FreefallTime))
    print("AverageSpeed: %dmph" % MsecTomph(AverageSpeed))
    print("MaxSpeed: %dmph" % MsecTomph(MaxSpeed))
    print("FirstHalfSpeed: %dmph" % MsecTomph(FirstHalfSpeed))
    print("SecondHalfSpeed: %dmph" % MsecTomph(SecondHalfSpeed))
    print("GroundLevelMeter: %0.1f" % GroundLevelMeter)
    
    # Write it out
    if not outf:
        outf = str("%s.csv" % JumpNumber)
    with open(outf, 'w') as csvfile:     
        csvfile.write(str("Time(s),Altitude(ft),TAS(mph),SAS LB(mph),Comments\n") )
        for i in range(0,len(AltiMeterList)):
            t       = IndexToTime(i)
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

if __name__ == "__main__":
    main()