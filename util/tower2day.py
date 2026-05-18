#!/usr/bin/env python3

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
def printPresentPct(yyyy, nPresent, nMissing):
    presentPct = 100 * (nPresent / (nPresent + nMissing))
    print('   ', yyyy, '{0: .1f}% of 15 min data is good'.format(presentPct))


# ==============
# MAIN PROGRAM.
# ==============
"""
tower2day.py
Read a 15-min csv file for one tower site, calculate the same set of wind direction, wind
  speed and stability categories used to generate a STAR file for CAP88, and make a list of
  the dates with the the most times falling in one category chosen by the user.
  Uses information from:
    1. EPA report EPA-454/R-99-005, "Meteorological Monitoring Guidance for Regulatory Modeling Applications" (2000)
    2. Los Alamos report LA-11735-MS, "Los Alamos Climatology" by Bruce Bowen (1990)
    3. LANL Technical Procedures document EPC-ES-TP-501, "Dose Assessment Using CAP88" by Mike McNaughton, (2018)
Usage: python tower2day.py [-v] [-day | -night] [-mon month] [-raw] metfile  
  metfile is the name of the met file to read. It is assumed to be in the format downloaded from the Weather Machine.
    The -raw option is used to read a raw file from the datalogger.
Ken Waight / July 2020
"""

# ----------
# Constants.
# ----------
WIND_DIR_BIN_DIAG = 'S'  # Print diagnostic information for this combination of wind dir, stability and wind speed.
STABILITY_CLASS_DIAG = 'E'
WIND_SPEED_BIN_DIAG = '3'
SHORTWAVE_DOWN_THRESH = 5.0  # If the downward shortwave irradiance (W/m2) is equal to or above this threshold,
                             #   it is assumed to be daytime.
WIND_SPEED_MAX = 200.0  # Maximum wind speed that will be allowed. Any higher or negative wind speeds will be reported
                        # and then ignored.
SHORTWAVE_DOWN_MAX = 1362.0  # Maximum allowed downward shortwave irradiance (W/m2). This value is the solar
                             #   constant, really should be less than this. Any higher values will be
                             #   reported and then ignored.
SHORTWAVE_DOWN_MIN = -5.0  # Minimum allowed downward shortwave irradiance (W/m2).  # Any lower values will be
                           #   reported and then ignored.
STD_DEV_W_MAX = 10.0  # Maximum allowed standard deviation of the level 1 vertical velocity (m/s). Any higher
                      #   values will be reported and then ignored. Not sure how high this value should be.
STD_DEV_W_MIN = -1.0  # Minimum allowed standard deviation of the level 1 vertical velocity (m/s). Any lower
                      #   values will be reported and then ignored.
SIGMA_E_MAX = 90.0  # Maximum allowed value of sigma-E. Any higher or negative values will be reported
                    #   and then ignored. The value of 90 comes from the McNaughton document.
#Z0 = 38.  # Assumed value for LANL, Bowen (1990)
Z0 = 40.  # Assumed value for LANL, earlier PV-WAVE program. 

# ----------------------------------------------------------------
# Parse arguments.
# Get name of met file to read. There are two types:
#   1. A 15 min file downloaded from the Weather Machine (default)
#   2. A raw 15 min file, with or without header lines (optional)
# The name of the STAR file produced will be data.str, unless a
#   different name is specified.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a Weather Machine file and make a list of days with some characteristic")
parser.add_argument("metfile", help="Name of met file to read")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
parser.add_argument("-raw", "--datalogger", help="File is in the raw met format (from the datalogger)",
                    action="store_true")
group1 = parser.add_mutually_exclusive_group()
group1.add_argument("-wdir", "--wdir", help="Specify a wind direction (N, NNE, NE, ENE, E, etc.)")
parser.add_argument("-z0", "--roughness", help="Roughness length (cm) to use for stability determination")
group2 = parser.add_mutually_exclusive_group()
group2.add_argument("-day", "--day", help="Use only daytime data",
                    action="store_true")
group2.add_argument("-night", "--night", help="Use only nighttime data",
                    action="store_true")
