#!/usr/bin/env python3

"""
tower2stats.py
Read a 15-min csv file for one tower site, calculate averages, medians and frequencies for all times and by hour.
  Uses information from:
    1. EPA report EPA-454/R-99-005, "Meteorological Monitoring Guidance for Regulatory Modeling Applications" (2000)
    2. Los Alamos report LA-11735-MS, "Los Alamos Climatology" by Bruce Bowen (1990)
    3. LANL Technical Procedures document EPC-ES-TP-501, "Dose Assessment Using CAP88" by Mike McNaughton, (2018)
Usage: python tower2avg.py [-v] [-day | -night] [-mon month] [-raw] metfile  
  metfile is the name of the met file to read. It is assumed to be in the format downloaded from the Weather Machine.
    The -raw option is used to read a raw file from the datalogger.
Ken Waight / August 2020
"""

# ========
# IMPORTS.
# ========
import sys
import os
import csv
from datetime import datetime, timedelta
import math
import argparse
import re
import statistics

# ==============
# FUNCTIONS.
# ==============
def printPresentPct(yyyy, nPresent, nMissing):
    presentPct = 100 * (nPresent / (nPresent + nMissing))
    print('   ', yyyy, '{0: .1f}% of 15 min data is good'.format(presentPct))

def calcStability(z0, WIND_SPEED_MAX,
                  dt, swDown, stdDevW1, windSpeed1):
    """
    Given met information and a set of criteria, calculate the Pasquill-Gifford stability class,
      following EPA guidance.
    Ken Waight / November 2020
    """
    SIGMA_E_MAX = 90.0  # Maximum allowed value of sigma-E. Any higher or negative values will be reported
                        #   and then ignored. The value of 90 comes from the McNaughton document.

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
    # Modify sigma-E values used for initial stability class determination by roughness factor.
    #print('Roughness length (z0) used for stability category determination:', z0)
    z0Correction = (z0/15.)**0.2
    for stability in stabilityClassesInitial.keys():
        stabilityClassesInitial[stability][0] *= z0Correction
        stabilityClassesInitial[stability][1] *= z0Correction

    # -----------------------------------------------------
    # Calculate sigma-E, converted from radians to degrees.
    # -----------------------------------------------------
    if windSpeed1 != 0.0:
        sigmaE = (stdDevW1/windSpeed1) * (180/math.pi)
    else:
        # Can't calculate stability with zero wind speed.
        print('INFO: Cannot calculate stabilility with 0 wind speed at:', dt)
        return None
    if sigmaE > SIGMA_E_MAX:
        print('INFO: Cannot calculate stabilility with sigmaE too high:', dt, sigmaE)
        return None

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
    else:
        stabilityClassFinal = stabilityClassInitial
    return stabilityClassFinal


# ==============
# MAIN PROGRAM.
# ==============
# ----------
# Constants.
# ----------
WIND_SPEED_MAX = 200.0  # Maximum wind speed that will be allowed. Any higher or negative wind speeds will be reported
                        # and then ignored.
SHORTWAVE_DOWN_THRESH = 5.0  # If the downward shortwave irradiance (W/m2) is equal to or above this threshold,
                             #   it is assumed to be daytime.
SHORTWAVE_DOWN_MAX = 1362.0  # Maximum allowed downward shortwave irradiance (W/m2). This value is the solar
                             #   constant, really should be less than this. Any higher values will be
                             #   reported and then ignored.
SHORTWAVE_DOWN_MIN = -5.0  # Minimum allowed downward shortwave irradiance (W/m2).  # Any lower values will be
                           #   reported and then ignored.
STD_DEV_W_MAX = 10.0  # Maximum allowed standard deviation of the level 1 vertical velocity (m/s). Any higher
                      #   values will be reported and then ignored. Not sure how high this value should be.
STD_DEV_W_MIN = -1.0  # Minimum allowed standard deviation of the level 1 vertical velocity (m/s). Any lower
                      #   values will be reported and then ignored.
