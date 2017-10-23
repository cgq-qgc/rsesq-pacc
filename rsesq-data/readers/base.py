# -*- coding: utf-8 -*-
"""
Created on Tue Oct 17 10:38:02 2017
@author: jsgosselin
"""

# ---- Imports: standard library

from abc import ABC, abstractmethod


class AbstractReader(ABC):

    DATABASE_FILEPATH = None

    def __init__(self):
        super().__init__()
        self.load_database()

    @abstractmethod
    def load_database(self):
        pass

    @abstractmethod
    def stations(self):
        pass

    @abstractmethod
    def station_ids(self):
        pass

    @abstractmethod
    def save_station_to_hdf5(self, station_id, filepath):
        pass

    @abstractmethod
    def save_station_to_csv(self, station_id, filepath):
        pass
