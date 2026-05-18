#!/usr/bin/env python3

"""
tower2list.py
Read a 15-min csv file for one tower site, print and write a file with a simple list (text/CSV) of basic variables. 
Usage: python tower2list.py [-v] [-z0 roughness] [-o csvfile] metfile  
  metfile is the name of the met file to read. It is assumed to be in the format downloaded from the Weather Machine.
Ken Waight / May 2021
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

# ==============
# FUNCTIONS.
# ==============
def calcStability(z0, WIND_SPEED_MAX,
                  dt, swDown, stdDevW1, windSpeed1,
                  windMeasurementHeight):
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

    # Coefficients for stability class adjustment for non-standard (not 10 m)
    #   wind measurement height (from EPA guidance).
    pTheta = {'A': 0.02, 'B': 0.04, 'C': 0.01, 'D': -0.14, 'E': -0.31}

    # Modify sigma-E values used for initial stability class determination by roughness factor.
    z0Correction = (z0/15.)**0.2
    for stability in stabilityClassesInitial.keys():
        stabilityClassesInitial[stability][0] *= z0Correction
        stabilityClassesInitial[stability][1] *= z0Correction

    if windMeasurementHeight != 10.0:
        heightCorrectionA = (windMeasurementHeight/10.0)**pTheta['A']
        heightCorrectionB = (windMeasurementHeight/10.0)**pTheta['B']
        heightCorrectionC = (windMeasurementHeight/10.0)**pTheta['C']
        heightCorrectionD = (windMeasurementHeight/10.0)**pTheta['D']
        heightCorrectionE = (windMeasurementHeight/10.0)**pTheta['E']
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
            break
    else:
        stabilityClassFinal = stabilityClassInitial
    #print('z0 WIND_SPEED_MAX,dt,swDown,stdDevW1,windSpeed1:', z0,WIND_SPEED_MAX,dt,swDown,stdDevW1,windSpeed1)
    #print(stabilityClassInitial, '->', stabilityClassFinal)
    return stabilityClassFinal

# ==============
# MAIN PROGRAM.
# ==============
# ----------
# Constants.
# ----------
FLAG = -999.9  # Possible value for data assumed to be bad. 
DEGRAD = math.pi / 180.0
RADDEG = 1.0 / DEGRAD
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
WIND_SPEED_MAX = 200.0  # Maximum wind speed that will be allowed. 
SHORTWAVE_DOWN_THRESH = 5.0  # If the downward shortwave irradiance (W/m2) is equal to or above this threshold,
                             #   it is assumed to be daytime.
#Z0 = 40.  # Assumed roughness length value for LANL, in cm, earlier PV-WAVE program. 
Z0 = 38.  # Assumed roughness length value for LANL, in cm, Bowen (1990)
WIND_MEASUREMENT_HEIGHT = 10.0  # Lowest measurement height assumed to be 10 m -- use "-windheight 11.5" for most LANL towers.
# Wind speed power law exponents for each stability class (from EPA guidance).
powerLawExponentRural = {'A': 0.07, 'B': 0.07, 'C': 0.10, 'D': 0.15, 'E': 0.35, 'F': 0.55}
# List of all possible variables.
ALL_VARIABLES = ['-dir1', '-dir2', '-dir3', '-dir4',
                 '-spd1', '-spd2', '-spd3', '-spd4',
                 '-sdw1', '-sdw2', '-sdw3', '-sdw4',
                 '-temp0', '-rh', '-dewp', '-precip', '-swdn', '-stability']

# ----------------------------------------------------------------
# Parse arguments.
# Get name of met file to read. There is one option:
#   1. A 15 min file downloaded from the Weather Machine.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a Weather Machine file and make a simple list of data")
parser.add_argument("metfile", help="Name of met file to read")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
parser.add_argument("-dir1", "--dir1", help="Average wind direction at level 1 (deg)",
                    action="store_true")
parser.add_argument("-dir2", "--dir2", help="Average wind direction at level 2 (deg)",
                    action="store_true")
parser.add_argument("-dir3", "--dir3", help="Average wind direction at level 3 (deg)",
                    action="store_true")
parser.add_argument("-dir4", "--dir4", help="Average wind direction at level 4 (deg)",
                    action="store_true")
parser.add_argument("-rose", "--rose", help="Output wind directions in text (e.g. NNW) instead of degrees",
                    action="store_true")
parser.add_argument("-spd1", "--spd1", help="Average wind speed at level 1 (m/s)",
                    action="store_true")
parser.add_argument("-spd2", "--spd2", help="Average wind speed at level 2 (m/s)",
                    action="store_true")
parser.add_argument("-spd3", "--spd3", help="Average wind speed at level 3 (m/s)",
                    action="store_true")
parser.add_argument("-spd4", "--spd4", help="Average wind speed at level 4 (m/s)",
                    action="store_true")
parser.add_argument("-mph", "--mph", help="Output wind speeds in miles per hour instead of meters per second",
                    action="store_true")
parser.add_argument("-temp0", "--temp0", help="Average temperature at lowest (C)",
                    action="store_true")
parser.add_argument("-F", "--F", help="Output temperatures in Fahrenheit instead of Celsius",
                    action="store_true")
parser.add_argument("-rh", "--rh", help="Average relative humidity at the first level (per cent)",
                    action="store_true")
parser.add_argument("-dewp", "--dewp", help="Average dew point temperature at the first level (C)",
                    action="store_true")
parser.add_argument("-precip", "--precip", help="15 min total precipitation (in)",
                    action="store_true")
parser.add_argument("-mm", "--mm", help="Output precipitation in millimeters instead of inches",
                    action="store_true")
parser.add_argument("-sdw1", "--sdw1", help="Average standard deviation of vertical wind speed at level 1 (m/s)",
                    action="store_true")
parser.add_argument("-sdw2", "--sdw2", help="Average standard deviation of vertical wind speed at level 2 (m/s)",
                    action="store_true")
parser.add_argument("-sdw3", "--sdw3", help="Average standard deviation of vertical wind speed at level 3 (m/s)",
                    action="store_true")
parser.add_argument("-sdw4", "--sdw4", help="Average standard deviation of vertical wind speed at level 4 (m/s)",
                    action="store_true")
parser.add_argument("-swdn", "--swdn", help="Average downward shortwave irradiance at the surface (W/m2)",
                    action="store_true")
parser.add_argument("-stability", "--stability", help="Pasquill-Gifford stability class",
                    action="store_true")
parser.add_argument("-z0", "--z0", help="Specified roughness length in cm for stability calculation, otherwise a default is used.")
parser.add_argument("-o", "--csvfile", help="Specified name of the CSV file that will be written, otherwise it will be tower2list.csv")
parser.add_argument("-hourly", "--hourly", help="Average data to hourly. Stability will be calculated from the averaged data.",
                    action="store_true")
parser.add_argument("-estimate10m", "--estimate10m", help="Use power law to adjust measured wind speeds to standard 10 m height.",
                    action="store_true")
parser.add_argument("-windheight", "--windheight", help="Wind measurement height (m), used for stability determination if it's not the 10 m default")
parser.add_argument("-sb", "--sb", help="Safety Basis mode; averaging is different, special output file",
                    action="store_true")

args = parser.parse_args()
metFile = args.metfile
if args.verbosity:
    verbosity = int(args.verbosity)
else:
    verbosity = 0

# Some options automatically set others.
if args.stability:
    args.spd1 = True
    args.sdw1 = True
    args.swdn = True
if args.sb:
    args.dir1 = True
    args.dir2 = True
    args.dir3 = True
    args.spd1 = True
    args.spd2 = True
    args.spd3 = True
    args.sdw1 = True
    args.sdw2 = True
    args.sdw3 = True
    args.hourly = True

# Build list of variables to process.
variables = []
if args.dir1:
    variables.append('dir1')
if args.dir2:
    variables.append('dir2')
if args.dir3:
    variables.append('dir3')
if args.dir4:
    variables.append('dir4')
if args.spd1:
    variables.append('spd1')
if args.spd2:
    variables.append('spd2')
if args.spd3:
    variables.append('spd3')
if args.spd4:
    variables.append('spd4')
if args.sdw1:
    variables.append('sdw1')
if args.sdw2:
    variables.append('sdw2')
if args.sdw3:
    variables.append('sdw3')
if args.sdw4:
    variables.append('sdw4')
if args.temp0:
    variables.append('temp0')
if args.rh:
    variables.append('rh')
if args.dewp:
    variables.append('dewp')
if args.swdn:
    variables.append('swdn')
if args.precip:
    variables.append('precip')

if len(variables) == 0:
    print('Must specify at least one variable from these options:\n', 
          *ALL_VARIABLES,
          '\nor use the Safety Basis Option (-sb)')
    sys.exit(1)

if args.z0:
    z0 = args.z0
else:
    z0 = Z0  # Use default roughness length value.
if args.csvfile:
    csvFile = args.o
else:
    csvFile = 'tower2list.csv'  # Default csv file name.
if args.windheight:
    windMeasurementHeight = float(args.windheight)
    print('\nNon-standard wind measurement height (not', WIND_MEASUREMENT_HEIGHT, 'm)',
          'used to adjust stability category determination:', 
          windMeasurementHeight, 'm')
else:
    windMeasurementHeight = WIND_MEASUREMENT_HEIGHT # Use default.
    print('\nWind measurement height assumed to be', WIND_MEASUREMENT_HEIGHT, 'm,',
          'so no adjustment of stability categories.')

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
columnDateTime1 = 'Date/Time' # Data request from old yellow Weather Machine.
columnDateTime2 = 'dts'       # Data request from current Weather Machine.
columnName = {}
columnName['dir1'] = 'dir1'
columnName['dir2'] = 'dir2'
columnName['dir3'] = 'dir3'
columnName['dir4'] = 'dir4'
columnName['spd1'] = 'spd1'
columnName['spd2'] = 'spd2'
columnName['spd3'] = 'spd3'
columnName['spd4'] = 'spd4'
columnName['sdw1'] = 'sdw1'
columnName['sdw2'] = 'sdw2'
columnName['sdw3'] = 'sdw3'
columnName['sdw4'] = 'sdw4'
columnName['temp0'] = 'temp0'
columnName['rh'] = 'rh'
columnName['dewp'] = 'dewp'
columnName['precip'] = 'precip'
columnName['swdn'] = 'swdn'

# =======
# Banner.
# =======
print('\n =====================================================\n',
      'Make a simple list of observed data\n',
      '=====================================================\n')
print(*sys.argv)

# Initialize lists for all variables.
dtIn = []
dtOut = []
obsIn = {}
obsOut = {}
for var in variables:
    obsIn[var] = []
    obsOut[var] = []

# --------------------------------------------------------------------
# Read LANL 15-minute data at one tower location.
#   Save each of the requested variables.
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
        try:
            row[columnDateTime1]
            columnDateTime = columnDateTime1
        except KeyError:
            columnDateTime = columnDateTime2
        if (row[columnDateTime] and
            (re.search(r'^\d+-\d+-\d+ \d+:\d+:\d+', row[columnDateTime]) or
             re.search(r'^\d+-\d+-\d+ \d+:\d+', row[columnDateTime]))):
            #print('row[0]:', row[columnDateTime]) #ktw
            try:
                # Try an old yellow Weather Machine-formatted date.
                dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M:%S")
            except:
                try:
                    # Try a datalogger-formatted date.
                    dt = datetime.strptime(row[columnDateTime], "%m/%d/%Y %H:%M")
                except:
                    # Try a new Weather Machine-formatted date.
                    dt = datetime.strptime(row[columnDateTime], "%Y-%m-%d %H:%M")
            # Save first time.
            if dtFirst is None:
                dtFirst = dt
            # ----------------------------------------------------------
            # Save requested variables, keep asterisks for missing data.
            # ----------------------------------------------------------
            dtIn.append(dt)
            for var in variables:
                try:
                    obsIn[var].append(float(row[columnName[var]]))
                except ValueError:
                    obsIn[var].append('*')
            # Save the last time.
            dtLast = dt

# --------------------------------------------
# Make list of all possible 15 min times.
#   Also collect hourly times in this dataset.
# --------------------------------------------
print('\nBuild list of all possible 15 min and hourly times:')
dt15All = []
dtHourAll = []
if (dtFirst is not None and
    dtLast is not None):
    dt = dtFirst
    while dt <= dtLast:
        dt15All.append(dt)
        mm = datetime.strftime(dt, '%M')
        if mm == '00':
            dtHourAll.append(dt)
        # Go to next time.
        dt = dt + timedelta(minutes=15)
else:
    print('Starting and ending times not found in data!')
    sys.exit(1)

if args.hourly:
    # -----------------------
    # Average data to hourly.
    # -----------------------
    print('\nCalculate hourly averages from 15 min times:')
    obsHour = {}
    oneHour = timedelta(hours=1)
    thirtyMinutes = timedelta(minutes=30)
    for var in variables:
        obsHour[var] = []
    # Calculate averages for each hour covered by the input data.
    for i, dtHour in enumerate(dtHourAll):
        if verbosity >= 1:
            print('   ', dtHour)
        hhHour = datetime.strftime(dtHour, '%H')
        # Calculate averages for each requested variable.
        for var in variables:
            uAvg = []
            vAvg = []
            obsAvg = []
            #print('var:', var) #ktw
            # Go through all 15 min data to find relevant times.
            for j, dt15 in enumerate(dtIn):
                #print('dt15:', dt15) #ktw
                hh15 = datetime.strftime(dt15, '%H')
                diffHour = dt15 - dtHour
                if diffHour > oneHour:
                    #print('break,dtHour,dt15,diffHour', dtHour,dt15,diffHour) #ktw
                    break  # Jump to next variable when comfortably past the needed data.
                if ((args.sb and 
                     abs(diffHour) <= 2*thirtyMinutes and 
                     hh15==hhHour) or  # For Safety Basis, average 00, 15, 30, 45 min times.
                    (not args.sb and 
                     abs(diffHour) <= thirtyMinutes)):  # Otherwise, average times from 
                                                        #   30 min before to 30 min after.
                    # Collect relevant 15 min values.
                    if var[0:3] == 'dir':
                        # Special averaging for wind direction.
                        wdir = var
                        wspd = 'spd' + var[3:4]
                        if args.sb:
                            # Use Safety Basis unit vector method of averaging sines and cosines.
                            if obsIn[wdir][j] != '*':  # Skip flagged values in calculating averages.
                                u = math.sin(DEGRAD*obsIn[wdir][j])
                                v = math.cos(DEGRAD*obsIn[wdir][j])
                                uAvg.append(u)
                                vAvg.append(v)
                        else:
                            # Average u and v, and the average wind direction is weighted by wind speeds.
                            if obsIn[wdir][j] != '*':  # Skip flagged values in calculating averages.
                                u = -obsIn[wspd][j] * math.sin(DEGRAD*obsIn[wdir][j])
                                v = -obsIn[wspd][j] * math.cos(DEGRAD*obsIn[wdir][j])
                                uAvg.append(u)
                                vAvg.append(v)
                        # Build list of wind direction components to average.
                    elif (args.sb and var[0:3] == 'sdw'):
                        # Build list for special averaging of squares to calculate sigmaE.
                        if obsIn[var][j] != '*':  # Skip flagged values in calculating averages.
                            obsAvg.append(obsIn[var][j]*obsIn[var][j])
                    else:
                        # Build list for simple averaging for all other variables.
                        if obsIn[var][j] != '*':  # Skip flagged values in calculating averages.
                            obsAvg.append(obsIn[var][j])
            # End of 15 min loop, calculate hourly averages from 15 min data.
            if var[0:3] == 'dir':
                # Special averaging for wind direction.
                if (len(uAvg) >= 1 and
                    len(vAvg) >= 1):
                    uHour = statistics.mean(uAvg)  # Either u/v or sines/cosines.
                    vHour = statistics.mean(vAvg)
                    dirHour = RADDEG*math.atan2(uHour, vHour)
                else:
                    dirHour = '*'
                if args.sb:
                    # Safety Basis method gives wdir from -180 to +180 deg.
                    if dirHour != '*':
                        if dirHour < -180.0:  
                            dirHour = -180.0
                        elif dirHour > 180.0:
                            dirHour = 180.0
                else:
                    # Regular wind direction from 0 to 360 deg.
                    if dirHour < 0.0:
                        dirHour = 0.0
                    if dirHour > 360.0:
                        dirHour = 0.0
                obsHour[wdir].append(dirHour)
            elif (args.sb and var[0:3] == 'sdw'):
                # Special calculation for Safety Basis.
                #   Calculate average of sdw squares, take square root, 
                #   divide by average speed and convert to degrees.
                wspd = 'spd' + var[3:4]
                if len(obsAvg) >= 1:
                    squaresAvg = statistics.mean(obsAvg)
                    sqrtAvg = math.sqrt(squaresAvg)
                    spd = obsHour[wspd][-1]  # Hourly average speed from earlier in the variables loop.
                    if (spd != '*' and spd > 0.0):
                        obsHour[var].append(RADDEG*(sqrtAvg/spd))
                    else:
                        obsHour[var].append('*')
                else:
                    obsHour[var].append('*')
            else:
                # Simple averaging for all other variables.
                if len(obsAvg) >= 1:
                    obsHour[var].append(statistics.mean(obsAvg))
                else:
                    obsHour[var].append('*')
                #print('var,dtHour,obsAvg,obsHour[var]:', var,dtHour,obsAvg,obsHour[var]) #ktw
            # Finished averaging for this variable and time, reset lists and go to next one.
        # End of variable loop, go to next dtHour.
    # End of dtHour loop, replace 15 min array of data with final hourly averages for output.
    dtOut = dtHourAll
    for var in variables:
        obsOut[var] = obsHour[var]
else:
    # -------------------------
    # Output 15 minute data.
    # -------------------------
    dtOut = dtIn
    for var in variables:
        obsOut[var] = obsIn[var]

# ----------------------------------------
# Additional calculations and conversions.
# ----------------------------------------
if args.stability:
    # --------------------------
    # Calculate stability class.
    # --------------------------
    obsOut['stability'] = []
    for i, dt in enumerate(dtOut):
        if (obsOut['swdn'][i] != '*' and
            obsOut['sdw1'][i] != '*' and
            obsOut['spd1'][i] != '*'):
            stabilityClassFinal = calcStability(z0, WIND_SPEED_MAX,
                                                dt, obsOut['swdn'][i], obsOut['sdw1'][i], obsOut['spd1'][i],
                                                windMeasurementHeight)
            if stabilityClassFinal is not None:
                obsOut['stability'].append(stabilityClassFinal)
            else:
                obsOut['stability'].append('*')
        else:
            obsOut['stability'].append('*')

if args.dir1 and args.rose:
    # ------------------------------------------------
    # Convert wind direction from degrees to secondary
    #   intercardinal directions.
    # ------------------------------------------------
    for i in range(len(dtIn)):
        if obsOut['dir1'][i] != '*':
            for bin in windDirBins.keys():
                if (obsOut['dir1'][i] >= windDirBins[bin][0] and
                    obsOut['dir1'][i] < windDirBins[bin][1]):
                    if (bin == 'N1' or
                        bin == 'N2'):
                        obsOut['dir1'][i] = 'N'
                    else:
                        obsOut['dir1'][i] = bin
                    break
        else:
            obsOut['dir1'][i] = str('*')

if (args.spd1 and windMeasurementHeight != 10.0 and args.estimate10m):
    # ----------------------------------------------------------------
    # Estimate the wind speed at 10 m with the wind profile power law.
    #   Use rural power law exponents from the EPA guidance.
    # ----------------------------------------------------------------
    for i in range(len(dtIn)):
        if obsOut['spd1'][i] != '*':
            stabilityClassFinal = obsOut['stability'][i]
            if stabilityClassFinal is not None:
                obsOut['spd1'][i] = obsOut['spd1'][i] * (10.0/windMeasurementHeight)**\
                                    powerLawExponentRural[stabilityClassFinal]
            else:
                obsOut['spd1'][i].append('*')  #ktw: Should we just keep the original wind speed?

if args.spd1 and args.mph:
    # -----------------------------------
    # Convert wind speed from m/s to mph.
    # -----------------------------------
    for i in range(len(dtIn)):
        if obsOut['spd1'][i] != '*':
            obsOut['spd1'][i] *= 2.237

if args.temp0 and args.F:
    # --------------------------------
    # Convert temperature from C to F.
    # --------------------------------
    for i in range(len(dtIn)):
        if obsOut['temp0'][i] != '*':
            obsOut['temp0'][i] = (9.0/5.0)*obsOut['temp0'][i] + 32.0

if args.dewp and args.F:
    # ------------------------------------------
    # Convert dew point temperature from C to F.
    # ------------------------------------------
    for i in range(len(dtIn)):
        if obsOut['dewp'][i] != '*':
            obsOut['dewp'][i] = (9.0/5.0)*obsOut['dewp'][i] + 32.0

if args.precip and args.mm:
    # ------------------------------------------
    # Convert precip from inches to millimeters.
    # ------------------------------------------
    for i in range(len(dtIn)):
        if obsOut['precip'][i] != '*':
            obsOut['precip'][i] *= 25.4

# -----------------------------------------
# Print a simple list of the data.
# Not sure the printed list is worth keeping. 
# -----------------------------------------
# print('\nSimple list of observations:')
header = ''
header += '\nDateTime       '
if args.dir1:
    header += '  {:>9s}'.format('dir1')
if args.dir2:
    header += '  {:>9s}'.format('dir2')
if args.dir3:
    header += '  {:>9s}'.format('dir3')
if args.dir4:
    header += '  {:>9s}'.format('dir4')
if args.spd1 and args.mph:
    header += '  {:>9s}'.format('spd1(mph)')
elif args.spd1:
    header += '  {:>9s}'.format('spd1(m/s)')
if args.spd2 and args.mph:
    header += '  {:>9s}'.format('spd2(mph)')
elif args.spd2:
    header += '  {:>9s}'.format('spd2(m/s)')
if args.spd3 and args.mph:
    header += '  {:>9s}'.format('spd3(mph)')
elif args.spd3:
    header += '  {:>9s}'.format('spd3(m/s)')
if args.spd4 and args.mph:
    header += '  {:>9s}'.format('spd4(mph)')
elif args.spd4:
    header += '  {:>9s}'.format('spd4(m/s)')
if args.temp0 and args.F:
    header += '  {:>9s}'.format('temp0(F)')
elif args.temp0:
    header += '  {:>9s}'.format('temp0(C)')
if args.rh:
    header += '  {:>9s}'.format('rh(%)')
if args.dewp and args.F:
    header += '  {:>9s}'.format('dewp(F)')
elif args.dewp:
    header += '  {:>9s}'.format('dewp(C)')
if args.precip and args.mm:
    header += '  {:>9s}'.format('precip(mm)')
elif args.precip:
    header += '  {:>9s}'.format('precip(in)')
if args.swdn:
    header += '  {:>9s}'.format('swdn(W/m2)')
if args.sdw1:
    header += '  {:>9s}'.format('sdw1(m/s)')
if args.sdw2:
    header += '  {:>9s}'.format('sdw2(m/s)')
if args.sdw3:
    header += '  {:>9s}'.format('sdw3(m/s)')
if args.sdw4:
    header += '  {:>9s}'.format('sdw4(m/s)')
if args.stability:
    header += '  {:>9s}'.format('stabilityClass')
# print(header)
# for i, dt in enumerate(dtOut):
#     line = ''
#     line += '{:s}'.format(datetime.strftime(dt, '%Y-%m-%d %H:%M'))
#     if args.dir1 and args.rose:
#         line += '  {:>9s}'.format(obsOut['dir1'][i])
#     elif args.dir1:
#         line += '  {:9.1f}'.format(obsOut['dir1'][i])
#     if args.dir2 and args.rose:
#         line += '  {:>9s}'.format(obsOut['dir2'][i])
#     elif args.dir2:
#         line += '  {:9.1f}'.format(obsOut['dir2'][i])
#     if args.dir3 and args.rose:
#         line += '  {:>9s}'.format(obsOut['dir3'][i])
#     elif args.dir3:
#         line += '  {:9.1f}'.format(obsOut['dir3'][i])
#     if args.dir4 and args.rose:
#         line += '  {:>9s}'.format(obsOut['dir4'][i])
#     elif args.dir4:
#         line += '  {:9.1f}'.format(obsOut['dir4'][i])
#     if args.spd1:
#         line += '  {:9.1f}'.format(obsOut['spd1'][i])
#     if args.spd2:
#         line += '  {:9.1f}'.format(obsOut['spd2'][i])
#     if args.spd3:
#         line += '  {:9.1f}'.format(obsOut['spd3'][i])
#     if args.spd4:
#         line += '  {:9.1f}'.format(obsOut['spd4'][i])
#     if args.temp0:
#         line += '  {:9.1f}'.format(obsOut['temp0'][i])
#     if args.rh:
#         line += '  {:9.1f}'.format(obsOut['rh'][i])
#     if args.dewp:
#         line += '  {:9.1f}'.format(obsOut['dewp'][i])
#     if args.precip:
#         line += '  {:9.1f}'.format(obsOut['precip'][i])
#     if args.swdn:
#         line += '  {:9.1f}'.format(obsOut['swdn'][i])
#     if args.sdw1:
#         line += '  {:9.3f}'.format(obsOut['sdw1'][i])
#     if args.sdw2:
#         line += '  {:9.3f}'.format(obsOut['sdw2'][i])
#     if args.sdw3:
#         line += '  {:9.3f}'.format(obsOut['sdw3'][i])
#     if args.sdw4:
#         line += '  {:9.3f}'.format(obsOut['sdw4'][i])
#     if args.stability:
#         line += '  {:9s}'.format(obsOut['stability'][i])
#     print(line)

# ------------------------------------
# Also write the output to a CSV file.
# ------------------------------------
print('\nWriting to CSV file:', csvFile)
with open(csvFile, 'w') as csvOut:
    csvOut.write(','.join(header.split()) + '\n')
    for i, dateTime in enumerate(dtOut):
        line = '{:s},'.format(datetime.strftime(dateTime, '%Y-%m-%d %H:%M'))
        if args.dir1:
            line += '{:s},'.format(str(obsOut['dir1'][i]))
        if args.dir2:
            line += '{:s},'.format(str(obsOut['dir2'][i]))
        if args.dir3:
            line += '{:s},'.format(str(obsOut['dir3'][i]))
        if args.dir4:
            line += '{:s},'.format(str(obsOut['dir3'][i]))
        if args.spd1:
            line += '{:s},'.format(str(obsOut['spd1'][i]))
        if args.spd2:
            line += '{:s},'.format(str(obsOut['spd2'][i]))
        if args.spd3:
            line += '{:s},'.format(str(obsOut['spd3'][i]))
        if args.spd4:
            line += '{:s},'.format(str(obsOut['spd4'][i]))
        if args.temp0:
            line += '{:s},'.format(str(obsOut['temp0'][i]))
        if args.rh:
            line += '{:s},'.format(str(obsOut['rh'][i]))
        if args.dewp:
            line += '{:s},'.format(str(obsOut['dewp'][i]))
        if args.precip:
            line += '{:s},'.format(str(obsOut['precip'][i]))
        if args.swdn:
            line += '{:s},'.format(str(obsOut['swdn'][i]))
        if args.sdw1:
            line += '{:s},'.format(str(obsOut['sdw1'][i]))
        if args.sdw2:
            line += '{:s},'.format(str(obsOut['sdw2'][i]))
        if args.sdw3:
            line += '{:s},'.format(str(obsOut['sdw3'][i]))
        if args.sdw4:
            line += '{:s},'.format(str(obsOut['sdw4'][i]))
        if args.stability:
            line += '{:s},'.format(obsOut['stability'][i])
        csvOut.write('{:s}\n'.format(line))

# ----------------------------------------------------------------------------------------
# For Safety Basis, write a separate CSV file with the variables and units that they need
#   for an annual dataset.
# ----------------------------------------------------------------------------------------
if args.sb:
    csvFile = 'safety-basis.csv'
    print('\nWriting to CSV file:', csvFile)
    with open(csvFile, 'w') as csvOut:
        csvOut.write('hour, wspd1, wspd2, wspd3, wdir1, wdir2, wdir3, sigmae1, sigmae2, sigmae3\n')
        hour = 0  # Safety Basis wants hour count through an entire year, 8760 hours.
        for i, dateTime in enumerate(dtOut):
            hour+= 1
            if hour > 8760:  # Omit last day of a leap year.
                break
            line = '{:d},'.format(hour)
            line += '{:s},'.format(str(obsOut['spd1'][i]))
            line += '{:s},'.format(str(obsOut['spd2'][i]))
            line += '{:s},'.format(str(obsOut['spd3'][i]))
            line += '{:s},'.format(str(obsOut['dir1'][i]))
            line += '{:s},'.format(str(obsOut['dir2'][i]))
            line += '{:s},'.format(str(obsOut['dir3'][i]))
            line += '{:s},'.format(str(obsOut['sdw1'][i]))
            line += '{:s},'.format(str(obsOut['sdw2'][i]))
            line += '{:s},'.format(str(obsOut['sdw3'][i]))
            csvOut.write('{:s}\n'.format(line))
    
# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
