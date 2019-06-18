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

# ---- Standard party imports
import datetime
import os.path as osp
# ---- Third party imports
import netCDF4
import numpy as np
import pandas as pd
# ---- Local imports
from correction_niveaux.utils import calc_dist_from_coord, save_content_to_csv
from data_readers import MDDELCC_RSESQ_Reader
from data_readers.read_mddelcc_rses import get_wldata_from_xls

# %%

rsesq_reader = MDDELCC_RSESQ_Reader(workdir="D:/Data")
rsesq_reader.load_database()

# We need to add data from Sainte-Martine manually because they were not
# published on the RSESQ website in 2018.
data = get_wldata_from_xls("D:/Data/Données_03097082.xls")
rsesq_reader._db["03097082"].update(data)

stations = rsesq_reader._stations

# %% Get lat/lon of RSESQ stations

stn_ids = rsesq_reader.station_ids()
lat_rsesq = [float(rsesq_reader[sid]['Latitude']) for sid in stn_ids]
lon_rsesq = [float(rsesq_reader[sid]['Longitude']) for sid in stn_ids]

# %% Get NARR Grid

path_to_narr = "D:/Data/baro_naar"
filename = osp.join(path_to_narr, "pres.sfc.2017.nc")
dset = netCDF4.Dataset(filename, 'r+')
lat_grid = np.array(dset['lat'])
lon_grid = np.array(dset['lon'])
dset.close()

# %% Get and save the barometric data to an csv file.

latlon_idx = []
latlon_jdx = []
for lat_sta, lon_sta in zip(lat_rsesq, lon_rsesq):
    # Get the baro data from the nearest node in the grid for each station
    # of the RSESQ.
    dist = calc_dist_from_coord(lat_grid, lon_grid, lat_sta, lon_sta)
    idx = np.argmin(np.min(dist, axis=1))
    jdx = np.argmin(dist[idx, :])

    latlon_idx.append(idx)
    latlon_jdx.append(jdx)

# # Remove duplicated nodes if any.
# ijdx = np.vstack(list({(i, j) for i, j in zip(latlon_idx, latlon_jdx)}))
# latlon_idx = ijdx[:, 0].tolist()
# latlon_jdx = ijdx[:, 1].tolist()

# %% Get baro data from NARR grid

patm_stacks = []
datetimes = []
for year in range(1979, 2018 + 1):
    print('\rFetching data for year %d...' % year, end=' ')
    filename = osp.join(path_to_narr, "pres.sfc.%d.nc" % year)
    netcdf_dset = netCDF4.Dataset(filename, 'r+')
    t = np.array(dset['time'])

    # Note that time is in UTC.
    datetimes.extend([datetime.datetime(year, 1, 1) +
                      datetime.timedelta(hours=(i * 3)) for
                      i in range(len(t))])

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
data_header = [['Date'] + list(stn_ids)]
fdata = [[datestrings[i]] + list(patm[i]) for i in range(Ndt)]
fcontent = fheader + data_header + fdata
save_content_to_csv(fname, fcontent)
