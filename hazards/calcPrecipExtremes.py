#!/usr/bin/env python3

# ========
# IMPORTS.
# ========
import sys
import csv
from datetime import datetime, timedelta
import statistics
import math
import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.stats import rankdata
import argparse
from scipy.stats import genextreme as gev
import plotly.graph_objs as go
import plotly.io as pio

# ==============
# FUNCTIONS.
# ==============
def calcChowExtremes(returnPeriods, durations,
                     precipMax):
    """
    Apply the Chow et al. algorithm to estimate extreme values
       for a set of durations and return periods.
       Ken Waight / December 2019
    """
    precipAmount = {}
    precipRate = {}
    sqrt6 = math.sqrt(6.)
    for returnPeriod in returnPeriods:
        print('   ', returnPeriod, 'years:')
        yT = -math.log(math.log(returnPeriod / (returnPeriod - 1)))
        precipAmount[returnPeriod] = {}
        precipRate[returnPeriod] = {}
        for duration in durations:
            precipMaxAvg = statistics.mean(precipMax[duration].values())
            precipMaxStd = statistics.stdev(precipMax[duration].values())
            alpha = (sqrt6 * precipMaxStd) / math.pi
            u = precipMaxAvg - 0.5772 * alpha
            precipAmount[returnPeriod][duration] = u + alpha * yT
            # Convert extreme from inches to inches/hour.
            precipRate[returnPeriod][duration] = (precipAmount[returnPeriod][duration] * 60) / duration
            print('      {0: d} min: {1: .2f} in, {2: .2f} in/hr'.format(duration,
                                                                         precipAmount[returnPeriod][duration],
                                                                         precipRate[returnPeriod][duration]))

    # Return both extreme precip amounts and rates.
    return (precipAmount, precipRate)


def jac(x, u, y):
    """
    Jacobian function from curve fitting example.
    https://docs.scipy.org/doc/scipy/reference/tutorial/optimize.html#least-square-fitting-leastsq
    """
    J = np.empty((u.size, x.size))
    den = u ** 2 + x[2] * u + x[3]
    num = u ** 2 + x[1] * u
    J[:, 0] = num / den
    J[:, 1] = x[0] * u / den
    J[:, 2] = -x[0] * num * u / den ** 2
    J[:, 3] = -x[0] * num / den ** 2
    return J


def model(x, u):
    """
    Model function from curve fitting example.
    https://docs.scipy.org/doc/scipy/reference/tutorial/optimize.html#least-square-fitting-leastsq
    """
    return x[0] * (u ** 2 + x[1] * u) / (u ** 2 + x[2] * u + x[3])


def fun(x, u, y):
    """
    Residual function from curve fitting example.
    https://docs.scipy.org/doc/scipy/reference/tutorial/optimize.html#least-square-fitting-leastsq
    """
    return model(x, u) - y


def residual(x, precip, R, omega):
    """
    Function to calculate a residual, an error, the difference between precip calculated as a function of
      the return period from a Beta-P extreme value distribution, and and observed value of precip.
    x: list of the three parameters for the Beta-P curve, [alpha, beta, theta]
    precip: observed value of precip for return period R
    R: observed value of the return period (years)
    omega: average sampling frequency (yr-1) = 365.25*n / N, where n is the number of integer years and
      N is the number of daily observations. omega should be very close to 1.
    precipBetaP is a function that calculates precip given a value of the return period, using the Beta-P
      relationship.
    Ken Waight / December 2019
    """
    err = precip - precipBetaP(x, R, omega)
    return err


def precipBetaP(x, R, omega):
    """
    Function to calculate precip given a value of the return period (or average recurrence interval),
      using the Beta-P relationship.
    x: list of the three parameters for the Beta-P curve, [alpha, beta, theta]
    R: observed value of the return period (years)
    omega: average sampling frequency (yr-1) = 365.25*n / N, where n is the number of integer years and
      N is the number of daily observations. omega should be very close to 1.
    Ken Waight / December 2019
    """
    alpha = x[0]
    beta = x[1]
    theta = x[2]
    precip = beta * ((omega*R)**(1.0/alpha) - 1.0)**(1.0/theta)
    #print('beta, omega, R, alpha, theta, precip:', beta, omega, R, alpha, theta, precip)
    return precip

