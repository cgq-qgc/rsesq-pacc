# -*- coding: utf-8 -*-
"""
Created on Wed May  1 11:10:08 2019
@author: User
"""
import os.path as osp
import sys
import geopandas as gpd
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
import datetime
import numpy as np

sys.path.append("C:/Users/User/inrs-rsesq/rsesq-data")
from data_readers import MDDELCC_RSESQ_Reader
from data_readers.read_mddelcc_rses import get_wldata_from_xls

# %%
workdir = "D:/Data"
shpfilename = osp.join(
    workdir, "zone_etude_Mercier", "ZoneMercier_NAD83_MTM_Zone8.shp")
zone_gdf = gpd.read_file(shpfilename)

# %%
reader = MDDELCC_RSESQ_Reader(workdir)
stations = reader.stations()

# %%

# Add manually the data for Well because they are not publicly available.
data = get_wldata_from_xls(osp.join(workdir, "Données_03097082.xls"))
reader._db["03097082"].update(data)

# %%

geometry = []
for sid in stations.index:
    geometry.append(Point(
        (stations.loc[sid]['Lon_ddeg'], stations.loc[sid]['Lat_ddeg'])
        ))

crs = "+proj=longlat +ellps=GRS80 +datum=NAD83 +towgs84=0,0,0,0,0,0,0 +no_defs"
sta_gdf = gpd.GeoDataFrame(stations, crs=crs, geometry=geometry)
sta_gdf = sta_gdf.to_crs(zone_gdf.crs)

sta_gdf['Mercier'] = sta_gdf['geometry'].within(
    zone_gdf.loc[0]['geometry']).astype(int)

path_shp_out = ("C:/Users/User/OneDrive/INRS/2017 - Projet INRS PACC/"
                "puits_mddelcc_shp")
sta_gdf.to_file(path_shp_out)

# %%

sta_gdf_inzone = sta_gdf[sta_gdf['Mercier'] == 1]
sids = list(sta_gdf_inzone.index) + ['03090007', '03090008', '03090020']

fig, ax = plt.subplots()
fig.set_size_inches(8.5, len(sids) * 0.175)
before_2000 = []
before_2010 = []
start_date = []
for i, sid in enumerate(sids):
    data = reader.get_station_data(sid)
    l, = plt.plot(data.index, [i] * len(data), 's', ms=1, color='blue', mew=0)
    l.set_rasterized(True)
    if not len(data.index):
        continue
    if np.min(data.index) <= datetime.datetime(2000, 1, 1):
        before_2000.append(sid)
    if np.min(data.index) <= datetime.datetime(2010, 1, 1):
        before_2010.append(sid)
    start_date.append(np.min(data.index))

ax.set_yticks(range(i+1))
ax.axis(ymin=-1, ymax=i+1)
ax.set_yticklabels(sids)

ax.tick_params(axis='y', direction='out', labelsize=8)
ax.grid(axis='x', ls='-', color='0.65')

fig.tight_layout()
fig.savefig('data_dist_ville_mercier.pdf', dpi=300)
