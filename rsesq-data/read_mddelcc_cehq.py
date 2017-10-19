# -*- coding: utf-8 -*-
"""
Created on Tue Jun 13 14:29:29 2017
@author: jnsebgosselin
"""

# ---- Imports: standard library

import urllib
from urllib.request import urlopen, urlretrieve
from urllib.error import HTTPError, URLError
from io import BytesIO
import numpy as np
import re
import os
import requests
import csv
import datetime

# ---- Imports: third parties

from bs4 import BeautifulSoup
from xlrd.xldate import xldate_from_date_tuple

# ---- Imports: local

from base import AbstractReader


# ---- Utilities

def dms2decdeg(coord):
    """
    Convert decimal, minute, second format lat/lon coordinate to
    decimal degree.
    """
    dd = coord[0] + coord[1]/60 + coord[2]/3600
    return dd


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

def get_data_from_url(tail):
    root = "http://www.cehq.gouv.qc.ca/depot/historique_donnees/"
    try:
        html = urlopen(root+tail).read()
    except (HTTPError, URLError):
        return None

    try:
        data = html.decode('iso-8859-1').split('\r\n')
        return data
    except (UnicodeDecodeError, UnicodeError):
        return None


def scrape_station_ids():
    """Get a list of all station ID on the CEHQ website"""
    url = ("http://www.cehq.gouv.qc.ca/hydrometrie/"
           "historique_donnees/default.asp")

    soup = BeautifulSoup(urlopen(url), 'html.parser')
    select = soup.find("select", attrs={"id": "lstStation"})
    options = select.find_all("option")

    return [row.text.strip() for row in options if row.text.strip()]


def scrape_station_info(sid, data):
    df = {'ID': sid}

    # ---- Scrape name and description

    items = [s.strip() for s in data[2].split("     ") if s][2].split('-')
    df['Name'] = items[0].strip()
    df['Description'] = items[1].strip()

    # ---- Scrape watershed area and flow regime

    items = [s.strip() for s in data[3].split() if s]
    df['Drainage Area'] = float(items[2])
    df['Regime'] = items[-1]

    # ---- Scrape latitude and longitude

    items = [item[:-1] for item in data[4].split()]
    df['Latitude'] = dms2decdeg((int(items[2]), int(items[3]), int(items[4])))
    df['Longitude'] = dms2decdeg((int(items[6]), int(items[7]), int(items[8])))

    # ---- Scrape elevation if available

    items = [s.strip() for s in data[5].split() if s]
    try:
        df['Elevation'] = float(items[2])
    except (IndexError, ValueError):
        df['Elevation'] = ''

    return df


def scrape_daily_series_from_txt(sid, data):
    df = {'Time': [], 'Year': [], 'Month': [], 'Day': [],
          'Daily values': [], 'Note': []}

    if data is None:
        return df
    else:
        for row in data:
            row = [s.strip() for s in row.split()]
            try:
                if row[0] == sid:
                    date = [int(s) for s in row[1].split("/")]
                    df['Time'].append(xldate_from_date_tuple(date, 0))
                    df['Year'].append(date[0])
                    df['Month'].append(date[1])
                    df['Day'].append(date[2])
                    try:
                        df['Daily values'].append(float(row[2]))
                    except IndexError:
                        df['Daily values'].append(np.nan)
                    try:
                        df['Note'].append(row[3])
                    except IndexError:
                        df['Note'].append('')
            except IndexError:
                pass
        return df


