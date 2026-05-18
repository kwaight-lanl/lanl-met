#!/usr/bin/env python3

"""
tower2sunshine.py
Read a 15-min csv file for one tower site, calculate the hours of sunshine and % sunshine for each year.
Method from the paper:
Hinssen, Y.B.L. and W.H. Knap, 2007:  Comparison of pyranometric and pyrheliometric methods for the 
  determination of sunshine duration. J. Atmos. Ocean. Tech., 24, 835-846.
Usage: python tower2sunshine.py [-v] metfile latitude longitude 
  metfile is the name of the met file to read, assumed to be in the format downloaded from the Weather Machine.
  Latitude and longitude in degrees.
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

# ==============
# FUNCTIONS.
# ==============
def calc_solar_params(verbosity, latitude, longitude, dtUtc):
    """
    Calculate the solar declination angle, hour angle and
      zenith angle for a given location, date and time.
    Ken Waight / February 2017

    Equation of time (minutes), corrects for eccentricity of 
      earth's orbit and earth's axial, and declination
      angle. From Williams via Wikipedia: 
      http://www.green-life-innovators.org/tiki-index.php?page=
        The+Latitude+and+Longitude+of+the+Sun+by+David+Williams
    """
    dayofyear = float(dtUtc.strftime('%j'))
    w         = 360. / 365.24
    a         = w * ((dayofyear-1.)+10.)
    b         = a + (360./math.pi)*.0167*math.sin(DEG_RAD*w*
                                                  ((dayofyear-1.)-2.))
    c         = ((a-RAD_DEG*math.atan(math.tan(DEG_RAD*b) / 
                                      math.cos(DEG_RAD*23.44)))/180.)
    eot       = 720. * (c-round(c))
    solarDeclination = (RAD_DEG *
                             -math.asin(math.sin(DEG_RAD*23.44)*
                                        math.cos(DEG_RAD*b)))

    # Calculate local solar time and hour angle.
    #   http://www.pveducation.org/properties-of-sunlight/solar-time
    # Local standard time meridian.
    lstm   = 15. * (round(longitude/15.))

    # Time correction factor, accounts for variation of solar time
    #   within a time zone and also the equation of time above.
    tc     = 4.*(longitude-lstm) + eot

    # Local solar time.
    hr = float(dtUtc.strftime('%H'))
    mn = float(dtUtc.strftime('%M'))
    sec = float(dtUtc.strftime('%S'))
    hrfrac_utc = hr + mn/60.0 + sec/3600.0
    soltim     = hrfrac_utc + lstm/15. + tc/60.
    if soltim < 0.:
        soltim += 24.
    elif soltim > 24.:
        soltim -= 24.

    # Hour angle.
    solarHour = 15.*(soltim-12.)

    # Calculate the zenith angle.
    cosZenith = (math.sin(DEG_RAD*latitude)*
                      math.sin(DEG_RAD*solarDeclination) + 
                      math.cos(DEG_RAD*latitude)*
                      math.cos(DEG_RAD*solarDeclination)*
                      math.cos(DEG_RAD*solarHour))
    cosZenith = max (cosZenith,-1.)
    cosZenith = min (cosZenith, 1.)

    # Zenith angle.
    solarZenith = RAD_DEG * math.acos(cosZenith)

    # Elevation angle.
    solarElevation = 90.0 - solarZenith

    # Print solar info.
    if verbosity > 0:
        hr = dtUtc.strftime('%H')
        mn = dtUtc.strftime('%M')
        yyyy = dtUtc.strftime('%Y')
        mm = dtUtc.strftime('%m')
        dd = dtUtc.strftime('%d')
        print("\n Solar parameters")
        print(" --------------------------------------------------")
        print(" Latitude                      : {:.4f} deg".format(latitude))
        print(" Longitude                     : {:.4f} deg".format(longitude))
        print(" Time                          : {0:2s}:{1:2s} UTC".format(hr, mn))
        print(" Date                          : {0:4s} {1:2s} {2:2s}".format(yyyy, mm, dd))
        print(" Day of year                   : {:.1f}".format(dayofyear))
        print(" Terrain height                : {:.1f} m".format(self.elevation))
        print(" --------------------------------------------------")
        print(" Declination                   : {:.2f} deg".format(solarDeclination))
        print(" Local std. time meridian      : {:.2f} deg".format(lstm))
        print(" Eq. of time                   : {:.2f} min".format(eot))
        print(" Local solar time              : {:.2f}".format(soltim))
        print(" Hour angle                    : {:.2f} deg".format(solarHour))
        print(" Zenith angle                  : {:.2f} deg".format(solarZenith))
        print(" Cosine zenith                 : {:.4f}".format(cosZenith))
        print(" Elevation angle               : {:.2f} deg".format(solarElevation))
        print(" Daytime?                      : {:}".format(daytime))

    # Return results.
    return dayofyear, cosZenith
        

# ==============
# MAIN PROGRAM.
# ==============
# ----------
# Constants.
# ----------
FLAG = -999.9  # Value for data assumed to be bad. 
D_HOURS_MST = 7.0  # Difference between Mountain Standard Time and UTC.
DEG_RAD = math.pi / 180.0
RAD_DEG = 180.0 / math.pi
I0 = 1376.0  # Solar irradiance at top of the atmosphere, W/m2.
HOURS_PERIOD = 0.25  # Always using 15-min data.
LOWER1 = 0.4  # Constants from Hinnsen and Knap.
UPPER1 = 0.5
LOWER2 = 0.4
UPPER2 = 0.5

# ----------------------------------------------------------------
# Parse arguments.
# Get name of met file to read. There is one option:
#   1. A 15 min file downloaded from the Weather Machine.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a Weather Machine file and calculate sunshine duration")
parser.add_argument("metfile", help="Name of met file to read")
parser.add_argument("latitude", help="Latitude of this location (deg).")
parser.add_argument("longitude", help="Longitude of this location (deg).")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
args = parser.parse_args()
metFile = args.metfile
latitude = float(args.latitude)
longitude = float(args.longitude)
if args.verbosity:
    verbosity = int(args.verbosity)
else:
    verbosity = 0

# ---------------------------------------
# Input and output data file information.
# ---------------------------------------
columnName = {}
columnName['DateTime'] = 'Date/Time'
columnName['swdn'] = 'swdn'

# =======
# Banner.
# =======
print('\n =====================================================\n',
      'Calculate sunshine duration\n',
      '=====================================================\n')
print(*sys.argv)

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
sunshineHours = {}
sunshineHoursMax = {}
with open(metFile, 'r') as infile:
    towerData = csv.DictReader(infile)
    for row in towerData:
        if (row[columnName['DateTime']] and
            (re.search(r'^\d+-\d+-\d+ \d+:\d+:\d+', row[columnName['DateTime']]) or
             re.search(r'^\d+/\d+/\d+ \d+:\d+', row[columnName['DateTime']]))):
            # This should be a data line (ignore header lines).
            #print('row[0]:', row[columnName['DateTime']]) #ktw
            try:
                # Try the default Weather Machine formatted date.
                dt = datetime.strptime(row[columnName['DateTime']], "%Y-%m-%d %H:%M:%S")
            except:
                # Try a datalogger formatted date.
                dt = datetime.strptime(row[columnName['DateTime']], "%m/%d/%Y %H:%M")
            # Save first time.
            if dtFirst is None:
                dtFirst = dt
            # ---------------------------------------------------------
            # Save data, convert * to a flag value.
            # ---------------------------------------------------------
            dtList.append(dt)
            yyyy = datetime.strftime(dt, '%Y')
            sunshineHours[yyyy] = sunshineHours.get(yyyy, 0.0)
            sunshineHoursMax[yyyy] = sunshineHoursMax.get(yyyy, 0.0)
            try:
                swdn = float(row[columnName['swdn']])
            except ValueError:
                swdn = None
            if swdn is not None:
                # Good data found, calculate sunshine minutes for this 15-min period.
                dtUtc = dt + timedelta(hours=D_HOURS_MST)
                dayOfYear, cosZenith = calc_solar_params(
                    verbosity, latitude, longitude, dtUtc)
                # Simplified form of equation for solar radiation at top of atmosphere,
                #   which accounts for varying earth-sun distance.
                G0 = I0 * (1.0 + 0.34*math.cos(2.0*math.pi*(float(dayOfYear)/365.25))) * cosZenith
                if cosZenith > 0:
                    # Daytime. Use correlation algorithm from Hinssen and Knap paper. 
                    # f is fraction of sunshine in the 15 min period.
                    GG0 = swdn / G0
                    if cosZenith < 0.3:
                        if GG0 < LOWER1:
                            f = 0.0
                        elif GG0 >= UPPER1:
                            f = 1.0
                        else:
                            f = (GG0-LOWER1) / (UPPER1-LOWER1)
                    else:
                        if GG0 < LOWER2:
                            f = 0.0
                        elif GG0 >= UPPER2:
                            f = 1.0
                        else:
                            f = (GG0-LOWER2) / (UPPER2-LOWER2)
                    # Accumulate hours of sunshine for this period,
                    #   and maximum hours of sunshine.
                    sunshineHours[yyyy] += f * HOURS_PERIOD
                    sunshineHoursMax[yyyy] += HOURS_PERIOD
            # Save the last time.
            dtLast = dt

# ---------------------------------------------------------------
# List the number of sunshine hours and % sunshine for each year.
# ---------------------------------------------------------------
nYears = 0
totalHours = 0.0
totalHoursMax = 0.0
print('\nyyyy hours   %sun',
      '\n----  ----  -----')
for yyyy in sunshineHours.keys():
    percentSunshine = 100.0 * (sunshineHours[yyyy]/sunshineHoursMax[yyyy])
    print('{:4s}  {:4.0f}  {:5.1f}%'.format(yyyy, round(sunshineHours[yyyy]), percentSunshine))
    nYears += 1
    totalHours += sunshineHours[yyyy]
    totalHoursMax += sunshineHoursMax[yyyy]
totalPercent = 100.0 * (totalHours/totalHoursMax)
totalHoursAvg = totalHours / float(nYears)
print('----  ----  -----')
print('      {:4.0f}  {:5.1f}%'.format(round(totalHoursAvg), totalPercent))

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
