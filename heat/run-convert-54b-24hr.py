"""
run-convert-54b-24hr.py
Run athena-convert-54b-24hr.py on a set of 54B csv historical files in the old format
  and write them in the new format.
Ken Waight / July 2026
"""

import os
import sys
import subprocess
import argparse

# -------------------------------------------------------------------
# Define destination directory for files converted to the new format.
# -------------------------------------------------------------------
NEW_HIST_DIR = 'histfiles-new'

# ----------------
# Parse arguments.
# ----------------
parser = argparse.ArgumentParser(description="Convert a set of 54B historical files.")
parser.add_argument("-histfiles", "--histfiles", nargs="*",
                    help="List of history files to read")
args = parser.parse_args()
oldHistFiles = args.histfiles

# Loop through input files and convert each one.
print('\nConverting old TA54B 24 hr history files to a new format:\n')
for oldHistFile in oldHistFiles:
    newHistFile = NEW_HIST_DIR + '/' + oldHistFile
    print(oldHistFile, '->', newHistFile)
    command = ['python3', 'athena-convert-54b-24hr.py', oldHistFile, newHistFile]
    #print('command:', command)
    subprocess.run(command)
    print(' ')
