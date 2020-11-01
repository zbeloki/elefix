import elevfix
import math
import argparse
import os

import plotly.express as px

from eval import elevation_gain, DEFAULT_VERT_THRESHOLD

SAVGOL_WINDOW = 231
SAVGOL_ORDER = 3

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

    # original accumulated elevation gain
    eg_orig = elevation_gain(altitudes_orig, DEFAULT_VERT_THRESHOLD)
    
    # SRTM raw altitudes
    altitudes_srtm_raw = elevfix.set_altitudes(latitudes, longitudes, smooth=False)
    eg_srtm_raw = elevation_gain(altitudes_srtm_raw, DEFAULT_VERT_THRESHOLD)
    
    # SRTM smoothed altitudes
    altitudes_srtm = elevfix.set_altitudes(latitudes, longitudes, True, SAVGOL_WINDOW, SAVGOL_ORDER)
    eg_srtm = elevation_gain(altitudes_srtm, DEFAULT_VERT_THRESHOLD)

    # print elevation gain values
    print("Elevation gain (original): {:.2f}".format(eg_orig))
    print("Elevation gain (raw SRTM): {:.2f}".format(eg_srtm_raw))
    print("Elevation gain (SRTM + smoothing): {:.2f}".format(eg_srtm)) 

    # draw diagram
    wpts = [ {'dist':w[0], 'orig':w[1], 'srtm_raw':w[2], 'srtm_smth':w[3]} for w in zip(dists_acc, altitudes_orig, altitudes_srtm_raw, altitudes_srtm) ]
    fig = px.line(wpts, x='dist', y=['orig', 'srtm_raw', 'srtm_smth'], title='Elevation profile')
    fig.show()


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Calculates elevation data based on SRTM and applies Savitzky-Golay smoothing filter")
    parser.add_argument("track_file", help='Input track file (GPX or TCX)')
    args = parser.parse_args()

    main(args.track_file)
