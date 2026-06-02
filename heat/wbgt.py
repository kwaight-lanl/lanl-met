# Module for calculation of wet bulb globe temperature (WBGT).
# Following Liljegren, J.C., R.A. Carhart, P. Lawday, S. Tschopp and 
#   R. Sharp: 2008: Modeling the wet bulb globe temperature using standard 
#   meteorological measurements. J. Occup. Env. Hygiene, 5, 645-655.
# Ken Waight / May 2025

import sys
from datetime import datetime
import math

# Constants needed.
# Local.
T0 = 273.16  # Freezing point, K.
R = 287.05  # Specific gas constant for dry air, J/mol-K
CP = 1005.0  # Specific heat of dry air at constant pressure.
MW = 0.018015  # Molecular weight of water, kg/mol
MAIR = 0.028964  # Molecular weight of dry air, kg/mol
MWATER = 0.018015  # Molecular weight of water, kg/mol
LHV = 2.501E06  # Latent heat of vaporization, J/kg

# From utils.py.
SB = 5.67e-08  # Stefan-Boltzmann constant, W/(m2K4).
I0 = 1376.  # Solar irradiance at top of atmosphere, W/m2.
P0 = 101325.  # Mean sea level pressure, Pa.
RAD_DEG = 180. / math.pi  # Convert radians to degrees.
DEG_RAD = math.pi / 180.  # Convert degrees to radians.
HIGH_WIND_SPEED_THRESH = 8.745  # 8.745 m/s, lower bound of Beaufort Force 5 (17 kt).
CLOUD_FRAC_OVERCAST_THRESH = 0.75  # Cloud fraction of "broken".
LOW_VISIBILITY_THRESH = 4828.0  # 4828 m = 3 mi, definition of IFR.

# Additional constants needed for Liljegren calculations.
EMIS_WICK = 0.95  # Emissivity of the wick, from Liljegren.
ALBEDO_WICK = 0.4  # Albedo of the wick, from Liljegren.
ALBEDO_SFC = 0.45  # Surface albedo assumption, from Liljegren.
ALBEDO_GLOBE = 0.05  # Albedo of globe.
EMIS_GLOBE = 0.95  # Emissivity of globe.
DIAM_GLOBE = 0.0508  # Diameter of globe from Liljegren, 50.8 mm.
EMIS_SFC = 0.999  # From Liljegren.
DIAM_WICK = .007  # Diameter of the wick, from Liljegren.
LENGTH_WICK = .0254  # Length of the wick, from Liljegren.
SIGMA_MU = 3.617
EPS_KAPPA = 97.0
P_CRIT_AIR = 36.4
P_CRIT_WATER = 218.0
T_CRIT_AIR = 132.0
T_CRIT_WATER = 647.3
A_DIFF = 3.64E-04
B_DIFF = 2.334
A_NUSS = 0.56
B_NUSS = 0.281
C_NUSS = 0.4

# Parameters with an assumed value, but which could be changed.
emisSfc = 0.9  # Longwave emissivity of surface.
skyViewFactor = 1.  # Assume no obstructions.
emisHuman = 0.97  # Longwave emissivity of human 
absHuman = 0.7  # Shortwave absorptivity of human
bowen = 1.  #ktw: Need to check this.
albedoSfc = 0.2  #ktw: Need to check this.
nIterTsfcMax = 10  # Max Tsfc iterations.
diffTsfcSmall = 0.1  # Close enough for Tsfc iterations, K.
solarZenithSunrise = 90.833  # Definition of sunrise/sunset, top of sun is at horizon.

def calc_frac_hour(dt):
    """
    Calculate the fractional hour of the day.
    """
    hr = float(dt.strftime('%H'))
    mn = float(dt.strftime('%M'))
    sec = float(dt.strftime('%S'))
    hrFrac = hr + mn/60. + sec/3600.
    return hrFrac


def calc_irradiances(latitude, longitude, dt,
                     T2m, e2m, wspd10m, pSfc, cloudFrac,
                     swdn, swup, lwdn, lwup,
                     verbosity):
    """
    Calculate all solar and longwave irradiances.
    Ken Waight / September 2020
    """
    # Calculate solar information.
    (solarZenith, cosZenith, solarElevation, dayofyear) = calc_solar_params(latitude, longitude, dt,
                                                                            pSfc)

    # Calculate solar downward irradiance.
    (solarDownDirect, solarDownDiffuse, 
     solarDownGlobal, solarDownGlobalClear, solarDownGlobalOvercast,
     cloudFrac) = calc_solar_down(dt, pSfc,
                                  cloudFrac, swdn,
                                  solarZenith, cosZenith, solarElevation,
                                  verbosity)

    # Calculate solar upward irradiance.
    solarUp = calc_solar_up(solarDownGlobal, solarDownGlobalClear, solarDownGlobalOvercast,
                            swup,
                            verbosity)

    # Calculate longwave downward irradiance.
    (longwaveDown, longwaveDownClear, longwaveDownOvercast) = calc_longwave_down(T2m, e2m, cloudFrac,
                                                                                 lwdn,
                                                                                 verbosity)

    # Calculate longwave upward irradiance.
    longwaveUp = calc_longwave_up(longwaveDown, solarDownGlobal,
                                  longwaveDownClear, solarDownGlobalClear,
                                  longwaveDownOvercast, solarDownGlobalOvercast,
                                  T2m, wspd10m,lwup,
                                  verbosity)

    return (solarZenith, solarElevation, cosZenith, dayofyear, 
            solarDownGlobal, solarDownDirect, solarDownDiffuse, solarUp,
            longwaveDown, longwaveUp,
            cloudFrac) 


