# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 20:24:09 2017
@author: jsgosselin
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.transforms as transforms
from readers import MDDELCC_RSESQ_Reader
import colorsys
from xlrd.xldate import xldate_from_date_tuple
from calendar import monthrange

# lightnes = 150
# hls = [[23/255, lightnes/255, 153/255],
#         [24/255, lightnes/255, 240/255],
#         [72/255, lightnes/255, 121/255],
#         [134/255, lightnes/255, 160/255],
#         [160/255, lightnes/255, 123/255]]
# RGB = [colorsys.hls_to_rgb(col[0], col[1], col[2]) for col in hls]

RGB = ["#ccebc5", "#a8ddb5", "#7bccc4", "#4eb3d3", "#2b8cbe"]
MONTHS = np.array(['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                   'Jui', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'])


def compute_monthly_statistics(years, months, values, q, pool='all'):
    percentiles = []
    nyear = []
    for m in range(1, 13):
        if pool == 'all':
            ixs = np.where(months == m)[0]
            mly_values = values[ixs]
            nyear.append(len(np.unique(years[ixs])))
        else:
            mly_values = []
            for yr in np.unique(years):
                ixs = np.where((months == m) & (years == yr))[0]
                if pool == 'median' and len(ixs) > 0:
                    mly_values.append(np.median(values[ixs]))
                elif pool == 'mean' and len(ixs) > 0:
                    mly_values.append(np.mean(values[ixs]))
            nyear.append(len(mly_values))
        percentiles.append(np.percentile(mly_values, q))

    return np.array(percentiles), np.array(nyear)


def plot_10yrs_annual_statistical_hydrograph(sid, cur_year, last_month=12,
                                             filename=None, pool='all'):
    reader = MDDELCC_RSESQ_Reader()
    stn_data = reader._db[sid]

    # Organize month order.
    year = stn_data['Year']
    month = stn_data['Month']
    time = stn_data['Time']

    if last_month == 12:
        year_lbl = "Année %d" % cur_year
        mth_idx = np.arange(12)
        tstart = xldate_from_date_tuple((cur_year, 1, 1), 0)
        tend = xldate_from_date_tuple((cur_year, 12, 31), 0)
    else:
        year_lbl = "Années %d-%d" % (cur_year-1, cur_year)
        mth_idx = np.arange(last_month, 12)
        mth_idx = np.hstack((mth_idx, np.arange(12-len(mth_idx))))

        tstart = xldate_from_date_tuple((cur_year-1, mth_idx[0]+1, 1), 0)
        nday_in_mth = monthrange(cur_year, mth_idx[-1]+1)[-1]
        tend = xldate_from_date_tuple(
                (cur_year, mth_idx[-1]+1, nday_in_mth), 0)
    try:
        istart = np.where(time >= tstart)[0][0]
        iend = np.where(time <= tend)[0][-1]
    except IndexError:
        istart = iend = 0

    # Generate the percentiles.
    level = stn_data['Elevation'] - stn_data['Water Level']
    q = [100, 90, 75, 50, 25, 10, 0]
    percentiles, nyear = compute_monthly_statistics(year, month, level,
                                                    q, pool)

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

    # Plot daily series.
    year = stn_data['Year']
    time = stn_data['Time'][istart:iend+1]
    level = stn_data['Elevation'] - stn_data['Water Level'][istart:iend+1]
    ax.plot((time-tstart)/365*12-0.5, level, '-', color='red')

    # Axe limits.
    ymax = max(np.max(percentiles), np.max(level))
    ymin = min(np.min(percentiles), np.min(level))
    yrange = ymax - ymin
    yoffset = 0.1/fh*yrange
    ax.axis([-0.75, 11.75, ymin-yoffset, ymax+yoffset])
    ax.invert_yaxis()

    # Set axis labels.
    ax.set_ylabel("Niveau d'eau en m sous la surface", fontsize=16,
                  labelpad=10)
    pad = mpl.transforms.ScaledTranslation(0, 5/72, fig.dpi_scale_trans)
    ax.text(0.5, 0, year_lbl, ha='center', va='bottom', fontsize=16,
            transform=fig.transFigure+pad)

    # Set ticks and ticklabels.
    ax.set_xticks(np.arange(-0.5, 11.51))
    ax.set_xticklabels([])

    xlabelspos = np.arange(12)
    y = ymax+yoffset
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

    # Add the pathes and labels to the legend.
    rw = 0.3/fw*1
    rh = 0.15/fh*1
    mpad = mpl.transforms.ScaledTranslation(0, -5/72, fig.dpi_scale_trans)
    lpad = mpl.transforms.ScaledTranslation(0, -22/72, fig.dpi_scale_trans)
    for i in range(5):
        ax2.add_patch(
                mpl.patches.Rectangle((x[i], 1-rh), rw, rh, fc=RGB[i],
                                      ec='black', linewidth=0.5,
                                      transform=ax2.transAxes+mpad))
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

    # Add title: Station name and ID
    mpad = mpl.transforms.ScaledTranslation(0, -5/72, fig.dpi_scale_trans)
    title = "%s\nStation %s" % (stn_data['Name'], stn_data['ID'])
    ax2.text(1, 1, title, ha='right', va='top', fontsize=12,
             transform=ax2.transAxes+mpad)

    # Plot and save the figure.
    if filename:
        fig.savefig(filename)
    return fig


def produce_tex_table(sid, cur_year, last_month=12, filename=None):
    pass


# ---- Helper functions


def plot_and_save_all(year, dirname, pool='all'):
    reader = MDDELCC_RSESQ_Reader()
    for stn in reader.stations():
        if 'Year' not in list(stn.keys()):
            continue

        years = np.unique(stn['Year'])
        if len(years) < 10:
            continue

        yr_to_plot = years[-1] if year == 'last' else year
        if yr_to_plot not in years:
            continue

        filename = ('%s - hydrogramme_statistique_annnuel_%d.png' %
                    (stn['ID'], yr_to_plot))
        if dirname:
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            filename = os.path.join(dirname, filename)

        last_month = stn['Month'][stn['Year'] == yr_to_plot][-1]
        plot_10yrs_annual_statistical_hydrograph(
                stn['ID'], yr_to_plot, last_month, filename, pool)
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
    plt.close('all')
    filename = '03090006 - hydrogramme_statistique_annnuel_2016.pdf'
    plot_10yrs_annual_statistical_hydrograph('03090006', 2016, filename)