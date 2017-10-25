# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 08:59:57 2017
@author: jsgosselin
"""

import numpy as np
import matplotlib.pyplot as plt
from readers import MDDELCC_RSESQ_Reader


# ---- Produce the bins

def compute_nbr_stn_bins(bstep, reader):
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


def compute_nbr_year_bins(bins, reader):
    values = [0] * len(bins)
    for stn in reader.stations():
        if 'Year' not in list(stn.keys()):
            nyear = 0
        else:
            nyear = len(np.unique(stn['Year']))

        for i, b in enumerate(bins):
            if nyear >= b:
                values[i] = values[i]+1

    return values


# ---- Produce the plot


def plot_nbr_stn_bins(bstep=5):
    # Produce the figure.
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_facecolor('0.85')
    ax.grid(color='white', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    for loc in ax.spines:
        ax.spines[loc].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0)

    # Produce the barplot.
    years, values = compute_nbr_stn_bins(bstep, MDDELCC_RSESQ_Reader())
    ax.bar(years[:-1]+2.5, values, 4)
    ax.set_ylabel('Nombre de stations actives', fontsize=16, labelpad=10)
    ax.set_xlabel('Années', fontsize=16, labelpad=10)
    ax.set_xticks(np.append(years, years[-1]+5))

    # Plot text values over the barplot.
    for year, value in zip(years[:-1], values):
        ax.text(year+2.5, value+1, str(value), ha='center', va='bottom')

    # Plot a continous line.
    years, values = compute_nbr_stn_bins(1, MDDELCC_RSESQ_Reader())
    ax.plot(years[:-1], values, ls='--', lw=1.5, color='red',
            dashes=[5, 2], alpha=0.75)

    plt.tight_layout()
    plt.show(block=False)
    fig.savefig('nbr_stns_actives_vs_temps.pdf')


def plot_nbr_year_bins(bins=[0, 1, 2, 3, 4, 5, 10, 15, 20, 25, 30, 35, 40]):
    # Produce the figure.
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_facecolor('0.85')
    ax.grid(color='white', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    for loc in ax.spines:
        ax.spines[loc].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0)

    # Produce the barplot.
    values = compute_nbr_year_bins(bins, MDDELCC_RSESQ_Reader())
    xpos = range(len(bins))
    ax.bar(xpos, values, 0.75)
    ax.set_ylabel('Nombre de stations', fontsize=16, labelpad=10)
    ax.set_xlabel("Nombre d'années avec des données disponibles",
                  fontsize=16, labelpad=10)
    ax.set_xticks(xpos)
    ax.set_xticklabels(["\u2265"+str(v) for v in bins])

    # Plot text values over the barplot.
    for x, value in zip(xpos, values):
        ax.text(x, value+1, str(value), ha='center', va='bottom')

    plt.tight_layout()
    plt.show(block=False)
    fig.savefig('stns_nbr_vs_year_nbr.pdf')


if __name__ == "__main__":
    plt.close('all')
    plot_nbr_stn_bins()
    plot_nbr_year_bins()