TEMP0_MIN = -35.0  # Minimum allowed temperature.
TEMP0_MAX = 45.0   # Maximum allowed temperature.
TPRECIP_MIN = 0.0  # Minimum allowed precipitation.
TPRECIP_MAX = 4.0  # Maximum allowed precipitation.
RH_MIN = 0.1    # Minimum allowed relative humidity.
RH_MAX = 100.0  #Maximum allowed relative humidity.
#Z0 = 38.  # Assumed value for LANL, Bowen (1990)
Z0 = 40.  # Assumed value for LANL, earlier PV-WAVE program. 
FLAG = -999.9  # Value for data assumed to be bad. 
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
stabilityBins = ['A', 'B', 'C', 'D', 'E', 'F']
stabilityClassNumerical = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6} # Assign numbers to classes. 
MW = 0.018015  # Molecular weight of water, kg/mol
R = 8.314  # Universal gas constant, J/mol-K
SUMMARY_FILE = 'tower2stats.txt'

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
group1 = parser.add_mutually_exclusive_group(required=True)
group1.add_argument("-wdir1", "--wdir1", help="Average wind direction at first level (deg)",
                    action="store_true")
group1.add_argument("-wspd1", "--wspd1", help="Average wind speed at first level (m/s)",
                    action="store_true")
group1.add_argument("-sdw1", "--sdw1", help="Average standard deviation of vertical wind speed at first level (m/s)",
                    action="store_true")
group1.add_argument("-sw", "--sw", help="Average downward shortwave irradiance at the surface (W/m2)",
                    action="store_true")
group1.add_argument("-stability", "--stability", help="Pasquill-Gifford stability class",
                    action="store_true")
group1.add_argument("-abshum0", "--abshum0", help="Absolute humidity at level 0 (g/m3)",
                    action="store_true")
group1.add_argument("-temp0", "--temp0", help="Temperature at level 0 (deg C)",
                    action="store_true")
group1.add_argument("-precip", "--precip", help="Precipitation amount (inches)",
                    action="store_true")
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
if args.roughness:
    z0 = float(args.roughness)
else:
    z0 = Z0  # default roughness value.
wdir1 = wspd1 = sdw1 = sw = stability = abshum0 = temp0 = precip = False
if args.wdir1:
    wdir1 = True
    varName = 'Wind direction at level 1 (deg)'
elif args.wspd1:
    wspd1 = True
    varName = 'Wind speed at level 1 (m/s)'
elif args.sdw1:
    sdw1 = True
    varName = 'Standard deviation of vertical wind speed at level 1 (m/s)'
elif args.sw:
    sw = True
    varName = 'Downward shortwave irradiance at surface (W/m2)'
elif args.stability:
    stability = True
    varName = 'Pasquill-Gifford stability category at level 1'
elif args.abshum0:
    abshum0 = True
    varName = 'Absolute humidity at level 0 (g/m3)'
elif args.temp0:
    temp0 = True
    varName = 'Temperature at level 0 (deg C)'
elif args.precip:
    precip = True
    varName = 'Precipitation (inches)'
else:
    print('Must enter a variable name (wdir1, wspd1, sdw1, sw, stability, abshum, temp0 or precip)!')
    sys.exit(1)

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
#columnDateTime = 'Date/Time'
columnDateTime1 = 'datetime' # From current Data Requests
columnDateTime2 = 'DateTime' # From WMDC
columnWindSpeed1 = 'spd1'
columnWindDir1 = 'dir1'
columnStdDevW1 = 'sdw1'
columnSWDown = 'swdn'
columnTemp0 = 'temp0'
columnRh = 'rh'
columnPrecip = 'precip'
if args.datalogger:
    # Locations of desired data in the optional raw (datalogger) format.
    pass
else:
    # Locations of desired data in the default Weather Machine format.
    pass

# =======
# Banner.
# =======
print('\n =====================================================\n',
      'Calculate averages/medians for one specified variable\n',
      '=====================================================\n')
