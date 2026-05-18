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
    print('   ', yyyy, '{0: .1f}% of possible 15 min times is being used'.format(presentPct))


def addFrequencies(frequency,
                   windDirections, stabilityClasses, windSpeeds):
    """
    Calculate total of all frequencies, should add up to 1. 
    Ken Waight / March 2023
    May 2024 / Optionally, round to four significant
               digits, as the STARGET program appparently does.
    """
    frequencyTotal = 0.0
    for windDirection in windDirections:
        for stability in stabilityClasses:
            for windSpeed in windSpeeds:
                if ROUND_FREQUENCIES:
                    frequencyTotal += round(frequency[windDirection][stability][windSpeed], 4)
                else:
                    frequencyTotal += frequency[windDirection][stability][windSpeed]
    return frequencyTotal


def adjustFrequency(frequency,
                    windDirections, stabilityClasses, windSpeeds,
                    frequencyDiff):
    """
    Make minor adjustment to the frequency dictionary to force it to total to exactly 1.
    Ken Waight / March 2023
    """
    if frequencyMax > frequencyDiff:
        frequency[windDirectionMax][stabilityMax][windSpeedMax] -= frequencyDiff
        print('Subtracted', frequencyDiff, 'from category:', windDirectionMax, windSpeedMax, stabilityMax)
        adjusted = True 
        return adjusted, frequency
    else:
        # No adjustment possible.
        print('No adjustment to 1.0 was possible.')
        adjusted = False
        return adjusted, frequency


# ==============
# MAIN PROGRAM.
# ==============
"""
tower2star.py
Read a 15-min csv file for one tower site, calculate the frequency of wind for a set of wind directions, wind
  speeds and stability classes, and write a file in the STAR format, ready to be converted to a WND file for input 
  into CAP88. Uses information from:
    1. EPA report EPA-454/R-99-005, "Meteorological Monitoring Guidance for Regulatory Modeling Applications" (2000)
    2. Los Alamos report LA-11735-MS, "Los Alamos Climatology" by Bruce Bowen (1990)
    3. LANL Technical Procedures document EPC-ES-TP-501, "Dose Assessment Using CAP88" by Mike McNaughton, (2018)
Usage: python tower2star.py [-v] [-day | -night] [-mon month] [-raw] metfile  [-o starfile] 
                            [-z0 roughness] [-windheight height]  metfile is the name of the met file to read. It is assumed to be in the format downloaded from the Weather Machine.
    The -raw option is used to read a raw file from the datalogger.
  The output CAP88 STAR file will be named data.str, unless a different name is specified with the -o option.
Ken Waight / February 2020
"""

# ----------
# Constants.
# ----------
WIND_DIR_BIN_DIAG = 'W'  # Print diagnostic information for this combination of wind dir, stability and wind speed.
STABILITY_CLASS_DIAG = 'D'
WIND_SPEED_BIN_DIAG = '4'
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
WIND_MEASUREMENT_HEIGHT = 10.0  # Lowest measurement height assumed to be 10 m -- use "-windheight 11.5" for most LANL towers.
ADJUST_FREQUENCY = False  # Try to slightly adjust one frequency to make the total exactly 1.
ROUND_FREQUENCIES = False  # Round frequencies to four digits when calculating total, because that's
                          #   what the STARGET program seems to do.

# ----------------------------------------------------------------
# Parse arguments.
# Get name of met file to read. There are two types:
#   1. A 15 min file downloaded from the Weather Machine (default)
#   2. A raw 15 min file, with or without header lines (optional)
# The name of the STAR file produced will be data.str, unless a
#   different name is specified.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a Weather Machine data file and produce a CAP-88 STAR file, with a default name of data.str")
parser.add_argument("metfile", help="Name of met file to read")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
parser.add_argument("-raw", "--datalogger", help="File is in the raw met format (from the datalogger)",
                    action="store_true")
