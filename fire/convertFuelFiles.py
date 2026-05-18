import sys
import scipy.stats
from datetime import datetime, timedelta

fuelFiles = sys.argv[1:]

# Read data.
for fuelFile in fuelFiles:
    print('\n==================================')
    print('Reading file:', fuelFile)
    print('==================================')
    nLines = 0
    column = {}
    with open (fuelFile, 'r') as ff:
        csvFile = fuelFile + '.csv'
        csvOut = open(csvFile, 'w')
        for line in ff:
            nLines += 1
            lineParts = line.split()
            for part in lineParts:
                col = int(part[0:2])
                value = float(part[2:])
                if col == 2:
                    # Year.
                    year = int(part[3:7])
                elif col == 3:
                    # Day of year.
                    doy = int(value)
                elif col == 4:
                    # Time.
                    if part[3:] == '0.000':
                        hr = 0
                        min = 0
                    else:
                        hr = int(part[3:5])
                        min = int(part[5:7])
                elif col == 6:
                    # 1 hr fuel moisture.
                    fm1hr = value
                elif col == 8:
                    # 10 hr fuel moisture.
                    fm10hr = value
            # Construct datetime.
            dt = datetime(year, 1, 1, hr, min) + timedelta(days=doy-1)
            # Write desired columns to csv file.
            csvOut.write(','.join([str(dt), str(fm1hr), str(fm10hr)]) + '\n')
    csvOut.close()

                    
