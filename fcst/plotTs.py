"""
plotTs.py
Read time series files and plot series from multiple models.
Ken Waight / November 2020
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import csv

# Set up plots.
plt.style.use('seaborn')
fig = plt.figure()
ax1 = fig.add_subplot(4, 1, 1)
ax1.set_title('Time Series Plots')
ax1.set_ylabel('T (C)')
ax2 = fig.add_subplot(4, 1, 2)
ax2.set_ylabel('Td (C)')
ax3 = fig.add_subplot(4, 1, 3)
ax3.set_ylabel('Wdir (deg)')
ax4 = fig.add_subplot(4, 1, 4)
ax4.set_ylabel('wspd (m/s)')

sourceList = ['hrrr', 'nam']
#sourceList = ['nam']
for source in sourceList:
    # Get the filename.
    fileName = 'TA6.' + source + '.csv'
    # Read data for one tower into a dataframe.
    ta6 = pd.read_csv(fileName, parse_dates=True)
    #print(ta6)
    # Parse the model name from the filename.
    fileNameParts = fileName.split('.')
    #modelName = fileNameParts[-2]

    # Create a dataframe for one tower, with all of the variables.
    df = pd.DataFrame(ta6['time'])
    df.time = pd.to_datetime(df.time)
    df['T'] = ta6['T']
    df['Td'] = ta6['Td']
    df['wdir'] = ta6['wdir']
    df['wspd'] = ta6['wspd']
    #print(df)

    # Temperature.
    ax1.plot_date(df['time'], df['T'], fmt='_', linestyle='solid', label=source)
    ax1.legend(loc='best')
    # Dew point.
    ax2.plot_date(df['time'], df['Td'], fmt='_', linestyle='solid', label=source)
    ax2.legend(loc='best')
    # Wind direction.
    ax3.plot_date(df['time'], df['wdir'], fmt='_', linestyle='solid', label=source)
    ax3.legend(loc='best')
    # Wind speed.
    ax4.plot_date(df['time'], df['wspd'], fmt='_', linestyle='solid', label=source)
    ax4.legend(loc='best')

# Save as a file.
fig.savefig('ts.png')
