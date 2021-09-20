# -*- coding: utf-8 -*-
"""
Un script pour classifier les descriptions lithologiques des logs de forage
en hydrofaciès, tracer les logs d'hydrofaciès sur un graphique et évaluer
le niveau de confinement à partir des séquences d'hydrofaciès.
"""
from math import ceil
import numpy as np
import numpy as np
import os.path as osp
import pandas as pd
from copy import copy
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.transforms import ScaledTranslation
from itertools import combinations
from matplotlib.backends.backend_pdf import PdfPages


secteurs_station_ids = {
    'Châteauguay': [
        '03000001', '03070001', '03070002', '03090001', '03090004', '03090005',
        '03090006', '03090008', '03090010', '03090011', '03090012', '03090013',
        '03090014', '03090015', '03090018', '03090020', '03090021', '03097062',
        '03097082', '03097094', '03097102', '03097131', '03097182', '03097191',
        '03097201', '03000002', '03000003', '03090002', '03090003', '03090007',
        '03090009', '03090019'
        ],
    'Yamaska Sud & Baie Missisquoi': [
        '03030010', '03030011', '03040012', '03040013', '03040014', '03040015',
        '03040016', '03040017', '03040018'
        ],
    'Yamaska Nord': [
        '03030001', '03030002', '03030003', '03030004', '03030005', '03030006',
        '03030007', '03030008', '03030012', '03030013', '03030014', '03030015',
        '03030016', '03030017', '03030018', '03037031', '03037041', '03037071'
        ],
    'Du Chêne': [
        '02360001', '02G47001', '02507001'
        ],
    'Bécancour Sud': [
        '02400001', '02400004', '02407004', '02407005'
        ],
    'Bécancour Nord': [
        '02000004', '02000005', '02000006', '02370001', '02370002', '02370003',
        '02370004', '02400002', '02400003'
        ],
    'Richelieu': [
        '03040001', '03040002', '03040005', '03040006', '03040007', '03040008',
        '03040009', '03040010', '03040011', '03047011'
        ],
    'Nicolet Sud': [
        '03010001', '03010005', '03010006'
        ],
    'Nicolet Nord & Saint-François Nord': [
        '03000005', '03010002', '03010003', '03010004', '03010007', '03020003',
        '03027021'
        ],
    'Saint-François Ouest': [
        '03027091', '03020001', '03020008', '03020009', '03020010', '03020011',
        '03020012', '03020013'
        ],
    'Saint-François Est': [
        '03020002', '03027032', '03027061', '03027062', '03020004', '03020005',
        '03020006', '03020007'
        ],
    'Chaudière': [
        '02340001', '02340002', '02340003', '02340004', '02340005', '02340006',
        '02340007', '02340008'
        ]
    }

# %% Load data

basedir = osp.dirname(__file__)
rsesq_data = pd.read_excel(
    osp.join(basedir, "RSESQ_20190222.xlsx"), sheet_name='STRATIGRAPHIE')

well_ids_rsesq_info = set(rsesq_data['PointID'])

# %% Hydrofacies definition

stratum = sorted({str(s) for s in rsesq_data['Stratum']})

# Remove the dot at the end of description.
stratum = sorted({s[:-1] if s.endswith('.') else s for s in stratum})

# Correct typographical error and replace end of line character.
for i, s in enumerate(stratum):
    if '\n' in s:
        stratum[i] = s.replace('\n', ' ')
    if 'gravelleux' in s:
        print(s, '->', s.replace('gravelleux', 'graveleux'))
        stratum[i] = s.replace('gravelleux', 'graveleux')
    elif 'Argle' in s:
        print(s, '->', s.replace('Argle', 'Argile'))
        stratum[i] = s.replace('Argle', 'Argile')
stratum = sorted(set(stratum))

HFO = []  # Sol organique
HF1 = []  # Argile, silt et sol gelé
HF2 = []  # Sable et gravier
HFX = []  # Till et diamicton indifférencé
ROC = []
AUTRE = []
FIN = []

HF_DESCS = {
    'HFO': 'HFO: terre organique',
    'HF1': 'HF1: argile, silt et sol gelé',
    'HF2': 'HF2: sable et gravier',
    'HFX': 'HFX: till et diamicton',
    'ROC': 'ROC',
    'AUTRE': 'AUTRE'
    }

