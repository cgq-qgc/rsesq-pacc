# rsesq
Réseau de Suivi des Eaux Souterraines du Québec

----

## API to download and format groundwater level data
(http://www.mddelcc.gouv.qc.ca/eau/piezo/)

```python
from read_mddelcc_rses import MDDELCC_RSESQ_Reader
import os

dirname = os.path.join(os.getcwd(), 'water_level')

reader = MDDELCC_RSESQ_Reader()
for station in reader.stations():
    filename = "%s (%s).csv" % (station['Name'], station['ID'])
    filepath = os.path.join(dirname, filename)
    reader.save_station_to_csv(station['ID'], filepath)
```