def calc_solar_params(latitude, longitude, dt,
                      pSfc):
    """
    Calculate the solar declination angle, hour angle and
    zenith angle for a given location, date and time.
    Ken Waight / February 2017

        Equation of time (minutes), corrects for eccentricity of 
          earth's orbit and earth's axial, and declination
          angle. From Williams via Wikipedia: 
          http://www.green-life-innovators.org/tiki-index.php?page=
            The+Latitude+and+Longitude+of+the+Sun+by+David+Williams
    """
    dayofyear = float(dt.strftime('%j'))
    w         = 360. / 365.24
    a         = w * ((dayofyear-1.)+10.)
    b         = a + (360./math.pi)*.0167*math.sin(DEG_RAD*w*
                                                  ((dayofyear-1.)-2.))
    c         = ((a-RAD_DEG*math.atan(math.tan(DEG_RAD*b) /
                                      math.cos(DEG_RAD*23.44)))/180.)
    eot       = 720. * (c-round(c))
    solarDeclination = (RAD_DEG *
                        -math.asin(math.sin(DEG_RAD*23.44)*
                                   math.cos(DEG_RAD*b)))

    # Calculate local solar time and hour angle.
    # Local standard time meridian.
    lstm   = 15. * (round(longitude/15.))

    # Time correction factor, accounts for variation of solar time
    #   within a time zone and also the equation of time above.
    tc     = 4.*(longitude-lstm) + eot

    # Local solar time.
    hrfrac_utc = calc_frac_hour(dt)
    soltim     = hrfrac_utc + lstm/15. + tc/60.
    if soltim < 0.:
        soltim += 24.
    elif soltim > 24.:
        soltim -= 24.

    # Hour angle.
    solarHour = 15.*(soltim-12.)

    # Calculate the zenith angle.
    cosZenith = (math.sin(DEG_RAD*latitude)*
                 math.sin(DEG_RAD*solarDeclination) +
                 math.cos(DEG_RAD*latitude)*
                 math.cos(DEG_RAD*solarDeclination)*
                 math.cos(DEG_RAD*solarHour))
    cosZenith = max (cosZenith,-1.)
    cosZenith = min (cosZenith, 1.)

    # Zenith angle.
    solarZenith = RAD_DEG * math.acos(cosZenith)

    # Elevation angle.
    solarElevation = 90.0 - solarZenith

    if solarZenith >= solarZenithSunrise:
        # Before sunrise or after sunset, so nighttime.
        daytime = False
    elif solarZenith >= 90.0:
        # Just after sunrise or before sunset, so it's daytime,
        #   but no solar irradiance.
        daytime = True
    else:
        # Zenith angle less than 90 deg, so daytime, continue.
        daytime = True

    # Return results.
    return solarZenith, cosZenith, solarElevation, dayofyear 


