# -*- coding: utf-8 -*-
# dataset = hsr.SolinstFileReader(file_path)
# print(dataset.header_content)
# dataset.plot()

# file_name = "2009772_Bromont_PO-02-B_2017_11_22.xle"
# file_location = os.path.join(file_loc, file_name)
# print(file_location)

import hydsensread as hsr
import matplotlib.pyplot as plt
import numpy as np
import os.path as osp
import os
import re
from readers import MDDELCC_RSESQ_Reader
from pyhelp.utils import calc_dist_from_coord, save_content_to_csv
import rasterio
import csv
import pandas as pd
from datetime import datetime, timedelta
from xlrd.xldate import xldate_from_datetime_tuple
from datetime import datetime
import xlsxwriter

import numpy as np
import matplotlib.pyplot as plt
import scipy.fftpack

import pygtide
import datetime as dt
import pytz


def calcul_center_latlon(lat, lon):
    """
    Calcul the centroid for a list of lat/lon coordinates.
    """
    # Based on https://gist.github.com/amites/3718961
    lat, lon = np.radians(lat), np.radians(lon)

    x = np.mean(np.cos(lat) * np.cos(lon))
    y = np.mean(np.cos(lat) * np.sin(lon))
    z = np.mean(np.sin(lat))

    lon_ctr = np.arctan2(y, x)
    hyp = (x**2 + y**2)**0.5
    lat_ctr = np.arctan2(z, hyp)

    return np.degrees(lat_ctr), np.degrees(lon_ctr)


def read_tsoft_expchan(filename, tstart, tdelta):
    """Read the datafiles produced with TSoft."""
    with open(filename) as csvfile:
        reader = list(csv.reader(csvfile, delimiter=' '))
    data = np.zeros(len(reader))
    for i, line in enumerate(reader):
        data[i] = [float(d) for d in line if d][1]

    dt0 = datetime.strptime(tstart, '%Y-%m-%d %H:%M:%S')
    dtarr = [dt0 + timedelta(minutes=(i * 15)) for i in range(len(data))]

    return pd.DataFrame(data, dtarr, columns=['earth_tides(nm/s2)'])


def generate_earth_tides(latitude, longitude, elevation):
    """
    Generate Earth tide synthetic data for the give latitude, longitude and
    elevation.
    """
    # Define the UTC time delta
    utc_tz = pytz.timezone('UTC')
    utc_dt = pytz.timezone('UTC').localize(dt.datetime(2017, 1, 1))
    local_tz = pytz.timezone('US/Eastern')
    local_dt = local_tz.localize(dt.datetime(2017, 1, 1))
    tz_delta = local_dt - utc_dt
    
    pt = pygtide.pygtide()
    start = dt.datetime(2017, 1, 1)
    duration = 365 * 24
    samplerate = 15 * 60
    pt.predict(latitude, longitude, elevation, start, duration, samplerate)

    # retrieve the results as dataframe
    data = pt.results()
    etdata = data[['UTC', 'Signal [nm/s**2]']]
    etdata.loc[:, 'UTC'] = etdata.loc[:, 'UTC'] - tz_delta
    etdata.rename(columns={'UTC': 'Index'}, inplace=True)
    etdata.set_index(['Index'], drop=True, inplace=True)
    etdata = etdata.tz_localize(None)
    
    return etdata

def save_to_gwhat(filename, leveldata, barodata, etdata, header):
    """
    Save the level, baro and earth tide data to a csv file in the GWHAT
    format.
    """
    # Compensate the level data.
    leveldata = leveldata - barodata

    # Transform the level data in mbgs.
    leveldata = np.max(leveldata) - leveldata

    # Join the data.
    brfdata = pd.merge(
        leveldata, barodata,
        left_index=True, right_index=True, how='inner')
    brfdata = pd.merge(
        brfdata, etdata, left_index=True, right_index=True, how='inner')

    # Convert time to Excel numeric format.
    datetimes = brfdata.index.to_pydatetime()
    xlrdates = [xldate_from_datetime_tuple(dt.timetuple()[:6], datemode=0) for
                dt in datetimes]

    # Save data to files.
    data = [[xlrdates[i]] + brfdata.iloc[i].tolist() for
            i in range(len(xlrdates))]
    save_content_to_csv(filename, header + data)
    print(filename)

    return header + data


def save_content_to_excel(fname, fcontent):
    """Save content in a xls or xlsx file."""
    with xlsxwriter.Workbook(root + '.xlsx') as wb:
        ws = wb.add_worksheet('Data')
        for i, row in enumerate(fcontent):
            ws.write_row(i, 0, row)


