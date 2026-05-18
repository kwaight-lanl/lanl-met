"""
nc2ts.py
For a set of locations, extract time series from a set of netcdf files
  and write them to a set of CSV files for plotting.
Usage: nc2ts.py -source source -ncfiles file1 [file2, . .]
Ken Waight / November 2020
"""

import sys
import math
import glob
import argparse
from datetime import datetime
import xarray as xr
import pandas as pd
from matplotlib import pyplot as plt

# ==========
# Constants.
# ==========
T0 = 273.16

# ----------------
# Parse arguments.
# ----------------
parser = argparse.ArgumentParser(description="Read a set of netcdf files and extract data at a set of locations")
parser.add_argument("-source", "--source", required=True,
                    help="Source of netcdf files (e.g. hrrr, nam)")
parser.add_argument("-ncfiles", "--ncfiles", nargs="*",
                    help="List of netcdf files to read")
args = parser.parse_args()
source = args.source
ncfiles = args.ncfiles

# ==========
# Functions.
# ==========
def getNearest(sites, iNearestAtt, jNearestAtt,
               latVar, lonVar, nxbeg, nxend, nybeg, nyend):
    """
    For a given grid of lat-lon values, find the nearest i-j grid points to 
      a set of site lat-lons.
    Ken Waight / October 2020
    """
    for site in sites:
        print('   ', site)
        iNearestTest = sites[site].get(iNearestAtt, -1) 
        jNearestTest = sites[site].get(jNearestAtt, -1) 
        if (iNearestTest >= nxbeg and iNearestTest <= nxend and 
            jNearestTest >= nybeg and jNearestTest <= nyend):
            print('      precalculated nearest point:', iNearestTest, jNearestTest)
            continue
        else:
            print('      finding nearest point')
            distMin = 360.
            for j in range(nybeg, nyend+1):
                for i in range(nxbeg, nxend+1):
                    dlat = abs(sites[site]['lat']-latVar[j, i].data)
                    dlon = abs(sites[site]['lon']-lonVar[j, i].data)
                    dist = math.sqrt(dlat*dlat + dlon*dlon)
                    if dist < distMin:
                        sites[site][iNearestAtt] = i
                        sites[site][jNearestAtt] = j
                        distMin = dist
            print('      nearest point:', sites[site][iNearestAtt], sites[site][jNearestAtt])

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

def TK2C(TK):
    """
    Convert temperature from deg K to deg C.
    Ken Waight / October 2020
    """
    return TK - T0

def RHT2Td(RH, T):
    """
    Convert from relative humidity (fraction) and temperature (K) to 
      dew point (K).
    Adapted from an old MASS subroutine.
    Ken Waight / October 2020
    """
    Td = T / (1.0+0.000425*T*(-math.log10(RH)))
    return Td

def q2Td(p, T, q):
    """
    Calculate dew point from pressure (Pa), temperature (K)
      and mixing ratio (kg/kg).
      From an old MASS routine.
    Ken Waight / November 2020
    """

    # Constants.
    EPSIL = .62197
    SFAC881 = 35.86
    SFAC882 = 7.66
    SFAC771 = 17.26938882
    SFAC772 = 21.8745584

    # Calculate the dew point (K)
    if q == 0.:
        Td = T - 30.
    else:
        e = (p*.01*q)/(EPSIL + q)
        dtemp2 = math.log10(e/6.1078)
        if e < 2.22:
            dtemp1 = SFAC882
            dtemp4 = SFAC772
        else:
            dtemp1 = SFAC881
            dtemp4 = SFAC771
        dtemp1 = dtemp1 * dtemp2
        dtemp3 = dtemp4 * 273.16
        dtemp1 = dtemp1 - dtemp3
        dtemp2 = dtemp2 - dtemp4
        dtemp1 = dtemp1 / dtemp2
        Td = dtemp1

    return Td

# ==================
# Procedural script.
# ==================
# Locations of desired sites.
sites = { 'TA6': {'lat': 35.8615, 'lon': -106.3195},
          'TA49': {'lat': 35.8133, 'lon': -106.2993},
          'TA53': {'lat': 35.8701, 'lon': -106.2543},
          'TA54': {'lat': 35.8259, 'lon': -106.2232},
          'TA5': {'lat': 35.8597, 'lon': -106.2522} } 