parser.add_argument("-z0", "--roughness", help="Roughness length (cm), used for stability determination")
parser.add_argument("-windheight", "--windheight", help="Wind measurement height (m), used for stability determination if it's not the 10 m default")
group = parser.add_mutually_exclusive_group()
group.add_argument("-day", "--day", help="Use only daytime data",
                    action="store_true")
group.add_argument("-night", "--night", help="Use only nighttime data",
                    action="store_true")
parser.add_argument("-mon", "--month", help="Use data from any year but only a single specified month (1-12)")
parser.add_argument("-o", "--starfile", help="Alternate name of the CAP-88 STAR file that will be written")
group.add_argument("-estimate10m", "--estimate10m", help="Use power law to adjust measured wind speeds to standard 10 m height.",
                    action="store_true")
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
if args.windheight:
    windMeasurementHeight = float(args.windheight)
else:
    windMeasurementHeight = WIND_MEASUREMENT_HEIGHT # Use default.
estimate10m = args.estimate10m

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
columnDateTime1 = 'datetime'  # From current Weather Machine Data Request.
columnDateTime2 = 'DateTime'  # From WMDC Download (with the order reversed).
columnDateTime3 = 'Date/Time' # From a Data Dump.
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
if args.starfile:
    starFile = args.starfile
else:
    starFile = 'data.str'

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
# Initial stability classes from EPA, so any LANL roughness adjustment will be made below.
stabilityClassesInitial = {'A': [11.5, SIGMA_E_MAX], 'B': [10.0, 11.5],
                           'C': [7.8, 10.0], 'D': [5.0, 7.8],
                           'E': [2.4, 5.0], 'F': [0.0, 2.4]}

# Coefficients for stability class adjustment for non-standard (not 10 m)
#   wind measurement height (from EPA guidance).
pTheta = {'A': 0.02, 'B': 0.04, 'C': 0.01, 'D': -0.14, 'E': -0.31}

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

# Wind speed power law exponents for each stability class (from EPA guidance).
powerLawExponentRural = {'A': 0.07, 'B': 0.07, 'C': 0.10, 'D': 0.15, 'E': 0.35, 'F': 0.55}

# =======
# Banner.
# =======
print(' =====================================\n',
      'Creation of a STAR file for CAP88\n',
      '=====================================\n')

# Show stability, wind direction and wind speed categories.
print('Stability categories:')
print(*stabilityClasses)    
print('\nWind direction categories:')
print(*windDirections)
print('\nWind speed categories:')
for bin in windSpeedBins.keys():
    print('{:s}: {:.1f} - {:.1f} m/s'.format(bin, windSpeedBins[bin][0], windSpeedBins[bin][1]))

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
            count[windDirection][stability][windSpeed] = 0
            frequency[windDirection][stability][windSpeed] = 0

# Modify sigma-E values used for initial stability class determination by 
#   roughness factor.
#z0 = 0.75*z0  # Experiment with lower roughness.
#z0 = 1.5*z0  # Experiment with higher roughness.
print('\nRoughness length (z0) used to adjust stability category determination:', 
      z0)
z0Correction = (z0/15.)**0.2
for stability in stabilityClassesInitial.keys():
    stabilityClassesInitial[stability][0] *= z0Correction
    stabilityClassesInitial[stability][1] *= z0Correction

# Modify sigma-E values used for initial stability class determination, if
#   the wind measurement height is not 10 m.
if windMeasurementHeight == 10.:
    print('\nWind measurement height assumed to be 10 m,',
          'so no adjustment of stability categories.')
else:
    print('\nNon-standard wind measurement height (not 10 m)',
          'used to adjust stability category determination:', 
          windMeasurementHeight)
    heightCorrectionA = (windMeasurementHeight/10.)**pTheta['A']
    heightCorrectionB = (windMeasurementHeight/10.)**pTheta['B']
    heightCorrectionC = (windMeasurementHeight/10.)**pTheta['C']
    heightCorrectionD = (windMeasurementHeight/10.)**pTheta['D']
    heightCorrectionE = (windMeasurementHeight/10.)**pTheta['E']
    stabilityClassesInitial['A'][0] *= heightCorrectionA
    stabilityClassesInitial['B'][1] *= heightCorrectionA
    stabilityClassesInitial['B'][0] *= heightCorrectionB
    stabilityClassesInitial['C'][1] *= heightCorrectionB
    stabilityClassesInitial['C'][0] *= heightCorrectionC
    stabilityClassesInitial['D'][1] *= heightCorrectionC
    stabilityClassesInitial['D'][0] *= heightCorrectionD
    stabilityClassesInitial['E'][1] *= heightCorrectionD
    stabilityClassesInitial['E'][0] *= heightCorrectionE
    stabilityClassesInitial['F'][1] *= heightCorrectionE

