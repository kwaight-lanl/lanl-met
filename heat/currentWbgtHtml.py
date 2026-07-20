"""
currentWbgtHtml.py
Read latest tower2wbgt.taX.csv files and write a simple HTMl file
showing the current values and supporting information.
Ken Waight / July 2026
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime
import pytz
import dominate
from dominate.tags import *

# ----------------------------------------------------------------
# Parse arguments.
# Get name of tower2wbgt.csv files to read.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Read a tower2wbgt.csv file and make a simple plot")
parser.add_argument("tower2wbgtFile1", help="Name of first tower2wbgt.csv file to read")
parser.add_argument("tower2wbgtFile2", help="Name of second tower2wbgt.csv file to read")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
args = parser.parse_args()
tower2wbgtFile1 = args.tower2wbgtFile1
tower2wbgtFile2 = args.tower2wbgtFile2

# Read data into a dataframe. Extract the last lines.
wbgtData1 = pd.read_csv(tower2wbgtFile1, parse_dates=True)
wbgtCurrent1 = wbgtData1.tail(1)
print(wbgtCurrent1)
#print(wbgtCurrent1['WBGT(F)'].values[0])
wbgtData2 = pd.read_csv(tower2wbgtFile1, parse_dates=True)
wbgtCurrent2 = wbgtData1.tail(2)

# Extract the desired current data for the WBGT webpage.
title = 'Wet Bulb Globe Temperatures (WBGT), most recent 15 min observations'
# TA6
time1 = wbgtCurrent1['dts'].values[0]
# Reformat time.
dt1 = datetime.strptime(time1, "%m/%d/%Y %H:%M")
#mountain = pytz.timezone('America/Denver')
#print('mountain:', mountain)
#localtime1 = dt1.astimezone(mountain)
timestring1 = dt1.strftime("%H:%M %p MST %B %d, %Y")
wbgt1 = 'WBGT at TA-6 (Main) meteorological tower: ' + str(wbgtCurrent1['WBGT(F)'].values[0]) + ' F'
temp1 = '   Air temperature (dry bulb): ' + str(wbgtCurrent1['T2m(F)'].values[0]) + ' F'
rh1 = '   Relative humidity: ' + str(wbgtCurrent1['RH'].values[0]) + ' %'
wspd1 = '   Wind speed: ' + str(wbgtCurrent1['wspd10m(mph)'].values[0]) + ' mph'
# TA54
time2 = wbgtCurrent2['dts'].values[0]
# Reformat time.
dt2 = datetime.strptime(time2, "%m/%d/%Y %H:%M")
timestring2 = dt2.strftime("%H:%M %p MST %B %d, %Y")
wbgt2 = 'WBGT at TA-54 (White Rock) meteorological tower: ' + str(wbgtCurrent2['WBGT(F)'].values[0]) + ' F'
temp2 = '   Air temperature (dry bulb): ' + str(wbgtCurrent2['T2m(F)'].values[0]) + ' F'
rh2 = '   Relative humidity: ' + str(wbgtCurrent2['RH'].values[0]) + ' %'
wspd2 = '   Wind speed: ' + str(wbgtCurrent2['wspd10m(mph)'].values[0]) + ' mph'

# Info for HTML file.
print(title)
print('\n', timestring1)
print(wbgt1)
print(temp1)
print(rh1)
print(wspd1)
print('\n', timestring2)
print(wbgt2)
print(temp2)
print(rh2)
print(wspd2)
print('\nNote: Use the WBGT measurement nearest to the location where the work is taking place.')
print('-------------------')
print('If WBGT is > 85 F, reach out to your local Industrial Hygienist for a heat stress assessment.') 
print('A Heat Stress Screening Protection Plan is required.')
print('Additional details are available on the <a href="https://int.lanl.gov/safety/industrial_hygiene_and_safety/ihs-programs/thermal-stress.shtml">Thermal Stress webpage</a>.')

# Write html file.
doc = dominate.document(title='wbgt_current.html')
with doc.head:
    link(rel='stylesheet', href='style.css')
    script(type='text/javascript', src='script.js')

with doc:
    print(html(body(h3('Wet Bulb Globe Temperature (WBGT), Most Recent 15 min Observations'))))
    print(html(body(h4(wbgt1))))
    list = ul()
    list += li('\n' + timestring1)
    list += li(temp1)
    list += li(rh1)
    list += li(wspd1)

    print(html(body(h4(wbgt2))))
    list = ul()
    list += li('\n' + timestring2)
    list += li(temp2)
    list += li(rh2)
    list += li(wspd2)

    print(html(body(h4('NOTE: Use the WBGT measurement nearest to the location where the work is taking place.'))))
    print('<hr>')
    print(html(body(h4('If WBGT is > 85 F, reach out to your local Industrial Hygienist for a heat stress assessment.'))))
    print(html(body(p('A Heat Stress Screening Protection Plan is required.'))))
    print(html(body(a('Additional details are available on the Thermal Stress webpage.', href='https://int.lanl.gov/safety/industrial_hygiene_and_safety/ihs-programs/thermal-stress.shtml'))))

# Write the file.
htmlFile = 'wbgt_current.html'
with open(htmlFile, 'w') as outFile:
   outFile.write(str(doc))

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()





