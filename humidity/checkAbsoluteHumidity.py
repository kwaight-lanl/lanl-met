"""
Test new calculation of absolute humidity against incorrect one.
Ken Waight / October 2021
"""

import math

# Constants.
MW = 0.018015  # Molecular weight of water, kg/mol
R = 8.314  # Universal gas constant, J/mol-K
RD = 287.05
RV = 461.51
L = 2501000.0

# Banner.
print('========================================================')
print('Compare new calculation of absolute humidity to old one.')
print('========================================================')
# Test range of temperatures and RH's.
print('\nNew and old absolute humidities (vapor densities) in g/m3.')
tCs = range(-30, 45, 5)
rhs = range(10, 110, 10)
print('T(C) RH(%) new   old   %diff')
print('---  ---   ----- ----- -----')
eps = RD / RV
for tC in tCs:
    for rh in rhs:
        tK = float(tC) + 273.15
        # New corrected calculation.
        es = 611.2*math.exp((17.67*float(tC))/(float(tC)+243.5))
        e = 0.01*float(rh) * es
        absHumNew = 1000.0 * (MW*e) / (R*tK)
        # Old calculation.
        es = 611.0*math.exp((L*MW/R)*((1.0/273.0)-(1.0/tK)))
        e = 0.01*float(rh) * es
        q = e * eps
        rho = 1.0 / (RD*tK)
        absHumOld = rho * q * 1000.0
        # % Difference.
        diffPct = 100.0 * ((absHumOld-absHumNew)/absHumNew)
        # Show results.
        print('{:3d}  {:3d}   {:5.2f} {:5.2f} {:4.1f}'.format(
            tC, rh, absHumNew, absHumOld, diffPct))
print('---  ---   ----- ----- -----')
print('T(C) RH(%) new   old   %diff')
