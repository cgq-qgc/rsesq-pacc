# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Jean-Sébastien Gosselin
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

import os.path as osp
import csv
from datetime import datetime, timedelta
import numpy as np
import rasterio
import pandas as pd


PATH_TO_ARCV3TIF = "D:/Data/mne_arc_v3_tifs"


def calcul_center_latlon(lat, lon):
    """
    Calcul the centroid of a list of lat/lon coordinates.
    """
    # Based on https://gist.github.com/amites/3718961
    lat, lon = np.radians(lat), np.radians(lon)

    x = np.mean(np.cos(lat) * np.cos(lon))
    y = np.mean(np.cos(lat) * np.sin(lon))
    z = np.mean(np.sin(lat))

    lon_ctr = np.arctan2(y, x)
    hyp = (x**2 + y**2)**0.5
    lat_ctr = np.arctan2(z, hyp)

    return np.degrees(lat_ctr), np.degrees(lon_ctr)


def get_elevation_from_larc_tif(lat, lon):
    """
    Get the elevation of the specified lat/lon corrdinates in decimal degrees
    from a 1arc_v3 tif files.
    https://power.larc.nasa.gov/data-access-viewer/
    """
    filename = '{}{:2d}_{}{:0>3d}_1arc_v3.tif'.format(
        'n' if lat > 0 else 's', int(lat),
        'e' if lon > 0 else 'w', int(abs(lon) + 1)
        )
    filepath = osp.join(PATH_TO_ARCV3TIF, filename)

    raster = rasterio.open(filepath)
    elev = next(raster.sample([(lat, lon)], indexes=[1]))[0]
    print('lat={:.3f}° lon={:.3f}° alt={:d}m'.format(lat, lon, elev))

    # img = raster.read()
    # img_plt = plt.imshow(img[0, :, :], cmap='gray')

    return elev


def read_tsoft_expchan(filename, tstart, tdelta):
    """
    Read the Earth tides data from a file produced with TSoft.
    http://seismologie.oma.be/en/downloads/tsoft
    """
    with open(filename) as csvfile:
        reader = list(csv.reader(csvfile, delimiter=' '))
    data = np.zeros(len(reader))
    for i, line in enumerate(reader):
        data[i] = [float(d) for d in line if d][1]

    dt0 = datetime.strptime(tstart, '%Y-%m-%d %H:%M:%S')
    dtarr = [dt0 + timedelta(minutes=(i * 15)) for i in range(len(data))]

    return pd.DataFrame(data, dtarr, columns=['earth_tides(nm/s2)'])
