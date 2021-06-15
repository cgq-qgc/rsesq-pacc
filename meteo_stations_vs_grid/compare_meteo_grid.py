# -*- coding: utf-8 -*-
from math import ceil, floor
import datetime
import os
import os.path as osp
from gwhat.meteo.weather_reader import read_weather_datafile
import numpy as np
import netCDF4
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import ScaledTranslation
from matplotlib.backends.backend_pdf import PdfPages
from itertools import product


class InfoClimatGridReader:
    """
    The :attr:`~pyhelp.weather_reader.InfoClimatGridReader` is a class
    to read and format precipitation and air temperature data from the
    interpolated grid produced by the `Info-climat service`_ of the MDDELCC.

    .. _Info-climat service:
       http://www.mddelcc.gouv.qc.ca/climat/surveillance/produits.htm
    """

    def __init__(self, dirpath_netcdf):
        super(InfoClimatGridReader, self).__init__()
        self.dirpath_netcdf = dirpath_netcdf
        self.lat = []
        self.lon = []
        self._setup_ncfile_list()
        self._setup_latlon_grid()

    def _setup_ncfile_list(self):
        """Read all the available netCDF files in dirpath_netcdf."""
        self.ncfilelist = []
        for file in os.listdir(self.dirpath_netcdf):
            if file.endswith('.nc'):
                self.ncfilelist.append(osp.join(self.dirpath_netcdf, file))

    def _setup_latlon_grid(self):
        if self.ncfilelist:
            netcdf_dset = netCDF4.Dataset(self.ncfilelist[0], 'r+')
            self.lat = np.array(netcdf_dset['lat'])
            self.lon = np.array(netcdf_dset['lon'])
            netcdf_dset.close()

    def _get_idx_from_latlon(self, latitudes, longitudes, unique=False):
        """
        Get the i and j indexes of the grid meshes from a list of latitude
        and longitude coordinates. If unique is True, only the unique pairs of
        i and j indexes will be returned.
        """
        try:
            lat_idx = [np.argmin(np.abs(self.lat - lat)) for lat in latitudes]
            lon_idx = [np.argmin(np.abs(self.lon - lon)) for lon in longitudes]
            if unique:
                ijdx = np.vstack({(i, j) for i, j in zip(lat_idx, lon_idx)})
                lat_idx = ijdx[:, 0].tolist()
                lon_idx = ijdx[:, 1].tolist()
        except TypeError:
            lat_idx = np.argmin(np.abs(self.lat - latitudes))
            lon_idx = np.argmin(np.abs(self.lon - longitudes))

        return lat_idx, lon_idx

    def _get_data_from_idx(self, lat_idx, lon_idx, years):
        try:
            len(lat_idx)
        except TypeError:
            lat_idx, lon_idx = [lat_idx], [lon_idx]

        tasmax_stacks = []
        tasmin_stacks = []
        precip_stacks = []
        years_stack = []
        for year in years:
            print('\rFetching daily weather data for year %d...' % year,
                  end=' ')
            filename = osp.join(self.dirpath_netcdf, 'GCQ_v2_%d.nc' % year)
            netcdf_dset = netCDF4.Dataset(filename, 'r+')

            tasmax_stacks.append(
                np.array(netcdf_dset['tasmax'])[:, lat_idx, lon_idx])
            tasmin_stacks.append(
                np.array(netcdf_dset['tasmin'])[:, lat_idx, lon_idx])
            precip_stacks.append(
                np.array(netcdf_dset['pr'])[:, lat_idx, lon_idx])
            years_stack.append(
                np.zeros(len(precip_stacks[-1][:])).astype(int) + year)

            netcdf_dset.close()
        print('done')

        tasmax = np.vstack(tasmax_stacks)
        tasmin = np.vstack(tasmin_stacks)
        precip = np.vstack(precip_stacks)
        years = np.hstack(years_stack)

        return tasmin, tasmax, precip, years

    def get_data_from_latlon(self, latitudes, longitudes, years):
        """
        Return the daily minimum, maximum and average air temperature and daily
        precipitation
        """
        lat_idx, lon_idx = self._get_idx_from_latlon(latitudes, longitudes)
        tasmin, tasmax, precip, years = self._get_data_from_idx(
            lat_idx, lon_idx, years)

        # Create an array of datestring and lat/lon
        Ndt, Ndset = np.shape(tasmax)
        start = datetime.datetime(years[0], 1, 1)
        # datetimes = [start + datetime.timedelta(days=i) for i in range(Ndt)]
        # datestrings = [dt.strftime("%Y-%m-%d") for dt in datetimes]
        datetimes = pd.to_datetime(
            [start + datetime.timedelta(days=i) for i in range(Ndt)])

        # Replace -999 with np.nan.
        precip[:, :][precip[:, :] == -999] = np.nan
        tasmax[:, :][tasmax[:, :] == -999] = np.nan
        tasmin[:, :][tasmin[:, :] == -999] = np.nan

        # Store the data in panda dataframes.
        columns = list(zip(latitudes, longitudes))

        precip_df = pd.DataFrame(precip, index=datetimes, columns=columns)
        precip_df.index.name = 'datetime'

        tasmax_df = pd.DataFrame(tasmax, index=datetimes, columns=columns)
        tasmax_df.index.name = 'datetime'

        tasmin_df = pd.DataFrame(tasmin, index=datetimes, columns=columns)
        tasmin_df.index.name = 'datetime'

        return tasmax_df, tasmin_df, precip_df

    def get_dist_from_latlon(self, lat1, lon1):
        """
        Compute the  horizontal distance in km between a location given in
        decimal degrees and a set of locations also given in decimal degrees.
        """
        lat2_idx, lon2_idx = self._get_idx_from_latlon(lat1, lon1)
        lat2 = self.lat[lat2_idx]
        lon2 = self.lon[lon2_idx]

        lat1, lon1 = np.radians(lat1), np.radians(lon1)
        lat2, lon2 = np.radians(lat2), np.radians(lon2)

        r = 6373  # r is the Earth radius in km

        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

        return r * c


