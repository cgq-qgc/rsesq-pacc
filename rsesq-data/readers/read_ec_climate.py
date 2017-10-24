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


    return df


# ---- API


class EC_Climate_Reader(AbstractReader):

    DATABASE_FILEPATH = 'ec_climate_database.npy'

    def __init__(self):
        super(EC_Climate_Reader, self).__init__()

    def load_database(self):
        try:
            self._db = np.load(self.DATABASE_FILEPATH).item()
        except FileNotFoundError:
            self.fetch_database_from_mddelcc()

    def fetch_database(self):
        self._db = read_stationlist_from_tor()
        np.save(self.DATABASE_FILEPATH, self._db)

    def stations(self):
        pass

    def station_ids(self):
        pass

    def save_station_to_hdf5(self, station_id, filepath):
        pass

    def save_station_to_csv(self, station_id, filepath):
        pass


if __name__ == "__main__":
    data = read_stationlist_from_tor()
    
    # reader = EC_Climate_Reader()
    # reader.save_station_to_csv('01160002', 'test.csv')
    