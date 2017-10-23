# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 15:28:06 2017
@author: jsgosselin
"""

# ---- Imports: standard library

from urllib.request import urlopen
from urllib.error import HTTPError, URLError

# ---- Imports: third parties

import numpy as np

# ---- Imports: local

from readers.base import AbstractReader


# ---- Base functions


def read_stationlist_from_tor():
    """"Read and format the `Station Inventory En.csv` file from Tor ftp."""

    url = "ftp://client_climate@ftp.tor.ec.gc.ca"
    url += "/Pub/Get_More_Data_Plus_de_donnees/Station%20Inventory%20EN.csv"

    try:
        html = urlopen(url).read()
    except (HTTPError, URLError):
        return None

    try:
        data = html.decode('utf-8-sig').split('\n')
    except (UnicodeDecodeError, UnicodeError):
        return None

    FIELDS_KEYS_STR = [('Name', 'Name'),
                       ('Province', 'Province'),
                       ('Climate ID', 'ID'),
                       ('Station ID', 'Station ID')]
    FIELDS_KEYS_FLOAT = [('Latitude (Decimal Degrees)', 'Latitude'),
                         ('Longitude (Decimal Degrees)', 'Longitude'),
                         ('Elevation (m)', 'Elevation')]
    FIELDS_KEYS_INT = [('HLY First Year', 'HLY First Year'),
                       ('HLY Last Year', 'HLY Last Year'),
                       ('DLY First Year', 'DLY First Year'),
                       ('DLY Last Year', 'DLY Last Year'),
                       ('MLY First Year', 'MLY First Year'),
                       ('MLY Last Year', 'MLY Last Year')]

    df = {}
    columns = None
    for row in data:
        if row[0] == 'Name':
            columns = row

        if columns:
            sid = row[columns.index('Climate ID')]
            for field, key in FIELDS_KEYS_STR:
                df[sid][key] = row[columns.index(field)]
            for field, key in FIELDS_KEYS_FLOAT:
                try:
                    df[sid][key] = float(row[columns.index(field)])
                except ValueError:
                    df[sid][key] = 'NA'
            for field, key in FIELDS_KEYS_INT:
                try:
                    df[sid][key] = int(row[columns.index(field)])
                except ValueError:
                    df[sid][key] = 'NA'
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
    