# Table des Matières

1. [Feuille de route](#1-feuille-de-route)
2. [Collecte et mise en forme des données](#2-collecte-et-mise-en-forme-des-données)<br />
    2.1. API pour télécharger les données du RSESQ du MDDELCC<br />
    2.2. API pour télécharger les données climatiques d'Environnement et Changement climatique Canada<br />
    2.3 API pour récupérer les données hydrométriques du CEHQ<br />
3. [License](#3-license)

# 1 Feuille de route

Tous les documents en lien avec la planification et le suivi de l'avancement du projet sont rendus disponibles dans le répertoire [inrs-rsesq/roadmap](https://github.com/jnsebgosselin/inrs-rsesq/tree/master/roadmap). Le fichier [gantt_chart_projet_inrs_rsesq.xml](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/roadmap/gantt_chart_projet_inrs_rsesq.xml) contient la feuille de route complète du projet et peut être consulté à l'aide du logiciel open source [GanttProject](http://www.ganttproject.biz/). Cette feuille de route est mise à jour en continue selon l'évolution du projet. Des rapports de suivi de l'avancement du projet en format pdf sont également produits sur une base hebdomadaire et sont disponibles dans le dossier [progress report](https://github.com/jnsebgosselin/inrs-rsesq/tree/master/roadmap/progress%20reports).

De plus, la majorité des tâches qui apparaissent dans la planification du projet sont répertoriées dans les [Issues](https://github.com/jnsebgosselin/inrs-rsesq/issues) de ce répertoire GitHub où il est possible de commenter et proposer de nouvelles idées pour le projet.

![Gantt diagram screenshot](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/roadmap/gantt_chart_scs.png)
_Figure: Diagramme de Gantt du projet tel que vu dans [GanttProject](http://www.ganttproject.biz/)(produit le 16/10/2017)_

# 2 Collecte et mise en forme des données

Outils développés à l'[INRS centre Eau-Terre-Environnement](http://www.ete.inrs.ca/) pour récupérer et mettre en forme automatiquement les données temporelles piézométriques, hydrométriques et climatiques qui sont rendues disponibles gratuitement par le [Ministère du Développement Durable, de l'Environnement et de la Lutte contre les Changements Climatiques](http://www.mddelcc.gouv.qc.ca/) du Québec et par [Environnement et Changement climatique Canada](https://www.ec.gc.ca/default.asp?lang=Fr).

## 2.1 API pour télécharger les données du [RSESQ du MDDELCC](http://www.mddelcc.gouv.qc.ca/eau/piezo/)

```python
from read_mddelcc_rses import MDDELCC_RSESQ_Reader
import os

dirname = os.path.join(os.getcwd(), 'data_files', 'water_level')

reader = MDDELCC_RSESQ_Reader()
for station in reader.stations():
    filename = "%s (%s).csv" % (station['Name'], station['ID'])
    reader.save_station_to_csv(station['ID'], os.path.join(dirname, filename))
```

## 2.2 API pour télécharger les données climatiques d'[Environnement et Changement climatique Canada](http://climate.weather.gc.ca/historical_data/search_historic_data_e.html)

À venir...

## 2.3 API pour récupérer les données hydrométriques du [CEHQ](https://www.cehq.gouv.qc.ca/)
https://www.cehq.gouv.qc.ca/hydrometrie/historique_donnees/default.asp

```python
import os
from numpy import min, max
from read_mddelcc_cehq import MDDELCC_CEHQ_Reader

dirname = os.path.join(os.getcwd(), 'data_files', 'streamflow_and_level')

reader = MDDELCC_CEHQ_Reader()
for i, sid in enumerate(reader.station_ids()):
    args = (sid, i+1, len(reader.station_ids()))
    print('Saving data for station %s: %d of %d' % args, end='\r')
    
    data = reader._db[sid]
    filename = "%s_%d-%d.csv" % (sid, min(data['Year']), max(data['Year']))
    filepath = os.path.join(dirname, filename)
    reader.save_station_to_csv(sid, filepath)
```

La première fois que `MDDELCC_CEHQ_Reader` est initialisé, la base de données hydrométriques complète sera téléchargée du site web du CEHQ et sera sauvegardée sur le disque en format binaire dans le fichier `mddelcc_cehq_stations.npy`. Les initialisations subséquentes de `MDDELCC_CEHQ_Reader` accéderont les données à partir de ce fichier.

Pour mettre à jour la base de données locale à partir de celle du CEHQ, simplement lancer:

```python
reader = MDDELCC_CEHQ_Reader()
reader.fetch_database_from_mddelcc()
```

Pour mettre à jour les données d'une station en particulier, par exemple la station '022513':
```python
reader = MDDELCC_CEHQ_Reader()
reader.fetch_station_data('022513')
```

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
