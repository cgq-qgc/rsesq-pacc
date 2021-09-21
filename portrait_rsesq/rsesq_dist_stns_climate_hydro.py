# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Institut National de la Recherche Scientifique (INRS)
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms
from readers import (MDDELCC_RSESQ_Reader,
                     MDDELCC_CEHQ_Reader,
                     EC_Climate_Reader)


def find_closest_location(lat1, lon1, lat2, lon2):
    """
    Compute the minimum horizontal distance between a location in radians and
    a set of locations also in radians.
    """
    r = 6373  # r is the Earth radius in km

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    min_dist = np.min(r * c)

    return min_dist


def calc_rsesq_dist_to_climate_and_hydro():
    """
    Compute the distance between each piezometric station of the RSESQ
    and the nearest climatic and hydrometric station.
    """
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
    """
    Plot a bar diagram that shows the number of piezometric stations of the
    RSESQ classied according to the distance to the neares climatic
    station (above in blue) and hydrometric station (below in organge).
    """
    # Produce the figure.

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax2 = ax.twiny()

    ax.set_facecolor('0.85')
    ax.grid(axis='both', color='white', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    for loc in ax.spines:
        ax.spines[loc].set_visible(False)
        ax2.spines[loc].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0)
    ax.xaxis.set_label_position('top')

    ax2.tick_params(axis='both', which='both', length=0)
    ax2.xaxis.set_label_position('bottom')

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
                  fontsize=16, labelpad=20)
    ax.set_xlabel("Distance à la station climatique la plus proche (km)",
                  fontsize=16, labelpad=25)
    ax2.set_xlabel("Distance à la station hydrométrique la plus proche (km)",
                   fontsize=16, labelpad=25)

    # Define the axe ticks and labels.

    ax.axis(ymin=-300, ymax=300)
    ypos = np.arange(-300, 301, 100)
    ax.set_yticks(ypos)
    ax.set_yticklabels(np.abs(ypos))

    ax.set_xticks(xpos)
    ax.set_xticklabels(["\u2264"+str(v) for v in bins])
    ax2.set_xticks(xpos)
    ax2.set_xticklabels(["\u2264"+str(v) for v in bins])

    # Plot text values over the barplot.

    for x, value, value2 in zip(xpos, values, values2):
        offset = transforms.ScaledTranslation(0, 2/72, fig.dpi_scale_trans)
        text = "%d\n(%d%%)" % (value, value/len(dist1)*100)
        ax.text(x, value, text, ha='center', va='bottom',
                transform=ax.transData+offset)

        offset = transforms.ScaledTranslation(0, -2/72, fig.dpi_scale_trans)
        text = "%d\n(%d%%)" % (abs(value2), abs(value2)/len(dist2)*100)
        ax2.text(x, value2, text, ha='center', va='top',
                 transform=ax.transData+offset)

    # Show and save figure.

    plt.tight_layout()
    plt.show(block=False)
    fig.savefig('rsesq_dist_stns_climate_hydro.pdf')


if __name__ == "__main__":
    results = calc_rsesq_dist_to_climate_and_hydro()
    rsesq_stns, dist_to_climstn, dist_to_hydstn = results
    plt.close('all')
    plot_bar_diagram(dist_to_climstn, dist_to_hydstn)
