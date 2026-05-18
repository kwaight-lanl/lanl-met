"""
runFcst.py
For one source and date, download national center gridded data,
  use it to initialize WRF initial states for each time. Then
  extract data for our set of locations, make a basic set of 
  time series plots and spatial plots.
Ken Waight / November 2020
"""

import sys
import os
import shutil
import math
import glob
import argparse
from datetime import datetime, timedelta
import subprocess
import re
import xarray as xr
import pandas as pd
from matplotlib import pyplot as plt

# ==================================
# Run parts of the complete process.
# ==================================
runCleanYesterday = True
runDownload = False
runWRF = False
runTs = True
runPlotTs = True

# ==========
# Constants.
# ==========
HH_INIT_DEFAULT = '06' # Default model initial hour.
# Info for different sources.
VTABLE = {'hrrr': 'Vtable.HRRR.bkb',
          'nam': 'Vtable.NAM' }
URL = {'hrrr': 'https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod',
       'nam': 'https://nomads.ncep.noaa.gov/pub/data/nccf/com/nam/prod' }
HR_LIST = {'hrrr': range(0,37),
           'nam': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 
                   19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 
                   39, 42, 45, 48, 51, 54, 57, 60, 63, 66, 69, 72, 75, 78, 81, 84] }

# ==========
# Functions.
# ==========
def fileNotEmpty(inFile):
    return os.path.isfile(inFile) and os.path.getsize(inFile)>0

# ==================
# Procedural script.
# ==================
# ----------------
# Parse arguments.
# ----------------
parser = argparse.ArgumentParser(description="Use a set of gridded files to initialize WRF and extract data at a set of locations")
parser.add_argument("-sources", "--sources", nargs='+', required=True,
                    help="Sources of gridded data (one or more, e.g. nam hrrr)")
parser.add_argument("-yyyymmddhh", "--yyyymmddhh", required=False,
                    help="UTC date and hour of gridded data to process")
args = parser.parse_args()
if args.yyyymmddhh:
    yyyymmddhh = args.yyyymmddhh
else:
    # Default to today's date at 06Z.
    dtNow = datetime.now()
    yyyymmdd = datetime.strftime(dtNow, '%Y%m%d')
    yyyymmddhh = yyyymmdd + HH_INIT_DEFAULT
sources = args.sources

# ------------------------------------------------------
# Change into directory for the correct day of the week.
# ------------------------------------------------------
yyyymmdd = yyyymmddhh[0:8]
hh = yyyymmddhh[-2:]
dtInit = datetime.strptime(yyyymmddhh, '%Y%m%d%H')
dayOfWeek = dtInit.strftime('%A')
todayDir = dayOfWeek[0:3].lower()
topDir = os.getcwd()
todayDir = topDir + '/' + todayDir
print('\nWorking in directory:', todayDir)

if runCleanYesterday:
    # ----------------------------------------
    # Remove large files from yesterday's run.
    # ----------------------------------------
    print('\nRemove large files from yesterdays run:')
    dtYesterday = dtInit - timedelta(days=1)
    dayOfWeekYesterday = dtYesterday.strftime('%A')
    yesterdayDir = dayOfWeekYesterday[0:3].lower()
    yesterdayDir = topDir + '/' + yesterdayDir
    os.chdir(yesterdayDir)
    print('yesterdays directory:', yesterdayDir)
    globStrings = ['*grib2*', 'wrfinput*.nc']
    for globString in globStrings:
        for rmFile in glob.glob(globString):
            print('   Remove file', rmFile) 
            os.remove(rmFile)

