"""
New calculation of absolute humidity.
Ken Waight / October 2021
"""

import math

# Constants.
MW = 0.018015  # Molecular weight of water, kg/mol
R = 8.314  # Universal gas constant, J/mol-K

# Banner.
print('========================================================')
print('Calculate absolute humidity from T and RH.')
print('========================================================')
# Test range of temperatures and RH's.
tC = input('\nEnter temperature in deg C: ')
rh = input('Enter relative humidity in %: ')

# Calculate absolute humidity (vapor density).
tK = float(tC) + 273.15
es = 611.2*math.exp((17.67*float(tC))/(float(tC)+243.5))
e = 0.01*float(rh) * es
absHum = 1000.0 * (MW*e) / (R*tK)
print('\nAbsolute humidity = {:.2f} g/m3'.format(absHum))
