import datetime
import subprocess
import pathlib
import json
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

def get_temp(filepath: pathlib.Path, latitude: float, longitude:float) -> tuple[float, float]:
    """Get the temperature for a given image file using historical data from Open-Meteo"""
    # Extract the date from the image metadata
    out = json.loads(subprocess.check_output(["exiftool", "-j", "-DateTimeOriginal", str(filepath)]))
    raw_date = out[0]["DateTimeOriginal"]
    date_created = datetime.datetime.strptime(raw_date, "%Y:%m:%d %H:%M:%S.%f%z")
    print(f"Date created:\t{date_created}")

    # Set up the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Make sure to list all required weather variables are listed here
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": date_created.strftime("%Y-%m-%d"),
        "end_date": date_created.strftime("%Y-%m-%d"),
        "hourly": ["temperature_2m", "relative_humidity_2m"],
        "timezone": "America/Los_Angeles",
    }
    responses = openmeteo.weather_api(url, params=params)

    # Get the first (only) location
    response = responses[0]

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
    hourly_data = {"date": pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    ), "temperature_2m": hourly_temperature_2m, "relative_humidity_2m": relative_humidity_2m}

    hourly_dataframe = pd.DataFrame(data=hourly_data)
    hourly_dataframe["date"] = hourly_dataframe["date"].dt.tz_convert(date_created.tzinfo)

    # Find the row whose hour matches the photo's local hour
    photo_hour = date_created.replace(minute=0, second=0, microsecond=0)
    row = hourly_dataframe[hourly_dataframe["date"] == photo_hour]

    # Grab the desired info and return it
    found_temp = float(row["temperature_2m"].iloc[0])
    found_rh = float(row["relative_humidity_2m"].iloc[0])
    return found_temp, found_rh