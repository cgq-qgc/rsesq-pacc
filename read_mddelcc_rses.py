# -*- coding: utf-8 -*-
"""
Created on Tue Jun 13 14:29:29 2017
@author: jnsebgosselin
"""

# ---- Imports: standard library

import urllib
from urllib.request import urlopen, urlretrieve
from bs4 import BeautifulSoup, CData
import re
import os

# ---- Utilities


def findUnique(pattern, string):
    """
    Return the first result found for the regex search or return None if
    nothing is found.
    """
    result = re.findall(pattern, string)
    if len(result) > 0:
        return result[0].strip()
    else:
        return None


# ---- Handlers


def get_xml_url():
    """
    Get the url of the last xml data table.
    """
    mpjs = ('http://www.mddelcc.gouv.qc.ca/eau/piezo/' +
            'carte_google/markers-piezo.js')

    f = urlopen(mpjs)
    reader = f.read().decode('utf-8', 'replace')

    txt = "MYMAP.placePuits('"
    n = len("MYMAP.placePuits('")
    indx0 = reader.find(txt) + n
    indx1 = reader.find("');", indx0)

    url = 'http://www.mddelcc.gouv.qc.ca/eau/piezo/%s' % reader[indx0:indx1]

    return url


def read_xml_datatable(url=None):
    """
    Read the xml datafile and return a database with the well info
    """
    url = get_xml_url() if url is None else url
    xml = urlopen(url)
    soup = BeautifulSoup(xml, 'html.parser')
    places = soup.find_all('placemark')

    db = {}
    for place in places:
        desc = place.find('description')
        name = place.find('name').text
        for cd in desc.findAll(text=True):
            if isinstance(cd, CData):
                pid = findUnique('Piézomètre =(.*?)<br/>', cd)
                db[pid] = {}
                db[pid]['ID'] = pid
                db[pid]['Name'] = name
                db[pid]['Longitude'] = findUnique('Longitude =(.*?)<br/>', cd)
                db[pid]['Latitude'] = findUnique('Latitude =(.*?)<br/>', cd)
                db[pid]['Nappe'] = findUnique('Nappe =(.*?)<br/>', cd)
                db[pid]['Influenced'] = findUnique('Influencé =(.*?)<br/>', cd)
                db[pid]['Last'] = findUnique(
                        'Dernière lecture =(.*?)<br/>', cd)

                s = '<br/><a href="(.*?)">Données'
                db[pid]['url data'] = findUnique(s, cd)
                s = 'Données</a><br/><a href="(.*?)">Schéma'
                db[pid]['url drilllog'] = findUnique(s, cd)
                s = 'Schéma</a><br/><a href="(.*?)">Graphique'
                db[pid]['url graph'] = findUnique(s, cd)

    return db


def get_file_from_url(url, filepath):
    # Convert non_ASCII char in the url if any.
    url = urllib.parse.urlsplit(url)
    url = list(url)
    url[2] = urllib.parse.quote(url[2])
    url = urllib.parse.urlunsplit(url)

    urlretrieve(url, filepath)


if __name__ == "__main__":
    db = read_xml_datatable()

    filepath = os.path.join(os.getcwd(), 'abc.xls')
    get_file_from_url(db['09000009']['url data'], filepath)
