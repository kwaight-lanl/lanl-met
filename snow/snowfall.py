"""
snowfall.py
Test the logic for calculating snowfall accumulation from a 15 min snow depth time series.
Assume precipitation and snow depth measurements in inches, and temperatures in Celsius.
Ken Waight / March 2023
"""

import sys
import os
import csv
from datetime import datetime
import argparse
import statistics

# Constants.
TEMP_THRESH = (40-32) / 1.8  # 40 F in Celsius.

# Initialize.
snowDepth15Min = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] 
snowDepthSmoothed = [0.0, 0.0, 0.0, 0.0, 0.0] 
snowDepthDiff = [0.0, 0.0, 0.0, 0.0] 
snowDepth = 0.0
snowfallHr = 0.0
snowfallToday = 0.0
precip15Min = [0.0, 0.0, 0.0, 0.0]
temp15Min = [0.0, 0.0, 0.0, 0.0]

# ----------------------------------------------------------------
# Parse arguments.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a Weather Machine data file and calculate snowfall.")
parser.add_argument("metfile", help="Name of met file to read")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
args = parser.parse_args()
metFile = args.metfile
if args.verbosity:
    verbosity = int(args.verbosity)
else:
    verbosity = 0

# --------------------------------------------
# Read met file with 15 min snow depth values.
# --------------------------------------------
columnDateTime = 'Date/Time'
columnTemp0 = 'temp0'
columnPrecip = 'precip'
columnSnowd = 'snowd'
print("\nReading LANL file:", metFile)
dtList = []
temp0List = []
precipList = []
snowdList = []
with open(metFile, 'r') as infile:
    towerData = csv.DictReader(infile)
    for row in towerData:
        if (row[columnDateTime] and  # Should be at least these fields.
            row[columnTemp0] and 
            row[columnPrecip] and
            row[columnSnowd]):
            # This should be a data line (ignore header lines).
            try:
                # Try the default Weather Machine formatted date.
                dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M:%S")
            except:
                # Try a datalogger formatted date.
                dt = datetime.strptime(row[columnDateTime], "%m/%d/%Y %H:%M")
            dtList.append(dt)
            temp0List.append(float(row[columnTemp0]))
            precipList.append(float(row[columnPrecip]))
            snowdList.append(float(row[columnSnowd]))
            
