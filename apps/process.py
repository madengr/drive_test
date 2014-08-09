#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  7 10:19:47 2014

@author: madengr
"""
import fileinput
import pynmea2
import pygmaps
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx

def main():
    """ Main rountine to parse drive log and create Google map """
 
    # Read the file, splitting into lists of parsed gps messages and RSSI floats
    gps = []
    rssi = []
    for line in fileinput.input():
        # Ignore lines that don't start with $
        if line[0] == '$':
            pmsg = pynmea2.parse(line.split()[0])
            # Strip out messages with no GPS fix (zero latitude or longitude)
            if (pmsg.latitude == 0.0) or (pmsg.longitude == 0.0): 
                pass
            else:
                gps.append(pmsg)
                rssi.append(float(line.split()[1]))
        else:
            pass
    
    # Use the first gps coordinate to center the map
    mymap = pygmaps.maps(gps[0].latitude, gps[0].longitude, 16)
 
    # Create a color map from the min and max RSSI
    rssi_max = sorted(rssi, key=float)[-1]
    rssi_min = sorted(rssi, key=float)[0]   
    cmap = plt.get_cmap('jet')
    cNorm  = colors.Normalize(vmin=rssi_min, vmax=rssi_max)
    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cmap)
    print 'RSSI_max = ' + str(rssi_max) + ' dBm'
    print 'RSSI_min = ' + str(rssi_min) + ' dBm'
    
    # Plot the points
    while len(gps) != 0:      
        # Map a color to the RSSI value and convert to hex string        
        color = scalarMap.to_rgba(rssi[0])
        red = "{0:0{1}x}".format(int(color[0]*255),2)
        green = "{0:0{1}x}".format(int(color[1]*255),2)
        blue = "{0:0{1}x}".format(int(color[2]*255),2)
        color_string = "#" + red + green + blue
        # Parse the gps_msg and plot             
        point_label = str(rssi[0]) + ' dBm, '
        point_label += str(gps[0].altitude) + gps[0].altitude_units        
        mymap.addpoint(gps[0].latitude,
                       gps[0].longitude,
                       color_string,
                       point_label)
        gps.pop(0)
        rssi.pop(0)
        
    
    # Create the Google map *.html file
    input_file_name = fileinput.filename()
    output_file_name = input_file_name.split('.')[0] + ".html"   
    mymap.draw(output_file_name)
    
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