def calcBetaPExtremes(returnPeriods, duration,
                      betaPParams, omega):
    """
    Apply the Beta-P extreme precip distribution to estimate extreme values for one duration
       and a set of return periods.
       Ken Waight / December 2019
    """
    precipAmount = {}
    precipRate = {}
    for returnPeriod in returnPeriods:
        precipAmount[returnPeriod] = precipBetaP(betaPParams, returnPeriod, omega)
        precipRate[returnPeriod] = (precipAmount[returnPeriod] * 60) / duration

    # Return both extreme precip amounts and rates.
    return (precipAmount, precipRate)


def printPresentPct(yyyy, nPresent, nMissing):
    presentPct = 100 * (nPresent / (nPresent + nMissing))
    print('   ', yyyy, '{0: .1f}% of 15 min data present'.format(presentPct))


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
"""
calcPrecipExtremes.py
Read a 15-min precip file for one site, use the method in the Chow hydrology textbook to calculate extreme precip
estimates for a range of durations and years. The goal is to provide a simple way to recalculate these values
with updated precip data.

After initially using the Chow et al. algorithm to calculate extremes, we are now calculating Partial Duration
Series (PDS), and fitting precip-recurrence interval data from PDS's to a Beta-P curve, as recommended by Wilks:
https://agupubs.onlinelibrary.wiley.com/doi/epdf/10.1029/93WR01710

The approach is described in DeGaetano and Zarrow:
http://precip.eas.cornell.edu/docs/xprecip_techdoc.pdf

Usage: python calcPrecipExtremes.py precip-file

Ken Waight / November 2019
"""

# ----------------------------------------------------------------
# Parse arguments.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a 15 min precip file and calculate frequency of extreme values.")
parser.add_argument("-metfiles", nargs="+", help="Name of 15 minute met files to read")
parser.add_argument("-pds", help="Calculate partial duration series from the data, use Beta-P distribution.",
                    action="store_true")
parser.add_argument("-ams", help="Calculate annual maximum series from the data, use Gumbel distribution.",
                    action="store_true")
parser.add_argument("-examine", "--examine", nargs=3, 
                    help="Look at context of suspicious value, enter variable name, value and month")
args = parser.parse_args()
metfiles = args.metfiles
if args.pds:
    pds = True
else:
    pds = False
if args.ams:
    ams = True
else:
    ams = False
if args.examine:
    examine = True
    examineVariable = args.examine[0]
    examineValue = args.examine[1]
    examineMonth = args.examine[2]
    examineData = OrderedDict()
else:
    examine = False

# =======
# Banner.
# =======
print(' =====================================\n',
      'Calculation of Precipitation Extremes\n',
      '=====================================\n')

# =================================
# Chow et al. example calculations.
# =================================
print('\nChow et al. example calculations:')
# ------------------------------------------
# Data for Chow et al. example calculations.
# ------------------------------------------
# Dictionaries for each precip duration.
precipDuration = {}
durations = [10]  # Durations in minutes.
returnPeriods = [5, 10, 50]  # Return periods in years.
precipMax = {}
precipMax[10] = {}
precipMax[10][1913] = 0.49
precipMax[10][1914] = 0.66
precipMax[10][1915] = 0.36
precipMax[10][1916] = 0.58
precipMax[10][1917] = 0.41
precipMax[10][1918] = 0.47
precipMax[10][1919] = 0.74
precipMax[10][1920] = 0.53
precipMax[10][1921] = 0.76
precipMax[10][1922] = 0.57
precipMax[10][1923] = 0.80
precipMax[10][1924] = 0.66
precipMax[10][1925] = 0.68
precipMax[10][1926] = 0.68
precipMax[10][1927] = 0.61
precipMax[10][1928] = 0.88
precipMax[10][1929] = 0.49
precipMax[10][1930] = 0.33
precipMax[10][1931] = 0.96
precipMax[10][1932] = 0.94
precipMax[10][1933] = 0.80
precipMax[10][1934] = 0.62
precipMax[10][1935] = 0.71
precipMax[10][1936] = 1.11
precipMax[10][1937] = 0.64
precipMax[10][1938] = 0.52
precipMax[10][1939] = 0.64
precipMax[10][1940] = 0.34
precipMax[10][1941] = 0.70
precipMax[10][1942] = 0.57
precipMax[10][1943] = 0.92
precipMax[10][1944] = 0.66
precipMax[10][1945] = 0.65
precipMax[10][1946] = 0.63
precipMax[10][1947] = 0.60

