# -*- coding: utf-8 -*-
"""
Created on Wed May  1 11:10:08 2019
@author: User
"""
import os.path as osp
import sys
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
import datetime
import numpy as np
import xlrd

# Note: On 2021-09-21, ther was no binary wheel of Fiona available on Pypi
# for Windows. Fiona is a dependency of Geopandas.

# So in order to install Geopandas with pip on Windows, we need first to
# download and install, in the right order, the following packages
# from Christopher Gohlke’s website.

# (1) https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
# (2) https://www.lfd.uci.edu/~gohlke/pythonlibs/#fiona
# (3) https://www.lfd.uci.edu/~gohlke/pythonlibs/#shapely

workdir = "D:/Projets/pacc-inrs/portrait_rsesq"

# %%
shpfilename = osp.join(
    workdir, "zone_etude_Mercier", "ZoneMercier_NAD83_MTM_Zone8.shp")
zone_gdf = gpd.read_file(shpfilename)

# %%
rsesq_data = np.load(
    osp.join(workdir, 'mddelcc_rsesq_database.npy'),
    allow_pickle=True).item()

# We need to add the data from Sainte-Martine manually because they were
# not available at the time on the RSESQ website.
data = pd.read_csv(
    osp.join(workdir, 'Sainte-Martine (03097082).csv'),
    skiprows=10)

rsesq_data['03097082']['Time'] = data['Time'].values
rsesq_data['03097082']['Water Level'] = data['Water level (masl)'].values
rsesq_data['03097082']['Temperature'] = data['Water temperature (degC)'].values

# %%

geometry = []
stations = pd.DataFrame([])
for sid, station_info in rsesq_data.items():
    station_info = {
        'Station ID': station_info['ID'],
        'Station Name': station_info['Name'],
        'Lon_ddeg': float(station_info['Longitude']),
        'Lat_ddeg': float(station_info['Latitude']),
        'Nappe': station_info['Nappe'],
        'Influenced': station_info['Influenced'],
        }
    stations = stations.append(station_info, ignore_index=True)
    geometry.append(Point(
        (station_info['Lon_ddeg'], station_info['Lat_ddeg'])
        ))

crs = "+proj=longlat +ellps=GRS80 +datum=NAD83 +towgs84=0,0,0,0,0,0,0 +no_defs"
sta_gdf = gpd.GeoDataFrame(stations, crs=crs, geometry=geometry)
sta_gdf = sta_gdf.to_crs(zone_gdf.crs)

sta_gdf['Mercier'] = sta_gdf['geometry'].within(
    zone_gdf.loc[0]['geometry']).astype(int)

path_shp_out = osp.join(workdir, "puits_mddelcc_shp")
sta_gdf.to_file(path_shp_out)

# %%

sta_gdf_inzone = sta_gdf[sta_gdf['Mercier'] == 1]
sids = (list(sta_gdf_inzone['Station ID']) +
        ['03090007', '03090008', '03090020'])

fig, ax = plt.subplots()
fig.set_size_inches(8.5, len(sids) * 0.175)
before_2000 = []
before_2010 = []
start_date = []
for i, sid in enumerate(sids):
    xlsdates = rsesq_data[sid].get('Time', [])
    dtimes = [datetime.datetime(*xlrd.xldate_as_tuple(t, 0)) for t in xlsdates]
    l, = plt.plot(dtimes, [i] * len(dtimes), 's', ms=1, color='blue', mew=0)
    l.set_rasterized(True)
    if not len(dtimes):
        continue
    if np.min(dtimes) <= datetime.datetime(2000, 1, 1):
        before_2000.append(sid)
    if np.min(dtimes) <= datetime.datetime(2010, 1, 1):
        before_2010.append(sid)
    start_date.append(np.min(dtimes))

ax.set_yticks(range(i+1))
ax.axis(ymin=-1, ymax=i+1)
ax.set_yticklabels(sids)

ax.tick_params(axis='y', direction='out', labelsize=8)
ax.grid(axis='x', ls='-', color='0.65')

fig.tight_layout()
fig.savefig(osp.join(workdir, 'data_dist_ville_mercier.pdf'), dpi=300)
