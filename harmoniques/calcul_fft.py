# -*- coding: utf-8 -*-
"""
Created on Fri Feb  1 13:40:55 2019
@author: User
"""
# https://en.wikipedia.org/wiki/Theory_of_tides

import os
import os.path as osp
from shutil import copyfile

import numpy as np
import scipy.fftpack
import scipy.signal
import matplotlib.pyplot as plt
from gwhat.projet.reader_projet import ProjetReader
from matplotlib.transforms import ScaledTranslation
from matplotlib.backends.backend_pdf import PdfPages
from xlrd import xldate_as_tuple
import datetime

import matplotlib
matplotlib.rcParams['axes.unicode_minus'] = False


root = ("C:/Users/User/OneDrive/INRS/2017 - Projet INRS PACC/Confinement/"
        "Analyses Baro/brf_monteregie_automne")
ppath = osp.join(root, "brf_monteregie_automne.gwt")

# Make a copy of the project.
ppath2 = osp.join(root, "brf_monteregie_automne_copy.gwt")
copyfile(ppath, ppath2)

project = ProjetReader(ppath2)
YMIN = 0
XMAX = 40

# fs: The sampling frequency

filename = osp.join(root, 'harmonic_analysis.pdf')

# pdfpages = PdfPages(filename)
pdfpages = None
NSTEP = 1
for wldset in project.wldsets[:]:
    fig, axes = plt.subplots(3, 1)
    fig.set_size_inches(w=8, h=6)

    wldset = project.get_wldset(wldset)
    time = wldset['Time']
    wl = wldset['WL']
    wl = np.nanmax(wl) - wl
    bp = wldset['BP']
    fs = 1/(time[1] - time[0])  # sample spacing in days
    N = len(time)  # number of samples

    datetimes = [datetime.datetime(*xldate_as_tuple(xldate, 0)) for
                 xldate in time]

    lg_lines = []
    lg_labels = []
    # axes[0].axhline(0, color='0', ls=':', lw=0.5)
    axes[0].zorder = 1
    axes[0].set_facecolor('None')
    # axes[0].invert_yaxis()
    axes[0].set_title(
        'Well {} (#{})'.format(wldset['Well'], wldset['Well ID']), pad=30)
    axes[0].axis(xmin=datetime.datetime(2017, 5, 1),
                 xmax=datetime.datetime(2017, 12, 1))
    axes[0].tick_params(axis='both', direction='out', labelsize=10)

    # Filter the water level data with a high pass filter.

    # nyq = 0.5 * fs
    cutoff = 0.1
    # order = 5
    # b, a = scipy.signal.butter(
    #     order, cutoff/nyq, btype='high', analog=False)

    # wl_filt = scipy.signal.filtfilt(b, a, wl)
    # wl_filt[indx_nan] = np.nan
    # axes[0].plot(time, wl_filt, lw=1)

    # wldset.dset['WL'][:] = wl_filt
    # wldset.dset.file.flush()

    # ---- Plot water level data

    # Fill the nan values and detrend the signal.
    indx = np.where(~np.isnan(wl))[0]

    # Interpolate missing values.
    wl = np.interp(time, time[indx], wl[indx])
    wl = scipy.signal.detrend(wl)

    # Replace missing values by zero.
    # m, b, r_val, p_val, std_err = scipy.stats.linregress(
    #     time[indx], wl[indx])
    # wl[indx] = wl[indx] - (m * time[indx] + b)
    # wl[np.where(np.isnan(wl))[0]] = 0

    # Plot the detrended water level data.
    wl_nonan = np.empty(N) * np.nan
    wl_nonan[indx] = wl[indx]
    wl_nonan_lines = axes[0].plot(
        datetimes[::NSTEP], wl_nonan[::NSTEP], lw=1, ls='-', color='blue')
    # wl_nonan_lines[0].set_rasterized(True)
    lg_lines.append(wl_nonan_lines[0])
    lg_labels.append('Detrended WL')

    wl_nan = np.copy(wl)
    wl_nan[indx] = np.nan
    wl_nan_lines = axes[0].plot(
        datetimes[::NSTEP], wl_nan[::NSTEP], lw=1, ls='--', color='red')
    # wl_nan_lines[0].set_rasterized(True)
    lg_lines.append(wl_nan_lines[0])
    lg_labels.append('Interpolated missing WL')

    axes[0].set_ylabel('WL (m)', fontsize=12)
    axes[0].axis(xmin=datetime.datetime(2017, 5, 1),
                 xmax=datetime.datetime(2017, 12, 1),
                 ymin=-np.max(np.abs(wl)) * 1.1,
                 ymax=np.max(np.abs(wl)) * 1.1
                 )

    # ---- Water level signal analysis

    # Compute the FFT for the water levels.
    fft = np.abs(np.fft.rfft(wl))[1:int(N/2)]
    fft_freqs = np.fft.fftfreq(N, d=1/fs)[1:int(N/2)]
    fft_periods = 24/fft_freqs  # in h/cycle

    # Only keep the values in the relevent x-range.
    indx = np.where(fft_periods <= XMAX)[0]
    fft = fft[indx]
    fft_freqs = fft_freqs[indx]
    fft_periods = fft_periods[indx]
    YMAX = np.max(fft) * 1.15

    # ax2 = fig2.add_axes([0.1, 0.12, 0.85, 0.8])
    axes[1].fill_between(fft_periods, fft, 0, lw=1, zorder=100, color='black')

    # Plot the harmonic components of tidal potential.
    FONTSIZE = 8

    # O1 component
    axes[1].axvline(25.81933871, lw=1, color='red', ls=':', zorder=10)
    axes[1].text(
        25.81933871, YMAX, 'O1', color='red', va='top', fontsize=FONTSIZE,
        transform=(axes[1].transData +
                   ScaledTranslation(2/72, -2/72, fig.dpi_scale_trans))
        )
    # K1 component
    axes[1].axvline(23.93447213, lw=1, color='green', ls=':', zorder=10)
    axes[1].text(
        23.93447213, YMAX, 'K1', color='green', va='top', ha='right',
        fontsize=FONTSIZE,
        transform=(axes[1].transData +
                   ScaledTranslation(-2/72, -2/72, fig.dpi_scale_trans))
        )
    # N2 component
    axes[1].axvline(12.65834751, lw=1, color='magenta', ls=':', zorder=10)
    axes[1].text(
        12.65834751, YMAX, 'N2', color='magenta', va='top', ha='left',
        fontsize=FONTSIZE,
        transform=(axes[1].transData +
                   ScaledTranslation(2/72, -2/72, fig.dpi_scale_trans))
        )
    # M2 component
    axes[1].axvline(
        12.4206012, lw=1, color='#ff6600', ls=':', zorder=10,
        clip_on=False)
    axes[1].text(
        12.4206012, YMAX, 'M2', color='#ff6600', va='bottom', ha='center',
        fontsize=FONTSIZE,
        transform=(axes[1].transData +
                   ScaledTranslation(0/72, 1/72, fig.dpi_scale_trans))
        )
    # S2 component
    axes[1].axvline(12, lw=1, color='#0066ff', ls=':', zorder=10)
    axes[1].text(
        12, YMAX, 'S2', color='#0066ff', va='top', ha='right',
        fontsize=FONTSIZE,
        transform=(axes[1].transData +
                   ScaledTranslation(-2/72, -2/72, fig.dpi_scale_trans))
        )
    # S3 component
    axes[1].axvline(8, lw=1, color='cyan', ls=':', zorder=1)
    axes[1].text(
        8, YMAX, 'S3', color='cyan', va='top', ha='right',
        fontsize=FONTSIZE,
        transform=(axes[1].transData +
                   ScaledTranslation(-2/72, -2/72, fig.dpi_scale_trans))
        )
    # Setup graph layout.
    axes[1].axvline(24/cutoff, lw=1, color='red', ls=':', zorder=10)
    axes[1].set_xticks(np.arange(100), minor=True)

    axes[1].axis(ymin=YMIN, ymax=YMAX, xmin=-0.1, xmax=XMAX)
    axes[1].tick_params(axis='both', direction='out', labelsize=10)
    axes[1].set_ylabel("Power", fontsize=12)
    axes[1].set_xlabel("Period (h/cycle)", fontsize=12)
    axes[1].text(
        0, 1, 'Water level\nsignal', va='top', ha='left',
        transform=(axes[1].transAxes +
                   ScaledTranslation(5/72, -5/72, fig.dpi_scale_trans)),
        zorder=100)

    # ---- Plot barometric data

    # Fill the nan values and detrend the signal.
    indx = np.where(~np.isnan(bp))[0]
    bp = np.interp(time, time[indx], bp[indx])
    bp = scipy.signal.detrend(bp)

    # Plot the detrended barometric pressure.
    ax0_twinx = axes[0].twinx()
    ax0_twinx.zorder = 2
    bp_lines = ax0_twinx.plot(
        datetimes[::NSTEP], bp[::NSTEP], lw=1, ls='-', alpha=0.65, color='0.5')
    # bp_lines[0].set_rasterized(True)
    lg_lines.append(bp_lines[0])
    lg_labels.append('Detrended BP')

    ax0_twinx.set_ylabel('BP (m)', fontsize=12)
    ax0_twinx.set_yticks([-0.5, 0, 0.5])
    ax0_twinx.set_yticks(np.arange(-0.5, 0.5, 0.1), minor=True)
    ax0_twinx.axis(ymin=-0.55, ymax=0.55)

    # ---- Atmospheric signal analysis

    # Calcul the FFT for the atmospheric signal.
    xfreq = np.abs(np.fft.rfft(bp))[1:int(N/2)]
    fft_freqs = np.fft.fftfreq(N, d=1/fs)[1:int(N/2)]
    fft_periods = 24/fft_freqs  # in h/cycle

    # Only keep the values in the relevent x-range.
    indx = np.where(fft_periods <= XMAX)[0]
    xfreq = xfreq[indx]
    fft_freqs = fft_freqs[indx]
    fft_periods = fft_periods[indx]
    YMAX = np.max(xfreq) * 1.15

    axes[2].fill_between(fft_periods, xfreq, 0, lw=1, zorder=10, color='black')

    # S1 component
    axes[2].axvline(24, lw=1, color='purple', ls=':', zorder=1)
    axes[2].text(
        24, YMAX, 'S1', color='purple', va='top', ha='right',
        fontsize=FONTSIZE,
        transform=(axes[2].transData +
                   ScaledTranslation(-2/72, -2/72, fig.dpi_scale_trans))
        )
    # S2 component
    axes[2].axvline(12, lw=1, color='#0066ff', ls=':', zorder=1)  # S2
    axes[2].text(
        12, YMAX, 'S2', color='#0066ff', va='top', ha='right',
        fontsize=FONTSIZE,
        transform=(axes[2].transData +
                   ScaledTranslation(-2/72, -2/72, fig.dpi_scale_trans))
        )
    # S3 component
    axes[2].axvline(8, lw=1, color='cyan', ls=':', zorder=1)
    axes[2].text(
        8, YMAX, 'S3', color='cyan', va='top', ha='right',
        fontsize=FONTSIZE,
        transform=(axes[2].transData +
                   ScaledTranslation(-2/72, -2/72, fig.dpi_scale_trans))
        )
    # Setup graph layout.
    axes[2].set_xticks(np.arange(100), minor=True)
    axes[2].tick_params(axis='both', direction='out', labelsize=10)
    axes[2].axis(ymin=YMIN, ymax=YMAX, xmin=0, xmax=XMAX)
    axes[2].set_ylabel("Power", fontsize=12)
    axes[2].set_xlabel("Period (h/cycle)", fontsize=12)
    axes[2].text(
        0, 1, 'Atmospheric\nsignal', va='top', ha='left',
        transform=(axes[2].transAxes +
                   ScaledTranslation(5/72, -5/72, fig.dpi_scale_trans)))

    # Calculate and plot the coherence between the water levels and the
    # barometric pressures time series.
    # freq, Cxy = scipy.signal.coherence(wl, bp, fs)
    # axes[3].plot(freq, Cxy)
    # axes[3].axis(ymin=0, ymax=1, xmin=-0.1, xmax=2.5)
    # axes[3].axvline(0.1, color='0.65', ls='--', zorder=1)
    # axes[3].axvline(0.8, color='0.65', ls='--', zorder=1)
    # axes[3].axvline(cutoff, color='red', ls='--', zorder=1)

    # ---- Setup legend
    lg = axes[0].legend(
        lg_lines, lg_labels, numpoints=1, fontsize=10, ncol=3,
        borderaxespad=0, loc='lower left', borderpad=0, bbox_to_anchor=(0, 1),
        bbox_transform=(axes[0].transAxes +
                        ScaledTranslation(5/72, 5/72, fig.dpi_scale_trans))
        )
    lg.draw_frame(False)

    # ---- Setup date format
    adf = axes[0].get_xaxis().get_major_formatter()
    adf.scaled[1. / 24] = '%H:%M'  # set the < 1d scale to H:M
    adf.scaled[1.0] = '%Y-%m-%d'  # set the > 1d < 1m scale to Y-m-d
    adf.scaled[30.] = "%b-'%y"  # set the > 1m < 1Y scale to Y-m
    adf.scaled[365.] = '%Y'  # set the > 1y scale to Y

    fig.tight_layout()
    fig.align_ylabels(axes)
    if pdfpages is not None:
        pdfpages.savefig(fig, bbox_inches="tight")
    plt.show()
plt.close('all')
project.close()
if pdfpages is not None:
    pdfpages.close()

    # ax2.set_ylabel('|Y(f)|')
    # ax2.set_xlabel("Frequency ($\mathrm{day^{-1}}$)")
    # ax2.axis([0, 48, 0, 350])
    # ax2.xaxis.set_ticks_position('bottom')
    # ax2.yaxis.set_ticks_position('left')
    # ax2.tick_params(axis='both', direction='out')
    # ax2.set_xticks(np.arange(100), minor=True)
    # ax2.grid(True, axis='both')
    # # ax2.set_title('Filter Input - Frequency Domain')
    # ax2.set_title(wldset['Well'])

    # # plt.subplot(2, 1, 1)
    # # plt.plot(xf, 2.0/N * np.abs(yf[0:N/2]))
    # # plt.subplot(2, 1, 2)
    # # plt.plot(xf[1:], 2.0/N * np.abs(yf[0:N/2])[1:])
