from collections import namedtuple
from typing import List
from array import array

Waypoint = namedtuple('Waypoint', 'lat, lon')
Dem = namedtuple('DEM', 'ncols, nrows, xllcenter, yllcenter, cellsize, nodataval, rows')


def set_altitudes(wpts: List[Waypoint]) -> float:
    return []
    

def srtm_load(fpath: str) -> Dem:

    with open(fpath, 'rb') as f:

        # load header values
        header_array = array('d')
        header_array.fromfile(f, 6)
        ncols = int(header_array[0])
        nrows = int(header_array[1])
        xllcenter = float(header_array[2])
        yllcenter = float(header_array[3])
        cellsize = float(header_array[4])
        nodataval = int(header_array[5])

        # load altitude values
        rows = []
        for i in range(nrows):
            row_array = array('h')
            row_array.fromfile(f, ncols)
            rows.append(list(row_array))

        return Dem(ncols, nrows, xllcenter, yllcenter, cellsize, nodataval, rows)
