"""
getHrrr.py
Download a set of grib2 files.
python3 getHrrr [yyyymmddhh]
Ken Waight / April 2026
"""

import sys
import subprocess
import argparse
from datetime import datetime, timedelta
import glob

# ==========
# Constants.
# ==========
HH_INIT_DEFAULT = '12' # Default model initial hour.

# ----------------
# Parse arguments.
# ----------------
parser = argparse.ArgumentParser(description="Download a set of grib2 files for one day and time.")
parser.add_argument("-yyyymmddhh", "--yyyymmddhh", required=False,
                    help="UTC date and hour of gridded data to process")
args = parser.parse_args()
if args.yyyymmddhh:
    yyyymmddhh = args.yyyymmddhh
else:
    # Default to today's date at the hour in HH_INIT_DEFAULT.
    dtNow = datetime.now()
    yyyymmdd = datetime.strftime(dtNow, '%Y%m%d')
    yyyymmddhh = yyyymmdd + HH_INIT_DEFAULT

# ---------------------------------------------
# Resolve date/time and download 24 hr of data.
# ---------------------------------------------
year = int(yyyymmddhh[0:4])
month = int(yyyymmddhh[4:6])
day = int(yyyymmddhh[6:8])
hourInit = int(yyyymmddhh[8:10])
yyyy = '{:4d}'.format(year)
mm = '{:2d}'.format(month)
dd = '{:2d}'.format(day)
hhInit = '{:2d}'.format(hourInit)

# ----------------------------------------------------------------------
# First remove any previous grib files for the same hour, since the date
#   is not in the filenames.
# ----------------------------------------------------------------------
pattern = 'hrrr.t' + hhInit + '*' + '.grib2'
print('pattern:', pattern)
filesToDelete = glob.glob(pattern)
nFilesToDelete = len(filesToDelete)
print('filesToDelete:', filesToDelete, 'nFilesToDelete:', nFilesToDelete)
if nFilesToDelete > 0:
    commandString = 'rm ' + pattern
    print('commandString:', commandString)
    output = subprocess.check_output(commandString, stderr=subprocess.STDOUT, shell=True)

# ----------------------------------------------------------------------
# Download grib files.
# ----------------------------------------------------------------------
print('\nFetching gridded data:')
for hourFcst in range(0, 25):
    print('   ', hourFcst)
    hhFcst = '{:2d}'.format(hourFcst)
    mm = mm.replace(' ', '0')
    dd = dd.replace(' ', '0')
    hhFcst = hhFcst.replace(' ', '0')
    url = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl?dir=%2Fhrrr.' + yyyy + mm + dd + '%2Fconus&file=hrrr.t' + hhInit + 'z.wrfsfcf' + hhFcst + '.grib2&all_var=on&all_lev=on&subregion=&toplat=38&leftlon=-108&rightlon=-105&bottomlat=35'
    print('url:', url)

    outfile = 'hrrr.t' + hhInit + 'z.wrfsfcf' + hhFcst + '.grib2'
    commandString = 'curl ' + '\'' + url + '\'' +  ' -o ' + outfile
    output = subprocess.check_output(commandString, stderr=subprocess.STDOUT, shell=True)


