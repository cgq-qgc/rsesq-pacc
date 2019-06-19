# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Jean-Sébastien Gosselin
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

# ---- Standard party imports
import os.path as osp
from datetime import datetime
import pytz
# ---- Third party imports
import numpy as np
import pandas as pd
import pygtide
# ---- Local imports
from data_readers import MDDELCC_RSESQ_Reader
from data_readers.read_mddelcc_rses import get_wldata_from_xls


def generate_earth_tides(latitude, longitude, elevation, start_year, end_year,
                         samplerate=3600):
    """
    Generate Earth tide synthetic data for the give latitude, longitude and
    elevation.
    """
    pt = pygtide.pygtide()
    etdata = pd.DataFrame()
    for year in range(start_year, end_year + 1):
        print("Calculating Earth tides for year %d..." % year)
        start = datetime(year, 1, 1)
        duration = 366 * 24
        pt.predict(latitude, longitude, elevation, start, duration, samplerate)

        # Retrieve the results as dataframe
        data = pt.results()
        data = data[['UTC', 'Signal [nm/s**2]']]
        data.rename(columns={'UTC': 'Date'}, inplace=True)
        data.set_index(['Date'], drop=True, inplace=True)
        data = data.tz_localize(None)

        etdata = pd.concat([etdata, data]).drop_duplicates()
    return etdata


# %% Load RSESQ database.

rsesq_reader = MDDELCC_RSESQ_Reader(workdir="D:/Data")
rsesq_reader.load_database()

# We need to add data from Sainte-Martine manually because they were not
# published on the RSESQ website.
data = get_wldata_from_xls("D:/Data/Données_03097082.xls")
rsesq_reader._db["03097082"].update(data)

# %% Produce and save the synthetic earth tides data to an csv file.

etdata_stack = pd.DataFrame()
i = 0
for stn_id in rsesq_reader.station_ids():
    i += 1
    sta_data = rsesq_reader.get_station_data(stn_id)
    sta_lat = float(rsesq_reader[stn_id]['Latitude'])
    sta_lon = float(rsesq_reader[stn_id]['Longitude'])
    sta_ele = float(rsesq_reader[stn_id]['Elevation'])
    if np.isnan(sta_ele):
        continue

    etdata = generate_earth_tides(sta_lat, sta_lon, sta_ele, 1980, 2018)
    etdata.rename(columns={'Signal [nm/s**2]': stn_id}, inplace=True)
    if not len(etdata_stack):
        etdata_stack = etdata
    else:
        etdata_stack = pd.merge(etdata_stack, etdata,
                                left_index=True, right_index=True,
                                how='inner')

# Save data to a csv file.
dirname = osp.dirname(__file__)
filename = osp.join(dirname, 'synthetic_earthtides_1980-2017_1H_UTC.csv')
etdata_stack.to_csv(filename)
