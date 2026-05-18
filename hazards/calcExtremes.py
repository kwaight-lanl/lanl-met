#!/usr/bin/env python3

"""
calcExtremes.py
Read a 24-hr csv file for one site, calculate extreme values for selected fields.
Usage: python calcExtremes.py [-v] [-changeunits] metfile  
  metfile is the name of the met file to read. It is assumed to be a csv file
  saved from an original Excel file, with header lines removed.
Adapted from arc2climo.py.
Ken Waight / September 2021
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
import statistics
import numpy as np
from collections import OrderedDict
from scipy.stats import boxcox
from scipy.stats import genextreme as gev
from scipy.stats import gumbel_r
import plotly.graph_objs as go
import plotly.io as pio

# ==============
# FUNCTIONS.
# ==============
def printPresentPct(yyyy, nPresent, nMissing):
    """
    Simple print of how much data is present and missing for a given year.
    """
    presentPct = 100 * (nPresent / (nPresent + nMissing))
    print('   ', yyyy, '{0: .1f}% of data is good'.format(presentPct))

def TC2F(TC):
    """
    Convert temperature from Celsius to Fahrenheit.
    """
    return (1.8*TC) + 32.0

def TF2C(TF):
    """
    Convert temperature from Fahrenheit to Celsius.
    """
    return (TF-32.0) / 1.8

def wspdMs2Mph(wspdMs):
    """
    Convert wind speed from meters per second to miles per hour.
    """
    return wspdMs * 2.237

def calcWindChill(TF, wspdMph):
    """
    Calculate the wind chill temperature from temperature and wind speed.
    Equation from David Bruggeman.
    """
    wspdPow = wspdMph**0.16
    windChill = 35.74 + (0.6215*TF) - (35.75*wspdPow) + (0.4275*TF*wspdPow)
    return windChill

def input2optional(unitsInput, unitsOptional, 
                   *vars):
    """
    Change variables from one unit to another.
    """
    varsOut = ()
    for var in vars:
        if (unitsInput == 'C' and
            unitsOptional == 'F'):
            var = TC2F(var)
        elif (unitsInput == 'm/s' and
            unitsOptional == 'mph'):
            var = wspdMs2Mph(var)
        else:
            print('WARNING: Cannot change', unitsInput, 'to', unitsOptional)
        varsOut = varsOut + (var,)
    return varsOut

def detectOutliersIqr(data, exclude=None):
    """
    Check for outliers in in a dataset, by using the Inter-Quartile Range (IQR).
    Optionally exclude a value from the data to improve detection.
    Use the scipy boxcox function to transform the data first, so that it should do
      a better job with skewed variables.
    Ken Waight / March 2021
    """
    if exclude is not None:
        # Remove a particular value from the dataset first (such as 0 for precip).
        dataT = [x for x in data if x != exclude]
        data = dataT
    if min(data) <= 0.0:
        # Shift the data, because the scipy boxcox function requires positive dataset.
        shift = abs(min(data)) + 1.0
        dataT = [x+shift for x in data]
    else:
        dataT = data
    # Apply the scipy boxcox function to transform the data.
    dataT, lamda = boxcox(dataT)
    # Calculate interquartile range, find outliers and return the original (untransformed)
    #   values.
    q1, q3 = np.percentile(sorted(dataT), [25, 75])
    iqr = q3 - q1
    lowerBound = q1 - (1.5*iqr) 
    upperBound = q3 + (1.5*iqr) 
    outliers = []
    dataWithoutOutliers = []
    for i, x in enumerate(dataT):
        xOrig = data[i] 
        if (x < lowerBound or
            x > upperBound):
            outliers.append(xOrig)
        else:
            dataWithoutOutliers.append(xOrig)
    return outliers

def detectOutliersZ(data, exclude=None):
    """
    Check for outliers in a dataset, by using the Z-score.
    Optionally exclude a value from the data to improve detection.
    Use the scipy boxcox function to transform the data first, so that it should do
      a better job with skewed variables.
    Ken Waight / March 2021
    """
    if exclude is not None:
        # Remove a particular value from the dataset first (such as 0 for precip).
        dataT = [x for x in data if x != exclude]
        data = dataT
    if min(data) <= 0.0:
        # Shift the data, because the scipy boxcox function requires positive dataset.
        shift = abs(min(data)) + 1.0
        dataT = [x+shift for x in data]
    else:
        dataT = data
    # Apply the scipy boxcox function to transform the data.
    dataT, lamda = boxcox(dataT)
    # Calculate z scores, find outliers and return the original (untransformed)
    #   values.
    mean = np.mean(dataT)
    stdDev = np.std(dataT)
    outliers = []
    dataWithoutOutliers = []
    for i, x in enumerate(dataT):
        xOrig = data[i] 
        zScore = (x-mean) / stdDev
        if abs(zScore) > 3.0:
            outliers.append(xOrig)
        else:
            dataWithoutOutliers.append(xOrig)
    return outliers

def checkOneValue(value, nFlagged,
                  rangeCheckVar=None, nOutOfRange=None):
    """
    For a single data value, check that it's not flagged (with
      an asterisk), and that it optionally passes a range check.
    """
    if '*' in value:
        nFlagged += 1
        return None
    else:
        value = float(value)
    if rangeCheckVar is not None:
        if not rangeCheck(value, rangeCheckVar):
            nOutOfRange += 1
            return None
    return value
    
def rangeCheck(value, variable):
    """
    Check a value for a variable against the allowed range.
    Ken Waight / March 2021 - using ranges from David Bruggeman.
    """
    # Set acceptable ranges.
    range = { 
        'spd1': {'min': 0.0, 'max': 30.0},
        'spd2': {'min': 0.0, 'max': 21.0}, 
        'spd3': {'min': 0.0, 'max': 26.0}, 
        'spd4': {'min': 0.0, 'max': 30.0},
        'sdspd1': {'min': 0.0, 'max': 7.0},
        'sdspd2': {'min': 0.0, 'max': 8.0},
        'sdspd3': {'min': 0.0, 'max': 8.0},
        'sdspd4': {'min': 0.0, 'max': 9.0},
        'dir': {'min': 0.0, 'max': 360.0},
        'sddir': {'min': 0.0, 'max': 180.0},
        'w': {'min': -3.0, 'max': 3.0},
        'sdw1': {'min': 0.0, 'max': 2.5},
        'sdw2': {'min': 0.0, 'max': 2.5},
        'sdw3': {'min': 0.0, 'max': 3.0},
        'sdw4': {'min': 0.0, 'max': 3.3},
        'temp': {'min': -35.0, 'max': 45.0},
        'press': {'min': 660.0, 'max': 820.0},
        'rh': {'min': 0.1, 'max': 100.0},
        'dewp': {'min': -50.0, 'max': 40.0},
        'precip': {'min': 0.0, 'max': 2.0},
        'snowd': {'min': 0.0, 'max': 120.0},
        'swdn': {'min': 0.0, 'max': 1400.0},
        'swup': {'min': 0.0, 'max': 800.0},
        'lwdn': {'min': 50.0, 'max': 600.0},
        'lwup': {'min': 100.0, 'max': 800.0},
        'netrad': {'min': -400.0, 'max': 1400.0},
        'avgspd1': {'min': 0.1, 'max': 18.0},
        'avgspd2': {'min': 0.5, 'max': 15.0}, 
        'avgspd3': {'min': 0.5, 'max': 15.0}, 
        'avgspd4': {'min': 0.5, 'max': 15.0},
        'mxgst1': {'min': 2.0, 'max': 44.0},
        'mxgst2': {'min': 2.0, 'max': 36.0}, 
        'mxgst3': {'min': 2.0, 'max': 38.0}, 
        'mxgst4': {'min': 2.0, 'max': 40.0},
        'time': {'min': 0.1, 'max': 2359.0},
        'mx1gst': {'min': 1.5, 'max': 33.0}, 
        'mxtemp': {'min': -25.0, 'max': 45.0}, 
        'mntemp': {'min': -35.0, 'max': 25.0}, 
        'midtemp': {'min': -35.0, 'max': 45.0}, 
        'press': {'min': 660.0, 'max': 820.0}, 
        'mxrh': {'min': 3.0, 'max': 100.0}, 
        'mnrh': {'min': 1.0, 'max': 98.0}, 
        'midrh': {'min': 0.0, 'max': 100.0}, 
        'avgrh': {'min': 3.0, 'max': 99.5}, 
        'mxdewp': {'min': -24.0, 'max': 25.0}, 
        'mndewp': {'min': -50.0, 'max': 16.0}, 
        'avgdewp': {'min': -30.0, 'max': 25.0}, 
        'tprecip': {'min': 0.0, 'max': 4.0}, 
        'tsnowf': {'min': 0.0, 'max': 45.0}, 
        'midsnowd': {'min': 0.0, 'max': 120.0}, 
        'swedn': {'min': 0.7, 'max': 43.2}, 
        'sweup': {'min': 0.1, 'max': 25.2}, 
        'lwedn': {'min': 7.2, 'max': 39.6}, 
        'lweup': {'min': 10.8, 'max': 54.0}, 
        'nete': {'min': -5.4, 'max': 21.6}, 
    } 
    variables = range.keys()
    # Check the value. Return true if it falls in the acceptable range,
    #   false if it doesn't.
    if variable in variables:
        if (value >= range[variable]['min'] and
            value <= range[variable]['max']):
            return True
        else:
            return False
    else:
        # Unknown variable name.
        print('Unknown variable name!:', variable)
        sys.exit(1)


# ==============
# MAIN PROGRAM.
# ==============
# ----------
# Constants.
# ----------

# ----------------------------------------------------------------
# Parse arguments.
# Get name of met file to read. There are two types:
#   1. A 24 hr file downloaded from the Weather Machine 
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a 24-hr ARC file and calculate maximums, minimums and averages.")
parser.add_argument("-metfiles", help="Name of met file to read", nargs='*')
parser.add_argument("-changeunits", help="Change input to optional units for selected variables.",
                    action="store_true")
parser.add_argument("-extremes", help="Calculate extreme values for a set of return periods.",
                    action="store_true")
parser.add_argument("-returns", help="Calculate return periods for a set of extreme values",
                    action="store_true")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
parser.add_argument("-examine", "--examine", nargs=3, 
                    help="Look at context of suspicious value, enter variable name, value and month")
args = parser.parse_args()
metFiles = args.metfiles
if args.changeunits:
    changeUnits = True
else:
    changeUnits = False
if args.extremes:
    calcExtremes = True
else:
    calcExtremes = False
if args.returns:
    calcReturns = True
else:
    calcReturns = False
if args.verbosity:
    verbosity = int(args.verbosity)
else:
    verbosity = 0
if args.examine:
    examine = True
    examineVariable = args.examine[0]
    examineValue = args.examine[1]
    examineMonth = args.examine[2]
    examineData = OrderedDict()
else:
    examine = False

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
monthName = ['January', 'February', 'March',
             'April', 'May', 'June',
             'July', 'August', 'September',
             'October', 'November', 'December']

# Variables to process.
vars = ['mxgst1', 'tprecip']

# Spreadsheet column names of the variables.
columnDateTime = 'Date/Time'
column = {}
column['mxgst1'] = 'mxgst1'
column['tprecip'] = 'tprecip'
# Units of the variables in the input data.
unitsInput = {}
unitsInput['mxgst1'] = 'm/s'
unitsInput['tprecip'] = 'in'
# Optional output units of the variables, default is to use original units.
unitsOptional = {}
unitsOptional['mxgst1'] = 'mph'
unitsOptional['tprecip'] = 'in'
# Variable to use for range checking input data.
rangeCheckVar = {}
rangeCheckVar['mxgst1'] = 'mxgst1'
rangeCheckVar['tprecip'] = 'tprecip'

# =======
# Banner.
# =======
print('\n ========================================================\n',
      'Calculate extremes from one or more 24-hr data file\n',
      '========================================================')
print(*sys.argv)

# Show input and output units.
print('\nInput and output units for the variables:')
print('Variable             In    Out')    
print('-------------------- ----- -----')
for var in vars:
    if changeUnits:
        print('{:20s} {:5s} {:5s}'.format(var, unitsInput[var], unitsOptional[var]))
    else:
        print('{:20s} {:5s} {:5s}'.format(var, unitsInput[var], unitsInput[var]))

# Initialize dict of all obs.
varAll = {}
for var in vars:
    varAll[var] = []
# Initialize dict for statistics by month.
varMonth = {}
for var in vars:
    varMonth[var] = {}
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        varMonth[var][mm] = []
# Initialize dicts for flagged and out of range data.
nFlagged = {}
nOutOfRange = {}
for var in vars:
    nFlagged[var] = 0
    nOutOfRange[var] = 0
# Initialize dict for statistics by year.
varYear = {}
for var in vars:
    varYear[var] = {}
# Initialize dict for monthly precipitation.
precipMonthYear = {}

# --------------------------------------------------------------------
# Read LANL 24-hr data at one or more locations.
# --------------------------------------------------------------------
for metFile in metFiles:
    print("\nReading LANL file:", metFile)
    # First check to be sure it has commas (because it has to be a CSV file).
    with open(metFile, 'r') as test:
        data = test.read()
    nCommas = data.count(',')
    if nCommas == 0:
        print('Input file has to be a CSV file, but there are no commas, wrong format!')
        sys.exit(1)
    # Now read file.
    dtFirst = None
    dtLast = None
    dtList = []
    yyyymmdds = []
    nBad = 0
    nDiag = 0
    with open(metFile, 'r') as infile:
        towerData = csv.DictReader(infile)
        next(towerData)
        for row in towerData:
            # Should be at least these fields.
            if (columnDateTime in row.keys() or
                ('month' in row.keys() and 'day' in row.keys() and 
                 'year' in row.keys())):
                pass  # This file has date information.
            else:
                print('\nERROR: This file does not have date informaion!',
                      '\nIt needs:',
                      '\n   ', columnDateTime, 'or month, day, year')
                sys.exit(1)
            if columnDateTime in row.keys():
                # Get the date from Date/Time column (yellow network).
                try:
                    # Try the default Weather Machine formatted date.
                    dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M:%S")
                except:
                    # Try a datalogger formatted date.
                    try:
                        dt = datetime.strptime(row[columnDateTime], "%m/%d/%Y %H:%M")
                    except:
                        print('ERROR: Problem reading date/time format:', row[columnDateTime])
                        sys.exit(1)
            else:
                # Get the date from the month, day, year columns.
                yyyymmdd = '{:04d}{:02d}{:02d}'.format(int(row['year']), int(row['month']),
                                                       int(row['day']))
                dt = datetime.strptime(yyyymmdd, "%Y%m%d")
            # Save first time.
            if dtFirst is None:
                dtFirst = dt
            # Get the year, month and day.
            yyyy = datetime.strftime(dt, '%Y')
            mm = '{:02d}'.format(int(datetime.strftime(dt, '%m')))
            dd = '{:02d}'.format(int(datetime.strftime(dt, '%d')))
            yyyymm = yyyy + mm
            mmdd = mm + dd
            # ---------------------------------------------------------
            # Check that each variable is good and save them.
            # ---------------------------------------------------------
            # Maximum wind gust.
            try:
                mxgst1 = checkOneValue(row[column['mxgst1']], nFlagged['mxgst1'],
                                       rangeCheckVar=rangeCheckVar['mxgst1'], 
                                       nOutOfRange=nOutOfRange['mxgst1']) 
            except KeyError:
                mxgst1 = None
            if mxgst1 is not None:
                mxgst1 = float(row[column['mxgst1']])  
                varAll['mxgst1'].append(mxgst1)
                varMonth['mxgst1'][mm].append(mxgst1)
                varYear['mxgst1'][yyyy] = varYear['mxgst1'].get(yyyy, [])
                varYear['mxgst1'][yyyy].append(mxgst1)
                if (examine and 
                    examineVariable == 'mxgst1' and
                    int(mm) == int(examineMonth)):
                    examineData[dt] = mxgst1
            # Daily precip amount.
            try:
                tprecip = checkOneValue(row[column['tprecip']], nFlagged['tprecip'],
                                       rangeCheckVar=rangeCheckVar['tprecip'], 
                                       nOutOfRange=nOutOfRange['tprecip']) 
            except KeyError:
                tprecip = None
            if tprecip is not None:
                tprecip = float(row[column['tprecip']])  
                varAll['tprecip'].append(tprecip)
                varMonth['tprecip'][mm].append(tprecip)
                varYear['tprecip'][yyyy] = varYear['tprecip'].get(yyyy, [])
                varYear['tprecip'][yyyy].append(tprecip)
                precipMonthYear[yyyymm] = precipMonthYear.get(yyyymm, [])
                precipMonthYear[yyyymm].append(tprecip)
                if (examine and 
                    examineVariable == 'tprecip' and
                    int(mm) == int(examineMonth)):
                    examineData[dt] = tprecip
            # -------------------------------------------------
            # If at least one variable is good, save this time.
            # -------------------------------------------------
            if (mxgst1 is not None or tprecip is not None):
                # One or more good values; add to list of all datetimes.
                dtList.append(dt)
            # Save the last time.
            dtLast = dt

# ----------------------------------------
# Make list of all possible 24 hr times.
# ----------------------------------------
print('\nBuild list of all possible 24 hr times:')
dtAll = []
if (dtFirst is not None and
    dtLast is not None):
    dt = dtFirst
    while dt <= dtLast:
        dtAll.append(dt)
        # Go to next time.
        dt = dt + timedelta(hours=24)
else:
    print('Starting and ending times not found in data!')
    sys.exit(1)

# --------------------------------------------------
# Calculate how much data is present for each year.
# --------------------------------------------------
print('\nCalculate how much data is present for each year:')
nTotal = 0
nPresent = 0
nMissing = 0
yyyyPrev = 0
years = []
for dt in dtAll:
    yyyy = datetime.strftime(dt, '%Y')
    if yyyyPrev == 0:
        # Initialize yyyyPrev.
        yyyyPrev = yyyy
    if (yyyyPrev != 0 and
        yyyy != yyyyPrev):
        # Print result for one year.
        printPresentPct(yyyyPrev, nPresent, nMissing)
        print('------------------------------')
        # Add this year to total.
        nTotal = nTotal + nPresent
        # Build list of years.
        years.append(yyyy)
        # Initialize for the next year.
        nPresent = 0
        nMissing = 0
        yyyyPrev = yyyy
    if dt in dtList:
        # Data present for this time.
        nPresent += 1
    else:
        # Data missing for this time.
        nMissing += 1
        print('          Missing:', dt)
# Print result for final year.
printPresentPct(yyyyPrev, nPresent, nMissing)
nTotal = nTotal + nPresent

# -----------------------------------------------
# Print total number of good and bad data times.
# -----------------------------------------------
print('\n', nTotal, 'total times found.')
print(nTotal, 'times with good data.')
print(nBad, ' times ignored because of bad data.')
if nTotal == 0:
    print('\nERROR: No good data found!')
    sys.exit(1)
if verbosity >= 2:
    diagPct = 100.0 * (float(nDiag) / float(nTotal))
    print(nDiag, 'times found for diagnostic categories, {:.2f}% of total'.format(diagPct))

# -----------------------------------------------------
# Calculate how much data is present for each variable.
# -----------------------------------------------------
print('\nData completeness report for each variable:')
print('      variable   % present    n flagged    n out of range')
print(' ------------- ------------- ------------- -------------')
for var in vars:
    varPct = 100.0 * (float(len(varAll[var]))/float(len(dtList)))
    print('{:13s} {:13.2f} {:13d} {:13d}'.format(var, varPct, 
                                                 nFlagged[var], 
                                                 nOutOfRange[var]))

# -----------------------------------------
# Calculate and print averages and medians.
# -----------------------------------------
print('\n================')
print('Daily Statistics')
print('================')
print('\nDaily maximums, minimums, averages and medians for all times:')
print('      variable       maximum       minimum       average        median')
print(' ------------- ------------- ------------- ------------- -------------')
averageAll = {}
for var in vars:
    if len(varAll[var]) > 0:
        maximum = max(varAll[var])
        minimum = min(varAll[var])
        averageAll[var] = statistics.mean(varAll[var])
        median = statistics.median(varAll[var])
        if (unitsInput[var] != unitsOptional[var] and
            changeUnits == True):
            # Convert to optional units.
            results = (maximum, minimum, averageAll[var], median)
            maximum, minimum, averageAll[var], median = input2optional(
                unitsInput[var], unitsOptional[var], 
                *results)
        print(' {:13s} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(
            var,
            maximum, minimum,
            averageAll[var], median))

# ----------------------
# Repeat for each month.
# ----------------------
print('\n==================')
print('Monthly Statistics')
print('==================')
for var in vars:
    if len(varAll[var]) > 0:
        print('\nMonthly maximums, minimums, averages and medians for {:s}:'.format(var))
        print('         month       maximum       minimum       average        median')
        print(' ------------- ------------- ------------- ------------- -------------')
        averageMonth = {}
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            try:
                maximum = max(varMonth[var][mm])
            except ValueError:
                maximum = 0.0
            try:
                minimum = min(varMonth[var][mm])
            except ValueError:
                minimum = 0.0
            try:    
                averageMonth[mm] = statistics.mean(varMonth[var][mm])
            except ValueError:
                averageMonth[mm] = 0.0
            try:    
                median = statistics.median(varMonth[var][mm])
            except ValueError:
                median = 0.0
            if (unitsInput[var] != unitsOptional[var] and
                changeUnits == True):
                # Convert to optional units.
                results = (maximum, minimum, averageMonth[mm], median)
                maximum, minimum, averageMonth[mm], median = input2optional(
                    unitsInput[var], unitsOptional[var], 
                    *results)
            print(' {:13d} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(
                int(mm),
                maximum, minimum,
                averageMonth[mm], median))
        print('Annual average: {:13.2f}'.format(averageAll[var]))
        # Write file of data for a report.
        csvFile = var + '.csv'
        print('Writing csv file:', csvFile)
        with open(csvFile, 'w') as csvOut:
            csvOut.write('month,var\n')
            for month in range(1, 13):
                mm = '{:02d}'.format(month)
                csvOut.write('{:s}, {:.1f}\n'.format(monthName[month-1], averageMonth[mm]))
            csvOut.write('{:s}, {:.1f}\n'.format('Annual', averageAll[var]))

# -------------------------------
# Calculate monthly precip stats.
# -------------------------------
if len(precipMonthYear.keys()) > 0:
    print('\nMaximums, minimums, averages and medians for monthly total precipitation:')
    print('         month       maximum       minimum       average        median')
    print(' ------------- ------------- ------------- ------------- -------------')
    averageMonth = {}
    averageAnnual = 0.0
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        varMonthTotals = []
        for yyyymm in precipMonthYear.keys():
            if int(yyyymm[-2:]) == month:
                varMonthTotal = sum(precipMonthYear[yyyymm])
                varMonthTotals.append(varMonthTotal)
        maximum = max(varMonthTotals)
        minimum = min(varMonthTotals)
        averageMonth[mm] = statistics.mean(varMonthTotals)
        median = statistics.median(varMonthTotals)
        if (unitsInput[var] != unitsOptional[var] and
            changeUnits == True):
            # Convert to optional units.
            results = (maximum, minimum, averageMonth[mm], median)
            maximum, minimum, averageMonth[mm], median = input2optional(
                unitsInput[var], unitsOptional[var], 
                *results)
        print(' {:13d} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(
            int(mm),
            maximum, minimum,
            averageMonth[mm], median))
        averageAnnual += averageMonth[mm]
    print('Annual average: {:.2f}'.format(averageAnnual))
    # Write file of data for a report.
    csvFile = 'precip.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('month,precip\n')
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            csvOut.write('{:s}, {:.2f}\n'.format(monthName[month-1], averageMonth[mm]))
        csvOut.write('{:s}, {:.2f}\n'.format('Annual', averageAnnual))

# ----------------------------------
# Show precipitation for each month.
# ----------------------------------
if len(precipMonthYear.keys()) > 0:
    print('\nPrecipitation total for each month:')
    print('yyyymmdd     total\n',
          '--------  --------')
    resultMonthYear = {}
    for yyyy in years:
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            yyyymm = yyyy + mm
            try:
                varMonthTotal = sum(precipMonthYear[yyyymm])
            except KeyError:
                # Skip months with no data.
                continue
            if (unitsInput[var] != unitsOptional[var] and
                changeUnits == True):
                # Convert to optional units.
                resultList = input2optional(
                    unitsInput['tprecip'], unitsOptional['tprecip'], 
                    varMonthTotal)
                resultMonthYear[yyyymm] = resultList[0] 
            else:
                resultMonthYear[yyyymm] = varMonthTotal
            print(' {:8s}  {:8.2f}'.format(yyyymm, resultMonthYear[yyyymm]))
    # Write file of data for a report.
    csvFile = 'monthlyPrecip.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('month-year,precip\n')
        for yyyymm in precipMonthYear.keys():
            yyyy = yyyymm[0:4]
            month = int(yyyymm[-2:])
            datestring = monthName[month-1][0:3] + '-' + yyyy
            try:
                csvOut.write('{:s}, {:.2f}\n'.format(datestring, resultMonthYear[yyyymm]))
            except KeyError:
                # Skip months with no data.
                continue

print('\n=================')
print('Yearly Statistics')
print('=================')
for var in vars:
    if len(varYear[var].keys()) > 0:
        print('\nYearly maximums, minimums, averages and medians for {:s}:'.format(var))
        print('          year       maximum       minimum       average        median')
        print(' ------------- ------------- ------------- ------------- -------------')
        varAll = []
        for yyyy in varYear[var].keys():
            maximum = max(varYear[var][yyyy])
            minimum = min(varYear[var][yyyy])
            average = statistics.mean(varYear[var][yyyy])
            median = statistics.median(varYear[var][yyyy])
            if (unitsInput[var] != unitsOptional[var] and
                changeUnits == True):
                # Convert to optional units.
                results = (maximum, minimum, average, median)
                maximum, minimum, average, median = input2optional(
                    unitsInput[var], unitsOptional[var], 
                    *results)
            print(' {:13d} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(
                int(yyyy),
                maximum, minimum,
                average, median))
            varAll += varYear[var][yyyy]
        maximum = max(varAll)
        minimum = min(varAll)
        average = statistics.mean(varAll)
        median = statistics.median(varAll)
        if (unitsInput[var] != unitsOptional[var] and
            changeUnits == True):
            # Convert to optional units.
            results = (maximum, minimum, average, median)
            maximum, minimum, average, median = input2optional(
                unitsInput[var], unitsOptional[var], 
                *results)
            print(' {:13s} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(
                'All'.rjust(13),
                maximum, minimum,
                average, median))

# ---------------------------------------
# Find possible outliers in monthly data.
# ---------------------------------------
print('\n=================')
print('Outliers')
print('=================')
for var in vars:
    print('\nExamine possible outliers for {:s} (input units):'.format(var))
    print(' month       outliers')
    print(' -- ----------------------------------------------------')
    nOutliers = 0
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        if len(varMonth[var][mm]) > 0:
            if ('precip' in var.lower() or 
                'sw' in var.lower() or 
                'snow' in var.lower()):
                # Exclude zero values for precip, shortwave.
                if (len(varMonth[var][mm]) > 0 and
                    any(x != 0.0 for x in varMonth[var][mm])):
                    outliersIqr = detectOutliersIqr(varMonth[var][mm], exclude=0.0)
                    outliersZ = detectOutliersZ(varMonth[var][mm], exclude=0.0)
                else:
                    outliersIqr = []
                    outliersZ = []
            else:
                outliersIqr = detectOutliersIqr(varMonth[var][mm])
                outliersZ = detectOutliersZ(varMonth[var][mm])
            # Show values that are outliers for both methods (intersection).
            outliers = set(outliersIqr) & set(outliersZ)
            nOutliers += len(outliers)
            print(' {:2d} {:s}'.format(int(mm), str(sorted(outliers))))
    print('Total number of possible outliers:', nOutliers)

# -------------------------------------------------------------------
# If the -examine option was used, print a list of all values of the 
#   desired variable for the desired month.
# -------------------------------------------------------------------
if examine:
    print('\nExamine selected variable, value and month:',
          '\n   Variable:', examineVariable,
          '\n   Value   :', examineValue,
          '\n   Month   :', examineMonth)
    for dt in examineData.keys():
        if examineData[dt] == float(examineValue):
            print(dt.strftime('%Y-%m-%d %H%m'), float(examineData[dt]), '<--- examine')
        else:
            print(dt.strftime('%Y-%m-%d %H%m'), float(examineData[dt]))

# -----------------------------------------------------
# Collect the maximums for each year to build a series,
#   calculate extreme values for different return 
#   periods.
# -----------------------------------------------------
print('\n===========================')
print('Extreme value distributions')
print('===========================')
for var in vars:
    print('-----------')
    print(var)
    print('-----------')
    seriesMax = []
    if len(varYear[var].keys()) > 0:
        # Build the series.
        for yyyy in varYear[var].keys():
            maximum = max(varYear[var][yyyy])
            seriesMax.append(maximum)
        if (unitsInput[var] != unitsOptional[var] and
            changeUnits == True):
            # Convert to optional units.
            seriesMax = input2optional(
                unitsInput[var], unitsOptional[var], 
                *seriesMax)
        print(var, seriesMax)
        # Fit the series to an extreme value distribution.
        #   1. Generalized extreme value distribution.
        shape, loc, scale = gev.fit(seriesMax, f0=0)
        #   Test calculation of loc and scale from the mean and standard 
        #     deviation, as in Chow hydrology textbook.
        mean = statistics.mean(seriesMax)
        stdev = statistics.stdev(seriesMax)
        alpha = (math.sqrt(6.0)*stdev) / math.pi
        u = mean - 0.5772*alpha
        print('mean, stdev:', mean, stdev)
        print('u, alpha:', u, alpha)
        #mean, variance = gev.stats(shape, moments='mv')
        #sys.exit()
        #   2. Gumbel distribution.
        #loc, scale = gumbel_r.fit(seriesMax)
        #shape = 0.0
        print('shape, loc, scale:', shape, loc, scale)
        if calcReturns:
            # Calculate return periods for a set of extreme values.
            print('\nCalculate return periods for a set of extreme values:')
            extremeValues = [1.34, 1.77, 2.07, 2.47, 2.78, 3.09]
            for extremeValue in extremeValues:
                cdf = gev.cdf(extremeValue, c=shape, loc=loc, scale=scale)
                returnPeriod = 1.0 / (1.0-cdf)
                print('extreme, period:', extremeValue, returnPeriod)
        if calcExtremes:
            # Calculate extreme values for a set of return periods.
            print('\nCalculate extreme values for a set of return periods:')
            returnPeriods = [2.0, 5.0, 10.0, 25.0, 50.0, 100.0,
                             2500.0, 6250.0, 10000.0, 25000.0]
            for returnPeriod in returnPeriods:
                #cdf = 1.0 - 1.0/returnPeriod
                #extremeValue = loc + (scale/shape)*\
                #               ((-math.log(cdf))**(-shape) - 1.0)
                #print('period, extreme', returnPeriod, extremeValue)
                # From Chow.
                yt = -math.log(math.log(returnPeriod/(returnPeriod-1.0)))
                xt = loc + scale*yt
                print('returnPeriod, xt:', returnPeriod, xt)


# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