print(*sys.argv)

# Initialize array of all obs.
if wdir1:
    obsAll = []
    u1All = []
    v1All = []
    if verbosity >= 1:
        # Initialize array for distribution by hour of day.
        obsHour = {}
        u1Hour = {}
        v1Hour = {}
        for hour in range(0,24):
            obsHour[hour] = []
            u1Hour[hour] = []
            v1Hour[hour] = []
            obsHour[hour] = []
        # Initialize array for distribution by month.
        obsMonth = {}
        u1Month = {}
        v1Month = {}
        for mon in range(0, 12):
            obsMonth[mon] = []
            u1Month[mon] = []
            v1Month[mon] = []
else:
    obsAll = []
    if verbosity >= 1:
        # Initialize array for distribution by hour of day.
        obsHour = {}
        for hour in range(0,24):
            obsHour[hour] = []
        # Initialize array for distribution by month.
        obsMonth = {}
        for mon in range(0, 12):
            obsMonth[mon] = []

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
        #print('row:', row)
        try:
            row[columnDateTime1]
            columnDateTime = columnDateTime1
        except KeyError:
            try:
                row[columnDateTime2]
                columnDateTime = columnDateTime2
            except KeyError:
                print('Datetime column header must be either', columnDateTime1, 'or', columnDateTime2)
                sys.exit(1)
        if (row[columnDateTime] and # Should be at least these fields.
            row[columnWindSpeed1] and
            row[columnStdDevW1] and
            row[columnSWDown] and
            (re.search(r'^\d+-\d+-\d+ \d+:\d+', row[columnDateTime]) or
             re.search(r'^\d+/\d+/\d+ \d+:\d+', row[columnDateTime]))):
            # This should be a data line (ignore header lines).
            #print('row[0]:', row[columnDateTime]) #ktw
            try:
                # Try the default Weather Machine formatted date.
                dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M")
            except:
                # Try a datalogger formatted date.
                dt = datetime.strptime(row[columnDateTime], "%m/%d/%Y %H:%M")
            # Save first time.
            if dtFirst is None:
                dtFirst = dt
            # ---------------------------------------------------------
            # Save data if both wind speed and direction are unflagged.
            # ---------------------------------------------------------
            if ((wspd1 and 
                 '*' not in row[columnWindSpeed1]) or  # Need wind speed to be unflagged.
                (wdir1 and
                 '*' not in row[columnWindDir1]) or # Need wind direction to be unflagged.
                (sdw1 and
                 '*' not in row[columnStdDevW1]) or # Need std. dev. of level 1 vertical velocity to be unflagged.
                (sw and 
                 '*' not in row[columnSWDown]) or
                (abshum0 and 
                 '*' not in row[columnTemp0] and  # Need temperature and RH to be unflagged.  
                 '*' not in row[columnRh]) or
                (temp0 and 
                 '*' not in row[columnTemp0]) or
                (precip and 
                 '*' not in row[columnPrecip]) or
                (stability and 
                 '*' not in row[columnStdDevW1] and
                 '*' not in row[columnSWDown] and
                 '*' not in row[columnWindSpeed1])):
                # --------------------------------------
                # If a month has been specified, process only times in that month, for any year.
                # --------------------------------------
                mm = datetime.strftime(dt, '%m')
                if (month and
                    int(mm) != int(month)):
                    continue  # Skip to next time.
                # --------------------------------------
                # Raw variables needed for calculations.
                # --------------------------------------
                if wspd1:
                    windSpeed1 = float(row[columnWindSpeed1])  # Wind speed at level 1 (10 m) in m/s.
                    # Be sure wind speed is not unreasonably high.
                    if (windSpeed1 < 0.0 or
                        windSpeed1 >= WIND_SPEED_MAX):
                        print('WARNING: Wind speed', windSpeed1, 'out of bounds at', dt, ', will be ignored.')
                        windSpeed1 = FLAG
                elif wdir1:
                    windDir1 = float(row[columnWindDir1])  # Wind direction at level 1.
                    if windDir1 == 360.0: # Change wind direction of 360 to 0 for simplicity.
                        windDir1 = 0.0
                    # Be sure wind direction is not out of bounds.
                    if (windDir1 < 0.0 or
                        windDir1 >= 360.0):
                        print('WARNING: Wind direction', windDir1, 'out of bounds at', dt, ', will be ignored.')
                        windDir1 = FLAG
                elif sdw1:
                    stdDevW1 = float(row[columnStdDevW1])  # Standard deviation of the level 1 vertical velocity (m/s).
                    if stdDevW1 < 0.0: # Constrain variable to be positive.
                        stdDevW1 = 0.0
                    # Be sure standard deviation of vertical velocity is not out of bounds.
                    if (stdDevW1 < STD_DEV_W_MIN or
                        stdDevW1 >= STD_DEV_W_MAX):
                        print('WARNING: Std. Dev. level 1 vertical velocity', stdDevW1, ' too low or too high at',
                              dt, ', will be ignored.')
                        stdDevW1 = FLAG
                elif sw:
                    swDown = float(row[columnSWDown])  # Downward shortwave irradiance at the surface (W/m2).
                    if swDown < 0.0: # Constrain variable to be positive.
                        swDown = 0.0
                    # Be sure downward shortwave radiation is not out of bounds.
                    if (swDown < SHORTWAVE_DOWN_MIN or
                        swDown >= SHORTWAVE_DOWN_MAX):
                        print('WARNING: Downward shortwave irradiance', swDown, ' too low or too high at',
                              dt, ', will be ignored.')
                        swDown = FLAG
                    # If day has been specified, process only times with swDown above threshold.
                    if (day and
                        swDown < SHORTWAVE_DOWN_THRESH):
                        continue  # Skip to next time.
                    # If night has been specified, process only times with swDown below threshold.
                    if (night and
                        swDown >= SHORTWAVE_DOWN_THRESH):
                        continue  # Skip to next time.
                elif abshum0:
                    t0 = float(row[columnTemp0])
                    rh = float(row[columnRh])
                    if (t0 < TEMP0_MIN or
                        t0 >= TEMP0_MAX or
                        rh < RH_MIN or
                        rh > RH_MAX):
                        abshum0 = FLAG
                elif temp0:
                    t0 = float(row[columnTemp0])
                    # Be sure temperature is not out of bounds.
                    if (t0 < TEMP0_MIN or
                        t0 >= TEMP0_MAX):
                        t0 = FLAG
                elif precip:
                    precip1 = float(row[columnPrecip])
                    # Be sure precip is not out of bounds.
                    if (precip < TPRECIP_MIN or
                        precip >= TPRECIP_MAX):
                        precip1 = FLAG
                elif stability:
                    windSpeed1 = float(row[columnWindSpeed1])  # Wind speed at level 1 (10 m) in m/s.
                    stdDevW1 = float(row[columnStdDevW1])  # Standard deviation of the level 1 vertical velocity (m/s).
                    if stdDevW1 < 0.0: # Constrain variable to be positive.
                        stdDevW1 = 0.0
                    swDown = float(row[columnSWDown])  # Downward shortwave irradiance at the surface (W/m2).
                    if swDown < 0.0: # Constrain variable to be positive.
                        swDown = 0.0
                # -----------------------------------------------------    
                # Data for this time will be used, if it's not flagged. 
                #   Add the value to a list of all obs.
                # -----------------------------------------------------    
                if wdir1:
                    # Calculate u and v.
                    if windSpeed1 != FLAG and windDir1 != FLAG:
                        u1 = -windSpeed1 * math.sin(2.*math.pi*windDir1/360.)
                        v1 = -windSpeed1 * math.cos(2.*math.pi*windDir1/360.)
                        # Add value to list of all obs.
                        obsAll.append(windDir1)
                        u1All.append(u1)
                        v1All.append(v1)
                        # Add to list of all datetimes with good data.
                        dtList.append(dt)
                        if verbosity >= 1:
                            # Collect data for distribution of obs by hour.
                            hh = datetime.strftime(dt, '%H')
                            obsHour[int(hh)].append(windDir1)
                            u1Hour[int(hh)].append(u1)
                            v1Hour[int(hh)].append(v1)
                            # Collect data for distribution of obs by month.
                            obsMonth[int(mm)-1].append(windDir1)
                            u1Month[int(mm)-1].append(u1)
                            v1Month[int(mm)-1].append(v1)
                else:
                    # Collect data for variables other than wind direction.
                    if wspd1:
                        ob = windSpeed1
                    elif sdw1:
                        ob = stdDevW1
                    elif sw:
                        ob = swDown
                    elif stability:
                        stabilityClassFinal = calcStability(z0, WIND_SPEED_MAX,
                                                            dt, swDown, stdDevW1, windSpeed1)
                        if stabilityClassFinal is not None:
                            # Convert class to numerical so that it can be averaged and plotted.
                            ob = stabilityClassNumerical[stabilityClassFinal]
                            # Add value to list of all obs.
                            obsAll.append(ob)
                            # If verbose, list each time and stability.
                            if verbosity >= 2:
                                print(dt, ',', stabilityClassFinal, ',', ob)
                        else:
                            # Stability couldn't be calculated, skip to next time.
                            continue
                    elif abshum0:
                        # Calculate absolute humidity (vapor density).
                        tK = float(t0) + 273.15
                        es = 611.2*math.exp((17.67*float(t0))/(float(t0)+243.5))
                        e = 0.01*float(rh) * es
                        absHum = 1000.0 * (MW*e) / (R*tK)
                        ob = absHum
                    elif temp0:
                        ob = t0
                    elif precip:
                        ob = precip1
                    if ob != FLAG:
                        # Add value to list of all obs.
                        obsAll.append(ob)
                        # Add to list of all datetimes with good data.
                        dtList.append(dt)
                        if verbosity >= 1:
                            # Collect data for distribution of obs by hour.
                            hh = datetime.strftime(dt, '%H')
                            obsHour[int(hh)].append(ob)
                            # Collect data for distribution of obs by month.
                            obsMonth[int(mm)-1].append(ob)
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
print('\n')

