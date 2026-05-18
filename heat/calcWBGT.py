"""
calcWBGT.py
Calculation of Wet Bulb Globe Temperature from met data.
Use input data from arguments or from sample data defined in the code.
Following Liljegren, J.C., R.A. Carhart, P. Lawday, S. Tschopp and 
R. Sharp: 2008: Modeling the wet bulb globe temperature using standard 
  meteorological measurements. J. Occup. Env. Hygiene, 5, 645-655.
Ken Waight / August 2023
"""

import sys
import math
from datetime import datetime
import argparse
import wbgt  # Module that contains everything necessary to calculate WBGT. 

#import thermofeel
# Using thermofeel doesn't work because of numba problem.
#wbgt = thermofeel.calculate_wbgt(float(T2mC), Tmrt, float(wspd10m), float(Td2mC))

# ----------
# Constants.
# ----------
T0 = 273.16  # Freezing point, K.
DEG_RAD = math.pi / 180.  # Convert degrees to radians.
RAD_DEG = 180. / math.pi  # Convert radians to degrees.

# ============
# Subroutines.
# ============
def TC2F(TC):
    """
    Convert temperature from Celsius to Fahrenheit.
    Ken Waight / December 2020
    """
    return (1.8*TC) +32.


# =============
# Main program.
# =============
# ----------------------------------------------------------------
# Parse arguments.
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Calculate the wet bulb globe temperature.")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
parser.add_argument("-latitude",  help="latitude (deg)")
parser.add_argument("-longitude", help="longitude (deg)")
parser.add_argument("-yyyymmddhhmn", help="Date/time string, UTC")
parser.add_argument("-t2m", help="2 meter temperature (C)")
parser.add_argument("-td2m", help="2 meter dew point temperature (C)")
parser.add_argument("-wspd10m", help="10 meter wind speed (m/s)")
parser.add_argument("-psfc", help="Surface pressure (mb)")
parser.add_argument("-cloudfrac", help="Cloud fraction (0.0-1.0)")
parser.add_argument("-swdn", help="Downward shortwave radiation (W/m2)")
parser.add_argument("-swup", help="Upward shortwave radiation (W/m2)")
parser.add_argument("-lwdn", help="Downward longwave radiation (W/m2)")
parser.add_argument("-lwup", help="Upward longwave radiation (W/m2)")
args = parser.parse_args()
if args.verbosity:
    verbosity = int(args.verbosity)
else:
    verbosity = 0
if (args.latitude and args.longitude and args.yyyymmddhhmn and
    args.t2m and args.td2m and args.wspd10m and args.psfc and
     args.cloudfrac): 
    # Use the input variables from the arguments.
    print('\nUsing input data from arguments, including cloud fraction.')
    latitude = float(args.latitude)
    longitude = float(args.longitude)
    yyyymmddhhmn = args.yyyymmddhhmn
    yyyy = int(yyyymmddhhmn[0:4])
    mm = int(yyyymmddhhmn[4:6])
    dd = int(yyyymmddhhmn[6:8])
    hh = int(yyyymmddhhmn[8:10])
    mn = int(yyyymmddhhmn[10:12])
    T2mC = float(args.t2m)
    Td2mC = float(args.td2m)
    wspd10m = float(args.wspd10m)
    pSfc = 100.0 * float(args.psfc)
    cloudFrac = float(args.cloudfrac)
    swdn = None
    swup = None
    lwdn = None
    lwup = None
elif (args.latitude and args.longitude and args.yyyymmddhhmn and
      args.t2m and args.td2m and args.wspd10m and args.psfc and
      args.swdn and args.swup and args.lwdn and args.lwup):
    # Use the input variables from the arguments, with radiation data instead of cloud fraction.
    print('\nUsing input data from arguments, including radiation data instead of cloud fraction.')
    latitude = float(args.latitude)
    longitude = float(args.longitude)
    yyyymmddhhmn = args.yyyymmddhhmn
    yyyy = int(yyyymmddhhmn[0:4])
    mm = int(yyyymmddhhmn[4:6])
    dd = int(yyyymmddhhmn[6:8])
    hh = int(yyyymmddhhmn[8:10])
    mn = int(yyyymmddhhmn[10:12])
    T2mC = float(args.t2m)
    Td2mC = float(args.td2m)
    wspd10m = float(args.wspd10m)
    pSfc = 100.0 * float(args.psfc)
    cloudFrac = None
    swdn = float(args.swdn)
    swup = float(args.swup)
    lwdn = float(args.lwdn)
    lwup = float(args.lwup)