def export_to_csv(levelfiles, barofiles, filename=None):
    fcontent = [["#", "Well_ID", "Location",
                 "Latitude_ddeg", "Longitude_ddeg", "Elevation_m",
                 "Delta_dist_baro_km", "Delta_elev_baro_m"]]

    baro_stations = list(barofiles.keys())
    baro_latitudes = np.array(
        [barofiles[stn].sites.latitude for stn in baro_stations])
    baro_longitudes = np.array(
        [barofiles[stn].sites.longitude for stn in baro_stations])

    print('#  ', '{:<8s}'.format('Piezo_id'), '{:<8s}'.format('Baro_id'),
          '{:>5s}'.format('dist'), '{:>6s}'.format('delev'),
          '  Location')
    print('   ', '{:<8s}'.format(''), '{:<8s}'.format(''),
          '{:>5s}'.format('(km)'), '{:>6s}'.format('(m)'))
    for i, stn_id in enumerate(sorted(list(levelfiles.keys()))):
        level_latitude = levelfiles[stn_id].sites.latitude
        level_longitude = levelfiles[stn_id].sites.longitude
        level_elevation = levelfiles[stn_id].sites.elevation

        dist = calc_dist_from_coord(baro_latitudes, baro_longitudes,
                                    level_latitude, level_longitude)
        baro_stn = baro_stations[np.argmin(dist)]
        delta_elev = (level_elevation - barofiles[baro_stn].sites.elevation)

        print('{:02d} '.format(i + 1),
              '{:<8s}'.format(stn_id),
              '{:<8s}'.format(baro_stn),
              '{:5.1f}'.format(np.min(dist)),
              '{:-6.1f}'.format(delta_elev),
              '  {}'.format(levelfiles[stn_id].sites.site_name)
              )

        fcontent.append(
            ["{:02d}".format(i), stn_id, levelfiles[stn_id].sites.site_name,
             "{}".format(level_latitude), "{}".format(level_longitude),
             "{}".format(level_elevation),
             "{:.1f}".format(np.min(dist)), "{:.1f}".format(delta_elev)
             ])

    if filename:
        root, ext = osp.splitext(filename)
        with open(root + '.csv', 'w', encoding='utf8') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', lineterminator='\n')
            writer.writerows(fcontent)


# %% Read level and baro raw data
root = "C:/Users/User/OneDrive/INRS/2017 - Projet INRS PACC/Analyses Baro"
rsesq_reader = MDDELCC_RSESQ_Reader()
rsesq_reader.load_database()

# # Download the drillogs.
# dirname = osp.join(root, 'drillogs')
# for stn_id in rsesq_reader.station_ids():
#     print('\rDownloading drillogs {}'.format(stn_id), end='')
#     rsesq_reader.dwnld_piezo_drilllog(stn_id, dirname)
# print('')

period = ['Printemps', 'Automne'][1]
region = ['Monteregie', 'Chaudière-Appalaches'][0]
dirname = osp.join(root, "raw_data/{}/{}".format(period, region))

barofiles = {}
levelfiles = {}
latitudes = {}
longitudes = {}
elevations = {}

i = 0
for file in os.listdir(dirname):
    if not file.endswith('csv'):
        continue
    i += 1
    print(i, file)

    solinst_file = hsr.SolinstFileReader(osp.join(dirname, file))
    if "baro" in file.lower():
        stn_id = re.sub(
            '[ -_]?BARO[ -_]?', '', solinst_file.sites.project_name)
        barofiles[stn_id] = solinst_file
    else:
        stn_id = solinst_file.sites.project_name
        levelfiles[stn_id] = solinst_file

    # Get latitude, longitude, and elevation of the well where the
    # logger is installed.
    solinst_file.sites.latitude = float(rsesq_reader[stn_id]['Latitude'])
    solinst_file.sites.longitude = float(rsesq_reader[stn_id]['Longitude'])
    try:
        solinst_file.sites.elevation = float(rsesq_reader[stn_id]['Elevation'])
    except KeyError:
        # We need to download the data to get the station elevation because
        # this info is not in the kml file.
        rsesq_reader.fetch_station_wldata(stn_id)
    finally:
        solinst_file.sites.elevation = float(rsesq_reader[stn_id]['Elevation'])

    latitudes[stn_id] = float(rsesq_reader[stn_id]['Latitude'])
    longitudes[stn_id] = float(rsesq_reader[stn_id]['Longitude'])
    elevations[stn_id] = float(rsesq_reader[stn_id]['Elevation'])

# %% Calcul the lat/lon/elev of region centroid

