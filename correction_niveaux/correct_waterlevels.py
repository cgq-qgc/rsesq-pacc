# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Jean-Sébastien Gosselin
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------


# ---- Standard party imports
import csv
import os.path as osp
import datetime

# ---- Third party imports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
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

# monteregie (37 wells)
influenced = ['03030011', '03040013', '03040010', '03040011', '03030005']
# chaudiere-appalache (27 wells)
influenced += ['02407004', '02407005', '02340002']
# centre-quebec (24 wells)
influenced += ['03027032', '03027061', '03010006', '03010004']
# capitale-nationale (16 wells)
influenced += ['05150001', ]
# montreal (41 wells)
influenced += ['04017031', '03090006', '03090020', '04017051', '04017011',
               '04640001', '03097131', '03090014', '03090015', '03070001',
               '03097102', '04440001', '04647001']
# Pas de données aux 15 minutes pour la puits #05080003

pdfpages = PdfPages('corrected_water_levels.pdf')
iwell = 0
for sid in rsesq_reader.station_ids():
    brf_fname = osp.join(osp.dirname(__file__),
                         'gwt_correction_baro',
                         'brf_results',
                         'brf_{}.csv'.format(sid))

    if sid not in influenced and not osp.exists(brf_fname):
        # This means that no BRF analysis has been done yet for that well.
        continue
    iwell += 1

    # ---- Get data for that well.
    sta_data = rsesq_reader.get_station_data(sid)
    sta_data.rename(columns={'Water Level (masl)': 'WL(masl)',
                             'Temperature (degC)': 'WT(degC)'},
                    inplace=True)
    sta_data.index.name = 'Date'
    sta_data = sta_data[~sta_data.index.duplicated()]

    filename = '%s_%s.csv' % (rsesq_reader[sid]['ID'],
                              rsesq_reader[sid]['Name'])
    if sid in influenced:
        print("{:>3d} - Saving water levels for influenced well {}...".format(
              iwell, sid), end=' ')
        dirname = osp.join(
            osp.dirname(__file__), 'corrected_water_levels', 'not_corrected')
    else:
        # ---- Prepare the data for the correction
        print("{:>3d} - Correcting water levels for well {}...".format(
              iwell, sid), end=' ')
        dirname = osp.join(osp.dirname(__file__), 'corrected_water_levels')

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
        corr_data = pd.merge(corr_data, etdata, left_index=True,
                             right_index=True, how='inner')

        # ---- Correct the WL data with the BRF

        # Get the BRF function.
        brf_data = pd.read_csv(brf_fname, skip_blank_lines=False, header=14)

        nlag = len(brf_data) - 1
        ndat = len(corr_data)
        dWL = np.empty(ndat) * np.nan

        # Calculate the effects of baro.
        BP = scipy.signal.detrend(corr_data['BP(m)'])
        M = np.empty((ndat - nlag, nlag + 1))
        M[:, 0] = BP[nlag:]
        A = brf_data['A'].copy()
        A[A.isnull()] = 0
        for i in range(1, nlag + 1):
            M[:, i] = BP[nlag - i:-i]
        dWL_BP = np.dot(M, A)

        # Calculate the effects of earth tides.
        ET = scipy.signal.detrend(corr_data['ET(nm/s**2)'])
        M = np.empty((ndat - nlag, nlag + 1))
        M[:, 0] = ET[nlag:]
        B = brf_data['B'].copy()
        B[B.isnull()] = 0
        for i in range(1, nlag + 1):
            M[:, i] = ET[nlag - i:-i]
        dWL_ET = np.dot(M, B) / 3.281

        # Calculate the total effect of baro and earth tides.
        dWL[nlag:] = dWL_BP + dWL_ET
        corr_data['dWL(m)'] = dWL

        # Correct the water levels.
        sta_data = pd.merge(sta_data, corr_data[['dWL(m)']],
                            left_index=True, right_index=True,
                            how='inner')
        sta_data = sta_data[~sta_data.index.duplicated()]

        WL = sta_data['WL(masl)'].copy()
        WLcorr = sta_data['WL(masl)'] + sta_data['dWL(m)']
        sta_data['WLcorr(masl)'] = sta_data['WL(masl)'] + sta_data['dWL(m)']

        # ---- Plot the data.
        plt.ioff()
        fig, ax = plt.subplots()
        fig.set_size_inches(8, 4)

        data_av_2000 = sta_data[
            sta_data.index < datetime.datetime(2000, 1, 1)]
        l1, = ax.plot(data_av_2000['WL(masl)'], '-', color='0.5', lw=1)
        l2, = ax.plot(data_av_2000['WLcorr(masl)'], '-', color='blue', lw=1)

        data_af_2000 = sta_data[
            sta_data.index >= datetime.datetime(2000, 1, 1)]
        ax.plot(data_af_2000['WL(masl)'], '-', color='0.5', lw=1)
        ax.plot(data_af_2000['WLcorr(masl)'], '-', color='blue', lw=1)

        ax.set_ylabel("Niveaux d'eau p/r n.m.m. (m)",
                      fontsize=14, labelpad=15)
        ax.set_title(rsesq_reader[sid]['Name'] + ' (#' + sid + ')',
                     pad=25)

        # ---- Setup date format
        adl = ax.get_xaxis().get_major_locator()
        adl.intervald['MONTHLY'] = [0]
        adf = ax.get_xaxis().get_major_formatter()
        adf.scaled[1. / 24] = '%Y'  # set the < 1d scale to H:M
        adf.scaled[1.0] = '%Y'  # set the > 1d < 1m scale to Y-m-d
        adf.scaled[30.] = "%Y"  # set the > 1m < 1Y scale to Y-m
        adf.scaled[365.] = '%Y'  # set the > 1y scale to Y

        ax.legend([l1, l2],
                  ["Niveaux d'eau non corrigés", "Niveaux d'eau corrigés"],
                  bbox_to_anchor=[0, 1], loc='lower left', ncol=3,
                  numpoints=1, fontsize=10, frameon=False, borderaxespad=0,
                  borderpad=0.25)
        fig.tight_layout()
        pdfpages.savefig(fig)
        plt.close('all')

    # ---- Save the data to file
    filename = osp.join(dirname, filename)
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

    print('done')
pdfpages.close()