if windMeasurementHeight == 10.:
    print('\nWind measurement height assumed to be 10 m,',
          'so no estimation of wind speed at 10 m.')
else:
    if estimate10m:
        print('\nFinal wind speeds will be estimated at 10 m from power law.')
    else:
        print('\nWind speeds will NOT be estimated at 10 m from power law,',
              'even though the measurement height is not 10 m')

if verbosity >= 1:
    print('\nInitial stability class criteria after adjustments:',
          stabilityClassesInitial)

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
    csvFile = 'tower2star.csv'    
    csvOut =  open(csvFile, 'w')
    print('\nWriting diagnostic info for each time to CSV file:', csvFile)
    header = ''
    header += '\nDate/Time       '
    header += '  {:>9s}'.format('dir1')
    header += '  {:>9s}'.format('spd1(m/s)')
    header += '  {:>9s}'.format('swdn(W/m2)')
    header += '  {:>9s}'.format('sdw1(m/s)')
    header += '  {:>9s}'.format('stabilityClass')
    csvOut.write(','.join(header.split()) + '\n')

# --------------------------------------------------------------------
# Read LANL 15-minute data at one tower location.
#   For each set of valid 15 min values, find the wind direction bin,
#   wind speed bin and stability class, and increment the counter for
#   that combination.
# --------------------------------------------------------------------
print("\nReading LANL file:", metFile)
dtFirst = None
dtLast = None
dtFound = []
dtList = []
nFound = 0
nFlag = 0
nIgnore = 0
nBad = 0
nDiag = 0
with open(metFile, 'r') as infile:
    towerData = csv.DictReader(infile)
    for row in towerData:
        try:
            row[columnDateTime1]
            columnDateTime = columnDateTime1
        except KeyError:
            try:
                row[columnDateTime2]
                columnDateTime = columnDateTime2
            except KeyError:
                try:
                    row[columnDateTime3]
                    columnDateTime = columnDateTime3
                except:
                    print('ERROR: Date and time column header not correct?')
                    print('  Should be datetime, DateTime or Date/Time!')
                    sys.exit(1)
        if (row[columnDateTime] and  # Date/time column.
            row[columnWindSpeed1] and
            row[columnStdDevW1] and
            (re.search(r'^\d+-\d+-\d+ \d+:\d+', row[columnDateTime]) or
             re.search(r'^\d+/\d+/\d+ \d+:\d+', row[columnDateTime]))):
            # This should be a data line (ignore header lines).
            #print('row[0]:', row[columnDateTime]) #ktw
            try:
                # Try a yellow Weather Machine-formatted date.
                dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M:%S")
            except:
                try:
                    # Try a datalogger-formatted date.
                    dt = datetime.strptime(row[columnDateTime], "%m/%d/%Y %H:%M")
                except:
                    # Try a new Weather Machine-formatted date.
                    dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M")
            nFound += 1
            dtFound.append(dt)
            # Save first time.
            if dtFirst is None:
                dtFirst = dt
            # --------------------------------------------------------------
            # Save data if wind speed, wind direction and standard deviation
            #   of vertical velocity are unflagged.
            # --------------------------------------------------------------
            if ('*' in row[columnWindSpeed1] or  # Need wind speed to be unflagged.
                '*' in row[columnWindDir1] or  # Need wind speed to be unflagged.
                '*' in row[columnStdDevW1]):  # Need std. dev. of level 1 vertical velocity to be unflagged.
                #'*' in row[columnSWDown]):  # Need downward shortwave to be unflagged.
                nFlag += 1
            else:
                # --------------------------------------
                # Raw variables needed for calculations.
                # --------------------------------------
                windSpeed1 = float(row[columnWindSpeed1])  # Wind speed at level 1 (10 m) in m/s.
                windDir1 = float(row[columnWindDir1])  # Wind direction at level 1.
                stdDevW1 = float(row[columnStdDevW1])  # Standard deviation of the level 1 vertical velocity (m/s).
                # Constrain variables to be positive.
                if stdDevW1 < 0.0:
                    stdDevW1 = 0.0
                # Change wind direction of 360 to 0 for simplicity.
                if windDir1 == 360.0:
                    windDir1 = 0.0
                # -----------------------------------------------------------------------
                # Try to determine day/night from swDown, or if it is not present, assume
                #   that 6 am to 6 pm is daytime, regardless of date.
                # -----------------------------------------------------------------------
                try:
                    # Shortwave value found.
                    swDown = float(row[columnSWDown])  # Downward shortwave irradiance at the surface (W/m2).
                    if swDown >= SHORTWAVE_DOWN_THRESH:
                        dayNow = True
                    else:
                        dayNow = False
                except:
                    # Shortwave value not found, so use hour of day to make an assumption.
                    hr = int(datetime.strftime(dt, '%H'))
                    if (hr >= 6 and hr < 18):
                        dayNow = True
                    else:
                        dayNow = False
                # -----------------------------------------------------------------------
                # Ignore undesired times, at the wrong time of day or in the wrong month.
                # -----------------------------------------------------------------------
                # If day has been specified, process only times assumed to be daytime.
                if (day and
                    dayNow is False):
                    nIgnore += 1
                    continue  # Skip to next time.
                # If night has been specified, process only times assumed to be nighttime.
                if (night and
                    dayNow is True):
                    nIgnore += 1
                    continue  # Skip to next time.
                # If a month has been specified, process only times in that month, for any year.
                mm = datetime.strftime(dt, '%m')
                if (month and
                    int(mm) != int(month)):
                    nIgnore += 1
                    continue  # Skip to next time.
                # -----------------------------------------------------
                # Calculate sigma-E, converted from radians to degrees.
                # -----------------------------------------------------
                if windSpeed1 != 0.0:
                    sigmaE = (stdDevW1/windSpeed1) * (180/math.pi)
                else:
                    if verbosity >= 1:
                        print('WARNING: Cannot calculate sigma-E and stability class with a zero wind speed at', dt,
                              ', will be ignored.')
                    nBad += 1
                    continue
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
                # -----------------------------------------------------------------------------    
                # Data for this time will be used. Add to list of all datetimes with good data.
                # -----------------------------------------------------------------------------    
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
                # Calculate the initial stability class.
                # ---------------------------------------------------------
                for stabilityClass in stabilityClassesInitial.keys():
                    if (sigmaE >= stabilityClassesInitial[stabilityClass][0] and
                        sigmaE < stabilityClassesInitial[stabilityClass][1]):
                        stabilityClassInitial = stabilityClass
                # ---------------------------------------------------------
                # Use different wind speed adjustments for day and night.
                # ---------------------------------------------------------
                if dayNow:
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
                if windMeasurementHeight != 10. and estimate10m:
                    # ----------------------------------------------------------------
                    # Estimate the wind speed at 10 m with the wind profile power law.
                    #   Use rural power law exponents from the EPA guidance.
                    # ----------------------------------------------------------------
                    windSpeed1 = windSpeed1 * (10./windMeasurementHeight)**\
                                 powerLawExponentRural[stabilityClassFinal]
                # ---------------------------------------------------------
                # Assign the wind speed bin.
                # ---------------------------------------------------------
                for bin in windSpeedBins.keys():
                    if (windSpeed1 >= windSpeedBins[bin][0] and
                        windSpeed1 < windSpeedBins[bin][1]):
                        windSpeedBin = bin
                # -------------------------------------------------------------------------------
                # Increment the counter for this wind direction/wind speed/stability class combo.
                # -------------------------------------------------------------------------------
                count[windDirBin][stabilityClassFinal][windSpeedBin] += 1
                # --------------------------------------------------
                # Optionally write data for all times to a CSV file.
                # --------------------------------------------------
                if verbosity >= 2:
                    line = '{:s},'.format(datetime.strftime(dt, '%Y-%m-%d %H:%M'))
                    line += '{:f},'.format(windDir1)
                    line += '{:f},'.format(windSpeed1)
                    line += '{:f},'.format(swDown)
                    line += '{:f},'.format(stdDevW1)
                    line += '{:s},'.format(stabilityClassFinal)
                    csvOut.write('{:s}\n'.format(line))
                # --------------------------------------------------------------------------       
                # Optionally print diagnostic information for a specified set of categories.
                # --------------------------------------------------------------------------       
                if (verbosity >= 2 and
                    windDirBin == WIND_DIR_BIN_DIAG and
                    stabilityClassFinal == STABILITY_CLASS_DIAG and
                    windSpeedBin == WIND_SPEED_BIN_DIAG):
                    nDiag += 1
                    print('\n', nDiag, 'Diagnostic categories', WIND_DIR_BIN_DIAG, STABILITY_CLASS_DIAG,
                           WIND_SPEED_BIN_DIAG, 'found at time:', dt)
                    print('wind direction:', windDir1, ', wind speed:', windSpeed1, ', std. dev. w1:', stdDevW1,
                          ', downward shortwave:', swDown)
                    print('SigmaE value is', sigmaE)
                    print('Stability class changes from', stabilityClassInitial,
                          'to', stabilityClassFinal)
            # Save the last time.

