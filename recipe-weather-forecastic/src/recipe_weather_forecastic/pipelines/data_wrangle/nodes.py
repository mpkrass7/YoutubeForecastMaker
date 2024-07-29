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

def _check_if_dataset_exists(name: str) -> Union[str, None]:
    """
    Check if a dataset with the given name exists in the AI Catalog
    Returns:
        id (string) or None
    """
    datasets = dr.Dataset.list()
    return next((dataset.id for dataset in datasets if dataset.name == name), None)

def get_today_city_data(
        locations: List[Dict[str, float]], 
        parameters: Dict[str, Any]
) -> pd.DataFrame:
    """
    Pull all the video ids from a playlist
    """
    import openmeteo_requests

    import pandas as pd
    import datetime
    import pytz

    # Setup the Open-Meteo API client with cache and retry on error
    openmeteo = openmeteo_requests.Client()

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"

    latitudes = [locations[city]["Latitude"] for city in locations]
    longitudes = [locations[city]["Longitude"] for city in locations]
    city_names = list(locations.keys())

    parameters["past_days"] = 1 # This should be tied to when the notebook scheduled to pull
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
                    ).strftime('%Y-%m-%d %H:%M:%S'),
            "temperature": hourly_temperature_2m,
            "uv_index": hourly_uv_index,
            "precipitation_probability": hourly_precipitation_probability,
            "precipitation": hourly_precipitation,
            "elevation": response.Elevation(),
            "longitude": response.Latitude(), # make this an integer?
            "latitude": response.Longitude(), # make this an integer?
            "city": city_names[i]
        }
        all_data.append(pd.DataFrame(data=hourly_data))

    hourly_dataframe = pd.concat(all_data, ignore_index=True)
    return hourly_dataframe


# 
def create_or_update_scoring_dataset(scoring_dataset_name: str,
                                    modeling_dataset_id: str,
                                    use_cases: Optional[UseCaseLike] = None) -> None:
    """Prepare a dataset for making/scoring in DataRobot.
    
    Parameters
    ----------
    scoring_dataset_name : pd.DataFrame
        The raw metadata dataset to combine with timeseries data for modeling
    modeling_dataset_id: str
        The ID of the modeling datset which we will turn into the scoring dataset
    use_cases : UseCaseLike
        Usually the use case id to further identify dataset
    Returns
    -------
    None
    """
    modeling_df = dr.Dataset.get(modeling_dataset_id).get_as_dataframe()

    scoring_dataset_id = _check_if_dataset_exists(scoring_dataset_name)

    if scoring_dataset_id is None:
        dataset: Dataset = Dataset.create_from_in_memory_data(
            data_frame=modeling_df, use_cases=use_cases
        )
        dataset.modify(name=f"{scoring_dataset_name}")
    else:
        dr.Dataset.create_version_from_in_memory_data(scoring_dataset_id, modeling_df)


def remove_old_retraining_data(endpoint: str, 
                               token: str,
                               datasets_to_check: Dict[str, str]):
    from logzero import logger

    client = dr.Client(endpoint=endpoint, token=token)

    for dataset_name in list(datasets_to_check.values()):
        data_id = _check_if_dataset_exists(dataset_name)
        if data_id is None:
            continue

        url = f"{endpoint}/datasets/{data_id}/versions/"
        dataset_versions = client.get(url).json()

        logger.info(f"Found {dataset_versions['count']} versions of {data_id}")

        if dataset_versions['count'] > 75:
            sorted_versions = sorted(dataset_versions['data'], key=lambda x: pd.to_datetime(x['creationDate']))
            for version in sorted_versions[:-50]:
                url = f"{endpoint}/datasets/{data_id}/versions/{version['versionId']}"
                client.delete(url)
            logger.info(f"Deleted {dataset_versions['count'] - 50} versions of {data_id}")

    
    




# def create_or_update_modeling_dataset(
#     incoming_data: pd.DataFrame,
#     timeseries_data_name: str,
#     use_cases: Optional[UseCaseLike] = None
# ) -> str:
#     """Prepare a dataset for modeling in DataRobot.
    
#     Parameters
#     ----------
#     metadata : pd.DataFrame
#         The raw metadata dataset to combine with timeseries data for modeling
#     timeseries_data: pd.DataFrame
#         The raw timeseries dataset to combine with metadata for modeling
#     Returns
#     -------
#     str
#         ID of the dataset prepared for modeling in DataRobot
#     """
#     raw_ts_data = dr.Dataset.get(_check_if_dataset_exists(timeseries_data_name)).get_as_dataframe()

#     # Calculate the difference in viewCount from the previous hour for each entry
#     #   for the first entry, it remains 0
#     new_data['as_of_datetime'] = pd.to_datetime(new_data['as_of_datetime'], errors='coerce')
#     new_data = new_data.sort_values(['video_id', 'as_of_datetime'])

#     new_data = new_data.drop_duplicates(subset=["video_id", "viewCount", "as_of_datetime"])

#     new_data = new_data.groupby('video_id').apply(lambda group: group.iloc[::3]).reset_index(drop=True)

#     new_data['viewDiff'] = new_data.groupby('video_id')['viewCount'].diff()
#     new_data['likeDiff'] = new_data.groupby('video_id')['likeCount'].diff()
#     new_data['commentDiff'] = new_data.groupby('video_id')['commentCount'].diff()

#     new_data.fillna(0, inplace=True)

#     new_data["viewDiff"] = new_data["viewDiff"].apply(lambda x: max(x, 0))

#     # If it exists, add a new version, otherwise create it!
#     modeling_dataset_id = _check_if_dataset_exists(modeling_dataset_name)
   
#     if modeling_dataset_id is None:
#         dataset: Dataset = Dataset.create_from_in_memory_data(
#             data_frame=new_data, use_cases=use_cases
#         )
#         dataset.modify(name=f"{modeling_dataset_name}")
#     else:     
#         dataset = dr.Dataset.create_version_from_in_memory_data(modeling_dataset_id, new_data)

#     return str(dataset.id)
