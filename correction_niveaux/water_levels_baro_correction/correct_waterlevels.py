# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Institut National de la Recherche Scientifique (INRS)
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------


# ---- Standard party imports
import csv
import os
import os.path as osp
from datetime import datetime

# ---- Third party imports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
import scipy.signal
import xlrd


workdir = osp.dirname(__file__)


def read_rsesq_data():
    print("Loading RSESQ data... ", end='')

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

        rsesq_data[stn_id] = stn_readings.copy()

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
    stn_readings = stn_readings.rename(
        columns={'Water level (masl)': 'Water Level (masl)',
                 'Water temperature (degC)': 'Temperature (degC)'})

    rsesq_data['03097082'] = stn_readings.copy()

    # Add some of the station metadata to the reading dataframe.
    for stn_id, stn_info in rsesq_data_raw.items():
        rsesq_data[stn_id].attrs['id'] = stn_info['ID']
        rsesq_data[stn_id].attrs['name'] = stn_info['Name']
        rsesq_data[stn_id].attrs['latitude'] = stn_info['Latitude']
        rsesq_data[stn_id].attrs['longitude'] = stn_info['Longitude']
        rsesq_data[stn_id].attrs['elevation'] = stn_info.get('Elevation', '')

    print("done")
    return rsesq_data


def load_baro_from_narr_preprocessed_file():
    print("Loading NARR barometric data... ", end='')
    patm_narr_fname = osp.join(
        osp.dirname(osp.dirname(__file__)),
        'narr_grid_barodata',
        'patm_narr_data_gtm0.csv')

    # Get the barometric data.
    narr_baro = pd.read_csv(patm_narr_fname, header=[0, 1, 2])

    narr_baro = narr_baro.set_index(
        [('Latitude (dd)', 'Longitude (dd)', 'Station')], drop=True)
    narr_baro.index = pd.to_datetime(
        narr_baro.index, format="%Y-%m-%d %H:%M:%S")
    narr_baro.index = narr_baro.index.rename('datetime')

    # !!! It is important to shift the data by 5 hours to match the
    #     local time of the data from the RSESQ.
    narr_baro.index = narr_baro.index - pd.Timedelta(hours=5)

    # Extract latitude and longitude data from the columns multi-index and drop
    # these from the columns.
    narr_coord = pd.DataFrame([], index=narr_baro.columns.get_level_values(2))
    narr_coord['lat_dd'] = (
        narr_baro.columns.get_level_values(0).astype('float'))
    narr_coord['lon_dd'] = (
        narr_baro.columns.get_level_values(1).astype('float'))

    narr_baro.columns = narr_baro.columns.droplevel(level=[0, 1])

    narr_baro.attrs['coords'] = narr_coord
    print("done")

    return narr_baro


def load_earthtides_from_preprocessed_file():
    print("Loading Earth tides synthetic data... ", end='')
    synth_earthtides = pd.read_csv(osp.join(
        osp.dirname(osp.dirname(__file__)),
        'synthetic_earthtides',
        'synthetic_earthtides_1980-2018_1H_UTC.csv'))
    synth_earthtides['Date'] = pd.to_datetime(
        synth_earthtides['Date'], format="%Y-%m-%d %H:%M:%S")
    synth_earthtides.set_index(['Date'], drop=True, inplace=True)

    # !!! It is important to shift the data by 5 hours to match the
    #     local time of the data from the RSESQ.
    synth_earthtides.index = synth_earthtides.index - pd.Timedelta(hours=5)
    print("done")
    return synth_earthtides


# Load RSESQ data.
rsesq_data = read_rsesq_data()


# Load Baro and Earthtides data from preprocessed csv file.
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
# Pas de données aux 15 minutes pour le puits #05080003

pdfpages = PdfPages(
    osp.join(osp.dirname(__file__), 'corrected_water_levels.pdf'))
iwell = 0
for sid, sta_data in rsesq_data.items():
    sta_name = sta_data.attrs['name']
    sta_lat = sta_data.attrs['latitude']
    sta_lon = sta_data.attrs['longitude']
    sta_alt = sta_data.attrs['elevation']

    brf_fname = osp.join(
        osp.dirname(osp.dirname(__file__)),
        'brf_1hour_projets_gwhat',
        'brf_1hour_results',
        'brf_{}.csv'.format(sid))

    if sid in influenced or not osp.exists(brf_fname):
        # This means that no BRF analysis has been done yet for that well.
        continue
    iwell += 1

    # ---- Get data for that well.
    sta_data = sta_data.rename(columns={'Water Level (masl)': 'WL(masl)',
                                        'Temperature (degC)': 'WT(degC)'})
    sta_data.index.name = 'Date'
    sta_data = sta_data[~sta_data.index.duplicated()].copy()

    filename = '{}_{}.csv'.format(sid, sta_name)
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
        barodata = baro_narr[[sid]].copy()
        barodata = barodata.rename(columns={sid: 'BP(m)'})
        barodata = barodata.resample('1H').asfreq()
        barodata = barodata.interpolate(method='linear')

        # Add Earth tide data to the WL time series.
        etdata = earthtides[[sid]].copy()
        etdata = etdata[~etdata.index.duplicated()]
        etdata = etdata.resample('1H').asfreq()
        etdata = etdata.interpolate(method='linear')
        etdata = etdata.rename(columns={sid: 'ET(nm/s**2)'})

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
        sta_data = sta_data[~sta_data.index.duplicated()].copy()

        WL = sta_data['WL(masl)']
        WLcorr = sta_data['WL(masl)'] + sta_data['dWL(m)']
        sta_data['WLcorr(masl)'] = sta_data['WL(masl)'] + sta_data['dWL(m)']

        # ---- Plot the data.
        plt.close('all')
        plt.ioff()
        fig, ax = plt.subplots()
        fig.set_size_inches(8, 4)

        data_av_2000 = sta_data[sta_data.index < datetime(2000, 1, 1)]
        l1, = ax.plot(data_av_2000['WL(masl)'], '-', color='0.5', lw=1)
        l2, = ax.plot(data_av_2000['WLcorr(masl)'], '-', color='blue', lw=1)

        data_af_2000 = sta_data[sta_data.index >= datetime(2000, 1, 1)]
        ax.plot(data_af_2000['WL(masl)'], '-', color='0.5', lw=1)
        ax.plot(data_af_2000['WLcorr(masl)'], '-', color='blue', lw=1)

        ax.set_ylabel("Niveaux d'eau p/r n.m.m. (m)",
                      fontsize=14, labelpad=15)
        ax.set_title("{} (#{})".format(sta_name, sid), pad=25)

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
    if not osp.exists(dirname):
        os.makedirs(dirname)

    filename = osp.join(dirname, filename)
    sta_data.to_csv(filename)

    with open(filename, 'r', encoding='utf8') as csvfile:
        reader = list(csv.reader(csvfile, delimiter=','))

    fcontent = [
        ["Well Name", sta_name],
        ["Well ID", sid],
        ["Latitude", sta_lat],
        ["Longitude", sta_lon],
        ["Altitude", sta_alt],
        ["Province", 'Qc'],
        [],
        ]
    fcontent.extend(reader)

    with open(filename, 'w', encoding='utf8') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', lineterminator='\n')
        writer.writerows(fcontent)

    print('done')
pdfpages.close()