# ----------------------------------------
# Make list of all possible 15 min times.
# ----------------------------------------
print('\nBuild list of all possible 15 min times')
dt15All = []
dtLast = dtFound[-1]
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
print('\nCalculate how much data is being used for each year:')
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
nUsed = len(dtList)

# ----------------------------------------------------------------
# Print total number of good, bad, flagged and ignored data times.
# ----------------------------------------------------------------
if nTotal == 0:
    print('\nERROR: No good data found!')
    sys.exit(1)
print('\n----------------------------')
print('Summary of data found')
print('----------------------------')
nPossible = len(dt15All)
print(nPossible, 'total possible 15 min times over the period of the data file.')
pct = 100.0 * (float(nFound) / float(nPossible))
print(nFound, 'times with data found, {:.2f}% of possible'.format(pct))
nUnique = len(list(set(dtFound)))
nDup = nFound - nUnique
pct = 100.0 * (float(nDup) / float(nFound))
print(nDup, 'duplicate times found, {:.2f}% of found times'.format(pct))
pct = 100.0 * (float(nFlag) / float(nFound))
print(nFlag, 'times with flagged data skipped, {:.2f}% of found times'.format(pct))
pct = 100.0 * (float(nBad) / float(nFound))
print(nBad, 'times with bad/out of range data, {:.2f}% of found times'.format(pct))
pct = 100.0 * (float(nIgnore) / float(nFound))
print(nIgnore, 'times ignored (wrong time of day or month), {:.2f}% of found times'.format(pct))
pct = 100.0 * (float(nUsed) / float(nFound))
print(nUsed, 'times used to create STAR file, {:.2f}% of found times'.format(pct))
if verbosity >= 2:
    diagPct = 100.0 * (float(nDiag) / float(nTotal))
    print(nDiag, 'times found for diagnostic categories, {:.2f}% of total'.format(diagPct))