parser.add_argument("-mon", "--month", help="Use data from any year but only a single specified month (1-12)")
args = parser.parse_args()
metFile = args.metfile
if args.verbosity:
    verbosity = int(args.verbosity)
else:
    verbosity = 0
day = args.day
night = args.night
month = args.month
if args.wdir:
    dayType = 'windDirection'
    windDirectionRequested = args.wdir
else:
    print('Must enter a wind direction with the -wdir argument!')
    sys.exit(1)
if args.roughness:
    z0 = float(args.roughness)
else:
    z0 = Z0  # default roughness value.

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
columnDateTime = 'Date/Time'
columnWindSpeed1 = 'spd1'
columnWindDir1 = 'dir1'
columnStdDevW1 = 'sdw1'
columnSWDown = 'swdn'
if args.datalogger:
    # Locations of desired data in the optional raw (datalogger) format.
    pass
else:
    # Locations of desired data in the default Weather Machine format.
    pass

# -------------------------------
# Bins for wind frequency data.
# -------------------------------
# Middle azimuths of 16 wind directions.
#windCardinalDirections = { 'N': 0., 'NNE': 22.5,  'NE': 45., 'ENE': 67.5,
#                           'E': 90., 'ESE': 112.5, 'SE': 135., 'SSE': 157.5,
#                           'S': 180., 'SSW': 202.5, 'SW': 225., 'WSW': 247.5,
#                           'W': 270., 'WNW': 292.5, 'NW': 315., 'NNW': 337.5 }
windDirections = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
# Wind direction bins. Assume 360 is never used.
windDirBins = {'N1': [348.75, 360.], 'N2': [0.0, 11.25],  # Deal with wind directions near 0/360.
                                     'NNE': [11.25, 33.75],
               'NE': [33.75, 56.25], 'ENE': [56.25, 78.75],
               'E': [78.75, 101.25], 'ESE': [101.25, 123.75],
               'SE': [123.75, 146.25], 'SSE': [146.25, 168.75],
               'S': [168.75, 191.25], 'SSW': [191.25, 213.75],
               'SW': [213.75, 236.25], 'WSW': [236.25, 258.75],
               'W': [258.75, 281.25], 'WNW': [281.25, 303.75],
               'NW': [303.75, 326.25], 'NNW': [326.25, 348.75]}

windSpeeds = ['1', '2', '3', '4', '5', '6']
# Wind speed bins in m/s, from McNaughton document.
#windSpeedBins = {'1': [0.0, 1.75], '2': [1.75, 3.25], '3': [3.25, 5.5], '4': [5.5, 8.5],
#                 '5': [8.5, 11.5], '6': [11.5, WIND_SPEED_MAX]}
# Wind speed bins from converting categories in CAP88 documentation from knots to m/s, splitting
#   halfway between the knot ranges.
#windSpeedBins = {'1': [0.0, 1.8], '2': [1.8, 3.34], '3': [3.34, 5.4], '4': [5.4, 8.49],
#                 '5': [8.49, 10.8], '6': [10.8, WIND_SPEED_MAX]}
# Wind speed bins from splitting categories in CAP88 documentation differently. Split on the
#   upper bounds in knots, converted to m/s. Produces results closer to PV-WAVE.
#windSpeedBins = {'1': [0.0, 1.54], '2': [1.54, 3.09], '3': [3.09, 5.14], '4': [5.14, 8.23],
#                 '5': [8.23, 10.8], '6': [10.8, WIND_SPEED_MAX]}
# Wind speed bins from PV-WAVE
windSpeedBins = {'1': [0.0, 1.56], '2': [1.56, 3.35], '3': [3.35, 5.59], '4': [5.59, 8.27],
                 '5': [8.27, 10.95], '6': [10.95, WIND_SPEED_MAX]}

