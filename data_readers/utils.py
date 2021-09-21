# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 09:22:27 2017
@author: jsgosselin
"""

# ---- Standard library imports
import urllib
import re
import numpy as np
import csv


def dms2decdeg(coord):
    """
    Convert decimal, minute, second format lat/lon coordinate to
    decimal degree.
    """
    sign = np.sign(coord[0])
    dd = abs(coord[0]) + coord[1]/60 + coord[2]/3600
    return sign*dd


def find_unique(pattern, string):
    """
    Return the first result found for the regex search or return None if
    nothing is found.
    """
    result = re.findall(pattern, string)
    if len(result) > 0:
        return result[0].strip()
    else:
        return None


def find_all(regex, string):
    """
    Return the stripped results found in string using the provided regex.
    """
    return [s.strip() for s in re.findall(regex, string)]


def find_float_from_str(string):
    """
    Search a string to find the first float number if any.
    """
    string = string.replace(',', '.')
    float_ = ''
    digit_sep_found = False
    for char in string:
        if char.isdigit():
            float_ += char
        elif char == '.' and not digit_sep_found:
            digit_sep_found = True
            float_ += char

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


def save_content_to_csv(fname, fcontent, mode='w', delimiter=',',
                        encoding='utf8'):
    """
    Save content in a csv file with the specifications provided
    in arguments.
    """
    with open(fname, mode, encoding='utf8') as csvfile:
        writer = csv.writer(csvfile, delimiter=delimiter, lineterminator='\n')
        writer.writerows(fcontent)
