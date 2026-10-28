
import subprocess

year = 2026
month = 10
day = 28
hourInit = 12
yyyy = '{:4d}'.format(year)
mm = '{:2d}'.format(month)
dd = '{:2d}'.format(day)
hhInit = '{:2d}'.format(hourInit)
print('\nFetching gridded data:')
for hourFcst in range(0, 25):
    print('   ', hourFcst)
    hhFcst = '{:2d}'.format(hourFcst)
    mm = mm.replace(' ', '0')
    dd = dd.replace(' ', '0')
    hhFcst = hhFcst.replace(' ', '0')
    url = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl?dir=%2Fhrrr.' + yyyy + mm + dd + '%2Fconus&file=hrrr.t' + hhInit + 'z.wrfsfcf' + hhFcst + '.grib2&all_var=on&all_lev=on&subregion=&toplat=38&leftlon=-108&rightlon=-105&bottomlat=35'
    print('url:', url)

    outfile = 'hrrr.t' + hhInit + 'z.wrfsfcf' + hhFcst + '.grib2'
    commandString = 'curl ' + '\'' + url + '\'' +  ' -o ' + outfile
    output = subprocess.check_output(commandString, stderr=subprocess.STDOUT, shell=True)