# ----------------------------------------------------------
# If a summary file is not already present, create a new one
#   and write the data range.
# ----------------------------------------------------------
if (os.path.isfile(SUMMARY_FILE) and
    os.path.getsize(SUMMARY_FILE) > 0):
    # File already exists, just append to it.
    print('\nAppending to summary file for results:', SUMMARY_FILE)
    summaryFile = open(SUMMARY_FILE, 'a')
else:
    print('\nWriting new summary file for results:', SUMMARY_FILE)
    # Create the file and write introductory info.
    summaryFile = open(SUMMARY_FILE, 'w')
    datetimeNow = datetime.now()
    summaryFile.write(datetimeNow.strftime('%Y-%m-%d %H:%M:%S'))
    summaryFile.write('\n\nResults from tower2stats.py')
    summaryFile.write('\nReading LANL file: ' + metFile)
    firstDate = str(dtFirst)
    lastDate = str(dtLast)
    summaryFile.write('\nData from: ' +  str(dtFirst) + 
                      '\nto       : ' + str(dtLast) + '\n')

# -------------------------------------
# Print data starting and ending times.
# -------------------------------------
print('\nData from:', dtFirst, 
      '\nto       :', dtLast) 

# -----------------------------------------
# Calculate and print averages and medians.
# -----------------------------------------
if wdir1:
    # Special method for wind direction.
    avgU1All = statistics.mean(u1All)
    avgV1All = statistics.mean(v1All)
    avgWindDir1All = (180./math.pi)*math.atan2(avgU1All, avgV1All) + 180.
    print('\n{:s} average for all obs: {:.1f}'.format(varName, avgWindDir1All))
    if verbosity >= 1:
        medianU1All = statistics.median(u1All)
        medianV1All = statistics.median(v1All)
        medianWindDir1All = (180./math.pi)*math.atan2(medianU1All, medianV1All) + 180.
        print('{:s} median for all obs: {:.1f}'.format(varName, medianWindDir1All))
    if verbosity >= 1:
        print('\n{:s} hourly averages:'.format(varName))
        for hour in range(0,24):
            if (len(u1Hour[hour]) > 0 and
                len(v1Hour[hour]) > 0):
                avgU1Hour = statistics.mean(u1Hour[hour])
                avgV1Hour = statistics.mean(v1Hour[hour])
                avgWindDir1Hour = (180./math.pi)*math.atan2(avgU1Hour, avgV1Hour) + 180.
                print('   {:d}: {:.1f}'.format(hour, avgWindDir1Hour))
        print('\n{:s} hourly medians:'.format(varName))
        for hour in range(0,24):
            if (len(u1Hour[hour]) > 0 and
                len(v1Hour[hour]) > 0):
                medianU1Hour = statistics.median(u1Hour[hour])
                medianV1Hour = statistics.median(v1Hour[hour])
                medianWindDir1Hour = (180./math.pi)*math.atan2(medianU1Hour, medianV1Hour) + 180.
                print('   {:d}: {:.1f}'.format(hour, medianWindDir1Hour))
        if not args.month:
            print('\n{:s} monthly averages:'.format(varName))
            for mon in range(0, 12):
                if (len(u1Month[mon]) > 0 and
                    len(v1Month[mon]) > 0):
                    avgU1Month = statistics.mean(u1Month[mon])
                    avgV1Month = statistics.mean(v1Month[mon])
                    avgWindDir1Month = (180./math.pi)*math.atan2(avgU1Month, avgV1Month) + 180.
                    print('   {:d}: {:.1f}'.format(mon+1, avgWindDir1Month))
            print('\n{:s} monthly medians:'.format(varName))
            for mon in range(0, 12):
                if (len(u1Month[mon]) > 0 and
                    len(v1Month[mon]) > 0):
                    medianU1Month = statistics.median(u1Month[mon])
                    medianV1Month = statistics.median(v1Month[mon])
                    medianWindDir1Month = (180./math.pi)*math.atan2(medianU1Month, medianV1Month) + 180.
                    print('   {:d}: {:.1f}'.format(mon+1, medianWindDir1Month))
