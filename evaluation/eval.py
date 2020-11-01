import elevfix
import math
import argparse
import os
import sys

DEFAULT_VERT_THRESHOLD = 5.0

def main(dataset_dir):

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

        # original latitudes, longitudes and altitudes
        latitudes = [ wpt.lat for wpt in wpts ]
        longitudes = [ wpt.lon for wpt in wpts ]
        altitudes = [ wpt.alt for wpt in wpts ]

        # accumulated distance on each waypoint
        dists = [ elevfix.wpt_distance(wpair[0], wpair[1]) for wpair in zip(wpts[:-1], wpts[1:]) ]
        dists_acc = [ sum(dists[:i]) for i in range(len(wpts)) ]

        # SRTM raw altitudes
        alts_srtm_raw = elevfix.set_altitudes(latitudes, longitudes, smooth=False)

        dataset_entry = {
            'lats': latitudes,
            'lons': longitudes,
            'dists': dists_acc,
            'alts_orig': altitudes,
            'alts_srtm_raw': alts_srtm_raw,
        }
        dataset.append(dataset_entry)

    # SRTM raw altitudes (baseline)
    sqr_avg_dev, avg_dev = calculate_deviation(dataset, None, None, None)
    print('-\t{:.2f}\t{:.2f}'.format(sqr_avg_dev, avg_dev))
    
    # SRTM smoothed altitudes after applying Savitzky-Golay filter
    best = [None, None, 999999, None]  # window, square_avg_dev, avg_dev
    for window in range(11, 402, 10):
        for polynom in [2, 3]:
            sqr_avg_dev, avg_dev = calculate_deviation(dataset, window, DEFAULT_VERT_THRESHOLD, polynom)
            print('{}\t{}\t{:.2f}\t{:.2f}'.format(window, polynom, sqr_avg_dev, avg_dev))

            if sqr_avg_dev < best[2]:
                best = [window, polynom, sqr_avg_dev, avg_dev]

    print(best)


def calculate_deviation(dataset, savgol_window, vertical_threshold = DEFAULT_VERT_THRESHOLD, polynom = 2):

    sqr_deviation = 0.0
    deviation = 0.0
    for entry in dataset:
        eg_orig = elevation_gain(entry['alts_orig'], DEFAULT_VERT_THRESHOLD)
        if savgol_window is None and vertical_threshold is None:
            eg_srtm = elevation_gain(entry['alts_srtm_raw'], DEFAULT_VERT_THRESHOLD)
        else:
            alts_srtm = elevfix.set_altitudes(entry['lats'], entry['lons'], True, savgol_window, polynom)
            eg_srtm = elevation_gain(alts_srtm, vertical_threshold)
        current_deviation = abs(eg_srtm - eg_orig)
        sqr_deviation += (current_deviation ** 2)
        deviation += current_deviation
        
    return ( math.sqrt(sqr_deviation / len(dataset)), (deviation / len(dataset)) ) 
    

def variance(altitudes1, altitudes2):

    if len(altitudes1) != len(altitudes2):
        raise ValueError("Both lists must be of the same size")

    sqr_sum = 0.0
    for alt1, alt2 in zip(altitudes1, altitudes2):
        sqr_sum += (alt1 - alt2) ** 2

    return sqr_sum / len(altitudes1)


def elevation_gain(altitudes, threshold):
    
    eg = 0.0
    last_valid_i = 0
    for i in range(1, len(altitudes)):
        ediff = altitudes[i] - altitudes[last_valid_i]
        if abs(ediff) >= threshold:
            last_valid_i = i
            if ediff > 0.0:
                eg += ediff

    return eg


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Calculates some metrics to evaluate inferred SRTM data")
    parser.add_argument("dataset_dir", help='Input directory containing the track dataset (GPX or TCX files)')
    args = parser.parse_args()

    main(args.dataset_dir)