# Do the calculations.
precipMaxFormatted = [ '%.2f' % value for value in precipMax[10].values()]
print(' Annual maximums:', *precipMaxFormatted)
precipMaxAvg = statistics.mean(precipMax[10].values())
precipMaxStd = statistics.stdev(precipMax[10].values())
print('    Mean: {0: .3f}, Std. Dev.: {1: .3f}'.format(precipMaxAvg, precipMaxStd))
(xTChow, xTRateChow) = calcChowExtremes(returnPeriods, durations,
                                        precipMax)

# ====================================
# Example least squares curve fitting.
# ====================================
print('\nLeast squares curve fitting example calculations:')
# -----------------------------------------------------------
# Data for least squares curve fitting example calculations.
# -----------------------------------------------------------
u = np.array([4.0, 2.0, 1.0, 5.0e-1, 2.5e-1, 1.67e-1, 1.25e-1, 1.0e-1,
              8.33e-2, 7.14e-2, 6.25e-2])
y = np.array([1.957e-1, 1.947e-1, 1.735e-1, 1.6e-1, 8.44e-2, 6.27e-2,
              4.56e-2, 3.42e-2, 3.23e-2, 2.35e-2, 2.46e-2])
x0 = np.array([2.5, 3.9, 4.15, 3.9])
# -------------------------------
# Run the curve fitting example.
# -------------------------------
res = least_squares(fun, x0, jac=jac, bounds=(0, 100), args=(u, y), verbose=1)
print('Parameters from curve fitting example:', res.x)

# ===================
# LANL Calculations.
# ===================
print('\nLANL Calculations:')

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
# Spreadsheet column names of the variables.
columnDateTime = 'Date/Time'
column = {}
column['precip'] = 'precip'
rangeCheckVar = {}
rangeCheckVar['precip'] = 'tprecip'
# -------------------------------
# Parameters for LANL calculations.
# -------------------------------
precipDuration1 = {}  # Dictionaries for each precip duration for one site at a time.
precipDuration = {}  # Dictionaries for each precip duration, with the maxes across all sites.
# Durations in minutes.
#durations = [15, 30, 45, 60, 75, 90, 105, 120]  # Stormwater project.
#durations = [15, 2880]  #ktw
durations = [15, 60, 120, 180, 360, 720, 1440, 2880]  # Hazards project, full set.
# Return periods in years.
#returnPeriods = [2, 5, 10, 25, 50, 100]  # Stormwater project.
returnPeriods = [2500, 6250, 10000, 25000]  # Hazards project main, FDC-3 and 4.
#returnPeriods = [100, 200, 500, 2000]  # FCD-1 and 2 periods for Stormwater.
deltaDaysMinAllowedPds = 0.5  # Minimum number of days between precip events to be included in PDS.
deltaHoursMinAllowedPds = 12  # Minimum number of hours between precip events to be included in PDS.
precipMaxAcceptable = 5.0
# --------------------------------------------------------------------
# Read LANL 15 min data at one or more locations.
# --------------------------------------------------------------------
# Create dictionaries for each duration.
for duration in durations:  
    precipDuration[duration] = {}