stabilityClasses = ['A', 'B', 'C', 'D', 'E', 'F']
# Initial Pasquill stability classes assigned for ranges of sigma-E (or sigma-phi) values. These include a correction
#   for an assumed roughness length at LANL (38 cm). From Bowen, Table 10.1,
#   so they differ from the ranges given in the EPA report, Table 6-8a.
#stabilityClassesInitial = {'A': [14.5, SIGMA_E_MAX], 'B': [12.0, 14.5],
#                           'C': [9.5, 12.0], 'D': [6.0, 9.5],
#                           'E': [2.9, 6.0], 'F': [0.0, 2.9]}
# Initial stability classes from McNaughton, almost the same as Bowen, they are multiplied by a factor using
#   a roughness length for LANL, probably either 38 cm (Bowen) or 40 cm. (PV-WAVE).
#stabilityClassesInitial = {'A': [13.9, SIGMA_E_MAX], 'B': [12.0, 13.9],
#                           'C': [9.4, 12.0], 'D': [6.0, 9.4],
#                           'E': [2.9, 6.0], 'F': [0.0, 2.9]}
# Initial stability classes from EPA, so no LANL roughness adjustment, that will be made below.
stabilityClassesInitial = {'A': [11.5, SIGMA_E_MAX], 'B': [10.0, 11.5],
                           'C': [7.8, 10.0], 'D': [5.0, 7.8],
                           'E': [2.4, 5.0], 'F': [0.0, 2.4]}

# Wind speed and day/night adjustments to convert initial estimate of stability class to final estimate.
#   From EPA report, Table 6-8b. McNaughton doesn't mention this, but the PV-WAVE code does some version of it.
stabilityClassesFinalDay = {'A': {'A': [0.0, 3.0], 'B': [3.0, 4.0], 'C': [4.0, 6.0], 'D': [6.0, WIND_SPEED_MAX]},
                            'B': {'B': [0.0, 4.0], 'C': [4.0, 6.0], 'D': [6.0, WIND_SPEED_MAX]},
                            'C': {'C': [0.0, 6.0],  'D': [6.0, WIND_SPEED_MAX]},
                            'D': {'D': [0.0, WIND_SPEED_MAX]},
                            'E': {'D': [0.0, WIND_SPEED_MAX]},
                            'F': {'D': [0.0, WIND_SPEED_MAX]}}
stabilityClassesFinalNight = {'A': {'D': [0.0, WIND_SPEED_MAX]},
                              'B': {'D': [0.0, WIND_SPEED_MAX]},
                              'C': {'D': [0.0, WIND_SPEED_MAX]},
                              'D': {'D': [0.0, WIND_SPEED_MAX]},
                              'E': {'E': [0.0, 5.0], 'D': [5.0, WIND_SPEED_MAX]},
                              'F': {'F': [0.0, 3.0], 'E': [3.0, 5.0], 'D': [5.0, WIND_SPEED_MAX]}}

# =======
# Banner.
# =======
print('\n=====================================\n',
      'Finding days of a requested type\n',
      '=====================================\n')

# ------------------------------------------------------------------------------------------------------------------
# Initialize dictionary for counts and frequencies of obs in each combination of
#   wind direction bin/stability class/wind speed bin.
# ------------------------------------------------------------------------------------------------------------------
count = {}
frequency = {}
for windDirection in windDirections:
    count[windDirection] = {}
    frequency[windDirection] = {}
    for stability in stabilityClasses:
        count[windDirection][stability] = {}
        frequency[windDirection][stability] = {}
        for windSpeed in windSpeeds:
            # Add a dictionary for the date.
            count[windDirection][stability][windSpeed] = {}

# Modify sigma-E values used for initial stability class determination by roughness factor.
print('Roughness length (z0) used for stability category determination:', z0)
z0Correction = (z0/15.)**0.2
for stability in stabilityClassesInitial.keys():
  stabilityClassesInitial[stability][0] *= z0Correction
  stabilityClassesInitial[stability][1] *= z0Correction

if verbosity >= 1:
    # Initialize array for distribution by hour of day.
    nHour = []
    for hour in range(0,24):
        nHour.append(0)
    # Initialize array for distribution by month.
    nMonth = []
    for mon in range(0, 12):
        nMonth.append(0)