# Pre-calculated locations on different types of grid points.
# T points (RH, etc.)
sites['TA6']['iNearest'] = 49
sites['TA6']['jNearest'] = 49
sites['TA49']['iNearest'] = 51
sites['TA49']['jNearest'] = 44
sites['TA53']['iNearest'] = 55
sites['TA53']['jNearest'] = 50
sites['TA54']['iNearest'] = 57
sites['TA54']['jNearest'] = 45
sites['TA5']['iNearest'] = 55
sites['TA5']['jNearest'] = 49

# -----------------------------------------------
# Gather the netcdf files. Read each one into an
#   xarray dataset.
# -----------------------------------------------
dsList = []
print('\nReading netcdf files:')
for ncfile in ncfiles:
    print('   ', ncfile)
    ds = xr.open_dataset(ncfile)
    dsList.append(ds)

# -----------------------------------------------
# Extract data at sites.
# -----------------------------------------------
# Find the x-y location of sites.
# T points (RH, etc.)
print('\nFinding nearest i-j of extraction sites for T . .')
xdim = ds.west_east
ydim = ds.south_north
latVar = ds.XLAT[0]
lonVar = ds.XLONG[0]
nxbeg = xdim.data[0]
nxend = xdim.data[-1]
nybeg = ydim.data[0]
nyend = ydim.data[-1]
getNearest(sites, 'iNearest', 'jNearest',
           latVar, lonVar, nxbeg, nxend, nybeg, nyend)

# Extract points, put them in a Pandas dataframe.
print('\nExtracting data at nearest points for each site:')
df = {}
for site in sites:
    print('   ', site)
    # Put data for one site in a dictionary of dictionaries. 
    dataDict = { 'T': {}, 'Td': {}, 'q': {}, 'wdir': {}, 'wspd': {} }
    for ds in dsList:
        timeString = ds.Times.sel().data[0].decode('UTF-8')
        time = datetime.strptime(timeString, '%Y-%m-%d_%H:%M:%S')
        # 2 m Temperature, convert from K to C.
        da =  ds.T2.sel(south_north=sites[site]['jNearest'], 
                        west_east=sites[site]['iNearest'])
        T = da.data[0]
        dataDict['T'][time] = TK2C(T)
        # Water vapor mixing ratio (kg/kg)
        da =  ds.Q2.sel(south_north=sites[site]['jNearest'], 
                        west_east=sites[site]['iNearest'])
        q = da.data[0]
        dataDict['q'][time] = 1000. * q
        # Dew point temperature (C).
        da =  ds.PSFC.sel(south_north=sites[site]['jNearest'], 
                          west_east=sites[site]['iNearest'])
        pSfc = da.data[0]
        Td = q2Td(pSfc, T, q)
        dataDict['Td'][time] = TK2C(Td)
        # 10 m u/v to wind direction (deg)/speed (m/s).
        da =  ds.U10.sel(south_north=sites[site]['jNearest'], 
                         west_east=sites[site]['iNearest'])
        u = da.data[0]
        da =  ds.V10.sel(south_north=sites[site]['jNearest'], 
                        west_east=sites[site]['iNearest'])
        v = da.data[0]
        (dataDict['wdir'][time], 
         dataDict['wspd'][time]) = uv2WdirWspd(u, v)
        
    # Transfer to Pandas dataframe.    
    df[site] = pd.DataFrame(dataDict)
    # Sort by time, because the netcdf file list may not be in the correct order.
    df[site] = df[site].sort_index()
    # Round values.
    df[site]['T'] = df[site]['T'].round(decimals=1)
    df[site]['Td'] = df[site]['Td'].round(decimals=1)
    df[site]['q'] = df[site]['q'].round(decimals=3)
    df[site]['wdir'] = df[site]['wdir'].round(decimals=1)
    df[site]['wspd'] = df[site]['wspd'].round(decimals=1)

# Write dataframe to CSV files, one for each site.
print('\nWriting to CSV files:')
for site in sites:
    csvFile = site + '.' + source + '.csv'
    print('   ', site, '-->', csvFile)
    df[site].to_csv(csvFile, index_label='time')

# -----------------------------------------------
# Make contour plots.
# -----------------------------------------------