precip15 = {}
# Initialize dicts for flagged and out of range data.
nFlagged = 0
nOutOfRange = 0
nGood = 0
for metfile in metfiles:
    print("\nReading LANL file:", metfile)
    # First check to be sure it has commas (because it has to be a CSV file).
    with open(metfile, 'r') as test:
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
    with open(metfile, 'r') as infile:
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
            # Check that variable is good and save it.
            # ---------------------------------------------------------
            # 15 min precip amount.
            try:
                precip = checkOneValue(row[column['precip']], nFlagged,
                                       rangeCheckVar=rangeCheckVar['precip'], 
                                       nOutOfRange=nOutOfRange) 
            except KeyError:
                precip = None
            if precip is not None:
                precip15[dt] = precip
                if (examine and 
                    examineVariable == 'precip' and
                    int(mm) == int(examineMonth)):
                    examineData[dt] = precip
            # -------------------------------------------------
            # If data is good, save this time.
            # -------------------------------------------------
            if (precip is not None):
                # One or more good values; add to list of all datetimes.
                dtList.append(dt)
                nGood += 1
            # Save the last time.
            dtLast = dt
    # The original data is for 15 min duration.
    precipDuration1[15] = precip15

    # -------------------------------------------------
    # Write a simple CSV file of the raw precip values.
    # -------------------------------------------------
    rawPrecipFile = 'precip15.csv'
    print('\nWriting simple CSV file of raw precipitation values:', rawPrecipFile)
    with open(rawPrecipFile, 'w+') as outfile:
        outfile.write('yyyy-mm-dd hh:mm' + ',' + 'precip(inches)\n')
        for dt in precip15:
            outfile.write(datetime.strftime(dt, '%Y-%m-%d %H:%M') + ',' + str(precip15[dt]) + '\n')

    # ----------------------------------------
    # Make list of all possible 15 min times.
    # ----------------------------------------
    print('\nBuild list of all possible 15 min times.')
    dt15All = []
    if (dtFirst is not None
            and dtLast is not None):
        dt = dtFirst
        while dt <= dtLast:
            dt15All.append(dt)
            # Go to next time.
            dt = dt + timedelta(minutes=15)
    else:
        print('Starting and ending times not found in data!')
        sys.exit(1)

    # --------------------------------------------------
    # Calculate how much data is present for each year.
    # --------------------------------------------------
    print('\nCalculate how much data is present for each year:')
    nPresent = 0
    nMissing = 0
    yyyyPrev = 0
    for dt in dt15All:
        yyyy = datetime.strftime(dt, '%Y')
        if yyyyPrev == 0:
            # Initialize yyyyPrev.
            yyyyPrev = yyyy
        if (yyyyPrev != 0
            and yyyy != yyyyPrev):
            # Print result for one year.
            printPresentPct(yyyyPrev, nPresent, nMissing)
            # Initialize for the next year.
            nPresent = 0
            nMissing = 0
            yyyyPrev = yyyy
        if dt in precip15:
            # Data present for this time.
            nPresent += 1
        else:
            # Data missing for this time.
            nMissing += 1
    # Print result for final year.
    printPresentPct(yyyyPrev, nPresent, nMissing)

    # -------------------------------------------------------------
    # Add 15-min values to calculate precip over longer durations.
    # -------------------------------------------------------------
    print('\nAdd 15-min values to calculate precip over longer durations:')
    for duration in durations[1:]:  # Skip 15 min duration for this step.
        print('   ', duration, 'min')
        precipDuration1[duration] = {}
        # -------------------------------
        # Test non-overlapping durations.
        #skip = int(duration/15) # Test non-overlapping durations.
        #for i in range(1,len(dt15All),skip):  # First range argument of 1 instead of 0 matches Kelly et al.
        # -------------------------------
        for dtEndPeriod in dt15All:
            # -------------------------------
            # Test non-overlapping durations.
            #dtEndPeriod = dt15All[i]
            # -------------------------------
            precipPeriod = 0.
            dt = dtEndPeriod - timedelta(minutes=duration) + timedelta(minutes=15)
            # Go through the period from beginning to end.
            while dt <= dtEndPeriod:
                if dt in precip15:
                    if precipPeriod is not None:
                        precipPeriod += precip15[dt]
                else:
                    precipPeriod = None
                # Go to next time.
                dt += timedelta(minutes=15) # Overlapping 15 min periods.
            if precipPeriod is not None:
                precipDuration1[duration][dtEndPeriod] = precipPeriod
    # -----------------------------------------------------------
    # Combine precip data from multiple sites, as if the analysis 
    #   were for a single site.
    # -----------------------------------------------------------
    print('\nAdd precip data from this dataset to combined lists.')
    for duration in durations:
        # For each time, save the value for each time from this dataset only
        #   if it's higher than previous datasets.
        for dt in precipDuration1[duration]:
            precipDuration[duration][dt] = max(precipDuration1[duration][dt], float(precipDuration[duration].get(dt, 0.)))

# End of loop of met files.

