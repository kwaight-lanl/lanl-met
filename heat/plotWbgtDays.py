"""
plotWbgtDays.py
Read Wet Bulb Globe Temperature time series file and plot WBGT time series 
from multiple days on the same plot.
Adapted from plotTs.py.
Ken Waight / June 2025
"""

import os
import sys
import csv
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
#import seaborn as sns
import argparse

# Initialize.
wbgtData = {}

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


# Parse tower2wbgt.location.csv filename for location name.
filenameParts = tower2wbgtFile.split('.')
location = filenameParts[1].upper()

# Set up plots.
#plt.style.use('seaborn')
fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)
ax1.set_xticks([0, 3, 6, 9, 12, 15, 18, 21, 24])
ax1.set_xlabel('Hour of the Day (MST)')
ax1.set_ylabel('WBGT (F)')
ax1.set_title('Wet Bulb Globe Temperature' + ', ' + location.upper())

# Read data into a dataframe.
wbgtData1 = pd.read_csv(tower2wbgtFile, parse_dates=True)
#print(wbgtData1)
wbgtData1Html = wbgtData1[['dts','wspd10m(mph)','RH','T2m(F)','WBGT(F)']]
htmlFile = 'wbgt.html'
htmlOut = open(htmlFile, 'w')
htmlOut.write(wbgtData1Html.to_html())

#print('pd.read_csv'); sys.exit()
wbgtData['ta6'] = wbgtData1
#print('wbgtData:', wbgtData['ta6'])

# Create a dataframe with all of the variables in the csv file.
#df = pd.DataFrame(wbgtData['ta6']['datetime'])
#df.time = pd.to_datetime(df.datetime)
df = pd.DataFrame(wbgtData['ta6']['dts'])
df.time = pd.to_datetime(df.dts)
df['wbgt'] = wbgtData['ta6']['WBGT(F)']
#print(df)
# Create a time series from the datetime and WBGT columns.
wbgts = wbgtData['ta6']['WBGT(F)'].values
dates = wbgtData['ta6']['dts'].values
dts = []
for date in dates:
    dt = datetime.strptime(date,'%m/%d/%Y %H:%M')
    dts.append(dt)
tsAll = pd.Series(wbgts, index=dts)
#print('wbgts:', wbgts)
#print('dates:', dates)
#print('dts:', dts)
#print('tsAll:', tsAll)
# Extract the dates in the time series.
dataDates = []
for date in dates:
    day = date[0:10]
    if day not in dataDates:
        dataDates.append(day)
most_recent_date = df['dts'].max()[0:10]
#print('most_recent_date:', most_recent_date)
mmddyyyyLatest = datetime.strptime(most_recent_date, '%m/%d/%Y')
#mmddyyyyLatest = str(most_recent_date)[0:10]
#print('mmddyyyyLatest:', mmddyyyyLatest)
#dfToday = df[mmddyyyyLatest:]

# Create an html table from the data frame.

# Slice each individual day from complete time series.
print('Slice individual dataDates:', dataDates)
tsDay = {}
#print('tsAll:', tsAll)
for dataDate in dataDates:
    #print('dataDate:', dataDate)
    tsSliced = tsAll[dataDate]
    #print('tsSliced:', tsSliced)
    hours = []
    wbgts = []
    for dt, value in tsSliced.items():
        hh = dt.strftime('%H')
        mn = dt.strftime('%M')
        hour = float(hh) + float(mn)/60.0
        hours.append(hour)
        wbgts.append(value)
        daystring = dataDate
        tsDay[daystring] = pd.Series( wbgts, index=hours)
        #print('daystring,tsDay', daystring, tsDay[daystring])

# Plot days.
ax1.set_title('Wet Bulb Globe Temperature' + ', ' + location.upper())
if len(dataDates) == 3:
    # Show only the latest two dates.
    plotDates = dataDates[1:]
else:
    plotDates = dataDates
# Plot first day with dashed line.
daystring = plotDates[0]
tsDay[daystring].plot()
ax1.plot(tsDay[daystring].index, tsDay[daystring].values, color='black', linestyle='dotted', label=daystring)
# Plot second day with solid line.
daystring = plotDates[1]
tsDay[daystring].plot()
ax1.plot(tsDay[daystring].index, tsDay[daystring].values, color='black', linestyle='solid', label=daystring)

# Legend.
ax1.legend(loc='best')

# Save as a file.
fig.savefig('wbgt.png')
