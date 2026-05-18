#!/usr/bin/env python3

"""
tower2dayvars.py
Read a 15-min csv file for one tower site, calculate a few variables for each day and write a CSV file.
Usage: python tower2dayvars.py [-v] metfile  
  metfile is the name of the met file to read. It is assumed to be in the format downloaded from the Weather Machine.
Ken Waight / November 2022
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

# ==============
# FUNCTIONS.
# ==============

# ==============
# MAIN PROGRAM.
# ==============
# ----------
# Constants.
# ----------
FLAG = -999.9  # Value for data assumed to be bad. 

# ----------------------------------------------------------------
# Parse arguments.
# Get name of met file to read. There is one option:
#   1. A 15 min file downloaded from the Weather Machine.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a Weather Machine file and make a simple list of data")
parser.add_argument("metfile", help="Name of met file to read")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
args = parser.parse_args()
metFile = args.metfile
if args.verbosity:
    verbosity = int(args.verbosity)
else:
    verbosity = 0

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
columnName = {}
columnName['DateTime'] = 'datetime'
#ktw columnName['DateTime'] = 'Date/Time'
columnName['doy'] = 'doy'
columnName['dir1'] = 'dir1'
columnName['spd1'] = 'spd1'
columnName['temp0'] = 'temp0'
columnName['temp1'] = 'temp1'
columnName['temp2'] = 'temp2'
columnName['temp3'] = 'temp3'
columnName['rh'] = 'rh'
columnName['dewp'] = 'dewp'
columnName['precip'] = 'precip'
columnName['swdn'] = 'swdn'

# =======
# Banner.
# =======
print('\n =====================================================\n',
      'Calculate variables for each day\n',
      '=====================================================\n')
print(*sys.argv)

# --------------------------------------------------------------------
# Read LANL 15-minute data at one tower location.
#   For each set of valid 15 min values, find the wind direction bin,
#   wind speed bin and stability class, and increment the counter for
#   that combination.
# --------------------------------------------------------------------
print("\nReading LANL file:", metFile)
dtFirst = None
dtLast = None
dtList = []
yyyymmdds = []
nBad = 0
nDiag = 0
doyPrev = -1
doyList = []
dtDay = {}
swdnMax = {}
t0mt1Max = {}
t1mt2Max = {}
t2mt3Max = {}
with open(metFile, 'r') as infile:
    towerData = csv.DictReader(infile)
    for row in towerData:
        if (row[columnName['DateTime']] and
            (re.search(r'^\d+-\d+-\d+ \d+:\d+', row[columnName['DateTime']]) or
             re.search(r'^\d+/\d+/\d+ \d+:\d+', row[columnName['DateTime']]))):
            # This should be a data line (ignore header lines).
            #print('row[0]:', row[columnName['DateTime']]) #ktw
            try:
                # Try a yellow Weather Machine-formatted date.
                dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M:%S")
            except:
                try:
                    # Try a datalogger-formatted date.
                    dt = datetime.strptime(row[columnName['DateTime']], "%m/%d/%Y %H:%M")
                except:
                    # Try a new Weather Machine-formatted date.
                    dt = datetime.strptime(row[columnName['DateTime']], "%Y-%m-%d %H:%M")
            # Save first time.
            if dtFirst is None:
                dtFirst = dt
            # ---------------------------------------------------------
            # Save data, convert * to a flag value.
            # ---------------------------------------------------------
            dtList.append(dt)
            try:
                doy = int(row['doy'])
            except ValueError:
                doy = None
            if doy is not None:
                if doy != doyPrev:
                    # Day of year changed, write completed data for previous day.
                    # Start calculating and collecting data for new day.
                    doyList.append(doy)
                    dtDay[doy] = dt.strftime('%m/%d/%Y')
                    t0mt1Max[doy] = -999.
                    t1mt2Max[doy] = -999.
                    t2mt3Max[doy] = -999.
                    swdnMax[doy] = 0.0
                    doyPrev = doy
                # For each time, update daily variables if necessary.
                # Maximum level 0 minus level 1 temperature.
                try:
                    t0mt1 = float(row['temp0']) - float(row['temp1'])
                except ValueError:
                    t0mt1 = None
                if t0mt1 is not None:    
                    t0mt1Max[doy] = max(t0mt1Max[doy], t0mt1)
                # Maximum level 1 minus level 2 temperature.
                try:
                    t1mt2 = float(row['temp1']) - float(row['temp2'])
                except ValueError:
                    t1mt2 = None
                if t1mt2 is not None:    
                    t1mt2Max[doy] = max(t1mt2Max[doy], t1mt2)
                # Maximum level 2 minus level 3 temperature.
                try:
                    t2mt3 = float(row['temp2']) - float(row['temp3'])
                except ValueError:
                    t2mt3 = None
                if t2mt3 is not None:    
                    t2mt3Max[doy] = max(t2mt3Max[doy], t2mt3)
                # Maximum shortwave down.
                try:
                    swdn = float(row['swdn'])
                except ValueError:
                    swdn = None
                if swdn is not None:    
                    swdnMax[doy] = max(swdnMax[doy], swdn)
            # Save the last time.
            dtLast = dt

# ----------------------------------------
# Make list of all possible 15 min times.
# ----------------------------------------
print('\nBuild list of all possible 15 min times:')
dt15All = []
if (dtFirst is not None and
    dtLast is not None):
    dt = dtFirst
    while dt <= dtLast:
        dt15All.append(dt)
        # Go to next time.
        dt = dt + timedelta(minutes=15)
else:
    print('Starting and ending times not found in data!')
    sys.exit(1)

# -----------------------------------------
# Write data to csv.
# -----------------------------------------
print('\nSimple list of observations:')
csvFile = 'dayvars.csv'
print('Writing csv file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write('dt, doy, t0mt1Max, t1mt2Max, t2mt3Max, swdnMax\n')
    for doy in doyList:
        csvOut.write('{:s},{:d},{:.1f},{:.1f},{:.1f},{:d}\n'.format(dtDay[doy],doy,
                                                                    t0mt1Max[doy],t1mt2Max[doy],t2mt3Max[doy],
                                                                    int(swdnMax[doy])))

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
