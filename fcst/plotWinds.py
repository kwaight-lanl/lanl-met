"""
plotWinds.py
Plot wind field for all times with matplotlib and animate with ImageMagick. 
Ken Waight / March 2021
"""

import sys
import glob
import subprocess
import numpy as np
from netCDF4 import Dataset
import matplotlib.pyplot as plt
from wrf import getvar, extract_dim

#sourceList = ['nam']
sourceList = ['hrrr', 'nam']
print('\nPlot wind field for each time:')
for source in sourceList:
    print('   ', '------')
    print('   ', source)
    print('   ', '------')
    # List of netcdf files to plot.
    pngfiles = []
    ncfiles = glob.glob('wrfinput.*' + source + '.nc')
    ncfiles.sort()
    for ncfile1 in ncfiles:
        print('   ', ncfile1)
        yyyymmddhh = ncfile1.split('.')[1]
        # Open a netcdf file.
        ncfile = Dataset(ncfile1)

        # Get the terrain.
        terrain = getvar(ncfile, "HGT")

        # Get the wind components.
        u = getvar(ncfile, "U10")
        v = getvar(ncfile, "V10")

        # Build simple x, y coordinates.
        west_east = extract_dim(ncfile, 'west_east')
        south_north = extract_dim(ncfile, 'south_north')
        x1 = np.arange(west_east)
        y1 = np.arange(south_north)
        x, y = np.meshgrid(x1, y1)

        # Set up plots.
        plt.style.use('seaborn')
        fig, ax1 = plt.subplots()
        fig.set_size_inches(10, 10)
        #fig.set_dpi(100)
        timeString = yyyymmddhh[0:8] + '/' + yyyymmddhh[-2:]
        plt.title(source + ' / ' + timeString)
        plotNthPoint = 3
        q = ax1.quiver(x[::plotNthPoint, ::plotNthPoint], 
                       y[::plotNthPoint, ::plotNthPoint], 
                       u[::plotNthPoint, ::plotNthPoint], 
                       v[::plotNthPoint, ::plotNthPoint],
                       scale_units='x', scale=1.75)
        ax1.quiverkey(q, X=0.9, Y=1.01, U=5., label='5 m/s', labelpos='E')
        image = ax1.imshow(terrain, origin='lower', cmap=plt.cm.terrain, aspect='equal')
        #ax1.contour(terrain)
        fig.colorbar(image)
        # Save as a file.
        pngfile = 'wind-' + source + '.' + yyyymmddhh + '.png'
        pngfiles.append(pngfile)
        fig.savefig(pngfile)
        plt.close()

    # Make an animation.
    args = ['/usr/bin/convert'] + pngfiles
    args.append('>')
    args.append('winds-' + source + '.gif')
    try:
        process = subprocess.check_call(args)
    except subprocess.CalledProcessError as e:
        print(e)