# %% Read Station Data

dirname = osp.join(osp.dirname(__file__), 'data_station')
filenames = os.listdir(dirname)

sta_lats = []
sta_lons = []
sta_names = []
sta_datastack = []
for filename in filenames:
    metadata, data = read_weather_datafile(
        osp.join(dirname, filename))
    sta_lats.append(metadata['Latitude'])
    sta_lons.append(metadata['Longitude'])
    sta_names.append(metadata['Station Name'])
    sta_datastack.append(data)


# %% Extract Grid Data

# Get weather data from the netCDF files for each year and each point of the
# grid that are within the study area.

years = np.arange(1980, 2018)
grid_reader = InfoClimatGridReader("D:/Data/MeteoGrilleDaily")
tasmax, tasmin, precip = grid_reader.get_data_from_latlon(
    sta_lats, sta_lons, years)
dist = grid_reader.get_dist_from_latlon(sta_lats, sta_lons)

# %% Compare precipitations

# Compare the precipitations from the station with that of the grid
# and plot the results.

nrow = 2
ncol = 4
npage = ceil(len(filenames) / (ncol * nrow))

figwidth = 11
figheight = 7
left_margin = 1.1 / figwidth
right_margin = 0.35 / figwidth
bottom_margin = 0.95 / figheight
top_margin = 0.6 / figheight
hspace = 0.65 / figwidth
vspace = 1.5 / figheight
axheight = (1 - top_margin - bottom_margin - (nrow - 1) * vspace) / nrow
axwidth = (1 - left_margin - right_margin - (ncol - 1) * hspace) / ncol

periods = ['daily', 'monthly', 'yearly']

