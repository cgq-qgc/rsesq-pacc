# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 15:28:06 2017
@author: jsgosselin
"""

# ---- Imports: standard library

from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import numpy as np
import os
import csv
from time import gmtime
import copy

# ---- Imports: third parties

import numpy as np

# ---- Imports: local

from readers.base import AbstractReader
from WHAT.meteo.dwnld_weather_data import (RawDataDownloader,
                                           ConcatenatedDataFrame)


# ---- Base functions


def read_stationlist_from_tor():
    """"Read and format the `Station Inventory En.csv` file from Tor ftp."""

    url = "ftp://client_climate@ftp.tor.ec.gc.ca/"
    url += "Pub/Get_More_Data_Plus_de_donnees/Station%20Inventory%20EN.csv"
    try:
        data = urlopen(url).read()
    except (HTTPError, URLError):
        return None
    try:
        data = data.decode('utf-8-sig').splitlines()
    except (UnicodeDecodeError, UnicodeError):
        return None
    data = list(csv.reader(data, delimiter=','))

    FIELDS_KEYS_STR = [('Name', 'Name'),
                       ('Province', 'Province'),
                       ('Climate ID', 'ID'),
                       ('Station ID', 'Station ID'),
                       ('DLY First Year', 'DLY First Year'),
                       ('DLY Last Year', 'DLY Last Year')]

    FIELDS_KEYS_FLOAT = [('Latitude (Decimal Degrees)', 'Latitude'),
                         ('Longitude (Decimal Degrees)', 'Longitude'),
                         ('Elevation (m)', 'Elevation')]

    df = {}
    columns = None
    for i, row in enumerate(data):
        if len(row) == 0:
            continue
        if row[0] == 'Name':
            columns = row
            data = np.array(data[i+1:])

            # Remove stations with no daily data
            hly_first_year = data[:, columns.index('DLY First Year')]
            data = data[~(hly_first_year == ''), :]

            break
    else:
        return None

    for field, key in FIELDS_KEYS_STR:
        arr = data[:, columns.index(field)]
        arr[arr == ''] = 'NA'
        df[key] = arr.tolist()
    for field, key in FIELDS_KEYS_FLOAT:
        arr = data[:, columns.index(field)]
        arr[arr == ''] = np.nan
        df[key] = arr.tolist()

    # Sanitarize station name.
    df['Name'] = [n.replace('\\', ' ').replace('/', ' ') for n in df['Name']]

    # Determine station status.
    dly_last_year = np.array(df['DLY Last Year']).astype(int)
    df['Status'] = dly_last_year >= 2017

    # Format province value.
    NAME_ABB = [('ALBERTA', 'AB'),
                ('BRITISH COLUMBIA', 'BC'),
                ('MANITOBA', 'MB'),
                ('NEW BRUNSWICK', 'NB'),
                ('NEWFOUNDLAND', 'NL'),
                ('NORTHWEST TERRITORIES', 'NT'),
                ('NOVA SCOTIA', 'NS'),
                ('NUNAVUT', 'NU'),
                ('ONTARIO', 'ON'),
                ('PRINCE EDWARD ISLAND', 'PE'),
                ('QUEBEC', 'QC'),
                ('SASKATCHEWAN', 'SK'),
                ('YUKON TERRITORY', 'YT')]

    for name, abb in NAME_ABB:
        df['Province'] = [p.replace(name, abb) for p in df['Province']]

    return df


# ---- API


class EC_Climate_Reader(AbstractReader):

    DATABASE_FILEPATH = 'ec_climate_database.npy'

    def __init__(self):
        super(EC_Climate_Reader, self).__init__()
        self.raw_data_dir = "raw_datafiles"

    def load_database(self):
        try:
            self._db = np.load(self.DATABASE_FILEPATH).item()
        except FileNotFoundError:
            self.fetch_database()

    def fetch_database(self):
        print("Fetching station list from EC Tor ftp server...")
        self._db = {}
        self._db['Station Table'] = read_stationlist_from_tor()
        self._db['Data Table'] = {}
        np.save(self.DATABASE_FILEPATH, self._db)
        print("Station list fetched sucessfully.")


    def stations(self, active=None, prov=None):
        stations = []
        for sid in self.station_ids():
            stn_info = self.station_info(sid)
            if prov is None or prov == stn_info['Province']:
                if active is None or active == stn_info['Status']:
                    stations.append(stn_info)
        return stations

    def station_ids(self):
        return self._db['Station Table']['ID']

    def station_info(self, sid):
        idx = self._db['Station Table']['ID'].index(sid)
        keys = ['Name', 'Province', 'ID', 'Station ID',
                'Latitude', 'Longitude', 'Elevation',
                'DLY First Year', 'DLY Last Year', 'Status']
        df = {}
        for key in keys:
            df[key] = self._db['Station Table'][key][idx]
        return df

    def station_has_dly_data(self, sid):
        """Check whether station have daily data or not"""
        return self.station_info(sid)['DLY First Year'] != 'NA'

    def fetch_station_data(self, sid, dirname):
        """
        Download the daily climate data for the station corresponding
        to the provided id and save the results in the local database.
        """
        if self.station_has_dly_data(sid) is False:
            print("No daily data is available for station %s." % sid)
            return

        # Download raw datafiles from EC website.

        dwnld_worker = RawDataDownloader()

        dwnld_worker.climateID = sid
        dwnld_worker.dirname = dirname

        station_info = self.station_info(sid)
        dwnld_worker.stationID = station_info['Station ID']
        dwnld_worker.StaName = station_info['Name']

        dwnld_worker.yr_start = max(int(station_info['DLY First Year']), 1980)
        dwnld_worker.yr_end = int(station_info['DLY Last Year'])

        # min_year = station_info[DLY First Year'']

        downloaded_raw_datafiles = dwnld_worker.download_data()

        # Concatenate and save data to the local database.

        cdf = ConcatenatedDataFrame()
        cdf.concatenate_rawdata(downloaded_raw_datafiles)

        self._db['Data Table'][sid] = cdf
        np.save(self.DATABASE_FILEPATH, self._db)

    def save_station_table_to_csv(self, filepath, active=None, prov=None):
        keys = ['Name', 'Province', 'ID', 'Station ID',
                'Latitude', 'Longitude', 'Elevation',
                'DLY First Year', 'DLY Last Year', 'Status']
        fcontent = [keys]
        for stn in self.stations(active, prov):
            fcontent.append([stn[key] for key in keys])

        with open(filepath, 'w', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=',', lineterminator='\n')
            writer.writerows(fcontent)

    def save_station_to_hdf5(self, station_id, filepath):
        pass

    def save_station_to_csv(self, sid, filepath):
        if self.station_has_dly_data(sid) is False:
            print("No daily data is available for station %s." % sid)
            return

        if sid not in list(self._db['Data Table'].keys()):
            self.fetch_station_data(sid, self.raw_data_dir)

        cdf = self._db['Data Table'][sid]
        cdf.save_to_csv(filepath)


if __name__ == "__main__":
    reader = EC_Climate_Reader()
    # reader.fetch_database()

    station_table = reader._db['Station Table']
    dly_data_first = station_table['DLY First Year']
    dly_data_last = station_table['DLY Last Year']
    active_qc_stns = reader.stations(active=True, prov='QC')

    filename = "Active_Climate_Stations_QC.csv"
    reader.save_station_table_to_csv(filename, active=True, prov='QC')
