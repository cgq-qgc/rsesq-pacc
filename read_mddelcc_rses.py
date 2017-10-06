# -*- coding: utf-8 -*-
"""
Created on Tue Jun 13 14:29:29 2017
@author: jnsebgosselin
"""

# ---- Imports: standard library

import urllib
from urllib.request import urlopen, urlretrieve
from io import BytesIO
import numpy as np
import re
import os
import requests
import csv

# ---- Imports: third parties

from bs4 import BeautifulSoup, CData
import xlrd


# ---- Utilities


def findUnique(pattern, string):
    """
    Return the first result found for the regex search or return None if
    nothing is found.
    """
    result = re.findall(pattern, string)
    if len(result) > 0:
        return result[0].strip()
    else:
        return None


def find_float_from_str(string, sep):
    """
    Search a string to find a float number if any.
    """
    float_ = ''
    digit_sep_found = False
    for char in string:
        if char.isdigit():
            float_ += char
        else:
            if char == sep and not digit_sep_found:
                digit_sep_found = True
                float_ += '.'
    return float(float_)


def format_url_to_ascii(url):
    """
    Convert non_ASCII char in the url if any.
    """
    url = urllib.parse.urlsplit(url)
    url = list(url)
    url[2] = urllib.parse.quote(url[2])
    url = urllib.parse.urlunsplit(url)
    return url


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

        elevation = find_float_from_str(ws.cell_value(2, 2), ',')

        return (elevation, time, wlvl, wtemp)


# ---- API


class MDDELCC_RSESQ_Reader(object):

    RSESQ_DB_FILE = 'mddelcc_rsesq_stations.npy'

    def __init__(self):
        self.load_database()

    def __getitem__(self, key):
        return self._db[key]

    def stations(self):
        return self._db.values()

    def station_ids(self):
        return list(self._db.keys())

    def load_database(self):
        try:
            self._db = np.load(self.RSESQ_DB_FILE).item()
        except FileNotFoundError:
            self.fetch_database_from_mddelcc()

    def fetch_database_from_mddelcc(self):
        url = get_xml_url()
        self._db = read_xml_datatable(url)
        np.save(self.RSESQ_DB_FILE, self._db)

    def fetch_station_wldata(self, station_id):
        station = self._db[station_id]
        if station['url data'] in [None, '', b'']:
            return

        elevation, time, wlvl, wtemp = get_wldata_from_xls(station['url data'])
        station['Elevation'] = elevation
        station['Time'] = time
        station['Water level'] = wlvl
        station['Temperature'] = wtemp

        np.save(self.RSESQ_DB_FILE, self._db)

    def dwnld_raw_xls_datafile(self, station_id, filepath):
        station = self._db[station_id]
        if station['url data'] not in [None, '', b'']:
            urlretrieve(station['url data'], filepath)

    def save_station_to_csv(self, station_id, filepath):
        station = self._db[station_id]
        if station['url data'] in [None, '', b'']:
            return

        if 'Water level' not in list(station.keys()):
            self.fetch_station_wldata(station_id)

        filecontent = [['Well Name', station['Name']],
                       ['Well ID', station['ID']],
                       ['Latitude', station['Latitude']],
                       ['Longitude', station['Longitude']],
                       ['Elevation', station['Elevation']],
                       ['Nappe', station['Nappe']],
                       ['Influenced', station['Influenced']],
                       []]

        filecontent.append(['Time', 'Year', 'Month', 'Day',
                            'Water level (masl)',
                            'Water temperature (degC)'])

        time = station['Time']
        wlvl = station['Water level']
        wtemp = station['Temperature']
        for i in range(len(wlvl)):
            yy, mm, dd = xlrd.xldate_as_tuple(time[i], 0)[:3]
            filecontent.append([time[i], yy, mm, dd, wlvl[i], wtemp[i]])

        with open(filepath, 'w') as f:
            writer = csv.writer(f, delimiter=',', lineterminator='\n')
            writer.writerows(filecontent)


if __name__ == "__main__":
    reader = MDDELCC_RSESQ_Reader()
    reader.save_station_to_csv('01160002', 'test.csv')