def scrape_data_from_sid(sid):
    data_Q = get_data_from_url("fichier/%s_Q.txt" % sid)
    data_N = get_data_from_url("fichier/%s_N.txt" % sid)

    df_dly_hydat = {}
    if data_N:
        df_dly_hydat = scrape_station_info(sid, data_N)
    elif data_Q:
        df_dly_hydat = scrape_station_info(sid, data_Q)
    else:
        return df_dly_hydat

    df_Q = scrape_daily_series_from_txt(sid, data_Q)
    df_N = scrape_daily_series_from_txt(sid, data_N)

    # ---- Combine flow and level datasets

    time = np.hstack([df_Q['Time'], df_N['Time']])
    time = np.unique(time)
    time = np.sort(time)

    df_dly_hydat['Time'] = time
    for field in ['Year', 'Month', 'Day']:
        df_dly_hydat[field] = np.zeros(len(time)).astype(int)
    for field in ['Flow', 'Level']:
        df_dly_hydat[field] = np.zeros(len(time)).astype(float) * np.nan

    indexes = np.digitize(df_Q['Time'], time, right=True)
    for key in ['Year', 'Month', 'Day']:
        df_dly_hydat[key][indexes] = df_Q[key]
    df_dly_hydat['Flow'][indexes] = df_Q['Daily values']

    indexes = np.digitize(df_N['Time'], time, right=True)
    for key in ['Year', 'Month', 'Day']:
        df_dly_hydat[key][indexes] = df_N[key]
    df_dly_hydat['Level'][indexes] = df_N['Daily values']

    # ---- Determine status

    now = datetime.datetime.now()
    if np.max(df_dly_hydat['Year']) == now.year:
        df_dly_hydat['Status'] = 'Open'
    else:
        df_dly_hydat['Status'] = 'Closed'

    return df_dly_hydat


# ---- API

class MDDELCC_CEHQ_Reader(AbstractReader):
    DATABASE_FILEPATH = 'mddelcc_cehq_stations.npy'

    def __init__(self):
        super(MDDELCC_CEHQ_Reader, self).__init__()

    def stations(self):
        return self._db.values()

    def station_ids(self):
        return list(self._db.keys())

    def load_database(self):
        try:
            self._db = np.load(self.DATABASE_FILEPATH).item()
        except FileNotFoundError:
            self.fetch_database_from_mddelcc()

    def fetch_database_from_mddelcc(self):
        sids = scrape_station_ids()
        self._db = {}
        for sid in sids:
            self._db[sid] = {}
        np.save(self.DATABASE_FILEPATH, self._db)

    def fetch_station_data(self, sid):
        self._db[sid] = scrape_data_from_sid(sid)
        np.save(self.DATABASE_FILEPATH, self._db)

        return self._db[sid]

    def save_station_to_hdf5(self):
        pass

    def save_station_to_csv(self, sid, filepath):
        # If the data are not already saved in the local database, fetch it
        # from the mddelcc website.
        if len(self._db[sid]) == 0:
            self.fetch_station_data(sid)
        station = self._db[sid]

        # Generate the file header.
        fc = [['Station ID', station['ID']],
              ['Station Name', station['Name']],
              ['Description', station['Description']],
              ['Status', station['Status']],
              ['Province', 'Qc'],
              ['Latitude (dd)', station['Latitude']],
              ['Longitude (dd)', station['Longitude']],
              ['Elevation (m)', station['Elevation']],
              ['Drainage Area (km2)', station['Drainage Area']],
              ['Regime', station['Regime']],
              [],
              ['Source', 'https://www.cehq.gouv.qc.ca'],
              [],
              ['Time', 'Year', 'Month', 'Day', 'Level (m)', 'Flow (m3/s)']]

        # Append the dataset.
        data = np.vstack([station['Time'], station['Year'], station['Month'],
                          station['Day'], station['Level'], station['Flow']]
                         ).transpose().tolist()
        fc.extend(data)

        # Create the destination directory if it doesn't exist.
        filepath = os.path.abspath(filepath)
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        # Save the csv.
        with open(filepath, 'w', encoding='iso-8859-1') as f:
            writer = csv.writer(f, delimiter=',', lineterminator='\n')
            writer.writerows(fc)


if __name__ == "__main__":
    reader = MDDELCC_CEHQ_Reader()
    reader.save_station_to_csv('030920', 'test_hyd.csv')
    
    
    # df_dly_hydat = scrape_data_from_sid(sids[0])
    # df_dly_hydat2 = scrape_data_from_sid('011508')
