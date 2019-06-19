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
    data['Level_m'] = data['Level_m'] - data['BP(m)']
    data['Level_m'] = np.max(data['Level_m']) - data['Level_m']

    # Convert time to string format.
    datetimes = data.index.strftime("%Y-%m-%dT%H:%M:%S").values.tolist()

    # Save data to files.
    fcontent = [[datetimes[i]] + data.iloc[i].tolist() for
                i in range(len(datetimes))]
    save_content_to_csv(filename, fheader + fcontent)

    return fheader + fcontent


def export_to_csv(levelfiles, barofiles, filename=None):
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

path_to_rawdatafiles = "D:/Data/rsesq_raw_15min_2017"

period = ['Printemps', 'Automne'][1]
region = ['Monteregie', 'Chaudière-Appalaches'][0]
dirname = osp.join(path_to_rawdatafiles, period, region)

rsesq_barofiles = {}
rsesq_levelfiles = {}
rsesq_latitudes = {}
rsesq_longitudes = {}
rsesq_elevations = {}

i = 0
for file in os.listdir(dirname):
    if not file.endswith('csv'):
        continue
    i += 1
    print(i, file)

    solinst_file = hsr.SolinstFileReader(osp.join(dirname, file))
    if "baro" in file.lower():
        stn_id = re.sub(
            '[ -_]?BARO[ -_]?', '', solinst_file.sites.project_name)
        rsesq_barofiles[stn_id] = solinst_file
    else:
        stn_id = solinst_file.sites.project_name
        rsesq_levelfiles[stn_id] = solinst_file

    # Get latitude, longitude, and elevation of the well where the
    # logger is installed.
    solinst_file.sites.latitude = float(rsesq_reader[stn_id]['Latitude'])
    solinst_file.sites.longitude = float(rsesq_reader[stn_id]['Longitude'])
    try:
        solinst_file.sites.elevation = float(rsesq_reader[stn_id]['Elevation'])
    except KeyError:
        # We need to download the data to get the station elevation because
        # this info is not in the kml file.
        rsesq_reader.fetch_station_wldata(stn_id)
    finally:
        solinst_file.sites.elevation = float(rsesq_reader[stn_id]['Elevation'])

    rsesq_latitudes[stn_id] = float(rsesq_reader[stn_id]['Latitude'])
    rsesq_longitudes[stn_id] = float(rsesq_reader[stn_id]['Longitude'])
    rsesq_elevations[stn_id] = float(rsesq_reader[stn_id]['Elevation'])

# Define some lists for the baro stations.
rsesq_baro_stations = list(rsesq_barofiles.keys())
rsesq_baro_latitudes = np.array(
    [rsesq_latitudes[stn] for stn in rsesq_baro_stations])
rsesq_baro_longitudes = np.array(
    [rsesq_longitudes[stn] for stn in rsesq_baro_stations])

# %% Load NARR data from csv file.

# The 'patm_narr_data.csv' file is generated from the NARR netCDF files with
# the script 'get_data_from_narr.py'

patm_narr_fname = osp.join(osp.dirname(__file__), "patm_narr_data.csv")

# Get the barometric data.
narr_baro = pd.read_csv(patm_narr_fname, header=6)
narr_baro['Date'] = pd.to_datetime(
    narr_baro['Date'], format="%Y-%m-%d %H:%M:%S")
narr_baro.set_index(['Date'], drop=True, inplace=True)

# Get the list of latitudes and longitudes for the barometric data series.
with open(patm_narr_fname, 'r+') as csvfile:
    reader = list(csv.reader(csvfile, delimiter=','))
    for row in reader:
        if len(row) == 0:
            continue
        if row[0].lower().startswith('lat'):
            narr_baro_latitudes = np.array(row[1:]).astype(float)
        elif row[0].lower().startswith('lon'):
            narr_baro_longitudes = np.array(row[1:]).astype(float)


# %% Read NARR Grid

filename = "D:/Data/baro_naar/pres.sfc.2017.nc"
dset = netCDF4.Dataset(filename, 'r+')

lat_grid = np.array(dset['lat'])
lon_grid = np.array(dset['lon'])
t = np.array(dset['time'])
pres = np.array(dset['pres']) * 0.00010197
x = np.array(dset['x'])
dt0 = datetime(2017, 1, 1)
dt_grid = [dt0 + timedelta(hours=(i * 3)) for i in range(len(t))]

