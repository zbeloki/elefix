import elefix
import math
import argparse
import os

import plotly.express as px

from eval import elevation_gain, track_avg_elevation_diff, DEFAULT_VERT_THRESHOLD

# optimized parameters
DEF_SAVGOL_WINDOW = 151
DEF_SAVGOL_GRADE = 2


def main(track_fpath, window, grade):

    # validate input
    fname, ext = os.path.splitext(track_fpath)
    if ext.lower() not in ['.gpx', '.tcx']:
        raise ValueError("Input file's format must be GPX or TCX")

    # parse input file
    with open(track_fpath, 'r') as f:
        track_content = f.read()
        if ext.lower() == '.gpx':
            wpts = elefix.gpx_parse(track_content)
        else:  # ext.lower() == '.tcx'
            wpts = elefix.tcx_parse(track_content)

    # remove waypoints for which the distance to the next one is 0
    i = 0
    while i < len(wpts)-1:
        if elefix.wpt_distance(wpts[i], wpts[i+1]) == 0.0:
            del wpts[i]
        else:
            i += 1

    # parsed original latitudes, longitudes and altitudes
    latitudes = [ wpt.lat for wpt in wpts ]
    longitudes = [ wpt.lon for wpt in wpts ]
    altitudes_orig = [ wpt.alt for wpt in wpts ]

    # accumulated distance on each waypoint
    dists = [ elefix.wpt_distance(wpair[0], wpair[1]) for wpair in zip(wpts[:-1], wpts[1:]) ]
    dists_acc = [ sum(dists[:i]) for i in range(len(wpts)) ]
    totaldist = dists_acc[-1]

    # original accumulated elevation gain
    eg_orig = elevation_gain(altitudes_orig, totaldist, DEFAULT_VERT_THRESHOLD)
    
    # SRTM raw altitudes
    altitudes_srtm_raw = elefix.set_altitudes(latitudes, longitudes, smooth=False)
    eg_srtm_raw = elevation_gain(altitudes_srtm_raw, totaldist, DEFAULT_VERT_THRESHOLD)
    diff_srtm_raw = track_avg_elevation_diff(dists_acc, altitudes_orig, altitudes_srtm_raw, True)
    
    # SRTM smoothed altitudes
    altitudes_srtm = elefix.set_altitudes(latitudes, longitudes, True, window, grade)
    eg_srtm = elevation_gain(altitudes_srtm, totaldist, DEFAULT_VERT_THRESHOLD)
    diff_srtm = track_avg_elevation_diff(dists_acc, altitudes_orig, altitudes_srtm, True)

    # print elevation gain values
    print("Elevation gain (original): {:.2f}".format(eg_orig * (totaldist/1000)))
    print("Elevation gain (SRTM + smoothing): {:.2f}".format(eg_srtm * (totaldist/1000))) 
    print("Elevation gain (raw SRTM): {:.2f}".format(eg_srtm_raw * (totaldist/1000)))
    print("Avg elevation diff (SRTM + smoothing): {:.2f}".format(diff_srtm))
    print("Avg elevation diff (raw SRTM): {:.2f}".format(diff_srtm_raw))
    
    # draw diagram
    wpts = []
    for w in zip(dists_acc, altitudes_orig, altitudes_srtm_raw, altitudes_srtm):
        wpts.append({'dist':w[0], 'type':'Original', 'alt':w[1]})
        wpts.append({'dist':w[0], 'type':'SRTM', 'alt':w[2]})
        wpts.append({'dist':w[0], 'type':'SRTM + Savitzky-Golay', 'alt':w[3]})
    fig = px.line(wpts, x='dist', y='alt', color='type', template='simple_white',
                  labels={
                      'dist': 'Distance',
                      'alt': 'Altitude',
                      'type': 'Data source',
                  })
    fig.update_traces(patch={"line":{"color":"blue", "width":1}}, 
                      selector={"legendgroup":"Original"})
    fig.update_traces(patch={"line":{"color":"red", "width":1}}, 
                      selector={"legendgroup":"SRTM"})
    fig.update_traces(patch={"line":{"color":"green", "width":1}}, 
                      selector={"legendgroup":"SRTM + Savitzky-Golay"})
    fig.show()


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Calculates elevation data based on SRTM and applies Savitzky-Golay smoothing filter")
    parser.add_argument("track_file", help='Input track file (GPX or TCX)')
    parser.add_argument("-w", "--window", required=False, default=DEF_SAVGOL_WINDOW, type=int, help='Smoothing window')
    parser.add_argument("-g", "--grade", required=False, default=DEF_SAVGOL_GRADE, type=int, choices=[2,3], help='Smoothing polynom grade')
    args = parser.parse_args()

    main(args.track_file, args.window, args.grade)
