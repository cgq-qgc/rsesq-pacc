# 1. Feuilles de route

Tous les documents en lien avec la planification et le suivi de l'avancement du projet sont rendu disponibles dans le répertoire [inrs-rsesq/roadmap](https://github.com/jnsebgosselin/inrs-rsesq/tree/master/roadmap). Le fichier [gantt_chart_projet_inrs_rsesq.xml](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/roadmap/gantt_chart_projet_inrs_rsesq.xml) contient la feuille de route complète du projet et peut être consulté à l'aide du logiciel open source [GanttProject](http://www.ganttproject.biz/). Cette feuille de route est mise à jour en continue selon l'évolution du projet. Des rapports de suivi de l'avancement du projet en format pdf sont également produits sur une base hebdomadaires et sont disponibles dans le dossier [progress report](https://github.com/jnsebgosselin/inrs-rsesq/tree/master/roadmap/progress%20reports).

De plus, la majorité des tâches qui apparaissent dans la planification du projet sont logguées dans les [Issues](https://github.com/jnsebgosselin/inrs-rsesq/issues) de ce répertoire GitHub où il est possible de commenter et proposer de nouvelles idées pour le projet.

![Gantt diagram screenshot](https://github.com/jnsebgosselin/inrs-rsesq/blob/master/roadmap/gantt_chart_scs.png)
_Figure: Diagramme de Gantt du projet tel que vu dans [GanttProject](http://www.ganttproject.biz/)(produit le 16/10/2017)_

# 2. rsesq-data: collecte et mise en forme des données

Outils développés à l'[INRS centre Eau-Terre-Environnement](http://www.ete.inrs.ca/) pour récupérer et mettre en forme automatiquement les données temporelles piézométriques, hydrométriques et climatiques qui sont rendues disponibles gratuitement par le [Ministère du Développement Durable, de l'Environnement et de la Lutte contre les Changements Climatiques](http://www.mddelcc.gouv.qc.ca/) du Québec et par [Environnement et Changement climatique Canada](https://www.ec.gc.ca/default.asp?lang=Fr).

## 2.1. API pour télécharger les données du [RSESQ du MDDELCC](http://www.mddelcc.gouv.qc.ca/eau/piezo/)

```python
from read_mddelcc_rses import MDDELCC_RSESQ_Reader
import os

dirname = os.path.join(os.getcwd(), 'water_level')

reader = MDDELCC_RSESQ_Reader()
for station in reader.stations():
    filename = "%s (%s).csv" % (station['Name'], station['ID'])
    reader.save_station_to_csv(station['ID'], os.path.join(dirname, filename))
```

## 2.2. API pour télécharger les données climatiques d'[Environnement et Changement climatique Canada](http://climate.weather.gc.ca/historical_data/search_historic_data_e.html)

À venir...

## 2.3. API pour récupérer les données hydrométriques de la base de données [HYDAT](https://ec.gc.ca/rhc-wsc/default.asp?lang=En&n=9018B5EC-1)

À venir...
