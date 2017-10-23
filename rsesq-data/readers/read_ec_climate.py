# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 15:28:06 2017
@author: jsgosselin
"""

# ---- Imports: standard library

from urllib.request import urlopen
from urllib.error import HTTPError, URLError

# ---- Imports: local

from readers.base import AbstractReader


# ---- Base functions


def get_climate_stations_from_tor():
    """
    Get the list of available climate station from Tor ftp.
    """
    # Save the content of the file in a memory buffer.
    url = "ftp://client_climate@ftp.tor.ec.gc.ca"
    url += "/Pub/Get_More_Data_Plus_de_donnees/Station%20Inventory%20EN.csv"

    try:
        html = urlopen(url).read()
    except (HTTPError, URLError):
        return None

    try:
        data = html.decode('utf-8-sig').split('\n')
        return data
    except (UnicodeDecodeError, UnicodeError):
        return None

# ---- API


class EC_Climate_Reader(AbstractReader):

    DATABASE_FILEPATH = 'ec_climate_database.npy'

    def __init__(self):
        super(EC_Climate_Reader, self).__init__()

    def load_database(self):
        pass

    def stations(self):
        pass

    def station_ids(self):
        pass

    def save_station_to_hdf5(self, station_id, filepath):
        pass

    def save_station_to_csv(self, station_id, filepath):
        pass


if __name__ == "__main__":
    data = get_climate_stations_from_tor()
    
    # reader = EC_Climate_Reader()
    # reader.save_station_to_csv('01160002', 'test.csv')
    