#!/usr/bin/env python3

"""
gis2wbgt.py
Read a 15-min csv file which contains all tower sites, calculate the wet bulb globe
  temperature for each time, write a simple csv file.
  The input file is the most recent 24 hours of data in the WMDC GIS24 report.
Usage: python gis2wbgt.py [-v] [-o csvfile] metfile  
  metfile is the met file to read. It is assumed to be a GIS24 report file.
Ken Waight / May 2026
"""

# ========
# IMPORTS.
# ========
import sys
import csv
from datetime import datetime, timedelta
import math
import argparse
import re
#from zoneinfo import ZoneInfo  # Not able to install.
#import pytz  # Not able to install.
import wbgt  # # Module that contains everything necessary to calculate WBGT. 

# ==============
# FUNCTIONS.
# ==============

# ==============
# MAIN PROGRAM.
# ==============
# ----------
# Constants.
# ----------
FLAG = -999.9  # Possible value for data assumed to be bad. 
T0 = 273.16  # Freezing point, K.

# ----------------------------------------------------------------
# Parse arguments.
# Get name of met file to read. There is one option:
#   1. A 15 min file containing 24 hr of data from all towers (the "GIS 24" report).
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a Weather Machine file and make a simple list of data")
parser.add_argument("metfile", help="Name of met file to read")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
parser.add_argument("-o", "--csvfile", help="Specified name of the CSV file that will be written, otherwise it will be tower2wbgt.csv")
parser.add_argument("-windobsheight", "--windobsheight", help="Wind measurement height (m)")
parser.add_argument("-windestheight", "--windestheight", help="Height of wind speed estimate (m)")

args = parser.parse_args()
metFile = args.metfile
variables = []
if args.verbosity:
    verbosity = int(args.verbosity)
else:
    verbosity = 0
print(args.verbosity, verbosity)
    
if args.csvfile:
    csvFile = args.o
else:
    csvFile = 'tower2wbgt.csv'  # Default csv file name.

# Information to estimate the wind speed at a different height than the observed height.
if args.windobsheight:
    windMeasurementHeight = float(args.windobsheight)
else:
    windMeasurementHeight = None
    
if args.windestheight:
    windEstimateHeight = float(args.windestheight)
else:
    windEstimateHeight = None

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
columnStation   = 'Station'
columnDateTime1 = 'DateTime' # WMDC download
columnDateTime2 = 'dts'       # Data request from current Weather Machine.
columnName = {}
columnName['spd1'] = 'SPD1 (MS)'
columnName['temp0'] = 'Temp0  (C)'
columnName['rh'] = 'RH'
columnName['press'] = 'PRES  (MB)'
#columnName['dewp'] = 'dewp'
#columnName['swdn'] = 'swdn'
#columnName['swup'] = 'swup'
#columnName['lwdn'] = 'lwdn'
#columnName['lwup'] = 'lwup'

# Wind speed power law exponents for each stability class (from EPA guidance).
powerLawExponentRural = {'A': 0.07, 'B': 0.07, 'C': 0.10, 'D': 0.15, 'E': 0.35, 'F': 0.55}

# Towers to process. Some towers do not have all of the necessary variables.
towers = ['TA6', 'TA54']

# =======
# Banner.
# =======
print('\n =====================================================\n',
      'Calculate wet bulb globe temperature from observed data.\n',
      '=====================================================\n')
print(*sys.argv)

# Initialize lists for all variables.
dtIn = []
dtOut = []
obsIn = {}
obsOut = {}
# Build list of variables to process.
variables = []
variables.append('SPD1')
variables.append('Temp0')
#variables.append('dewp')
#variables.append('swdn')
for var in variables:
    obsIn[var] = []
    obsOut[var] = []
csvOut = {}

