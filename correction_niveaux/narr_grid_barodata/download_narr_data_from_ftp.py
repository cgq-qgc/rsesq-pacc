# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Institut National de la Recherche Scientifique (INRS)
# https://github.com/cgq-qgc/pacc-inrs
#
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
from urllib.request import urlretrieve
import os.path as osp

NAAR_FTP = "ftp://ftp.cdc.noaa.gov/Datasets/NARR/monolevel/"
DIRNAME = osp.join(osp.dirname(__file__), "baro_naar_netcdf")

filenames = ["pres.sfc.{}.nc".format(y) for y in range(1979, 2020)]
for filename in filenames:
    print("Downloading {}...".format(filename), end='')
    urlretrieve(osp.join(NAAR_FTP, filename), osp.join(DIRNAME, filename))
    print(" done")
