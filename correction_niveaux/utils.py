# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Jean-Sébastien Gosselin
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

# ---- Standard party imports
import csv
from datetime import datetime, timedelta
import os.path as osp
# ---- Third party imports
import numpy as np
import pandas as pd
import rasterio
import xlsxwriter
# ---- Local imports
from data_readers import MDDELCC_RSESQ_Reader


PATH_TO_ARCV3TIF = "D:/Data/mne_arc_v3_tifs"
PATH_TO_RSESQ_DATA = "D:/Data"


def calc_dist_from_coord(lat1, lon1, lat2, lon2):
    """
    Compute the  horizontal distance in km between a location given in
    decimal degrees and a set of locations also given in decimal degrees.
    """
    lat1, lon1 = np.radians(lat1), np.radians(lon1)
    lat2, lon2 = np.radians(lat2), np.radians(lon2)

    r = 6373  # r is the Earth radius in km

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    return r * c


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


def download_drillogs(dirname):
    """Download the drillogs pdf from the RSESQ web site."""
    rsesq_reader = MDDELCC_RSESQ_Reader(workdir=PATH_TO_RSESQ_DATA)
    rsesq_reader.load_database()

    for stn_id in rsesq_reader.station_ids():
        print('\rDownloading drillogs {}'.format(stn_id), end='')
        rsesq_reader.dwnld_piezo_drilllog(stn_id, dirname)
    print('')


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


def load_baro_from_narr_preprocessed_file():
    print("Loading NARR barometric data... ", end='')
    patm_narr_fname = osp.join(osp.dirname(__file__), "patm_narr_data.csv")

    # Get the barometric data.
    narr_baro = pd.read_csv(patm_narr_fname, header=6)
    narr_baro['Date'] = pd.to_datetime(
        narr_baro['Date'], format="%Y-%m-%d %H:%M:%S")
    narr_baro.set_index(['Date'], drop=True, inplace=True)

    # !!! It is important to shift the data by 5 hours to match the
    #     local time of the data from the RSESQ.
    narr_baro.index = narr_baro.index - pd.Timedelta(hours=5)
    print("done")
    return narr_baro


def load_earthtides_from_preprocessed_file():
    print("Loading Earth tides synthetic data... ", end='')
    synth_earthtides = pd.read_csv(osp.join(
        osp.dirname(__file__), 'synthetic_earthtides_1980-2018_1H_UTC.csv'))
    synth_earthtides['Date'] = pd.to_datetime(
        synth_earthtides['Date'], format="%Y-%m-%d %H:%M:%S")
    synth_earthtides.set_index(['Date'], drop=True, inplace=True)

    # !!! It is important to shift the data by 5 hours to match the
    #     local time of the data from the RSESQ.
    synth_earthtides.index = synth_earthtides.index - pd.Timedelta(hours=5)
    print("done")
    return synth_earthtides


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


def save_content_to_csv(fname, fcontent, mode='w', delimiter=',',
                        encoding='utf8'):
    """
    Save fcontent in a csv file with the specifications provided
    in arguments.
    """
    with open(fname, mode, encoding='utf8') as csvfile:
        writer = csv.writer(csvfile, delimiter=delimiter, lineterminator='\n')
        writer.writerows(fcontent)


def save_content_to_excel(fname, fcontent):
    """Save content in a xls or xlsx file."""
    with xlsxwriter.Workbook(fname) as wb:
        ws = wb.add_worksheet('Data')
        for i, row in enumerate(fcontent):
            ws.write_row(i, 0, row)
