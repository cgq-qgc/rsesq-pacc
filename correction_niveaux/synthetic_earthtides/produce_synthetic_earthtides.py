# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Institut National de la Recherche Scientifique (INRS)
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

"""
This scripts use PyGTide to produce a set of synthetic Earth tides data at the
location of each well of the RSESQ. The results are then saved in a csv.

https://github.com/hydrogeoscience/pygtide
"""

# ---- Standard party imports
import os.path as osp
from datetime import datetime

# ---- Third party imports
import numpy as np
import pandas as pd
import pygtide

# ---- Local imports
from data_readers import MDDELCC_RSESQ_Reader


def generate_earth_tides(latitude, longitude, elevation, start_year, end_year,
                         samplerate=3600):
    """
    Generate Earth tide synthetic data for the give latitude, longitude and
    elevation.
    """
    # We need to loop over the years or else ETERNA complains.
    pt = pygtide.pygtide()
    etdata = pd.DataFrame()
    for year in range(start_year, end_year + 1):
        print("Calculating Earth tides for year %d..." % year)
        start = datetime(year, 1, 1)
        duration = 366 * 24
        pt.predict(latitude, longitude, elevation, start, duration, samplerate)

        # Retrieve the results as a pandas dataframe.
        data = pt.results()
        data = data[['UTC', 'Signal [nm/s**2]']]
        data.rename(columns={'UTC': 'Date'}, inplace=True)
        data.set_index(['Date'], drop=True, inplace=True)
        data = data.tz_localize(None)

        etdata = pd.concat([etdata, data]).drop_duplicates()
    return etdata


# %% Produce and save the synthetic earth tides data to an csv file.

rsesq_reader = MDDELCC_RSESQ_Reader()
etdata_stack = None
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
    if etdata_stack is None:
        etdata_stack = etdata
    else:
        etdata_stack = pd.merge(etdata_stack, etdata,
                                left_index=True, right_index=True,
                                how='inner')

# Save data to a csv file.
dirname = osp.dirname(__file__)
filename = osp.join(dirname, 'synthetic_earthtides_1980-2017_1H_UTC.csv')
etdata_stack.to_csv(filename)
