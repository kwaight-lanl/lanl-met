#!/usr/bin/env python3

"""
arc2climo.py
Read a 24-hr csv file for one ARC site, calculate maximums, mininums and 
  averages needed for climatology.
Usage: python arc2climo.py [-v] [-changeunits] metfile  
  metfile is the name of the met file to read. It is assumed to be a csv file
  saved from an original Excel file, with header lines removed.
Adapted from tower2climo.py.
Ken Waight / August 2021
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

def calc_solar_params(lat, lon, datetimeUtc):
    """
    Given a latitude, longitude and time, calculate the 
      main solar parameters:
      Declination, hour angle, zenith angle, solar irradiance at top of
        atmosphere
    Using equations from Massen (2011) paper, pointing to Hinssen and 
      Knap (2007).
    Ken Waight / June 2021
    """
    DEG_RAD = math.pi / 180.0

    # Day of year.
    dayofyear = float(datetimeUtc.strftime('%j'))

    #Solar declination.
    d = 23.45 * math.sin(360.0*(dayofyear+284.0)/365.0)
    theta = 2.0 * math.pi * (d/365.0)
    solarDeclination = (0.006918 - 0.3999912*math.cos(theta) +
                        0.070257*math.sin(theta) -
                        0.006758*math.cos(2.0*theta) +
                        0.000908*math.sin(2.0*theta))

    # Hour angle.
    hr = datetimeUtc.strftime('%H')
    mn = datetimeUtc.strftime('%M')
    sec = datetimeUtc.strftime('%S')
    hrFracUtc = hr + mn/60.0 + sec/3600.0
    eot = (0.0172 + 0.4281*math.cos(theta) -
           7.3515*math.sin(theta) -
           3.3495*math.cos(2.0*theta) -
           9.3619*math.sin(2.0*theta))
    solarTime = hrFracUtc + lon/15.0 + eot
    hourAngle = 15.0 * (solarTime - 12.0)

    # Zenith angle.
    elevationAngle = math.asin(
        math.sin(solarDeclination)*math.sin(latitude) +
        math.cos(solarDeclination)*math.cos(latitude)*math.cos(hourAngle))
    zenithAngle = 90.0 - elevationAngle

    # Irradiance at the top of the atmosphere.
    S0 = 1080.0 * (math.sin(elevationAngle))**1.25

    # Return.
    return declinationAngle, hourAngle, zenithAngle, S0

# ==============
# MAIN PROGRAM.
# ==============
# ----------
# Constants.
# ----------
N_YEARS = 30.0
DEGREE_DAY_BASE = 65.0  # Heating and cooling degree days calculated from base of 65 deg F.
PRECIP_DAILY_HIGH_THRESH = 0.5
TEMP_DAILY_HIGH_THRESH = 90.0
TEMP_DAILY_LOW_THRESH = 0.0
OUTLIERS = False

# ----------------------------------------------------------------
# Parse arguments.
# Get name of met file to read. There are two types:
#   1. A 24 hr file downloaded from the Weather Machine 
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a 24-hr ARC file and calculate maximums, minimums and averages.")
parser.add_argument("metfile", help="Name of met file to read")
parser.add_argument("-changeunits", help="Change input to optional units for selected variables.",
                    action="store_true")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
parser.add_argument("-examine", "--examine", nargs=3, 
                    help="Look at context of suspicious value, enter variable name, value and month")
args = parser.parse_args()
metFile = args.metfile
if args.changeunits:
    changeUnits = True
else:
    changeUnits = False
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
vars = ['mxtemp', 'mntemp', 'avgTemp0',
        'tprecip', 'tsnowf']

# Spreadsheet column names of the variables.
columnDateTime = 'Date/Time'
column = {}
column['mxtemp'] = 'mxtemp'
column['mntemp'] = 'mntemp'
column['tprecip'] = 'tprecip'
column['tsnowf'] = 'tsnowf'
# Units of the variables in the input data.
unitsInput = {}
unitsInput['mxtemp'] = 'C'
unitsInput['mntemp'] = 'C'
unitsInput['avgTemp0'] = 'C'
unitsInput['tprecip'] = 'in'
unitsInput['tsnowf'] = 'in'
# Optional output units of the variables, default is to use original units.
unitsOptional = {}
unitsOptional['mxtemp'] = 'F'
unitsOptional['mntemp'] = 'F'
unitsOptional['avgTemp0'] = 'F'
unitsOptional['tprecip'] = 'in'
unitsOptional['tsnowf'] = 'in'
# Variable to use for range checking input data.
rangeCheckVar = {}
rangeCheckVar['mxtemp'] = 'mxtemp'
rangeCheckVar['mntemp'] = 'mntemp'
rangeCheckVar['avgTemp0'] = 'temp'
rangeCheckVar['tprecip'] = 'tprecip'
rangeCheckVar['tsnowf'] = 'tsnowf'

# =======
# Banner.
# =======
print('\n ========================================================\n',
      'Calculate climatological info from an ARC data file\n',
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
snowMonthYear = {}
# Initialize dict for annual precipitation.
precipYear = {}
snowYear = {}
# Initialize dict for monthly min and max temp.
mntempMonthYear = {}
mxtempMonthYear = {}
# Initialize dicts for annual monsoon and winter precipitation.
monsoonPrecipYear = {}
winterPrecipYear = {}
# Initialize dict for monthly heating and cooling degree days.
heatingDegreeDaysMonthYear = {}
coolingDegreeDaysMonthYear = {}
# Initialize dict for annual heating and cooling degree days.
heatingDegreeDaysYear = {}
coolingDegreeDaysYear = {}
# Initialize dict for latest and earliest freeze dates.
lastFreeze = {}
firstFreeze = {}
# Initialize dict for daily max and min temperatures.
varDay = {}
varDay['mxtemp'] = {}
varDay['mntemp'] = {}
varDay['tprecip'] = {}
varDay['tsnowf'] = {}

# --------------------------------------------------------------------
# Read LANL 24-hr data at one tower location.
# --------------------------------------------------------------------
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
highestPrecipDays = {}
with open(metFile, 'r') as infile:
    towerData = csv.DictReader(infile)
    next(towerData)
    for row in towerData:
        # Should be at least these fields.
        if (columnDateTime in row.keys() or
            ('month' in row.keys() and 'day' in row.keys() and 
             'year' in row.keys()) and 
            row[column['mxtemp']] and
            row[column['mntemp']]):
            pass  # This file has all of the necessary fields.
        else:
            print('\nERROR: This file does not have all of the necessary fields!',
                  '\nIt needs:',
                  '\n   ', columnDateTime, 'or month, day, year and')
            for var in column.keys():
                print('   ', column[var])
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
        # Max temperature at level 0.
        mxtemp = checkOneValue(row[column['mxtemp']], nFlagged['mxtemp'],
                                rangeCheckVar=rangeCheckVar['mxtemp'], 
                                nOutOfRange=nOutOfRange['mxtemp']) 
        if mxtemp is not None:
            mxtemp = float(row[column['mxtemp']])  
            varAll['mxtemp'].append(mxtemp)
            varMonth['mxtemp'][mm].append(mxtemp)
            mxtempMonthYear[yyyymm] = mxtempMonthYear.get(yyyymm, [])
            mxtempMonthYear[yyyymm].append(mxtemp)
            varYear['mxtemp'][yyyy] = varYear['mxtemp'].get(yyyy, [])
            varYear['mxtemp'][yyyy].append(mxtemp)
            if (examine and 
                examineVariable == 'mxtemp' and
                int(mm) == int(examineMonth)):
                examineData[dt] = mxtemp
        # Min temperature at level 0.
        mntemp = checkOneValue(row[column['mntemp']], nFlagged['mntemp'],
                                rangeCheckVar=rangeCheckVar['mntemp'], 
                                nOutOfRange=nOutOfRange['mntemp']) 
        if mntemp is not None:
            mntemp = float(row[column['mntemp']])  
            varAll['mntemp'].append(mntemp)
            varMonth['mntemp'][mm].append(mntemp)
            mntempMonthYear[yyyymm] = mntempMonthYear.get(yyyymm, [])
            mntempMonthYear[yyyymm].append(mntemp)
            varYear['mntemp'][yyyy] = varYear['mntemp'].get(yyyy, [])
            varYear['mntemp'][yyyy].append(mntemp)
            # Keep track of mxtemp by day of year.
            varDay['mntemp'][mmdd] = varDay['mntemp'].get(mmdd, [])
            varDay['mntemp'][mmdd].append(mntemp)
            # Keep track of latest and earliest freeze dates.
            if unitsInput['mntemp'] == 'C':
                tempFreezing = 0.0
            elif unitsInput['mntemp'] == 'F':
                tempFreezing = 32.0
            else:
                print('ERROR: mntemp input units should be C or F!')
                sys.exit(1)
            lastFreeze[yyyy] = lastFreeze.get(yyyy, None)
            firstFreeze[yyyy] = firstFreeze.get(yyyy, None)
            if mntemp <= tempFreezing:
                if int(mm) <= 6:
                    # Replace last freeze date until there are no more.
                    lastFreeze[yyyy] = mmdd
                else:
                    # Only save the first freeze date, starting in July. 
                    if firstFreeze[yyyy] is None:
                        firstFreeze[yyyy] = mmdd
        # Assume daily average temperature is just midway between max and min.
        if (mxtemp is not None and
            mntemp is not None):
            avgTemp0 = 0.5 * (mxtemp+mntemp) 
            varAll['avgTemp0'].append(avgTemp0)
            varMonth['avgTemp0'][mm].append(avgTemp0)
            varYear['avgTemp0'][yyyy] = varYear['avgTemp0'].get(yyyy, [])
            varYear['avgTemp0'][yyyy].append(avgTemp0)
            # Keep track of mntemp by day of year.
            varDay['mxtemp'][mmdd] = varDay['mxtemp'].get(mmdd, [])
            varDay['mxtemp'][mmdd].append(mxtemp)
            # Accumulate heating and cooling degree days by month.
            if unitsInput['mntemp'] == 'C':
                avgTemp0F = TC2F(avgTemp0)
            elif unitsInput['mntemp'] == 'F':
                avgTemp0F = avgTemp0
            else:
                print('ERROR: mntemp input units should be C or F!')
                sys.exit(1)
            if avgTemp0F < DEGREE_DAY_BASE:
                # Heating degree days.
                degreeDays = DEGREE_DAY_BASE - avgTemp0F
                heatingDegreeDaysMonthYear[yyyymm] = heatingDegreeDaysMonthYear.get(yyyymm, [])
                heatingDegreeDaysMonthYear[yyyymm].append(degreeDays)
                heatingDegreeDaysYear[yyyy] = heatingDegreeDaysYear.get(yyyy, [])
                heatingDegreeDaysYear[yyyy].append(degreeDays)
            elif avgTemp0F > DEGREE_DAY_BASE:
                # Cooling degree days.
                degreeDays = avgTemp0F - DEGREE_DAY_BASE
                coolingDegreeDaysMonthYear[yyyymm] = coolingDegreeDaysMonthYear.get(yyyymm, [])
                coolingDegreeDaysMonthYear[yyyymm].append(degreeDays)
                coolingDegreeDaysYear[yyyy] = coolingDegreeDaysYear.get(yyyy, [])
                coolingDegreeDaysYear[yyyy].append(degreeDays)
        else:
            avgTemp0 = None
        # Daily precipitation amount.
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
            precipMonthYear[yyyymm] = precipMonthYear.get(yyyymm, [])
            precipMonthYear[yyyymm].append(tprecip)
            varYear['tprecip'][yyyy] = varYear['tprecip'].get(yyyy, [])
            varYear['tprecip'][yyyy].append(tprecip)
            precipYear[yyyy] = precipYear.get(yyyy, [])
            precipYear[yyyy].append(tprecip)
            # Keep track of precip by day of year.
            varDay['tprecip'][mmdd] = varDay['tprecip'].get(mmdd, [])
            varDay['tprecip'][mmdd].append(tprecip)
            if (examine and 
                examineVariable == 'tprecip' and
                int(mm) == int(examineMonth)):
                examineData[dt] = tprecip
            # Save any days with 1 inch of precip or more.
            if tprecip >= 1.0:
                highestPrecipDays[yyyy+mm+dd] = tprecip
            # Save yearly monsoon precip, between June 15 and September 30.
            if ((int(mm) == 6 and int(dd) >= 15) or
                (int(mm) >= 7 and int(mm) <= 9)):
                monsoonPrecipYear[yyyy] = monsoonPrecipYear.get(yyyy, [])
                monsoonPrecipYear[yyyy].append(tprecip)
            # Save yearly winter precip, between November 1 and March 31.
            if (int(mm) >= 11 and int(mm) <= 12):
                yyyyNext = str(int(yyyy) + 1)
                winterPrecipYear[yyyyNext] = winterPrecipYear.get(yyyyNext, [])
                winterPrecipYear[yyyyNext].append(tprecip)
            if (int(mm) >= 1 and int(mm) <= 3):
                winterPrecipYear[yyyy] = winterPrecipYear.get(yyyy, [])
                winterPrecipYear[yyyy].append(tprecip)
        # Daily snow amount.
        try:
            tsnowf = checkOneValue(row[column['tsnowf']], nFlagged['tsnowf'],
                                    rangeCheckVar=rangeCheckVar['tsnowf'], 
                                    nOutOfRange=nOutOfRange['tsnowf']) 
        except KeyError:
            tsnowf = None
        if tsnowf is not None:
            tsnowf = float(row[column['tsnowf']])  
            # -1 means a trace, so change to zero.
            if tsnowf == -1.0:
                tsnowf = 0.0
            varAll['tsnowf'].append(tsnowf)
            varMonth['tsnowf'][mm].append(tsnowf)
            snowMonthYear[yyyymm] = snowMonthYear.get(yyyymm, [])
            snowMonthYear[yyyymm].append(tsnowf)
            varYear['tsnowf'][yyyy] = varYear['tsnowf'].get(yyyy, [])
            varYear['tsnowf'][yyyy].append(tsnowf)
            snowYear[yyyy] = snowYear.get(yyyy, [])
            snowYear[yyyy].append(tsnowf)
            # Keep track of snow by day of year.
            varDay['tsnowf'][mmdd] = varDay['tsnowf'].get(mmdd, [])
            varDay['tsnowf'][mmdd].append(tsnowf)
            if (examine and 
                examineVariable == 'tsnowf' and
                int(mm) == int(examineMonth)):
                examineData[dt] = tsnowf
                
        # -------------------------------------------------
        # If at least one variable is good, save this time.
        # -------------------------------------------------
        if (mxtemp is not None or 
            mntemp is not None or
            tprecip is not None or
            tsnowf is not None):
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
nYears = 0
years = []
for dt in dtAll:
    yyyy = datetime.strftime(dt, '%Y')
    if yyyyPrev == 0:
        # Initialize yyyyPrev.
        yyyyPrev = yyyy
        # Start years list.
        years.append(yyyy)
    if (yyyyPrev != 0 and
        yyyy != yyyyPrev):
        # Print result for one year.
        printPresentPct(yyyyPrev, nPresent, nMissing)
        print('------------------------------')
        # Add this year to total.
        nTotal = nTotal + nPresent
        # Build list of years.
        years.append(yyyy)
        # If data was found for this year, add to total of years, used
        #   for calculating some averages.
        if nPresent > 0:
            nYears += 1
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
nYears += 1

# Total number of years in this climatology.
print('\nTotal number of years in this climatology: {:2d}'.format(nYears))

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

# -------------------------------------------------
# Calculate daily average max and min temperatures
#   and write to a file.
# -------------------------------------------------
print('\nCalculate daily average max and min for each day of the year:')
# Write file of data for a report.
csvFile = 'DailyNorms.csv'
print('Writing csv file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write('mm, dd, Tmax(F), Tmin(F)\n')
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        for day in range(1, 32):
            dd = '{:02d}'.format(day)
            mmdd = mm + dd
            if mmdd != '0229':  # Ignore leap day.
                try:
                    mxtempAvg = TC2F(statistics.mean(varDay['mxtemp'][mmdd]))
                    mntempAvg = TC2F(statistics.mean(varDay['mntemp'][mmdd]))
                    csvOut.write('{:d}, {:d}, {:d}, {:d}\n'.format(int(mm), int(dd), 
                                                                   int(round(mxtempAvg)), int(round(mntempAvg))))
                except KeyError:  # Skip last day(s) for months that don't have 31 days.  
                    pass

# ----------------------------
# Average precip for each day.
# ----------------------------
print('\nCalculate daily average precipitation for each day of the year:')
# Write file of data for a report.
csvFile = 'DailyPrecip.csv'
print('Writing csv file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write('mm, dd, Average Precip, Cumulative Precip, Average Snowfall, Cumulative Snowfall\n')
    precipCum = 0.0
    snowCum = 0.0
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        for day in range(1, 32):
            dd = '{:02d}'.format(day)
            mmdd = mm + dd
            if mmdd != '0229':  # Ignore leap day.
                try:
                    # Assume precip for missing days is zero.
                    nObs = len(varDay['tprecip'][mmdd])
                    if nObs < nYears:
                        for y in range(nObs+1, nYears+1):
                            varDay['tprecip'][mmdd].append(0.0)
                    # Average and cumulative precip for the date.
                    precipAvg = statistics.mean(varDay['tprecip'][mmdd])
                    precipCum += precipAvg
                    # Average and cumulative snow for the date.
                    snowAvg = statistics.mean(varDay['tsnowf'][mmdd])
                    snowCum += snowAvg
                    csvOut.write('{:d}, {:d}, {:.2f}, {:.2f}, {:.1f}, {:.1f}\n'.format(
                        int(mm), 
                        int(dd), 
                        round(precipAvg,2),
                        round(precipCum,2),
                        round(snowAvg,1),
                        round(snowCum,1)))
                except KeyError:  # Skip last day(s) for months that don't have 31 days.  
                    pass

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
        # Save Tavg, Tmax and Tmin to write Normals.csv file below.
        if var == 'avgTemp0':
            avgTemp0AverageMonth = averageMonth
            avgTemp0AverageAnnual = averageAll[var]
        elif var == 'mxtemp':
            mxtempAverageMonth = averageMonth
            mxtempAverageAnnual = averageAll[var]
        elif var == 'mntemp':
            mntempAverageMonth = averageMonth
            mntempAverageAnnual = averageAll[var]

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
        try:
            maximum = max(varMonthTotals)
        except ValueError:
            maximum = 0.0
        try:
            minimum = min(varMonthTotals)
        except ValueError:
            minimum = 0.0
        try:
            averageMonth[mm] = statistics.mean(varMonthTotals)
        except ValueError:
            averageMonth[mm] = 0.0
        try:
            median = statistics.median(varMonthTotals)
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
    # Save Tavg, Tmax and Tmin to write Normals.csv file below.
    precipAverageMonth = averageMonth
    precipAverageAnnual = averageAnnual

# -------------------------------
# Calculate monthly snow stats.
# -------------------------------
if len(snowMonthYear.keys()) > 0:
    print('\nMaximums, minimums, averages and medians for monthly total snowfall:')
    print('         month       maximum       minimum       average        median')
    print(' ------------- ------------- ------------- ------------- -------------')
    averageMonth = {}
    averageAnnual = 0.0
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        varMonthTotals = []
        for yyyymm in snowMonthYear.keys():
            if int(yyyymm[-2:]) == month:
                varMonthTotal = sum(snowMonthYear[yyyymm])
                varMonthTotals.append(varMonthTotal)
        try:        
            maximum = max(varMonthTotals)
        except ValueError:
            maximum = 0.0
        try:        
            minimum = min(varMonthTotals)
        except ValueError:
            minimum = 0.0
        try:        
            averageMonth[mm] = statistics.mean(varMonthTotals)
        except ValueError:
            averageMonth[mm] = 0.0
        try:        
            median = statistics.median(varMonthTotals)
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
        averageAnnual += averageMonth[mm]
    print('Annual average: {:.2f}'.format(averageAnnual))
    # Write file of data for a report.
    csvFile = 'snow.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('month,snow\n')
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            csvOut.write('{:s}, {:.2f}\n'.format(monthName[month-1], averageMonth[mm]))
        csvOut.write('{:s}, {:.2f}\n'.format('Annual', averageAnnual))
    # Write another file of monthly average Tavg, Tmax, Tmin, precip and snowfall, temps in F.
    print('\nWrite monthly average Tavg, Tmax, Tmin, precip and snowfall:')
    csvFile = 'Normals.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('Month,Tavg(F),Tmax(F),Tmin(F),Precip(in.),Snow(in.)\n')
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            Tavg = TC2F(avgTemp0AverageMonth[mm])
            Tmax = TC2F(mxtempAverageMonth[mm])
            Tmin = TC2F(mntempAverageMonth[mm])
            csvOut.write('{:s},{:.1f},{:.1f},{:.1f},{:.2f},{:.1f}\n'.format(monthName[month-1][0:3], Tavg, Tmax, Tmin,
                                                                            precipAverageMonth[mm], averageMonth[mm]))
        TavgAverageAnnual = TC2F(avgTemp0AverageAnnual)
        TmaxAverageAnnual = TC2F(mxtempAverageAnnual)
        TminAverageAnnual = TC2F(mntempAverageAnnual)
        csvOut.write('{:s},{:.1f},{:.1f},{:.1f},{:.2f},{:.1f}\n'.format('Annual',TavgAverageAnnual,
                                                                        TmaxAverageAnnual,TminAverageAnnual,
                                                                        precipAverageAnnual,averageAnnual))

    # ----------------------------------------    
    # Calculate stats for days of high precip.
    # ----------------------------------------    
    print('\nNumber of days with precipitation above threshold:', PRECIP_DAILY_HIGH_THRESH, 'inches')
    print('         month       maximum       minimum       average        median')
    print(' ------------- ------------- ------------- ------------- -------------')
    averageMonth = {}
    averageAnnual = 0.0
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        varMonthTotals = []
        for yyyymm in precipMonthYear.keys():
            if int(yyyymm[-2:]) == month:
                varMonthTotal = 0
                for precipDay in precipMonthYear[yyyymm]:
                    if precipDay > PRECIP_DAILY_HIGH_THRESH:
                        varMonthTotal += 1 
                        varMonthTotals.append(varMonthTotal)
        if len(varMonthTotals) >= 1:
            maximum = max(varMonthTotals)
            minimum = min(varMonthTotals)
            averageMonth[mm] = statistics.mean(varMonthTotals)
            median = statistics.median(varMonthTotals)
        else:
            maximum = minimum = averageMonth[mm] = median = 0
        print(' {:13d} {:13.1f} {:13.1f} {:13.1f} {:13.1f}'.format(
            int(mm),
            maximum, minimum,
            averageMonth[mm], median))
        averageAnnual += averageMonth[mm]
    print('Annual average: {:.1f}'.format(averageAnnual))
    # Write file of data for a report.
    csvFile = 'nHighPrecipDays.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('month,ndays\n')
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            csvOut.write('{:s}, {:.1f}\n'.format(monthName[month-1], averageMonth[mm]))
        csvOut.write('{:s}, {:.1f}\n'.format('Annual', averageAnnual))
    # Show highest precip days (>=1 inch).
    highest = sorted([(value, key) for (key, value) in highestPrecipDays.items()], reverse=True)
    print('\nHighest precip days (>= 1 inch):\n',
          'yyyymmdd   tprecip\n',
          '--------  --------')
    for (precip, yyyymmdd) in highest:
        print(' {:8s}  {:8.2f}'.format(yyyymmdd, precip))

# -----------------------------------------------------------  
# Calculate stats for days of very high temperatures.
# -----------------------------------------------------------
# Monthly.
print('\nNumber of days with temperature at or above threshold:', TEMP_DAILY_HIGH_THRESH, 'F')
print('         month       average')
print(' ------------- -------------')
averageMonth = {}
averageAnnual = 0.0
for month in range(1, 13):
    mm = '{:02d}'.format(month)
    varMonthTotal = 0
    for temp in varMonth['mxtemp'][mm]:
        temp = input2optional(
            unitsInput['mxtemp'], unitsOptional['mxtemp'], 
            temp)
        if temp[0] >= TEMP_DAILY_HIGH_THRESH:
            varMonthTotal += 1 
    averageMonth[mm] = varMonthTotal / N_YEARS
    print(' {:13d} {:13.1f}'.format(int(mm),averageMonth[mm]))
    averageAnnual += averageMonth[mm]
print('Annual average: {:.1f}'.format(averageAnnual))
# Write file of data for a report.
csvFile = 'nHighTempDaysMonth.csv'
print('Writing csv file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write('month,ndays\n')
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        csvOut.write('{:s}, {:.1f}\n'.format(monthName[month-1], averageMonth[mm]))
    csvOut.write('{:s}, {:.1f}\n'.format('Annual', averageAnnual))

# Yearly.
print('\nNumber of days with temperature at or above threshold:', TEMP_DAILY_HIGH_THRESH, 'F')
print('          year         total')
print(' ------------- -------------')
totalYear = {}
averageAnnual = 0.0
for yyyy in varYear['mxtemp'].keys():
    varYearTotal = 0
    for temp in varYear['mxtemp'][yyyy]:
        temp = input2optional(
            unitsInput['mxtemp'], unitsOptional['mxtemp'], 
            temp)
        if round(temp[0],1) >= TEMP_DAILY_HIGH_THRESH:
            varYearTotal += 1 
    averageAnnual += varYearTotal
    print(' {:13d} {:13d}'.format(int(yyyy),varYearTotal))
    totalYear[yyyy] = varYearTotal
if averageAnnual > 0.0:
    averageAnnual = averageAnnual / N_YEARS
print('Annual average: {:.1f}'.format(averageAnnual))
# Write file of data for a report.
csvFile = 'nHighTempDaysYear.csv'
print('Writing csv file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write('year,ndays\n')
    for yyyy in varYear['mxtemp'].keys():
        csvOut.write('{:s}, {:.1f}\n'.format(yyyy, totalYear[yyyy]))
    csvOut.write('{:s}, {:.1f}\n'.format('Annual', averageAnnual))

# -----------------------------------------------------------  
# Calculate stats for days of very low temperatures.
# -----------------------------------------------------------
print('\nNumber of days with temperature at or below threshold:', TEMP_DAILY_LOW_THRESH, 'F')
print('         month       average')
print(' ------------- -------------')
averageMonth = {}
averageAnnual = 0.0
for month in range(1, 13):
    mm = '{:02d}'.format(month)
    varMonthTotal = 0
    for temp in varMonth['mntemp'][mm]:
        temp = input2optional(
            unitsInput['mntemp'], unitsOptional['mntemp'], 
            temp)
        if temp[0] <= TEMP_DAILY_LOW_THRESH:
            varMonthTotal += 1 
    averageMonth[mm] = varMonthTotal / N_YEARS
    print(' {:13d} {:13.1f}'.format(int(mm),averageMonth[mm]))
    averageAnnual += averageMonth[mm]
print('Annual average: {:.1f}'.format(averageAnnual))
# Write file of data for a report.
csvFile = 'nLowTempDaysMonth.csv'
print('Writing csv file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write('month,ndays\n')
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        csvOut.write('{:s}, {:.1f}\n'.format(monthName[month-1], averageMonth[mm]))
    csvOut.write('{:s}, {:.1f}\n'.format('Annual', averageAnnual))

# Yearly.
print('\nNumber of days with temperature at or below threshold:', TEMP_DAILY_LOW_THRESH, 'F')
print('          year         total')
print(' ------------- -------------')
totalYear = {}
averageAnnual = 0.0
for yyyy in varYear['mntemp'].keys():
    varYearTotal = 0
    for temp in varYear['mntemp'][yyyy]:
        temp = input2optional(
            unitsInput['mntemp'], unitsOptional['mntemp'], 
            temp)
        if round(temp[0],1) <= TEMP_DAILY_LOW_THRESH:
            varYearTotal += 1 
    averageAnnual += varYearTotal
    print(' {:13d} {:13d}'.format(int(yyyy),varYearTotal))
    totalYear[yyyy] = varYearTotal
if averageAnnual > 0.0:
    averageAnnual = averageAnnual / N_YEARS
print('Annual average: {:.1f}'.format(averageAnnual))
# Write file of data for a report.
csvFile = 'nLowTempDaysYear.csv'
print('Writing csv file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write('year,ndays\n')
    for yyyy in varYear['mntemp'].keys():
        csvOut.write('{:s}, {:.1f}\n'.format(yyyy, totalYear[yyyy]))
    csvOut.write('{:s}, {:.1f}\n'.format('Annual', averageAnnual))

# ---------------------------------------------------
# Calculate monthly heating and cooling degree stats.
# ---------------------------------------------------
# Heating degree days.
print('\nMaximums, minimums, averages and medians for monthly heating degree days:')
print('         month       maximum       minimum       average        median')
print(' ------------- ------------- ------------- ------------- -------------')
averageMonth = {}
averageAnnual = 0.0
for month in range(1, 13):
    mm = '{:02d}'.format(month)
    varMonthTotals = []
    for yyyymm in heatingDegreeDaysMonthYear.keys():
        if int(yyyymm[-2:]) == month:
            varMonthTotal = sum(heatingDegreeDaysMonthYear[yyyymm])
            varMonthTotals.append(varMonthTotal)
    try:
        maximum = max(varMonthTotals)
    except:
        maximum = 0.0
    try:
        minimum = min(varMonthTotals)
    except:
        minimum = 0.0
    try:
        averageMonth[mm] = statistics.mean(varMonthTotals)
    except:
        averageMonth[mm] = 0.0
    try:
        median = statistics.median(varMonthTotals)
    except:
        median = 0.0
    if (unitsInput[var] != unitsOptional[var] and
        changeUnits == True):
        # Convert to optional units.
        results = (maximum, minimum, averageMonth[mm], median)
        maximum, minimum, averageMonth[mm], median = input2optional(
            unitsInput[var], unitsOptional[var], 
            *results)
    print(' {:13d} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(int(mm),
                                                               maximum, minimum,
                                                               averageMonth[mm], median))
    averageAnnual += averageMonth[mm]
print('Annual average: {:.1f}'.format(averageAnnual))
# Write file of data for a report.
csvFile = 'heatingDegreeDays.csv'
print('Writing csv file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write('month,degreeDays\n')
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        csvOut.write('{:s}, {:.1f}\n'.format(monthName[month-1], averageMonth[mm]))
    csvOut.write('{:s}, {:.1f}\n'.format('Annual', averageAnnual))

# Cooling degree days.
print('\nMaximums, minimums, averages and medians for monthly cooling degree days:')
print('         month       maximum       minimum       average        median')
print(' ------------- ------------- ------------- ------------- -------------')
averageMonth = {}
averageAnnual = 0.0
for month in range(1, 13):
    mm = '{:02d}'.format(month)
    varMonthTotals = []
    for yyyymm in coolingDegreeDaysMonthYear.keys():
        if int(yyyymm[-2:]) == month:
            varMonthTotal = sum(coolingDegreeDaysMonthYear[yyyymm])
            varMonthTotals.append(varMonthTotal)
    if len(varMonthTotals) > 0:
        maximum = max(varMonthTotals)
        minimum = min(varMonthTotals)
        averageMonth[mm] = statistics.mean(varMonthTotals)
        median = statistics.median(varMonthTotals)
    else:
        maximum = minimum = averageMonth[mm] = median = 0.0
    if (unitsInput[var] != unitsOptional[var] and
        changeUnits == True):
        # Convert to optional units.
        results = (maximum, minimum, averageMonth[mm], median)
        maximum, minimum, averageMonth[mm], median = input2optional(
            unitsInput[var], unitsOptional[var], 
            *results)
    print(' {:13d} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(int(mm),
                                                               maximum, minimum,
                                                               averageMonth[mm], median))
    averageAnnual += averageMonth[mm]
print('Annual average: {:.1f}'.format(averageAnnual))
# Write file of data for a report.
csvFile = 'coolingDegreeDays.csv'
print('Writing csv file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write('month,degreeDays\n')
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        csvOut.write('{:s}, {:.1f}\n'.format(monthName[month-1], averageMonth[mm]))
    csvOut.write('{:s}, {:.1f}\n'.format('Annual', averageAnnual))

# ----------------------
# Repeat for each year
# ----------------------
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
        
# -----------------------------------------
# Calculate yearly total degree days stats.
# -----------------------------------------
# Heating degree days.
print('\nMaximums, minimums, averages and medians for yearly total heating degree days:')
print('       maximum       minimum       average        median')
print(' ------------- ------------- ------------- -------------')
varYearTotals = []
for yyyy in heatingDegreeDaysYear.keys():
    varYearTotal = sum(heatingDegreeDaysYear[yyyy])
    varYearTotals.append(varYearTotal)
maximum = max(varYearTotals)
minimum = min(varYearTotals)
average = statistics.mean(varYearTotals)
median = statistics.median(varYearTotals)
if (unitsInput[var] != unitsOptional[var] and
    changeUnits == True):
    # Convert to optional units.
    results = (maximum, minimum, average, median)
    maximum, minimum, average, median = input2optional(
        unitsInput[var], unitsOptional[var], 
        *results)
print(' {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(maximum, minimum,
                                                    average, median))
# Cooling degree days.
print('\nMaximums, minimums, averages and medians for yearly total cooling degree days:')
print('       maximum       minimum       average        median')
print(' ------------- ------------- ------------- -------------')
varYearTotals = []
for yyyy in coolingDegreeDaysYear.keys():
    varYearTotal = sum(coolingDegreeDaysYear[yyyy])
    varYearTotals.append(varYearTotal)
maximum = max(varYearTotals)
minimum = min(varYearTotals)
average = statistics.mean(varYearTotals)
median = statistics.median(varYearTotals)
if (unitsInput[var] != unitsOptional[var] and
    changeUnits == True):
    # Convert to optional units.
    results = (maximum, minimum, average, median)
    maximum, minimum, average, median = input2optional(
        unitsInput[var], unitsOptional[var], 
        *results)
print(' {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(maximum, minimum,
                                                    average, median))

# ------------------------------------
# Calculate yearly total precip stats.
# ------------------------------------
if len(precipYear.keys()) > 0:
    print('\nMaximums, minimums, averages and medians for yearly total precipitation:')
    print('       maximum       minimum       average        median')
    print(' ------------- ------------- ------------- -------------')
    varYearTotals = []
    for yyyy in precipYear.keys():
        varYearTotal = sum(precipYear[yyyy])
        varYearTotals.append(varYearTotal)
    maximum = max(varYearTotals)
    minimum = min(varYearTotals)
    average = statistics.mean(varYearTotals)
    median = statistics.median(varYearTotals)
    if (unitsInput[var] != unitsOptional[var] and
        changeUnits == True):
        # Convert to optional units.
        results = (maximum, minimum, average, median)
        maximum, minimum, average, median = input2optional(
            unitsInput[var], unitsOptional[var], 
            *results)
    print(' {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(maximum, minimum,
                                                        average, median))
    # ------------------------------------
    # Calculate yearly monsoon precip.
    # ------------------------------------
    print('\nMonsoon precipitation (Jun 15-Sep 30)')
    print('          year         total')
    print(' ------------- -------------')
    totalYear = {}
    averageAnnual = 0.0
    for yyyy in monsoonPrecipYear.keys():
        varYearTotal = 0
        varYearTotal = sum(monsoonPrecipYear[yyyy])
        averageAnnual += varYearTotal
        print(' {:13d} {:13.2f}'.format(int(yyyy),varYearTotal))
        totalYear[yyyy] = varYearTotal
    if averageAnnual > 0.0:
        averageAnnual = averageAnnual / N_YEARS
    print('Annual average: {:.2f}'.format(averageAnnual))
    # Write file of data for a report.
    csvFile = 'monsoonPrecip.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('year,precip\n')
        for yyyy in monsoonPrecipYear.keys():
            csvOut.write('{:s}, {:.2f}\n'.format(yyyy, totalYear[yyyy]))
        csvOut.write('{:s}, {:.2f}\n'.format('Annual', averageAnnual))
    # ------------------------------------
    # Calculate yearly winter precip.
    # ------------------------------------
    print('\nWinter precipitation (Nov 1-Mar 31, year of the end of the season)')
    print('Note that the first and last years will be partial')
    print('          year         total')
    print(' ------------- -------------')
    totalYear = {}
    averageAnnual = 0.0
    for yyyy in winterPrecipYear.keys():
        varYearTotal = 0
        varYearTotal = sum(winterPrecipYear[yyyy])
        averageAnnual += varYearTotal
        print(' {:13d} {:13.2f}'.format(int(yyyy),varYearTotal))
        totalYear[yyyy] = varYearTotal
    if averageAnnual > 0.0:
        averageAnnual = averageAnnual / N_YEARS
    #print('Annual average: {:.1f}'.format(averageAnnual)) # Don't print because it is not correct.
    # Write file of data for a report.
    csvFile = 'winterPrecip.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('year,precip\n')
        for yyyy in winterPrecipYear.keys():
            csvOut.write('{:s}, {:.2f}\n'.format(yyyy, totalYear[yyyy]))
        #csvOut.write('{:s}, {:.2f}\n'.format('Annual', averageAnnual)) # Don't write because it is not correct.

# -----------------------------------------------------
# Print latest and earliest freeze dates for each year,
#   and calculate averages.
# -----------------------------------------------------
print('\nEarliest and latest freezes for each year:')
yyyyCalc = datetime.strftime(datetime.utcnow(), '%Y')
timestampLasts = []
timestampFirsts = []
print(' yyyy  first')
print(' ---- -----')
for yyyy in firstFreeze.keys():
    if firstFreeze[yyyy] is not None:
        print(' {:4s} {:2s}/{:2s}'.format(yyyy, 
                                          firstFreeze[yyyy][0:2], firstFreeze[yyyy][2:4]))
print('\n yyyy  last')
print(' ---- -----')
for yyyy in lastFreeze.keys():
    if lastFreeze[yyyy] is not None:
        print(' {:4s} {:2s}/{:2s}'.format(yyyy, 
                                      lastFreeze[yyyy][0:2], lastFreeze[yyyy][2:4]))
    if (lastFreeze[yyyy] is not None and
        firstFreeze[yyyy] is not None):
        # Average by calculating timestamps in the same arbitrary year (use current year).
        yyyymmddLast = yyyyCalc + lastFreeze[yyyy]
        dtLast = datetime.strptime(yyyymmddLast, '%Y%m%d')
        timestampLast = dtLast.timestamp()
        timestampLasts.append(timestampLast)
        yyyymmddFirst = yyyyCalc + firstFreeze[yyyy]
        dtFirst = datetime.strptime(yyyymmddFirst, '%Y%m%d')
        timestampFirst = dtFirst.timestamp()
        timestampFirsts.append(timestampFirst)
# Calculate and print averages.
if (len(timestampLasts) > 0 and
    len(timestampFirsts) > 0):
    timestampLastAvg = statistics.mean(timestampLasts)
    dtLastAvg = datetime.fromtimestamp(timestampLastAvg)
    mmddLastAvg = dtLastAvg.strftime('%m/%d')
    timestampFirstAvg = statistics.mean(timestampFirsts)
    dtFirstAvg = datetime.fromtimestamp(timestampFirstAvg)
    mmddFirstAvg = dtFirstAvg.strftime('%m/%d')
    delta = dtFirstAvg - dtLastAvg 
    growingDays = delta.days - 1
    print('\nAverage latest freeze: {:5s}'.format(mmddLastAvg))
    print('Average earliest freeze: {:5s}'.format(mmddFirstAvg))
    print('Average growing season: {:d} days'.format(growingDays))

# ------------------------------------
# Show max temperature for each month.
# ------------------------------------
if len(mxtempMonthYear.keys()) > 0:
    print('\nMxtemp average for each month:')
    print('yyyymmdd   average\n',
          '--------  --------')
    resultMonthYear = {}
    for yyyy in years:
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            yyyymm = yyyy + mm
            try:
                varMonthAverage = statistics.mean(mxtempMonthYear[yyyymm])
            except KeyError:
                continue
            if (unitsInput['mxtemp'] != unitsOptional['mxtemp'] and
                changeUnits == True):
                # Convert to optional units.
                resultList = input2optional(
                    unitsInput['mxtemp'], unitsOptional['mxtemp'], 
                    varMonthAverage)
                resultMonthYear[yyyymm] = resultList[0] 
            else:
                resultMonthYear[yyyymm] = varMonthAverage
            print(' {:8s}  {:8.2f}'.format(yyyymm, resultMonthYear[yyyymm]))
    # Write file of data for a report.
    csvFile = 'monthlyMxtemp.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('month-year,mxtemp\n')
        for yyyymm in mxtempMonthYear.keys():
            yyyy = yyyymm[0:4]
            month = int(yyyymm[-2:])
            datestring = monthName[month-1][0:3] + '-' + yyyy
            csvOut.write('{:s}, {:.2f}\n'.format(datestring, resultMonthYear[yyyymm]))

# ------------------------------------
# Show min temperature for each month.
# ------------------------------------
if len(mntempMonthYear.keys()) > 0:
    print('\nMntemp average for each month:')
    print('yyyymmdd   average\n',
          '--------  --------')
    resultMonthYear = {}
    for yyyy in years:
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            yyyymm = yyyy + mm
            try:
                varMonthAverage = statistics.mean(mntempMonthYear[yyyymm])
            except KeyError:
                continue
            if (unitsInput['mntemp'] != unitsOptional['mntemp'] and
                changeUnits == True):
                # Convert to optional units.
                resultList = input2optional(
                    unitsInput['mntemp'], unitsOptional['mntemp'], 
                    varMonthAverage)
                resultMonthYear[yyyymm] = resultList[0] 
            else:
                resultMonthYear[yyyymm] = varMonthAverage
            print(' {:8s}  {:8.2f}'.format(yyyymm, resultMonthYear[yyyymm]))
    # Write file of data for a report.
    csvFile = 'monthlyMntemp.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('month-year,mntemp\n')
        for yyyymm in mntempMonthYear.keys():
            yyyy = yyyymm[0:4]
            month = int(yyyymm[-2:])
            datestring = monthName[month-1][0:3] + '-' + yyyy
            csvOut.write('{:s}, {:.2f}\n'.format(datestring, resultMonthYear[yyyymm]))

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
            csvOut.write('{:s}, {:.2f}\n'.format(datestring, resultMonthYear[yyyymm]))

# ----------------------------------------
# Show heating degree days for each month.
# ----------------------------------------
if len(precipMonthYear.keys()) > 0:
    print('\nHeating degree day total for each month:')
    print('yyyymmdd     total\n',
          '--------  --------')
    resultMonthYear = {}
    for yyyy in years:
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            yyyymm = yyyy + mm
            try:
                varMonthTotal = sum(heatingDegreeDaysMonthYear[yyyymm])
            except KeyError:
                varMonthTotal = 0.0
            resultMonthYear[yyyymm] = varMonthTotal
            print(' {:8s}  {:8.2f}'.format(yyyymm, resultMonthYear[yyyymm]))
    # Write file of data for a report.
    csvFile = 'monthlyHeatingDegreeDays.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('month-year,heating degree days\n')
        for yyyymm in resultMonthYear.keys():
            yyyy = yyyymm[0:4]
            month = int(yyyymm[-2:])
            datestring = monthName[month-1][0:3] + '-' + yyyy
            csvOut.write('{:s}, {:.2f}\n'.format(datestring, resultMonthYear[yyyymm]))

# ----------------------------------------
# Show cooling degree days for each month.
# ----------------------------------------
if len(precipMonthYear.keys()) > 0:
    print('\nCooling degree day total for each month:')
    print('yyyymmdd     total\n',
          '--------  --------')
    resultMonthYear = {}
    for yyyy in years:
        for month in range(1, 13):
            mm = '{:02d}'.format(month)
            yyyymm = yyyy + mm
            try:
                varMonthTotal = sum(coolingDegreeDaysMonthYear[yyyymm])
            except KeyError:
                varMonthTotal = 0.0
            resultMonthYear[yyyymm] = varMonthTotal
            print(' {:8s}  {:8.2f}'.format(yyyymm, resultMonthYear[yyyymm]))
    # Write file of data for a report.
    csvFile = 'monthlyCoolingDegreeDays.csv'
    print('Writing csv file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('month-year,cooling degree days\n')
        for yyyymm in resultMonthYear.keys():
            yyyy = yyyymm[0:4]
            month = int(yyyymm[-2:])
            datestring = monthName[month-1][0:3] + '-' + yyyy
            csvOut.write('{:s}, {:.2f}\n'.format(datestring, resultMonthYear[yyyymm]))

if OUTLIERS:
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

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
