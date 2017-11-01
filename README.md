# Table des Matières

1. [Collecte et mise en forme des données](#1-collecte-et-mise-en-forme-des-données)<br />
    1.1. [API pour télécharger les données du RSESQ du MDDELCC](#11-api-pour-télécharger-les-données-du-rsesq-du-mddelcc)<br />
    1.2a. [API pour télécharger les données climatiques d'ECCC](#12a-api-pour-télécharger-les-données-climatiques-deccc)<br />
    1.2b. [Logiciel pour télécharger les données climatiques d'ECCC](#12b-logiciel-avec-interface-graphique-pour-télécharger-les-données-climatiques-deccc)<br />
    1.3. [API pour récupérer les données hydrométriques du CEHQ](#13-api-pour-récupérer-les-données-hydrométriques-du-cehq)<br />
2. [Caractérisation du Réseau](#2-caractérisation-du-réseau)
3. [License](#3-license)

# 1 Collecte et mise en forme des données

Outils développés à l'[INRS centre Eau-Terre-Environnement](http://www.ete.inrs.ca/) pour récupérer et mettre en forme automatiquement les données temporelles piézométriques, hydrométriques et climatiques qui sont rendues disponibles gratuitement par le [Ministère du Développement Durable, de l'Environnement et de la Lutte contre les Changements Climatiques](http://www.mddelcc.gouv.qc.ca/) du Québec et par [Environnement et Changement climatique Canada](https://www.ec.gc.ca/default.asp?lang=Fr).

## 1.1 API pour télécharger les données du RSESQ du MDDELCC
http://www.mddelcc.gouv.qc.ca/eau/piezo/

Le script ci-dessous montre comment il est possible d'utiliser l'API pour sauvegarder les données journalières de toutes les stations piézométriques du MDDELCC dans un fichier csv.

```python
from readers import MDDELCC_RSESQ_Reader
import os

dirname = os.path.join(os.getcwd(), 'data_files', 'water_level')

reader = MDDELCC_RSESQ_Reader()
for stn in reader.stations():
    filename = "%s (%s).csv" % (stn['Name'], stn['ID'])
    reader.save_station_to_csv(stn['ID'], os.path.join(dirname, filename))
```

## 1.2a API pour télécharger les données climatiques d'ECCC
http://climate.weather.gc.ca/historical_data/search_historic_data_e.html

Le script ci-dessous montre comment il est possible d'utiliser l'API pour télécharger, formatter et sauvegarder dans un fichier csv les données climatiques journalières de toutes les stations climatiques actives d'ECCC (Environnement et Changement Climatique Canada) localisées au Québec.


```python
import os
from readers import EC_Climate_Reader

dirname = os.path.join(os.getcwd(), 'data_files', 'climate')

reader = EC_Climate_Reader()
reader.raw_data_dir = os.path.join(dirname, 'raw_datafiles')
stationlist = reader.stations(active=True, prov='QC')
for i, stn in enumerate(stationlist):
    filepath = os.path.join(dirname, "%s (%s).csv" % (stn['Name'], stn['ID']))
    reader.save_station_to_csv(stn['ID'], filepath)
```

La première fois que `EC_Climate_Reader` est initialisé, les infos pour l'ensemble des stations climatiques canadiennes avec des données journalières disponibles sont téléchargées du site web d'Environnement Canada et sont sauvegardées sur le disque en format binaire dans le fichier `ec_climate_database.npy`. Les initialisations subséquentes de `EC_Climate_Reader` accéderont les infos des stations directement à partir de ce fichier. Toutefois, seul les infos relatives aux stations sont téléchargées lors de cette opération et non les données climatiques journalières. Si les données journalières n'existent pas dans la base de données locale pour une station donnée lorsque l'on appelle `save_station_to_csv(<station_id>, <filepath>)`, ces dernières sont alors automatiquement téléchargées du site web d'Environnement Canada.

Il est également possible de sauvegarder les données dans la base de données locale sans les sauvegarder dans un csv en faisant:

```python
reader = EC_Climate_Reader()
reader.fetch_station_data(<station_id>)
```
Pour mettre à jour la base de données locale à partir de celle d'Environnement Canada, il suffit de lancer:

```python
reader = EC_Climate_Reader()
reader.fetch_database()
```

Cela effacera toutefois toutes les données journalières de la base de données locale. Il faudra alors télécharger à nouveau les données journalières pour chacune des stations.

## 1.2b Logiciel avec interface graphique pour télécharger les données climatiques d'ECCC
https://github.com/jnsebgosselin/what

Le logiciel [WHAT](https://github.com/jnsebgosselin/what), qui est développé dans le cadre de ce projet, permet également de télécharger les données climatiques d'ECCC (Environnement et Changement Climatique Canada) et de combler les données manquantes à partir d'une interface graphique.

![Prise d'écran de l'interface de WHAT pour télécharger les données climatiques](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/img_src/what_telecharger_donnees_climatiques.png)
_Figure: Caputre d'écran de l'interface du logiciel [WHAT](https://github.com/jnsebgosselin/what) pour le téléchargement et la mise en forme des données climatique d'[Environnement et Changement climatique Canada](http://climat.meteo.gc.ca/historical_data/search_historic_data_f.html)_

## 1.3 API pour récupérer les données hydrométriques du CEHQ
https://www.cehq.gouv.qc.ca/hydrometrie/historique_donnees/default.asp

Le script ci-dessous montre comment il est possible d'utiliser l'API pour sauvegarder les données journalières de toutes les stations hydrométriques actives du CEHQ dans un fichier csv.

```python
import os
from readers import MDDELCC_CEHQ_Reader

dirname = os.path.join(os.getcwd(), 'data_files', 'streamflow_and_level')

reader = MDDELCC_CEHQ_Reader()
for i, stn in enumerate(reader.stations()):
    filepath = os.path.join(dirname, "%s (%s).csv" % (stn['Name'], stn['ID']))
    reader.save_station_to_csv(stn['ID'], filepath)
```

La première fois que `MDDELCC_CEHQ_Reader` est initialisé, les infos pour l'ensemble des stations hydrométriques sont téléchargées du site web du CEHQ et sont sauvegardées sur le disque en format binaire dans le fichier `mddelcc_cehq_stations.npy`. Les initialisations subséquentes de `MDDELCC_CEHQ_Reader` accéderont les infos directement à partir de ce fichier. Toutefois, seul les infos relatives aux stations sont téléchargées lors de cette opération et non les données journalières de débits et niveaux d'eau. Si les données journalières n'existent pas dans la base de données locale pour une station donnée lorsque l'on appelle `save_station_to_csv(<station_id>, <filepath>)`, ces dernières sont alors automatiquement téléchargées du site web du CEHQ.

Il est également possible de sauvegarder les données dans la base de données locale sans les sauvegarder dans un csv en faisant:

```python
reader = MDDELCC_CEHQ_Reader()
reader.fetch_station_data(<station_id>)
```

Pour mettre à jour la base de données locale à partir de celle du CEHQ, il suffit de lancer:

```python
reader = MDDELCC_CEHQ_Reader()
reader.fetch_database()
```

Cela effacera toutefois toutes les données journalières de la base de données locale. Il faudra alors télécharger à nouveau les données journalières pour chacune des stations.

# 2 Caractérisation du Réseau
![Nombre de stations piézo en fonction des années](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/rsesq-data/nbr_stns_actives_vs_temps.png)
_**Figure**: Nombre de stations piézométriques actives du RSESQ par tranches de 5 ans (diagramme à bandes bleues) et pour chaque année (ligne pointillée rouge)._<br />
_**Code source**: https://github.com/jnsebgosselin/inrs-rsesq/blob/master/rsesq-data/rsesq_timeline.py_

![Nombre de stations piézo en fonction du nbr d'années](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/rsesq-data/stns_nbr_vs_year_nbr.png)
_**Figure**: Diagramme à bandes du nombre de stations piézométriques du RSESQ selon le nombre d'années avec des données disponibles à chacune des stations._<br />
_**Code source**: https://github.com/jnsebgosselin/inrs-rsesq/blob/master/rsesq-data/rsesq_timeline.py_

![Dist. piézo vs climat et hydro](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/rsesq-data/rsesq_dist_stns_climate_hydro.png)
_**Figure**: Diagramme à bandes de la distribution du nbr. de stations piézo actives en fonction de la distance min. aux stations climatiques et hydrométriques._<br />
_**Code source**: https://github.com/jnsebgosselin/inrs-rsesq/blob/master/rsesq-data/rsesq_dist_stns_climate_hydro.py_


# 3 License

Copyright 2017 Jean-Sébastien Gosselin. All Rights Reserved.

email: jean-sebastien.gosselin@ete.inrs.ca

This is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
[GNU General Public License](http://www.gnu.org/licenses/) for more details.
