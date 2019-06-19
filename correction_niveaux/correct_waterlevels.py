# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Jean-Sébastien Gosselin
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

import os.path as osp
import csv
import pandas as pd
import numpy as np
from pyhelp.utils import calc_dist_from_coord
import matplotlib.pyplot as plt
import pygtide
import pytz
import datetime
import sys
import matplotlib.pyplot as plt
import scipy.signal
from data_readers import MDDELCC_RSESQ_Reader


WORKDIR = osp.dirname(__file__)


# %% Load RSESQ database.

rsesq_reader = MDDELCC_RSESQ_Reader(workdir="D:/Data")
rsesq_reader.load_database()

# %% Load NARR data from csv file.

patm_narr_fname = osp.join(WORKDIR, "patm_narr_data.csv")

narr_baro = pd.read_csv(patm_narr_fname, header=5)
narr_baro['Date'] = pd.to_datetime(
    narr_baro['Date'], format="%Y-%m-%d %H:%M:%S")
narr_baro.set_index(['Date'], drop=True, inplace=True)

with open(patm_narr_fname, 'r+') as csvfile:
    reader = list(csv.reader(csvfile, delimiter=','))
    for row in reader:
        if len(row) == 0:
            continue
        if row[0].lower().startswith('lat'):
            latitudes = np.array(row[1:]).astype(float)
        elif row[0].lower().startswith('lon'):
            longitudes = np.array(row[1:]).astype(float)

# %% Format water level, barometric, and Earth tide data.

sid = '03040005'  # Saint-Amable
sid = '03030018'  # Saint-Hyacinte
sid = '03040009'  # Saint-Jean-sur-Richelieu
sid = '03030001'  # Sainte-Victoire
sta_data = rsesq_reader.get_station_data(sid)
sta_data = sta_data.resample('15min').asfreq()

# Add baro data to the WL time series.
sta_lat = float(rsesq_reader[sid]['Latitude'])
sta_lon = float(rsesq_reader[sid]['Longitude'])
sta_ele = float(rsesq_reader[sid]['Elevation'])

dist = calc_dist_from_coord(latitudes, longitudes, sta_lat, sta_lon)
idx = np.argmin(dist)
idx_narr_baro = narr_baro[[str(idx)]]
idx_narr_baro.rename(columns={str(idx): 'BP(m)'}, inplace=True)
idx_narr_baro = idx_narr_baro.resample('15min').asfreq()
idx_narr_baro = idx_narr_baro.interpolate(method='linear')
sta_data = pd.merge(
    sta_data, idx_narr_baro, left_index=True, right_index=True, how='left')

# Add Earth tide data to the WL time series.
etdata = generate_earth_tides(
    sta_lat, sta_lon, sta_ele, sta_data.index[0].year, sta_data.index[-1].year)
etdata = etdata[~etdata.index.duplicated()]

sta_data = pd.merge(
    sta_data, etdata, left_index=True, right_index=True, how='left')
sta_data.rename(columns={'Water Level (masl)': 'WL(masl)',
                         'Signal [nm/s**2]': 'ET(nm/s**2)',
                         'Temperature (degC)': 'WT(degC)'},
                inplace=True)

sta_data['ET(nm/s**2)'] = sta_data['ET(nm/s**2)'].interpolate(method='linear')

# %% Correct the WL data with the BRF

# Get the BRF function.
brf_fname = {'03040005': "brf_Saint-Amable_03040005.csv",
             '03030018': "brf_Saint-Hyacinte_03030018.csv",
             '03040009': "brf_Saint-Jean-sur-Richelieu_03040009.csv",
             '03030001': "brf_Sainte-Victoire_03030001.csv"}[sid]
brf_data = pd.read_csv(
    osp.join(WORKDIR, brf_fname), skip_blank_lines=False, header=14)

dWL = np.empty(len(sta_data)) * np.nan
nlag = len(brf_data) - 1
ndat = len(sta_data)

BP = scipy.signal.detrend(sta_data['BP(m)'])
M = np.empty((ndat-nlag, nlag+1))
M[:, 0] = BP[nlag:]
A = brf_data['A'].copy()
A[A.isnull()] = 0
for i in range(1, nlag+1):
    M[:, i] = BP[nlag-i:-i]
dWL_BP = np.dot(M, A)

ET = scipy.signal.detrend(sta_data['ET(nm/s**2)'])
M = np.empty((ndat-nlag, nlag+1))
M[:, 0] = ET[nlag:]
B = brf_data['B'].copy()
B[B.isnull()] = 0
for i in range(1, nlag+1):
    M[:, i] = ET[nlag-i:-i]
dWL_ET = np.dot(M, B) / 3.281

dWL[nlag:] = dWL_BP + dWL_ET


# %%

WL = sta_data['WL(masl)'].copy()
WL = WL[~WL.index.duplicated()]
WL = WL.resample('D').asfreq()
# WL.dropna(inplace=True)

WLcorr = sta_data['WL(masl)'].copy() + dWL
WLcorr = WLcorr[~WLcorr.index.duplicated()]
WLcorr = WLcorr.resample('D').asfreq()
# WLcorr.dropna(inplace=True)

fig, ax = plt.subplots()
l1, = ax.plot(WL, '-', color='0.75', lw=2)
l2, = ax.plot(WLcorr, '-', lw=2)

ax.set_ylabel('WL (masl)')
ax.set_title('Station Sainte-Victoire (03030001)')
ax.legend([l1, l2], ["Niveau d'eau non corrigés", "Niveaux d'eau corrigés"],
          bbox_to_anchor=[1, 1], loc='upper right', ncol=3,
          numpoints=1, fontsize=10, frameon=False)

# BP = scipy.signal.detrend(sta_data['BP(m)']) * 3.281
# dWL = BP * 0.8 / 3.281
# WLcorr = sta_data['WL(masl)'].copy() + dWL
# WLcorr = WLcorr[~WLcorr.index.duplicated()]
# WLcorr = WLcorr.resample('D').asfreq()

# ax.plot(WLcorr, '--', lw=2,)

# %%
filename = osp.join(
    WORKDIR,
    '%s_%s.csv' % (rsesq_reader[sid]['ID'], rsesq_reader[sid]['Name'])
    )
sta_data.to_csv(filename)

with open(filename, 'r', encoding='utf8') as csvfile:
    reader = list(csv.reader(csvfile, delimiter=','))[1:]

fcontent = [
    ["Well Name", rsesq_reader[sid]['Name']],
    ["Well ID", rsesq_reader[sid]['ID']],
    ["Latitude", rsesq_reader[sid]['Latitude']],
    ["Longitude", rsesq_reader[sid]['Longitude']],
    ["Altitude", rsesq_reader[sid]['Elevation']],
    ["Province", 'Qc'],
    [],
    ['Date', 'WL(mbgs)', 'WT(degC)', 'BP(m)', 'ET(nm/s**2)']
    ]
fcontent.extend(reader)

with open(filename, 'w', encoding='utf8') as csvfile:
    writer = csv.writer(csvfile, delimiter=',', lineterminator='\n')
    writer.writerows(fcontent)

sta_data.to_excel(osp.join(WORKDIR, 'new_data.xlsx'))
