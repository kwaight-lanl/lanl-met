#!/usr/bin/env python3

"""
fuelm.py
Emulate the evolution of fuel moisture variables over time.
Usage: fuelm.py
Ken Waight / February 2022
"""

# ========
# Imports.
# ========
import sys
import os
import math

# Constants
CSVFILE = 'fuelm.csv'
ETIME_MAX = 90.0 * 24.0 * 3600.  # Sumulation time in seconds.

# ----------------
# Initialization.
# ----------------
fuelm10hr_us = 18.0 # Raw measurement.
airtemp1_degc = 5.0
rh_pct1 = 50.0
daylit = 12.0
daily_precip_time = 0.0
pptdur = 0.0
fuelm100hr_yest = None
emcmax = None
emcmin = None
bndryt = {1: 20, 2:20, 3:20, 4:20, 5:20, 6:20, 7:20} # (10+5*climat)
mc1000 = {1: 20, 2:20, 3:20, 4:20, 5:20, 6:20, 7:20} # (climat=2 for Lab)
precipMinutes = {}
# Six days of rain all day.
precipMinutes = {5:1440.0, 6:1440.0, 7:1440.0, 8:1440.0, 9:1440.0, 10:1440.0}

# --------------------
# Write to a csv file.
# --------------------
with open(CSVFILE, 'w') as csvOut:
    # Header.
    csvOut.write('Day' + ',' + 
                 'emcbar' + ',' + 
                 'bndryh' + ',' + 
                 'fuelm10hr_prct' + ',' + 
                 'fuelm100hr_prct' + ',' + 
                 'fuelm1000hr_prct' + '\n') 

    # ----------------
    # 3 sec scan loop.
    # ----------------
    print('Running loop of 3 s iterations:')
    etime = 0.0
    while etime <= ETIME_MAX:

        # Calculate the day.
        day = etime/(24.0*3600.0)
        nDay = int(day)
        hour = (day - float(nDay)) * 24.0

        # Accumulate precip.
        precipMinutesToday = precipMinutes.get(nDay, 0.0) 
        if (precipMinutesToday > 0.0 and
            hour >= 0.60):
            daily_precip_time = precipMinutesToday
            #print('nDay, hour, precipDay, daily_precip_time:', nDay, hour, precipDay, daily_precip_time)
        
        # 10 hr fuel moisture measurement.
        if fuelm10hr_us <= 17.7:
          fuelm10hr_prct=7.6298*fuelm10hr_us-130.0904
        else:
          fuelm10hr_prct=0.0406*fuelm10hr_us**2+3.7685*fuelm10hr_us-73.7974

        # Calculate 1 hr value.
        airtemp1_degf = (1.8*airtemp1_degc)+32
        if rh_pct1 < 10:
          emc = 0.03229 + 0.281073*rh_pct1 - 0.000578*airtemp1_degf*rh_pct1
        elif rh_pct1>=10 and rh_pct1 < 50:
          emc = 2.22749 + 0.160107*rh_pct1 - 0.014784*airtemp1_degf
        elif rh_pct1>= 50:
          emc = 21.0606 + 0.005565*rh_pct1*rh_pct1 - 0.00035*rh_pct1*airtemp1_degf - 0.483199*rh_pct1
        fuelm1hr_prct = (4.12*emc+fuelm10hr_prct)/5.0

        # Keep track of max and min EMC for each day.
        if emcmax == None:
            emcmax = emc
            emcmin = emc
        else:
            emcmax = max(emcmax, emc)
            emcmin = min(emcmin, emc)

        # At the end of every day, make calculations for 100 and
        #   1000 hr variables.
        if etime%(24.0*3600.0) == 0:

            # 100 Hr Fuel Moisture
            #fuelm100hr_yest = dat24hr.fuelm100hr_prct(1,1)
            # 1st time through set to 10% so calc does not = None
            if fuelm100hr_yest == None:
                fuelm100hr_yest = 15 #(5 + 5*climat) where climat is regional and = 2
            else:
                fuelm100hr_yest = fuelm100hr_prct
            pptdur = daily_precip_time/60.0 # get time of precip in hours
            #emcbar = (daylit*emc_vals.emcmin(1,1) + (24.0-daylit)*emc_vals.emcmax(1,1))/24.0
            emcbar = (daylit*emcmin + (24.0-daylit)*emcmax)/24.0
            bndryh = ((24.0-pptdur)*emcbar + pptdur*(0.5*pptdur + 41.0))/24.0
            #if pptdur != 0: print('daily_precip_time, pptdur, emcbar, bndryh:', daily_precip_time, pptdur, emcbar, bndryh)
            fuelm100hr_prct = fuelm100hr_yest+(bndryh-fuelm100hr_yest)*(1.0-0.87*math.exp(-0.24))

            # 1000 Hr Fuel Moisture
            # calculate average of bndryt over previous seven days.
            bdybar = (bndryt[1]+bndryt[2]+bndryt[3]+bndryt[4]+bndryt[5]+bndryt[6]+bndryt[7]) / 7.0
            # pm1000 is the fuel moisture from seven days ago.
            pm1000 = mc1000[1]
            #'Calculate new value of 1000 hr fuel moisture.
            fuelm1000hr_prct = pm1000 + (bdybar-pm1000)*(1.00-0.82*math.exp(-.168))
            # Now shift the arrays of BNDRYT and MC1000 forward one day, dropping the values
            #   from 7 days ago.
            for i in range(1, 7):
                bndryt[i] = bndryt[i+1]
                mc1000[i] = mc1000[i+1]
            # Add new values of 24 hr boundary condition and fuel moisture to the end of arrays.
            bndryt[7] = ((24.0-pptdur)*emcbar + pptdur*(2.7*pptdur + 76.0))/24.0
            mc1000[7] = fuelm1000hr_prct 

            # Reset variables at end of each day.
            daily_precip_time = 0.0
            emcmax = None
            emcmin = None

        # Print results.
        if etime%(24.0*3600.0) == 0:
            #print('   etime, fuelm10hr_prct, emc, fuelm1hr_prct:', etime, round(fuelm10hr_prct, 1), round(emc, 1), round(fuelm1hr_prct,1))
            print('   day, fuelm10hr_prct, fuelm100hr_prct, fuelm1000hr_prct:', etime/(24.0*3600.0), round(fuelm10hr_prct, 1), round(fuelm100hr_prct, 1), round(fuelm1000hr_prct, 1))  
            csvOut.write(str(etime/(24.0*3600.0)) + ',' + 
                         str(round(emcbar, 1)) + ',' + 
                         str(round(bndryh, 1)) + ',' + 
                         str(round(fuelm10hr_prct, 1)) + ',' + 
                         str(round(fuelm100hr_prct, 1)) + ',' + 
                         str(round(fuelm1000hr_prct, 1)) + '\n') 
        
        # Next iteration.
        etime+= 3.0 # Every 3 sec.

# ----
# End.
# ----
sys.exit()