for period in periods:
    print('Producing scatter plot for {} precip...'.format(period))
    print('-' * 50)
    scale = {'daily': 50, 'monthly': 100, 'yearly': 500}[period]
    scale_minor = {'daily': 10, 'monthly': 20, 'yearly': 100}[period]
    minval = {'daily': 0, 'monthly': 0, 'yearly': 500}[period]
    maxval = {'daily': 150, 'monthly': 300, 'yearly': 2000}[period]
    units = {'daily': 'mm/jour',
             'monthly': 'mm/mois',
             'yearly': 'mm/an'}[period]

    rmse_stack = []
    me_stack = []
    r_stack = []
    figures = []
    for j in range(npage):
        fig = plt.figure()
        fig.set_size_inches(w=figwidth, h=figheight)
        figures.append(fig)
        for row, col in product(range(nrow), range(ncol)):
            i = col + (row * ncol) + j * (nrow * ncol)
            if i > len(filenames) - 1:
                continue
            x0 = left_margin + col * (axwidth + hspace)
            y0 = bottom_margin + (nrow - row - 1) * (axheight + vspace)
            ax = fig.add_axes([x0, y0, axwidth, axheight])

            station = sta_names[i]
            lat_sta = sta_lats[i]
            lon_sta = sta_lons[i]

            ax.set_aspect('equal')
            ax.set_axisbelow(True)
            ax.tick_params(axis='both', direction='out', labelsize=12)
            ax.grid(True, axis='both', color='#C0C0C0')
            ax.set_xlabel('Ptot station ({})'.format(units),
                          labelpad=10, fontsize=14)
            if i % ncol == 0:
                ax.set_ylabel('Ptot grille ({})'.format(units),
                              labelpad=10, fontsize=14)

            # Prepare the data.
            sta_precip = sta_datastack[i][['Ptot']]
            grid_precip = precip[[(sta_lats[i], sta_lons[i])]]
            join_precip = (
                sta_precip.copy()
                .join(grid_precip, how='left', sort=True)
                .dropna(axis=0, how='any')
                )
            year_min = join_precip.index[0].year
            year_max = join_precip.index[-1].year
            year_range = (year_max - year_min) + 1
            join_precip.columns = ['sta_ptot', 'grid_ptot']
            if period == 'monthly':
                join_precip = join_precip.groupby(
                    [join_precip.index.year, join_precip.index.month]).sum()
            elif period == 'yearly':
                join_precip = join_precip.groupby(
                    [join_precip.index.year]).sum()

            # Plot the data.
            l1, = ax.plot(join_precip['sta_ptot'], join_precip['grid_ptot'],
                          ms=3, alpha=0.5, mfc='k', mec='k', marker='o',
                          clip_on=True, mew=0, ls='none')
            l1.set_rasterized(True)
            ax.plot([0, maxval], [0, maxval], '--', lw=1, color='red')

            ax.set_title(
                "{}\n{} - {}".format(station, year_min, year_max),
                fontsize=12, linespacing=1.3)

            # Setup the axis.
            xyticks = np.arange(minval, maxval + scale, scale)
            xyticklabels = [str(val) for val in xyticks]
            xyticklabels[0] = ''
            xyticklabels[-1] = ''
            ax.set_xticks(xyticks)
            ax.set_xticklabels(xyticklabels)
            ax.set_yticks(xyticks)
            ax.set_yticklabels(xyticklabels)
            ax.set_xticks(
                np.arange(0, maxval + scale_minor, scale_minor),
                minor=True)
            ax.set_yticks(
                np.arange(0, maxval + scale_minor, scale_minor),
                minor=True)
            ax.axis(ymin=minval, ymax=maxval, xmin=minval, xmax=maxval)

            # Plot the distance between the station and the closest node
            # of the grid, the coefficient of regression, and the rmse.
            r = np.corrcoef(
                join_precip['sta_ptot'].values,
                join_precip['grid_ptot'].values)[1, 0]
            rmse = np.nanmean((join_precip['sta_ptot'].values -
                               join_precip['grid_ptot'].values
                               )**2)**0.5
            me = np.nanmean(join_precip['grid_ptot'].values -
                            join_precip['sta_ptot'].values)

            rmse_stack.append(rmse)
            me_stack.append(me)
            r_stack.append(r)

            ax.text(
                0, 1,
                ('rmse = {:0.2f} {}\n'
                 'me = {:0.2f} {}\n'
                 'dist. = {:0.1f} km\n'
                 'r = {:0.3f}'
                 ).format(rmse, units, me, units, dist[i], r),
                ha='left', va='top', fontsize=10, linespacing=1.3,
                transform=(
                    ax.transAxes +
                    ScaledTranslation(5/72, -5/72, fig.dpi_scale_trans))
                )

            # Add mean value.
            bbox = ax.get_tightbbox(fig.canvas.get_renderer())
            y0 = ax.transAxes.inverted().transform(bbox)[0, 1]

            precip_moy = join_precip['sta_ptot'].mean()
            ax.text(
                0.5, y0,
                ('moy. = {:0.2f} {}').format(precip_moy, units),
                ha='center', va='top', fontsize=10, linespacing=1.3,
                transform=(
                    ax.transAxes +
                    ScaledTranslation(0, -5/72, fig.dpi_scale_trans))
                )

    print('Ptot {} min rmse = {:0.5f}'.format(period, np.min(rmse_stack)))
    print('Ptot {} max rmse = {:0.5f}'.format(period, np.max(rmse_stack)))
    print('Ptot {} mean rmse = {:0.5f}'.format(period, np.mean(rmse_stack)))
    print('Ptot {} min r = {:0.5f}'.format(period, np.min(r_stack)))
    print('Ptot {} max r = {:0.5f}'.format(period, np.max(r_stack)))
    print('Ptot {} mean r = {:0.5f}'.format(period, np.mean(r_stack)))
    print('Ptot {} min me = {:0.5f}'.format(period, np.min(me_stack)))
    print('Ptot {} max me = {:0.5f}'.format(period, np.max(me_stack)))
    print('Ptot {} mean me = {:0.5f}'.format(period, np.mean(me_stack)))
    print('-' * 50)

    dirname = osp.dirname(__file__)
    filename = 'precip_grid_vs_station_{}.pdf'.format(period)
    with PdfPages(osp.join(dirname, filename)) as pdf:
        for i, fig in enumerate(figures):
            filename = 'precip_grid_vs_station_{}_page{}.png'.format(period, i)
            fig.savefig(osp.join(dirname, 'figures_png', filename), dpi=300)
            pdf.savefig(fig)
