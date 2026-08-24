"""
dat24run.py
Read dat file with last 48 hours, calculate and plot Wet Bulb Globe Temperature for
  one or more locations. Copy plots to the S3 bucket where they can be linked
  from the Weather Machine webpage.
Ken Waight / July 2026
"""

import os
import sys
import subprocess

# List of locations to run.
locations = ['ta6', 'ta54']


# ----------------------------------------------------------------
# Copy the latest 48 hour dat files from Sean's S3 bucket.
# ----------------------------------------------------------------
print('\nCopy the latest 48 hour dat files from Seans S3 bucket:')
for location in locations:
    print('   ', location)
    dat48Path = 's3://446936272237-lanlwmbucket1-production/wet-bulb-data/'
    dat48DatFile = location + '-last48hours.dat'
    command = ['aws', 's3', 'cp', 
               dat48Path + dat48DatFile, '.']
    print("Command:", command)
    result = subprocess.run(command, capture_output=True, text=True)
    print("Output:", result.stdout)
    print('after output')
    print("Errors:", result.stderr)

# ----------------------------------------------------------------
# Read latest last 48 hr dat file. Calculate WBGT and write output
#   csv files.
# ----------------------------------------------------------------
print('\nAdd headers to 48 hour dat files and then calculate WBGT:')
for location in locations:
    print('   ', location)
    dat48DatHeaderFile = location + '-15-dat-header.txt'
    dat48DatFile = location + '-last48hours.dat'
    dat48CsvFile = location + '-last48hours.csv'
    dat2wbgtOutFile = 'dat2wbgt.' + location + '.txt'
    print('   ', dat48DatFile, '->', dat48CsvFile)
    filenames = [dat48DatHeaderFile, dat48DatFile]
    with open(dat48CsvFile, 'w') as outfile:
        for fname in filenames:
            with open(fname) as infile:
                outfile.write(infile.read())
    command = ['python3', 'dat2wbgt.py', dat48CsvFile]
    #print('command:', command)
    subprocess.run(command)
    # Add location to the resulting dat2wbgt.csv file.
    dat2wbgtCsvFile = 'dat2wbgt.' + location + '.csv'
    print('   Rename resulting dat2wbgt.csv file: dat2wbgt.csv ->', dat2wbgtCsvFile)
    command = ['mv', 'dat2wbgt.csv', dat2wbgtCsvFile]
    #print('command:', command)
    subprocess.run(command)

# ----------------------------------------------------------------
# Make a WBGT time series plot for each location.
# ----------------------------------------------------------------
print('\nPlot WBGT time series:')
for location in locations:
    print('   ', location)
    dat2wbgtFile = 'dat2wbgt' + '.' + location + '.csv'
    command = ['python3', 'plotWbgtDays.py', dat2wbgtFile]
    #print(command)
    subprocess.run(command)
    # Add location name to resulting png and html files.
    pngFile = 'wbgt.' + location.upper() + '.png'
    htmlFile = 'wbgt.' + location.upper() + '.html'
    command = ['mv', 'wbgt.png', pngFile]
    #print(command)
    subprocess.run(command)
    command = ['mv', 'wbgt.html', htmlFile]
    #print(command)
    subprocess.run(command)

# ----------------------------------------------------------------
# Write an HTML file with the current WBGT and related info.
# ----------------------------------------------------------------
print('\nWrite current WBGT and related info to an HTML file:')
dat2wbgtFile1 = 'dat2wbgt' + '.' + locations[0] + '.csv'
dat2wbgtFile2 = 'dat2wbgt' + '.' + locations[1] + '.csv'
command = ['python3', 'currentWbgtHtml.py', dat2wbgtFile1, dat2wbgtFile2]
print(command)
subprocess.run(command)

# ----------------------------------------------------------------
# Make a WBGT time series plot for each location.
# ----------------------------------------------------------------
print('\nPlot WBGT time series:')
for location in locations:
    print('   ', location)
    dat2wbgtFile = 'dat2wbgt' + '.' + location + '.csv'
    command = ['python3', 'plotWbgtDays.py', dat2wbgtFile]
    #print(command)
    subprocess.run(command)
    # Add location name to resulting png and html files.
    pngFile = 'wbgt.' + location.upper() + '.png'
    htmlFile = 'wbgt.' + location.upper() + '.html'
    command = ['mv', 'wbgt.png', pngFile]
    #print(command)
    subprocess.run(command)
    command = ['mv', 'wbgt.html', htmlFile]
    #print(command)
    subprocess.run(command)
# ----------------------------------------------------------------
# Copy plots and html files to the S3 bucket.
# ----------------------------------------------------------------
print('\nCopy plots and html tables to S3 bucket:')
for location in locations:
    print('   ', location)
    plotFile = 'wbgt' + '.' + location.upper() + '.png'
    htmlFile = 'wbgt' + '.' + location.upper() + '.html'
    command = ['aws', 's3', 'cp', plotFile, 
               's3://weather.lanl.gov/visualization_assets/' + plotFile]
    subprocess.run(command)
    command = ['aws', 's3', 'cp', htmlFile, 
               's3://weather.lanl.gov/visualization_assets/' + htmlFile]
    print("Command:", command)
    result = subprocess.run(command, capture_output=True, text=True)
    print("Output:", result.stdout)
    print("Errors:", result.stderr)

htmlFile = 'wbgt_current.html'
command = ['aws', 's3', 'cp', htmlFile, 
           's3://weather.lanl.gov/visualization_assets/' + htmlFile]
print("Command:", command)
result = subprocess.run(command, capture_output=True, text=True)
print("Output:", result.stdout)
print("Errors:", result.stderr)
