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
compareStars.py
Read two STAR files for CAP88 input, compare them and print info to show how similar they are.
Ken Waight / March 2020
"""

# ----------
# Constants.
# ----------
VERBOSE = True  # Print extra diagnostic information or not.
WIND_DIR_BIN_DIAG = 'S'  # Print diagnostic information for this combination of wind dir, stability and wind speed.
STABILITY_CLASS_DIAG = 'E'
WIND_SPEED_BIN_DIAG = '3'

# --------------------------------------------------
# Wind speed and direction bins, stability classes.
# --------------------------------------------------
windDirections = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
windSpeeds = ['1', '2', '3', '4', '5', '6']
stabilityClasses = ['A', 'B', 'C', 'D', 'E', 'F']

# ----------------------------------------
# Get names of files to compare.
# ----------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("starfile1", help="first STAR file to compare")
parser.add_argument("starfile2", help="second STAR file to compare")
args = parser.parse_args()
starFiles = []
starFiles.append(args.starfile1)
starFiles.append(args.starfile2)

# ----------------------------
# Name of the difference file.
# ----------------------------
differenceFile = 'star-differences.dat'

# =======
# Banner.
# =======
print(' =====================================\n',
      'Compare two CAP88 STAR files\n',
      '=====================================\n')

# ---------------------------------------------------------------------------------------------
# Read two STAR files.
# ---------------------------------------------------------------------------------------------
frequency = []
for nFile, starFile in enumerate(starFiles):
    print('\nReading from STAR file:', starFile)
    frequency.append({})
    with open(starFile, 'r') as star:
        for stability in stabilityClasses:
            frequency[nFile][stability] = {}
            for windDirection in windDirections:
                frequency[nFile][stability][windDirection] = {}
                line = star.readline()
                nStart = 7
                for windSpeed in windSpeeds:
                    frequency[nFile][stability][windDirection][windSpeed] = float(line[nStart:nStart+6])
                    nStart += 7

# --------------------------------------------
# Summarize the characteristics of both files.
# --------------------------------------------
print('Summarize the frequencies in both files:')
frequencyAverages = [0.0, 0.0]
fracStability = {}
fracWindDirection = {}
fracWindSpeed = {}
for stability in stabilityClasses:
    fracStability[stability] = []
for windDirection in windDirections:
    fracWindDirection[windDirection] = []
for windSpeed in windSpeeds:
    fracWindSpeed[windSpeed] = []
for nFile, starFile in enumerate(starFiles):
    print('\n   ', starFile)
    nNonZero = 0
    nStability = {}
    nWindDirection = {}
    nWindSpeed = {}
    frequencyTotal = 0.0
    for stability in stabilityClasses:
        for windDirection in windDirections:
            for windSpeed in windSpeeds:
                # Sum nonzero frequencies.
                if frequency[nFile][stability][windDirection][windSpeed] != 0.0:
                    nNonZero += 1
                    frequencyTotal += frequency[nFile][stability][windDirection][windSpeed]
                # Distribution of stability classes.
                nStability[stability] = (nStability.get(stability, 0)
                                         + frequency[nFile][stability][windDirection][windSpeed])
                # Distribution of wind directions.
                nWindDirection[windDirection] = (nWindDirection.get(windDirection, 0)
                                               + frequency[nFile][stability][windDirection][windSpeed])
                # Distribution of wind speeds.
                nWindSpeed[windSpeed] = (nWindSpeed.get(windSpeed, 0)
                                         + frequency[nFile][stability][windDirection][windSpeed])

    frequencyAverage = frequencyTotal / float(nNonZero)
    print('       Sum of all frequencies:', frequencyTotal)
    print('       Average nonzero frequency:', frequencyAverage)
    print('       Distribution of stability classes:')
    for stability in stabilityClasses:
        fracStability[stability].append(100.0 * nStability.get(stability, 0))
        print('         {:1} {:5.1f}%'.format(stability, fracStability[stability][nFile]))
    print('       Distribution of wind directions:')
    for windDirection in windDirections:
        fracWindDirection[windDirection].append(100.0 * nWindDirection.get(windDirection, 0))
        print('         {:3} {:5.1f}%'.format(windDirection, fracWindDirection[windDirection][nFile]))
    print('       Distribution of wind speeds:')
    for windSpeed in windSpeeds:
        fracWindSpeed[windSpeed].append(100.0 * nWindSpeed.get(windSpeed, 0))
        print('         {:1} {:5.1f}%'.format(windSpeed, fracWindSpeed[windSpeed][nFile]))
    frequencyAverages[nFile] = frequencyAverage

# -----------------------
# Calculate differences.
# -----------------------
print('\n=====================================================================================')
print('\nCalculating differences . .')
difference = {}
sumDifferences = 0.0
sumAbsDifferences = 0.0
sumSquaredDifferences = 0.0
for stability in stabilityClasses:
    difference[stability] = {}
    for windDirection in windDirections:
        difference[stability][windDirection] = {}
        for windSpeed in windSpeeds:
            difference[stability][windDirection][windSpeed] = (
                frequency[1][stability][windDirection][windSpeed]
                - frequency[0][stability][windDirection][windSpeed])
            sumDifferences += difference[stability][windDirection][windSpeed]
            sumAbsDifferences += abs(difference[stability][windDirection][windSpeed])
            sumSquaredDifferences += (difference[stability][windDirection][windSpeed]
                                      * difference[stability][windDirection][windSpeed])
            if (VERBOSE
                and stability == STABILITY_CLASS_DIAG
                and windDirection == WIND_DIR_BIN_DIAG
                and windSpeed == WIND_SPEED_BIN_DIAG):
                print('At diagnostic point', windDirection, stability, windSpeed, 'values are:',
                      frequency[0][stability][windDirection][windSpeed],
                      frequency[1][stability][windDirection][windSpeed],
                      ', difference is:',
                      difference[stability][windDirection][windSpeed])
                #if (difference[stability][windDirection][windSpeed] != 0.0):
                #    print(frequency[0][stability][windDirection][windSpeed],
                #          frequency[1][stability][windDirection][windSpeed],
                #          difference[stability][windDirection][windSpeed])

# ----------------------------------
# Show differences in distributions.
# ----------------------------------
print('\nDistribution differences:')
print('       Distribution of stability classes:')
for stability in stabilityClasses:
    diffFrac = fracStability[stability][1] - fracStability[stability][0]
    print('         {:1} {:5.1f}%'.format(stability, diffFrac))
print('       Distribution of wind directions:')
for windDirection in windDirections:
    diffFrac = fracWindDirection[windDirection][1] - fracWindDirection[windDirection][0]
    print('         {:3} {:5.1f}%'.format(windDirection, diffFrac))
print('       Distribution of wind speeds:')
for windSpeed in windSpeeds:
    diffFrac = fracWindSpeed[windSpeed][1] - fracWindSpeed[windSpeed][0]
    print('         {:1} {:5.1f}%'.format(windSpeed, diffFrac))

# -----------------------
# Summarize differences.
# -----------------------
print('\nSummary of differences:')
nTotal = 0
nZeros = 0
nDifferent = 0
nIdentical = 0
nPositive = 0
nNegative = 0
largestAbsolute = -999.0
largestPositive = -999.0
largestNegative = 999.0
for stability in stabilityClasses:
    for windDirection in windDirections:
        for windSpeed in windSpeeds:
            nTotal += 1
            if (frequency[0][stability][windDirection][windSpeed] == 0.0
                and frequency[1][stability][windDirection][windSpeed] == 0.0):
                nZeros += 1
            elif (frequency[0][stability][windDirection][windSpeed]
                  != frequency[1][stability][windDirection][windSpeed]):
                nDifferent += 1
            else:
                nIdentical += 1
            if difference[stability][windDirection][windSpeed] > 0.0:
                nPositive += 1
            elif difference[stability][windDirection][windSpeed] < 0.0:
                nNegative += 1
            if abs(difference[stability][windDirection][windSpeed]) > largestAbsolute:
                largestAbsolute = abs(difference[stability][windDirection][windSpeed])
                stabilityLargest = stability
                windDirectionLargest = windDirection
                windSpeedLargest = windSpeed
            if difference[stability][windDirection][windSpeed] > largestPositive:
                largestPositive = difference[stability][windDirection][windSpeed]
            if difference[stability][windDirection][windSpeed] < largestNegative:
                largestNegative = difference[stability][windDirection][windSpeed]
fracDifferent = 100.0 * nDifferent/nTotal
fracIdentical = 100.0 * nIdentical/nTotal
fracZeros = 100.0 * nZeros/nTotal
fracPositive = 100.0 * nPositive/nTotal
fracNegative = 100.0 * nNegative/nTotal
frequencyAveragePctChange = 100.0 * (frequencyAverages[1]-frequencyAverages[0])/frequencyAverages[0]
meanDifference = sumDifferences / float(nTotal)
meanAbsDifference = sumAbsDifferences / float(nTotal)
rootMeanSquaredDifference = math.sqrt(sumSquaredDifferences/float(nTotal))

print('Total number of data values:', nTotal)
print('Values are different:', nDifferent, ', {:.2f}% of total'.format(fracDifferent))
print('Nonzero values are identical:', nIdentical, ', {:.2f}% of total'.format(fracIdentical))
print('Both frequencies are zero:', nZeros, ', {:.2f}% of total'.format(fracZeros))
print('Positive differences:', nPositive, ', {:.2f}% of total'.format(fracPositive))
print('Negative differences:', nNegative, ', {:.2f}% of total'.format(fracNegative))
print('Largest absolute difference:', largestAbsolute, 'at:',
      windDirectionLargest, stabilityLargest, windSpeedLargest)
print('Largest positive difference:', largestPositive)
print('Largest negative difference:', largestNegative)
print('Difference in average nonzero frequency:', frequencyAverages[1], '-', frequencyAverages[0],
      '=', frequencyAverages[1]-frequencyAverages[0])
print('Percent change of average nonzero frequency:', frequencyAveragePctChange, '%')
print('Mean difference: {:.2f}%'.format(100.0*meanDifference))
print('Mean absolute difference: {:.2f}%'.format(100.0*meanAbsDifference))
print('Root mean square difference: {:.2f}%'.format(100.0*rootMeanSquaredDifference))

# ---------------------------------------------------------------------------------------------
# Write difference file in STAR format.
# ---------------------------------------------------------------------------------------------
print('\nWriting to difference STAR file:', differenceFile)
with open(differenceFile, 'w') as star:
    for stability in stabilityClasses:
        for windDirection in windDirections:
            star.write('{:3} {:1} '.format(windDirection, stability))
            for windSpeed in windSpeeds:
                star.write('{:7.5f}'.format(difference[stability][windDirection][windSpeed]))
            star.write('\n')

# ----
# End.
# ----
print('\n', sys.argv[0], 'completed.')
sys.exit()