# HF1 = # Argile et silt
for label in stratum:
    x = copy(label)

    # Particular cases.
    if x == "Sable brun devenant brun-gris à partir de 12 mètres":
        x = 'Sable'
    elif x == ("Interstratification de lits de sable fin à grossier, "
               "traces de gravier et de silt argileux compact"):
        x = 'Till'
    elif x == ("Sable fin, traces de gravier. Présence de petits cailloux. "
               "Présence d'argile de 19.2 à 22.9 m"):
        x = 'Sable fin'
    elif x == "Refus sur sol gelé":
        x = "Sol gelé"
    elif x == "Remblai et terre végétale":
        x = "Terre végétale"
    elif x == "Alternance de lits de silt et de sable fin à moyen":
        x = "Silt"
    elif x == "Alternance de lits de sable fin silteux, de silt et d'argile":
        x = "Argile"

    x = x.lower().strip()

    # Terms not relevant to hydrofacies classification.
    for term in ['brun-rouge', 'brun', 'gris', 'jaune', 'rouge',
                 'hétérogène', 'oxydé']:
        x = x.replace(' ' + term, '')

    # Replace 'à matrice'.
    x = x.replace('à matrice silteuse', 'silteux')
    x = x.replace('à matrice sableuse', 'sableux')
    x = x.replace('à matrice sablo-silteuse', 'sablo-silteux')
    x = x.replace('à matrice silto-sableuse', 'silto-sableux')
    x = x.replace('à matrice silto-argileuse', 'silto-argileux')
    x = x.replace('à matrice gravelo-sableuse', 'gravelo-sableux')

    # Classify labels.

    # =========================================================================
    # Till et diamicton
    # =========================================================================
    if 'till' in x or 'diamicton' in x or 'bloc' in x:
        HFX.append(label)
    # =========================================================================
    # Sol organique
    # =========================================================================
    elif 'terre' in x:
        HFO.append(label)
    elif 'sol organique' in x:
        HFO.append(label)
    # =========================================================================
    # Argile et silt
    # =========================================================================
    elif x.startswith(('argile', 'sol gelé', 'dépôts meubles argileux')):
        HF1.append(label)
    elif x.startswith(('silt', 'remblai silto-argileux')):
        HF1.append(label)
    # =========================================================================
    # Sable et gravier
    # =========================================================================
    elif x.startswith(('gravier', 'cailloux')):
        HF2.append(label)
    elif x.startswith('remblai'):
        x = x.replace(':', '')
        if x == 'remblai':
            HF2.append(label)
        elif x.startswith(('remblai gravier')):
            HF2.append(label)
        if x.startswith('remblai silto-argileux'):
            HF1.append(label)
        elif x.startswith(('remblai sable fin')):
            HF2.append(label)
        elif x.startswith(('remblai de sable et gravier',
                           'remblai sable et cailloux')):
            HF2.append(label)
    elif x.startswith('sable'):
        if x == 'sable':
            HF2.append(label)
        elif x.startswith(('sable,', 'sable et gravier', 'sable graveleux',
                           'sable grossier', 'sable avec')):
            HF2.append(label)
        elif x.startswith(('sable argileux', 'sable silteux', 'sable compact',
                           'sable très fin', 'sable fin', 'sable moyen',
                           'sable et argile')):
            HF2.append(label)
    # =========================================================================
    # Roc
    # =========================================================================
    elif x.startswith(('alternance', 'calcaire', 'dolomie', 'roc', 'grès',
                       'schiste', 'shale')):
        ROC.append(label)
    # =========================================================================
    # Autres
    # =========================================================================
    elif x.startswith(('nan', 'fracture')):
        AUTRE.append(label)
    elif x.startswith(('fin du forage', 'fracture')):
        FIN.append(label)

unclassified = [
    x for x in stratum if x not in
    HF1 + HF2 + ROC + AUTRE + HFX + HFO + FIN]
print('unclassified:', unclassified)

HF_LABEL_STRINGS = {
    'HF2': '; '.join(HF2) + '.',
    'HF1': '; '.join(HF1) + '.',
    'HFX': '; '.join(HFX) + '.',
    'HFO': '; '.join(HFO) + '.',
    'ROC': '; '.join(ROC) + '.',
    'AUTRE': '; '.join(AUTRE) + '.'
    }

HF_LABELS = {'HF2': HF2, 'HF1': HF1, 'HFX': HFX, 'HFO': HFO,
             'ROC': ROC, 'AUTRE': AUTRE, 'FIN': FIN}

# Count the number of unique descriptions.
n = 0
for hf, labels in HF_LABELS.items():
    n += len(labels)


# Save the classification to a file.
fcontent = ''
for hf, labels in HF_LABEL_STRINGS.items():
    fcontent += HF_DESCS[hf] + '\n'
    fcontent += '-' * len(HF_DESCS[hf]) + '\n'
    fcontent += labels + '\n\n'

dirname = osp.dirname(__file__)
filename = 'hydrofacies_log_classification.txt'
with open(osp.join(dirname, filename), 'w', encoding='utf8') as txtfile:
    txtfile.write(fcontent)

