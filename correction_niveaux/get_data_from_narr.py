# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Jean-Sébastien Gosselin
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

"""
This script matches the piezometric stations of the RSESQ with the barometric
data of the NARR data grid.

ftp://ftp.cdc.noaa.gov/Datasets/NARR/monolevel/
"""

import netCDF4
import os.path as osp
import numpy as np
from data_readers import MDDELCC_RSESQ_Reader
from pyhelp.utils import calc_dist_from_coord
from pyhelp.utils import save_content_to_csv
import datetime
import pandas as pd

path_to_narr = "D:/Data/baro_naar"

# %%

rsesq_reader = MDDELCC_RSESQ_Reader(workdir="D:/Data")
rsesq_reader.load_database()

stations = rsesq_reader._stations

# %% Get lat/lon of RSESQ stations

latitudes = []
longitudes = []
stn_ids = rsesq_reader.station_ids()
for stn_id in stn_ids:
    latitudes.append(float(rsesq_reader[stn_id]['Latitude']))
    longitudes.append(float(rsesq_reader[stn_id]['Longitude']))

# %% Get NARR Grid

filename = osp.join(path_to_narr, "pres.sfc.2017.nc")
dset = netCDF4.Dataset(filename, 'r+')
lat_grid = np.array(dset['lat'])
lon_grid = np.array(dset['lon'])
dset.close()

# %% Associate NARR grid with RSESQ stations location

latlon_idx = []
latlon_jdx = []
for lat_sta, lon_sta in zip(latitudes, longitudes):
    # Get the baro data from the nearest node in the grid for each station
    # of the RSESQ.
    dist = calc_dist_from_coord(lat_grid, lon_grid, lat_sta, lon_sta)
    idx = np.argmin(np.min(dist, axis=1))
    jdx = np.argmin(dist[idx, :])

    latlon_idx.append(idx)
    latlon_jdx.append(jdx)

# Remove duplicated nodes if any.
ijdx = np.vstack({(i, j) for i, j in zip(latlon_idx, latlon_jdx)})
latlon_idx = ijdx[:, 0].tolist()
latlon_jdx = ijdx[:, 1].tolist()

# %% Get baro data from NARR grid

lat_grid = None
lon_grid = None

patm_stacks = []
datetimes = []
for year in range(1979, 2018 + 1):
    print('\rFetching data for year %d...' % year, end=' ')
    filename = osp.join(path_to_narr, "pres.sfc.%d.nc" % year)
    netcdf_dset = netCDF4.Dataset(filename, 'r+')
    if lat_grid is None:
        lat_grid = np.array(netcdf_dset['lat'])
        lon_grid = np.array(netcdf_dset['lon'])
    t = np.array(dset['time'])

    # Note that we substract 5 hours to align time with GMT-5 local time.
    datetimes.extend(
        [datetime.datetime(year, 1, 1) +
         datetime.timedelta(hours=(i * 3)) -
         pd.Timedelta(hours=5) for
         i in range(len(t))]
        )

    patm_stacks.append(np.array(
        netcdf_dset['pres'])[:, latlon_idx, latlon_jdx] * 0.00010197)

    netcdf_dset.close()
print('done')
datestrings = [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in datetimes]
patm = np.vstack(patm_stacks)

lat_dd = list(lat_grid[latlon_idx, latlon_jdx])
lon_dd = list(lon_grid[latlon_idx, latlon_jdx])


# %% Save data to file.

fname = osp.join(osp.dirname(__file__), "patm_narr_data.csv")

Ndt, Ndset = np.shape(patm)
fheader = [
    ['Atmospheric pressure (m)'],
    ['Created from NARR grid'],
    ['', ''],
    ['Latitude (dd)'] + lat_dd,
    ['Longitude (dd)'] + lon_dd,
    ['', '']]
fdata = [[datestrings[i]] + list(patm[i]) for i in range(Ndt)]
fcontent = fheader + fdata
save_content_to_csv(fname, fcontent)