if pds:
    # --------------------------------------------------------------------------
    # To construct a Partial Duration Series (PDS), accumulate a list of the
    #   highest values in the dataset.
    # --------------------------------------------------------------------------
    print('\nTo get the Partial Duration Series (PDS), accumulate the highest precip values:')
    # Count the number of years in the dataset.
    delta = dtLast - dtFirst
    deltaYears = delta.days / 365.25
    intDeltaYears = int(deltaYears)
    omega = 365.25 * float(intDeltaYears) / (deltaYears * 365.25)
    print('   First data:', dtFirst,
          '\n   Last data:', dtLast,
          '\n   Number of years: {0: .1f}'.format(deltaYears),
          '\n   Integer number of years:', intDeltaYears,
          '\n   frequency: {0: .1f}'.format(omega))

    precipHigh = {}
    precipAmount = {}
    precipRate = {}
    for duration in durations:
        print('   ', duration, 'min:')
        # ------------------
        # Construct the PDS.
        # ------------------
        precipHigh[duration] = [0]
        dtLastPrecipAdded = dtFirst
        # Go through all precip values.
        for dt in precipDuration[duration]:
            if precipDuration[duration][dt] > 0:
                # Consider whether this precip value should be added to the series.
                deltaLastPrecipAdded = dt - dtLastPrecipAdded
                deltaHoursLastPrecipAdded = 24.*deltaLastPrecipAdded.days + deltaLastPrecipAdded.seconds/3600.
                if deltaHoursLastPrecipAdded <= deltaHoursMinAllowedPds:
                    # This event is too close to previous event, so only choose the largest of the two.
                    if precipDuration[duration][dt] > precipHigh[duration][-1]:
                        # This event is higher, keep it and drop the previous one. Otherwise, keep the previous one
                        #   and ignore this one.
                        precipHigh[duration].pop()
                        precipHigh[duration].append(precipDuration[duration][dt])
                        dtLastPrecipAdded = dt
                else:
                    # This event is enough later than the previous event to use.
                    precipHigh[duration].append(precipDuration[duration][dt])
                    dtLastPrecipAdded = dt
        # Sort the precip events from largest to smallest.
        precipHigh[duration].sort(reverse=True)
        #print('entire list of events, sorted:', precipHigh[duration])  #ktw
        # Save only the largest events, truncate at the number of years in the data record, so for 25 years
        #   of data, save the largest 25 precip events.
        precipHigh[duration] = precipHigh[duration][0:intDeltaYears]
        print('final truncated list of sorted events:', precipHigh[duration])  #ktw
        # ---------------------------------------------------------------
        # Calculate average recurrence interval (ARI) for each PDS value.
        # http://geog.uoregon.edu/amarcus/geog422/Handout_Recurrence_calcs.htm
        # https://stackoverflow.com/questions/24251919/scipy-rankdata-reverse-highest-to-lowest
        # ---------------------------------------------------------------
        # Calculate ranks of the sorted precip list with scipy function, then reverse the order
        #   so that the highest precip value  has rank=1.
        precipRanks = rankdata([-1 * i for i in precipHigh[duration]])
        # Calculate the recurrence intervals.
        ari = {}
        for rank, precipValue in zip(precipRanks, precipHigh[duration]):
            ari[precipValue] = float(intDeltaYears+1) / rank
            #print(ari[precipValue], ',', precipValue)  #ktw
        # ----------------------------------------------------------------
        # For the 15 min data, write a csv file of observed precip values
        #   and return intervals, in order to plot an illustration of the
        #   concept.
        # ----------------------------------------------------------------
        if duration == 15:
            precipRecurrenceFile = 'precipRecurrenceData.csv'
            print('\nWriting output csv file:', precipRecurrenceFile)
            with open(precipRecurrenceFile, 'w+') as outfile:
                for rank, precipValue in zip(precipRanks, precipHigh[duration]):
                    outfile.write('{0: .2f},{1: .2f}\n'.format(ari[precipValue], precipValue))
        # -----------------------------
        # Fit Beta-P curve to this PDS.
        # -----------------------------
        print('      Fit Beta-P extreme value distribution to PDS:')
        # First guess of parameters.
        alpha0 = 0.5
        beta0 = 0.5
        theta0 = 0.5
        x0 = [alpha0, beta0, theta0]
        # Call the scipy least_squares package to fit a curve to the data.
        precip = np.array(list(ari.keys()))
        R = np.array(list(ari.values()))
        result = least_squares(residual, x0, args=(precip, R, omega), method='lm')
        print('        alpha: {0: .2f}, beta: {1: .2f}, theta: {2: .2f}'.format(result.x[0],
                                                                                result.x[1],
                                                                                result.x[2]))
        # Plug a set of return periods into the extreme distribution to get precip values.
        betaPParams = result.x
        print('plug a set of return periods')
        (precipAmount[duration], precipRate[duration]) = calcBetaPExtremes(returnPeriods, duration,
                                                                           betaPParams, omega)
        for returnPeriod in returnPeriods:
            print('       {0: d} years: {1: .2f} in, {2: .2f} in/hr'.format(returnPeriod,
                                                                            precipAmount[duration][returnPeriod],
                                                                            precipRate[duration][returnPeriod]))

