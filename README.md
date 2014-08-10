drive_test
======

RF drive test for the Ettus USRP using GNU Radio and Google Maps

Author: Louis Brown KD4HSO

Homepage: https://github.com/madengr/drive_test

Features:
- Averages WBFM channel over 1 second to obtain calibrated RSSI 
- Queries GPSDO module to obtain position
- Logs position and RSSI to text file
- Post-processing of log to generate colored, labled points on Google Maps

Tested with:
- Ettus B200 + GPSDO (http://www.ettus.com)
- Ettus UHD 3.7.2 (https://github.com/EttusResearch/uhd)
- GNU Radio 3.7.5 (https://github.com/gnuradio/gnuradio)
- pynmea2 1.3.0 (https://github.com/Knio/pynmea2)
- pygmaps (https://code.google.com/p/pygmaps/) 

This is an RF drive test demo using the USRP + GPSDO, and GNU Radio.  Drive tests are the equivalent of “can you hear me now?” for RF propagation.  

The “drive.py” sets the USRP for 500 ksps sampling rate and tunes 125 kHz below the desired WBFM channel frequency.  This offset tuning moves the DC feed-through out of the 200 kHz WBFM band.  A frequency translating FIR filter tunes to +125 kHz in the baseband, filters to 200 kHz, and decimates by two to 250 ksps.  The FM demodulator filters the audio to 16 kHz and decimates by five to 50 kHz.  A re-sampler reduces the audio rate to 48 kHz for the sound card.

The WBFM channel from the frequency translating FIR filter is fed through a complex_to_mag^2 to obtain the power, then integrated and decimated by 250,000 to obtain mean power over 1 second.  The 10*Log10() converts to dB, which is then offset by a calibration factor obtained by feeding the USRP with a calibrated signal generator.  This results in an Received Strength Signal Indicator (RSSI) with units dBm, which is sampled by a probe_signal.

The main loop, outside the GNU Radio flow, samples the RSSI probe_signal.level() once per second, and also query's the GPSDO for the NMEA data.  The NMEA data and RSSI are logged to a text file.  The file name is comprised of the channel frequency and UNIX system time.  Typical usage is as follows (with CTRL-C to terminate):

./drive.py -f 98.9E6 -v 

The “process.py” reads the log file, and using pynmea2, strips out NMEA data without a position fix.  The RSSI minimum and maximum values are used to generate a matplotlib 'jet' colorscale; i.e. blue is low power and red is high power.  The pygmaps is used to plot points to an html file for Google Maps.  Each point is color scaled and labeled with RSSI value and altitude.  Typical usage is:

./process.py log_98900000_1407460630.txt

firefox log_98900000_1407460630.html

I have included the “fixed” version of pygmaps, which correctly adds the point label.  The fixed version may also be found here:

https://pygmaps.googlecode.com/issues/attachment?aid=50001000&name=pygmaps.py&token=ABZ6GAcrAjoSOQqAo7Pi9Zr5ktERso797g%3A1407467117294

This is a sample screen shot for a quick drive of KQRC, 98.9 MHz; the transmitter on the east side of Kansas City.  See the apps directory for the Google Maps html file.

![Drive test screenshot](https://github.com/madengr/drive_test/blob/master/drive_test.png)