# %% Analyze data


def eval_hf_seq(well_ids):
    wells_hf_seq = {}
    for wid in wells_ids:
        strati = rsesq_data[rsesq_data['PointID'] == wid]
        hf_seq = []
        for index, row in strati.iterrows():
            stratum = str(row['Stratum'])
            stratum = stratum[:-1] if stratum.endswith('.') else stratum
            stratum = stratum.replace('\n', ' ')
            stratum = stratum.replace('gravelleux', 'graveleux')
            stratum = stratum.replace('Argle', 'Argile')
            for key, values in HF_LABELS.items():
                if stratum in values:
                    hf = key
                    break
            else:
                hf = 'nan'
            hf_seq.append((hf, row['Depth'], row['Bottom'],
                           round(row['Bottom'] - row['Depth'], 1)))
        wells_hf_seq[wid] = hf_seq
    return wells_hf_seq


def plot_hf_seq(wells_hf_seq, title):
    wells_ids = sorted(wells_hf_seq.keys())
    HF_COLORS = {'HF1': '#aaffee', 'HF2': '#fed976', 'HF3': '#ffeda0',
                 'HF4': '#fed976', 'HF5': '#feb24c', 'HFX': '#66CC00',
                 'HFO': '#784421', 'ROC': '0.5', 'AUTRE': '#f768a1',
                 'FIN': 'white'}
    nbar = 15
    nfig = ceil(len(wells_hf_seq) / nbar)
    figures = []
    for i in range(nfig):
        istart = i * 15
        iend = istart + 15
        page_wells_ids = wells_ids[istart:iend]
        if i > 0:
            page_title = '{} (suite {})'.format(title, i)
        else:
            page_title = title

        fig, ax = plt.subplots()
        figures.append(fig)

        figwidth = 8.5
        figheight = 5
        fig.set_size_inches(figwidth, figheight)

        left_margin = 1.1 / figwidth
        right_margin = 0.5 / figwidth
        bottom_margin = 0.75 / figheight
        top_margin = 1.25 / figheight

        x0 = left_margin
        y0 = bottom_margin
        axheight = 1 - top_margin - bottom_margin
        axwidth = 1 - left_margin - right_margin
        ax.set_position([x0, y0, axwidth, axheight])
        ax.grid(True, which='major', axis='y')

        hmax = 0
        bar_width = 0.5
        istart = i * 15
        iend = istart + 15
        for i, wid in enumerate(page_wells_ids):
            hf_seq = wells_hf_seq[wid]
            for hf in hf_seq:
                ax.bar(i, hf[2] - hf[1], width=bar_width, bottom=hf[1],
                       align='center', color=HF_COLORS[hf[0]],
                       clip_on=True, lw=0)
                hmax = max(hmax, hf[2])
            if i == nbar - 1:
                break

        ax.invert_yaxis()
        ax.set_ylabel('Profondeur (m sous la surface)', fontsize=16,
                      labelpad=20, ha='center', va='center')
        ax.yaxis.set_label_coords(-0.1, 0.5)

        ax.set_xlabel(page_title, fontsize=16, labelpad=15)
        ax.xaxis.set_label_position('top')
        ax.xaxis.set_ticks_position('top')

        # Setup xticks and xticklabels.
        ax.set_xticks(range(i + 1))
        ax.set_xticklabels(page_wells_ids, rotation=45, ha='left')

        # Setup yticks and yticklabels.
        if hmax <= 20:
            yscale = 2
            yscale_minor = 0.5
        elif hmax <= 50:
            yscale = 5
            yscale_minor = 1
        else:
            yscale = 10
            yscale_minor = 2
        ymin = ceil(hmax / yscale) * yscale
        yticks_pos = np.arange(0, ymin + yscale, yscale)
        yticks_pos_minor = np.arange(0, ymin, yscale_minor)
        ax.set_yticks(yticks_pos)
        ax.set_yticks(yticks_pos_minor, minor=True)

        # Setup axis range.
        ax.axis(ymin=ymin, xmin=-0.5, xmax=nbar - 0.5)
        ax.set_axisbelow(True)

        lg_artists = [
            Rectangle((0, 0), 1, 1, fc=HF_COLORS['HFO'], ec='none'),
            Rectangle((0, 0), 1, 1, fc=HF_COLORS['HF1'], ec='none'),
            Rectangle((0, 0), 1, 1, fc=HF_COLORS['HF2'], ec='none'),
            Rectangle((0, 0), 1, 1, fc=HF_COLORS['HFX'], ec='none'),
            Rectangle((0, 0), 1, 1, fc=HF_COLORS['ROC'], ec='none'),
            ]
        lg_labels = [
            'Terre organique',
            'Argile, silt et sol gelé',
            'Sable et gravier',
            'Till et Diamicton indifférencié',
            'Roc fracturé',
            ]

        lg = ax.legend(
            lg_artists, lg_labels, numpoints=1, fontsize=10, ncol=3,
            borderaxespad=0, loc='upper left', borderpad=0,
            bbox_to_anchor=(0, 0, 1, 0), mode="expand",
            bbox_transform=(
                ax.transAxes +
                ScaledTranslation(0/72, -5/72, fig.dpi_scale_trans))
            )
        lg.draw_frame(False)

    return figures


