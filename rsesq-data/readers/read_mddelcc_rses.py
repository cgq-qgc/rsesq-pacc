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
import os.path as osp
import requests
import datetime

# ---- Imports: third parties
from bs4 import BeautifulSoup, CData
import xlrd
import pandas as pd

# ---- Imports: local
from readers.base import AbstractReader
from readers.utils import (findUnique, find_float_from_str,
                           format_url_to_ascii, save_content_to_csv)


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
    df['Elevation'] = find_float_from_str(ws.cell_value(2, 2))
    df['Time'] = time[indexes]
    df['Water Level'] = wlvl[indexes]
    df['Temperature'] = wtemp[indexes]

    # Produce year, month and data time series.
    df['Year'] = np.zeros(np.shape(df['Time'])).astype(int)
    df['Month'] = np.zeros(np.shape(df['Time'])).astype(int)
    df['Day'] = np.zeros(np.shape(df['Time'])).astype(int)
    for i, t in enumerate(df['Time']):
        date = xlrd.xldate_as_tuple(t, 0)[:3]
        df['Year'][i], df['Month'][i], df['Day'][i] = date

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
        return list(self._db.values())

    def station_ids(self):
        return list(self._db.keys())

    def get_station_data(self, stn_id):
        """
        Return a pandas dataframe with the temperature and water level time
        series corresponding to the specified station indexed by date.
        """
        data = self[stn_id]
        df = pd.DataFrame(
            np.vstack((data['Water Level'], data['Temperature'])).T,
            [datetime.datetime(*xlrd.xldate_as_tuple(t, 0)) for
             t in data['Time']],
            columns=['Water Level (masl)', 'Temperature (degC)']
            )
        return df

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

    def save_station_to_csv(self, sid, filepath):
        if self._db[sid]['url data'] in [None, '', b'']:
            return

        # If the data are not already saved in the local database, fetch it
        # from the mddelcc website.
        if 'Water Level' not in list(self._db[sid].keys()):
            self.fetch_station_wldata(sid)

        stn = self._db[sid]
        # Generate the file header.
        fc = [['Well Name', stn['Name']],
              ['Well ID', stn['ID']],
              ['Latitude', stn['Latitude']],
              ['Longitude', stn['Longitude']],
              ['Elevation', stn['Elevation']],
              ['Nappe', stn['Nappe']],
              ['Influenced', stn['Influenced']],
              [],
              ['Source', 'http://www.mddelcc.gouv.qc.ca/eau/piezo/'],
              [],
              ['Time', 'Year', 'Month', 'Day', 'Water level (masl)',
               'Water temperature (degC)']]

        # Append the dataset.
        data = np.vstack([stn['Time'].astype(str), stn['Year'].astype(str),
                          stn['Month'].astype(str), stn['Day'].astype(str),
                          stn['Water Level'].astype(str),
                          stn['Temperature'].astype(str)]
                         ).transpose().tolist()
        fc.extend(data)

        # Create the destination directory if it doesn't exist.
        filepath = os.path.abspath(filepath)
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        # Save the csv.
        save_content_to_csv(filepath, fc)

    def save_station_table_to_csv(self, filepath):
        """
        Save the information for all the wells of the RSESQ in a csv file.
        """
        fcontent = [['#', 'Well_ID', 'Well_Name', 'Latitude_ddeg',
                     'Longitude_ddeg', 'Elevation', 'Nappe', 'Influenced']]
        for i, stn_id in enumerate(sorted(self.station_ids())):
            try:
                self._db[stn_id]['Elevation']
            except KeyError:
                # We need to download the data to get the station
                # elevation because this info is not in the kml file.
                self.fetch_station_wldata(stn_id)

            fcontent.append([
                str(i), stn_id, self._db[stn_id]['Name'],
                self._db[stn_id]['Latitude'], self._db[stn_id]['Longitude'],
                self._db[stn_id]['Elevation'], self._db[stn_id]['Nappe'],
                self._db[stn_id]['Influenced']])

        # Create the destination directory if it doesn't exist.
        filepath = osp.abspath(filepath)
        if not osp.exists(osp.dirname(filepath)):
            os.makedirs(osp.dirname(filepath))

        # Save the csv.
        save_content_to_csv(filepath, fcontent)


if __name__ == "__main__":
    reader = MDDELCC_RSESQ_Reader()
    # reader.save_station_to_csv('01160002', 'test.csv')

    data = reader.fetch_station_wldata('02257001')
    reader.save_station_to_csv('02257001', 'stantonin_doublon.csv')
