# -*- coding: utf-8 -*-
"""
Created on Wed Mar 27 14:29:45 2019
@author: User
"""
from urllib.request import urlopen, urlretrieve
import os.path as osp

NAAR_FTP = "ftp://ftp.cdc.noaa.gov/Datasets/NARR/monolevel/"
DIRNAME = "D:/Data_NARR"

filenames = ["pres.sfc.{}.nc".format(y) for y in range(1979, 2020)]

for filename in filenames:
    print("Downloading {}...".format(filename), end='')
    urlretrieve(osp.join(NAAR_FTP, filename), osp.join(DIRNAME, filename))
    print(" done".format(filename))
