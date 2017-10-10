# rsesq-data

Tools developped at [INRS centre Eau-Terre-Environnement](http://www.ete.inrs.ca/) for collecting and formating groundwater level, hydrometric data, and weather data that are made freely available by the [Ministry of Sustainable Development, Environment, and Action against Climate Change ](http://www.mddelcc.gouv.qc.ca/) of the Province of Quebec and by [Environment and Climate Change Canada](https://ec.gc.ca/default.asp?lang=en&n=FD9B0E51-1).

## API to download groundwater level data from the [MDDELCC](http://www.mddelcc.gouv.qc.ca/eau/piezo/) website

```python
from read_mddelcc_rses import MDDELCC_RSESQ_Reader
import os

dirname = os.path.join(os.getcwd(), 'water_level')

reader = MDDELCC_RSESQ_Reader()
for station in reader.stations():
    filename = "%s (%s).csv" % (station['Name'], station['ID'])
    reader.save_station_to_csv(station['ID'], os.path.join(dirname, filename))
```