# =========================
# Loop through the sources.
# =========================
print('\nSources:')
for source in sources:
    print('\n========================')
    print(source)
    print('========================')
    if runDownload:
        # -----------------------------------
        # Download the set of gridded files.
        # -----------------------------------
        print('\nDownloading grib files:')
        os.chdir(todayDir)
        # Be sure there are no leftover grib files.
        for rmFile in glob.glob(source +'*.grib2*'):
            print('   Removing leftover grib file', rmFile) 
            os.remove(rmFile)
        # Download files.
        datedDir = source + '.' + yyyymmdd
        for hr in HR_LIST[source]:
            hhForecast = '{:02d}'.format(hr)
            if source == 'nam':
                gribName = 'nam.t' + hh + 'z.awphys' + hhForecast + '.tm00.grib2'
            elif source == 'hrrr':
                gribName = 'conus/hrrr.t' + hh + 'z.wrfprsf' + hhForecast + '.grib2'
            url = URL[source] + '/' + datedDir + '/' + gribName
            try:
                process = subprocess.check_call(['/usr/bin/wget', url])
            except subprocess.CalledProcessError as e:
                print(e)

    if runWRF:
        # -------------------------------------------------
        # Be sure there are no leftover files.
        # -------------------------------------------------
        globStrings = ['WPS/met*.nc', 'WPS/FILE*', 'WPS/PFILE*', 'WPS/GRIBFILE*',
                       'WRF/met*.nc']
        for globString in globStrings:
            for rmFile in glob.glob(globString):
                print('Removing leftover file', rmFile) 
                os.remove(rmFile)
        # -------------------------------------
        # Build list of all grib files present.
        # -------------------------------------
        gribList = glob.glob(source + '.t' + hh + '*.grib2')
        # ----------------------------------------------------------
        # Change into the WPS directory to run the WRF preprocessor.
        # ----------------------------------------------------------
        print('\nLink to the correct Vtable in the WPS directory:')
        os.chdir(todayDir + '/WPS')
        # -----------------------------------
        # Link the correct Vtable for ungrib.
        # -----------------------------------
        # First remove a previous Vtable.
        print('Remove Vtable if one is already there:')
        try:
            os.remove('Vtable')
            print('   Removed old Vtable file successfully.')
        except:
            print('   Vtable file had already been removed.')
        # Link the new one.
        vtablePath = '../../Variable_Tables/' + VTABLE[source]
        os.symlink(vtablePath, './Vtable')
        # -----------------------------------
        # Initialize WRF for each time.
        # -----------------------------------
        print('\nProcessing each grib file:')
        nGrib = 0
        for grib in gribList:
            nGrib += 1
            # Parse the date for the grib file.
            if source == 'nam':
                search = re.search(r'awphys(\d+)\.', grib)
                hrFcst = search.group(1)
            elif source == 'hrrr':
                search = re.search(r'wrfprsf(\d+)\.', grib)
                hrFcst = search.group(1)
            dtForecast = dtInit + timedelta(hours=int(hrFcst))
            startDate = datetime.strftime(dtForecast, '%Y-%m-%d_%H:00:00')
            endDate = startDate
            print('      forecast time:', dtForecast)
            # Link the grib file.
            os.chdir(todayDir + '/WPS')
            gribPath = '../' + grib
            process = subprocess.check_output(['./link_grib.csh', gribPath])
            print('    {:d}. Grib file: {:s}'.format(nGrib, gribPath))
            # Edit namelist.wps.
            namelistNew = open('namelist.new', 'w')
            with open ('namelist.wps', 'r') as namelist:
                for line in namelist:
                    if 'start_date' in line:
                        modLine = ' start_date = \'' + startDate + '\'\n'
                        namelistNew.write(modLine)
                    elif 'end_date' in line:
                        modLine = ' end_date = \'' + endDate + '\'\n'
                        namelistNew.write(modLine)
                    else:
                        # Maintain unchanged lines.
                        namelistNew.write(line)
            namelistNew.close()
            # Check that the rewritten file has the same number of lines.
            nLinesOld = len(open('namelist.wps').readlines())
            nLinesNew = len(open('namelist.new').readlines())
            if nLinesNew == nLinesOld:
                # Successful writing of new file. Rename.
                print('      modified namelist.wps successfully')
                os.rename('namelist.new', 'namelist.wps')
            else:
                print('ERROR: Problem editing namelist file!')
            # Run ungrib.
            print('      running ungrib . .')
            process = subprocess.check_output(['./ungrib.exe'])
            # Run metgrid.
            print('      running metgrib . .')
            process = subprocess.check_output(['./metgrid.exe'])
            # Clean out large ungrib-produce FILE: file.
            patterns = ['GRIBFILE*', 'PFILE:*', 'FILE:*']
            rmFiles = []
            for pattern in patterns:
                rmFiles.extend(glob.glob(pattern))
            for rmFile in rmFiles:
                print('      removing', rmFile) 
                os.remove(rmFile)
            # Check and move resulting netcdf file to WRF directory.
            ncFiles = glob.glob('met*.nc')
            if (len(ncFiles) == 1 and  
                fileNotEmpty(ncFiles[0])):
                print('      moving metgrid netcdf file to WRF dir')
                shutil.move(ncFiles[0], '../WRF/')
            # Change to WRF directory.
            print('      change to WRF directory')
            os.chdir(todayDir + '/WRF')
            # Start with correct version of namelist.input.
            shutil.copyfile('namelist.input.' + source, 'namelist.input')
            # Edit namelist.input.
            startYear = datetime.strftime(dtForecast, '%Y')
            startMonth = datetime.strftime(dtForecast, '%m')
            startDay =  datetime.strftime(dtForecast, '%d')
            startHour =datetime.strftime(dtForecast, '%H')
            endYear = startYear
            endMonth = startMonth
            endDay = startDay
            endHour = startHour
            namelistNew = open('namelist.new', 'w')
            with open ('namelist.input', 'r') as namelist:
                for line in namelist:
                    if 'start_year' in line:
                        modLine = ' start_year = ' + startYear + '\n'
                        namelistNew.write(modLine)
                    elif 'start_month' in line:
                        modLine = ' start_month = ' + startMonth + '\n'
                        namelistNew.write(modLine)
                    elif 'start_day' in line:
                        modLine = ' start_day = ' + startDay + '\n'
                        namelistNew.write(modLine)
                    elif 'start_hour' in line:
                        modLine = ' start_hour = ' + startHour + '\n'
                        namelistNew.write(modLine)
                    elif 'end_year' in line:
                        modLine = ' end_year = ' + endYear + '\n'
                        namelistNew.write(modLine)
                    elif 'end_month' in line:
                        modLine = ' end_month = ' + endMonth + '\n'
                        namelistNew.write(modLine)
                    elif 'end_day' in line:
                        modLine = ' end_day = ' + endDay + '\n'
                        namelistNew.write(modLine)
                    elif 'end_hour' in line:
                        modLine = ' end_hour = ' + endHour + '\n'
                        namelistNew.write(modLine)
                    else:
                        # Maintain unchanged lines.
                        namelistNew.write(line)
            namelistNew.close()
            # Check that the rewritten file has the same number of lines.
            nLinesOld = len(open('namelist.input').readlines())
            nLinesNew = len(open('namelist.new').readlines())
            if nLinesNew == nLinesOld:
                # Successful writing of new file. Rename.
                print('      modified namelist.input successfully')
                os.rename('namelist.new', 'namelist.input')
            else:
                print('ERROR: Problem editing namelist file!')
            # Run real.exe.
            print('      running real . .')
            process = subprocess.check_output(['./real.exe'])
            # Rename wrfinput_d01 and move it to day directory.
            yyyymmddhh_fcst = datetime.strftime(dtForecast, '%Y%m%d%H')
            ncPlot = '../wrfinput.' + yyyymmddhh_fcst + '.' + source + '.nc'
            print('      moving resulting netcdf file to', ncPlot)
            os.rename('wrfinput_d01', ncPlot)

        # If everything worked, clean out unnecessary files.
        # Change back to the WPS directory.
        print('      change back to WPS directory')
        os.chdir(todayDir + '/WPS')

    if runTs:
        # ------------------------------------------------------------
        # Extract time series from netcdf files.
        # ------------------------------------------------------------
        print('\nExtract time series from netcdf files:')
        os.chdir(todayDir)
        ncFileList = glob.glob('wrfinput*' + source + '.nc')
        argList = ['python', '../nc2ts.py', '-source', source, 
                   '-ncfiles'] 
        for ncFile in ncFileList:
            argList.append(ncFile)
        process = subprocess.check_call(argList)
# ===================
# End of source loop.
# ===================

if runPlotTs:
    # ------------------------------------------------------------
    # Run script to make simple time series plots with matplotlib.
    # ------------------------------------------------------------
    print('\nRun script to make simple time series plots with matplotlib:')
    os.chdir(todayDir)
    try:
        process = subprocess.check_call(['python', '../plotTs.py'])
    except subprocess.CalledProcessError as e:
        print(e)

    