elif stability:
    # Just print numerical average of classes.
    avgAll = statistics.mean(obsAll)
    print('\n{:s} average for all obs: {:.2f}'.format(varName, avgAll))
    print(stabilityClassNumerical)
elif precip:
    # Calculate total precipitation over the data period.
    sumAll = sum(obsAll)
    print('\n{:s} total for all obs: {:.2f}'.format(varName, sumAll))
    # Also write to summary file.
    summaryFile.write('\n{:s} total for all obs: {:.2f}'.format(varName, sumAll))
    # Also write precipitation in cm for FTWC.
    print('\nPrecipitation (cm) total for all obs (cm): {:.2f}'.format(2.54*sumAll))
    summaryFile.write('\nPrecipitation (cm) total for all obs: {:.2f}'.format(2.54*sumAll))
else:
    # Ordinary means for other variables.
    avgAll = statistics.mean(obsAll)
    print('\n{:s} average for all obs: {:.2f}'.format(varName, avgAll))
    # Also write to summary file.
    summaryFile.write('\n{:s} average for all obs: {:.2f}'.format(varName, avgAll))
    if verbosity >= 1:
        medianAll = statistics.median(obsAll)
        print('{:s} median for all obs: {:.2f}'.format(varName, medianAll))
        # Also write to summary file.
        summaryFile.write('\n{:s} median for all obs: {:.2f}'.format(varName, medianAll))
    if verbosity >= 1:
        print('\n{:s} hourly averages:'.format(varName))
        for hour in range(0,24):
            if len(obsHour[hour]) > 0:
                avgHour = statistics.mean(obsHour[hour])
                print('   {:d}: {:.2f}'.format(hour, avgHour))
        print('\n{:s} hourly medians:'.format(varName))
        for hour in range(0,24):
            if len(obsHour[hour]) > 0:
                medianHour = statistics.median(obsHour[hour])
                print('   {:d}: {:.2f}'.format(hour, medianHour))
        print('\n{:s} monthly averages:'.format(varName))
        for mon in range(0, 12):
            if len(obsMonth[mon]) > 0:
                avgMonth = statistics.mean(obsMonth[mon])
                print('   {:d}: {:.2f}'.format(mon+1, avgMonth))
        print('\n{:s} monthly medians:'.format(varName))
        for mon in range(0, 12):
            if len(obsMonth[mon]) > 0:
                medianMonth = statistics.median(obsMonth[mon])
                print('   {:d}: {:.2f}'.format(mon+1, medianMonth))

