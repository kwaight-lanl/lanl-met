#!/usr/bin/env python3

# ========
# IMPORTS.
# ========
import sys
import csv
import argparse
import plotly.graph_objs as go
import plotly.io as pio

# ==============
# FUNCTIONS.
# ==============

# ==============
# MAIN PROGRAM.
# ==============
"""
plotPrecipExtremes.py
Read an extremes CSV file from calcPrecipExtremes.py and make a bar chart of the results. Optionally
plot two files for comparison for a single duration.

Usage: python plotExtremes.py extremes-csv-file-1 [extremes-csv-file-2 duration]

Ken Waight / June 2022
"""

# ----------------------------------------------------------------
# Parse arguments.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read one or two extremes CSV files and make a bar chart.")
parser.add_argument("extremesfile1", help="Name of extremes CSV file to read")
parser.add_argument("-file2", "--extremesfile2", help="Optional second extremes file.")
parser.add_argument("-duration", help="With two extremes files, also specify a duration.")
args = parser.parse_args()
extremesFile1 = args.extremesfile1
if args.extremesfile2:
    extremesFile2 = args.extremesfile2
    durationSelected = args.duration
else:
    extremesFile2 = False

# =======
# Banner.
# =======
print('=====================================\n',
      'Plot Extremes\n',
      '=====================================\n')

# Read first csv file.
returnPeriods1 = []
durations1 = []
extremes1 = {}
print('\nReading extremes csv file:', extremesFile1)
with open(extremesFile1, 'r') as infile:
    csvin = csv.reader(infile)
    nRow = 0
    for row in csvin: 
        nRow += 1
        if nRow == 1:
            fieldnames = row
            for nField in range(1,len(fieldnames)):
                returnPeriods1.append(row[nField])
        else:
            duration = row[0].strip()
            durations1.append(duration)
            extremes1[duration] = []
            for nField in range(1,len(fieldnames)):
                extremes1[duration].append(float(row[nField]))

# Make a grouped bar chart of extremes for all durations and return periods.
extremesPlotFile = "extremes1.png"
print('\nMake a bar chart of the results:', extremesPlotFile)
fig = go.Figure(data=[
    go.Bar(name="15", x=returnPeriods1, y=extremes1["15"]),
    go.Bar(name="60", x=returnPeriods1, y=extremes1["60"]),
    go.Bar(name="120", x=returnPeriods1, y=extremes1["120"]),
    go.Bar(name="180", x=returnPeriods1, y=extremes1["180"]),
])
fig.update_layout(title_text=extremesFile1)
#fig.update_layout(barmode="group")
pio.write_image(fig, extremesPlotFile)

# If specified, read second csv file.
if extremesFile2:
    returnPeriods2 = []
    extremes2 = {}
    print('\nReading second extremes csv file:', extremesFile2)
    with open(extremesFile2, 'r') as infile:
        csvin = csv.reader(infile)
        nRow = 0
        for row in csvin: 
            nRow += 1
            if nRow == 1:
                fieldnames = row
                for nField in range(1,len(fieldnames)):
                    returnPeriods2.append(row[nField])
            else:
                duration = row[0].strip()
                if duration == durationSelected:
                    extremes2[extremesFile1] = []
                    extremes2[extremesFile2] = []
                    for nField in range(1,len(fieldnames)):
                        extremes2[extremesFile1].append(extremes1[duration][nField-1])
                        extremes2[extremesFile2].append(float(row[nField]))

# Make a bar chart of the one specified duration and all return periods
#   from both extremes files to compare.
# Make a grouped bar chart of extremes for all durations and return periods.
extremesPlotFile = "extremes2.png"
print('\nMake a bar chart of the results:', extremesPlotFile)
fig = go.Figure(data=[
    go.Bar(name=extremesFile1, x=returnPeriods2, y=extremes2[extremesFile1]),
    go.Bar(name=extremesFile2, x=returnPeriods2, y=extremes2[extremesFile2]),
])
fig.update_layout(title_text=extremesFile2)
#fig.update_layout(barmode="group")
pio.write_image(fig, extremesPlotFile)

# End.
print('\nCompleted.')
sys.exit()