elif len(sys.argv) > 0:
    print('\nWARNING: Incomplete set of arguments provided!',
          '\nExamples of the two possible sets:',
          '\n1. -latitude 35.86 -longitude -106.32 -yyyymmddhhmn 202505162148 -t2m 20.1 -td2m -11.4 -wspd10m 4.4 -psfc 774.4 -cloudfrac 0.5',
          '\n2. -latitude 35.86 -longitude -106.32 -yyyymmddhhmn 202505162148 -t2m 20.1 -td2m -11.4 -wspd10m 4.4 -psfc 774.4 -swdown 800 -swup 200 -lwdn 300 -lwup 600')
    print('\nOr just run without arguments to see a sample calculation.') 
    sys.exit()
else:
    # If the input variable arguments are not there or incomplete, default
    #   to one of the sets of sample input data below.
    print('\nUsing example input data from definitions in the code.')
    #ktw: From Dimiceli and Piltz, first example. Their WBGT was 91.4 F = 33 C
    latitude = 36.15  # Near Tulsa, OK.
    longitude = -95.99
    yyyy = 2010
    mm = 9
    dd = 9
    hh = 14 # They didn't give a time, but 14Z gives about their 336 W/m2
    mn = 00
    wspd10m = 2.5    # 5-6 mph
    pSfc = 99300.0   # 30.08 in Hg
    T2mC = 30.0      # 86 F
    Td2mC = 20.56    # 69 F
    cloudFrac = 0.0  # Hazy

    #ktw: From Dimiceli and Piltz, second example. Their WBGT was 103 F =  C
    latitude = 36.15  # Near Tulsa, OK.
    longitude = -95.99
    yyyy = 2010
    mm = 9
    dd = 10
    hh = 16 # They didn't give a time, but 16Z gives about their 754 W/m2
    mn = 00
    wspd10m = 3.1    # 7 mph
    pSfc = 98200.0   # 29.75 in Hg
    T2mC = 33.9      # 93 F
    Td2mC = 24.4    # 76 F
    cloudFrac = 0.0  # Sunny

    #ktw: From Dimiceli and Piltz, third example. Their WBGT was 105 F =  C
    latitude = 36.15  # Near Tulsa, OK.
    longitude = -95.99
    yyyy = 2010
    mm = 9
    dd = 17
    hh = 15 # They didn't give a time, but 15Z gives about their 579 W/m2
    mn = 00
    wspd10m = 1.7    # 3.7 mph
    pSfc = 99200.0   # 30.05 in Hg
    T2mC = 34.4      # 94 F
    Td2mC = 24.4    # 76 F
    cloudFrac = 0.0  # Sunny

    #ktw: Input location, date/time, basic met values.
    # Compare to Rob Daly's WBGT instrument, 11/2/2023 near TA54:
    #latitude = 35.8259   # TA54 tower.
    #longitude = -106.2232
    #yyyy = 2023 
    #mm = 11
    #dd = 2
    #hh = 21
    #mn = 15
    #wspd10m = 2.1
    #T2mC = 16.6
    #pSfc = 80400.0
    #Td2mC = -14.3
    #cloudFrac = 0.0

    # Create the date string.
    yyyymmddhh = '{:04d}{:02d}{:02d}{:02d}{:02d}'.format(int(yyyy), int(mm), int(dd), int(hh), int(mn))
    
# Banner.
print('\n========================================================')
print('Calculate Wet Bulb Globe Temperature from Met Data.')
print('Method of Liljegren et al. (2008).')
print('========================================================')

# --------------------
# Show input met data.
# --------------------
if verbosity == 1:
    print(*sys.argv)
    print("\n Input data:")
    print(" --------------------------------------------------")
    print(" Time and date     : {:02d}{:02d} UTC {:02d}/{:02d}/{:04d}".format(hh,mn,mm,dd,yyyy))
    print(" Latitude          : {:.1f} deg".format(latitude))
    print(" Longitude         : {:.1f} deg".format(longitude))
    print(" Station pressure  : {:.1f} mb".format(.01*pSfc))
    print(" 2 m temperature   : {:.1f} C".format(T2mC))
    print(" 2 m dew point     : {:.1f} C".format(Td2mC))
    print(" 10 m wind speed   : {:.1f} m/s".format(wspd10m))
    if cloudFrac is not None:
        print(" Cloud fraction    : {:.3f}".format(cloudFrac))
    if swdn is not None:
        print(" Downward shortwave: {:.1f} W/m2".format(swdn))
    if swup is not None:
        print(" Upward shortwave  : {:.1f} W/m2".format(swup))
    if lwdn is not None:
        print(" Downward longwave : {:.1f} W/m2".format(lwdn))
    if lwup is not None:
        print(" Upward longwave   : {:.1f} W/m2".format(lwup))

# Call WBGT function.
(Twet, Tglobe, wbgt) = wbgt.calcWbgt(yyyymmddhhmn,latitude, longitude,
                                     T2mC, Td2mC, wspd10m, pSfc, cloudFrac, swdn,
                                     verbosity)
if verbosity <= 1:
    print("\n Result:")
    print(" --------------------------------------------------")
    print(" 2 m WBGT: {:.1f} C = {:.1f} F".format(wbgt, TC2F(wbgt)))

