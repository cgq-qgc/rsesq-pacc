# -*- coding: utf-8 -*-
"""
Created on Tue Jun 13 14:29:29 2017
@author: jnsebgosselin
"""

# ---- Imports: standard library

from urllib.request import urlopen, urlretrieve
from io import BytesIO
import numpy as np
import os
import requests
import csv

# ---- Imports: third parties

from bs4 import BeautifulSoup, CData
import xlrd

# ---- Imports: local

from readers.base import AbstractReader
from readers.utils import findUnique, find_float_from_str, format_url_to_ascii

# ---- Base functions


def get_xml_url():
    """
    Get the url of the last xml data table.
    """
    mpjs = ('http://www.mddelcc.gouv.qc.ca/eau/piezo/' +
            'carte_google/markers-piezo.js')

    f = urlopen(mpjs)
    reader = f.read().decode('utf-8', 'replace')

    txt = "MYMAP.placePuits('"
    n = len("MYMAP.placePuits('")
    indx0 = reader.find(txt) + n
    indx1 = reader.find("');", indx0)

    url = 'http://www.mddelcc.gouv.qc.ca/eau/piezo/%s' % reader[indx0:indx1]

    return url


def read_xml_datatable(url):
    """
    Read the xml datafile and return a database with the well info
    """
    xml = urlopen(url)
    soup = BeautifulSoup(xml, 'html.parser')
    places = soup.find_all('placemark')

    db = {}
    for place in places:
        desc = place.find('description')
        name = place.find('name').text
        for cd in desc.findAll(text=True):
            if isinstance(cd, CData):
                pid = findUnique('Piézomètre =(.*?)<br/>', cd)

                # ---- Get well info

                db[pid] = {}
                db[pid]['ID'] = pid
                db[pid]['Name'] = name
                db[pid]['Longitude'] = findUnique('Longitude =(.*?)<br/>', cd)
                db[pid]['Latitude'] = findUnique('Latitude =(.*?)<br/>', cd)
                db[pid]['Nappe'] = findUnique('Nappe =(.*?)<br/>', cd)
                db[pid]['Influenced'] = findUnique('Influencé =(.*?)<br/>', cd)
                db[pid]['Last'] = findUnique(
                        'Dernière lecture =(.*?)<br/>', cd)

                # ---- Get datafiles url

                keys = ['url data', 'url drilllog', 'url graph']
                ss = ['<br/><a href="(.*?)">Données',
                      'Données</a><br/><a href="(.*?)">Schéma',
                      'Schéma</a><br/><a href="(.*?)">Graphique']

                for key, s in zip(keys, ss):
                    url = findUnique(s, cd)
                    db[pid][key] = url if None else format_url_to_ascii(url)

    return db


def get_wldata_from_xls(url):
    """
    Get elevation, time, water level and water temperature data from a xls
    file downloaded from http://www.mddelcc.gouv.qc.ca/eau/piezo/.
    """
    # Save the content of the file in a memory buffer.
    response = requests.get(url)
    bytes_io = BytesIO(response.content)

    # Read the content of the file and extract the data.
    with xlrd.open_workbook(file_contents=bytes_io.read()) as wb:
        ws = wb.sheet_by_index(0)

        row_idx = ws.col_values(0).index('Date du relevé')+1
        time = np.array(ws.col_values(0, start_rowx=row_idx)).astype(float)
        wlvl = np.array(ws.col_values(1, start_rowx=row_idx)).astype(float)
        wtemp = np.array(ws.col_values(2, start_rowx=row_idx)).astype(float)

    # Remove duplicates in time series and save in a dataframe
    indexes = np.digitize(np.unique(time), time, right=True)

    df = {}
    df['Elevation'] = find_float_from_str(ws.cell_value(2, 2), ',')
    df['Time'] = time[indexes]
    df['Water Level'] = wlvl[indexes]
    df['Temperature'] = wtemp[indexes]

    return df


# ---- API


class MDDELCC_RSESQ_Reader(AbstractReader):

    DATABASE_FILEPATH = 'mddelcc_rsesq_database.npy'

    def __init__(self):
        super(MDDELCC_RSESQ_Reader, self).__init__()

    def __getitem__(self, key):
        return self._db[key]

    # ---- Utility functions

    def stations(self):
        return self._db.values()

    def station_ids(self):
        return list(self._db.keys())

    # ---- Load and fetch database

    def load_database(self):
        try:
            self._db = np.load(self.DATABASE_FILEPATH).item()
        except FileNotFoundError:
            self.fetch_database()

    def fetch_database(self):
        url = get_xml_url()
        self._db = read_xml_datatable(url)
        np.save(self.DATABASE_FILEPATH, self._db)

    # ---- Fetch data

    def fetch_station_wldata(self, sid):
        url = self._db[sid]['url data']
        if url in [None, '', b'']:
            return
        else:
            self._db[sid].update(get_wldata_from_xls(url))
            np.save(self.DATABASE_FILEPATH, self._db)
            return self._db[sid]

    def dwnld_raw_xls_datafile(self, station_id, filepath):
        # Create the destination directory if it doesn't exist.
        filepath = os.path.abspath(filepath)
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        # Download the xls file.
        station = self._db[station_id]
        if station['url data'] not in [None, '', b'']:
            urlretrieve(station['url data'], filepath)

    # ---- Save to file

    def save_station_to_hdf5(self, station_id, filepath):
        pass

    def save_station_to_csv(self, station_id, filepath):
        station = self._db[station_id]
        if station['url data'] in [None, '', b'']:
            return

        # If the data are not already saved in the local database, fetch it
        # from the mddelcc website.
        if 'Water level' not in list(station.keys()):
            self.fetch_station_wldata(station_id)
            station = self._db[station_id]

        # Generate the file header.
        filecontent = [['Well Name', station['Name']],
                       ['Well ID', station['ID']],
                       ['Latitude', station['Latitude']],
                       ['Longitude', station['Longitude']],
                       ['Elevation', station['Elevation']],
                       ['Nappe', station['Nappe']],
                       ['Influenced', station['Influenced']],
                       [],
                       ['Source', 'http://www.mddelcc.gouv.qc.ca/eau/piezo/'],
                       []]

        filecontent.append(['Time', 'Year', 'Month', 'Day',
                            'Water level (masl)',
                            'Water temperature (degC)'])

        # Append the dataset.
        time = station['Time']
        wlvl = station['Water level']
        wtemp = station['Temperature']
        for i in range(len(wlvl)):
            yy, mm, dd = xlrd.xldate_as_tuple(time[i], 0)[:3]
            filecontent.append([time[i], yy, mm, dd, wlvl[i], wtemp[i]])

        # Create the destination directory if it doesn't exist.
        filepath = os.path.abspath(filepath)
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        # Save the csv.
        with open(filepath, 'w') as f:
            writer = csv.writer(f, delimiter=',', lineterminator='\n')
            writer.writerows(filecontent)


if __name__ == "__main__":
    reader = MDDELCC_RSESQ_Reader()
    reader.save_station_to_csv('01160002', 'test.csv')
    data = reader.fetch_station_wldata('02257001')
