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

# plot_cross_correllation(
#     baro_naar.values, baro_sta['BP(m)'].values,
#     station=station, dist=dist[rowmin, colmin])


# %% Read barometric data from the NARR grid

# This file is produced with the script 'format_narr_data.py'.
narr_datafile = osp.join(osp.dirname(__file__), 'patm_narr_data.csv')
pres_grid = pd.read_csv(narr_datafile, header=[0, 1, 2], index_col=0)
pres_grid.index = pd.to_datetime(pres_grid.index)

lat_grid = pres_grid.columns.get_level_values(0)
#         [dt0 + timedelta(hours=(i * 3)) for i in range(len(t))])

# pres_grid = np.vstack(pres_stack)
# lat_grid = np.array(dset['lat'])
# lon_grid = np.array(dset['lon'])

# %% Read measured baro

fig, axes = plt.subplots(2, 5)
axes = axes.flatten()
fig.set_size_inches(w=11, h=6)
for i, ax in enumerate(axes):
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

baroname = ("D:/OneDrive/INRS/2017 - Projet INRS PACC/Correction Baro RSESQ/"
            "rsesq_barodata.hdf5")
hdf5baro = h5py.File(baroname, 'r')
stations = list(hdf5baro.keys())

crosscorr_figs = []
# stations = ['03020001']
for i, station in enumerate(stations):

    # Get data from the RSESQ measurements
    data_sta = hdf5baro[station]
    baro_sta = pd.Series(
        data_sta['baro_m'][:],
        pd.to_datetime(data_sta['date'], format="%Y-%m-%d %H:%M:%S"))

    # Get the baro data from the nearest node in the NARR grid.
    lat_sta = data_sta.attrs['latitude']
    lon_sta = data_sta.attrs['longitude']
    dist = calc_dist_from_coord(lat_grid, lon_grid, lat_sta, lon_sta)
    rowmin = np.argmin(np.min(dist, axis=1))
    colmin = np.argmin(dist[rowmin, :])

    baro_naar = pd.Series(
        np.copy(pres_grid[:, rowmin, colmin]), dtime_grid)
    baro_naar = baro_naar * 0.00010197  # Pa -> m
    baro_naar.index = baro_naar.index - pd.Timedelta(hours=5)

    # Keep only the values that are synchronized.
    baro_naar.dropna(inplace=True)
    baro_sta = baro_sta[baro_naar.index]
    baro_sta.dropna(inplace=True)
    baro_naar = baro_naar[baro_sta.index]

    # Normalize the data.
    baro_sta = baro_sta - np.nanmean(baro_sta)
    baro_naar = baro_naar - np.nanmean(baro_naar)

    # Plot the data.
    l1, = axes[i].plot(baro_naar * 100, baro_sta * 100, '.',
                       ms=3, alpha=0.5, mfc='k', mec='k', clip_on=True, mew=0)
    l1.set_rasterized(True)
    axes[i].plot((-30, 30), (-30, 30), '--', lw=1, color='red')
    axes[i].set_title('#' + str(station), fontsize=14)
    axes[i].axis(ymin=-30, ymax=30, xmin=-30, xmax=30)

    # PLot the coefficient of regression.
    r = np.corrcoef(baro_naar.values, baro_sta.values)[1, 0]
    axes[i].text(
        0, 1, 'r = %0.3f' % (r), ha='left', va='top', fontsize=11,
        transform=(axes[i].transAxes +
                   ScaledTranslation(5/72, -20/72, fig.dpi_scale_trans)))

    # Plot the RMSE.
    rmse = np.nanmean((baro_naar.values - baro_sta.values)**2)**0.5
    rmse = rmse * 100  # m -> cm
    axes[i].text(
        0, 1, 'RMSE = %0.1f cm' % (rmse), ha='left', va='top', fontsize=11,
        transform=(axes[i].transAxes +
                   ScaledTranslation(5/72, -5/72, fig.dpi_scale_trans)))

    # crosscorr_figs.append(plot_cross_correllation(
    #     baro_naar.values, baro_sta['BP(m)'].values,
    #     station=station, dist=dist[rowmin, colmin])
    # )

suptitle = (
    "Comparaison des données barométriques normalisées du RSESQ \n"
    " avec la grille NARR pout la période du {} au {}"
    ).format(baro_sta.index[0].strftime("%Y-%m-%d"),
             baro_sta.index[-1].strftime("%Y-%m-%d"))

fig.suptitle(suptitle, fontsize=15)
fig.tight_layout()
fig.subplots_adjust(wspace=0.3, hspace=0.3, top=0.85)
# fig.savefig("baro_rsesq_vs_narr.pdf", dpi=600)

# pdfpages = PdfPages('cross_correllation_RSESQ_NARR.pdf')
# for crosscorr_fig in crosscorr_figs:
#     pdfpages.savefig(crosscorr_fig)
# pdfpages.close()

hdf5baro.close()
