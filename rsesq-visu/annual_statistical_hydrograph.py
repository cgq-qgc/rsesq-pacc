# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 20:24:09 2017

@author: jsgosselin
"""

rbg = [(57, 82, 164), (110, 205, 222), (105, 189, 69), (248, 151, 29),
       (152, 100, 38)]import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms
from readers import MDDELCC_RSESQ_Reader


def compute_monthly_statistics_table(years, months, values, q):
    percentiles = []
    for m in range(1, 13):
        ixs = np.where(months == m)[0]
        percentiles.append(np.percentile(values[ixs], q))
    return np.array(percentiles)

