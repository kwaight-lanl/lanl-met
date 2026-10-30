"""
grib2series.py
Read a set of grib2 files, extract time series for a set of points and
  write to CSV files.
Ken Waight / April 2026
"""

import metview as mv
import glob
import csv
import math
from datetime import datetime

def uv2WdirWspd(u, v):
    """
    Convert u- and v-components of wind to wind direction and wind speed.
    Adapted from an old Perl subroutine.
    Ken Waight / October 2020
    """
    rad = math.pi / 180.
    # Calculate speed. 
    wspd = math.sqrt(u*u + v*v)
    # Calculate direction. 
    if u == 0.:
        if v == 0.0:
            dirrad = 0.
        elif v > 0.0:
            dirrad = 3.14159
        elif v <0.0:
            dirrad = 6.28318
    else:
        ang = v / u
        ang = math.atan2(ang, 1)
        if (v >= 0.0 and u > 0.0):
            dirrad = 4.712385 - ang
        elif (v >= 0.0 and u < 0.0):
            dirrad = 1.570795 - ang
        elif (v <= 0.0 and u > 0.0):
            dirrad = -ang + 4.712385
        elif (v <= 0.0 and u < 0.0):
            dirrad = -ang + 1.570795
    # Convert direction to degrees. 
    wdir = dirrad / rad
    # Return direction and speed.
    return (wdir, wspd)

# Sites.
sites = ['ta6', 'ta49', 'ta53', 'ta54', 'ta5',
         'ta16b', 'ta54b', 'ta63', 'ta68']
# Coordinates of points for extraction.
coords = {'ta6'  : [35.8615, -106.3195],
          'ta49' : [35.8133, -106.2993],
          'ta53' : [35.8701, -106.2543],
          'ta54' : [35.8259, -106.2232],
          'ta5'  : [35.8597, -106.2522],
          'ta16b': [35.8433, -106.3503],
          'ta54b': [35.8464, -106.2662],
          'ta63' : [35.8603, -106.2960],
          'ta68' : [35.8150, -106.2569],
          }

u10point = {}
v10point = {}
wspd = {}
wdir = {}
hrMst = {}

# Options.
uvOrWspdWdir = 'wspdWdir'
#scenario = 'thunderstorm'
#scenario = 'spring'
#scenario = 'drainage'
scenario = 'series'

# -----------------------
# Go through sites:
# -----------------------
print('\nGo through sites:')
for site in sites:
    print('   ', site)
    u10point[site] = {}
    v10point[site] = {}
    wspd[site] = {}
    wdir[site] = {}
    # ---------------------------
    # Open CSV file.
    # ---------------------------
    csvFile = scenario + '-' + site + '.csv'
    with open(csvFile, 'w') as csvOut:
        if uvOrWspdWdir == 'uv':
            csvOut.write('n,time,u(m/s),v(m/s)\n')
        else:
            csvOut.write('n,timeUtc,hrMst,HRRR dir1,obs dir1,HRRR spd1(m/s),obs spd1\n')
        # -----------------------
        # Go through grib2 files.
        # -----------------------
        gribfiles = sorted(glob.glob('*.grib2'))
        #print('gribfiles:', gribfiles)
        n = 0
        hrMstInit = None
        ntimes = len(gribfiles)
        for gribfile in gribfiles:
            n += 1
            # ----------------
            # Extract u and v.
            # ----------------
            gribdata = mv.read(gribfile)
            u10 = gribdata['10u']
            v10 = gribdata['10v']
            u10point[site][n] = u10.nearest_gridpoint(coords[site])
            v10point[site][n] = v10.nearest_gridpoint(coords[site])
            if uvOrWspdWdir == 'wspdWdir':
                # -------------------------
                # Convert u/v to wspd/wdir.
                # -------------------------
                (wdir[site][n], wspd[site][n]) = uv2WdirWspd(u10point[site][n], v10point[site][n])
            # -----------------------------------------
            # Save UTC datetime and calculate MST hour.
            # -----------------------------------------
            validDate = mv.valid_date(u10)
            #print('validDate:', validDate)
            timeUtcOut = datetime.strftime(validDate,'%H%M UTC %Y%m%d')
            hrUtc = float(datetime.strftime(validDate,'%H'))
            if not hrMstInit:
                hrMstInit = hrUtc - 7.0
            if hrMstInit < 0:
                hrMstInit += 24.0
            hrMst[n] = hrMstInit + n - 1
            # ---------------------------
            # Write a line for this time.
            # ---------------------------
            if uvOrWspdWdir == 'uv':
                line = '{:3d},{:s},{:.4f},{:.4f}'.format(n,timeUtcOut,u10point[site][n],v10point[site][n])
            else:
                line = '{:3d},{:s},{:.0f},{:.2f},{:.2f},{:.2f},{:.2f}'.format(n,timeUtcOut,hrMst[n],wdir[site][n],0,wspd[site][n],0)
            #print('validDate:', validDate)
            #print('line:', line)
            csvOut.write(line + '\n')
        
# ---------------------------------------------------------------------------
# Write a separate file of wind speeds and directions for all sites together.
# ---------------------------------------------------------------------------
if uvOrWspdWdir == 'wspdWdir':
    # ---------------------------
    # Open CSV file.
    # ---------------------------
    csvFile = scenario + '-all' + '.csv'
    with open(csvFile, 'w') as csvOut:
        header = 'n,timeUtc,hrMst'
        for site in sites:
            header += ',' + site + ' wdir'
        header += ',hrMst'
        for site in sites:
            header += ',' + site + ' wspd'
        csvOut.write(header + '\n')
        for n in range(1, ntimes):
            # ---------------------------
            # Write a line for this time.
            # ---------------------------
            line = '{:3d},{:s},{:.0f},'.format(n,timeUtcOut,hrMst[n])
            for site in sites:
                line += '{:.2f},'.format(wdir[site][n])
            line+= '{:.0f},'.format(hrMst[n])
            for site in sites:
                line += '{:.2f},'.format(wspd[site][n])
            csvOut.write(line + '\n')