plt.close('all')

# %% PDF for daily precip

print('Producing PDF for precip.')
ncol = 4
nrow = 2
npage = ceil(len(filenames) / (ncol * nrow))

minval = 0
maxval = 150
scale = 50
scale_minor = 10

figwidth = 11
figheight = 7
left_margin = 1.1 / figwidth
right_margin = 0.35 / figwidth
bottom_margin = 1 / figheight
top_margin = 0.6 / figheight
hspace = 0.65 / figwidth
vspace = 1.5 / figheight
axheight = (1 - top_margin - bottom_margin - (nrow - 1) * vspace) / nrow
axwidth = (1 - left_margin - right_margin - (ncol - 1) * hspace) / ncol

figures = []
for j in range(npage):
    fig = plt.figure()
    fig.set_size_inches(w=figwidth, h=figheight)
    figures.append(fig)
    for row, col in product(range(nrow), range(ncol)):
        i = col + (row * ncol) + j * (nrow * ncol)
        if i > len(filenames) - 1:
            continue
        x0 = left_margin + col * (axwidth + hspace)
        y0 = bottom_margin + (nrow - row - 1) * (axheight + vspace)
        ax = fig.add_axes([x0, y0, axwidth, axheight])

        station = sta_names[i]
        lat_sta = sta_lats[i]
        lon_sta = sta_lons[i]

        ax.set_yscale('log', nonposy='clip')
        ax.set_axisbelow(True)
        ax.tick_params(axis='both', direction='out', labelsize=12)
        ax.grid(True, axis='both', color='#C0C0C0')
        ax.set_xlabel('Ptot (mm/jour)', labelpad=10, fontsize=14)
        if i % ncol == 0:
            ax.set_ylabel('Probabilité', labelpad=10, fontsize=14)

        # Prepare the data.
        sta_precip = sta_datastack[i][['Ptot']]
        grid_precip = precip[(sta_lats[i], sta_lons[i])]
        join_precip = (
            sta_datastack[i][['Ptot']].copy()
            .join(precip[[(sta_lats[i], sta_lons[i])]], how='left', sort=True)
            .dropna(axis=0, how='any')
            )
        year_min = join_precip.index[0].year
        year_max = join_precip.index[-1].year
        year_range = (year_max - year_min) + 1
        join_precip.columns = ['sta_ptot', 'grid_ptot']

        # Plot the data.
        c1, c2 = '#6495ED', 'red'
        ax.hist(join_precip['sta_ptot'], bins=20, color=c1,
                histtype='stepfilled', density=True,
                alpha=0.65, ec='None', label='FDP Ptot station')
        ax.hist(join_precip['grid_ptot'], bins=20, facecolor="None",
                histtype='stepfilled', density=True,
                alpha=1, ec=c2, label='FDP Ptot grille')

        # Setup the axes title.
        ax.set_title(
            "{}\n{} - {}".format(station, year_min, year_max),
            fontsize=12, linespacing=1.3)

        # Setup legend.
        lg = ax.legend(loc='upper right', frameon=False)

        # Setup wet days delta.
        grid_wet_days = (join_precip['grid_ptot'] > 0).sum()
        sta_wet_days = (join_precip['sta_ptot'] > 0).sum()
        delta_wet_days = ceil((grid_wet_days - sta_wet_days) / year_range)

        fig.canvas.draw()
        bbox = ax.get_tightbbox(fig.canvas.get_renderer())
        y0 = ax.transAxes.inverted().transform(bbox)[0, 1]

        ax.text(
            0.5, y0,
            ('Δjours pluvieux = {} jours/an').format(delta_wet_days),
            ha='center', va='top', fontsize=10, linespacing=1.3,
            transform=(
                ax.transAxes +
                ScaledTranslation(0, -5/72, fig.dpi_scale_trans))
            )

        # Setup the axis.

        # We offset the first tick by 1 to avoid plotting the vertical red line
        # at x=0 of the grid_ptot hist.
        xticks = np.arange(0, maxval + scale, scale)
        xticks[0] = 1
        xticklabels = [str(val) for val in xticks]
        xticklabels[0] = ''
        xticklabels[-1] = ''
        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels)
        ax.set_xticks(
            np.arange(0, maxval + scale_minor, scale_minor),
            minor=True)
        ax.set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1e0])
        ax.axis(xmin=1, xmax=maxval, ymax=1, ymin=7e-6)

