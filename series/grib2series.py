"""
grib2series.py
Read a set of grib2 files and extract time series for a set of points,
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

# Options.
uvOrWspdWdir = 'wspdWdir'
#scenario = 'thunderstorm'
#scenario = 'spring'
#scenario = 'drainage'
scenario = 'series'

# Go through sites:
print('\nGo through sites:')
for site in sites:
    print('   ', site)
    # Open CSV file.
    csvFile = scenario + '-' + site + '.csv'
    with open(csvFile, 'w') as csvOut:
        if uvOrWspdWdir == 'uv':
            csvOut.write('n,time,u(m/s),v(m/s)\n')
        else:
            csvOut.write('n,timeUtc,hrMst,dir1(deg),dir1 obs,spd1(m/s),spd1 obs\n')
        # Go through grib2 files.
        gribfiles = sorted(glob.glob('*.grib2'))
        #print('gribfiles:', gribfiles)
        n = 0
        hrMst = None
        for gribfile in gribfiles:
            n += 1
            #print('gribfile:', gribfile)
            gribdata = mv.read(gribfile)
            u10 = gribdata['10u']
            validDate = mv.valid_date(u10)
            #print('validDate:', validDate)
            timeUtcOut = datetime.strftime(validDate,'%H%M UTC %Y%m%d')
            hrUtc = float(datetime.strftime(validDate,'%H'))
            if not hrMst:
                hrMstInit = hrUtc - 7.0
            if hrMstInit < 0:
                hrMstInit = hrMst + 24.0
            hrMst = hrMstInit + n - 1
            v10 = gribdata['10v']
            u10point = u10.nearest_gridpoint(coords[site])
            v10point = v10.nearest_gridpoint(coords[site])
            if uvOrWspdWdir == 'uv':
                line = '{:3d},{:s},{:.4f},{:.4f}'.format(n,timeUtcOut,u10point,v10point)
            else:
                # Convert u/v to wspd/wdir.
                (wdir, wspd) = uv2WdirWspd(u10point, v10point)
                line = '{:3d},{:s},{:.0f},{:.2f},{:.2f},{:.2f},{:.2f}'.format(n,timeUtcOut,hrMst,wdir,0,wspd,0)
            #print('validDate:', validDate)
            #print('line:', line)
            csvOut.write(line + '\n') 

