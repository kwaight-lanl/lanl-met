"""
gis24run.py
Read GIS24 report, calculate and plot Wet Bulb Globe Temperature for
  one or more locations.
Ken Waight / June 2026
"""

import os
import sys
import subprocess

# List of locations to run.
locations = ['ta6', 'ta54']

# ----------------------------------------------------------------
# Read latest GIS24 report file. Calculate WBGT and write output
#   csv files.
# ----------------------------------------------------------------
gis24File = 'gis24.csv'
command = ['python3', './gis2wbgt.py', gis24File]
print('\nRun gis24.csv to calculate WBGT . .')
subprocess.run(command)

# ----------------------------------------------------------------
# Make a WBGT time series plot for each location.
# ----------------------------------------------------------------
print('\nPlot WBGT time series:')
for location in locations:
    tower2wbgtFile = 'tower2wbgt' + '.' + location + '.csv'
    command = ['python3', './plotWbgt.py', tower2wbgtFile]
    print('   ', location)
    subprocess.run(command)

# ----------------------------------------------------------------
# Copy plots and html tables to the S3 bucket.
# ----------------------------------------------------------------
print('\Copy plots and html tables to S3 bucket:')
for location in locations:
    plotFile = 'wbgt' + '.' + location.upper() + '.png'
    htmlFile = 'wbgt' + '.' + location.upper() + '.html'
    #aws s3 cp wbgt.TA54.png s3://weather.lanl.gov/visualization_assets/wbgt.TA54.png
    print('   ', location)
    command = ['aws', 's3', 'cp', plotFile, 
               's3://weather.lanl.gov/visualization_assets/' + plotFile]
    #print('command:', ' '.join(command))
    subprocess.run(command)
    command = ['aws', 's3', 'cp', htmlFile, 
               's3://weather.lanl.gov/visualization_assets/' + htmlFile]
    subprocess.run(command)