# %% Read the synthetic Earth tides.

synth_earthtides = pd.read_csv(
    osp.join(osp.dirname(__file__), 'synthetic_earthtides_incomplete.csv'))
synth_earthtides['Date'] = pd.to_datetime(
    synth_earthtides['Date'], format="%Y-%m-%d %H:%M:%S")
synth_earthtides.set_index(['Date'], drop=True, inplace=True)

# %% Format the piezo, baro and earth tides data.

baro_source = ['NAAR', 'RSESQ'][1]

nlevel = len(rsesq_levelfiles)
level_baro_link_tbl = {}
print('{:<8s}'.format('Piezo_id'), '{:<8s}'.format('Baro_id'),
      '{:>5s}'.format('dist'), '{:>6s}'.format('delev'),
      '  Location')
print('{:<8s}'.format(''), '{:<8s}'.format(''),
      '{:>5s}'.format('(km)'), '{:>6s}'.format('(m)'))

for stn_id in sorted(list(rsesq_levelfiles.keys()))[:]:

    stn_lat = float(rsesq_reader[stn_id]['Latitude'])
    stn_lon = float(rsesq_reader[stn_id]['Longitude'])
    stn_elev = float(rsesq_reader[stn_id]['Elevation'])

    # Generate the synthetic earth tides data.
    etdata = synth_earthtides[[stn_id]]

    # Get the piezometric data from the NARR or RSESQ.
    colname = rsesq_levelfiles[stn_id].records.columns[0]
    leveldata = rsesq_levelfiles[stn_id].records[[colname]]

    # Associate a barometric pressure time series from NAAR or RSESQ to
    # the piezometric station stn_id.
    if baro_source == 'NAAR':
        baro_stn = 'NAAR grid'
        delta_elev = 0

        dist = calc_dist_from_coord(lat_grid, lon_grid, stn_lat, stn_lon)
        rowmin = np.argmin(np.min(dist, axis=1))
        colmin = np.argmin(dist[rowmin, :])

        barodata = pd.DataFrame(
            np.copy(pres[:, rowmin, colmin]), dt_grid, columns=['BP(m)'])
        barodata.index = barodata.index - pd.Timedelta(hours=5)
        barodata = barodata.interpolate(method='linear')

        # dist = calc_dist_from_coord(
        #     narr_baro_latitudes, narr_baro_longitudes, stn_lat, stn_lon)
        # idx = np.argmin(dist)
        # barodata = narr_baro[[str(idx)]]
        # barodata.rename(columns={str(idx): 'BP(m)'}, inplace=True)
        # barodata = barodata.resample('15min').asfreq()
        # barodata = barodata.interpolate(method='linear')
    elif baro_source == 'RSESQ':
        dist = calc_dist_from_coord(
            rsesq_baro_latitudes, rsesq_baro_longitudes, stn_lat, stn_lon)

        baro_stn = rsesq_baro_stations[np.argmin(dist)]
        colname = rsesq_barofiles[baro_stn].records.columns[0]
        barodata = rsesq_barofiles[baro_stn].records[[colname]]
        barodata.rename(columns={'Level_m': 'BP(m)'}, inplace=True)

        delta_elev = (rsesq_reader[stn_id]['Elevation'] -
                      rsesq_reader[baro_stn]['Elevation'])

    # Prepare the file header.
    sites = rsesq_levelfiles[stn_id].sites
    stn_id = sites.project_name
    fheader = [['Well Name', sites.site_name],
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
          '  {}'.format(sites.site_name)
          )

    etdata = etdata.resample('3H').asfreq()
    barodata = barodata.resample('3H').asfreq()
    leveldata = leveldata.resample('3H').asfreq()
    if True:
        foldername = osp.join(osp.dirname(__file__), '15min_formatted_data')
        if not osp.exists(foldername):
            os.makedirs(foldername)
        filename = '{}_{}_{}_{}_baro.csv'.format(
            region.lower(), period.lower(), stn_id, baro_source.lower())
        fcontent = save_to_gwhat_file(osp.join(foldername, filename),
                                      leveldata, barodata, etdata, fheader)

    break
