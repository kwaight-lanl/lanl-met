#!/usr/bin/env python3

"""
assemble.py
Assemble a Campbell Scientific data logger program from a library of code
fragments.
Usage: assemble.py -tables table1 [table2 . .] -parts part1 [part2 . .] [-o outfile]

Names of possible parts: 
header footer . .

Towers (code specific to one tower, e.g. wiring info, port assignments):
TA16B.txt  TA54B.txt  TA63.txt
TA49.txt   TA54.txt   TA6.txt
TA53.txt   TA5.txt    NCOM.TXT
TA68.txt . .
 
Instruments:
wind-horiz-1 
wind-horiz-2 
wind-horiz-20ft 
wind-vert-1 
81000 
csat
temp-rh-41382-0
temp-rh-41382-1
fuelm-1 
fuelm-10 
fuelm-100-1000 
snow-laser
tipping-bucket
solar-voltage
. .

Ken Waight / February 2022
"""

# ========
# Imports.
# ========
import sys
import os
import argparse
import datetime

# ----------------
# Parse arguments.
# ----------------
parser = argparse.ArgumentParser(description="Build a Campbell Scientific data logger program from a library of parts.")
parser.add_argument("-v", "--verbosity", help="Increase the verbosity of the output",
                    action="count")
parser.add_argument("-mode", choices=['sequential', 'pipeline'],
                    help="Set SequentialMode or PipelineMode.")
parser.add_argument("-angledegrees", action="store_true", help="Insert AngleDegrees statement.")
parser.add_argument("-tables", nargs='*', help="List of data tables to be included.")
parser.add_argument("-parts", nargs='*', help="List of components to be combined.")
parser.add_argument("-o", "--outfile", help="Name of Campbell program file to produce.")
args = parser.parse_args()
if args.mode == 'sequential':
    sequential = True
    pipeline = False
elif args.mode == 'pipeline':
    sequential = False
    pipeline = True
else:
    sequential = False
    pipeline = False
tables = args.tables
parts = args.parts
if args.verbosity:
    verbosity = int(args.verbosity)
else:
    verbosity = 0
if args.outfile:
    codeFile = args.outfile
else:
    codeFile = 'test.cr3'

# ==========
# Variables.
# ==========
# Basic parts, used for all versions of the code.
fragments = {}
tableFragments = {}

sections1 = ['header', 'wiring', 'instruments', 'definitions', 'variables']
fragments['header'] = []
fragments['wiring'] = ['header']
fragments['instruments'] = ['header']
fragments['definitions'] = ['header']
fragments['variables'] = ['header']

tablesAll = ['dat1min', 'dat10min', 'dat15min', 'dat24hr', 
             'public15', 'emc_vals',
             'CSAT3BMonitorData', 'CSAT3BSonicData',
             'DataStats', 'DataWindVec',
             'opsMonitor',
             'csat']
tableFragments['dat15min'] = ['header']
tableFragments['dat24hr'] = ['header']
tableFragments['dat1min'] = ['header']
tableFragments['public15'] = ['header']
tableFragments['emc_vals'] = ['header']
tableFragments['dat10min'] = ['header']
tableFragments['CSAT3BMonitorData'] = ['header']
tableFragments['CSAT3BSonicData'] = ['header']
tableFragments['DataStats'] = ['header']
tableFragments['DataWindVec'] = ['header']
tableFragments['opsMonitor'] = ['header']
tableFragments['csat'] = []

sections2 = ['subroutines', 'program', 'scan']
fragments['subroutines'] = ['header']
fragments['program'] = ['header']
fragments['scan'] = ['header']
sections3 = ['slow', 'end']
fragments['slow'] = ['header', 'footer']
fragments['end'] = ['footer']

# Add parts provided as arguments into lists of fragments.
for section in sections1:
    if 'header' in fragments[section]:
        fragments[section][1:1] = parts
    else: 
        fragments[section][0:0] = parts

for table in tablesAll:
    if table in tables:
        if 'header' in tableFragments[table]:
            tableFragments[table][1:1] = parts
        else: 
            tableFragments[table][0:0] = parts

for section in sections2:
    if 'header' in fragments[section]:
        fragments[section][1:1] = parts
    else: 
        fragments[section][0:0] = parts

for section in sections3:
    if 'header' in fragments[section]:
        fragments[section][1:1] = parts
    else: 
        fragments[section][0:0] = parts