def calc_solar_down(dt, pSfc,
                    cloudFrac, swdn,
                    solarZenith, cosZenith, solarElevation,
                    verbosity):
    """
    Calculate a set of solar irradiances (W/m2), using the method 
      in Matzarakis et al. (2010).
    Ken Waight / February 2017
    Constants present in this class.
        I0            - solar constant (W/m2)
        P0            - Standard sea level pressure (Pa)
    Assumed to be present in this class.
        [cloudFrac - cloud fraction or 
         swdn - downward solar, will override calculated value]
        dt      - Date/time object
    Assumes that calc_solar_params has already been called.
    Provided or calculated here:
        tL            - Linke turbidity factor
        airmass       - relative optical air mass
        pSfc          - surface pressure (Pa)
    Output:
        solarDownDirect
           - direct solar irradiance (W/m2) with given cloud amount
        solarDownDiffuse
           - clear sky diffuse solar irradiance (W/m2) with given 
             cloud amount
        solarDownGlobal
           - global solar irradiance (W/m2) with given 
             cloud amount
        solarDownDirectClear
           - clear sky direct solar irradiance (W/m2)
        solarDownDiffuseClear
           - clear sky diffuse solar irradiance (W/m2)
        solarDownGlobalClear
           - clear sky global solar irradiance (W/m2)
        solarDownDiffuseOvercast
           - overcast diffuse solar irradiance (W/m2)
        solarDownGlobalOvercast
           - overcast global solar irradiance (W/m2)
    """
    if solarZenith >= solarZenithSunrise:
        # Before sunrise or after sunset, so nighttime.
        solarDownGlobal       = 0.
        solarDownDirect       = 0.
        solarDownDiffuse      = 0.
        solarDownGlobalClear  = 0.
        solarDownDirectClear  = 0.
        solarDownDiffuseClear = 0.
        solarDownDiffuseOvercast = 0.
        solarDownGlobalOvercast = 0.
        cloudFrac = 0.0  # Assume no clouds for night, since WBGT probably isn't relevant anyway.
        daytime = False
        return (solarDownDirect, solarDownDiffuse,
                solarDownGlobal, solarDownGlobalClear, solarDownGlobalOvercast,
                cloudFrac)
    elif solarZenith >= 90.0:
        # Just after sunrise or before sunset, so it's daytime,
        #   but no solar irradiance.
        solarDownGlobal       = 0.
        solarDownDirect       = 0.
        solarDownDiffuse      = 0.
        solarDownGlobalClear  = 0.
        solarDownDirectClear  = 0.
        solarDownDiffuseClear = 0.
        solarDownDiffuseOvercast = 0.
        solarDownGlobalOvercast = 0.
        cloudFrac = 0.0  # Assume no clouds for night, since WBGT probably isn't relevant anyway.
        daytime = True
        return (solarDownDirect, solarDownDiffuse,
                solarDownGlobal, solarDownGlobalClear, solarDownGlobalOvercast,
                cloudFrac)
    else:
        # Zenith angle less than 90 deg, so daytime, continue.
        daytime = True

    # Monthly Linke turbidity factors from two locations: northeast
    #  U.S. and Kasten, Germany.
    TL_NEUS   = [1.9, 2.1, 2.5, 3.2, 3.9, 5.1, 5.9, 4.4, 
                 3.0, 2.4, 2.1, 2.0]
    TL_KASTEN = [3.8, 4.2, 4.8, 5.2, 5.4, 6.4, 6.3, 6.1,
                 5.5, 4.3, 3.7, 3.6]

    # Determine the Linke turbidity factor.
    # For now, we'll use the NE US turbidity factor data.
    month = int(dt.strftime('%m'))
    tL    = TL_NEUS[month-1] 

    # Calculate the clear sky global irradiance.
    solarDownGlobalClear = (0.84 * I0 * cosZenith *
                                 math.exp(-.027*(pSfc/P0)*
                                          (tL/cosZenith)))

    if (cloudFrac is not None and swdn is None):
        # Use the provided cloud fraction to estimate solarDownGlobal, etc.
        pass
    elif (cloudFrac is None and swdn is not None):
        # Estimate the cloud fraction from the observed swdn and
        #   the calculated global clear for this location and time.
        cloudFrac = 1.0 - (swdn/solarDownGlobalClear)
        cloudFrac = max(cloudFrac, 0.0)
        cloudFrac = min(cloudFrac, 1.0)
    elif (cloudFrac is not None and swdn is not None):
        # # Use the provided cloud fraction and swdn.
        pass
    else:
        print('ERROR: Must have either cloud fraction or downward solar irradiance',
              'to estimate the other!')
        sys.exit(1)

    # Calculate the airmass.
    airmass = 1. / (cosZenith+0.50572*
                    (6.07995+(solarElevation))**-1.6364)

    # Calculate the vertical optical thickness of the standard
    #   (Rayleigh) atmosphere.
    if solarZenith < 85.:
        vot = 1. / (0.9*airmass + 9.4)
    else:
        if solarZenith >= 89.0:
            vot = .0027*(90.0-solarZenith) + .0435
        elif solarZenith >= 88.:
            vot = .0028*(89.0-solarZenith) + .0463
        elif solarZenith >= 87.:
            vot = .0028*(88.0-solarZenith) + .0491
        elif solarZenith >= 86.:
            vot = .0028*(87.0-solarZenith) + .0519
        elif solarZenith >= 85.:
            vot = .0029*(86.0-solarZenith) + .0548

    # Calculate clear sky direct irradiance
    solarDownDirectClear = (I0 * cosZenith * 
                                 math.exp(-tL*vot*airmass*
                                          (pSfc/P0)))

    solarDownDirect = ((1.0-cloudFrac) *
                           solarDownDirectClear)

    # Calculate clear sky diffuse irradiance.
    transmittance = (solarDownDirectClear /
                     (cosZenith*I0))
    dIso = ((solarDownGlobalClear-
             solarDownDirectClear) *
            (1.-transmittance)*skyViewFactor)
    dAniso = ((solarDownGlobalClear-
               solarDownDirectClear) *
              transmittance)
    solarDownDiffuseClear = dIso + dAniso

    # Calculate overcast diffuse irradiance.
    solarDownDiffuseOvercast = (0.28 * solarDownGlobalClear * 
                                skyViewFactor)

    # Calculate diffuse irradiance for the given cloud amount.
    solarDownDiffuse = ((1.-cloudFrac) *
                             solarDownDiffuseClear +
                             cloudFrac *
                             solarDownDiffuseOvercast)

    # Calculate global irradiances.
    solarDownGlobal = solarDownDirect + solarDownDiffuse
    solarDownGlobalCalculated = solarDownGlobal

    if swdn is not None:
        # Adjust solarDownDirect and Diffuse to produce the
        #   provided solarDownGlobal (swdn) value.
        if solarDownGlobalCalculated > 0.0:
            solarDownDirect *= swdn / solarDownGlobalCalculated
            solarDownDiffuse *= swdn / solarDownGlobalCalculated
        solarDownGlobal = swdn

    # Calculate overcast global irradiance.
    solarDownGlobalOvercast = solarDownDiffuseOvercast

    if verbosity > 1:
        print("\n Solar downward irradiances")
        print(" --------------------------------------------------")
        print(" Zenith angle                         : {:.2f} deg".format(solarZenith))
        print(" Cosine of zenith angle               : {:.2f}".format(cosZenith))
        print(" Surface pressure                     : {:.1f} Pa".format(pSfc))
        print(" Air mass                             : {:.2f}".format(airmass))
        print(" Cloud fraction                       : {:.2f}".format(cloudFrac))
        print(" Clear sky direct                     : {:.1f} W/m2".format(solarDownDirectClear))
        print(" Clear sky diffuse                    : {:.1f} W/m2".format(solarDownDiffuseClear))
        print(" Clear sky global                     : {:.1f} W/m2".format(solarDownGlobalClear))
        print(" Overcast diffuse                     : {:.1f} W/m2".format(solarDownDiffuseOvercast))
        print(" Overcast global                      : {:.1f} W/m2".format(solarDownGlobalOvercast))
        print(" Solar downward direct                : {:.1f} W/m2".format(solarDownDirect))
        print(" Solar downward diffuse               : {:.1f} W/m2".format(solarDownDiffuse))
        print(" Solar downward global, calculated    : {:.1f} W/m2".format(solarDownGlobalCalculated))
        print(" Solar downward global                : {:.1f} W/m2".format(solarDownGlobal))
        print(" Daytime?                             : {:}".format(daytime))


    return (solarDownDirect, solarDownDiffuse,
            solarDownGlobal, solarDownGlobalClear, solarDownGlobalOvercast,
            cloudFrac)