dirname = osp.dirname(__file__)
filename = 'fdp_precip_grid_vs_station.pdf'
with PdfPages(osp.join(dirname, filename)) as pdf:
    for i, fig in enumerate(figures):
        filename = 'fdp_precip_grid_vs_station_page{}.png'.format(i)
        fig.savefig(osp.join(dirname, 'figures_png', filename), dpi=300)
        pdf.savefig(fig)
plt.close('all')


# %% Compare air temperature

# Compare the air temperature from the station with that of the grid
# and plot the results.

nrow = 2
ncol = 4
npage = ceil(len(filenames) / (ncol * nrow))

figwidth = 11
figheight = 7
left_margin = 1.1 / figwidth
right_margin = 0.35 / figwidth
bottom_margin = 0.95 / figheight
top_margin = 0.6 / figheight
hspace = 0.65 / figwidth
vspace = 1.5 / figheight
axheight = (1 - top_margin - bottom_margin - (nrow - 1) * vspace) / nrow
axwidth = (1 - left_margin - right_margin - (ncol - 1) * hspace) / ncol

scale = 20
scale_minor = 5
minval = -40
maxval = 40
units = '°C'

rmse_stack = []
me_stack = []
r_stack = []
for var in ['tamin', 'tamax']:
    print('Producing scatter plot for {} temperature...'.format(var))
    print('-' * 50)
    figures = []
    for j in range(npage):
        fig = plt.figure()
        fig.set_size_inches(w=figwidth, h=figheight)
        figures.append(fig)
        for row, col in product(range(nrow), range(ncol)):
            i = col + (row * ncol) + j * (nrow * ncol)
            if i > len(filenames) - 1:
                continue
            x0 = left_margin + col * (axwidth + hspace)
            y0 = bottom_margin + (nrow - row - 1) * (axheight + vspace)
            ax = fig.add_axes([x0, y0, axwidth, axheight])

            station = sta_names[i]
            lat_sta = sta_lats[i]
            lon_sta = sta_lons[i]

            ax.set_aspect('equal')
            ax.set_axisbelow(True)
            ax.tick_params(axis='both', direction='out', labelsize=12)
            ax.grid(True, axis='both', color='#C0C0C0')
            ax.set_xlabel('Ptot station ({})'.format(units),
                          labelpad=10, fontsize=14)
            if i % ncol == 0:
                ylabel = ('Tmin grille (°C)' if var == 'tamin' else
                          'Tmax grille (°C)')
                ax.set_ylabel(ylabel, labelpad=10, fontsize=14)

            # Prepare the data.
            sta_temp = sta_datastack[i][['Tmin' if var == 'tamin' else 'Tmax']]
            grid_temp = (
                (tasmin if var == 'tamin' else tasmax)
                [[(sta_lats[i], sta_lons[i])]]
                )
            join_temp = (
                sta_temp.copy()
                .join(grid_temp, how='left', sort=True)
                .dropna(axis=0, how='any')
                )
            year_min = join_temp.index[0].year
            year_max = join_temp.index[-1].year
            year_range = (year_max - year_min) + 1
            join_temp.columns = ['sta_temp', 'grid_temp']

            # Plot the data.
            l1, = ax.plot(join_temp['sta_temp'], join_temp['grid_temp'],
                          ms=3, alpha=0.5, mfc='k', mec='k', marker='o',
                          clip_on=True, mew=0, ls='none')
            l1.set_rasterized(True)
            ax.plot([minval, maxval], [minval, maxval],
                    '--', lw=1, color='red')

            ax.set_title(
                "{}\n{} - {}".format(station, year_min, year_max),
                fontsize=12, linespacing=1.3)

            # Setup the axis.
            xyticks = np.arange(minval, maxval + scale, scale)
            xyticklabels = [str(val) for val in xyticks]
            xyticklabels[0] = ''
            xyticklabels[-1] = ''
            ax.set_xticks(xyticks)
            ax.set_xticklabels(xyticklabels)
            ax.set_yticks(xyticks)
            ax.set_yticklabels(xyticklabels)
            ax.set_xticks(
                np.arange(minval, maxval + scale_minor, scale_minor),
                minor=True)
            ax.set_yticks(
                np.arange(minval, maxval + scale_minor, scale_minor),
                minor=True)
            ax.axis(ymin=minval, ymax=maxval, xmin=minval, xmax=maxval)

            # Plot the distance between the station and the closest node
            # of the grid, the coefficient of regression, and the rmse.
            r = np.corrcoef(
                join_temp['sta_temp'].values,
                join_temp['grid_temp'].values)[1, 0]
            rmse = np.nanmean(
                (join_temp['sta_temp'].values -
                 join_temp['grid_temp'].values)**2
                )**0.5
            me = np.nanmean(join_temp['grid_temp'].values -
                            join_temp['sta_temp'].values)
            rmse_stack.append(rmse)
            me_stack.append(me)
            r_stack.append(r)

            ax.text(
                0, 1,
                ('rmse = {:0.2f} °C\n'
                 'me = {:0.2f} °C\n'
                 'dist. = {:0.1f} km\n'
                 'r = {:0.3f}'
                 ).format(rmse, me, dist[i], r),
                ha='left', va='top', fontsize=10, linespacing=1.3,
                transform=(
                    ax.transAxes +
                    ScaledTranslation(5/72, -5/72, fig.dpi_scale_trans))
                )

            # Add mean value.
            bbox = ax.get_tightbbox(fig.canvas.get_renderer())
            y0 = ax.transAxes.inverted().transform(bbox)[0, 1]

            temp_moy = join_temp['sta_temp'].mean()
            ax.text(
                0.5, y0,
                ('moy. = {:0.2f} °C').format(temp_moy),
                ha='center', va='top', fontsize=10, linespacing=1.3,
                transform=(
                    ax.transAxes +
                    ScaledTranslation(0, -5/72, fig.dpi_scale_trans))
                )

    print('{} min rmse = {:0.5f}'.format(var, np.min(rmse_stack)))
    print('{} max rmse = {:0.5f}'.format(var, np.max(rmse_stack)))
    print('{} mean rmse = {:0.5f}'.format(var, np.mean(rmse_stack)))
    print('{} min r = {:0.5f}'.format(var, np.min(r_stack)))
    print('{} max r = {:0.5f}'.format(var, np.max(r_stack)))
    print('{} mean r = {:0.5f}'.format(var, np.mean(r_stack)))
    print('{} min me = {:0.5f}'.format(var, np.min(me_stack)))
    print('{} max me = {:0.5f}'.format(var, np.max(me_stack)))
    print('{} mean me = {:0.5f}'.format(var, np.mean(me_stack)))
    print('-' * 50)
    dirname = osp.dirname(__file__)
    filename = '{}_grid_vs_station_daily.pdf'.format(var)
    with PdfPages(osp.join(dirname, filename)) as pdf:
        for i, fig in enumerate(figures):
            filename = '{}_grid_vs_station_daily_page{}.png'.format(var, i)
            fig.savefig(osp.join(dirname, 'figures_png', filename), dpi=300)
            pdf.savefig(fig)
plt.close('all')
