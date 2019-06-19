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
import os
import os.path as osp
import re
# ---- Third party imports
import netCDF4
import hydsensread as hsr
import numpy as np
import pandas as pd
# ---- Local imports
from correction_niveaux.utils import calc_dist_from_coord, save_content_to_csv
from data_readers import MDDELCC_RSESQ_Reader
from data_readers.read_mddelcc_rses import get_wldata_from_xls

BARO_SOURCE = ['NARR', 'RSESQ'][1]


def save_to_gwhat_file(filename, leveldata, barodata, etdata, fheader):
    """
    Save the level, baro and earth tides data to a csv file in the GWHAT
    format.
    """
    # Join the data.
    data = pd.merge(leveldata, barodata,
                    left_index=True, right_index=True, how='inner')
    data = pd.merge(data, etdata,
                    left_index=True, right_index=True, how='inner')

    # Compensate transform the level data in mbgs.
    data['WL(m)'] = data['WL(m)'] - data['BP(m)']
    data['WL(m)'] = np.max(data['WL(m)']) - data['WL(m)']

    # Interpolate missing values if any.
    data = data.interpolate(method='linear')

    # Convert time to string format.
    datetimes = data.index.strftime("%Y-%m-%dT%H:%M:%S").values.tolist()

    # Save data to files.
    fcontent = [[datetimes[i]] + data.iloc[i].tolist() for
                i in range(len(datetimes))]
    save_content_to_csv(filename, fheader + fcontent)

    return fheader + fcontent


def export_to_csv(levelfiles, barofiles, filename=None):
    """
    Match each levelfile with a barofile and generate a summary table that is
    saved in a csv file.
    """
    fcontent = [["#", "Well_ID", "Location",
                 "Latitude_ddeg", "Longitude_ddeg", "Elevation_m",
                 "Delta_dist_baro_km", "Delta_elev_baro_m"]]

    baro_stations = list(barofiles.keys())
    baro_latitudes = np.array(
        [barofiles[stn].sites.latitude for stn in baro_stations])
    baro_longitudes = np.array(
        [barofiles[stn].sites.longitude for stn in baro_stations])

    print('#  ', '{:<8s}'.format('Piezo_id'), '{:<8s}'.format('Baro_id'),
          '{:>5s}'.format('dist'), '{:>6s}'.format('delev'),
          '  Location')
    print('   ', '{:<8s}'.format(''), '{:<8s}'.format(''),
          '{:>5s}'.format('(km)'), '{:>6s}'.format('(m)'))
    for i, stn_id in enumerate(sorted(list(levelfiles.keys()))):
        level_latitude = levelfiles[stn_id].sites.latitude
        level_longitude = levelfiles[stn_id].sites.longitude
        level_elevation = levelfiles[stn_id].sites.elevation

        dist = calc_dist_from_coord(baro_latitudes, baro_longitudes,
                                    level_latitude, level_longitude)
        baro_stn = baro_stations[np.argmin(dist)]
        delta_elev = (level_elevation - barofiles[baro_stn].sites.elevation)

        print('{:02d} '.format(i + 1),
              '{:<8s}'.format(stn_id),
              '{:<8s}'.format(baro_stn),
              '{:5.1f}'.format(np.min(dist)),
              '{:-6.1f}'.format(delta_elev),
              '  {}'.format(levelfiles[stn_id].sites.site_name)
              )

        fcontent.append(
            ["{:02d}".format(i), stn_id, levelfiles[stn_id].sites.site_name,
             "{}".format(level_latitude), "{}".format(level_longitude),
             "{}".format(level_elevation),
             "{:.1f}".format(np.min(dist)), "{:.1f}".format(delta_elev)
             ])

    if filename:
        root, ext = osp.splitext(filename)
        with open(root + '.csv', 'w', encoding='utf8') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', lineterminator='\n')
            writer.writerows(fcontent)


# %% Read data from the RSESQ

rsesq_reader = MDDELCC_RSESQ_Reader(workdir='D:/Data')
rsesq_reader.load_database()

# We need to add data from Sainte-Martine manually because they were not
# published on the RSESQ website.
data = get_wldata_from_xls("D:/Data/Données_03097082.xls")
rsesq_reader._db["03097082"].update(data)

# %% Read the level and baro raw data from the Solinst csv files.

dirname = osp.join(osp.dirname(__file__), '15min_formatted_data')
region = ['monteregie'][0]

# Get the baro data.
filename = "barodata_{}_15M_LOCAL.csv".format(region)
rsesq_baro = pd.read_csv(osp.join(dirname, filename))
rsesq_baro['Date'] = pd.to_datetime(
    rsesq_baro['Date'], format="%Y-%m-%d %H:%M:%S")
rsesq_baro.set_index(['Date'], drop=True, inplace=True)

rsesq_baro_stations = rsesq_baro.columns.tolist()
rsesq_baro_latitudes = np.array(
    [float(rsesq_reader[sid]['Latitude']) for sid in rsesq_baro_stations])
rsesq_baro_longitudes = np.array(
    [float(rsesq_reader[sid]['Longitude']) for sid in rsesq_baro_stations])
rsesq_baro_elevations = np.array(
    [float(rsesq_reader[sid]['Elevation']) for sid in rsesq_baro_stations])

