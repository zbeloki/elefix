import elefix
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
    #for window in range(11, 402, 10):
    for window in range(11, 602, 10):
        for polynom in [2, 3]:
            sqr_avg_acc_dev, avg_acc_dev = calculate_acc_deviation(dataset, window, DEFAULT_VERT_THRESHOLD, polynom)
            sqr_avg_ele_diff, avg_ele_diff = dataset_avg_elevation_diff(dataset, True, window, polynom)
            print('{}\t{}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}'.format(window, polynom, sqr_avg_acc_dev, avg_acc_dev, sqr_avg_ele_diff, avg_ele_diff))

            if sqr_avg_acc_dev < best_acc[2]:
                best_acc = [window, polynom, sqr_avg_acc_dev, avg_acc_dev]
            if sqr_avg_ele_diff < best_elediff[2]:
                best_elediff = [window, polynom, sqr_avg_ele_diff, avg_ele_diff]

    print(best_acc)
    print(best_elediff)

    
def calculate_acc_deviation(dataset, savgol_window, vertical_threshold = DEFAULT_VERT_THRESHOLD, polynom = 2):

    sqr_deviation = 0.0
    deviation = 0.0
    for entry in dataset:
        totaldist = entry['dists'][-1]
        eg_orig = elevation_gain(entry['alts_orig'], totaldist, DEFAULT_VERT_THRESHOLD)
        if savgol_window is None and vertical_threshold is None:
            eg_srtm = elevation_gain(entry['alts_srtm_raw'], totaldist, DEFAULT_VERT_THRESHOLD)
        else:
            alts_srtm = elefix.set_altitudes(entry['lats'], entry['lons'], True, savgol_window, polynom)
            eg_srtm = elevation_gain(alts_srtm, totaldist, vertical_threshold)
        current_deviation = abs(eg_srtm - eg_orig)
        sqr_deviation += (current_deviation ** 2)
        deviation += current_deviation
        
    return ( math.sqrt(sqr_deviation / len(dataset)), (deviation / len(dataset)) ) 


def dataset_avg_elevation_diff(dataset, overlap, savgol_window, polynom = 2):

    sqr_elev_diff = 0.0
    elev_diff = 0.0
    for entry in dataset:
        dists = entry['dists']
        alts1 = entry['alts_orig']
        if savgol_window is None:
            alts2 = entry['alts_srtm_raw']
        else:
            alts2 = elefix.set_altitudes(entry['lats'], entry['lons'], True, savgol_window, polynom)
        entry_elev_diff = track_avg_elevation_diff(dists, alts1, alts2, overlap)
        sqr_elev_diff += (entry_elev_diff ** 2)
        elev_diff += entry_elev_diff
        
    return ( math.sqrt(sqr_elev_diff / len(dataset)), (elev_diff / len(dataset)) )


def track_avg_elevation_diff(dists_acc, alts1, alts2, overlap):
    
    if overlap:
        avg_alt_1 = sum(alts1) / len(alts1)
        alts1 = [ alt - avg_alt_1 for alt in alts1 ]
        avg_alt_2 = sum(alts2) / len(alts2)
        alts2 = [ alt - avg_alt_2 for alt in alts2 ]

    n_coords = len(dists_acc)
    coords1 = list(zip(dists_acc, alts1))
    coords2 = list(zip(dists_acc, alts2))

    elev_diffs = []
    for i in range(n_coords-1):
        seg1 = ( coords1[i], coords1[i+1] )
        seg2 = ( coords2[i], coords2[i+1] )
        intersec = seg_intersection(seg1, seg2)
        if intersec is None:
            avg_diff = seg_avg_elev_diff(seg1, seg2)
            dist = seg1[1][0] - seg1[0][0]
            elev_diffs.append( (dist, avg_diff) )
        else:
            seg1 = ( seg1[0], intersec )
            seg2 = ( seg2[0], intersec )
            avg_diff = seg_avg_elev_diff(seg1, seg2)
            dist = seg1[1][0] - seg1[0][0]
            elev_diffs.append( (dist, avg_diff) )
            seg1 = ( intersec, seg1[1] )
            seg2 = ( intersec, seg2[1] )
            avg_diff = seg_avg_elev_diff(seg1, seg2)
            dist = seg1[1][0] - seg1[0][0]
            elev_diffs.append( (dist, avg_diff) )

    total_avg_diff = sum([ dist * ediff for dist, ediff in elev_diffs ]) / dists_acc[-1]

    return total_avg_diff
    

def seg_intersection(seg1, seg2):

    if seg1[0][0] == seg1[1][0]:  # equal points, no distance between both (!)
        return None
    
    line1 = line_constants(seg1[0], seg1[1])
    line2 = line_constants(seg2[0], seg2[1])

    if line1[0] == line2[0]:  # equal slope => no intersection
        return None
    
    intersec_x = (line2[1] - line1[1]) / (line1[0] - line2[0])  
    intersec_y = (line1[0] * intersec_x) + line1[1]

    if intersec_x <= seg1[0][0] or intersec_x >= seg1[1][0]:
        return None
    else:
        return (intersec_x, intersec_y)
    

def line_constants(p1, p2):
    # line =>  y = ax + b
    # return (a, b)
    a = (p2[1] - p1[1]) / (p2[0] - p1[0])
    b = p1[1] - (a * p1[0])
    return (a, b)
    

def seg_avg_elev_diff(seg1, seg2):
    diff_p1 = seg2[0][1] - seg1[0][1]
    diff_p2 = seg2[1][1] - seg1[1][1]
    return (abs(diff_p1) + abs(diff_p2)) / 2


def variance(altitudes1, altitudes2):

    if len(altitudes1) != len(altitudes2):
        raise ValueError("Both lists must be of the same size")

    sqr_sum = 0.0
    for alt1, alt2 in zip(altitudes1, altitudes2):
        sqr_sum += (alt1 - alt2) ** 2

    return sqr_sum / len(altitudes1)


def elevation_gain(altitudes, distance, threshold):
    """Elevation gain per km """
    
    eg = 0.0
    last_valid_i = 0
    for i in range(1, len(altitudes)):
        ediff = altitudes[i] - altitudes[last_valid_i]
        if abs(ediff) >= threshold:
            last_valid_i = i
            if ediff > 0.0:
                eg += ediff

    return (eg / distance) * 1000


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Finds best parameters to optimize the smoothing algorithm")
    parser.add_argument("dataset_dir", help='Input directory containing the track dataset (GPX or TCX files)')
    args = parser.parse_args()

    main(args.dataset_dir)
