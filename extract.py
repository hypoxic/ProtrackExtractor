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
Gravity = 9.81

def IndexToTime(i):
    return TimeStep * float(i) + TimeInitial;

def TimeToIndex(time):
    return (int)((time - TimeInitial) / TimeStep);

def TimeMSToIndex(time):
    return (int)((time - TimeInitial) / (TimeStep * 1000.0));

IndexSpeedStart = TimeToIndex(TimeSpeedStarts)
    
def MiliBarToDecaPa(p):
    return p * 10.0    

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
       
def PressureToMeter(p, groundLevelMeter):
	return 44330.8 * (1.0 - pow(p / 10132.5, 0.190263)) - groundLevelMeter

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
    #print(lined[1])    1.00
    #print(lined[2])   1
    #print(lined[3])    1.00  
        
    # Extract information from protrackii txt file
    #  Data deliminted by line number.
    JumpDataMeter   = []
    SpeedList       = []
    AccelList       = []   
    SerialNumber    = lined[4]    
    JumpNumber      = int(lined[5])
    datestr         = str("%s%s" % (lined[6],lined[7]))
    datetime_object = datetime.strptime(datestr, '%Y%m%d%H%M%S')
    ExitAltitude    = int(lined[8])
    DeploymentAltitude = int(lined[9])
    FreefallTime    = int(lined[10])
    AverageSpeed    = int(lined[11])
    MaxSpeed        = int(lined[12])
    FirstHalfSpeed  = int(lined[14])
    SecondHalfSpeed = int(lined[15])
    GroundLevel     = int(lined[35])/10.0  # Pressure at ground level. 
    profileExists   = int(lined[36])     
    canopyDataInProfile = int(lined[37])  
    profilePoints   = int(lined[38]) 
    JumpData        = ''.join(lined[39:lines-1]).split(",")
    JumpData.pop()  # remove last element
    JumpDataInt     = list(map(int, JumpData)) # convert strings to meters
    GroundLeveldPa  = MiliBarToDecaPa(GroundLevel)
    groundLevelMeter = (int)(44330.8 * (1.0 - pow(GroundLevel / 1013.25, 0.190263)))

    i = 0
    DeploymentIndex = -1
    for readingM in JumpDataInt:
        alti= PressureToMeter(readingM,groundLevelMeter)
        JumpDataMeter.append(round(alti))
        
        #set deployment index
        if alti <= DeploymentAltitude and DeploymentIndex == -1:
            DeploymentIndex = i
        
        #speed calculations
        if i < IndexSpeedStart:    
            SpeedList.append(0.0)    
        elif alti > DeploymentAltitude:
            SpeedList.append((JumpDataMeter[i -IndexIncForSpeedInFF] - alti) / TimeIncForSpeedInFF)
        else:
            SpeedList.append((JumpDataMeter[i -IndexIncForSpeedCanopy] - alti) / TimeIncForSpeedCanopy)
        i+=1
        
    # Calculate acceleration             
    i = 0        
    for alti in JumpDataMeter:
        if i < IndexSpeedStart:
            AccelList.append(0.0)
        elif round(JumpDataMeter[i]) == 0:
            AccelList.append(0.0)
        else:        
            AccelList.append( (MsecToMsec(SpeedList[i]) - MsecToMsec(SpeedList[i-1])) / TimeStep / Gravity )
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
    print("GroundLeveldPa: %0.1f" % GroundLeveldPa)
    print("GroundLevelMeter: %0.1f" % groundLevelMeter)

    # Write it out
    if not outf:
        outf = str("%s.csv" % JumpNumber)
    with open(outf, 'w') as csvfile:     
        csvfile.write(str("Time(s),Altitude(m),Altitude(ft),Speed(mph),Comments\n") )
        for i in range(0,len(JumpDataMeter)):
            t       = IndexToTime(i)
            alti    = JumpDataMeter[i]
            speed   = SpeedList[i]
            accel   = AccelList[i]
            
            if(i == DeploymentIndex):
                comment = "Deployment"
            elif( i == IndexExit ):
                comment = "Exit"
            elif(t == TimeSpeedStarts):
                comment = "Speed Accurate"
            else:
                comment = ""
            csvfile.write(str("%f,%d,%f,%f,%s\n" % (t, alti, MToft(alti), MsecTomph(speed), comment))) 

if __name__ == "__main__":
    main()