# --------------------------------------------------------------------
# Read 15-minute data at one tower location.
#   Save each of the requested variables.
# --------------------------------------------------------------------
index = csvFile.find('.csv')
for tower in towers:
    print('tower:', tower, tower.lower())
    csvFileTower = csvFile[:index] + '.' + tower.lower() + csvFile[index:]
    csvOut[tower] = open(csvFileTower, 'w')
    csvOut[tower].write('dts,WBGT(C),T2m(C),Td2m,wspd10m(m/s),pSfc(mb),cloudFrac,' +
                        'swdn,swup,lwdn,lwup,Twet,Tglobe,' +
                        'T2m(F),wspd10m(mph),RH,pSfc(in Hg),WBGT(F)\n')
    print("\nReading data file:", metFile)
    
dtFirst = None
dtLast = None
dtList = []
yyyymmdds = []
nBad = 0
nDiag = 0
with open(metFile, 'r') as infile:
    towerData = csv.DictReader(infile)
    for row in towerData:
        #print('row:', row) #ktw
        try:
            tower = row[columnStation]
            row[columnDateTime1]
            columnDateTime = columnDateTime1
            #print('columnDateTime 1:', columnDateTime)
        except KeyError:
            columnDateTime = columnDateTime2
            #print('columnDateTime 2:', columnDateTime)
        if tower not in towers:
            continue
        print('\nTower:', tower)
        if (row[columnDateTime] and
            (re.search(r'^\d+-\d+-\d+ \d+:\d+:\d+', row[columnDateTime]) or
             re.search(r'^\d+-\d+-\d+ \d+:\d+', row[columnDateTime]))):
            #print('row[0]:', row[columnDateTime]) #ktw
            try:
                # Try an older formatted date.
                dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M:%S")
                #print('dt 1:', dt)
            except:
                try:
                    # Try a datalogger-formatted date.
                    dt = datetime.strptime(row[columnDateTime], "%m/%d/%Y %H:%M")
                    #print('dt 2:', dt)
                except:
                    # Try a new Weather Machine-formatted date.
                    dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M")
                    #print('dt 3:', dt)
            print('dt:', dt)
            # Save first time.
            # ----------------------------------------------------------
            # Save needed variables, set to None for missing data.
            # ----------------------------------------------------------
            # Convert local time (MST, Mountain Standard Time) to UTC.
            #   Because I don't know how to install pytz or zoneinfo, just add seven hours.
            yyyymmddhhmn = datetime.strftime(dt, '%Y%m%d%H%M')
            dtsMst = datetime.strftime(dt, '%m/%d/%Y %H:%M')
            dtUtc = dt + timedelta(hours=7)
            yyyymmddhhmnUtc = datetime.strftime(dtUtc, '%Y%m%d%H%M')
            try:
                T2mC = float(row['Temp0  (C)'])
                #print('T2mC:', T2mC) #ktw
            except ValueError:
                T2mC = None
            try:
                Td2mC = float(row['dewp'])
            except KeyError:
                try:
                    rh = float(row['RH'])
                    #print('rh:', rh) #ktw
                    #print('T2mC:', T2mC) #ktw
                    Td2mC = wbgt.Rh2Td(T2mC, rh)
                    #print('Td2mC:', Td2mC) #ktw
                except:
                    #print('Td calc failed?') #ktw
                    sys.exit()
                    Td2mC = None
            try:
                wspd10m = float(row['SPD1 (MS)'])
            except ValueError:
                wspd10m = None
            try:
                pSfc = 100.0 * float(row['Press  (MBAR)'])
            except KeyError:
                pSfc = None
            try:
                swdn = float(row['swdn'])
                if swdn > 5.0:
                    cloudFrac = None
                else:
                    # Assume no clouds for night, since WBGT probably isn't relevant anyway.
                    cloudFrac = 0.0
            except KeyError:
                swdn = None
                cloudFrac = 0.0
            # Estimate the wind speed at a different height than observed, but keep it in the wspd10m variable.
            if (windMeasurementHeight is not None and
                windEstimateHeight is not None and
                wspd10m is not None):
                # -------------------------------------------------------------------------------
                # Estimate the wind speed at windEstimateHeight with the wind profile power law.
                #   Use rural power law exponents from the EPA guidance, assuming D stability
                #   for simplicity.
                # -------------------------------------------------------------------------------
                stabilityClass = 'D'
                wspd10m = wspd10m * (windEstimateHeight/windMeasurementHeight)**\
                                     powerLawExponentRural[stabilityClass]

            # Calculate WBGT for each time, use calcWbgt function in wbgt module.
            latitude = 35.8615
            longitude = -106.3195
            swup = None
            lwdn = None
            lwup = None
            print('T2mC,Td2mC,wspd10m,pSfc:', T2mC,Td2mC,wspd10m,pSfc)
            if (T2mC is not None and
                Td2mC is not None and
                wspd10m is not None and
                pSfc is not None):
                try:
                    # Calculate WBGT for one time.
                    print('calcWbgt')
                    (Twet, Tglobe, wbgt1, cloudFrac) = wbgt.calcWbgt(yyyymmddhhmnUtc,
                                                                     latitude, longitude,
                                                                     T2mC, Td2mC, wspd10m, pSfc, cloudFrac,
                                                                     swdn, swup, lwdn, lwup,
                                                                     verbosity)
                    T2mF = round(wbgt.TC2F(T2mC), 1)
                    wspd10mMph = round(2.237*wspd10m, 1)
                    T2mK = T0 + T2mC
                    Td2mK = T0 + Td2mC
                    rh = round(100.0*wbgt.Td2Rh(T2mK,Td2mK), 1)
                    pSfcInHg = round(pSfc/3386.39, 2)
                    wbgtF = wbgt.TC2F(wbgt1)
                    # Write to csv file.
                    line = "{:s},{:5.1f},{:},{:},{:},{:},{:},{:},{:},{:},{:},{:5.1f},{:5.1f},{:},{:},{:},{:},{:5.1f}\n".format(
                        dtsMst,
                        wbgt1,
                        T2mC,Td2mC,
                        wspd10m,round(0.01*pSfc,1),round(cloudFrac,2),
                        swdn,swup,lwdn,lwup,
                        Twet,Tglobe,
                        T2mF,wspd10mMph,
                        rh,pSfcInHg,
                        wbgtF)
                    csvOut[tower].write(line)
                except:
                    print('ERROR')
                    continue
        
