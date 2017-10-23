# -*- coding: utf-8 -*-
"""
Created on Tue Jun 13 14:29:29 2017
@author: jnsebgosselin
"""

# ---- Imports: standard library

from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import numpy as np
import os
import csv
from multiprocessing import Pool

# ---- Imports: third parties

from bs4 import BeautifulSoup
from xlrd.xldate import xldate_from_date_tuple

# ---- Imports: local

from readers.base import AbstractReader
from readers.utils import findUnique, dms2decdeg


# ---- Base functions


def read_html_from_url(url):
    """"Get, read and decode html data from a url in the the CEHQ domain."""
    try:
        html = urlopen(url).read()
    except (HTTPError, URLError):
        return None

    try:
        data = html.decode('iso-8859-1').split('\r\n')
        return data
    except (UnicodeDecodeError, UnicodeError):
        return None


def scrape_station_ids():
    """
    Get a list of the IDs of all the stations for which data are available
    on the CEHQ website
    """
    url = ("http://www.cehq.gouv.qc.ca/hydrometrie/"
           "historique_donnees/default.asp")

    soup = BeautifulSoup(urlopen(url), 'html.parser')
    select = soup.find("select", attrs={"id": "lstStation"})
    options = select.find_all("option")

    return [row.text.strip() for row in options if row.text.strip()]


def scrape_station_datasheet(sid):
    """
    Read the information in the station datasheet.
    """
    url = "http://www.cehq.gouv.qc.ca/hydrometrie/historique_donnees/"
    url += "fiche_station.asp?NoStation=%s" % sid
    html = urlopen(url).read().decode('iso-8859-1')

    FIELDS_KEYS = [('Numéro de la station :', 'ID'),
                   ('Nom de la station :', 'Name'),
                   ('Description :', 'Description'),
                   ('État :', 'Status'),
                   ("Période(s) d'activité :", 'Active period'),
                   ("Municipalité :", 'Municipality'),
                   ('Région administrative :', 'Administrative Region'),
                   ("Lac ou cours d'eau :", 'Stream Name'),
                   ("Région hydrographique", 'Hydrographic Region'),
                   ("Bassin versant à la station", 'Drainage Area'),
                   ("Régime d'écoulement", 'Flow Regime'),
                   ("Numéro fédéral de la station :", "Federal ID")]

    # BeautifulSoup is not working correctly for this content due to the mixed
    # up of <a> and <b> fields in the table. So we use a basic crawling of the
    # content using regexes instead.

    data = {'ID': sid}
    for field, key in FIELDS_KEYS:
        idx = html.find(field)
        data[key] = findUnique('<td width="421">(.*?)&nbsp;</td>', html[idx:])

    data['Active period'] = data['Active period'].replace('<br>', ' ; ')

    data['Drainage Area'] = data['Drainage Area'].replace(',', '.')
    data['Drainage Area'] = data['Drainage Area'].replace(' km²', '')
    data['Drainage Area'] = data['Drainage Area'].replace('\xa0', '')
    try:
        data['Drainage Area'] = float(data['Drainage Area'])
    except ValueError:
        data['Drainage Area'] = 'Non disponible'

    return data


def scrape_station_data_header(data):
    """
    Get latitude, longitude, and elevation (if available) from the header of
    the datafile.
    """
    df = {}

    # ---- Scrape latitude and longitude

    items = [item[:-1] for item in data[4].split()]
    df['Latitude'] = dms2decdeg((int(items[2]), int(items[3]), int(items[4])))
    df['Longitude'] = dms2decdeg((int(items[6]), int(items[7]), int(items[8])))

    # ---- Scrape elevation if available

    items = [s.strip() for s in data[5].split() if s]
    try:
        df['Elevation'] = float(items[2])
    except (IndexError, ValueError):
        df['Elevation'] = 'Non disponible'

    return df


def scrape_daily_series_from_txt(sid, data):
    """
    Structured the daily streamflow and level that were downloaded on the CEHQ
    website into structured arrays and store them in a dataframe.
    """
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
    """
    This is a meta function that will read and restructured station info and
    daily streamflow and level data for the station with the specified id.
    """
    df_dly_hydat = {'ID': sid}

    root = "http://www.cehq.gouv.qc.ca/depot/historique_donnees/"
    data_Q = read_html_from_url(root+"fichier/%s_Q.txt" % sid)
    data_N = read_html_from_url(root+"fichier/%s_N.txt" % sid)

    if data_N:
        df_dly_hydat.update(scrape_station_data_header(data_N))
    elif data_Q:
        df_dly_hydat.update(scrape_station_data_header(data_Q))
    else:
        return {}

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
        """
        Clear the local database and fetch the datasheets for all available
        station on the CEHQ website. The daily streamflow and level data are
        not downloaded during this operation.
        """
        sids = scrape_station_ids()
        self._db = {}
        p = Pool(5)
        itr = 0
        print("Fetching station datasheets from the CEHQ website...")
        for result in p.imap(scrape_station_datasheet, sids):
            itr += 1
            self._db[result['ID']] = result
            print("\r", "%d of %d" % (itr, len(sids)), end="")
        print("\nDatasheet fetched for all stations.")
        p.close()
        p.join()
        np.save(self.DATABASE_FILEPATH, self._db)

    def fetch_station_dlydata(self, sid):
        """
        Download the daily streamflow and level for the station corresponding
        to the provided id and save the results in the local database.
        """
        self._db[sid].update(scrape_data_from_sid(sid))
        np.save(self.DATABASE_FILEPATH, self._db)
        return self._db[sid]

    # def fetch_all_station_dlydata(self, sid):

    def save_station_to_hdf5(self):
        pass

    def save_station_to_csv(self, sid, filepath):
        """
        Save data from local database to csv. If the data are not already
        saved in the local database, it is fetched from the mddelcc website.
        """
        if 'Level' not in list(self._db[sid].keys()):
            self.fetch_station_dlydata(sid)
        station = self._db[sid]

        # Generate the file header.
        fc = [['Station ID', station['ID']],
              ['Station Name', station['Name']],
              ['Description', station['Description']],
              ['Status', station['Status']],
              ['Active period', station['Active period']],
              ['Province', 'Qc'],
              ['Municipality', station['Municipality']],
              ['Administrative Region', station['Administrative Region']],
              ['Stream Name', station['Stream Name']],
              ['Hydrographic Region', station['Hydrographic Region']],
              ['Latitude (dd)', station['Latitude']],
              ['Longitude (dd)', station['Longitude']],
              ['Elevation (m)', station['Elevation']],
              ['Drainage Area (km2)', station['Drainage Area']],
              ['Flow Regime', station['Flow Regime']],
              [],
              ['Source', 'https://www.cehq.gouv.qc.ca'],
              ['Federal ID', station["Federal ID"]],
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
    # reader.fetch_database_from_mddelcc()
    reader.save_station_to_csv('022704', 'test.csv')
