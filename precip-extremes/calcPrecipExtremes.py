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
parser.add_argument("precipfile", help="Name of 15 minute precip file to read")
args = parser.parse_args()
precipFile = args.precipfile

# =======
# Banner.
# =======
print('=====================================\n',
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

# -------------------------------
# Parameters for LANL calculations.
# -------------------------------
precipDuration = {}  # Dictionaries for each precip duration.
# Durations in minutes.
#durations = [15, 30, 45, 60, 75, 90, 105, 120]  # Stormwater project.
durations = [15, 60, 120, 180, 360, 720, 1440, 2880]  # Hazards project.
# Return periods in years.
#returnPeriods = [2, 5, 10, 25, 50, 100]  # Stormwater project.
returnPeriods = [2500, 6250, 10000, 25000]  # Hazards project.
deltaDaysMinAllowedPds = 0.5  # Minimum number of days between precip events to be included in PDS.
deltaHoursMinAllowedPds = 12  # Minimum number of hours between precip events to be included in PDS.
precipMaxAcceptable = 5.0
# -------------------------------
# Read LANL data.
# -------------------------------
print("\nReading precip file:", precipFile)
precip15 = {}
dtFirst = None
dtLast = None
nBadRow = 0
rowBad = []
nFlagged = 0
nBadDate = 0
dateBad = []
nBadPrecip = 0
precipBad = []
nGood = 0
with open(precipFile, 'r') as infile:
    precipData = csv.reader(infile)
    next(precipData)
    for row in precipData:
        if len(row) < 2:
            # Incomplete row, doesn't have date and precip.
            nBadRow += 1
            rowBad.append(row)
            continue
        # Convert date string to datetime.
        try:
            dt = datetime.strptime(row[0], "%m/%d/%Y %H:%M")
        except:
            nBadDate += 1
            dateBad.append(row[0])
            continue
        # Save first time.
        if dtFirst is None:
            dtFirst = dt
        # Save precip value unless it's flagged or out of range.
        if row[1] != '*':
            try:
                precip1 = float(row[1])
                if (precip1 >= 0. and
                        precip1 <= precipMaxAcceptable):
                    precip15[dt] = float(row[1])
                    nGood += 1
                else:
                    nBadPrecip += 1
                    precipBad.append(precip1)
            except:
                nBadPrecip += 1
                precipBad.append(row[1])
        else:
            nFlagged += 1
        # Save last time.
        dtLast = dt
# The original data is for 15 min duration.
precipDuration[15] = precip15

# ----------------------------------------
# Make list of all possible 15 min times.
# ----------------------------------------
print('\nBuild list of all possible 15 min times:')
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
    precipDuration[duration] = {}
    for dtEndPeriod in dt15All:
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
            dt += timedelta(minutes=15)
        if precipPeriod is not None:
            precipDuration[duration][dtEndPeriod] = precipPeriod

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
    #print('final truncated list of sorted events:', precipHigh[duration])  #ktw
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
for duration in durations:
    print('   ', duration, 'min:')
    precipMax[duration] = {}
    for dt in precipDuration[duration].keys():
        yyyy = datetime.strftime(dt, '%Y')
        precipMax[duration][yyyy] = max(precipDuration[duration][dt], float(precipMax[duration].get(yyyy, 0.)))
    precipMaxFormatted = ['%.2f' % value for value in precipMax[duration].values()]
    print('      ', *precipMaxFormatted)
    precipMaxAvg = statistics.mean(precipMax[duration].values())
    precipMaxStd = statistics.stdev(precipMax[duration].values())
    print('           Mean: {0: .3f}, Std. Dev.: {1: .3f}'.format(precipMaxAvg, precipMaxStd))
    # Calculate average recurrence interval (ARI) for each AMS value.
    ari = {}
    nYears = len(precipMax[duration])
    precipAMS = list(precipMax[duration].values())
    precipAMS.sort(reverse=True)
    for i, precipValue in enumerate(precipAMS):
        ari[precipValue] = float(nYears + 1) / float(i + 1)
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

# -------------------------------------------------------------------------
# Apply the Chow et al. algorithm to the AMS to estimate extreme values
#    for each duration and return period.
# We're no longer using these results, because the PDS approach is seen as
#   better than AMS, and Wilks recommends the Beta-P extreme distribution
#   over others -- Chow uses the Extreme Value Type I.
# Reference: Chow,  Maidment and Mays, "Applied Hydrology" (1988)
# -------------------------------------------------------------------------
#print('\nApply the Chow et al. algorithm to calculate extreme values for each return period and duration:')
#(precipAmount, precipRate) = calcChowExtremes(returnPeriods, durations,
#                                              precipMax)

# ----
# End.
# ----
if nBadRow > 0:
    pct = 100. * float(nBadRow)/float(nGood+nBadRow+nBadDate+nFlagged+nBadPrecip)
    print('\nINFO: Number of incomplete rows of data: {0:d} ({1:.1f}%)'.format(nBadRow, pct))
    print('   ', *rowBad)
if nBadDate > 0:
    pct = 100. * float(nBadDate)/float(nGood+nBadRow+nBadDate+nFlagged+nBadPrecip)
    print('\nINFO: Number of bad dates: {0:d} ({1:.1f}%)'.format(nBadDate, pct))
    print('   ', *dateBad)
if nFlagged > 0:
    pct = 100. * float(nFlagged)/float(nGood+nBadRow+nBadDate+nFlagged+nBadPrecip)
    print('\nINFO: Number of flagged precip values: {0:d} ({1:.1f}%)'.format(nFlagged, pct))
if nBadPrecip > 0:
    pct = 100. * float(nBadPrecip)/float(nGood+nBadRow+nBadDate+nFlagged+nBadPrecip)
    print('\nINFO: Number of out of range precip values: {0:d} ({1:.1f}%)'.format(nBadPrecip, pct))
    print('   ', *precipBad)
    print('   (Maximum precip allowed in one observation period: {})'.format(precipMaxAcceptable))
print('\nCompleted.')
sys.exit()
