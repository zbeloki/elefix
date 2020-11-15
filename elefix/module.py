from collections import namedtuple
from typing import List, Tuple
from array import array
import os

import elefix.helper

Waypoint = namedtuple('Waypoint', 'lat, lon')
Point = namedtuple('Point', 'x, y, z')
BoundingBox = namedtuple('BoundingBox', 'xmin, xmax, ymin, ymax')
TileSRTM = namedtuple('TileSRTM', 'row, col')
Dem = namedtuple('DEM', 'ncols, nrows, xllcenter, yllcenter, cellsize, nodataval, rows')


def set_altitudes(latitudes: List[float], longitudes: List[float],
                  smooth: bool = True, window: int = 151, polynom: int = 2) -> List[float]:

    if 'SRTMPATH' not in os.environ:
        raise ValueError('Environment variable SRTMPATH must be set')
    
    srtm_path = os.environ['SRTMPATH']
    if srtm_path == "":
        raise ValueError('Environment variable SRTMPATH is empty')

    if not os.path.isdir(srtm_path):
        raise ValueError('The path defined in SRTMPATH is not a valid directory')
    
    if len(latitudes) != len(longitudes):
        raise ValueError('"latitudes" and "longitudes" must be of the same size')

    if len(latitudes) == 0:
        return []

    if window < 0 or window % 2 == 0:
        raise ValueError('"window" must be a positive odd number')
    
    wpts = [ Waypoint(*wpt) for wpt in zip(latitudes, longitudes) ]
    bbox = track_boundingbox(wpts)
    tiles = srtm_find_tiles(bbox)

    altitudes = [None] * len(wpts)
    for tile in tiles:
        fname = srtm_tile_build_fname(tile)
        fpath = os.path.join(srtm_path, fname)
        dem = srtm_load(fpath)
    
        for i in range(len(wpts)):
            wpt = wpts[i]
            alt = srtm_find_altitude(wpt, dem)
            if alt is not None:
                altitudes[i] = alt

    if smooth:
        altitudes = smooth_altitudes(latitudes, longitudes, altitudes, window, polynom)
        
    return altitudes


def smooth_altitudes(lats: List[float], lons: List[float], alts: List[float], win: int, polynom: int) -> List[float]:

    wpts = [ elefix.helper.Waypoint(w[0], w[1], w[2]) for w in zip(lats, lons, alts) ] 
    dists = [ elefix.helper.wpt_distance(wpair[0], wpair[1]) for wpair in zip(wpts[:-1], wpts[1:]) ]
    dists_acc = [ sum(dists[:i]) for i in range(len(wpts)) ]
    
    return elefix.helper.non_uniform_savgol(dists_acc, alts, win, polynom)
    

def track_boundingbox(wpts: List[Waypoint]) -> BoundingBox:

    xmin = 200.0
    xmax = -200.0
    ymin = 200.0
    ymax = -200.0
    for wpt in wpts:
        xmin = min(wpt.lon, xmin)
        xmax = max(wpt.lon, xmax)
        ymin = min(wpt.lat, ymin)
        ymax = max(wpt.lat, ymax)
        
    return BoundingBox(xmin, xmax, ymin, ymax)


def srtm_find_tiles(bbox: BoundingBox) -> List[TileSRTM]:

    tile_tl = srtm_find_tile(Waypoint(bbox.ymax, bbox.xmin))
    tile_br = srtm_find_tile(Waypoint(bbox.ymin, bbox.xmax))

    tiles = set()
    for col in range(tile_tl.col, tile_br.col + 1):
        for row in range(tile_tl.row, tile_br.row + 1):
            tiles.add(TileSRTM(row, col))

    return list(tiles)
        

def srtm_find_tile(wpt: Waypoint) -> TileSRTM:
        
    if wpt.lat < -60.0 or wpt.lat >= 60.0 or wpt.lon < -180.0 or wpt.lon >= 180.0:
        return None
  
    col = int((wpt.lon + 180) / 5) + 1
    row = 24 - (int((wpt.lat + 60) / 5) + 1) + 1;
    
    return TileSRTM(row, col)


def srtm_tile_build_fname(tile: TileSRTM) -> str:

    return 'srtm_{:02d}_{:02d}.bin'.format(tile.col, tile.row)
    

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


def srtm_find_altitude(wpt: Waypoint, dem: Dem) -> float:

    if wpt.lat < dem.yllcenter - (dem.cellsize / 2):
        return None
    if wpt.lat > dem.yllcenter - (dem.cellsize / 2) + (dem.nrows * dem.cellsize):
        return None
    if wpt.lon < dem.xllcenter - (dem.cellsize / 2):
        return None
    if wpt.lon > dem.xllcenter - (dem.cellsize / 2) + (dem.ncols * dem.cellsize):
        return None

    x_row_f = (wpt.lon - dem.xllcenter) / dem.cellsize
    yl_row_f = (wpt.lat - dem.yllcenter) / dem.cellsize
    y_row_f = dem.nrows - 1 - yl_row_f

    x_row = round(x_row_f)
    y_row = round(y_row_f)
    
    if x_row_f - x_row < 0:
        if x_row > 0:
            x_row_adjacent = x_row - 1
        else:
            x_row_adjacent = x_row + 1
    else:
        if x_row < dem.ncols - 1:
            x_row_adjacent = x_row + 1
        else:
            x_row_adjacent = x_row - 1    
  
    if y_row_f - y_row < 0:
        if y_row > 0:
            y_row_adjacent = y_row - 1
        else:
            y_row_adjacent = y_row + 1
    else:
        if y_row < dem.nrows - 1:
            y_row_adjacent = y_row + 1
        else:
            y_row_adjacent = y_row - 1

    x = dem.xllcenter + (x_row * dem.cellsize)
    y = dem.yllcenter + ((dem.nrows - 1 - y_row) * dem.cellsize)
    z = dem.rows[y_row][x_row]
    p1 = Point(x, y, z)

    x = dem.xllcenter + (x_row_adjacent * dem.cellsize)
    y = dem.yllcenter + ((dem.nrows - 1 - y_row) * dem.cellsize)
    z = dem.rows[y_row][x_row_adjacent]
    p2 = Point(x, y, z)

    x = dem.xllcenter + (x_row * dem.cellsize)
    y = dem.yllcenter + ((dem.nrows - 1 - y_row_adjacent) * dem.cellsize)
    z = dem.rows[y_row_adjacent][x_row]
    p3 = Point(x, y, z)

    p = Point(wpt.lon, wpt.lat, None)
    return interpolate_elevation(p, p1, p2, p3)


def interpolate_elevation(p: Point, p1: Point, p2: Point, p3: Point) -> float:

    v1_x = p2.x - p1.x
    v1_y = p2.y - p1.y
    v1_z = p2.z - p1.z
    v2_x = p3.x - p1.x
    v2_y = p3.y - p1.y
    v2_z = p3.z - p1.z
    vnorm_x = v1_y * v2_z - v1_z * v2_y
    vnorm_y = v1_z * v2_x - v1_x * v2_z
    vnorm_z = v1_x * v2_y - v1_y * v2_x
    k = 0 - (vnorm_x * p1.x) - (vnorm_y * p1.y) - (vnorm_z * p1.z)
    
    if vnorm_z == 0.0:
        return None
    
    return (0 - (vnorm_x * p.x) - (vnorm_y * p.y) - k) / vnorm_z
    
