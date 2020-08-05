import elevfix
import math
import argparse
import os
import sys

import plotly.express as px


def main(track_fpath):

    # validate input
    fname, ext = os.path.splitext(track_fpath)
    if ext.lower() not in ['.gpx', '.tcx']:
        raise ValueError("Input file's format must be GPX or TCX")

    # parse input file
    with open(track_fpath, 'r') as f:
        track_content = f.read()
        if ext.lower() == '.gpx':
            wpts = elevfix.gpx_parse(track_content)
        else:  # ext.lower() == '.tcx'
            wpts = elevfix.tcx_parse(track_content)

    # remove waypoints for which the distance to the next one is 0
    i = 0
    while i < len(wpts)-1:
        if elevfix.wpt_distance(wpts[i], wpts[i+1]) == 0.0:
            del wpts[i]
        else:
            i += 1

    # parsed original latitudes, longitudes and altitudes
    latitudes = [ wpt.lat for wpt in wpts ]
    longitudes = [ wpt.lon for wpt in wpts ]
    altitudes_orig = [ wpt.alt for wpt in wpts ]

    # accumulated distance on each waypoint
    dists = [ elevfix.wpt_distance(wpair[0], wpair[1]) for wpair in zip(wpts[:-1], wpts[1:]) ]
    dists_acc = [ sum(dists[:i]) for i in range(len(wpts)) ]

    ## calculate metrics for evaluation

    # original accumulated elevation gain
    eg_orig = elevation_gain_with_threshold(altitudes_orig)
    print('Original elevation gain: {:.2f}'.format(eg_orig))

    # SRTM raw altitudes
    altitudes_srtm_raw = elevfix.set_altitudes(latitudes, longitudes, smooth=False)
    o2_srtm = variance(altitudes_orig, altitudes_srtm_raw)
    o_srtm = math.sqrt(o2_srtm)
    eg_srtm = elevation_gain(altitudes_srtm_raw)
    eg_th_srtm = elevation_gain_with_threshold(altitudes_srtm_raw)
    print('SRTM raw:')
    print('- Variance: {:.2f}'.format(o2_srtm))
    print('- Standard deviation: {:.2f}'.format(o_srtm))
    print('- Accumulated elevation gain: {:.2f}'.format(eg_srtm))
    print('- Elevation gain with threshold: {:.2f}'.format(eg_th_srtm))

    # SRTM smoothed altitudes after applying Savitzky-Golay filter
    min_o = sys.maxsize
    min_eg_diff = sys.maxsize
    best_altitudes = []
    best_window = None
    for window in range(51, 501, 50):
        
        altitudes_srtm = elevfix.set_altitudes(latitudes, longitudes, smooth=True, window=window)
        o2_srtm = variance(altitudes_orig, altitudes_srtm)
        o_srtm = math.sqrt(o2_srtm)
        eg_srtm = elevation_gain(altitudes_srtm)
        eg_th_srtm = elevation_gain_with_threshold(altitudes_srtm)
        print('SRTM smoothed (w = {}):'.format(window))
        print('- Variance: {:.2f}'.format(o2_srtm))
        print('- Standard deviation: {:.2f}'.format(o_srtm))
        print('- Elevation gain: {:.2f}'.format(eg_srtm))
        print('- Elevation gain with threshold: {:.2f}'.format(eg_th_srtm))
        
        if abs(eg_th_srtm - eg_orig) < min_eg_diff:
            best_altitudes = altitudes_srtm
            best_window = window
            min_eg_diff = abs(eg_th_srtm - eg_orig)
            min_o = o_srtm

    # draw diagram
    wpts = [ {'dist':w[0], 'orig':w[1], 'srtm':w[2], 'srtm_smth':w[3]} for w in zip(dists_acc, altitudes_orig, altitudes_srtm_raw, best_altitudes) ]
    fig = px.line(wpts, x='dist', y=['orig', 'srtm', 'srtm_smth'], title='Elevation profile (w={})'.format(best_window))
    fig.show()


def variance(altitudes1, altitudes2):

    if len(altitudes1) != len(altitudes2):
        raise ValueError("Both lists must be of the same size")

    sqr_sum = 0.0
    for alt1, alt2 in zip(altitudes1, altitudes2):
        sqr_sum += (alt1 - alt2) ** 2

    return sqr_sum / len(altitudes1)


def elevation_gain(altitudes):

    eg = 0.0
    for wpt1_alt, wpt2_alt in zip(altitudes[:-1], altitudes[1:]):
        ediff = wpt2_alt - wpt1_alt
        if ediff > 0.0:
            eg += ediff

    return eg


EG_THRESHOLD = 5.0
def elevation_gain_with_threshold(altitudes):
    
    eg = 0.0
    last_valid_i = 0
    for i in range(1, len(altitudes)):
        ediff = altitudes[i] - altitudes[last_valid_i]
        if abs(ediff) >= EG_THRESHOLD:
            last_valid_i = i
            if ediff > 0.0:
                eg += ediff

    return eg


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Calculates some metrics to evaluate inferred SRTM data")
    parser.add_argument("track_file", help='Input track file (GPX or TCX)')
    args = parser.parse_args()

    main(args.track_file)
