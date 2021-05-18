# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Jean-Sébastien Gosselin
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import csv
import os
import os.path as osp
import re

# ---- Third party imports
import hydsensread as hsr
import numpy as np
import pandas as pd

# ---- Local imports
from correction_niveaux.utils import calc_dist_from_coord
from data_readers import MDDELCC_RSESQ_Reader
from data_readers.read_mddelcc_rses import get_wldata_from_xls


def export_station_infos_to_csv(levelfiles, barofiles, filename=None):
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

rsesq_reader = MDDELCC_RSESQ_Reader(workdir=osp.join(osp.dirname(__file__)))
rsesq_reader.load_database()

# We need to add data from Sainte-Martine manually because they were not
# published on the RSESQ website.
data = get_wldata_from_xls("data_sainte_martine_03097082.xls")
rsesq_reader._db["03097082"].update(data)

# %% Read the level and baro raw data from the Solinst csv files.

path_to_rawdatafiles = "D:/Data/rsesq_raw_15min_2017"

region = ['Monteregie',                # 0
          'Chaudiere-Appalaches',      # 1
          'centre-quebec',             # 2
          'montreal',                  # 3
          'capitale-nationale'         # 4
          ][1]

rsesq_barofiles = {}
rsesq_levelfiles = {}
rsesq_latitudes = {}
rsesq_longitudes = {}
rsesq_elevations = {}

i = 0
dirname = osp.join(path_to_rawdatafiles, region)
for file in os.listdir(dirname):
    if not file.endswith('csv'):
        continue
    i += 1
    print(i, region, file)

    solinst_file = hsr.SolinstFileReader(osp.join(dirname, file))
    solinst_file.undo_zero_point_offset()
    solinst_file.undo_altitude_correction()

    if "baro" in file.lower():
        stn_id = re.sub('[ -_]?BARO[ -_]?', '',
                        solinst_file.sites.project_name,
                        flags=re.IGNORECASE)
        if stn_id in rsesq_barofiles:
            rsesq_barofiles[stn_id].records = (
                rsesq_barofiles[stn_id].records.append(
                    solinst_file.records, sort=True))
        else:
            rsesq_barofiles[stn_id] = solinst_file
    else:
        stn_id = solinst_file.sites.project_name
        if stn_id in rsesq_levelfiles:
            rsesq_levelfiles[stn_id].records = (
                rsesq_levelfiles[stn_id].records.append(
                    solinst_file.records, sort=True))
        else:
            rsesq_levelfiles[stn_id] = solinst_file

    # Get latitude, longitude, and elevation of the well where the
    # logger is installed.
    solinst_file.sites.latitude = float(rsesq_reader[stn_id]['Latitude'])
    solinst_file.sites.longitude = float(rsesq_reader[stn_id]['Longitude'])
    try:
        solinst_file.sites.elevation = float(
            rsesq_reader[stn_id]['Elevation'])
    except KeyError:
        # We need to download the data to get the station elevation
        # because this info is not in the kml file.
        rsesq_reader.fetch_station_wldata(stn_id)
    finally:
        solinst_file.sites.elevation = float(rsesq_reader[stn_id]['Elevation'])

rsesq_latitudes[stn_id] = float(rsesq_reader[stn_id]['Latitude'])
rsesq_longitudes[stn_id] = float(rsesq_reader[stn_id]['Longitude'])
rsesq_elevations[stn_id] = float(rsesq_reader[stn_id]['Elevation'])

# %% Save the formatted data to a csv

print("Concatenating the level data... ")
leveldata_stack = None
for stn_id in rsesq_levelfiles.keys():
    for column in rsesq_levelfiles[stn_id].records:
        if column.lower().startswith('level'):
            level_data_stn = rsesq_levelfiles[stn_id].records[[column]].copy()
            # We convert into meters.
            if column.lower().endswith('_cm'):
                level_data_stn[column] = level_data_stn[column] / 100
            level_data_stn = level_data_stn.rename(columns={column: stn_id})
            break
    else:
        print("Warning: there is no level data in that record.")
        continue

    if leveldata_stack is None:
        leveldata_stack = level_data_stn
    else:
        leveldata_stack = pd.merge(leveldata_stack,
                                   level_data_stn,
                                   left_index=True,
                                   right_index=True,
                                   how='outer')
leveldata_stack.index.names = ['Date']
print('Level data concatenated successfully.')

print("Concatenating the baro data... ")
barodata_stack = None
for stn_id in rsesq_barofiles.keys():
    for column in rsesq_barofiles[stn_id].records.columns:
        if column.lower().startswith('level'):
            baro_data_stn = rsesq_barofiles[stn_id].records[[column]].copy()
            # We convert into meters.
            if column.lower().endswith('_cm'):
                baro_data_stn[column] = baro_data_stn[column] / 100
            elif column.lower().endswith('_kpa'):
                baro_data_stn[column] = baro_data_stn[column] * 0.101972
            baro_data_stn = baro_data_stn.rename(columns={column: stn_id})
            break
    else:
        print("Warning: there is no level data in that record.")
        continue
    if barodata_stack is None:
        barodata_stack = baro_data_stn
    else:
        barodata_stack = pd.merge(barodata_stack,
                                  baro_data_stn,
                                  left_index=True,
                                  right_index=True,
                                  how='outer')
barodata_stack.index.names = ['Date']
print('Baro data concatenated successfully.')

print("Saving the level and baro data to a csv... ", end='')
dirname = osp.join(osp.dirname(__file__), 'rsesq_15min_formatted_data')
filename = 'leveldata_{}_15M_LOCAL.csv'.format(region.lower())
leveldata_stack.to_csv(osp.join(dirname, filename))
filename = 'barodata_{}_15M_LOCAL.csv'.format(region.lower())
barodata_stack.to_csv(osp.join(dirname, filename))
print('done')
