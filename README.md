# rsesq-data

Outils développés à l'[INRS centre Eau-Terre-Environnement](http://www.ete.inrs.ca/) pour récupérer et mettre en forme automatiquement les données temporelles piézométriques, hydrométriques et climatiques qui sont rendues disponibles gratuitement par le [Ministère du Développement Durable, de l'Environnement et de la Lutte contre les Changements Climatiques](http://www.mddelcc.gouv.qc.ca/) du Québec et par [Environnement et Changement climatique Canada](https://www.ec.gc.ca/default.asp?lang=Fr).

## API pour télécharger les données du [RSESQ du MDDELCC](http://www.mddelcc.gouv.qc.ca/eau/piezo/)

```python
from read_mddelcc_rses import MDDELCC_RSESQ_Reader
import os

dirname = os.path.join(os.getcwd(), 'water_level')

reader = MDDELCC_RSESQ_Reader()
for station in reader.stations():
    filename = "%s (%s).csv" % (station['Name'], station['ID'])
    reader.save_station_to_csv(station['ID'], os.path.join(dirname, filename))
```

## API pour télécharger les données climatiques d'[Environnement et Changement climatique Canada](http://climate.weather.gc.ca/historical_data/search_historic_data_e.html)

À venir...

## API pour récupérer les données hydrométriques de la base de données [HYDAT](https://ec.gc.ca/rhc-wsc/default.asp?lang=En&n=9018B5EC-1)

À venir...
