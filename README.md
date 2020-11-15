Elefix is a library to set elevation data to a list of latitude-longitude pairs. It also contains the scripts used to tune and evaluate the smoothing algorithm parameters. 


# Elefix library

In order to use this library you only need the following function:

```python
set_altitudes(lats: List[float], lons: List[float], smooth: bool=True, window: int=151, polynom: int=2) -> List[float]
```

- `lats` and `lons` are the latitudes and longitudes.
- If `smooth` is `False` the altitudes will be the originals retrieved from the SRTM digital elevation model. If `True` the SRTM altitudes are smoothed with Savitzky-Golay filter.
- `window` and `polynom` are the filter's parameters. The defaults are optimized for mountain biking tracks.


# Tuning the smoothing parameters

I described the experiment I used to tune the parameters in this article (in process). The scripts to train and test the parameters are included in `evaluation/`.


# SRTM data

This library needs the SRTM database in binary format. In the directory `bin/` You will find the utility script `srtm_asc_to_bin.py` which helps you convert the ASCII database to the required format.

You can download the SRTM data from here: [http://srtm.csi.cgiar.org/srtmdata]()


# More details

In this article I explain all the details of the project, from the motivation to the results and accuracy of the resulting altitude data.

(in process)


# Contact

Zuhaitz Beloki \<zbeloki@gmail.com\>