if verbosity >= 2:
    # Initialize array for wind direction distribution by degree.
    nWindDirectionDeg = []
    for deg in range(0, 360):
        nWindDirectionDeg.append(0)
    # Initialize array for wind speed distribution by m/s.
    nWindSpeed = []
    for speed in range(0, 12):
        nWindSpeed.append(0)

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
with open(metFile, 'r') as infile:
    towerData = csv.DictReader(infile)
    for row in towerData:
        if (row[columnDateTime] and # Should be at least these fields.
            row[columnWindSpeed1] and
            row[columnStdDevW1] and
            row[columnSWDown] and
            (re.search(r'^\d+-\d+-\d+ \d+:\d+:\d+', row[columnDateTime]) or
             re.search(r'^\d+/\d+/\d+ \d+:\d+', row[columnDateTime]))):
            # This should be a data line (ignore header lines).
            #print('row[0]:', row[columnDateTime]) #ktw
            try:
                # Try the default Weather Machine formatted date.
                dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M:%S")
            except:
                # Try a datalogger formatted date.
                dt = datetime.strptime(row[columnDateTime], "%m/%d/%Y %H:%M")
            # Save first time.
            if dtFirst is None:
                dtFirst = dt
            # ---------------------------------------------------------
            # Save data if both wind speed and direction are unflagged.
            # ---------------------------------------------------------
            if ('*' not in row[columnWindSpeed1] and  # Need wind speed to be unflagged.
                '*' not in row[columnWindDir1] and  # Need wind speed to be unflagged.
                '*' not in row[columnStdDevW1] and  # Need std. dev. of level 1 vertical velocity to be unflagged.
                '*' not in row[columnSWDown]):  # Need downward shortwave to be unflagged.
                # --------------------------------------
                # Raw variables needed for calculations.
                # --------------------------------------
                windSpeed1 = float(row[columnWindSpeed1])  # Wind speed at level 1 (10 m) in m/s.
                windDir1 = float(row[columnWindDir1])  # Wind direction at level 1.
                stdDevW1 = float(row[columnStdDevW1])  # Standard deviation of the level 1 vertical velocity (m/s).
                swDown = float(row[columnSWDown])  # Downward shortwave irradiance at the surface (W/m2).
                # Constrain variables to be positive.
                if stdDevW1 < 0.0:
                    stdDevW1 = 0.0
                if swDown < 0.0:
                    swDown = 0.0
                # Change wind direction of 360 to 0 for simplicity.
                if windDir1 == 360.0:
                    windDir1 = 0.0
                # -----------------------------------------------------
                # Calculate sigma-E, converted from radians to degrees.
                # -----------------------------------------------------
                if windSpeed1 != 0.0:
                    sigmaE = (stdDevW1/windSpeed1) * (180/math.pi)
                else:
                    print('WARNING: Cannot calculate sigma-E and stability class with a zero wind speed at', dt,
                          ', will be ignored.')
                    nBad += 1
                    continue
                #print('windSpeed1 windDir1 stdDevW1 swDown sigmaE:', windSpeed1, windDir1, stdDevW1, swDown, sigmaE)
                # -------------------------------------------------------------
                # Check for bad data values. If any are found, skip this time.
                # -------------------------------------------------------------
                # Be sure wind speed is not unreasonably high.
                if (windSpeed1 < 0.0 or
                    windSpeed1 >= WIND_SPEED_MAX):
                    print('WARNING: Wind speed', windSpeed1, 'out of bounds at', dt, ', will be ignored.')
                    nBad += 1
                    continue
                # Be sure wind direction is not out of bounds.
                if (windDir1 < 0.0 or
                    windDir1 >= 360.0):
                    print('WARNING: Wind direction', windDir1, 'out of bounds at', dt, ', will be ignored.')
                    nBad += 1
                    continue
                # Be sure standard deviation of vertical velocity is not out of bounds.
                if (stdDevW1 < STD_DEV_W_MIN or
                    stdDevW1 >= STD_DEV_W_MAX):
                    print('WARNING: Std. Dev. level 1 vertical velocity', stdDevW1, ' too low or too high at',
                          dt, ', will be ignored.')
                    nBad += 1
                    continue
                # Be sure downward shortwave radiation is not out of bounds.
                if (swDown < SHORTWAVE_DOWN_MIN or
                    swDown >= SHORTWAVE_DOWN_MAX):
                    print('WARNING: Downward shortwave irradiance', swDown, ' too low or too high at',
                          dt, ', will be ignored.')
                    nBad += 1
                    continue
                # If day has been specified, process only times with swDown above threshold.
                if (day and
                    swDown < SHORTWAVE_DOWN_THRESH):
                    continue  # Skip to next time.
                # If night has been specified, process only times with swDown below threshold.
                if (night and
                    swDown >= SHORTWAVE_DOWN_THRESH):
                    continue  # Skip to next time.
                # If a month has been specified, process only times in that month, for any year.
                mm = datetime.strftime(dt, '%m')
                if (month and
                    int(mm) != int(month)):
                    continue  # Skip to next time.
                # Data for this time will be used. Add to list of all datetimes with good data.
                dtList.append(dt)
                if verbosity >= 2:
                    # Collect data for distribution of wind directions by degree.
                    nWindDirectionDeg[int(windDir1)] += 1
                    # Collect data for distribution of wind speeds by m/s.
                    nWindSpeed[int(round(windSpeed1))] += 1
                    if int(round(windSpeed1)) > 10:
                        nWindSpeed[11] += 1
                if verbosity >= 1:
                    # Collect data for distribution of obs by hour.
                    hh = datetime.strftime(dt, '%H')
                    nHour[int(hh)] += 1
                    # Collect data for distribution of obs by month.
                    nMonth[int(mm)-1] += 1
                # ---------------------------------------------------------
                # Assign the wind direction bin.
                # ---------------------------------------------------------
                for bin in windDirBins.keys():
                    #ktw print('windDir1, bin, windDirBins[bin]:', windDir1, bin, windDirBins[bin], windDirBins[bin][0])
                    if (windDir1 >= windDirBins[bin][0] and
                        windDir1 < windDirBins[bin][1]):
                        if (bin == 'N1' or
                            bin == 'N2'):
                            windDirBin = 'N'
                        else:
                            windDirBin = bin
                # ---------------------------------------------------------
                # Assign the wind speed bin.
                # ---------------------------------------------------------
                for bin in windSpeedBins.keys():
                    if (windSpeed1 >= windSpeedBins[bin][0] and
                        windSpeed1 < windSpeedBins[bin][1]):
                        windSpeedBin = bin
                # ---------------------------------------------------------
                # Calculate the initial stability class.
                # ---------------------------------------------------------
                for stabilityClass in stabilityClassesInitial.keys():
                    if (sigmaE >= stabilityClassesInitial[stabilityClass][0] and
                        sigmaE < stabilityClassesInitial[stabilityClass][1]):
                        stabilityClassInitial = stabilityClass
                # ---------------------------------------------------------
                # Use different wind speed adjustments for day and night.
                # ---------------------------------------------------------
                if swDown >= SHORTWAVE_DOWN_THRESH:
                    # Use wind speed adjustments for daytime.
                    stabilityClassesFinal = stabilityClassesFinalDay
                else:
                    # Use wind speed adjustments for nighttime.
                    stabilityClassesFinal = stabilityClassesFinalNight
                # ----------------------------------------------------------
                # Apply wind speed adjustments to get final stability class.
                # ----------------------------------------------------------
                for stabilityClass in stabilityClassesFinal[stabilityClassInitial].keys():
                    if (windSpeed1 >= stabilityClassesFinal[stabilityClassInitial][stabilityClass][0] and
                        windSpeed1 < stabilityClassesFinal[stabilityClassInitial][stabilityClass][1]):
                        stabilityClassFinal = stabilityClass
                        #ktw: Try not using the adjusted final class, stay with the initial class.
                        #stabilityClassFinal = stabilityClassInitial
                # ------------------------------------------------------------------------------------
                # Increment the counter for this wind direction/wind speed/stability class/date combo.
                # ------------------------------------------------------------------------------------
                # Get the date in yyyymmdd format.
                yyyymmdd = datetime.strftime(dt, "%Y%m%d")
                # Append to a list of dates if it's not already there.
                if yyyymmdd not in yyyymmdds:
                    yyyymmdds.append(yyyymmdd)
                # Increment.
                count[windDirBin][stabilityClassFinal][windSpeedBin][yyyymmdd] = \
                    count[windDirBin][stabilityClassFinal][windSpeedBin].get(yyyymmdd, 0) + 1
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

