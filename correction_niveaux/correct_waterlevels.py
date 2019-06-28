# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Jean-Sébastien Gosselin
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------


# ---- Standard party imports
import csv
import datetime
import os.path as osp
import sys
# ---- Third party imports
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyhelp.utils import calc_dist_from_coord
import scipy.signal
# ---- Local import
from data_readers import MDDELCC_RSESQ_Reader
from data_readers.read_mddelcc_rses import get_wldata_from_xls
from correction_niveaux.utils import (load_baro_from_narr_preprocessed_file,
                                      load_earthtides_from_preprocessed_file)


WORKDIR = osp.dirname(__file__)


# %% Load RSESQ database.

rsesq_reader = MDDELCC_RSESQ_Reader(workdir="D:/Data")
rsesq_reader.load_database()

# We need to add data from Sainte-Martine manually because they were not
# published on the RSESQ website.
data = get_wldata_from_xls("D:/Data/Données_03097082.xls")
rsesq_reader._db["03097082"].update(data)


# %% Load Baro and Earthtides data from preprocessed csv file.

baro_narr = load_baro_from_narr_preprocessed_file()
earthtides = load_earthtides_from_preprocessed_file()

# %% Format water level, barometric, and Earth tide data.

influenced = ['03030011', '03040013', '03040010', '03040011', '03030005']

for sid in rsesq_reader.station_ids():
    brf_fname = osp.join(osp.dirname(__file__),
                         'gwt_correction_baro',
                         'brf_{}.csv'.format(sid))
    if not osp.exists(brf_fname):
        # This means that no BRF is available for this probably, probably
        # because it is influenced by pumping.
        continue

    # Add baro data to the WL time series.
    barodata = baro_narr[[sid]]
    barodata.rename(columns={sid: 'BP(m)'}, inplace=True)
    barodata = barodata.resample('1H').asfreq()
    barodata = barodata.interpolate(method='linear')

    # Add Earth tide data to the WL time series.
    etdata = earthtides[[sid]]
    etdata = etdata[~etdata.index.duplicated()]
    etdata = etdata.resample('1H').asfreq()
    etdata = etdata.interpolate(method='linear')
    etdata.rename(columns={sid: 'ET(nm/s**2)'}, inplace=True)

    corr_data = barodata
    corr_data = pd.merge(
        corr_data, etdata, left_index=True, right_index=True, how='inner')

    # ---- Correct the WL data with the BRF

    # Get the BRF function.
    brf_data = pd.read_csv(brf_fname, skip_blank_lines=False, header=14)

    nlag = len(brf_data) - 1
    ndat = len(corr_data)
    dWL = np.empty(ndat) * np.nan

    BP = scipy.signal.detrend(corr_data['BP(m)'])
    M = np.empty((ndat - nlag, nlag + 1))
    M[:, 0] = BP[nlag:]
    A = brf_data['A'].copy()
    A[A.isnull()] = 0
    for i in range(1, nlag + 1):
        M[:, i] = BP[nlag - i:-i]
    dWL_BP = np.dot(M, A)

    ET = scipy.signal.detrend(corr_data['ET(nm/s**2)'])
    M = np.empty((ndat - nlag, nlag + 1))
    M[:, 0] = ET[nlag:]
    B = brf_data['B'].copy()
    B[B.isnull()] = 0
    for i in range(1, nlag + 1):
        M[:, i] = ET[nlag - i:-i]
    dWL_ET = np.dot(M, B) / 3.281

    dWL[nlag:] = dWL_BP + dWL_ET

    corr_data['dWL(m)'] = dWL

    # ---- Plot the results
    sta_data = rsesq_reader.get_station_data(sid)
    sta_data.rename(columns={'Water Level (masl)': 'WL(masl)',
                             'Temperature (degC)': 'WT(degC)'},
                    inplace=True)
    sta_data.index.name = 'Date'
    sta_data = sta_data[~sta_data.index.duplicated()]
    sta_data = pd.merge(sta_data, corr_data[['dWL(m)']],
                        left_index=True, right_index=True,
                        how='inner')
    sta_data = sta_data[~sta_data.index.duplicated()]
    # sta_data = sta_data.resample('1D').asfreq()

    WL = sta_data['WL(masl)'].copy()
    WLcorr = sta_data['WL(masl)'] + sta_data['dWL(m)']
    sta_data['WLcorr(masl)'] = sta_data['WL(masl)'] + sta_data['dWL(m)']

    if False:
        fig, ax = plt.subplots()
        l1, = ax.plot(sta_data['WL(masl)'], '-', color='0.75', lw=1)
        l2, = ax.plot(sta_data['WLcorr(masl)'], '-', lw=1)

        ax.set_ylabel('WL (masl)')
        ax.set_title(rsesq_reader[sid]['Name'] + ' (#' + sid + ')')
        ax.legend([l1, l2],
                  ["Niveau d'eau non corrigés", "Niveaux d'eau corrigés"],
                  bbox_to_anchor=[1, 1], loc='upper right', ncol=3,
                  numpoints=1, fontsize=10, frameon=False)

    # ---- Save the data to file
    filename = osp.join(
        osp.dirname(__file__),
        'corrected_water_levels',
        '%s_%s.csv' % (rsesq_reader[sid]['ID'], rsesq_reader[sid]['Name'])
        )
    sta_data.to_csv(filename)

    with open(filename, 'r', encoding='utf8') as csvfile:
        reader = list(csv.reader(csvfile, delimiter=','))

    fcontent = [
        ["Well Name", rsesq_reader[sid]['Name']],
        ["Well ID", rsesq_reader[sid]['ID']],
        ["Latitude", rsesq_reader[sid]['Latitude']],
        ["Longitude", rsesq_reader[sid]['Longitude']],
        ["Altitude", rsesq_reader[sid]['Elevation']],
        ["Province", 'Qc'],
        [],
        ]
    fcontent.extend(reader)

    with open(filename, 'w', encoding='utf8') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', lineterminator='\n')
        writer.writerows(fcontent)
