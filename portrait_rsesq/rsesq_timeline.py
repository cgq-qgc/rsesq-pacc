# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 08:59:57 2017
@author: jsgosselin
"""
import pandas as pd
import os.path as osp
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import xlrd


workdir = "D:/Projets/pacc-inrs/portrait_rsesq"


def read_rsesq_data():

    rsesq_data_raw = np.load(
        osp.join(workdir, 'mddelcc_rsesq_database.npy'),
        allow_pickle=True).item()

    rsesq_data = {}
    for stn_id, stn_data in rsesq_data_raw.items():
        stn_readings = pd.DataFrame(
            [],
            columns=['Water Level (masl)', 'Temperature (degC)']
            )
        if 'Time' not in stn_data:
            rsesq_data[stn_id] = stn_readings
            continue

        stn_readings['Water Level (masl)'] = pd.to_numeric(
            stn_data['Water Level'], errors='coerce')
        stn_readings['Temperature (degC)'] = pd.to_numeric(
            stn_data['Temperature'], errors='coerce')
        stn_readings.index = [
            datetime(*xlrd.xldate_as_tuple(t, 0)) for t in stn_data['Time']]

        rsesq_data[stn_id] = stn_readings

    # We need to add the data from Sainte-Martine manually because they
    # were not available at the time on the RSESQ website.
    stn_data = pd.read_csv(
        osp.join(workdir, 'Sainte-Martine (03097082).csv'),
        skiprows=10)

    stn_readings = stn_data[
        ['Time', 'Water level (masl)', 'Water temperature (degC)']].copy()
    stn_readings.index = [
        datetime(*xlrd.xldate_as_tuple(t, 0)) for t in stn_data['Time']]
    stn_readings = stn_readings.drop('Time', axis=1)

    return rsesq_data


# ---- Compute bins
def compute_nbr_stn_bins(bstep, rsesq_data):
    """Compute the number of active stations for periods of bstep years."""
    bins = {}
    for stn_id, stn_readings in rsesq_data.items():
        if stn_readings.empty:
            continue

        dec = stn_readings.index.year.unique() // bstep * bstep
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

    years = np.append(years, years[-1] + bstep)

    return years, values


def compute_nbr_year_bins(bins, rsesq_data):
    "Compute the number of stations with data for at "
    values = [0] * len(bins)
    for stn_id, stn_readings in rsesq_data.items():
        if stn_readings.empty:
            nyear = 0
        else:
            nyear = len(stn_readings.index.year.unique())

        for i, b in enumerate(bins):
            if nyear >= b:
                values[i] = values[i]+1

    return values


# ---- Produce the plot
def plot_nbr_stn_bins(rsesq_data, bstep=5):
    # Produce the figure.
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_facecolor('0.85')
    ax.grid(color='white', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    for loc in ax.spines:
        ax.spines[loc].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0)

    # Produce the barplot.
    years, values = compute_nbr_stn_bins(bstep, rsesq_data)
    ax.bar(years[:-1]+2.5, values, 4)
    ax.set_ylabel('Nombre de stations actives', fontsize=16, labelpad=10)
    ax.set_xlabel('Années', fontsize=16, labelpad=10)
    ax.set_xticks(np.append(years, years[-1]+5))

    # Plot text values over the barplot.
    for year, value in zip(years[:-1], values):
        ax.text(year+2.5, value+1, str(value), ha='center', va='bottom')

    # Plot a continous line.
    years, values = compute_nbr_stn_bins(1, rsesq_data)
    ax.plot(years[:-1], values, ls='--', lw=1.5, color='red',
            dashes=[5, 2], alpha=0.75)

    plt.tight_layout()
    plt.show(block=False)
    fig.savefig(osp.join(workdir, 'nbr_stns_actives_vs_temps.pdf'))


def plot_nbr_year_bins(rsesq_data,
                       bins=[0, 1, 2, 3, 4, 5, 10, 15, 20, 25, 30, 35, 40]):
    # Produce the figure.
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_facecolor('0.85')
    ax.grid(color='white', linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    for loc in ax.spines:
        ax.spines[loc].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0)

    # Produce the barplot.
    values = compute_nbr_year_bins(bins, rsesq_data)
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
    fig.savefig(osp.join(workdir, 'stns_nbr_vs_year_nbr.pdf'))


if __name__ == "__main__":
    rsesq_data = read_rsesq_data()
    plt.close('all')
    plot_nbr_stn_bins(rsesq_data)
    plot_nbr_year_bins(rsesq_data)