def calc_solar_up(solarDownGlobal, solarDownGlobalClear, solarDownGlobalOvercast,
                  swup,
                  verbosity):
    """
    Calculate the upward (reflected from the surface) solar
      irradiance (W/m2).
    Ken Waight / February 2017
    Constants present in this class.
    Assumes that calc_solar_down has already been called.
    Assumed to be present in this class.
        solarDownGlobal
           - global solar irradiance (W/m2) with given 
             cloud amount
        solarDownGlobalClear
           - clear sky global solar irradiance (W/m2)
        solarDownGlobalOvercast
           - overcast global solar irradiance (W/m2)
    Optionally provided:
        swup - upward solar, will override calculated value
    Output:
        solarUp 
           - solar upward irradiance (W/m2) with given cloud amount
    """
    # Calculate the solar upward irradiance with the given cloud
    #   amount.
    solarUp = albedoSfc * solarDownGlobal
    solarUpCalculated = solarUp

    if swup is not None:
        # Override the calculated value with the provided swup.
        solarUp = swup

    # Calculate the solar upward irradiance under clear skies.
    solarUpClear = albedoSfc * solarDownGlobalClear

    # Calculate the solar upward irradiance under overcast skies.
    solarUpOvercast = albedoSfc * solarDownGlobalOvercast

    if verbosity > 1:
        print("\n Solar upward irradiances")
        print(" --------------------------------------------------")
        print(" Surface solar albedo                   : {:.1f}".format(albedoSfc))
        print(" Solar upward clear sky                 : {:.1f} W/m2".format(solarUpClear))
        print(" Solar upward overcast                  : {:.1f} W/m2".format(solarUpOvercast))
        print(" Solar upward, calculated               : {:.1f} W/m2".format(solarUpCalculated))
        print(" Solar upward                           : {:.1f} W/m2".format(solarUp))

    return solarUp


def calc_longwave_down(T2m, e2m, cloudFrac,
                       lwdn,
                       verbosity):
    """
    Calculate a set of longwave irradiances (W/m2), using the method 
      in Matzarakis et al. (2010).
    Ken Waight / February 2017
    Constants present in this class.
    Assumed to be present in this class.
        T             - 2 m air temperature (C)
        e             - 2 m vapor pressure (Pa)
        cloudFrac     - cloud fraction
    Optionally provided:
        lwdn - downward longwave, will override calculated value
    Output:
        longwaveDown
           - longwave downward irradiance (W/m2) with given 
             cloud amount
    """
    # Calculate the longwave downward irradiance under clear skies.
    longwaveDownClear = (
        SB*(T2m*T2m*T2m*T2m) * 
        (0.82-0.25*(10.**(-.000945*e2m))) * 1.)

    # Calculate the longwave downward irradiance under overcast skies.
    longwaveDownOvercast = longwaveDownClear * 1.21

    # Calculate the longwave downward irradiance with the given cloud
    #   amount.
    longwaveDown = (longwaveDownClear *
                    (1. + 0.21*cloudFrac**2.5))
    longwaveDownCalculated = longwaveDown

    if lwdn is not None:
        # Override the calculated value with the provided lwdn.
        longwaveDown = lwdn
        

    if verbosity > 1:
        print("\n Longwave downward irradiances")
        print(" --------------------------------------------------")
        print(" 2 m Temperature                         : {:.1f} K".format(T2m))
        print(" 2 m water vapor pressure                : {:.1f} Pa".format(e2m))
        print(" Cloud fraction                          : {:.2f}".format(cloudFrac))
        print(" Longwave clear sky downward             : {:.1f} W/m2".format(longwaveDownClear))
        print(" Longwave overcast downward              : {:.1f} W/m2".format(longwaveDownOvercast))
        print(" Longwave downward, calculated:          : {:.1f} W/m2".format(longwaveDownCalculated))
        print(" Longwave downward                       : {:.1f} W/m2".format(longwaveDown))

    return longwaveDown, longwaveDownClear, longwaveDownOvercast


