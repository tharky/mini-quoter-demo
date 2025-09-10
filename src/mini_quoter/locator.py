from importlib.resources import files
import pandas as pd
import numpy as np
import pgeocode

def find_nearest_station(sqft, zipcode, usd_per_therm, usd_per_kwh):
  # Get location info from zip using pgeocode
    nominatim = pgeocode.Nominatim('us')
    zip_rec = nominatim.query_postal_code(zipcode)
    if pd.isna(zip_rec.latitude) or pd.isna(zip_rec.longitude):
        raise ValueError("Invalid ZIP code")

    zip_lat = float(zip_rec.latitude)
    zip_lon = float(zip_rec.longitude)
    zip_city = str(zip_rec.place_name)
    zip_state = str(zip_rec.state_code)

    # Load climate data from stations
    csv_path = files("mini_quoter").joinpath("data/noaa_hdd_cdd_allstations.csv")
    with csv_path.open("rb") as f:
      climate = pd.read_csv(f)
    lats = climate["LATITUDE"].to_numpy(dtype=float)
    lons = climate["LONGITUDE"].to_numpy(dtype=float)

    # Earth's radius in miles
    R_miles = 3958.7613
    # Convert degrees to radians for trig functions
    lat1 = np.radians(zip_lat)
    lon1 = np.radians(zip_lon)
    lat2 = np.radians(lats)
    lon2 = np.radians(lons)

    # subtract difference of zipcode lat/long from stations lat/long
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula: look at north/south difference and east/west difference and get how far apart the stations vs the zipcode are.
    a = np.sin(dlat/2.0)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2.0)**2
    # Convert to radian value and multiply by earths radius to get distance in miles
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    dist_mi = R_miles * c

    # Pick nearest station (minimum distance)
    idx = int(np.argmin(dist_mi))
    rec = climate.iloc[idx]

    # Pull information from the station and return detailed data on location and climate
    location_name = f"{zip_city}, {zip_state}"
    HDD65 = float(rec["HDD65"])
    CDD65 = float(rec["CDD65"])
    nearest_station =  rec['NAME']
    return {
        'Name': location_name,
        'City': zip_city,
        'State': zip_state,
        'HDD65': HDD65,
        'CDD65': CDD65,
        'Nearest Station':  nearest_station
    }

