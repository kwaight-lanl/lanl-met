"""
plotWbgt.py
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
print(wbgtData1)
wbgtData1Html = wbgtData1[['dts','wspd10m(mph)','RH','T2m(F)','WBGT(F)']]
htmlFile = 'wbgt.html'
htmlOut = open(htmlFile, 'w')
htmlOut.write(wbgtData1Html.to_html())

print('pd.read_csv'); sys.exit()
wbgtData['ta6'] = wbgtData1

# Create a dataframe with all of the variables in the csv file.
df = pd.DataFrame(wbgtData['ta6']['datetime'])
df.time = pd.to_datetime(df.datetime)
df['wbgt'] = wbgtData['ta6']['WBGT(F)']
print(df)
# Create a time series from the datetime and WBGT columns.
wbgts = wbgtData['ta6']['WBGT(F)'].values
dates = wbgtData['ta6']['datetime'].values
tsAll = pd.Series(wbgts, index=dates)
print('wbgts:', wbgts)
print('dates:', dates)
print('tsAll:', tsAll)
most_recent_date = df['datetime'].max()[0:10]
print('most_recent_date:', most_recent_date)
mmddyyyyLatest = datetime.strptime(most_recent_date, '%m/%d/%Y')
#mmddyyyyLatest = str(most_recent_date)[0:10]
print('mmddyyyyLatest:', mmddyyyyLatest)
#dfToday = df[mmddyyyyLatest:]

# Create an html table from the data frame.


# Slice today (latest day in file).
tsSliced = tsAll['09/30/2023':]
hours = []
wbgts = []
for index, value in tsSliced.items():
    print('index,value:', index,value)
    dt = datetime.strptime(index, '%m/%d/%Y %H:%M')
    hh = dt.strftime('%H')
    mn = dt.strftime('%M')
    hour = float(hh) + float(mn)/60.0
    hours.append(hour)
    wbgts.append(value)
tsDay = {}
daystring = 'Saturday, Sep 30'
tsDay[daystring] = pd.Series( wbgts, index=hours)

# Slice yesterday.
tsSliced = tsAll['09/29/2023':'09/30/2023']
hours = []
wbgts = []
for index, value in tsSliced.items():
    dt = datetime.strptime(index, '%m/%d/%Y %H:%M')
    hh = dt.strftime('%H')
    mn = dt.strftime('%M')
    hour = float(hh) + float(mn)/60.0
    hours.append(hour)
    wbgts.append(value)
daystring = 'Friday, Sep 29'
tsDay[daystring] = pd.Series( wbgts, index=hours)

# Slice day before yesterday.
tsSliced = tsAll['09/28/2023':'09/29/2023']
hours = []
wbgts = []
for index, value in tsSliced.items():
    dt = datetime.strptime(index, '%m/%d/%Y %H:%M')
    hh = dt.strftime('%H')
    mn = dt.strftime('%M')
    hour = float(hh) + float(mn)/60.0
    hours.append(hour)
    wbgts.append(value)
daystring = 'Thursday, Sep 28'
tsDay[daystring] = pd.Series( wbgts, index=hours)

# Plot.
daystring = 'Saturday, Sep 30'
tsDay[daystring].plot()
ax1.plot(tsDay[daystring].index, tsDay[daystring].values, color='black', linestyle='solid', label=daystring)

daystring = 'Friday, Sep 29'
tsDay[daystring].plot()
ax1.plot(tsDay[daystring].index, tsDay[daystring].values, color='black', linestyle='dashed', label=daystring)

daystring = 'Thursday, Sep 28'
tsDay[daystring].plot()
ax1.plot(tsDay[daystring].index, tsDay[daystring].values, color='black', linestyle='dotted', label=daystring)

# Legend.
ax1.legend(loc='best')

# Save as a file.
fig.savefig('wbgt.png')
