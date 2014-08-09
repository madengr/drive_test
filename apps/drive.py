#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  6 20:58:08 2014

@author: madengr
"""

from gnuradio import gr
from gnuradio import uhd
from gnuradio import blocks
from gnuradio import analog
from gnuradio import filter # Warning: redefining built-in filter()
from gnuradio import audio
import time
from gnuradio.eng_option import eng_option
from optparse import OptionParser

class MyTopBlock(gr.top_block):
    """ Class for WBFM receiver with RSSI probe

    USRP set for 500 kHz sample rate
    USRP tuned 125 kHz below desired WBFM channel to avoid DC
    FXFIR tunes to desired channel and decimates to 250 kHz
    WBFM demod and decimate to 50 kHz
    Resample to 48 kHz
    Multiply by constant to increase volume
    Sink to audio

    Complex to mag^2 calciulates power of WBFM channel
    Integrate and decimate to 1 Hz
    Take 10*LOG10() and offset by src_gain and calibration offset
    Sample with probe whose level() method is called from outside the flow
    """

    def __init__(self):

        # Call the initialization method from the parent class
        gr.top_block.__init__(self)

        # Setup the parser for command line arguments
        parser = OptionParser(option_class=eng_option)
        parser.add_option("-v",
                          "--verbose",
                          action="store_true",
                          dest="verbose",
                          default=False,
                          help="print settings to stdout")
        parser.add_option("-f",
                          "--frequency",
                          type="eng_float",
                          dest="rx_freq",
                          default=98.9E6,
                          help="RX frequency in Hz")
        parser.add_option("-a",
                          "--args",
                          type="string",
                          dest="uhd_args",
                          default='type=b200',
                          help="USRP device args")
        parser.add_option("-c",
                          "--cal",
                          type="eng_float",
                          dest="rssi_cal_offset_dB",
                          default=-50,
                          help="RSSI calibration offset in dB")
        parser.add_option("-g",
                          "--gain",
                          type="eng_float",
                          dest="src_gain_dB",
                          default=50,
                          help="USRP gain in dB")
        parser.add_option("-V",
                          "--volume",
                          type="eng_float",
                          dest="volume_dB",
                          default=30,
                          help="Audio volume in dB")
        parser.add_option("-s",
                          "--soundrate",
                          type="eng_float",
                          dest="snd_card_rate",
                          default=48000,
                          help="Sound card rate in Hz")

        (options, args) = parser.parse_args()
        if len(args) != 0:
            parser.print_help()
            raise SystemExit, 1

        # Define constants
        uhd_args = options.uhd_args
        self.rx_freq = options.rx_freq
        lo_offset_freq = 125E3
        src_samp_rate = 500000
        src_gain_dB = options.src_gain_dB
        rssi_cal_offset_dB = -50
        volume_dB = options.volume_dB
        snd_card_rate = options.snd_card_rate

        # Print some info to stdout for verbose option
        if options.verbose:
            print 'USRP args string "%s" ' % uhd_args
            print 'RX frequency = %f MHz' % (self.rx_freq/1E6)
            print 'Source sample rate = %i Hz' % src_samp_rate
            print 'USRP gain = %i dB' % src_gain_dB
            print 'RSSI cal offset= %i dB' % rssi_cal_offset_dB
            print 'Audio volume = %i dB' % volume_dB
            print 'Sound card rate = %i Hz' % snd_card_rate

        # Setup the USRP source
        self.src = uhd.usrp_source(uhd_args, uhd.io_type_t.COMPLEX_FLOAT32, 1)
        self.src.set_samp_rate(src_samp_rate)
        self.src.set_center_freq(self.rx_freq - lo_offset_freq, 0)
        self.src.set_gain(src_gain_dB, 0)

        # Generate taps for frequency translating FIR filter
        filter_taps = filter.firdes.low_pass(gain=1.0,
                                             sampling_freq=src_samp_rate,
                                             cutoff_freq=100E3,
                                             transition_width=25E3,
                                             window=filter.firdes.WIN_HAMMING)
        # Frequency translating FIR filter
        fxlate = filter.freq_xlating_fir_filter_ccc(decimation=2,
                                                    taps=filter_taps,
                                                    center_freq=lo_offset_freq,
                                                    sampling_freq=src_samp_rate)
        # Wideband FM demodulator
        wbfm = analog.fm_demod_cf(channel_rate=src_samp_rate/2,
                                  audio_decim=5,
                                  deviation=75000,
                                  audio_pass=15000,
                                  audio_stop=16000,
                                  gain=1.0,
                                  tau=75E-6)

        # Rational resampler
        resamp = filter.rational_resampler_fff(interpolation=snd_card_rate,
                                               decimation=src_samp_rate/10)

        # Multiply for voulme control
        volume = blocks.multiply_const_ff(10**(volume_dB/20)-1)

        # Sound card sink
        sndcard = audio.sink(snd_card_rate, '', True)

        # Connect the blocks for audio monitoring
        self.connect(self.src, fxlate, wbfm, resamp, volume, sndcard)

        # Calculate power for RSSI
        c2magsqr = blocks.complex_to_mag_squared(1)

        # Integrate for mean power and decimate down to 1 Hz
        integrator = blocks.integrate_ff(decim=src_samp_rate/2)

        # Take 10*Log10 and offset for calibrated power and src gain
        logten = blocks.nlog10_ff(10, 1, rssi_cal_offset_dB-src_gain_dB)

        # Probe the RSSI signal
        self.rssi = blocks.probe_signal_f()

        # Connect the blocks for the RSSI
        self.connect(fxlate, c2magsqr, integrator, logten, self.rssi)

def main():
    """ Start the flow and log GPS message and RSSI to file """

    # Start the flow and wait to settle
    tb = MyTopBlock()
    tb.start()
    time.sleep(2)

    # Open a file for logging
    filename = 'log_'
    filename += str(int(tb.rx_freq))
    filename += '_'
    filename += str(int(time.time()))
    filename += '.txt'
    f = open(filename, 'w')

    # Write a header
    f.write('#gps_message RSSI(dBm)\n')
    print '\n'

    # Start logging
    while True:
        gps = str(tb.src.get_mboard_sensor('gps_gpgga'))
        gps = gps.lstrip('GPS_GPGGA: ') # lstrip() won't lose checksum byte
        rssi = tb.rssi.level()
        log_string = gps + ' ' + "{:2.1f}".format(rssi)
        f.write(log_string + '\n')
        print log_string
        time.sleep(1)

    # Stop the flow and close file
    tb.stop()
    tb.wait()
    f.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
