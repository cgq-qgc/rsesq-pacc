# -*- coding: utf-8 -*-
"""
Created on Thu Oct 26 08:21:32 2017
@author: jsgosselin
"""

import numpy as np
import matplotlib.pyplot as plt
from multiprocessing import Pool
from readers import (MDDELCC_RSESQ_Reader, MDDELCC_CEHQ_Reader,
                     EC_Climate_Reader)


def find_closest_location(lat1, lon1, lat2, lon2):
    """"Compute the horizontal distance between the two points in km."""
    r = 6373  # r is the Earth radius in km

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    min_dist = np.min(r * c)

    return min_dist


def calc_rsesq_dist_to_climate_and_hydro():
    reader_eccc = EC_Climate_Reader()
    climstns = reader_eccc.stations(active=True, prov='QC')
    lat2 = np.radians([float(stn['Latitude']) for stn in climstns])
    lon2 = np.radians([float(stn['Longitude']) for stn in climstns])
    dist_to_climstn = []

    reader_cehq = MDDELCC_CEHQ_Reader()
    hydstns = reader_cehq.stations(active=True)
    lat3 = np.radians([float(stn['Latitude']) for stn in hydstns])
    lon3 = np.radians([float(stn['Longitude']) for stn in hydstns])
    dist_to_hydstn = []

    reader_rsesq = MDDELCC_RSESQ_Reader()
    rsesq_stns = reader_rsesq.stations()
    for stn in rsesq_stns:
        if 'Year' not in list(stn.keys()):
            continue

        lat1 = np.radians(float(stn['Latitude']))
        lon1 = np.radians(float(stn['Longitude']))

        dist_to_climstn.append(find_closest_location(lat1, lon1, lat2, lon2))
        dist_to_hydstn.append(find_closest_location(lat1, lon1, lat3, lon3))

    return rsesq_stns, np.array(dist_to_climstn), np.array(dist_to_hydstn)


def plot_bar_diagram(dist1, dist2):
    # Produce the figure.

    fig, ax = plt.subplots(figsize=(8, 5))
    ax2 = ax.twiny()

    ax.set_facecolor('0.85')
    ax.grid(color='white', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    for loc in ax.spines:
        ax.spines[loc].set_visible(False)
        ax2.spines[loc].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0)
    ax2.tick_params(axis='both', which='both', length=0)

    # Generate the bins.

    bins = [1, 5, 10, 20, 30, 40, 50, 75, 150, np.inf]
    values = []
    values2 = []
    for b in bins:
        values.append(len(np.where(dist1 <= b)[0]))
        values2.append(-len(np.where(dist2 <= b)[0]))

    # Plot the data.

    xpos = range(len(bins))
    ax.bar(xpos, values, 0.75)
    ax2.bar(xpos, values2, 0.75, color='orange')

    ax.set_ylabel("Nombre de stations piézométriqes",
                  fontsize=16, labelpad=10)
    ax.set_xlabel("Distance à la station climatique la plus proche (km)",
                  fontsize=16, labelpad=10)
    ax2.set_xlabel("Distance à la station hydrométrique la plus proche (km)",
                   fontsize=16, labelpad=10)

    ax.set_xticks(xpos)
    ax.set_xticklabels(["\u2264"+str(v) for v in bins])
    ax2.set_xticks(xpos)
    ax2.set_xticklabels(["\u2264"+str(v) for v in bins])

    ax.axis(ymin=-300, ymax=300)

    # Plot text values over the barplot.

    for x, value, value2 in zip(xpos, values, values2):
        ax.text(x, value+1, str(value), ha='center', va='bottom')
        ax2.text(x, value2-5, str(abs(value2)), ha='center', va='top')

    # Show and save figure.

    plt.tight_layout()
    plt.show(block=False)
    fig.savefig('rsesq_dist_stns_climate_hydro.pdf')


if __name__ == "__main__":
    # results = calc_rsesq_dist_to_climate_and_hydro()
    # rsesq_stns, dist_to_climstn, dist_to_hydstn = results
    plt.close('all')
    plot_bar_diagram(dist_to_climstn, dist_to_hydstn)


    # plt.close('all')
    # plt.plot(dist_to_climstn, dist_to_hydstn, '.', alpha=0.85)
    # plt.show()
