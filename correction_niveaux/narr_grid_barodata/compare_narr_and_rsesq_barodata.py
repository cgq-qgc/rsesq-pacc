# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Institut National de la Recherche Scientifique (INRS)
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

"""
"""

# ---- Standard party imports
import os.path as osp
from datetime import datetime, timedelta

# ---- Third party imports
import netCDF4
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import h5py
from scipy import interpolate
import matplotlib
from matplotlib.transforms import ScaledTranslation
from matplotlib.backends.backend_pdf import PdfPages

# ---- Local imports
from data_readers import MDDELCC_RSESQ_Reader

matplotlib.rcParams['axes.unicode_minus'] = False
plt.close('all')


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


def plot_cross_correllation(x1, x2, station='', dist=0):
    crosscorr = np.correlate(x1, x2, mode='full')
    lags = np.arange(-len(x1) + 1, len(x1)) * 3

    # Interpolate the results to an hourly time frame.
    tck = interpolate.splrep(lags, crosscorr)
    lags_hours = np.arange(-48, 49, 0.1)
    crosscorr_hours = interpolate.splev(lags_hours, tck)

    # Normalize the results.
    crosscorr = crosscorr / np.max(crosscorr_hours)
    crosscorr_hours = crosscorr_hours / np.max(crosscorr_hours)

    # Plot the results.
    fig, ax = plt.subplots()
    fig.set_size_inches(w=8, h=4)
    ax.set_axisbelow(True)

    ax.set_xlabel('Lags (hours)', labelpad=5, fontsize=14)
    ax.set_ylabel('Normed correlation coefficient', labelpad=10, fontsize=14)

    ax.plot(lags_hours, crosscorr_hours, '-', zorder=10, lw=1)
    ax.plot(lags, crosscorr, '.', color='blue', zorder=15, ms=10, mec='white')
    xticks = np.arange(-48, 48 + 1, 3)
    ax.set_xticks(xticks)
    xticklabels = [''] * len(xticks)
    xticklabels[::4] = np.arange(-48, 48 + 1, 12).astype(str)
    ax.set_xticklabels(xticklabels)
    ax.set_xticks(np.arange(-48, 48 + 1, 1), minor=True)
    ax.grid(True, axis='y')
    ax.axis(xmin=-48, xmax=48, ymin=0)

    imax = np.argmax(crosscorr_hours)
    maxlag = lags_hours[imax]
    ax.axvline(maxlag, ls=':', lw=1, zorder=20, color='red')

    # Plot max lag.
    text = '%0.1f hours' % maxlag if maxlag >= 2 else '%0.1f hour' % maxlag
    ax.text(
        lags_hours[imax], 0, text, ha='left', va='bottom', fontsize=12,
        color='red',
        transform=(ax.transData +
                   ScaledTranslation(3/72, 2/72, fig.dpi_scale_trans)))
    ax.text(-48, 1, 'Station #' + station, ha='left', va='top', fontsize=12,
            transform=(ax.transData +
                       ScaledTranslation(5/72, -5/72, fig.dpi_scale_trans)))
    ax.text(-48, 1, 'Dist. to node = %0.1f km' % dist,
            ha='left', va='top', fontsize=12,
            transform=(ax.transData +
                       ScaledTranslation(5/72, -25/72, fig.dpi_scale_trans)))

    fig.tight_layout()

    return fig


# %% Read barometric data from the NARR grid

patm_narr_fname = osp.join(osp.dirname(__file__), "patm_narr_data_gtm0.csv")

# Get the barometric data.
narr_baro = pd.read_csv(patm_narr_fname, header=[0, 1, 2])

narr_baro = narr_baro.set_index(
    [('Latitude (dd)', 'Longitude (dd)', 'Station')], drop=True)
narr_baro.index = pd.to_datetime(narr_baro.index, format="%Y-%m-%d %H:%M:%S")
narr_baro.index = narr_baro.index.rename('datetime')

# !!! It is important to shift the data by 5 hours to match the
#     local time of the data from the RSESQ.
narr_baro.index = narr_baro.index - pd.Timedelta(hours=5)

# Extract latitude and longitude data from the columns multi-index and drop
# these from the columns.
narr_coord = pd.DataFrame([], index=narr_baro.columns.get_level_values(2))
narr_coord['lat_dd'] = narr_baro.columns.get_level_values(0).astype('float')
narr_coord['lon_dd'] = narr_baro.columns.get_level_values(1).astype('float')

narr_baro.columns = narr_baro.columns.droplevel(level=[0, 1])

# %% Read measured baro from RSESQ

dirname = osp.join(
    osp.dirname(osp.dirname(__file__)),
    'rsesq_data_15min_2017',
    'formatted_baro_and_level_data')
