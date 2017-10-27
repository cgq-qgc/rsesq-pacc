# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 20:24:09 2017
@author: jsgosselin
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms
from readers import MDDELCC_RSESQ_Reader

rbg = [[57/255, 82/255, 164/255],
       [110/255, 205/255, 222/255],
       [105/255, 189/255, 69/255],
       [248/255, 151/255, 29/255],
       [152/255, 100/255, 38/255]]


def compute_monthly_statistics_table(years, months, values, q):
    percentiles = []
    for m in range(1, 13):
        ixs = np.where(months == m)[0]
        percentiles.append(np.percentile(values[ixs], q))
    return np.array(percentiles)


def plot_10yrs_annual_statistical_hydrograph(sid, cur_year):
    reader = MDDELCC_RSESQ_Reader()
    stn_data = reader._db[sid]

    # Generate the percentiles.
    year = stn_data['Year']
    month = stn_data['Month']
    level = stn_data['Elevation'] - stn_data['Water Level']
    q = [100, 90, 75, 50, 25, 10, 0]
    percentiles = compute_monthly_statistics_table(year, month, level, q)

    # Produce the figure.
    fw, fh = 8, 5
    fig = plt.figure(figsize=(fw, fh))
    lm, rm, bm, tm = 0.75/fw, 0.1/fw, 0.35/fh, 0.3/fh
        
    # Produce the axe.
    ax = fig.add_axes([lm, bm, 1-lm-rm, 1-bm-tm], zorder=1)
    ax.set_facecolor('0.85')
    ax.grid(axis='both', color='white', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    ax.invert_yaxis()
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

    # Set axis labels.
    ax.set_ylabel("Niveau d'eau en m sous la surface", fontsize=16,
                  labelpad=10)

    # Set ticks and ticklabels.
    ax.set_xticks(np.arange(-0.5, 11.51))
    ax.set_xticks(np.arange(12), minor=True)

    months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jui', 'Aoû', 'Sep',
              'Oct', 'Nov', 'Déc']
    ax.set_xticklabels([])
    ax.set_xticklabels(months, minor=True, fontsize=12)

    # Add a Title.
    offset = transforms.ScaledTranslation(0, 3/72, fig.dpi_scale_trans)
    title = "Puits %s (%s)" % (stn_data['Name'], sid)
    ax.text(0, 1, title, weight='normal', fontsize=12,
            transform=ax.transAxes+offset)

    # Plot and save figure.
    plt.show(block=False)

    return percentiles


if __name__ == "__main__":
    plt.close('all')
    percentiles = plot_10yrs_annual_statistical_hydrograph('03090006', 2016)