# ------------------------------------------------------------------------------------------
# Calculate frequencies.
# ------------------------------------------------------------------------------------------
print('\n----------------------------------------------------------------------------------------')
print('Calculate frequencies for each combination of wind direction/stability class/wind speed:')
print('----------------------------------------------------------------------------------------')
frequencyStability = {}
for stability in stabilityClasses: 
    frequencyStability[stability] = 0.0
frequencyWindDirection= {}
for windDirection in windDirections:
    frequencyWindDirection[windDirection] = 0.0
frequencyWindSpeed= {}
for windSpeed in windSpeeds:
    frequencyWindSpeed[windSpeed] = 0.0
# Find category with maximum frequency.
frequencyMax = 0.0
# --------------------------------------------------------------------
# Loop through all wind directions, wind speeds and stability classes.
# --------------------------------------------------------------------
for windDirection in windDirections:
    for stability in stabilityClasses:
        for windSpeed in windSpeeds:
            frequency[windDirection][stability][windSpeed] = (float(count[windDirection][stability][windSpeed])
                                                              / float(nTotal))
            frequency[windDirection][stability][windSpeed] = round(frequency[windDirection][stability][windSpeed], 5)
            # Keep track of total for each stability, wind direction and speed.
            frequencyStability[stability] += frequency[windDirection][stability][windSpeed]
            frequencyWindDirection[windDirection] += frequency[windDirection][stability][windSpeed]
            frequencyWindSpeed[windSpeed] += frequency[windDirection][stability][windSpeed]
            # Check for maximum frequency.
            if frequency[windDirection][stability][windSpeed] > frequencyMax:
                frequencyMax = frequency[windDirection][stability][windSpeed]
                windDirectionMax = windDirection
                stabilityMax = stability
                windSpeedMax = windSpeed

