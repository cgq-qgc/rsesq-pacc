# Table des Matières

1. [Feuille de route](#1-feuille-de-route)
2. [Collecte et mise en forme des données](#2-collecte-et-mise-en-forme-des-données)<br />
    2.1. [API pour télécharger les données du RSESQ du MDDELCC](#21-api-pour-télécharger-les-données-du-rsesq-du-mddelcc)<br />
    2.2. [API pour télécharger les données climatiques d'Environnement et Changement climatique Canada](#22-api-pour-télécharger-les-données-climatiques-denvironnement-et-changement-climatique-canada)<br />
    2.3. [API pour récupérer les données hydrométriques du CEHQ](#23-api-pour-récupérer-les-données-hydrométriques-du-cehq)<br />
3. [License](#3-license)

# 1 Feuille de route

Tous les documents en lien avec la planification et le suivi de l'avancement du projet sont rendus disponibles dans le répertoire [inrs-rsesq/roadmap](https://github.com/jnsebgosselin/inrs-rsesq/tree/master/roadmap). Le fichier [gantt_chart_projet_inrs_rsesq.xml](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/roadmap/gantt_chart_projet_inrs_rsesq.xml) contient la feuille de route complète du projet et peut être consulté à l'aide du logiciel open source [GanttProject](http://www.ganttproject.biz/). Cette feuille de route est mise à jour en continue selon l'évolution du projet. Des rapports de suivi de l'avancement du projet en format pdf sont également produits sur une base hebdomadaire et sont disponibles dans le dossier [progress report](https://github.com/jnsebgosselin/inrs-rsesq/tree/master/roadmap/progress%20reports).

De plus, la majorité des tâches qui apparaissent dans la planification du projet sont répertoriées dans les [Issues](https://github.com/jnsebgosselin/inrs-rsesq/issues) de ce répertoire GitHub où il est possible de commenter et proposer de nouvelles idées pour le projet.

![Gantt diagram screenshot](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/roadmap/gantt_chart_scs.png)
_Figure: Diagramme de Gantt du projet tel que vu dans [GanttProject](http://www.ganttproject.biz/)(produit le 16/10/2017)_

# 2 Collecte et mise en forme des données

Outils développés à l'[INRS centre Eau-Terre-Environnement](http://www.ete.inrs.ca/) pour récupérer et mettre en forme automatiquement les données temporelles piézométriques, hydrométriques et climatiques qui sont rendues disponibles gratuitement par le [Ministère du Développement Durable, de l'Environnement et de la Lutte contre les Changements Climatiques](http://www.mddelcc.gouv.qc.ca/) du Québec et par [Environnement et Changement climatique Canada](https://www.ec.gc.ca/default.asp?lang=Fr).

## 2.1 API pour télécharger les données du RSESQ du MDDELCC
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

## 2.2 API pour télécharger les données climatiques d'Environnement et Changement climatique Canada
http://climate.weather.gc.ca/historical_data/search_historic_data_e.html

Le script ci-dessous montre comment il est possible d'utiliser l'API pour télécharger, formatter et sauvegarder dans un fichier csv les données climatiques journalières de toutes les stations climatiques actives d'Environnement Canada localisées au Québec.


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

Le logiciel [WHAT](https://github.com/jnsebgosselin/what), qui est développé dans le cadre de ce projet, permet également de télécharger les données climatiques et de combler les données manquantes à partir d'une interface graphique.

## 2.3 API pour récupérer les données hydrométriques du CEHQ
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
