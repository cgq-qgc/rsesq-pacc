# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 08:59:57 2017
@author: jsgosselin
"""

import numpy as np
import matplotlib.pyplot as plt
from readers import MDDELCC_RSESQ_Reader


# ---- Produce the bins

def compute_nbr_stn_bins(bstep):
    reader = MDDELCC_RSESQ_Reader()
    bins = {}
    for stn in reader.stations():
        if 'Year' not in list(stn.keys()):
            continue

        dec = np.unique(stn['Year']//bstep)*bstep
        for d in dec.astype(str):
            if d not in list(bins.keys()):
                bins[d] = 0
            else:
                bins[d] = bins[d] + 1

    years = np.array(list(bins.keys())).astype(int)
    values = np.array(list(bins.values())).astype(int)

    indexes = np.argsort(years)
    years = years[indexes]
    values = values[indexes]

    years = np.append(years, years[-1]+bstep)

    return years, values

