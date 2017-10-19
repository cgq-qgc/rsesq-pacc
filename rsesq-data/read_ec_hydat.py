# -*- coding: utf-8 -*-
"""
Created on Tue Jun 13 14:29:29 2017
@author: jnsebgosselin
"""

# ---- Imports: standard library

import sqlite3
import os
import csv

# ---- Imports: third parties

import pandas as pd
import numpy as np
from xlrd.xldate import xldate_from_date_tuple

# ---- Imports: local

from base import AbstractReader


# ---- API


class HYDAT_Reader(AbstractReader):

    DATABASE_FILEPATH = 'Hydat.sqlite3'

    def load_database(self):
        if not os.path.exists(self.DATABASE_FILEPATH):
            raise FileNotFoundError

        self._con = sqlite3.connect(self.DATABASE_FILEPATH)
        self._db = pd.read_sql_query("select * from STATIONS;", self._con)

    def get_version(self):
        cur = self._con.execute("select * from Version;")
        results = cur.fetchall()[0]

        print("Version de la BD: ", results[0])
        print("Date de la préparation de la BD: ", results[1])

        return results

    def stations(self):
        return self._db['STATION_NAME'].as_matrix().flatten()

    def station_ids(self):
        return self._db['STATION_NUMBER'].as_matrix().flatten()

    def get_station_ids(self, hydstatus=None, province=None):
        params = []
        req = "select STATION_NUMBER from STATIONS"
        keyword = "WHERE"
        if hydstatus:
            params.append(hydstatus)
            req += " %s HYD_STATUS = ?" % keyword
            keyword = "AND"
        if province:
            params.append(province)
            req += " %s PROV_TERR_STATE_LOC = ?" % keyword

        cur = self._con.execute(req, params)
        results = cur.fetchall()

        return [i[0] for i in results]

    def _get_from_sid(self, sid, param):
        req = "select %s from STATIONS WHERE STATION_NUMBER = ?;" % param
        cur = self._con.execute(req, [sid])
        return cur.fetchall()[0][0]

    def get_hydstatus_from_sid(self, sid):
        """Return whether the station is still active or not."""
        return self._get_from_sid(sid, 'HYD_STATUS') == 'A'

    def get_name_from_sid(self, sid):
        """Return the name of the station."""
        return self._get_from_sid(sid, 'STATION_NAME')

    def get_prov_from_sid(self, sid):
        """Return the Canadian province where the station is located."""
        return self._get_from_sid(sid, 'PROV_TERR_STATE_LOC')

    def get_xy_from_sid(self, sid):
        """
        Return the North-South (latitude) and East-West (longitude) coordinates
        of the gauging station in decimal degrees.
        """
        return (self._get_from_sid(sid, 'LATITUDE'),
                self._get_from_sid(sid, 'LONGITUDE'))

    def get_drainage_area_gross(self, sid):
        """The total surface area that drains to the gauge site (km^2)"""
        return self._get_from_sid(sid, 'DRAINAGE_AREA_GROSS')

    def get_drainage_area_effect(self, sid):
        """
        Return the portion of the drainage basin that contributes runoff to
        the gauge site, calculated by subtracting any noncontributing
        portion from the gross drainage area (km^2).
        """
        return self._get_from_sid(sid, 'DRAINAGE_AREA_EFFECT')

    def get_dly_flow(self, sid):
        """"Return a time series with daily flow values in m^3/s"""
        req = ("select * from DLY_FLOWS WHERE STATION_NUMBER = ?"
               " AND YEAR > 1930")
        df = pd.read_sql_query(req, self._con, params=[sid])
        return self._dly_series_tolist(df, 'FLOW')

    def get_dly_level(self, sid):
        """"Return a time series with water level values in m"""
        req = ("select * from DLY_LEVELS WHERE STATION_NUMBER = ?"
               " AND YEAR > 1930")
        df = pd.read_sql_query(req, self._con, params=[sid])
        return self._dly_series_tolist(df, 'LEVEL')

    def get_dly_hydat_from_id(self, sid):
        df_dly_hydat = {}

        # ---- Fetch station info

        df_dly_hydat['ID'] = sid
        df_dly_hydat['Name'] = self.get_name_from_sid(sid)
        df_dly_hydat['Province'] = self.get_prov_from_sid(sid)
        df_dly_hydat['Latitude'], df_dly_hydat['Longitude'] = \
            self.get_xy_from_sid(sid)
        df_dly_hydat['Drainage Area Gross'] = self.get_drainage_area_gross(sid)
        df_dly_hydat['Drainage Area Effect'] = \
            self.get_drainage_area_effect(sid)

        # ---- Fetch and format daily data

        # Fetch the daily flow and level data from the database and format
        # the data in an array.

        df_dly_flows = self.get_dly_flow(sid)
        df_dly_levels = self.get_dly_level(sid)

        # ---- Combine flow and level datasets

        time = np.hstack([df_dly_flows['Time'], df_dly_levels['Time']])
        time = np.unique(time)
        time = np.sort(time)

        df_dly_hydat['Time'] = time
        for field in ['Year', 'Month', 'Day']:
            df_dly_hydat[field] = np.zeros(len(time)).astype(int)
        for field in ['Flow', 'Level']:
            df_dly_hydat[field] = np.zeros(len(time)).astype(float) * np.nan

        if len(df_dly_flows) > 0:
            indexes = np.digitize(df_dly_flows['Time'], time, right=True)
            for key in ['Year', 'Month', 'Day', 'Flow']:
                df_dly_hydat[key][indexes] = df_dly_flows[key]
        if len(df_dly_levels) > 0:
            indexes = np.digitize(df_dly_levels['Time'], time, right=True)
            for key in ['Year', 'Month', 'Day', 'Level']:
                df_dly_hydat[key][indexes] = df_dly_levels[key]

        return df_dly_hydat

    def _dly_series_tolist(self, df_dly, dtype):
        columns = df_dly.columns.values.tolist()
        data = {'Time': [], 'Year': [], 'Month': [], 'Day': [],
                dtype.title(): []}
        for row in df_dly.itertuples(index=False):
            year = row.YEAR
            mth = row.MONTH
            day = 0
            while day < row.NO_DAYS:
                try:
                    index = columns.index(dtype+str(day))
                except ValueError:
                    pass
                else:
                    time = xldate_from_date_tuple((year, mth, day), 0)
                    data['Time'].append(time)
                    data['Year'].append(year)
                    data['Month'].append(mth)
                    data['Day'].append(day)
                    data[dtype.title()].append(row[index])
                finally:
                    day += 1
        return data

    def save_station_to_hdf5(self, station_id, filepath):
        return

    def save_station_to_csv(self, sid, filepath):
        station = self.get_dly_hydat_from_id(sid)

        # Generate the file header.
        fc = [['Station Name', station['Name']],
              ['Station ID', station['ID']],
              ['Province', station['Province']],
              ['Latitude (dd)', station['Latitude']],
              ['Longitude (dd)', station['Longitude']],
              ['Drainage Area Gross (km2)', station['Drainage Area Gross']],
              ['Drainage Area Effect (km2)', station['Drainage Area Effect']],
              [],
              ['Source', 'https://ec.gc.ca/rhc-wsc'],
              [],
              ['Time', 'Year', 'Month', 'Day',
               'Water level (m)', 'Flow (m3/s)']]

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
        with open(filepath, 'w') as f:
            writer = csv.writer(f, delimiter=',', lineterminator='\n')
            writer.writerows(fc)


if __name__ == "__main__":
    reader = HYDAT_Reader()
    for sid in reader.get_station_ids(hydstatus='A', province='ON'):
        reader.get_hydstatus_from_sid(sid)
        reader.get_prov_from_sid(sid)
        df_dly_hydat = reader.get_dly_hydat_from_id(sid)
        print(np.min(df_dly_hydat['Year']), np.max(df_dly_hydat['Year']))
        # reader.save_station_to_csv(sid, 'test_hydat.csv')