# --------------------------------------------
# Make list of all possible 15 min times.
#   Also collect hourly times in this dataset.
# --------------------------------------------
print('\nBuild list of all possible 15 min and hourly times:')
dt15All = []
if (dtFirst is not None and
    dtLast is not None):
    dt = dtFirst
    while dt <= dtLast:
        dt15All.append(dt)
        mm = datetime.strftime(dt, '%M')
        # Go to next time.
        dt = dt + timedelta(minutes=15)
else:
    print('Starting and ending times not found in data!')
    sys.exit(1)

# -------------------------
# Output 15 minute data.
# -------------------------
dtOut = dtIn
for var in variables:
    obsOut[var] = obsIn[var]

# -----------------------------------------
# Print a simple list of the data.
# Not sure the printed list is worth keeping. 
# -----------------------------------------

# ------------------------------------
# Also write the output to a CSV file.
# ------------------------------------
print('\nWriting to CSV file:', csvFile)
sys.exit()
with open(csvFile, 'w') as csvOut:
    csvOut.write(','.join(header.split()) + '\n')
    for i, dateTime in enumerate(dtOut):
        line = '{:s},'.format(datetime.strftime(dateTime, '%Y-%m-%d %H:%M'))
        line += '{:s},'.format(str(obsOut['spd1'][i]))
        line += '{:s},'.format(str(obsOut['temp0'][i]))
        line += '{:s},'.format(str(obsOut['dewp'][i]))
        line += '{:s},'.format(str(obsOut['swdn'][i]))
        csvOut.write('{:s}\n'.format(line))

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