# Get the level data.
filename = "leveldata_monteregie_15M_LOCAL.csv"
rsesq_level = pd.read_csv(osp.join(dirname, filename))
rsesq_level['Date'] = pd.to_datetime(
    rsesq_level['Date'], format="%Y-%m-%d %H:%M:%S")
rsesq_level.set_index(['Date'], drop=True, inplace=True)

rsesq_level_stations = rsesq_level.columns.tolist()
rsesq_level_latitudes = np.array(
    [float(rsesq_reader[sid]['Latitude']) for sid in rsesq_level_stations])
rsesq_level_longitudes = np.array(
    [float(rsesq_reader[sid]['Longitude']) for sid in rsesq_level_stations])
rsesq_level_elevations = np.array(
    [float(rsesq_reader[sid]['Elevation']) for sid in rsesq_level_stations])


# %% Load NARR data from csv file.

# The 'patm_narr_data.csv' file is generated from the NARR netCDF files with
# the script 'get_data_from_narr.py'

if BARO_SOURCE == 'NARR':
    print("Loading NARR barometric data... ", end='')
    patm_narr_fname = osp.join(osp.dirname(__file__), "patm_narr_data.csv")

    # Get the barometric data.
    narr_baro = pd.read_csv(patm_narr_fname, header=6)
    narr_baro['Date'] = pd.to_datetime(
        narr_baro['Date'], format="%Y-%m-%d %H:%M:%S")
    narr_baro.set_index(['Date'], drop=True, inplace=True)
    print("done")

# %% Read the synthetic Earth tides.

print("Loading Earth tides synthetic data... ", end='')
synth_earthtides = pd.read_csv(osp.join(
    osp.dirname(__file__), 'synthetic_earthtides_1980-2018_1H_UTC.csv'))
synth_earthtides['Date'] = pd.to_datetime(
    synth_earthtides['Date'], format="%Y-%m-%d %H:%M:%S")
synth_earthtides.set_index(['Date'], drop=True, inplace=True)
print("done")

# %% Format the piezo, baro and earth tides data.

nlevel = len(rsesq_level_stations)
print('{:<8s}'.format('Piezo_id'), '{:<8s}'.format('Baro_id'),
      '{:>5s}'.format('dist'), '{:>6s}'.format('delev'),
      '  Location')
print('{:<8s}'.format(''), '{:<8s}'.format(''),
      '{:>5s}'.format('(km)'), '{:>6s}'.format('(m)'))

for stn_id in rsesq_level_stations:
    stn_lat = float(rsesq_reader[stn_id]['Latitude'])
    stn_lon = float(rsesq_reader[stn_id]['Longitude'])
    stn_elev = float(rsesq_reader[stn_id]['Elevation'])

    # Generate the synthetic earth tides data.
    etdata = synth_earthtides[[stn_id]]
    etdata.index = etdata.index - pd.Timedelta(hours=5)
    # !!! It is important to shift the data by 5 hours to match the local time
    #     of the data from the RSESQ,

    # Get the piezometric data from the RSESQ.
    leveldata = rsesq_level[[stn_id]]
    leveldata.rename(columns={stn_id: 'WL(m)'}, inplace=True)

    # Associate a barometric pressure time series from NARR or RSESQ to
    # the piezometric station stn_id.
    if BARO_SOURCE == 'NARR':
        baro_stn = 'NARR grid'
        delta_elev = 0

        barodata = narr_baro[[stn_id]]
        barodata.index = barodata.index - pd.Timedelta(hours=5)
        # !!! It is important to shift the data by 5 hours to match the
        #     local time of the data from the RSESQ,
    elif BARO_SOURCE == 'RSESQ':
        dist = calc_dist_from_coord(
            rsesq_baro_latitudes, rsesq_baro_longitudes, stn_lat, stn_lon)
        baro_stn = rsesq_baro_stations[np.argmin(dist)]
        barodata = rsesq_baro[[baro_stn]]
        delta_elev = (rsesq_reader[stn_id]['Elevation'] -
                      rsesq_reader[baro_stn]['Elevation'])
    barodata.rename(columns={baro_stn: 'BP(m)'}, inplace=True)

    # Prepare the file header.
    name = rsesq_reader[stn_id]['Name']
    fheader = [['Well Name', name],
               ['Well ID', stn_id],
               ['Latitude', rsesq_reader[stn_id]['Latitude']],
               ['Longitude', rsesq_reader[stn_id]['Longitude']],
               ['Altitude', rsesq_reader[stn_id]['Elevation']],
               ['Province', 'Qc'],
               [''],
               ['Date', 'WL(mbgs)', 'BP(m)', 'ET']
               ]

    print('{:<8s}'.format(stn_id),
          '{:<8s}'.format(baro_stn),
          '{:5.1f}'.format(np.min(dist)),
          '{:-6.1f}'.format(delta_elev),
          '  {}'.format(name)
          )

    etdata = etdata[~etdata.index.duplicated()]
    etdata = etdata.resample('3H').asfreq()
    barodata = barodata.resample('3H').asfreq()
    leveldata = leveldata.resample('3H').asfreq()

    if True:
        foldername = osp.join(osp.dirname(__file__), '15min_formatted_data')
        if not osp.exists(foldername):
            os.makedirs(foldername)
        filename = '{}_{}_{}_baro.csv'.format(
            region.lower(), stn_id, BARO_SOURCE.lower())
        fcontent = save_to_gwhat_file(osp.join(foldername, filename),
                                      leveldata, barodata, etdata, fheader)

    break
