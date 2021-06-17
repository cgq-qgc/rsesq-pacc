# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Institut National de la Recherche Scientifique (INRS)
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

"""
Script to match piezometric, barometric and earth tide data and saved
them in format that is compatible with GWHAT.
"""

# ---- Standard library imports
import csv
import os
import os.path as osp

# ---- Third party imports
import numpy as np
import pandas as pd

# ---- Local imports
from correction_niveaux.utils import (
    calc_dist_from_coord, save_content_to_csv,
    load_baro_from_narr_preprocessed_file,
    load_earthtides_from_preprocessed_file)
from data_readers import MDDELCC_RSESQ_Reader

BARO_SOURCE = ['NARR', 'RSESQ'][1]


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


# %% Read the level and baro raw data

rsesq_reader = MDDELCC_RSESQ_Reader()

# The data are read from the post-processed csv files that were created
# with the script named 'format_raw_solinst_data.py'.

dirname = osp.join(osp.dirname(__file__), 'rsesq_15min_formatted_data')
region = ['Monteregie',                # 0
          'Chaudiere-Appalaches',      # 1
          'centre-quebec',             # 2
          'montreal',                  # 3
          'capitale-nationale'         # 4
          ][1]

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
filename = "leveldata_{}_15M_LOCAL.csv".format(region)
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


# %% Load NARR Baro data from preprocessed csv file.

# The 'patm_narr_data.csv' file is generated from the NARR netCDF files with
# the script 'get_data_from_narr.py'

if BARO_SOURCE == 'NARR':
    narr_baro = load_baro_from_narr_preprocessed_file()
else:
    narr_baro = None


# %% Load Earthtides data from preprocessed csv file.

synth_earthtides = load_earthtides_from_preprocessed_file()

# %% Format the piezo, baro and earth tides data.

nlevel = len(rsesq_level_stations)
print('{:<8s}'.format('Piezo_id'), '{:<8s}'.format('Baro_id'),
      '{:>5s}'.format('dist'), '{:>6s}'.format('delev'),
      '  Location')
print('{:<8s}'.format(''), '{:<8s}'.format(''),
      '{:>5s}'.format('(km)'), '{:>6s}'.format('(m)'))

for stn_id in rsesq_level_stations[:]:
    stn_lat = float(rsesq_reader[stn_id]['Latitude'])
    stn_lon = float(rsesq_reader[stn_id]['Longitude'])
    stn_elev = float(rsesq_reader[stn_id]['Elevation'])

    # Get the synthetic earth tides data that were produced for this
    # observation well.
    etdata = synth_earthtides[[stn_id]]

    # Get the piezometric data from the RSESQ.
    leveldata = rsesq_level[[stn_id]]
    leveldata.rename(columns={stn_id: 'WL(m)'}, inplace=True)

    # Associate a barometric pressure time series from NARR or RSESQ to
    # the piezometric station stn_id.
    if BARO_SOURCE == 'NARR':
        baro_stn = 'NARR grid'
        delta_elev = 0
        barodata = narr_baro[[stn_id]]
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

    # Drop nan.
    etdata = etdata.dropna()
    barodata = barodata.dropna()
    leveldata = leveldata.dropna()

    # Drop duplicates.
    etdata = etdata[~etdata.index.duplicated()]
    barodata = barodata[~barodata.index.duplicated()]
    leveldata = leveldata[~leveldata.index.duplicated()]

    # Join the data.
    data = pd.merge(leveldata, barodata,
                    left_index=True, right_index=True, how='inner')
    data = pd.merge(data, etdata,
                    left_index=True, right_index=True, how='inner')

    # Resample and interpolate missing values if any.
    data = data.resample('1H').asfreq()
    data = data.interpolate(method='linear')

    # Save the data to a file.
    foldername = osp.join(
        osp.dirname(__file__), 'water_levels_for_brf_eval_1hour')
    if not osp.exists(foldername):
        os.makedirs(foldername)
    filename = '{}_{}_{}_baro.csv'.format(
        region.lower(), stn_id, BARO_SOURCE.lower())

    # Compensate transform the level data in mbgs.
    data['WL(m)'] = data['WL(m)'] - data['BP(m)']
    data['WL(m)'] = np.max(data['WL(m)']) - data['WL(m)']

    # Convert time to string format.
    datetimes = data.index.strftime("%Y-%m-%dT%H:%M:%S").values.tolist()

    # Save data to files.
    fcontent = [[datetimes[i]] + data.iloc[i].tolist() for
                i in range(len(datetimes))]
    save_content_to_csv(osp.join(foldername, filename), fheader + fcontent)
