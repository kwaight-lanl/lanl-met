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
locations = ['TA6', 'TA54']

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