# Sort by stability, wind direction and speed.
print('\nFrequency by stability class:')
frequencyStabilitySorted = sorted(frequencyStability.items(), key=lambda x: x[1], reverse=True)
for sortedItem in frequencyStabilitySorted:
    print('{:s}: {:.5f}'.format(sortedItem[0], sortedItem[1]))

print('\nFrequency by wind direction:')
frequencyWindDirectionSorted = sorted(frequencyWindDirection.items(), key=lambda x: x[1], reverse=True)
for sortedItem in frequencyWindDirectionSorted:
    print('{:s}: {:.5f}'.format(sortedItem[0], sortedItem[1]))

print('\nFrequency by wind speed:')
frequencyWindSpeedSorted = sorted(frequencyWindSpeed.items(), key=lambda x: x[1], reverse=True)
for sortedItem in frequencyWindSpeedSorted:
    print('{:s} ({:.1f}-{:.1f} m/s): {:.5f}'.format(sortedItem[0], windSpeedBins[sortedItem[0]][0], 
                                                    windSpeedBins[sortedItem[0]][1], sortedItem[1]))
# Category with the maximum frequency.
print('\nMaximum frequency:', frequencyMax, 'at category:', windDirectionMax, windSpeedMax, stabilityMax) 

# -------------------------------
# Check total of all frequencies.
# -------------------------------
frequencyTotal = addFrequencies(frequency,
                                windDirections, stabilityClasses, windSpeeds)
print('\nTotal sum of all frequencies: {:.5f}'.format(frequencyTotal))

if (ADJUST_FREQUENCY and
    frequencyTotal != 1.0):
    # ------------------------------------------------------------------------
    # Make minor change to force the total of all frequencies to be exactly 1.
    # ------------------------------------------------------------------------
    if ROUND_FREQUENCIES:
        frequencyDiff = round(frequencyTotal-1.0, 4)
    else:
        frequencyDiff = round(frequencyTotal-1.0, 5)
    if abs(frequencyDiff) > 0.0:
        adjusted, frequencyAdjusted = adjustFrequency(frequency,
                                                      windDirections, stabilityClasses, windSpeeds,
                                                      frequencyDiff)
    else:
        adjusted = False
    if adjusted:
        frequency = frequencyAdjusted
        frequencyTotal = addFrequencies(frequency,
                                        windDirections, stabilityClasses, windSpeeds)
        print('Total sum of all frequencies after adjustment: {:.5f}'.format(frequencyTotal))
    
