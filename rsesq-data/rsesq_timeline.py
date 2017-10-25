# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 08:59:57 2017
@author: jsgosselin
"""

import numpy as np
import matplotlib.pyplot as plt
from readers import MDDELCC_RSESQ_Reader


# ---- Produce the bins

def compute_nbr_stn_bins(bstep):
    reader = MDDELCC_RSESQ_Reader()
    bins = {}
    for stn in reader.stations():
        if 'Year' not in list(stn.keys()):
            continue

        dec = np.unique(stn['Year']//bstep)*bstep
        for d in dec.astype(str):
            if d not in list(bins.keys()):
                bins[d] = 0
            else:
                bins[d] = bins[d] + 1

    years = np.array(list(bins.keys())).astype(int)
    values = np.array(list(bins.values())).astype(int)

    indexes = np.argsort(years)
    years = years[indexes]
    values = values[indexes]

    years = np.append(years, years[-1]+bstep)

    return years, values


# ---- Produce the plot

# Produce the figure.
plt.close('all')
fig, ax = plt.subplots(figsize=(8, 5))
ax.set_facecolor('0.85')
ax.grid(color='white', linestyle='-', linewidth=1)
ax.set_axisbelow(True)
for loc in ax.spines:
    ax.spines[loc].set_visible(False)
ax.tick_params(axis='both', which='both', length=0)

# Produce the barplot.
years, values = compute_nbr_stn_bins(5)
ax.bar(years[:-1]+2.5, values, 4)
ax.set_ylabel('Nombre de stations actives', fontsize=16, labelpad=10)
ax.set_xlabel('Années', fontsize=16, labelpad=10)
ax.set_xticks(np.append(years, years[-1]+5))

# Plot text values over the barplot.
for year, value in zip(years[:-1], values):
    ax.text(year+2.5, value+1, str(value), ha='center', va='bottom')

# Plot a continous line.
years, values = compute_nbr_stn_bins(1)
ax.plot(years[:-1], values, ls='--', lw=1.5, color='red',
        dashes=[5, 2], alpha=0.75)

fig.savefig('nbr_stns_actives_vs_temps.pdf')
plt.tight_layout()
plt.show(block=False)
fig.savefig('nbr_stns_actives_vs_temps.pdf')
