# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Jean-Sébastien Gosselin
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import os
import os.path as osp
import re

# ---- Third party imports
import hydsensread as hsr
import pandas as pd


region = ['Monteregie',
          'Chaudiere-Appalaches',
          'centre-quebec',
          'montreal',
          'capitale-nationale'
          ][3]

rsesq_barofiles = {}
rsesq_levelfiles = {}

i = 0
dirname = osp.join(osp.dirname(__file__), region)
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
dirname = osp.dirname(__file__)
filename = 'formatted_leveldata_{}_15min_LOCALTIME.csv'.format(region.lower())
leveldata_stack.to_csv(osp.join(dirname, filename))
filename = 'formatted_barodata_{}_15min_LOCALTIME.csv'.format(region.lower())
barodata_stack.to_csv(osp.join(dirname, filename))
print('done')