plt.close('all')
figures = []
for secteur, wells_ids in secteurs_station_ids.items():
    wells_hf_seq = eval_hf_seq(wells_ids)
    figures.extend(plot_hf_seq(wells_hf_seq, secteur))

dirname = osp.dirname(__file__)
filename = 'wells_hf_seq.pdf'
with PdfPages(osp.join(dirname, filename)) as pdf:
    for i, fig in enumerate(figures):
        fig.savefig(
            osp.join(dirname,
                     'wells_hf_seq_png',
                     'wells_hf_seq_{:02d}.png'.format(i)),
            dpi=300)
        pdf.savefig(fig)

# %% Déterminer le confinement à partir des séquences d'hydrofaciès.


def eval_confinement(hfseq):
    """
    Détermine les conditions de confinement de l’aquifère rocheux à
    partir de critères établis sur l’épaisseur des hydrofaciès définies dans
    les séquences qui sont fournies dans le dictionnaire hfseq.
    """
    if not len(hfseq):
        return ['Indéterminé']

    h_hf1 = 0  # matériaux fins
    h_hfx = 0  # matériaux indifférenciés
    for hf in hfseq:
        if hf[0] == 'HF1':
            h_hf1 += hf[3]
        elif hf[0] == 'HFX':
            h_hfx += hf[3]
    # Note: les matériaux de type sable et gravier ne sont pas pris en compte
    # dans l'évaluation du niveau de confinement de l'aquifère rocheux.

    # Critère établi sur l'épaisseur des couches de types hf1 pour déterminer
    # si l'aquifère rocheux est libre.
    crit_hf1_libre = 1
    # Critère établi sur l'épaisseur des couches de types hfx pour
    # détermine si l'aquifère rocheux est libre.
    crit_hf1_hfx_libre = 3
    # Critère établis sur l'épaisseur des couches de types hf1 pour déterminer
    # si l'aquifère rocheux est captif.
    crit_hf1_captive = 5

    if h_hf1 >= crit_hf1_captive:
        confinement = 'Captive'
    elif h_hf1 < crit_hf1_libre and h_hfx < crit_hf1_hfx_libre:
        confinement = 'Libre'
    else:
        confinement = 'Semi-captive'
    return confinement


confinement = {}
fcontent = []
for secteur, wells_ids in secteurs_station_ids.items():
    print('-' * 72)
    print(secteur)
    print('-' * 72)
    confinement[secteur] = []
    wells_hf_seq = eval_hf_seq(wells_ids)
    for wid in wells_ids:
        hf_seq = wells_hf_seq[wid]
        well_confinement = eval_confinement(hf_seq)
        confinement[secteur].append(well_confinement)
        print(wid, well_confinement)
        fcontent.append([secteur, wid, well_confinement])

    # Check that it is unique in case there is a double
    # piezo in one borehole.
    for (wid1, wid2) in combinations(wells_ids, 2):
        hf_seq_1 = wells_hf_seq[wid1]
        hf_seq_2 = wells_hf_seq[wid2]
        if len(hf_seq_1) and len(hf_seq_2) and (hf_seq_1 == hf_seq_2):
            print(("Warning: The wells #{} and #{} have the same exact "
                   "HF sequence.").format(wid1, wid2))

import pandas.io.formats.excel
pandas.io.formats.excel.ExcelFormatter.header_style = None

dataframe = pd.DataFrame(
    data=fcontent,
    columns=['secteur', 'station', 'confinement'])
filename = osp.join(osp.dirname(__file__), 'confinement_from_hf.xlsx')
dataframe.to_excel(filename, index=False)

# %%
colums = ['']
for key, values in confinement.items():
    print(key)
    print('-' * len(key))
    total_puits = 0
    for cond in ['Libre', 'Semi-captive', 'Captive']:
        nbr_puits = np.sum([v == cond for v in values])
        total_puits += nbr_puits
        print('{}= {}'.format(cond, nbr_puits))
    print('{}= {}'.format('total', total_puits))
    print()