# --------------------------------------------------------------------------
# To construct an Annual Maximum Series (AMS), calculate the maximum precip
#   for each year for each duration.
# --------------------------------------------------------------------------
print('\nTo get the AMS, calculate the maximum precip for each year:')
precipMax = {}
if ams:
    precipAmount = {}
for duration in durations:
    print('\n   ', duration, 'min:')
    precipMax[duration] = {}
    for dt in precipDuration[duration].keys():
        yyyy = datetime.strftime(dt, '%Y')
        mm = datetime.strftime(dt, '%m')
        precipMax[duration][yyyy] = max(precipDuration[duration][dt], float(precipMax[duration].get(yyyy, 0.)))
        #if (duration == 2880.0 and  #ktw: Prints to find date of max events as they increase through each year for one duration.
        #    precipMax[duration][yyyy] > 0.0 and
        #    precipDuration[duration][dt] == precipMax[duration][yyyy]):
        #    print('yyyy, new max, dt:', yyyy, precipMax[duration][yyyy], dt) 
        #if (duration == 2880.0 and  #ktw: Prints to find date of max events as they grow in one certain month above a threshold for each year for one duration.
        #    mm == '12' and
        #    precipDuration[duration][dt] > 0.3):
        #    print('yyyy, Dec amount, dt:', yyyy, precipDuration[duration][dt], dt) 
    precipMaxFormatted = ['%.2f' % value for value in precipMax[duration].values()]
    print('      ', *precipMaxFormatted)
    precipMaxAvg = statistics.mean(precipMax[duration].values())
    precipMaxStd = statistics.stdev(precipMax[duration].values())
    print('           Mean: {0: .3f}, Std. Dev.: {1: .3f}'.format(precipMaxAvg, precipMaxStd))
    # Make a bar chart of the annual maximum series.
    seriesPlotFile = "series." + str(duration) + ".png"
    years = list(precipMax[duration].keys())
    maximums = list(precipMax[duration].values())
    print('\nMake a bar chart of the annual maximum series:', 
          seriesPlotFile)
    fig = go.Figure(data=[
        go.Bar(name="Annual maximums", x=years,
               y=maximums),
    ])
    fig.update_layout(title_text=seriesPlotFile)
    pio.write_image(fig, seriesPlotFile)
    # Also write a csv file.
    seriesFile = 'annualSeries.' + str(duration) + '.csv'
    print('\nWriting series to output csv file:', seriesFile)
    with open(seriesFile, 'w+') as outfile:
        outfile.write('year' + ',' + 'maximum')
        for year in years:
            outfile.write('\n' + str(year) + ',' + str(precipMax[duration][year]))
    # Calculate average recurrence interval (ARI) for each AMS value.
    ari = {}
    nYears = len(precipMax[duration])
    precipAMS = list(precipMax[duration].values())
    precipAMS.sort(reverse=True)
    for i, precipValue in enumerate(precipAMS):
        ari[precipValue] = float(nYears + 1) / float(i + 1)
    if pds:     
        # Fit Beta-P curve to this AMS.
        print('      Fit Beta-P extreme value distribution to AMS:')
        # First guess of parameters.
        alpha0 = 0.5
        beta0 = 0.5
        theta0 = 0.5
        x0 = [alpha0, beta0, theta0]
        # Call the scipy least_squares package to fit a curve to the data.
        precip = np.array(list(ari.keys()))
        R = np.array(list(ari.values()))
        result = least_squares(residual, x0, args=(precip, R, omega), method='lm')
        betaPParams = result.x
        # Plug 1.58 year return period into extreme distribution to get precip values.
        #   Atlas 14 has an equation showing that the 1.58 year return period for AMS is
        #   equivalent to the 1 year return period for PDS.
        (precipAmountAMS, precipRateAMS) = calcBetaPExtremes([1.58], duration,
                                                             betaPParams, omega)
        # Insert 1.58 year values into the PDS 1 year dictionaries.
        returnPeriod = 1
        precipAmount[duration][returnPeriod] = precipAmountAMS[1.58]
        precipRate[duration][returnPeriod] = precipRateAMS[1.58]
        print('      {0: d} years: {1: .2f} in, {2: .2f} in/hr'.format(returnPeriod,
                                                                       precipAmount[duration][returnPeriod],
                                                                       precipRate[duration][returnPeriod]))
    elif ams:
        precipAmount[duration] = {}
        # Fit the series to an extreme value distribution.
        #   1. Generalized extreme value distribution.
        shape, loc, scale = gev.fit(precipAMS, f0=0)
        print('        shape, loc, scale:', shape, loc, scale)
        # Calculate extreme values for a set of return periods.
        print('        Calculate extreme values for a set of return periods:')
        for returnPeriod in returnPeriods:
            # From Chow.
            yt = -math.log(math.log(returnPeriod/(returnPeriod-1.0)))
            xt = loc + scale*yt
            precipAmount[duration][returnPeriod] = xt
            print('           ReturnPeriod, amount:', returnPeriod, precipAmount[duration][returnPeriod])