def calc_longwave_up(longwaveDown, solarDownGlobal,
                     longwaveDownClear, solarDownGlobalClear,
                     longwaveDownOvercast, solarDownGlobalOvercast,
                     T2m, wspd10m,
                     lwup,
                     verbosity):
    """
    Calculate the surface temperature (K) and upward longwave 
      irradiance (W/m2), using the method in Matzarakis et al. (2010).
    Ken Waight / February 2017
    Constants present in this class.
    Assumes that calc_solar_down has already been called.
    Assumes that calc_longwave_down has already been called.
    Assumed to be present in this class.
        T             - 2 m air temperature (C)
        wspd10m       - 10 m wind speed (m/s)
        bowen         - Bowen ratio
        solarDownGlobal
           - global solar irradiance (W/m2) with given 
             cloud amount
        solarDownGlobalClear
           - clear sky global solar irradiance (W/m2)
        solarDownGlobalOvercast
           - overcast global solar irradiance (W/m2)
        longwaveDown
           - longwave downward irradiance (W/m2) with given 
             cloud amount
        longwaveDownClear
           - longwave downward irradiance (W/m2) under a clear sky
        longwaveDownOvercast
           - longwave downward irradiance (W/m2) under an overcast sky
    Optionally provided:
        lwup - upward longwave, will override calculated value
    Output:
        longwaveUp
           - longwave upward irradiance (W/m2) with given 
             cloud amount
    """
    # Calculate longwave upward and Tsfc for given cloud amount.
    (Tsfc, longwaveUp) = (
        tsfcIterate(longwaveDown, solarDownGlobal,
                    T2m, wspd10m))

    # Calculate longwave upward and Tsfc under clear skies
    (TsfcClear, longwaveUpClear) = (
        tsfcIterate(longwaveDownClear, solarDownGlobalClear,
                    T2m, wspd10m))
    # Calculate longwave upward and Tsfc under overcast skies
    (TsfcOvercast, longwaveUpOvercast) = (
        tsfcIterate(longwaveDownOvercast, solarDownGlobalOvercast,
                    T2m, wspd10m))

    longwaveUpCalculated = longwaveUp

    if lwup is not None:
        # Override the calculated value with the provided swup.
        longwaveUp = lwup

    if verbosity > 1:
        print("\n Longwave upward irradiances")
        print(" --------------------------------------------------")
        print(" 2 m Temperature                        : {:.1f} K".format(T2m))
        print(" 10 m wind speed                        : {:.1f} m/s".format(wspd10m))
        print(" Surface longwave emissivity            : {:.2f}".format(emisSfc))
        print(" Surface solar albedo                   : {:.2f}".format(albedoSfc))
        print(" Surface temperature                    : {:.1f} K".format(Tsfc))
        print(" Surface temperature, clear             : {:.1f} K".format(TsfcClear))
        print(" Longwave clear sky upward              : {:.1f} W/m2".format(longwaveUpClear))
        print(" Surface temperature, overcast          : {:.1f} K".format(TsfcOvercast))
        print(" Longwave overcast upward               : {:.1f} W/m2".format(longwaveUpOvercast))
        print(" Longwave upward, calculated            : {:.1f} W/m2".format(longwaveUpCalculated))
        print(" Longwave upward                        : {:.1f} W/m2".format(longwaveUp))
    
    return longwaveUp


def calc_Tmrt(latitude, longitude, dt,
              T2m, e2m, pSfc, cloudFrac,
              solarZenith, solarElevation,
              longwaveDown, longwaveUp, 
              solarDownDirect, solarDownDiffuse, solarUp,
              verbosity):
    """
    Calculate the mean radiant temperature (K), using the method 
    in Matzarakis et al. (2010) and Weihs et al. (2012).
    Ken Waight / February 2017
    Constants:
        SB            - Stefan Boltzmann constant, W/(m2K4)
        absHuman      - absorption coefficient for shortwave radiation
                        of human body
        emisHuman    - longwave emissivity of human body 
     Present in this class, or a function will be called:
        solarDownDirect
           - direct solar irradiance (W/m2) with given cloud amount
        solarDownDiffuse
           - diffuse solar irradiance (W/m2) with given cloud amount
        solarUp
           - solar irradiance reflected upward from the surface (W/m2)
        longwaveDown 
           - downward longwave irradiance from the sky (W/m2) with
             given cloud amount
        longwaveUp 
           - upward longwave irradiance from the surface (W/m2)
    Provided or calculated here:
        fa            - fraction of sphere for upward and
                        downward fluxes
        fp            - fraction of direct solar intercepted by a human,
                        standing or walking
    Output:
        Tmrt          - mean radiant temperature (K) with given cloud
                        amount
    """
    # Calculate solar and longwave irradiances if necessary.
    if solarZenith is None:
        (solarZenith, solarElevation, cosZenith, dayofyear,
         solarDownGlobal, solarDownDirect, solarDownDiffuse, solarUp,
         longwaveDown, longwaveUp,
         cloudFrac) = calc_irradiances(latitude, longitude, dt,
                                       T2m, e2m, wspd10m, pSfc, cloudFrac,
                                       swdn, swup, lwdn, lwup,
                                       verbosity)
                                                                        
    # Fraction of total sphere taken up by sky/surface.
    fa = 0.5

    # Calculate the fraction of direct solar irradiance intercepted
    #   by a person standing or walking.
    elevationRad = DEG_RAD * solarElevation
    fp = 0.308 * math.cos(elevationRad*
                          (0.998-((solarElevation*solarElevation)/
                                  50000.)))

    # Calculate Tmrt.
    irradiances = (fa*longwaveDown + 
                   fa*longwaveUp   + 
                   (absHuman/emisHuman)*
                   (fp*solarDownDirect +
                    fa*solarDownDiffuse+
                    fa*solarUp))
    Tmrt = (irradiances/SB)**0.25

    if verbosity > 1:
        print("\n Calculation of Mean Radiant Temperature")
        print(" --------------------------------------------------")
        print(" Longwave down                          : {:.1f} W/m2".format(longwaveDown))
        print(" Longwave up                            : {:.1f} W/m2".format(longwaveUp))
        print(" Solar down direct                      : {:.1f} W/m2".format(solarDownDirect))
        print(" Solar down diffuse                     : {:.1f} W/m2".format(solarDownDiffuse))
        print(" Solar up                               : {:.1f} W/m2".format(solarUp))
        print(" Tmrt                                   : {:.1f} C".format(Tmrt-T0))
        
    return Tmrt


