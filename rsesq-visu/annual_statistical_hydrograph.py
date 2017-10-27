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

rbg = [[152/255, 100/255, 38/255],
       [248/255, 151/255, 29/255],
       [105/255, 189/255, 69/255],
       [110/255, 205/255, 222/255],
       [57/255, 82/255, 164/255]]


def compute_monthly_statistics_table(years, months, values, q):
    percentiles = []
    nyear = []
    for m in range(1, 13):
        ixs = np.where(months == m)[0]
        percentiles.append(np.percentile(values[ixs], q))
        nyear.append(len(np.unique(years[ixs])))
    return np.array(percentiles), np.array(nyear)


def plot_10yrs_annual_statistical_hydrograph(sid, cur_year):
    reader = MDDELCC_RSESQ_Reader()
    stn_data = reader._db[sid]

    # Generate the percentiles.
    year = stn_data['Year']
    month = stn_data['Month']
    level = stn_data['Elevation'] - stn_data['Water Level']
    q = [100, 90, 75, 50, 25, 10, 0]
    percentiles, nyear = compute_monthly_statistics_table(year, month,
                                                          level, q)

    # Produce the figure.
    fw, fh = 8, 6
    fig = plt.figure(figsize=(fw, fh))
    lm, rm, bm, tm = 0.75/fw, 0.1/fw, 1.25/fh, 0.3/fh

    # Produce the axe.
    ax = fig.add_axes([lm, bm, 1-lm-rm, 1-bm-tm], zorder=1)
    ax.set_facecolor('0.85')
    ax.grid(axis='both', color='white', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    for loc in ax.spines:
        ax.spines[loc].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0)

    # Plot the percentiles.
    xpos = range(12)
    idx = [0, 1, 2, 4, 5, 6]
    for i in range(len(idx)-1):
        ax.bar(xpos, percentiles[:, idx[i]]-percentiles[:, idx[i+1]], 0.95,
               percentiles[:, idx[i+1]], color=rbg[i])
    ax.plot(xpos, percentiles[:, 3], '^k')

    # Plot daily series.
    year = stn_data['Year']
    time = stn_data['Time'][year == cur_year]
    level = stn_data['Elevation'] - stn_data['Water Level'][year == cur_year]
    ax.plot((time-time[0])/365*12-0.5, level, '.', color='red')

    # Axe limits.
    ymax = max(np.max(percentiles), np.max(level))
    ymin = min(np.min(percentiles), np.min(level))
    yrange = ymax - ymin
    yoffset = 0.1/fh*yrange
    ax.axis([-1, 12, ymin-yoffset, ymax+yoffset])
    ax.invert_yaxis()

    # Set axis labels.
    ax.set_ylabel("Niveau d'eau en m sous la surface", fontsize=16,
                  labelpad=10)

    # Set ticks and ticklabels.
    ax.set_xticks(np.arange(-0.5, 11.51))
    ax.set_xticklabels([])

    xlabelspos = np.arange(12)
    months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jui', 'Aoû', 'Sep',
              'Oct', 'Nov', 'Déc']
    y = ymax+yoffset
    for m, n, x in zip(months, nyear, xlabelspos):
        offset = transforms.ScaledTranslation(0, -3/72, fig.dpi_scale_trans)
        ax.text(x, y, m, ha='center', va='top', fontsize=12,
                transform=ax.transData+offset)
        offset = transforms.ScaledTranslation(0, -18/72, fig.dpi_scale_trans)
        ax.text(x, y, '(%d)' % n, ha='center', va='top', fontsize=9,
                transform=ax.transData+offset)

    # Add a Title.
    offset = transforms.ScaledTranslation(0, 3/72, fig.dpi_scale_trans)
    title = "Puits %s (%s)" % (stn_data['Name'], sid)
    ax.text(0, 1, title, weight='normal', fontsize=12,
            transform=ax.transAxes+offset)

    # Create a custom Legend.
    ax_pos = ax.get_position()
    ax_pos.y0 = 0
    ax_pos.y1 = 1
    ax2 = fig.add_axes(ax_pos, facecolor=None)
    ax2.axis('off')

    labels = ['<10', '10-24', '25-75', '76-90', '>90', 'Médiane',
              'Mesures\nde %d' % cur_year]

    x = [0, 0.075, 0.15, 0.225, 0.3, 0.45, 0.6]
    x = [val+0.2 for val in x]

    # Add the pathes to the legend
    rw = 0.3/fw*1
    rh = 0.15/fh*1
    mpad = mpl.transforms.ScaledTranslation(0, 30/72, fig.dpi_scale_trans)
    lpad = mpl.transforms.ScaledTranslation(0, 25/72, fig.dpi_scale_trans)
    for i in range(5):
        ax2.add_patch(
                mpl.patches.Rectangle((x[i], 0), rw, rh, fc=rbg[i],
                                      ec='black', linewidth=0.5,
                                      transform=ax2.transAxes+mpad))
        ax2.text(x[i]+rw/2, 0, labels[i], ha='center', va='top', fontsize=10,
                 transform=ax2.transAxes+lpad)

    mpad = mpl.transforms.ScaledTranslation(0, 35/72, fig.dpi_scale_trans)  
    ax2.plot([x[i+1]], [0], marker='^', color='black', ms=10, ls='',
             transform=ax2.transAxes+mpad)
    ax2.text(x[i+1], 0, labels[i+1], ha='center', va='top', fontsize=10,
                 transform=ax2.transAxes+lpad)
    
    ax2.plot([x[i+2]], [0], marker='.', color='red', ms=10, ls='',
             transform=ax2.transAxes+mpad)
    ax2.text(x[i+2], 0, labels[i+2], ha='center', va='top', fontsize=10,
             transform=ax2.transAxes+lpad)

    # Plot and save the figure.
    plt.show(block=False)

    return percentiles


if __name__ == "__main__":
    plt.close('all')
    percentiles = plot_10yrs_annual_statistical_hydrograph('03090006', 2016)
