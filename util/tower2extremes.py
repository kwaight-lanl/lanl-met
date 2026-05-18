#!/usr/bin/env python3

"""
tower2extremes.py
Read a 15-min csv file for one tower site, calculate maximums, mininums.
Usage: python tower2extremes.py [-v] [-changeunits] metfile  
  metfile is the name of the met file to read. It is assumed to be in the format downloaded from the Weather Machine.
  -changeunits will print the results in an optional set of units defined below.
Ken Waight / February 2021
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
from collections import OrderedDict

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

# ==============
# MAIN PROGRAM.
# ==============
# ----------
# Constants.
# ----------
# Constraints used to eliminate obviously bad data.
WIND_SPEED_MAX = 200.0  # Maximum wind speed that will be allowed. Any higher or negative wind speeds will be reported
                        # and then ignored.
RELATIVE_HUMIDITY_MAX = 100.0  # Maximum relative humidity allowed (%).
SURFACE_PRESSURE_MIN = 700.0  # Minimum surface pressure allowed (mb).
SURFACE_PRESSURE_MAX = 900.0  # Maximum surface pressure allowed (mb).
SHORTWAVE_DOWN_MAX = 40.0  # Maximum downward shortwave allowed (MJ/m2).
SHORTWAVE_UP_MAX = 25.0  # Maximum upward shortwave allowed (MJ/m2).
LONGWAVE_DOWN_MAX = 40.0  # Maximum downward longwave allowed (MJ/m2).
LONGWAVE_UP_MAX = 50.0  # Maximum upward longwave allowed (MJ/m2).
NET_RADIATION_MAX = 30.0  # Maximum net radiation allowed (MJ/m2).
NET_RADIATION_MIN = -10.0  # Minimum net radiation allowed (MJ/m2).
# Other.

# ----------------------------------------------------------------
# Parse arguments.
# Get name of met file to read. There are two types:
#   1. A 24 hr file downloaded from the Weather Machine 
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a Weather Machine 15-min file and calculate maximums and minimums.")
parser.add_argument("metfile", help="Name of met file to read")
parser.add_argument("-changeunits", help="Change input to optional units for selected variables.",
                    action="store_true")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
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

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
# Variables to process.
vars = ['windSpeed1', 'vertVelocity1',
        'temp1', 'pres', 'RH1', 'Td1',
        'precip', 'snowDepth', 
        'swDown', 'swUp',
        'lwDown', 'lwUp', 
        'netRad',
        'windChill']
# Spreadsheet column names of the variables.
columnDateTime = 'Date/Time'
column = {}
column['windSpeed1'] = 'spd1'
column['vertVelocity1'] = 'w1'
column['temp1'] = 'temp1'
column['pres'] = 'press'
column['RH1'] = 'rh'
column['Td1'] = 'dewp'
column['precip'] = 'precip'
column['snowDepth'] = 'snowd'
column['swDown'] = 'swdn'
column['swUp'] = 'swup'
column['lwDown'] = 'lwdn'
column['lwUp'] = 'lwup'
column['netRad'] = 'netrad'
# Units of the variables in the input data.
unitsInput = {}
unitsInput['windSpeed1'] = 'm/s'
unitsInput['vertVelocity1'] = 'm/s'
unitsInput['temp1'] = 'C'
unitsInput['pres'] = 'mb'
unitsInput['RH1'] = '%'
unitsInput['Td1'] = 'C'
unitsInput['precip'] = 'in'
unitsInput['snowDepth'] = 'in'
unitsInput['swDown'] = 'W/m2'
unitsInput['swUp'] = 'W/m2'
unitsInput['lwDown'] = 'W/m2'
unitsInput['lwUp'] = 'W/m2'
unitsInput['netRad'] = 'W/m2'
unitsInput['windChill'] = 'C'
# Optional output units of the variables, default is to use original units.
unitsOptional = {}
unitsOptional['windSpeed1'] = 'mph'
unitsOptional['vertVelocity1'] = 'cm/s'
unitsOptional['temp1'] = 'F'
unitsOptional['pres'] = 'mb'
unitsOptional['RH1'] = '%'
unitsOptional['Td1'] = 'F'
unitsOptional['precip'] = 'mm'
unitsOptional['snowDepth'] = 'cm'
unitsOptional['swDown'] = 'W/m2'
unitsOptional['swUp'] = 'W/m2'
unitsOptional['lwDown'] = 'W/m2'
unitsOptional['lwUp'] = 'W/m2'
unitsOptional['netRad'] = 'W/m2'
unitsOptional['windChill'] = 'F'

# =======
# Banner.
# =======
print('\n ========================================================\n',
      'Find extremes from a met tower data file\n',
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
# Initialize dict for statistics by year.
varYear = {}
for var in vars:
    varYear[var] = {}

# --------------------------------------------------------------------
# Read LANL 15-min data at one tower location.
# --------------------------------------------------------------------
print("\nReading LANL file:", metFile)
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
             'year' in row.keys()) and 
            row[column['windSpeed1']] and
            row[column['vertVelocity1']] and
            row[column['temp1']] and
            row[column['pres']] and
            row[column['RH1']] and
            row[column['Td1']] and
            row[column['precip']] and
            row[column['snowDepth']] and
            row[column['swUp']] and
            row[column['swDown']] and
            row[column['lwUp']] and
            row[column['lwDown']] and
            row[column['netRad']]):
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
        # Check that data is good and save it.
        # ---------------------------------------------------------
        # Wind speed at level 1 (10 m) in m/s.
        if ('*' not in row[column['windSpeed1']] and  
            float(row[column['windSpeed1']]) >= 0.0 and
            float(row[column['windSpeed1']]) <=  WIND_SPEED_MAX):
            windSpeed1 = float(row[column['windSpeed1']])
            varAll['windSpeed1'].append(windSpeed1)
            varMonth['windSpeed1'][mm].append(windSpeed1)
            varYear['windSpeed1'][yyyy] = varYear['windSpeed1'].get(yyyy, [])
            varYear['windSpeed1'][yyyy].append(windSpeed1)
        else:
            windSpeed1 = None
        # Vertical velocity at level 1 in m/s.
        if ('*' not in row[column['vertVelocity1']] and  
            float(row[column['vertVelocity1']]) > 0.0):
            vertVelocity1 = float(row[column['vertVelocity1']])  
            varAll['vertVelocity1'].append(vertVelocity1)
            varMonth['vertVelocity1'][mm].append(vertVelocity1)
            varYear['vertVelocity1'][yyyy] = varYear['vertVelocity1'].get(yyyy, [])
            varYear['vertVelocity1'][yyyy].append(vertVelocity1)
        else:
            vertVelocity1 = None
        # Temperature at level 1 in C.
        if '*' not in row[column['temp1']]:
            temp1 = float(row[column['temp1']])  
            varAll['temp1'].append(temp1)
            varMonth['temp1'][mm].append(temp1)
            varYear['temp1'][yyyy] = varYear['temp1'].get(yyyy, [])
            varYear['temp1'][yyyy].append(temp1)
        else:
            temp1 = None
        # Calculate wind chill temperature in C.
        if (temp1 is not None and
            windSpeed1 is not None):
            temp1F = TC2F(temp1)
            windSpeed1Mph = wspdMs2Mph(windSpeed1)
            windChillF = calcWindChill(temp1F, windSpeed1Mph)
            windChill = TF2C(windChillF)
            varAll['windChill'].append(windChill)
            varMonth['windChill'][mm].append(windChill)
            varYear['windChill'][yyyy] = varYear['windChill'].get(yyyy, [])
            varYear['windChill'][yyyy].append(windChill)
        # Surface pressure in mb.
        if ('*' not in row[column['pres']] and  
            float(row[column['pres']]) >= SURFACE_PRESSURE_MIN and
            float(row[column['pres']]) <= SURFACE_PRESSURE_MAX):
            pres = float(row[column['pres']])
            varAll['pres'].append(pres)
            varMonth['pres'][mm].append(pres)
            varYear['pres'][yyyy] = varYear['pres'].get(yyyy, [])
            varYear['pres'][yyyy].append(pres)
        else:
            pres = None
        # Relative humidity at level 1 (10 m) in %.
        if ('*' not in row[column['RH1']] and  
            float(row[column['RH1']]) >= 0.0 and
            float(row[column['RH1']]) <=  RELATIVE_HUMIDITY_MAX):
            RH1 = float(row[column['RH1']])
            varAll['RH1'].append(RH1)
            varMonth['RH1'][mm].append(RH1)
            varYear['RH1'][yyyy] = varYear['RH1'].get(yyyy, [])
            varYear['RH1'][yyyy].append(RH1)
        else:
            RH1 = None
        # Dew point temperature at level 1 (10 m) in C.
        if '*' not in row[column['Td1']]:
            Td1 = float(row[column['Td1']])
            varAll['Td1'].append(Td1)
            varMonth['Td1'][mm].append(Td1)
            varYear['Td1'][yyyy] = varYear['Td1'].get(yyyy, [])
            varYear['Td1'][yyyy].append(Td1)
        else:
            Td1 = None
        # Precipitation amount in inches.
        if ('*' not in row[column['precip']] and 
            float(row[column['precip']]) >= 0.0):
            precip = float(row[column['precip']])  
            varAll['precip'].append(precip)
            varMonth['precip'][mm].append(precip)
            varYear['precip'][yyyy] = varYear['precip'].get(yyyy, [])
            varYear['precip'][yyyy].append(precip)
            precipYear[yyyy] = precipYear.get(yyyy, [])
            precipYear[yyyy].append(precip)
        else:
            precip = None
        # Snow depth in inches.
        if ('*' not in row[column['snowDepth']] and 
            float(row[column['snowDepth']]) >= 0.0):
            snowDepth = float(row[column['snowDepth']])  
            varAll['snowDepth'].append(snowDepth)
            varMonth['snowDepth'][mm].append(snowDepth)
            varYear['snowDepth'][yyyy] = varYear['snowDepth'].get(yyyy, [])
            varYear['snowDepth'][yyyy].append(snowDepth)
            snowDepthYear[yyyy] = snowDepthYear.get(yyyy, [])
            snowDepthYear[yyyy].append(snowDepth)
        else:
            snowDepth = None
        # Downward shortwave radiation (W/m2).
        if ('*' not in row[column['swDown']] and
            float(row[column['swDown']]) >= 0.0 and
            float(row[column['swDown']]) <= SHORTWAVE_DOWN_MAX):
            swDown = float(row[column['swDown']])
            varAll['swDown'].append(swDown)
            varMonth['swDown'][mm].append(swDown)
            varYear['swDown'][yyyy] = varYear['swDown'].get(yyyy, [])
            varYear['swDown'][yyyy].append(swDown)
        else:
            swDown = None
        # Upward shortwave radiation (W/m2).
        if ('*' not in row[column['swUp']] and
            float(row[column['swUp']]) >= 0.0 and
            float(row[column['swUp']]) <= SHORTWAVE_UP_MAX):
            swUp = float(row[column['swUp']])
            varAll['swUp'].append(swUp)
            varMonth['swUp'][mm].append(swUp)
            varYear['swUp'][yyyy] = varYear['swUp'].get(yyyy, [])
            varYear['swUp'][yyyy].append(swUp)
        else:
            swUp = None
        # Downward longwave radiation (W/m2).
        if ('*' not in row[column['lwDown']] and
            float(row[column['lwDown']]) >= 0.0 and
            float(row[column['lwDown']]) <= LONGWAVE_DOWN_MAX):
            lwDown = float(row[column['lwDown']])
            varAll['lwDown'].append(lwDown)
            varMonth['lwDown'][mm].append(lwDown)
            varYear['lwDown'][yyyy] = varYear['lwDown'].get(yyyy, [])
            varYear['lwDown'][yyyy].append(lwDown)
        else:
            lwDown = None
        # Upward longwave radiation (W/m2).
        if ('*' not in row[column['lwUp']] and
            float(row[column['lwUp']]) >= 0.0 and
            float(row[column['lwUp']]) <= LONGWAVE_UP_MAX):
            lwUp = float(row[column['lwUp']])
            varAll['lwUp'].append(lwUp)
            varMonth['lwUp'][mm].append(lwUp)
            varYear['lwUp'][yyyy] = varYear['lwUp'].get(yyyy, [])
            varYear['lwUp'][yyyy].append(lwUp)
        else:
            lwUp = None
        # Net radiation (W/m2).
        if ('*' not in row[column['netRad']] and
            float(row[column['netRad']]) >= NET_RADIATION_MIN and
            float(row[column['netRad']]) <= NET_RADIATION_MAX):
            netRad = float(row[column['netRad']])
            varAll['netRad'].append(netRad)
            varMonth['netRad'][mm].append(netRad)
            varYear['netRad'][yyyy] = varYear['netRad'].get(yyyy, [])
            varYear['netRad'][yyyy].append(netRad)
        else:
            netRad = None
        # -------------------------------------------------
        # If at least one variable is good, save this time.
        # -------------------------------------------------
        if (windSpeed1 is not None or
            vertVelocity1 is not None or
            temp1 is not None or 
            pres is not None or 
            RH1 is not None or 
            Td1 is not None or 
            precip is not None or
            snowDepth is not None or
            swUp is not None or
            swDown is not None or
            lwUp is not None or
            lwDown is not None or
            netRad is not None):
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

# -----------------------------------------
# Calculate and print averages and medians.
# -----------------------------------------
print('\n================')
print('Daily Statistics')
print('================')
print('\nDaily maximums, minimums, averages and medians for all times:')
print('      variable       maximum       minimum       average        median')
print(' ------------- ------------- ------------- ------------- -------------')
for var in vars:
    maximum = max(varAll[var])
    minimum = min(varAll[var])
    average = statistics.mean(varAll[var])
    median = statistics.median(varAll[var])
    if (unitsInput[var] != unitsOptional[var] and
        changeUnits == True):
        # Convert to optional units.
        results = (maximum, minimum, average, median)
        maximum, minimum, average, median = input2optional(
            unitsInput[var], unitsOptional[var], 
            *results)
    print(' {:13s} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(var,
                                                               maximum, minimum,
                                                               average, median))
# ----------------------
# Repeat for each month.
# ----------------------
print('\n==================')
print('Monthly Statistics')
print('==================')
for var in vars:
    print('\nMonthly maximums, minimums, averages and medians for {:s}:'.format(var))
    print('         month       maximum       minimum       average        median')
    print(' ------------- ------------- ------------- ------------- -------------')
    for month in range(1, 13):
        mm = '{:02d}'.format(month)
        maximum = max(varMonth[var][mm])
        minimum = min(varMonth[var][mm])
        average = statistics.mean(varMonth[var][mm])
        median = statistics.median(varMonth[var][mm])
        if (unitsInput[var] != unitsOptional[var] and
            changeUnits == True):
            # Convert to optional units.
            results = (maximum, minimum, average, median)
            maximum, minimum, average, median = input2optional(
                unitsInput[var], unitsOptional[var], 
                *results)
        print(' {:13d} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(int(mm),
                                                                   maximum, minimum,
                                                                   average, median))


# ----------------------
# Repeat for each year
# ----------------------
print('\n=================')
print('Yearly Statistics')
print('=================')
for var in vars:
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
        print(' {:13d} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format(int(yyyy),
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
    print(' {:13s} {:13.2f} {:13.2f} {:13.2f} {:13.2f}'.format('All'.rjust(13),
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

# -----------------------------------------------------
# Print latest and earliest freeze dates for each year,
#   and calculate averages.
# -----------------------------------------------------
print('\nLatest and earliest freezes for each year:')
print(' yyyy  last first')
print(' ---- ----- -----')
yyyyCalc = datetime.strftime(datetime.utcnow(), '%Y')
timestampLasts = []
timestampFirsts = []
for yyyy in firstFreeze.keys():
    print(' {:4s} {:2s}/{:2s} {:2s}/{:2s}'.format(yyyy, 
                                                  lastFreeze[yyyy][0:2], lastFreeze[yyyy][2:4], 
                                                  firstFreeze[yyyy][0:2], firstFreeze[yyyy][2:4]))
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

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