level_stn_lat = np.array([latitudes[stn] for stn in list(levelfiles.keys())])
level_stn_lon = np.array([longitudes[stn] for stn in list(levelfiles.keys())])

lat_ctr, lon_ctr = calcul_center_latlon(level_stn_lat, level_stn_lon)

# Get the elevation at the region centroid.
elevation = '{}{:2d}_{}{:0>3d}_1arc_v3.tif'.format(
    'n' if lat_ctr > 0 else 's', int(lat_ctr),
    'e' if lon_ctr > 0 else 'w', int(abs(lon_ctr) + 1)
    )
raster = rasterio.open(osp.join(root, 'mne_arc_v3_tifs', elevation))
elev_ctr = next(raster.sample([(lon_ctr, lat_ctr)], indexes=[1]))[0]
print('lat={:.3f}° lon={:.3f}° alt={:d}m'.format(lat_ctr, lon_ctr, elev_ctr))

img = raster.read()
img_plt = plt.imshow(img[0, :, :], cmap='gray')

# %%

os.chdir("C:/Users/User/Program/pygtide")

# Ndata = 4*24*365*2 = 70080 points
# etdata = read_tsoft_expchan(
    # osp.join(root, '{}_expchan.dat'.format(region.lower())),
    # '2017-01-01 00:00:00', 900)

baro_stations = list(barofiles.keys())
baro_latitudes = np.array([latitudes[stn] for stn in baro_stations])
baro_longitudes = np.array([longitudes[stn] for stn in baro_stations])

nlevel = len(levelfiles)
level_baro_link_tbl = {}
print('{:<8s}'.format('Piezo_id'), '{:<8s}'.format('Baro_id'),
      '{:>5s}'.format('dist'), '{:>6s}'.format('delev'),
      '  Location')
print('{:<8s}'.format(''), '{:<8s}'.format(''),
      '{:>5s}'.format('(km)'), '{:>6s}'.format('(m)'))

for stn_id in sorted(list(levelfiles.keys()))[:]:

    latitude = float(rsesq_reader[stn_id]['Latitude'])
    longitude = float(rsesq_reader[stn_id]['Longitude'])
    elevation = float(rsesq_reader[stn_id]['Elevation'])
    etdata = generate_earth_tides(latitude, longitude, elevation)

    dist = calc_dist_from_coord(
        baro_latitudes, baro_longitudes, latitudes[stn_id], longitudes[stn_id])
    # Prepare the data.
    baro_stn = baro_stations[np.argmin(dist)]
    colname = barofiles[baro_stn].records.columns[0]
    barodata = barofiles[baro_stn].records[[colname]]
    colname = levelfiles[stn_id].records.columns[0]
    leveldata = levelfiles[stn_id].records[[colname]]

    delta_elev = (rsesq_reader[stn_id]['Elevation'] -
                  rsesq_reader[baro_stn]['Elevation'])

    # Prepare the file header.
    sites = levelfiles[stn_id].sites
    stn_id = sites.project_name
    header = [['Well Name', sites.site_name],
              ['Well ID', stn_id],
              ['Latitude', rsesq_reader[stn_id]['Latitude']],
              ['Longitude', rsesq_reader[stn_id]['Longitude']],
              ['Altitude', rsesq_reader[stn_id]['Elevation']],
              ['Province', 'Qc'],
              [''],
              ['Date', 'WL(mbgs)', 'BP(m)', 'ET']
              ]

    print('{:<8s}'.format(stn_id),
          '{:<8s}'.format(baro_stn),
          '{:5.1f}'.format(np.min(dist)),
          '{:-6.1f}'.format(delta_elev),
          '  {}'.format(sites.site_name)
          )

    if True:
        foldername = osp.join('formatted_data', region, period)
        if not osp.exists(foldername):
            os.makedirs(foldername)
        filename = '{}_{}_{}_.csv'.format(
            region.lower(), period.lower(), stn_id)
        save_to_gwhat(osp.join(foldername, filename),
                      leveldata, barodata, etdata, header)

# %% Plot the results

# plt.show()

# with rasterio.open(elevation) as src:
#     array = src.read()
#     print(src.width)
    # vals = src.sample((lat_ctr, lon_ctr))
# print(vals[0])
    # for val in vals:
    #     print(val[0]) #val is an array of values, 1 element 
    #                   #per band. src is a single band raster 
    #                   #so we only need val[0]
# sites = solinst_file.sites
# print(solinst_file.sites)
# print(sites.instrument_serial_number)
# print(sites.project_name)
# print(sites.site_name)
# records = solinst_file.records

# solinst_file.plot()
# plt.show()
