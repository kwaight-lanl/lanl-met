"""
plotWbgt.py
Read Wet Bulb Globe Temperature time series file and make a basic WBGT time series.
  Also write a simle HTML table.
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

# Initialize.
wbgtData = {}

# Set up plots.
#plt.style.use('seaborn')
fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)
ax1.set_title('Wet Bulb Globe Temperature')
ax1.set_xticks([0, 3, 6, 9, 12, 15, 18, 21, 24])
ax1.set_xlabel('Hour of the Day (MST)')
ax1.set_ylabel('WBGT (F)')

tower = 'ta6'

# Get the filename.
fileName = 'tower2wbgt.' + tower + '.csv'
# Read data into a dataframe.
wbgtData1 = pd.read_csv(fileName, parse_dates=True)
#print(wbgtData1)
# Create an html table from a subset of the data frame.
wbgtData1Html = wbgtData1[['dts','wspd10m(mph)','RH','T2m(F)','WBGT(F)']]
htmlFile = 'wbgt.html'
htmlOut = open(htmlFile, 'w')
# Write the html file.
htmlOut.write(wbgtData1Html.to_html())

wbgtData['ta6'] = wbgtData1

# Create a dataframe with all of the variables in the csv file.
df = pd.DataFrame(wbgtData['ta6']['dts'])
print('df:', df)
print('df.dts:', df.dts)
df['wbgt'] = wbgtData['ta6']['WBGT(F)']
#print(df)
# Create a time series from the datetime and WBGT columns.
wbgts = wbgtData['ta6']['WBGT(F)'].values
dates = wbgtData['ta6']['dts'].values
print('dates:', dates)
hours = []
day1 = None
for date in dates:
    #hour = date[11:]
    dt1 = datetime.strptime(date, "%m/%d/%Y %H:%M")
    if not day1:
        day1 = dt1.strftime("%b %d %Y")
    hour = dt1.hour + (dt1.minute/60.0)
    hours.append(hour)
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
fig.savefig('wbgt.png')
