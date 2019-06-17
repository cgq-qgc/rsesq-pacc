# -*- coding: utf-8 -*-
"""
Created on Thu Mar 28 14:20:59 2019
@author: User
"""

import re
import os
import os.path as osp
from readers import MDDELCC_RSESQ_Reader
import hydsensread as hsr
import h5py
import six
import numpy as np


# %% Read level and baro raw data

root = ("D:/Data/rsesq_donnees_15min_2017")
rsesq_reader = MDDELCC_RSESQ_Reader(workdir="D:/Data")
rsesq_reader.load_database()

period = ['Printemps', 'Automne'][1]
region = ['Monteregie', 'Chaudière-Appalaches'][0]

barofiles = {}
levelfiles = {}
latitudes = {}
longitudes = {}
elevations = {}

i = 0
for period in ['Printemps', 'Automne']:
    dirname = osp.join(root, "raw_data/{}/{}".format(period, region))
    for file in os.listdir(dirname):
        if not file.endswith('csv'):
            continue
        i += 1
        print(i, period, region, file)

        solinst_file = hsr.SolinstFileReader(osp.join(dirname, file))
        if "baro" in file.lower():
            stn_id = re.sub(
                '[ -_]?BARO[ -_]?', '', solinst_file.sites.project_name)
            if stn_id in barofiles:
                barofiles[stn_id].records = barofiles[stn_id].records.append(
                    solinst_file.records)
            else:
                barofiles[stn_id] = solinst_file
        else:
            stn_id = solinst_file.sites.project_name
            levelfiles[stn_id] = solinst_file

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
            solinst_file.sites.elevation = float(
                rsesq_reader[stn_id]['Elevation'])

        latitudes[stn_id] = float(rsesq_reader[stn_id]['Latitude'])
        longitudes[stn_id] = float(rsesq_reader[stn_id]['Longitude'])
        elevations[stn_id] = float(rsesq_reader[stn_id]['Elevation'])

# %% Save barologger data to hdf5file

hdf5file = h5py.File(osp.join(root, 'barodata.hdf5'), 'w')
for stn_id in barofiles.keys():
    grp = hdf5file.create_group(stn_id)

    records = barofiles[stn_id].records

    strftimes = records.index.strftime().values.tolist()
    strftimes = np.array(strftimes,
                         dtype=h5py.special_dtype(vlen=six.text_type))

    barodata = records['Level_m'].values

    grp.attrs['latitude'] = latitudes[stn_id]
    grp.attrs['longitude'] = longitudes[stn_id]
    grp.attrs['elevation'] = elevations[stn_id]

    grp.create_dataset('date', data=strftimes)
    grp.create_dataset('baro_m', data=barodata)

    print(stn_id)
hdf5file.close()
