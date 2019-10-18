# -*- coding: utf-8 -*-
"""
Created on Tue Oct 17 10:38:02 2017
@author: jsgosselin
"""

# ---- Imports: standard library
from abc import ABC, abstractmethod
import os.path as osp


class AbstractReader(ABC):

    DATABASE_FILEPATH = None

    def __init__(self, workdir=None):
        super().__init__()
        if isinstance(workdir, str) and osp.exists(workdir):
            self.DATABASE_FILEPATH = osp.join(workdir, self.DATABASE_FILEPATH)
        self.load_database()

    # ---- Load and fetch database

    @abstractmethod
    def load_database(self):
        pass

    @abstractmethod
    def fetch_database(self):
        pass

    @abstractmethod
    def set_local_database_dir(dirname):
        pass

    # ---- Utility functions

    @abstractmethod
    def stations(self):
        pass

    @abstractmethod
    def station_ids(self):
        pass

    # ---- Save to file

    @abstractmethod
    def save_station_to_hdf5(self, station_id, filepath):
        pass

    @abstractmethod
    def save_station_to_csv(self, station_id, filepath):
        pass