outfile = open('snowfall.csv', 'w')
outfile.write('date/time,snowDepth,snowfallHr,snowfallToday\n')
lastHrPrecip = 0.0
snowTrace = ' '
snowfallToday = 0.0
snowTraceToday = ' '
notes = []
yyyymmddToday = datetime.strftime(dtList[0], "%Y%m%d")
snowfallTotal = 0.0
print('yyyymmdd  snowf T Notes')
print('--------  ----- - -----')
for dt, temp0, precip, snowDepth in zip(dtList, temp0List, precipList, snowdList):
    yyyymmdd = datetime.strftime(dt, "%Y%m%d")
    hour = int(datetime.strftime(dt, "%H"))
    min = int(datetime.strftime(dt, "%M"))

    # ---------------------------------------------------------------------
    # Snowfall Estimation
    # ---------------------------------------------------------------------
    # Update running record of last seven 15 minute snow depth values.
    for i in range(6, 0, -1):
        snowDepth15Min[i] = snowDepth15Min[i-1]
    snowDepth15Min[0] = snowDepth

    if (hour == 1 and min == 15):
        # Reset the daily snowfall at the beginning of a new day.
        yyyymmddToday = yyyymmdd
        snowfallToday = 0.0
        snowTraceToday = ' '
        notes = []

    if min == 15:
        # -------------------------------------------------------------------
        # At :15, estimate snowfall for the previous hour.
        # -------------------------------------------------------------------
        # Calculate smoothed snow depth, 3 point smoother.
        for i in range(0, 5): # From 15 min before previous hour to 15 min after.
            snowDepthSmoothed[i] = (snowDepth15Min[i] + snowDepth15Min[i+1] +
                                      snowDepth15Min[i+2]) / 3.0

        # Find the differences in smoothed snow depth over the last hour, from 0-15-30-60.
        for i in range(0, 4):
            snowDepthDiff[i] = snowDepthSmoothed[i] - snowDepthSmoothed[i+1]

        # Add up the snowfall for the previous hour.
        snowfallHrRaw = 0.0
        for i in range(0, 4):
            if snowDepthDiff[i] > 0.0:
                snowfallHrRaw = snowfallHrRaw + snowDepthDiff[i]
        snowfallHr = round(snowfallHrRaw ,1)  # Round hourly snowfall to the nearest 0.1.

        if verbosity >= 1:
            # Show details.
            print('--------------------------', dt, '--------------------------')
            print('temp15Min        :', temp15Min)
            print('precip15Min      :', precip15Min)
            print('snowDepth15Min   :', snowDepth15Min)
            print('snowDepthSmoothed:', snowDepthSmoothed)
            print('snowDepthDiff    :', snowDepthDiff)
            print('snowfallHrRaw    :', snowfallHrRaw)
            print('snowfallHr(round):', snowfallHr)

        # Sum precip over the previous hour.
        precipLastHr = sum(precip15Min)
        # Average temperature over the previous hour.
        tempLastHr = statistics.mean(temp15Min)

        # --------------------------------------------------------------------------------
        # Main section: Decide whether there is snowfall or a trace for the previous hour.
        # --------------------------------------------------------------------------------
        if (snowfallHrRaw > 0.1 and 
              precipLastHr > 0.0 and
              tempLastHr < TEMP_THRESH): 
            # 1. If snowfallHr > 0.1 and precip occurred and hourly 
            #    avg air temp < 40 deg F, add the rounded value.
            #    Previously there had been a test for snowfall > 0.4
            #    and precip > 0, but that was incorrect.
            snowfallHr = snowfallHr  
            note = '/ snowf>0.1 in, last hr precip>0, T<40F'
            if not note in notes:
                notes.append(note)
            if verbosity >= 1:
                print('Result:', note, '==> snowfallHr rounded =', snowfallHr)
        elif (precipLastHr > 0.0 and
              tempLastHr <= 0.0): 
            # 2. If the snowfallHr < 0.1" (even if negative), 
            #    precip was measured during the hour and 
            #    the average temperature was <= 32F, record as a trace.
            snowfallHr = 0.0
            snowTraceToday = 'T'  # Trace snowfall occurred.
            note = '/ snowf<=0.1 in, last hr precip>0, T<32F'
            if not note in notes:
                notes.append(note)
            if verbosity >= 1:
                print('Result:', note, '==> Trace')
        else:
            # 3. No snow at all.    
            snowfallHr = 0.0
            if verbosity >= 1:
                print('Result: No snow or trace, no precip or too warm.')

        # Accumulate snowfall over each day.
        snowfallToday = snowfallToday + snowfallHr

    elif (hour == 1 and min == 0):
        snowfallTotal += snowfallToday
        # Basic diagnostic print of snow results at the end of each day.
        if (snowfallToday > 0.0 and snowTraceToday == 'T'):
            # Don't show trace if there was also a snowfall amount.
            snowTraceToday = ' '
        if len(notes) > 0: 
            notes.append(' /')
        print('{:8s}  {:5.1f} {:1s}'.format(yyyymmddToday, snowfallToday, snowTraceToday), *notes)
        if verbosity >= 1:
            print('=======================================')

    # Update running record of the last four 15 minute temperature and precip values.
    for i in range(3, 0, -1):
        temp15Min[i] = temp15Min[i-1]
        precip15Min[i] = precip15Min[i-1]
    temp15Min[0] = temp0
    precip15Min[0] = precip

    # -------------------------------
    # Write basic output to CSV file.
    # -------------------------------
    dtFormatted = datetime.strftime(dt, "%Y-%m-%d %H:%M:%S")
    outfile.write('{:s},{:.1f},{:.1f},{:.1f}\n'.format(dtFormatted,snowDepth,snowfallHr,snowfallToday))
outfile.close()

print('--------  ----- -')
print('  Total   {:.1f}'.format(snowfallTotal))

print('\nComplete')
sys.exit()
