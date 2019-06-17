# -*- coding: utf-8 -*-
"""
Created on Mon Apr  1 15:01:49 2019
@author: User
"""

import os.path as osp
import pygtide
from readers import MDDELCC_RSESQ_Reader
import pytz
import datetime
import pandas as pd

WORKDIR = ("C:/Users/User/OneDrive/INRS/2017 - Projet INRS PACC/"
           "Correction Baro RSESQ")


def generate_earth_tides(latitude, longitude, elevation, start_year, end_year):
    """
    Generate Earth tide synthetic data for the give latitude, longitude and
    elevation.
    """
    # Define the UTC time delta
    utc_tz = pytz.timezone('UTC')
    utc_dt = pytz.timezone('UTC').localize(datetime.datetime(2017, 1, 1))
    local_tz = pytz.timezone('US/Eastern')
    local_dt = local_tz.localize(datetime.datetime(2017, 1, 1))
    tz_delta = local_dt - utc_dt

    pt = pygtide.pygtide()
    etdata = pd.DataFrame()
    for year in range(start_year, end_year + 1):
        print("Calculating Earth tides for year %d..." % year)
        start = datetime.datetime(year, 1, 1)
        duration = 366 * 24
        samplerate = 60 * 60
        pt.predict(latitude, longitude, elevation, start, duration, samplerate)

        # retrieve the results as dataframe
        data = pt.results()
        data = data[['UTC', 'Signal [nm/s**2]']]
        data.loc[:, 'UTC'] = data.loc[:, 'UTC'] - tz_delta
        data.rename(columns={'UTC': 'Index'}, inplace=True)
        data.set_index(['Index'], drop=True, inplace=True)
        data = data.tz_localize(None)
        data = data.resample('D').asfreq()

        etdata = pd.concat([etdata, data]).drop_duplicates()
        print('done')

    return etdata

etdata = generate_earth_tides(rsesq_lat[0], rsesq_lon[0], rsesq_elev[0],
                              1980, 2018)

# %% Load RSESQ database.

DATABASE_FILEPATH = osp.join(WORKDIR, "mddelcc_rsesq_database.npy")
rsesq_reader = MDDELCC_RSESQ_Reader()
rsesq_reader.DATABASE_FILEPATH = DATABASE_FILEPATH
rsesq_reader.load_database()

# Get lat/lon of RSESQ stations
rsesq_lat = []
rsesq_lon = []
rsesq_elev = []
stn_ids = rsesq_reader.station_ids()
for stn_id in stn_ids:
    rsesq_lat.append(float(rsesq_reader[stn_id]['Latitude']))
    rsesq_lon.append(float(rsesq_reader[stn_id]['Longitude']))
    try:
        rsesq_elev.append(float(rsesq_reader[stn_id]['Elevation']))
    except KeyError:
        # We need to download the data to get the station elevation because
        # this info is not in the kml file.
        rsesq_reader.fetch_station_wldata(stn_id)
    finally:
        rsesq_elev.append(float(rsesq_reader[stn_id]['Elevation']))

# %%

etdata = generate_earth_tides(rsesq_lat[0], rsesq_lon[0], rsesq_elev[0])
