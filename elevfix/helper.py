from collections import namedtuple
from typing import List
import xml.etree.ElementTree as ET
from math import radians, cos, sqrt

EARTH_RADIUS = 6371000
    
Waypoint = namedtuple('Waypoint', 'lat, lon, alt')


def tcx_parse(tcx_content: str) -> List[Waypoint]:

    ns = {
        "tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    }

    root = ET.fromstring(tcx_content)

    wpts = []
    for trpt_elem in root.findall('tcx:Activities/tcx:Activity/tcx:Lap/tcx:Track/tcx:Trackpoint', ns):
        lat = float(trpt_elem.find('tcx:Position/tcx:LatitudeDegrees', ns).text)
        lon = float(trpt_elem.find('tcx:Position/tcx:LongitudeDegrees', ns).text)
        alt = float(trpt_elem.find('tcx:AltitudeMeters', ns).text)
        wpts.append(Waypoint(lat, lon, alt))

    return wpts


def wpt_distance(wpt1: Waypoint, wpt2: Waypoint) -> float:

    # distance in 2D
    x = (radians(wpt2.lon) - radians(wpt1.lon)) * cos((radians(wpt1.lat) + radians(wpt2.lat)) / 2)
    y = radians(wpt2.lat) - radians(wpt1.lat)
    dist_2d = EARTH_RADIUS * sqrt(x**2 + y**2)

    return dist_2d
