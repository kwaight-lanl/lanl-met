"""
plotWbgt.py
Read a Wet Bulb Globe Temperature time series file and make a basic WBGT time series plot.
  Also write a simle HTML table.
Adapted from plotTs.py.
Ken Waight / June 2026
"""

import os
import sys
import csv
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
#import seaborn as sns
import argparse

# ----------------------------------------------------------------
# Parse arguments.
# Get name of tower2wbgt.csv file to read. 
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a tower2wbgt.csv file and make a simple plot")
parser.add_argument("tower2wbgtFile", help="Name of tower2wbgt.csv file to read")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
args = parser.parse_args()
tower2wbgtFile = args.tower2wbgtFile

# Initialize.
wbgtData = {}

# Parse tower2wbgt.location.csv filename for location name.
filenameParts = tower2wbgtFile.split('.')
location = filenameParts[1].upper()

# Set up plots.
#plt.style.use('seaborn')
fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)
ax1.set_title('Wet Bulb Globe Temperature' + ', ' + location.upper())
ax1.set_xticks([0, 3, 6, 9, 12, 15, 18, 21, 24])
ax1.set_xlabel('Hour of the Day (MST)')
ax1.set_ylabel('WBGT (F)')


# Read data into a dataframe.
wbgtData1 = pd.read_csv(tower2wbgtFile, parse_dates=True)
#print(wbgtData1)
# Create an html table from a subset of the data frame.
wbgtData1Html = wbgtData1[['dts','wspd10m(mph)','RH','T2m(F)','WBGT(F)']]
htmlFile = 'wbgt.' + location.upper() + '.html'
htmlOut = open(htmlFile, 'w')
# Write the html file.
htmlOut.write(wbgtData1Html.to_html())

wbgtData[0] = wbgtData1

# Create a dataframe with all of the variables in the csv file.
df = pd.DataFrame(wbgtData[0]['dts'])
print('df:', df)
print('df.dts:', df.dts)
df['wbgt'] = wbgtData[0]['WBGT(F)']
#print(df)
# Create a time series from the datetime and WBGT columns.
wbgts = wbgtData[0]['WBGT(F)'].values
dates = wbgtData[0]['dts'].values
print('dates:', dates)
hours = []
day1 = None
lastHour = -1.0
for date in dates:
    #hour = date[11:]
    dt1 = datetime.strptime(date, "%m/%d/%Y %H:%M")
    if not day1:
        day1 = dt1.strftime("%b %d %Y")
    nextHour = dt1.hour + (dt1.minute/60.0)
    if nextHour < lastHour:
        hour = nextHour + 24.0
    else:
        hour = nextHour
    hours.append(hour)
    lastHour = hour
print('hours:', hours)
tsAll = pd.Series(wbgts, index=hours)
#print('wbgts:', wbgts)
#print('dates:', dates)
print('tsAll:', tsAll)

# Plot.
daystring = day1
tsAll.plot()
ax1.plot(tsAll.index, tsAll.values, color='black', linestyle='solid', label=daystring)

# Legend.
ax1.legend(loc='best')

# Save as a file.
wbgtFile = 'wbgt.' + location.upper() + '.png'
fig.savefig(wbgtFile)