# ---------------------------------------
# Print simple depiction of frequencies.
# ---------------------------------------
print('\nSimple depiction of frequencies:')
print('   (single digits are % of total, . is < 1%, + is >= 10%)')
frequencySymbol = {}
for stability in stabilityClasses:
    print('\nStability Class:', stability)
    print('     ------')
    for windDirection in windDirections:
        frequencySymbolString = ''
        for windSpeed in windSpeeds:
            frequencySymbol = (str(int(round(
                100.0*frequency[windDirection][stability][windSpeed], 0))))
            if int(frequencySymbol) >= 10:
                frequencySymbol = '+'
            elif int(frequencySymbol) == 0:
                if frequency[windDirection][stability][windSpeed] == 0.0:
                    frequencySymbol = ' '
                else:
                    frequencySymbol = frequencySymbol = '.'
            frequencySymbolString += frequencySymbol
        print('{:3} |{:6}|'.format(windDirection, frequencySymbolString))
    print('     ------')

# ----------------------------------
# Additional diagnostic information.
# ----------------------------------
if verbosity >= 1:
    # Print distribution of obs by hour.
    print('\nNumber of obs by hour:')
    nObs = sum(nHour)
    for hour in range(0, 24):
        frac = 100.0 * float(nHour[hour]) / float(nObs)
        print('{:2} {:5.1f}% {:d}'.format(hour, frac, nHour[hour]))
    print('\nNumber of obs by month:')
    nObs = sum(nMonth)
    for mon in range(0, 12):
        frac = 100.0 * float(nMonth[mon]) / float(nObs)
        print('{:2} {:5.1f}% {:d}'.format(mon+1, frac, nMonth[mon]))
if verbosity >= 2:
    # Print distribution of wind directions by degree.
    print('\nNumber of wind direction obs by degree:')
    for deg in range(0, 360):
        windDirectionString = ''
        for n in range(0, nWindDirectionDeg[deg]+1):
            windDirectionString += '*'
        print('{:3} {:s} {:d}'.format(deg, windDirectionString, nWindDirectionDeg[deg]))
    # Print distribution of wind speeds by m/s.
    print('\nFraction of wind speed obs by m/s:')
    nSpeeds = sum(nWindSpeed)
    for speed in range(0, 11):
        frac = 100.0 * float(nWindSpeed[speed]) / float(nSpeeds)
        print('{:2} {:5.1f}% {:d}'.format(speed, frac, nWindSpeed[speed]))
    print('11+       {:d}'.format(nWindSpeed[11]))

# ---------------------------------------------------------------------------------------------
# Write file in STAR format. The star file can be converted to a WND file for input into CAP88.
# ---------------------------------------------------------------------------------------------
print('\nWriting to STAR file:', starFile)
with open(starFile, 'w') as star:
    for stability in stabilityClasses:
        for windDirection in windDirections:
            star.write(' {:>3} {:1} '.format(windDirection, stability))
            for windSpeed in windSpeeds:
                star.write('{:7.5f}'.format(frequency[windDirection][stability][windSpeed]))
            star.write('\n')

# --------------------------
# Summarize run and options.
# --------------------------
print('\n----------------------------')
print('Summary')
print('----------------------------')
print(*sys.argv)
print('Met input data file:', metFile)
if day:
    print('Used only daytime data')
elif night:
    print('Used only nighttime data')
if args.month:
    print('Used only data for month:', month)
if args.roughness:
    print('Used custom roughness value of', z0, 'cm')
else:
    print('Assumed default roughness of', Z0, 'cm')
if args.windheight:
    print('Used custom wind measurement height of', windMeasurementHeight, 'm')
else:
    print('Assumed default wind measurement height of', WIND_MEASUREMENT_HEIGHT, 'm')
if windMeasurementHeight == 10.:
    print('Wind measurement height was assumed to be 10 m,',
          'so no estimation of wind speed at 10 m.')
else:
    if estimate10m:
        print('Final wind speeds were estimated at 10 m from power law')
    else:
        print('Wind speeds were NOT estimated at 10 m from power law,',
              'even though the measurement height is not 10 m')
if args.starfile:
    print('Output file written with a custom name:', starFile)
else:
    print('Output file written with the generic name: data.str')

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
