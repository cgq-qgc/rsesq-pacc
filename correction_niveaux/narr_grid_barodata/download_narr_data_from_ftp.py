# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Institut National de la Recherche Scientifique (INRS)
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

"""
A script to download in batch the atmospheric pressure data
of the North American Regional Reanalysis (NARR) grid.

https://psl.noaa.gov/data/gridded/data.narr.html
"""

# ---- Standard library imports
from urllib.request import urlretrieve
import os
import os.path as osp

narr_ftp = "ftp://ftp.cdc.noaa.gov/Datasets/NARR/monolevel/"

dirname = osp.join(osp.dirname(__file__), 'baro_naar_netcdf')
if not osp.exists(dirname):
    os.makedirs(dirname)

years = range(1979, 2020)
for year in years:
    filename = "pres.sfc.{}.nc".format(year)
    print("Downloading {}...".format(filename), end='')
    urlretrieve(osp.join(narr_ftp, filename), osp.join(dirname, filename))
    print(" done")
