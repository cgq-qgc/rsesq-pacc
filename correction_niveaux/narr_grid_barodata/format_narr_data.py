# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Institut National de la Recherche Scientifique (INRS)
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

"""
This script matches the piezometric stations of the RSESQ with the barometric
data of the NARR data grid, extract the atmospheric pressure from the
NARR grid files and save the extracted data in a csv file.
"""

# ---- Standard library imports
import csv
import datetime
import os.path as osp

# ---- Third party imports
import netCDF4
import numpy as np

# ---- Local imports
from data_readers import MDDELCC_RSESQ_Reader


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


# %% Get RSESQ station locations

rsesq_reader = MDDELCC_RSESQ_Reader()
stations = rsesq_reader.stations()
stn_ids = stations['ID'].values
lat_rsesq = stations['Lat_ddeg'].values
lon_rsesq = stations['Lon_ddeg'].values

# %% Get NARR grid nodes

path_to_narr = osp.join(osp.dirname(__file__), 'baro_naar_netcdf')
filename = osp.join(path_to_narr, "pres.sfc.2017.nc")
dset = netCDF4.Dataset(filename, 'r+')
lat_grid = np.array(dset['lat'])
lon_grid = np.array(dset['lon'])
dset.close()

# %% Match RSESQ stations with NARR grid

# Get the daily barometric data from the NARR grid for the nodes that are
# nearest to the stations of the RSESQ.

latlon_idx = []
latlon_jdx = []
for lat_sta, lon_sta in zip(lat_rsesq, lon_rsesq):
    dist = calc_dist_from_coord(lat_grid, lon_grid, lat_sta, lon_sta)
    idx = np.argmin(np.min(dist, axis=1))
    jdx = np.argmin(dist[idx, :])

    latlon_idx.append(idx)
    latlon_jdx.append(jdx)


# %% Extract baro data from NARR grid

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


# %% Save extracted data to a file

fname = osp.join(osp.dirname(__file__), "patm_narr_data_gtm0.csv")

Ndt, Ndset = np.shape(patm)
fheader = [
    ['Latitude (dd)'] + lat_dd,
    ['Longitude (dd)'] + lon_dd,
    ['Station'] + list(stn_ids)
    ]
fdata = [[datestrings[i]] + list(patm[i]) for i in range(Ndt)]
fcontent = fheader + fdata
with open(fname, 'w', encoding='utf8') as csvfile:
    writer = csv.writer(csvfile, delimiter=',', lineterminator='\n')
    writer.writerows(fcontent)