# --------------------------------------------------
# Calculate how much data is present for each year.
# --------------------------------------------------
print('\nCalculate how much data is present for each year:')
nTotal = 0
nPresent = 0
nMissing = 0
yyyyPrev = 0
for dt in dt15All:
    yyyy = datetime.strftime(dt, '%Y')
    if yyyyPrev == 0:
        # Initialize yyyyPrev.
        yyyyPrev = yyyy
    if (yyyyPrev != 0 and
        yyyy != yyyyPrev):
        # Print result for one year.
        printPresentPct(yyyyPrev, nPresent, nMissing)
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

# ------------------------------------------------------------------------------------------
# For each date, count the obs times with the requested category.
# ------------------------------------------------------------------------------------------
if dayType == 'windDirection':
    print('\nLooking for days with', dayType, windDirectionRequested) 
# Initialize day counts.
obsCount = {}
for yyyymmdd in yyyymmdds:
    obsCount[yyyymmdd] = 0
if dayType == 'windDirection':
    print('\nFor each date, count the obs times with the requested wind direction.')
    for yyyymmdd in yyyymmdds:
        obsCount[yyyymmdd] = 0
        for stability in stabilityClasses:
            for windSpeed in windSpeeds:
                obsCount[yyyymmdd] += count[windDirectionRequested][stability][windSpeed].get(yyyymmdd, 0)
