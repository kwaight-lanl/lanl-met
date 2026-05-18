#!/usr/bin/env python3

# ========
# IMPORTS.
# ========
import sys
import argparse
import math

# ==============
# FUNCTIONS.
# ==============

# ==============
# MAIN PROGRAM.
# ==============
"""
updateStar.py
Read a STAR file for CAP88 input, which was produced by an old PV-WAVE program,
  and rewrite it with corrected wind direction and stability information on 
  each line, which will allow it to be read by the new CAP-88 utility program, StarGet.
  The PV-WAVE STAR files worked with the previous CAP-88 utility program, but not
  with the new one.
Ken Waight / January 2021
"""

# ----------
# Constants.
# ----------

# --------------------------------------------------
# Wind direction and stability corrections.
# --------------------------------------------------
windDirections = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
stabilityClasses = ['A', 'B', 'C', 'D', 'E', 'F']

# ----------------------------------------
# Get names of file to update.
# ----------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("starfile", help="STAR file to update")
args = parser.parse_args()
starFile = args.starfile

# =======
# Banner.
# =======
print(' =====================================\n',
      'Update a PV-WAVE STAR file\n',
      '=====================================\n')

# ---------------------------------------------------------------------------------------------
# Read PV-WAVE STAR file, write updated one.
# ---------------------------------------------------------------------------------------------
# Build filename of updated file.
starFileParts = starFile.split('.')
starFileParts[-2] += '_updated'
starFileUpdated = '.'.join(starFileParts)
updated = open(starFileUpdated, 'w')
print('\nReading from STAR file:', starFile)
print('\nWriting to updated STAR file:', starFileUpdated)
with open(starFile, 'r') as star:
    for stability in stabilityClasses:
        for windDirection in windDirections:
            line = star.readline()
            line = ' {:3s} {:1s} '.format(windDirection.rjust(3), stability) + line[7:]
            print(line)
            updated.write(line)

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