# ===============
# Build the code.
# ===============
print('\nBuilding code file:', codeFile, '\n')
with open(codeFile, 'w') as codeOut:

    # ----------------------------------
    # Insert date of this code assembly.
    # ----------------------------------
    now = datetime.datetime.now()
    codeOut.write('\' Built with assemble.py: ' + now.strftime('%Y-%m-%d %H:%M') + '\n')
    call = ' '.join(sys.argv)
    codeOut.write('\' ' + call)
    # -------------
    # Top sections.
    # -------------
    for section in sections1:
        print('Section:', section)
        if verbosity >= 1:
            comment = ('\n\'=================\n' + '\'' + section.upper() + 
                       '\n' + '\'=================\n')
            codeOut.write(comment)
        codeOut.write('\n')    
        if len(fragments[section]) > 0:
            for fragment in fragments[section]:
                fname = 'sections/' + section + '/' + fragment + '.txt'
                if not os.path.isfile(fname):
                    continue  # No file found, skip to next fragment.
                print('   Fragment:', fragment)
                if verbosity >= 1:
                    comment = ('\'--------------\n' + '\'' + fragment + '\n' +
                               '\'--------------\n')
                    codeOut.write(comment)
                if section != 'instruments':  # Don't put blank lines in the instrument list.
                    codeOut.write('\n')    
                with open(fname, 'r') as fragmentFile:
                    fragmentText = fragmentFile.read()
                    codeOut.write(fragmentText)
    if sequential:
        print('Sequential mode')
        if verbosity >= 1:
            comment = ('\'--------------\n' + '\'' + 'SequentialMode' + '\n' +
                       '\'--------------\n')
            codeOut.write('\n')    
            codeOut.write(comment)
        codeOut.write('SequentialMode\n')
    elif pipeline:
        print('Pipeline mode')
        if verbosity >= 1:
            comment = ('\'--------------\n' + '\'' + 'PipelineMode' + '\n' +
                       '\'--------------\n')
            codeOut.write(comment)
        codeOut.write('\n')    
        codeOut.write('PipelineMode\n')

    # Optionally insert AngleDegrees statement.
    if args.angledegrees:
        if verbosity >= 1:
            comment = ('\'--------------\n' + '\'' + 'AngleDegrees' + '\n' +
                       '\'--------------\n')
            codeOut.write(comment)
        codeOut.write('\n')    
        codeOut.write('AngleDegrees\n')
        
    # -------------
    # Data tables.
    # -------------
    print('Section: tables')
    if verbosity >= 1:
        comment = ('\n\'=================\n' + '\'' + 'TABLES' + 
                   '\n' + '\'=================\n')
        codeOut.write(comment)
    # Add header for data tables section.
    fname = 'sections/tables/header.txt'
    with open(fname, 'r') as fragmentFile:
        fragmentText = fragmentFile.read()
        codeOut.write('\n')    
        codeOut.write(fragmentText)
    # Insert tables.
    for table in tablesAll:
        if table in tables:
            print('   Table:', table)
            if len(tableFragments[table]) > 0:
                for tableFragment in tableFragments[table]:
                    fname = 'sections/tables/' + table + '/' + tableFragment + '.txt'
                    if not os.path.isfile(fname):
                        continue  # No file found, skip to next fragment.
                    print('      Table Fragment:', tableFragment)
                    if verbosity >= 1:
                        comment = ('\'--------------\n' + '\'' + tableFragment + '\n' +
                                   '\'--------------\n')
                        if tableFragment != 'header':
                            codeOut.write(comment)
                    with open(fname, 'r') as fragmentFile:
                        fragmentText = fragmentFile.read()
                        codeOut.write('\n')    
                        codeOut.write(fragmentText)
                codeOut.write('EndTable\n')

    # ----------------
    # Bottom sections.
    # ----------------
    for section in sections2:
        print('Section:', section)
        if verbosity >= 1:
            comment = ('\n\'=================\n' + '\'' + section.upper() + 
                       '\n' + '\'=================\n')
            codeOut.write(comment)
        if len(fragments[section]) > 0:
            for fragment in fragments[section]:
                fname = 'sections/' + section + '/' + fragment + '.txt'
                if not os.path.isfile(fname):
                    continue  # No file found, skip to next fragment.
                print('   Fragment:', fragment)
                if verbosity >= 1:
                    comment = ('\'--------------\n' + '\'' + fragment + '\n' +
                               '\'--------------\n')
                    codeOut.write(comment)
                with open(fname, 'r') as fragmentFile:
                    fragmentText = fragmentFile.read()
                    codeOut.write('\n')    
                    codeOut.write(fragmentText)
    # --------------------------------------------
    # Call each table at the end of the main loop.
    # --------------------------------------------
    print('Table calls')
    comment = ('\n\' =================\n' + '\'' + ' Table calls' + 
               '\n' + '\' =================\n')
    codeOut.write(comment)
    codeOut.write('\n')    
    for table in tables:
        callTable = '    CallTable ' + table + '\n'
        codeOut.write(callTable)
    # --------------------
    # End of main section.
    # --------------------
    for section in sections3:
        print('Section:', section)
        if verbosity >= 1:
            comment = ('\n\'=================\n' + '\'' + section.upper() + 
                       '\n' + '\'=================\n')
            codeOut.write(comment)
        if len(fragments[section]) > 0:
            codeOut.write('\n')    
            for fragment in fragments[section]:
                fname = 'sections/' + section + '/' + fragment + '.txt'
                if not os.path.isfile(fname):
                    continue  # No file found, skip to next fragment.
                print('   Fragment:', fragment)
                if verbosity >= 1:
                    comment = ('\'--------------\n' + '\'' + fragment + '\n' +
                               '\'--------------\n')
                    codeOut.write(comment)
                with open(fname, 'r') as fragmentFile:
                    fragmentText = fragmentFile.read()
                    codeOut.write(fragmentText)
print('\nWrote file:', codeFile)

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