def tsfcIterate(ld, sdg,
                T2m, wspd10m):
    """
    Iterate to estimate Tsfc that is consistent with upward longwave 
      irradiance and a simplified surface energy budget equation, 
      equations 12 and 13 from Matzarakis et al. (2010).
    Ken Waight / February 2017
    """
    # Start by assuming that the surface temperature is the same as
    #   the 2 m air temperature.
    Tsfc      = T2m
    #print "Iterating to get Tsfc:\n"
    diff       = 999.
    nIter      = 0
    while (diff  > diffTsfcSmall and
           nIter < nIterTsfcMax):
        nIter += 1
        #print "   Iteration nIter: Tsfc = Tsfc\n"
        # Calculate upward longwave.
        E          = (emisSfc*SB*
                      Tsfc*Tsfc*Tsfc*Tsfc +     
                      (1.-emisSfc)*ld)
        # Calculate Tsfc from fluxes, etc.
        Q = albedoSfc*sdg + ld - E
        if Q >= 0:
            B = -0.19 * Q
        else:
            B = -0.32 * Q
        TsfcNew = (T2m + ((Q+B) /
                               ((6.2+4.26*wspd10m)*
                                (1.+(1./bowen)))))
        diff  = TsfcNew - Tsfc
        Tsfc = 0.5 * (Tsfc+TsfcNew)
    # End of iteration, accept the resulting Tsfc.
    return (Tsfc, E)


def Td2Rh(T, Td):
    """
    Given T and Td, calculate RH.
    Ken Waight / June 2021
    """
    e = T2es(Td)
    es = T2es(T)
    RH = e / es
    return RH


def Rh2Td(T, Rh):
    """
    Given T in deg K and RH in %, calculate Td in deg K.
    Use the August-Roche-Magnus formula, as given in Lawrence (2005):
      http://journals.ametsoc.org/doi/pdf/10.1175/BAMS-86-2-225
    Ken Waight / May 2026
    """
    A1 = 17.625
    B1 = 243.04 # deg C
    C1 = 610.94 # Pa
    RhOver100 = Rh / 100.0
    lnRhOver100 = math.log(Rh/100.0)
    numerator = B1*(lnRhOver100 + (A1*T/(B1+T)))
    denominator = A1 - lnRhOver100 - (A1*T/(B1+T))
    Td = numerator / denominator
    return Td


def T2es(T):
    """
    Calculate the saturation vapor pressure es (Pa) from 
      a given temperature (deg K).
    Use the August-Roche-Magnus formula, as given in Lawrence (2005):
      http://journals.ametsoc.org/doi/pdf/10.1175/BAMS-86-2-225
    Ken Waight / February 2017
    """
    a1 = 17.625
    b1 = 243.04
    c1 = 610.94
    es = c1 * math.exp((a1*(T-T0))/(b1+(T-T0)))
    return es


def TC2F(TC):
    """
    Convert temperature from Celsius to Fahrenheit.
    Ken Waight / December 2020
    """
    return (1.8*TC) +32.


