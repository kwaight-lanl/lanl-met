import sys
import scipy.stats

fuelFiles = sys.argv[1:]

# Read data.
for fuelFile in fuelFiles:
    print('\n==================================')
    print('Reading file:', fuelFile)
    print('==================================')
    nLines = 0
    column = {}
    with open (fuelFile, 'r') as ff:
        for line in ff:
            nLines += 1
            lineParts = line.split()
            for part in lineParts:
                col = int(part[0:2])
                value = float(part[2:])
                try:
                    column[col].append(value)
                except:
                    column[col] = [value]
    # Summarize data found.
    print('\nSummary')
    print('Lines of data:', nLines)
    for c in column.keys():
        print('Column:', c)
        print(scipy.stats.describe(column[c]))

                    
