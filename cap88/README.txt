The Python script used to create a STAR file for CAP88 from 15-minute
LANL data is tower2star.py.

A report describes the preparation of data for CAP88, which
includes technical details of how observations are classified into
wind direction, wind speed and stability categories:
"Processing of Meteorological Data for the CAP88 Model at Los Alamos
National Laboratory", 2020, LA-UR-xxxxx.

To run the code on our Linux virtual machine:

1. From a machine on the yellow network, open a terminal window.
On a Windows machine, there are several ways to open a terminal window
that can be used to log in to another machine -- here are three options:
a. In the Windows Start Menu, open a Windows PowerShell window under
the Windows Powershell submenu
b. In the Windows Start Menu open a Command Prompt window under
the Windows System submenu
c. A terminal window can be opened with the third-party PuTTY
application

Linux and Mac machines have native Terminal window applications and
lots of other choices. 

2. Log in to the virtual machine:
ssh maq@kwaightlinux.lanl.gov (get password from Ken)
The first time you log in from a different machine, you may get a
warning asking if you are sure that you want to connect. If so, say
yes. "maq" is the username and "kwaightlinux.lanl.gov" is the hostname.

3. Go to an example directory that is already there:
cd projects/cap88

4. Run the script:
You can test with the example data file TA6_15.csv. Run the script,
giving the name of the 15 min file as the single argument: 
tower2star.py TA6_15.csv
On the virtual machine, the script's default location is /home/maq/bin,
and tower2star.py can be called like this from anywhere without specifying
its location. 

Running the script writes lots of information and results to the
screen, and writes the resulting STAR file as data.str. If you would
like to save the screen output, add "> output-filename" when running
the script, e.g.:
tower2star.py TA6_15.csv > output.txt
An example of the output is available in sample-output.txt.

You usually will want to assign a different name to the STAR file, so
add a -o argument with a custom STAR file name:
tower2star.py TA6_15.csv -o ta6.str

The method assumes that the lowest level of wind data is at the standard
height of 10 meters, but the four main LANL towers have a first level of 
11.5 meters (often listed as 12 meters). The sigma-e values used to 
determine initial stability categories need to be adjusted if the wind
is not measured at the standard 10 m height, so the -windheight option
should be used for the main LANL towers, for example:
tower2star.py -windheight 11.5 TA6_15.csv 

In the notes below, some other examples of tower2star.py runs are given,
showing some other options.

==========================================================================
So a run with a typical set of options and redirecting the standard 
output to a text file might be:
tower2star.py -windheight 11.5 -o ta6.str TA6_15.csv > tower2star-ta6.txt
==========================================================================

5. The script can be run with a custom raw data file downloaded from
weather.lanl.com, on the yellow network. Because of a difference in 
the date formatting, the code would need to be modified to run with 
data from weathermachine.lanl.gov, on the green network.

To run with your own data, download a file of 15-minute LANL data
for one of the met towers, in csv format and transfer it to the virtual
machine (see options for tranferring files below). It's
important to retain only the two header lines with comma-separated field
names and units, but remove any other header lines. So if the Weather 
Machine (weather.lanl.gov) produces a file beginning like this: 

Data is for site TA6 for 15-minute
data.,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 
This file was obtained from the LANL Weather
Machine.,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 
Request made at 2020-02-25 08:37:00
MST.,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 
All Data times are Mountain Standard Time
(MST).,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,, 
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
Date/Time,doy,spd1,spd2,spd3,spd4,sdspd1,sdspd2,sdspd3,sdspd4,dir1,dir2,dir3,dir4,sddir1,sddir2,sddir3,sddir4,w1,w2,w3,w4,sdw1,sdw2,sdw3,sdw4,fvel2,temp0,temp1,temp2,temp3,temp4,press,rh,ah,dewp,precip,snowd,lstks,swdn,swup,lwdn,lwup,netrad,sheat,lheat,stemp1,stemp2,stemp3,smoist1,smoist2,gheat,created_on,created by,updated on,updated by
yyyy-mm-dd hh:mm,ddd,m/s,m/s,m/s,m/s,m/s,m/s,m/s,m/s,deg,deg,deg,deg,deg,deg,deg,deg,m/s,m/s,m/s,m/s,m/s,m/s,m/s,m/s,m^2/s^2,deg-C,deg-C,deg-C,deg-C,deg-C,mb,%,g/m^3,deg-C,in,in,stks,W/m^2,W/m^2,W/m^2,W/m^2,W/m^2,W/m^2,W/m^2,deg-C,deg-C,deg-C,%,%,W/m^2,,,,
12/1/2019 0:00,335,0.8,0.6,0.3,0.1,0.2,0.27,0.41,0.24,247,228,204,248,12,13,18,16,0,0,0,0,0,0,0.01,0.02,*,-9.5,-6.8,-6.7,-6.9,-7.2,775.3,76,*,-12.9,0,2.5,*,0,0,190,236,-46,*,*,*,*,*,*,*,*,12/2/2019 8:10,system,12/2/2019 8:10,system
.
.

then remove all of the first lines except for the two header lines containing
field names and units.. Different towers will have different sets of fields, 
but the header lines for all of them should look similar to this. The end result 
is that the file begins with two header lines and then all of the data lines, 
like this:

Date/Time,doy,spd1,spd2,spd3,spd4,sdspd1,sdspd2,sdspd3,sdspd4,dir1,dir2,dir3,dir4,sddir1,sddir2,sddir3,sddir4,w1,w2,w3,w4,sdw1,sdw2,sdw3,sdw4,fvel2,temp0,temp1,temp2,temp3,temp4,press,rh,ah,dewp,precip,snowd,lstks,swdn,swup,lwdn,lwup,netrad,sheat,lheat,stemp1,stemp2,stemp3,smoist1,smoist2,gheat,created_on,created by,updated on,updated by
yyyy-mm-dd hh:mm,ddd,m/s,m/s,m/s,m/s,m/s,m/s,m/s,m/s,deg,deg,deg,deg,deg,deg,deg,deg,m/s,m/s,m/s,m/s,m/s,m/s,m/s,m/s,m^2/s^2,deg-C,deg-C,deg-C,deg-C,deg-C,mb,%,g/m^3,deg-C,in,in,stks,W/m^2,W/m^2,W/m^2,W/m^2,W/m^2,W/m^2,W/m^2,deg-C,deg-C,deg-C,%,%,W/m^2,,,,
12/1/2019 0:00,335,0.8,0.6,0.3,0.1,0.2,0.27,0.41,0.24,247,228,204,248,12,13,18,16,0,0,0,0,0,0,0.01,0.02,*,-9.5,-6.8,-6.7,-6.9,-7.2,775.3,76,*,-12.9,0,2.5,*,0,0,190,236,-46,*,*,*,*,*,*,*,*,12/2/2019 8:10,system,12/2/2019 8:10,system
.
.

Then run the script in the same way, using your filename as the argument
instead of the example file above. 

6. When raw data files need to be transferred to the virtual machine, and when STAR files
or other output files need to be transferred from the virtual machine to another location,
there are a few options:
a. From the destination machine, open a terminal window and use the Linux scp command. For example,
on a Windows machine, open a Windows Powershell window, change into a directory where you want the
file(s) to go, and fetch the file with the scp (secure copy) command:
cd C:\Users\999999
scp maq@kwaightlinux.lanl.gov:projects/cap88/data.str .
Or to transfer a file from the other machine to the virtual machine:
cd C:\Users\999999
scp TA6_15.csv maq@kwaightlinux.lanl.gov:projects/cap88
b. There are many specialized applications to transfer files between systems. On Windows, WS FTP Pro
is available in the Software Center at LANL. UltraEdit is an editing program that is also 
available, and it includes an FTP (file transfer) feature. 


7. Examples of other options:
a. If you would like the STAR file to have only data from a given month,
add a -mon argument: 
tower2star.py -mon 6 TA6_15.csv 
where 6 means June. 

b. If you would like the STAR file to include only data for night or day,
add the -night or -day flag: 
tower2star.py -day   TA6_15.csv 
tower2star.py -night TA6_15.csv 

c. The -mon and -day/-night arguments can also be combined:
tower2star.py -mon 6 -day TA6_15.csv 

d. The roughness length has a modest impact on the calculation of stability
categories. The default value is 40 cm, which is an average value for
LANL. But there are significant differences for some parts of the
lab, so a different value (21 cm in the example below) can be provided 
with the -z0 option:
tower2star.py -z0 21 TA6_15.csv 

e. If the wind is measured at a non-standard height, the wind speeds
going into the STAR file categories will be estimated at 10 m with
a power law wind profile, unless the -noestimate10m option is used:
tower2star.py -nestimate10m TA6_15.csv 

f. To see all options, use the -h (help) argument:
tower2star.py -h


Note:
Warning messages such as this can be ignored:
WARNING: Cannot calculate sigma-E and stability class with a zero wind speed at 2017-01-11 09:45:00 , will be ignored.


Note:
If you need to modify the tower2star.py script for testing or debugging, 
copy the script from it's home location to a different directory and 
then edit it there and run the script from the local location, for
example:
cd /home/maq/projects/cap88
cp ~/bin/tower2star.py .
vi tower2star.py
./tower2star.py -windheight 11.5 -o ta6.str TA6_15.csv > tower2star-ta6.txt
(The "./" before tower2star.py tells it to use the script in the current directory)


Note:
compareStars.py is a utility program to show the differences between
two different STAR files. It can be used to compare a STAR file
produced by the PV-WAVE code to one produced by tower2star.py. Run the
script with the two files to compare as arguments: 
compareStars.py data1.str data2.str


Note:
tower2day.py is a utility program to read tower data and search for cases (days) with some characteristic.
Currently the only option is to specify a wind direction (e.g. N, NNE, NE, ENE, W, etc.), and a list of
the days which have the most observations times with a wind direction in that sector. To run:
tower2day.py  TA6_15.csv 
It has the same -day/-night, -mon and -z0 options as tower2star.py.


Note:
As a backup location for running the Python scripts in case the Linux virtual machine is 
unavailable for some reason, there are a couple of options:
1. Ken Waight's Windows desktop machine (pn2000013) has Python 3.8 installed, and a directory 
is set up with the code. Open either a Windows Command Prompt window or a Windows PowerShell
window, change to the correct directory:
cd C:\Users\348298\PycharmProjects\cap88 
Copy the desired met data file there and then run the script, for example:
python ./tower2star.py -windheight 11.5 ta54-15-2018.csv
2. David Bruggeman can run the program using Anaconda/Spyder on his Windows desktop machine.


Ken Waight / kwaight@lanl.gov / September 2020