files = ['formatted_barodata_capitale-nationale_15min_LOCALTIME.csv',
         'formatted_barodata_centre-quebec_15min_LOCALTIME.csv',
         'formatted_barodata_chaudiere-appalaches_15min_LOCALTIME.csv',
         'formatted_barodata_monteregie_15min_LOCALTIME.csv',
         'formatted_barodata_montreal_15min_LOCALTIME.csv']

for i, file in enumerate(files):
    if i == 0:
        rsesq_baro = pd.read_csv(
            osp.join(dirname, files[0]), header=0, index_col='Date')
    else:
        rsesq_baro = rsesq_baro.append(pd.read_csv(
            osp.join(dirname, file), header=0, index_col='Date'))

# %%
plt.close('all')

rsesq_reader = MDDELCC_RSESQ_Reader()
rsesq_stations = rsesq_reader.stations()

fig, axes = plt.subplots(2, 5)
fig.set_size_inches(w=11, h=6)
axes = axes.flatten()

for i, ax in enumerate(axes.flatten()):
    ax.set_aspect('equal')
    ax.set_axisbelow(True)
    ax.set_xticks([-30, 0, 30])
    ax.set_yticks([-30, 0, 30])
    ax.tick_params(axis='both', direction='out', labelsize=12)
    ax.grid(True, axis='both')
    if i not in [0, 5]:
        ax.set_yticklabels([])
    else:
        ax.set_ylabel('Baro RSESQ (cm)', labelpad=5, fontsize=14)

    if i not in [5, 6, 7, 8, 9]:
        pass
        # ax.set_xticklabels([])
    else:
        ax.set_xlabel('Baro NARR (cm)', labelpad=10, fontsize=14)

crosscorr_figs = []
for i, station in enumerate(rsesq_baro.columns[:10]):
    if i == 10:
        break

    rsesq_baro_sta = rsesq_baro[station]
    rsesq_baro_sta.name = 'RSESQ'

    narr_baro_sta = narr_baro[station]
    narr_baro_sta.name = 'NARR'

    # Get the baro data from the nearest node in the NARR grid.
    dist = calc_dist_from_coord(
        narr_coord.loc[station]['lat_dd'],
        narr_coord.loc[station]['lon_dd'],
        rsesq_stations.loc[station]['Lat_ddeg'],
        rsesq_stations.loc[station]['Lon_ddeg'])

    # Keep only the values that are synchronized.
    baro_stack = rsesq_baro_sta.to_frame().join(
        narr_baro_sta, how='outer').dropna()

    # Normalize the data.
    baro_stack['RSESQ'] = baro_stack['RSESQ'] - baro_stack['RSESQ'].mean()
    baro_stack['NARR'] = baro_stack['NARR'] - baro_stack['NARR'].mean()

    # Plot the data.
    ax = axes[i]
    l1, = ax.plot(
        baro_stack['NARR'] * 100, baro_stack['RSESQ'] * 100,
        '.', ms=3, alpha=0.5, mfc='k', mec='k', clip_on=True, mew=0)
    l1.set_rasterized(True)
    ax.plot((-30, 30), (-30, 30), '--', lw=1, color='red')
    ax.set_title('#' + str(station), fontsize=14)
    ax.axis(ymin=-30, ymax=30, xmin=-30, xmax=30)

    # Plot the coefficient of regression.
    r = np.corrcoef(baro_stack['NARR'], baro_stack['RSESQ'])[1, 0]
    ax.text(
        0, 1, 'r = %0.3f' % (r), ha='left', va='top', fontsize=11,
        transform=(ax.transAxes +
                   ScaledTranslation(5/72, -20/72, fig.dpi_scale_trans)))

    # Plot the RMSE.
    rmse = np.nanmean((baro_stack['NARR'] - baro_stack['RSESQ'])**2)**0.5
    rmse = rmse * 100  # m -> cm
    ax.text(
        0, 1, 'RMSE = %0.1f cm' % (rmse), ha='left', va='top', fontsize=11,
        transform=(ax.transAxes +
                   ScaledTranslation(5/72, -5/72, fig.dpi_scale_trans)))

suptitle = (
    "Comparaison des données barométriques normalisées du RSESQ \n"
    " avec la grille NARR pout la période du {} au {}"
    ).format(baro_stack.index[0].strftime("%Y-%m-%d"),
             baro_stack.index[-1].strftime("%Y-%m-%d"))

fig.suptitle(suptitle, fontsize=15)
fig.tight_layout()
fig.subplots_adjust(wspace=0.3, hspace=0.3, top=0.85)
fig.savefig("baro_rsesq_vs_narr.pdf", dpi=600)
