# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from typing import List, Dict, Any, Tuple, Union, Optional
import datarobot as dr
import pandas as pd

from datarobot import Dataset
from datarobot.models.use_cases.utils import UseCaseLike
from datarobotx.idp.common.hashing import get_hash
import time

def get_historical_city_data(
        locations: List[Dict[str, float]], 
        parameters: Dict[str, Any]
) -> pd.DataFrame:
    """
    Pull all the video ids from a playlist
    """
    import openmeteo_requests

    import requests_cache
    import pandas as pd
    from retry_requests import retry
    import datetime
    import pytz

    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"

    latitudes = [locations[city]["Latitude"] for city in locations]
    longitudes = [locations[city]["Longitude"] for city in locations]
    city_names = list(locations.keys())

    parameters["past_days"] = 90 # Set to past 3 months to get some historical data.
    parameters["latitude"] = latitudes
    parameters["longitude"] = longitudes

    responses = openmeteo.weather_api(url, params=parameters)

    all_data = []
    for i, response in enumerate(responses):
        # TODO: Log this?
        # print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        # Print city as well
        # print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        # print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")
        

        # Process hourly data. The order of variables needs to be the same as requested.
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()        
        hourly_precipitation_probability = hourly.Variables(1).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(2).ValuesAsNumpy()
        hourly_uv_index = hourly.Variables(3).ValuesAsNumpy()

        timezone = pytz.timezone(response.Timezone())
        timestart = datetime.datetime.fromtimestamp(hourly.Time(), tz=timezone)
        timeend = datetime.datetime.fromtimestamp(hourly.TimeEnd(), tz=timezone)

        hourly_data = {
            "date": pd.date_range(
                        start = timestart,
                        end = timeend,
                        freq = pd.Timedelta(seconds = hourly.Interval()),
                        inclusive = "left"
                    ),
            "temperature": hourly_temperature_2m,
            "uv_index": hourly_uv_index,
            "precipitation_probability": hourly_precipitation_probability,
            "precipitation": hourly_precipitation,
            "elevation": response.Elevation(),
            "longitude": response.Latitude(),
            "latitude": response.Longitude(),
            "city": city_names[i]
        }
        all_data.append(pd.DataFrame(data=hourly_data))
        

    hourly_dataframe = pd.concat(all_data, ignore_index=True)
    hourly_dataframe.to_csv("Test_df.csv", index=False)
    return hourly_dataframe


def _check_if_dataset_exists(name: str) -> Union[str, None]:
    """
    Check if a dataset with the given name exists in the AI Catalog
    Returns:
        id (string) or None
    """
    datasets = dr.Dataset.list()
    return next((dataset.id for dataset in datasets if dataset.name == name), None)

def update_or_create_timeseries_dataset(
        endpoint: str,
        token: str,
        name: str, 
        data_frame: pd.DataFrame, 
        use_cases: Optional[UseCaseLike] = None,
        **kwargs: Any,
) -> None:
    """
    """
    from datetime import timedelta
    CLIENT = dr.Client(token=token, endpoint=endpoint)
    dataset_token = get_hash(name, data_frame, use_cases, **kwargs)
    dataset_id = _check_if_dataset_exists(name)

    if dataset_id is None:
        dataset: Dataset = Dataset.create_from_in_memory_data(
            data_frame=data_frame, use_cases=use_cases
        )
        dataset.modify(name=f"{name}")
    else:
        current_data = dr.Dataset.get(dataset_id).get_as_dataframe()
        latest_time_pulled = pd.to_datetime(current_data["as_of_datetime"]).max()

        time_pulled_this_df = pd.to_datetime(data_frame["as_of_datetime"]).max()

        # Guard rail to ensure that there is sufficient time between data pulls.
        if abs(latest_time_pulled - time_pulled_this_df) <= timedelta(hours=0.5):
            return name
        else:
            # update dataset if time is greater than 2 hours
            updated_df = pd.concat([current_data, data_frame]).reset_index(drop=True)
            dataset = dr.Dataset.create_version_from_in_memory_data(dataset_id, updated_df)