if pds:
    # Add 1 year to the list of return periods.
    returnPeriods.insert(0, 1)
    # -------------------------------------------------------
    # Write a csv file of extreme precip rates for plotting.
    # -------------------------------------------------------
    precipExtremesFile = 'precipExtremes.csv'
    print('\nWriting output csv file:', precipExtremesFile)
    with open(precipExtremesFile, 'w+') as outfile:
        outfile.write('Duration (min)')
        for returnPeriod in returnPeriods:
            outfile.write(',{0: d} yr extremes(in/hr)'.format(returnPeriod))
        outfile.write('\n')
        for duration in durations:
            outfile.write('{0: d}'.format(duration))
            for returnPeriod in returnPeriods:
                outfile.write(',{0: .2f}'.format(precipRate[duration][returnPeriod]))
            outfile.write('\n')
    # -------------------------------------------------------------------------------------------
    # For an illustration of a Beta-P curve, print the values for a provided duration, omega and
    #   set of alpha, beta, theta parameter, for our set of return periods:
    # -------------------------------------------------------------------------------------------
    duration = 15
    omega =  0.96846590909
    betaPParams =  [0.15397971, 0.455051, 29.30487937]
    (precipAmount1, precipRate1) = calcBetaPExtremes(returnPeriods, duration,
                                                     betaPParams, omega)
    print('\nIllustration of a Beta-P curve:')
    print('   duration:', duration)
    print('   omega:', omega)
    print('   alpha, beta, theta:', *betaPParams)
    for returnPeriod in returnPeriods[1:]:
        print('       {0: d} years: {1: .2f} in, {2: .2f} in/hr'.format(returnPeriod,
                                                                    precipAmount1[returnPeriod],
                                                                    precipRate1[returnPeriod]))

elif ams:
    # --------------------------------------------------------
    # Write a csv file of extreme precip amounts for plotting.
    # --------------------------------------------------------
    precipExtremesFile = 'precipExtremes.csv'
    print('\nWriting output csv file:', precipExtremesFile)
    with open(precipExtremesFile, 'w+') as outfile:
        outfile.write('Duration (min)')
        for returnPeriod in returnPeriods:
            outfile.write(',{0: d} yr extremes(in)'.format(returnPeriod))
        outfile.write('\n')
        for duration in durations:
            outfile.write('{0: d}'.format(duration))
            for returnPeriod in returnPeriods:
                outfile.write(',{0: .2f}'.format(precipAmount[duration][returnPeriod]))
            outfile.write('\n')

# ----
# End.
# ----
pct = 100. * float(nFlagged)/float(nGood+nFlagged+nOutOfRange)
print('\nINFO: Number of flagged precip values: {0:d} ({1:.1f}%)'.format(nFlagged, pct))
pct = 100. * float(nOutOfRange)/float(nGood+nFlagged+nOutOfRange)
print('\nINFO: Number of out of range precip values: {0:d} ({1:.1f}%)'.format(nOutOfRange, pct))
print('\nCompleted.')
sys.exit()
