# ProtrackExtractor
 Extracts a jump's altitude profile data from a ProtrackII and creates a CSV file with the respective data. This data is good for Full Break Sequentials where you want to ensure the fall rate remains constant between points and attempts. Works even when in Skyvan's where obtaining GPS signals does not work until late on the dive. 
   
This is useful to understand the commponents of ProtrackII's data file. 

Run with Python3 and specify the input txt file. Example:   
python extract.py testdata\370.txt testdata\AABW_TBS80Way_J2_DanBC.csv   

See AABW_TBS80Way_J2_DanBC.csv for sample data. 

Based on / extracted code from:   
* Skydiving Logbook from Freefall Bits https://www.facebook.com/freefallbits   
* Protrack Reader https://github.com/damjandakic93/ProtrackReader

ToDo:   
* Convert speed to SAS   
"The SAS formula calculates airspeed (using the same metrics used with TAS) frommeasurements of air pressure and temperature and converted to a fixed air pressure(875.3 mb) and a fixed temperature (+7.080C) which corresponds to 4,000 feet MSL.4,000 feet is chosen as the reference altitude by LB ALTIMETERS since this is theaverage altitude at which the working time of a skydive is normally ended"
