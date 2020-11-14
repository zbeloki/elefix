import elefix
import math
import argparse
import os
import sys

from train import *

def main(dataset_dir, window, grade):

    # validate input directory
    if not os.path.isdir(dataset_dir):
        raise ValueError('"dataset_dir" is not a valid directory path')

    # prepare dataset
    # each dataset entry: {'lats', 'lons', 'dists', 'alts_orig', 'alts_srtm_raw'}
    dataset = []
    for fname in os.listdir(dataset_dir):
        
        # validate file
        _, ext = os.path.splitext(fname)
        fpath = os.path.join(dataset_dir, fname)
        if not os.path.isfile(fpath) or ext not in ['.gpx', '.tcx']:
            continue

        # parse input file
        with open(fpath, 'r') as f:
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

        # original latitudes, longitudes and altitudes
        latitudes = [ wpt.lat for wpt in wpts ]
        longitudes = [ wpt.lon for wpt in wpts ]
        altitudes = [ wpt.alt for wpt in wpts ]

        # accumulated distance on each waypoint
        dists = [ elefix.wpt_distance(wpair[0], wpair[1]) for wpair in zip(wpts[:-1], wpts[1:]) ]
        dists_acc = [ sum(dists[:i]) for i in range(len(wpts)) ]

        # SRTM raw altitudes
        alts_srtm_raw = elefix.set_altitudes(latitudes, longitudes, smooth=False)

        dataset_entry = {
            'lats': latitudes,
            'lons': longitudes,
            'dists': dists_acc,
            'alts_orig': altitudes,
            'alts_srtm_raw': alts_srtm_raw,
        }
        dataset.append(dataset_entry)

    # SRTM raw altitudes (baseline)
    sqr_avg_acc_dev, avg_acc_dev = calculate_acc_deviation(dataset, None, None, None)
    sqr_avg_ele_diff, avg_ele_diff = dataset_avg_elevation_diff(dataset, True, None, None)
    print('N\tG\tEGD (quadratic mean)\tEGD (mean)\tAPD (quadratic mean)\tAPD (mean)'.format(sqr_avg_acc_dev, avg_acc_dev, sqr_avg_ele_diff, avg_ele_diff))
    print('-\t-\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}'.format(sqr_avg_acc_dev, avg_acc_dev, sqr_avg_ele_diff, avg_ele_diff))
    
    # SRTM smoothed altitudes after applying Savitzky-Golay filter
    best_acc = [None, None, 999999, None]  # window, sqr_avg_acc_dev, avg_acc_dev
    best_elediff = [None, None, 999999, None]  # window, sqr_avg_ele_diff, avg_ele_diff

    sqr_avg_acc_dev, avg_acc_dev = calculate_acc_deviation(dataset, window, DEFAULT_VERT_THRESHOLD, grade)
    sqr_avg_ele_diff, avg_ele_diff = dataset_avg_elevation_diff(dataset, True, window, grade)
    print('{}\t{}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}'.format(window, grade, sqr_avg_acc_dev, avg_acc_dev, sqr_avg_ele_diff, avg_ele_diff))


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Calculates avg deviation in elev_gain and profile distance")
    parser.add_argument("dataset_dir", help='Input directory containing the track dataset (GPX or TCX files)')
    parser.add_argument("-w", dest="window", required=True, help='Savitzky-Golay parameter: window')
    parser.add_argument("-g", dest="grade", required=True, help='Savitzky-Golay parameter: polynom grade)')
    args = parser.parse_args()

    main(args.dataset_dir, int(args.window), int(args.grade))