if verbosity >= 2:
    # --------------------------------------
    # Print simple depiction of frequencies.
    # --------------------------------------
    # Count number of obs for each integer value:
    nObs = len(obsAll)
    obMin = min(obsAll)
    obMax = max(obsAll)
    if wdir1:
        # Bins for wind direction.
        countObs = {}
        for bin in windDirBins.keys():
            if (bin == 'N1' or
                bin == 'N2'):
                countObs['N'] = 0
            else:
                countObs[bin] = 0
        # Assign the wind direction bin.
        for ob in obsAll:
            for bin in windDirBins.keys():
                if (ob >= windDirBins[bin][0] and
                    ob < windDirBins[bin][1]):
                    if (bin == 'N1' or
                        bin == 'N2'):
                        windDirBin = 'N'
                    else:
                        windDirBin = bin
                    countObs[windDirBin] += 1
    elif stability:
        # Stability classes are bins.
        countObs = {}
        for bin in stabilityBins:
            countObs[bin] = 0
        # Assign the stability bin.
        for ob in obsAll:
            countObs[ob] += 1
    else:
        # Integer bins for other variables.
        countObs = {}
        for intValue in range(int(obMin), int(obMax)+1):
            countObs[str(intValue)] = 0
        for ob in obsAll:
            countObs[str(int(ob))] += 1
    # Show frequency with a bar graph.
    bins = countObs.keys()
    print('\n{:s} frequencies for {:d} obs:'.format(varName, nObs))
    for bin in bins:
        frequency = 100. * (float(countObs[bin])/float(nObs))
        frequencySymbol = int(frequency) * '#'
        print('{:3s}: {:s} {:.1f}%'.format(bin, frequencySymbol, frequency))
    # -------------------
    # Hourly frequencies.
    # -------------------
    print('\n{:s} hourly frequencies:'.format(varName))
    for hour in range(0,24):
        if len(obsHour[hour]) > 0:
            nObs = len(obsHour[hour])
            obMin = min(obsHour[hour])
            obMax = max(obsHour[hour])
            if wdir1:
                countObs = {}
                for bin in windDirBins.keys():
                    if (bin == 'N1' or
                        bin == 'N2'):
                        countObs['N'] = 0
                    else:
                        countObs[bin] = 0
                # Assign the wind direction bin.
                for ob in obsHour[hour]:
                    for bin in windDirBins.keys():
                        if (ob >= windDirBins[bin][0] and
                            ob < windDirBins[bin][1]):
                            if (bin == 'N1' or
                                bin == 'N2'):
                                windDirBin = 'N'
                            else:
                                windDirBin = bin
                            countObs[windDirBin] += 1
            elif stability:
                # Stability classes are bins.
                countObs = {}
                for bin in stabilityBins:
                   countObs[bin] = 0
                # Assign the stability bin.
                for ob in obsHour[hour]:
                    countObs[ob] += 1
            else:
                countObs = {}
                for intValue in range(int(obMin), int(obMax)+1):
                    countObs[str(intValue)] = 0
                for ob in obsHour[hour]:
                    countObs[str(int(ob))] += 1
            # Show frequency with a bar graph.
            bins = countObs.keys()
            print('\n    Hour {:d} {:s} frequencies for {:d} obs:'.format(hour, varName, nObs))
            for bin in bins:
                frequency = 100. * (float(countObs[bin])/float(nObs))
                frequencySymbol = int(frequency) * '#'
                print('    {:3s}: {:s} {:.1f}%'.format(bin, frequencySymbol, frequency))
    # -------------------
    # Monthly frequencies.
    # -------------------
    if not args.month:
        print('\n{:s} monthly frequencies:'.format(varName))
        for mon in range(0,12):
            nObs = len(obsMonth[mon])
            obMin = min(obsMonth[mon])
            obMax = max(obsMonth[mon])
            if wdir1:
                countObs = {}
                for bin in windDirBins.keys():
                    if (bin == 'N1' or
                        bin == 'N2'):
                        countObs['N'] = 0
                    else:
                        countObs[bin] = 0
                # Assign the wind direction bin.
                for ob in obsMonth[mon]:
                    for bin in windDirBins.keys():
                        if (ob >= windDirBins[bin][0] and
                            ob < windDirBins[bin][1]):
                            if (bin == 'N1' or
                                bin == 'N2'):
                                windDirBin = 'N'
                            else:
                                windDirBin = bin
                            countObs[windDirBin] += 1
            elif stability:
                # Stability classes are bins.
                countObs = {}
                for bin in stabilityBins:
                    countObs[bin] = 0
                # Assign the stability bin.
                for ob in obsMonth[mon]:
                    countObs[ob] += 1
            else:
                countObs = {}
                for intValue in range(int(obMin), int(obMax)+1):
                    countObs[str(intValue)] = 0
                for ob in obsMonth[hour]:
                    countObs[str(int(ob))] += 1
            # Show frequency with a bar graph.
            bins = countObs.keys()
            print('\n    Month {:d} {:s} frequencies for {:d} obs:'.format(mon+1, varName, nObs))
            for bin in bins:
                frequency = 100. * (float(countObs[bin])/float(nObs))
                frequencySymbol = int(frequency) * '#'
                print('    {:3s}: {:s} {:.1f}%'.format(bin, frequencySymbol, frequency))

        # --------------------------------------------------------------
        # For stability, find fraction of days which include each class.
        # --------------------------------------------------------------
        if stability:
            obsDay = {}
            # Go through each time.
            for dt, ob in zip(dtList, obsAll):
                yyyymmdd = datetime.strftime(dt, '%Y%m%d')
                #print(dt, yyyymmdd, ob) 
                if yyyymmdd not in obsDay:
                    # Add new day to list.
                    obsDay[yyyymmdd] = []
                # Collect all classes for each calendar day. 
                obsDay[yyyymmdd].append(ob)
            # Now go through each class and find frequency of days which have it.
            countObs = {}
            for bin in stabilityBins:
                countObs[bin] = 0
            for bin in stabilityBins:
                for yyyymmdd in obsDay.keys():
                    if bin in obsDay[yyyymmdd]:
                        #if bin == 'A': print(yyyymmdd, obsDay[yyyymmdd])
                        countObs[bin] += 1
            # Show frequency with a bar graph.
            bins = countObs.keys()
            nObs = len(obsDay.keys())
            print('\n    Frequency of days with one or more occurrences of each stability bin:')
            for bin in bins:
                frequency = 100. * (float(countObs[bin])/float(nObs))
                frequencySymbol = int(frequency) * '#'
                print('    {:3s}: {:s} {:.1f}%'.format(bin, frequencySymbol, frequency))

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
