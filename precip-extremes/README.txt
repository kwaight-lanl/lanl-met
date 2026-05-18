The Python script used to calculate precipitation extremes from
15-minute LANL data is calcPrecipExtremes.py.

A LANL report describes the technical details of the methods used 
to calculate precipitation extremes:
"Analysis of the Frequency of Extreme Precipitation Events at Los
Alamos National Laboratory", 2020, LA-UR-23488.

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

3. Enter this command:
source envs/general/bin/activate
This activates a virtual environment that's been set up there, a
tool which ensures that the correct version of Python and a few necessary
packages are present and ready to use. Just do that each time that you
log in, and there should be no need to worry about it after that. If the
virtual environment worked, you should see (general) before the usual
Linux prompt, like this:
(general) [maq@kwaightlinux ~]$

4. Go to an example directory that is already there:
cd projects/stormwater/precip-extremes

5. Run the script:
You can test with the example data file precip-ta6.csv. Run the
script, giving the name of the 15 min precip file as the single
argument: 
calcPrecipExtremes.py precip-ta6.csv

The script prints lots of information and results to the
screen. If you would like to save the screen output, add ">
output-filename" when running the script, e.g.:
calcPrecipExtremes.py precip-ta6.csv > output.txt
An example of the output is available in sample-output.txt.

Two output CSV files are created: 
precipExtremes.csv - The major output file, shows extremes for each
duration and return period. 
precipRecurrenceData.csv - Recurrence interval (return period) and
precip values for one duration. This file is for diagnostic purposes
and can be ignored.

6. To run the script with your own data, create a file of 15-minute
LANL precipitation data from one of our locations, in CSV format. Each
line in the file should have only two fields: a date and the 15-min
precip value in inches. It's OK to have or not have a simple header
line. Here's an example of the beginning of a suitable file, with a header: 

date,precip(in) 
2/1/1990 0:15,0 
2/1/1990 0:30,0 
2/1/1990 0:45,0 
2/1/1990 1:00,0 
2/1/1990 1:15,0
.  .

Currently, the best way to get a file like this is to request a raw
data file in Excel format from the Weather Machine, then manipulate it
in Excel to create a CSV file with only those two columns. 

Then run the script in the same way, using your filename as the argument
instead of the example file above.

7. If any files need to be transferred between the virtual machine and another location,
there are a few options:
a. From the other machine, open a terminal window and use the Linux scp command. For example,
on a Windows machine, open a Windows Powershell window, change into a directory where you want the
file(s) to go, and fetch the file with the scp (secure copy) command:
cd C:\Users\999999
scp maq@kwaightlinux.lanl.gov:projects/stormwater/precip-extremes/precipExtremes.csv .
Or to transfer a file from the other machine to the virtual machine:
cd C:\Users\999999
scp TA6_precip.csv maq@kwaightlinux.lanl.gov:projects/stormwater/precip-extremes
b. There are many specialized applications to transfer files between systems. On Windows, WS FTP Pro
is available for download at LANL. UltraEdit is an editing progfram that is also available, and 
it includes an FTP (file transfer) feature. 


Note: We've been running successfully with a dataset covering more
than 28 years of continuous precip data, but tests with datasets less
than 5 years may produce errors, and results from such a short precip
period would probably not be useful anyway.


Note: Running the script may produce one or more error messages
similar to this: 

calcPrecipExtremes.py:110: RuntimeWarning: invalid
value encountered in 
power precip = beta * ((omega*R)**(1.0/alpha) -1.0)**(1.0/theta) 

An iterative process is used for curve-fitting, and
it seems that one or more of the iterations create problem values of a
coefficient, but the iterations seem to continue successfully after
that, so it should be OK to ignore the errors, as long as the
calculations are completed and the results look reasonable. If there
are a lot of these kinds of errors, it may be necessary to investigate
further.


Ken Waight / kwaight@lanl.gov