def calcWbgt(yyyymmddhhmn,
             latitude, longitude,
             T2mC, Td2mC, wspd10m, pSfc, cloudFrac,
             swdn, swup, lwdn, lwup,
             verbosity):
    """ 
    Input variables needed:
    yyyymmddhhmn - UTC time
    T2mC (C)
    Td2mC (C)
    wspd10m (m/s)
    pSfc (Pa)
    1. cloudfrac or 
    2. swdn - cloudfrac will be estimated, or
    3. swdn,swup,lwdn,lwup - cloudfrac will be estimated  
    Ken Waight / May 2025
    """

    # Prepare input variables.
    dt = datetime.strptime(yyyymmddhhmn, '%Y%m%d%H%M')  # UTC.
    yyyy = int(yyyymmddhhmn[0:4])
    mm = int(yyyymmddhhmn[4:6])
    dd = int(yyyymmddhhmn[6:8])
    hh = int(yyyymmddhhmn[8:10])
    mn = int(yyyymmddhhmn[10:12])
    T2m = float(T2mC) + T0
    Td2m = float(Td2mC) + T0
    e2m = 611.2*math.exp((17.67*float(Td2mC))/(float(Td2mC)+243.5))
    rh2m = Td2Rh(T2m, Td2m)
    
    # --------------------
    # Show input met data.
    # --------------------
    if verbosity > 1:
        print("\n Input data:")
        print(" --------------------------------------------------")
        print(" Time and date     : {:02d}{:02d} UTC {:02d}/{:02d}/{:04d}".format(hh,mn,mm,dd,yyyy))
        print(" Latitude          : {:.1f} deg".format(latitude))
        print(" Longitude         : {:.1f} deg".format(longitude))
        print(" Station pressure  : {:.1f} mb".format(.01*pSfc))
        print(" 2 m temperature   : {:.1f} C".format(T2mC))
        print(" 2 m dew point     : {:.1f} C".format(Td2mC))
        print(" 2 m rel. humidity : {:.1f} %".format(100.0 * rh2m))
        print(" 10 m wind speed   : {:.1f} m/s".format(wspd10m))
        if cloudFrac is not None:
            print(" cloud fraction        : {:.3f}".format(cloudFrac))
        if swdn is not None:
            print(" Downward shortwave: {:.1f} W/m2".format(swdn))
        if swup is not None:
            print(" Upward shortwave  : {:.1f} W/m2".format(swup))
        if lwdn is not None:
            print(" Downward longwave : {:.1f} W/m2".format(lwdn))
        if lwup is not None:
            print(" Upward longwave   : {:.1f} W/m2".format(lwup))

    # Calculate solar and longwave irradiances.
    (solarZenith, solarElevation, cosZenith, dayofyear, 
     solarDownGlobal, solarDownDirect, solarDownDiffuse, solarUp,
     longwaveDown, longwaveUp,
     cloudFrac) = calc_irradiances(latitude, longitude, dt,
                                   T2m, e2m, wspd10m, pSfc, cloudFrac,
                                   swdn, swup, lwdn, lwup,
                                   verbosity)
    
    # Calculate mean radiant temperature.
    Tmrt = calc_Tmrt(latitude, longitude, dt,
                     T2m, e2m, pSfc, cloudFrac,
                     solarZenith, solarElevation,
                     longwaveDown, longwaveUp, 
                     solarDownDirect, solarDownDiffuse, solarUp,
                     verbosity)
    
    # ====================================
    # Liljegren et al. (2008) calculation. 
    # ====================================
    # -------------------------------------------------
    # Iterate to estimate natural wet bulb temperature.
    # -------------------------------------------------
    if verbosity > 1:
        print('\nIterate to estimate natural (includes radiation, wind) wet bulb temperature . .')
    TwetPrev = Td2m  # First guess.
    if verbosity > 1:
        print("First guess = dew point temperature: {:.1f} K = {:.1f} C = {:.1f} F".format(TwetPrev, TwetPrev-T0, TC2F(TwetPrev-T0)))
    iterMax = 100
    converged = False
    iter = 0
    while not converged and iter < iterMax:  # Iterate until the difference becomes small.
        iter += 1
        Tref = 0.5 * (TwetPrev+T2m)  # Use this for air temperature in each iteration.
        # Calculate delta Fnet/A, Liljegren, eq. 12.
        areaWick = math.pi * DIAM_WICK * LENGTH_WICK  # Given in Liljegren et al. but apparently not needed.
        # Calculate the fraction of solar radiation that is direct, from the total irradiance and 
        #   an empirical relation referenced in Liljegren.
        if solarZenith <= 89.5:
            # Earth-sun distance in astronomical units, 1.0 is average, from physics.stackexchange.com
            dEarthSun = 1.0 - 0.01672*math.cos(0.9856*dayofyear-4.0) 
            sMax = I0*cosZenith / (dEarthSun*dEarthSun) # Liljegren, eq. 14.
            sStar = solarDownGlobal / sMax
            if sStar > 0.0:
                fDir = math.exp(3.0 - 1.34*sStar -1.65/sStar) # Liljegren, eq. 13.
            else:
                fDir = 0.0  # Night.
        else:
            fDir = 0.0  # Night.
        # From text above eq. 12, from Oke, p. 373, e2m in mb.
        emisAir = 0.575 * (0.01*e2m)**0.143 
        # Eq. 12 in Liljegren.
        deltaFnetOverA = (SB*EMIS_WICK*0.5*((1.0+emisAir)*T2m*T2m*T2m*T2m-TwetPrev*TwetPrev*TwetPrev*TwetPrev) + 
                          (1.0-ALBEDO_WICK)*solarDownGlobal*((1.0-fDir)*(1.0-(DIAM_WICK/(4.0*LENGTH_WICK))+
                                                                         fDir*(math.tan(solarZenith)/math.pi)+
                                                                         (DIAM_WICK/(4.0*LENGTH_WICK))+ALBEDO_SFC)))
        # Calculate muAir, the viscosity of air, following subroutine in Liljegren's f90 code.
        mAir = 1000.0 * MAIR  # Molecular weight of air in g/mol instead of kg/mol
        sigma2 = SIGMA_MU * SIGMA_MU
        tr = T2m / EPS_KAPPA
        omega = ((tr-2.9)/0.4)*(-0.034) + 1.048
        muAir = 2.6693e-06*math.sqrt(mAir*Tref) / (sigma2*omega)
        # Calculate kAir, thermal conductivity of air from routine in Liljegren's f90 code.
        kAir = (CP + 1.25*R) * muAir
        rhoAir = pSfc / (R*Tref)  # Density of air.
        pr = (CP*muAir) / kAir  # Prandtl number.
        #ktw Replaced this simpler calculation with Liljegren's.
        # ResearchGate: https://www.researchgate.net/post/Binary_diffusion_coefficients_for_water_vapour_in_air_at_normal_pressure
        #diffWaterAir = 22.5e-06 * (T2m/273.15)**1.8
        # Liljegren's calculation.
        mAir = 1000.0 * MAIR  # Molecular weight of air in g/mol instead of kg/mol.
        mWater = 1000.0 * MWATER  # Molecular weight of water in g/mol instead of kg/mol.
        pCrit13 = (P_CRIT_AIR*P_CRIT_WATER)**(1.0/3.0)
        tCrit512 = (T_CRIT_AIR*T_CRIT_WATER)**(5.0/12.0)
        tCrit12 = (T_CRIT_AIR*T_CRIT_WATER)**0.5
        mMix = (1.0/mAir + 1.0/mWater)**0.5
        pAtm = pSfc / 101325.0
        diffWaterAir = (A_DIFF*(Tref/tCrit12)**B_DIFF *pCrit13*tCrit512*mMix/pAtm)*1.0e-4
        sc = muAir / (rhoAir*diffWaterAir)  # Schmidt number. 
        eWick = 611.2*math.exp((17.67*(TwetPrev-T0))/((TwetPrev-T0)+243.5))
        speed = max(wspd10m, 0.13) # Threshold of wind speed anemometers, from Liljegren.
        re = (rhoAir*speed*DIAM_WICK) / muAir  # Reynolds number.
        nu = B_NUSS*re**(1.0-C_NUSS)*(pr**(1.0-A_NUSS))  # Nusselt number.
        # Heat transfer coefficient from a cylinder, Liljegren, after eq. 10.
        h = (kAir/DIAM_WICK) * nu
        # Calculate new value of Twet, eq. 9 in Liljegren.
        Twet = (T2m - (LHV/CP)*(MW/MAIR)*((pr/sc)**A_NUSS)*((eWick-e2m)/(pSfc-eWick)) + 
                deltaFnetOverA/h)
        if verbosity > 1:
            print('  ','iter:', iter, TwetPrev, '->', Twet, 'difference:', Twet-TwetPrev)
        if abs(Twet-TwetPrev) <= 0.02:  # Iterate until the difference becomes small.
            converged = True
        TwetPrev = 0.9*TwetPrev + 0.1*Twet  # Value for next iteration.
    # Revert to simple estimation if the result of the iteration is too far off.
    diffWetDew = Twet - Td2m
    if abs((Twet > T2m) or
           abs(diffWetDew) >= 30.0):
        Twet = (2.0/3.0)*T2m + (1.0/3.0)*Td2m
        if verbosity > 1:
            print('WARNING: Bad iteration, reverted to simple approximation')
    if verbosity > 1:
        print("Final wet bulb temperature: {:.1f} K = {:.1f} C = {:.1f} F".format(Twet, Twet-T0, TC2F(Twet-T0)))
    if not converged:
        print('Iteration to wet bulb temperature failed!')
        sys.exit()
    
    # ---------------------------------------
    # Iterate to estimate globe temperature.
    # ---------------------------------------
    if verbosity > 1:
        print('\nIterate to estimate globe temperature . .')
    Tsfc = T2m  # Following Liljegren.
    TglobePrev = T2m  # Initialize TglobePrev for first iteration, following Liljegren's code.
    if verbosity > 1:
        print("First guess = air temperature: {:.1f} K = {:.1f} C = {:.1f} F".format(TglobePrev, TglobePrev-T0, TC2F(TglobePrev-T0)))
    iterMax = 50
    converged = False
    iter = 0
    while not converged and iter < iterMax:  # Iterate until the difference becomes small.
        iter += 1
        Tref = 0.5 * (TglobePrev+T2m)  # Use this for air temperature in each iteration.
        # Heat transfer coefficient from a sphere, Liljegren, eq. 16.
        rhoAir = pSfc / (R*Tref)  # Density of air.
        speed = max(wspd10m, 0.13) # Threshold of wind speed anemometers, from Liljegren's code.
        muAir = 2.6693e-06*math.sqrt(mAir*Tref) / (sigma2*omega)
        kAir = (CP + 1.25*R) * muAir
        re = (rhoAir*speed*DIAM_GLOBE) / muAir  # Reynolds number.
        nu = 2.0 + (0.6*re**0.5)*(pr**0.3333)  # Nusselt number.
        h = (kAir/DIAM_GLOBE) * nu
        # Minor modifications to match Liljegren's code rather than article. 
        Tglobe4 = (0.5*(emisAir*T2m*T2m*T2m*T2m+EMIS_SFC*Tsfc*Tsfc*Tsfc*Tsfc) -
                   (h/(EMIS_GLOBE*SB))*(TglobePrev-T2m) +
                   (solarDownGlobal/(2.0*EMIS_GLOBE*SB))*(1.0-ALBEDO_GLOBE)*
                   (1.0+(1.0/(2.0*cosZenith)-1.0)*fDir+ALBEDO_SFC))
        Tglobe = Tglobe4 ** 0.25
        if verbosity > 1:
            print('  ','iter:', iter, TglobePrev, '->', Tglobe, 'difference:', Tglobe-TglobePrev)
        if abs(Tglobe-TglobePrev) <= 0.02:  # Iterate until the difference becomes small.
            converged = True
        TglobePrev = 0.9*TglobePrev + 0.1*Tglobe  # Go to next iteration.
    if verbosity > 1:
        print("Final globe temperature: {:.1f} K = {:.1f} C = {:.1f} F".format(Tglobe, Tglobe-T0, TC2F(Tglobe-T0)))
    if not converged:
        print('Iteration to globe temperature failed!')
        sys.exit()
    
    # ---------------
    # Calculate WBGT.
    # ---------------
    wbgt = 0.7*Twet + 0.2*Tglobe + 0.1*T2m
    if verbosity > 1:
        print("\n Results:")
        print(" --------------------------------------------------")
        print(" WBGT = 0.7*wet bulb temperature + 0.2*globe temperature + 0.1*temperature")
        print(" 2 m wet bulb temperature : {:5.1f} C = {:5.1f} F".format(Twet-T0, TC2F(Twet-T0)))
        print(" 2 m globe temperature    : {:5.1f} C = {:5.1f} F".format(Tglobe-T0, TC2F(Tglobe-T0)))
        print(" 2 m temperature          : {:5.1f} C = {:5.1f} F".format(T2mC, TC2F(T2mC)))
        print(" 2 m WBGT                 : {:5.1f} C = {:5.1f} F".format(wbgt-T0, TC2F(wbgt-T0)))
    
    # Return results.
    return (Twet-T0, Tglobe-T0, wbgt-T0, cloudFrac)