# Sort by the count.
yyyymmddSorted = sorted(obsCount, key=obsCount.get, reverse=True)
print('Dates with the most times with requested category:')
for yyyymmdd in yyyymmddSorted[0:20]:
    print('\n   ', yyyymmdd, ':', obsCount[yyyymmdd])
    # Print a summary of the categories found for this day.
    dayCountWindDirection = {}
    dayCountWindSpeed = {}
    dayCountStability = {}
    for windDirection in windDirections:
        dayCountWindDirection[windDirection] = 0
        for stability in stabilityClasses:
            dayCountStability[stability] = 0
            for windSpeed in windSpeeds:
                dayCountWindSpeed[windSpeed] = 0
    for windDirection in windDirections:
        for stability in stabilityClasses:
            for windSpeed in windSpeeds:
                dayCountWindDirection[windDirection] += count[windDirection][stability][windSpeed].get(yyyymmdd, 0)
                dayCountStability[stability] += count[windDirection][stability][windSpeed].get(yyyymmdd, 0)
                dayCountWindSpeed[windSpeed] += count[windDirection][stability][windSpeed].get(yyyymmdd, 0)
    # Print wind directions for the day. 
    windDirectionSorted = sorted(dayCountWindDirection, key=dayCountWindDirection.get, reverse=True)
    print('      ', end='')
    for windDirection in windDirectionSorted:
        if dayCountWindDirection[windDirection] > 0:
            print(windDirection, ':', dayCountWindDirection[windDirection], ',', end='')
        else:
            break
    # Print wind speeds for the day. 
    windSpeedSorted = sorted(dayCountWindSpeed, key=dayCountWindSpeed.get, reverse=True)
    print('\n      ', end='')
    for windSpeed in windSpeedSorted:
        if dayCountWindSpeed[windSpeed] > 0:
            print(windSpeed, ':', dayCountWindSpeed[windSpeed], ',', end='')
        else:
            break
    # Print stabilities for the day. 
    stabilitySorted = sorted(dayCountStability, key=dayCountStability.get, reverse=True)
    print('\n      ', end='')
    for stability in stabilitySorted:
        if dayCountStability[stability] > 0:
            print(stability, ':', dayCountStability[stability], ',', end='')
        else:
            break
print('\n')

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
