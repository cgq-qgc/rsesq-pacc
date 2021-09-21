# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 20:24:09 2017
@author: jsgosselin
"""

# ---- Standard library imports
import os
import os.path as osp
from calendar import monthrange
import datetime as dt

# ---- Third party imports
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.transforms as transforms
import numpy as np
import pandas as pd

# ---- Local imports
from data_readers import MDDELCC_RSESQ_Reader


RGB = ["#ccebc5", "#a8ddb5", "#7bccc4", "#4eb3d3", "#2b8cbe"]
MONTHS = np.array(['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                   'Jui', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'])


def compute_monthly_statistics(tseries, q, pool='all'):
    percentiles = []
    nyear = []
    mly_values = []

    if pool == 'all':
        for m in range(1, 13):
            mly_stats = tseries.loc[tseries.index.month == m]
            mly_values.append(mly_stats.values)
            nyear.append(len(np.unique(mly_stats.index.year)))
    else:
        group = tseries.groupby([tseries.index.year, tseries.index.month])
        if pool == 'min_max_median':
            mly_stats = pd.concat(
                [group.min(), group.median(), group.max()], axis=1)
        elif pool == 'median':
            mly_stats = group.median()
        elif pool == 'mean':
            mly_stats = group.mean()
        for m in range(1, 13):
            mly_stats_m = mly_stats[mly_stats.index.get_level_values(1) == m]
            mly_values.append(mly_stats_m.values.flatten())
            nyear.append(len(mly_stats_m))

    percentiles = [np.percentile(v, q) for v in mly_values]
    return np.array(percentiles), np.array(nyear)


def plot_10yrs_annual_statistical_hydrograph(stn_info, stn_data, cur_year,
                                             last_month=12, filename=None,
                                             pool='all'):
    stn_name = stn_info['Name']
    stn_id = stn_info['ID']

    # Organize month order and define first and last datetime value for
    # the current data.
    if last_month == 12:
        year_lbl = "Année %d" % cur_year
        mth_idx = np.arange(12)
        dtstart = dt.datetime(cur_year, 1, 1)
        dtend = dt.datetime(cur_year, 12, 31)
    else:
        year_lbl = "Années %d-%d" % (cur_year-1, cur_year)
        mth_idx = np.arange(last_month, 12)
        mth_idx = np.hstack((mth_idx, np.arange(12 - len(mth_idx))))
        dtstart = dt.datetime(cur_year - 1, mth_idx[0] + 1, 1)
        dtend = dt.datetime(
            cur_year,
            mth_idx[-1] + 1,
            monthrange(cur_year, mth_idx[-1] + 1)[-1])

    # Generate the percentiles.
    wlevels = stn_data['Water Level (masl)']
    q = [100, 90, 75, 50, 25, 10, 0]
    percentiles, nyear = compute_monthly_statistics(wlevels, q, pool)

    # Produce the figure.
    fw, fh = 8, 6
    fig = plt.figure(figsize=(fw, fh))
    lm, rm, bm, tm = 0.85/fw, 0.1/fw, 0.8/fh, 0.5/fh

    # Produce the axe.
    ax = fig.add_axes([lm, bm, 1-lm-rm, 1-bm-tm], zorder=1)
    ax.set_facecolor('1')
    ax.grid(axis='y', color='0.65', linestyle='-', linewidth=0.5,
            dashes=[10, 3])
    ax.set_axisbelow(True)
    ax.tick_params(axis='x', which='both', length=3)
    ax.tick_params(axis='y', which='both', length=0)

    # Plot the percentiles.
    xpos = np.arange(12)
    idx = [0, 1, 2, 4, 5, 6]
    for i in range(len(idx)-1):
        ax.bar(xpos,
               percentiles[mth_idx, idx[i]]-percentiles[mth_idx, idx[i+1]],
               width=0.9, bottom=percentiles[mth_idx, idx[i+1]], color=RGB[i],
               edgecolor='black', linewidth=0.5)
    ax.plot(xpos, percentiles[mth_idx, 3], '^k')

    # Plot the current water level data series.
    cur_wlevels = wlevels[(wlevels.index >= dtstart) &
                          (wlevels.index <= dtend)]
    cur_rel_time = cur_wlevels.index.dayofyear.values / 365 * 12 - 0.5
    ax.plot(cur_rel_time, cur_wlevels.values, '-', color='red')

    # Axe limits.
    ymax = max(np.max(percentiles), np.max(cur_wlevels))
    ymin = min(np.min(percentiles), np.min(cur_wlevels))
    yrange = ymax - ymin
    yoffset = 0.1 / fh * yrange
    ax.axis([-0.75, 11.75, ymin - yoffset, ymax + yoffset])

    # Set axis labels.
    ax.set_ylabel("Niveau d'eau en m sous la surface", fontsize=16,
                  labelpad=10)
    pad = mpl.transforms.ScaledTranslation(0, 5/72, fig.dpi_scale_trans)
    ax.text(0.5, 0, year_lbl, ha='center', va='bottom', fontsize=16,
            transform=fig.transFigure + pad)

    # Set ticks and ticklabels.
    ax.set_xticks(np.arange(-0.5, 11.51))
    ax.set_xticklabels([])

    xlabelspos = np.arange(12)
    y = ymin - yoffset
    for m, n, x in zip(MONTHS[mth_idx], nyear[mth_idx], xlabelspos):
        offset = transforms.ScaledTranslation(0, -3/72, fig.dpi_scale_trans)
        ax.text(x, y, m, ha='center', va='top', fontsize=12,
                transform=ax.transData+offset)
        offset = transforms.ScaledTranslation(0, -18/72, fig.dpi_scale_trans)
        ax.text(x, y, '(%d)' % n, ha='center', va='top', fontsize=9,
                transform=ax.transData+offset)

    # Create a custom Legend.
    ax_pos = ax.get_position()
    ax_pos.y0 = 0
    ax_pos.y1 = 1
    ax2 = fig.add_axes(ax_pos, facecolor=None)
    ax2.axis('off')

    labels = ['<10', '10-24', '25-75', '76-90', '>90', 'Médiane', 'Mesures']
    x = [0, 0.075, 0.15, 0.225, 0.3, 0.4, 0.5]

    # Add the patches and labels to the legend.
    rw = 0.3 / fw * 1
    rh = 0.15 / fh * 1
    mpad = mpl.transforms.ScaledTranslation(0, -5/72, fig.dpi_scale_trans)
    lpad = mpl.transforms.ScaledTranslation(0, -22/72, fig.dpi_scale_trans)
    for i in range(5):
        patch = mpl.patches.Rectangle(
            (x[i], 1-rh), rw, rh, fc=RGB[i], ec='black', linewidth=0.5,
            transform=ax2.transAxes+mpad)
        ax2.add_patch(patch)
        ax2.text(x[i]+rw/2, 1, labels[i], ha='center', va='top', fontsize=10,
                 transform=ax2.transAxes+lpad)

    mpad = mpl.transforms.ScaledTranslation(0, -10/72, fig.dpi_scale_trans)
    ax2.plot([x[i+1]], [1], marker='^', color='black', ms=10, ls='',
             transform=ax2.transAxes+mpad)
    ax2.text(x[i+1], 1, labels[i+1], ha='center', va='top', fontsize=10,
             transform=ax2.transAxes+lpad)

    ax2.plot([x[i+2]], [1], marker='_', color='red', ms=10, ls='',
             mew=2,
             transform=ax2.transAxes+mpad)
    ax2.text(x[i+2], 1, labels[i+2], ha='center', va='top', fontsize=10,
             transform=ax2.transAxes+lpad)

    # Add title: Station name and ID.
    mpad = mpl.transforms.ScaledTranslation(0, -5/72, fig.dpi_scale_trans)
    title = "{}\nStation {}".format(stn_name, stn_id)
    ax2.text(1, 1, title, ha='right', va='top', fontsize=12,
             transform=ax2.transAxes+mpad)

    # Plot and save the figures.
    if filename:
        fig.savefig(filename)
    return fig


def plot_and_save_all(year, dirname, pool='all'):
    reader = MDDELCC_RSESQ_Reader()
    stations = reader.stations()
    for stn_id, stn_info in stations.iterrows():
        stn_data = reader.get_station_data(stn_id)

        avail_years = stn_data.index.year.unique()
        if len(avail_years) < 10:
            continue

        year_to_plot = avail_years[-1] if year == 'last' else year
        if year_to_plot not in avail_years:
            continue

        if not osp.exists(dirname):
            os.makedirs(dirname)
        filename = osp.join(
            dirname,
            '{} - hydrogramme_statistique ({}).png'
            .format(stn_id, year_to_plot)
            )

        last_month = 12
        plot_10yrs_annual_statistical_hydrograph(
            stn_info, stn_data, year_to_plot, last_month, filename, pool)
        plt.close('all')


def plot_all_year_from_sid(sid):
    reader = MDDELCC_RSESQ_Reader()
    stn_data = reader._db[sid]

    dirname = os.path.join('Hydrogrammes statistiques annnuels',
                           '%s (%s)' % (stn_data['Name'], stn_data['ID']))
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    years = np.unique(stn_data['Year'])
    for yr in years:
        filename = ('%s - hydrogramme_statistique_annnuel_%d.png' %
                    (stn_data['ID'], yr))
        plot_10yrs_annual_statistical_hydrograph(
            sid, yr, filename=os.path.join(dirname, filename))


if __name__ == "__main__":
    stn_data = plot_and_save_all(
        year=2020,
        dirname=osp.join(osp.dirname(__file__), 'figures_hydrogrammes'),
        pool='min_max_median')
