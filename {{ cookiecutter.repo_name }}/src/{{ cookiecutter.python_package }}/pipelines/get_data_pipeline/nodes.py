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

# TODO: How in-depth do these docstrings need to be?
def get_videos(playlist_ids: List[str], api_key: str) -> List[str]:
    """
    Pull all the video ids from a playlist
    """
    import requests

    request_header = "https://www.googleapis.com/youtube/v3/playlistItems?playlistId={}&key={}&maxResults=50&part=contentDetails"
    data = []
    for playlist_id in playlist_ids:
        datum = requests.get(request_header.format(playlist_id, api_key)).json()
        data += [i['contentDetails']['videoId'] for i in datum['items']]
    return data

def _pull_video_data(video_id: str, api_key: str) -> Dict[str, Any]:
    """
    Pulls data from the Youtube API for a given video id
    """

    import requests #TODO: should I do "from requests import get" instead?

    request_header = "https://www.googleapis.com/youtube/v3/videos?id={}&key={}&fields=items(id,snippet(publishedAt,channelId,title,description,categoryId,channelTitle, tags),statistics(viewCount,likeCount,commentCount),contentDetails,status)&part=snippet,statistics,contentDetails,Status"
    data = requests.get(request_header.format(video_id, api_key)).json()

    return data

def compile_metadata(videos: List[str], api_key: str) -> pd.DataFrame:
    """
    Run the Youtube API on a list of videos to extract view statistics and metadata
    """
    from logzero import logger

    video_metadata = []
    for id in videos:
        try:
            items = _pull_video_data(id, api_key)["items"][0]

            video_metadata.append({
                "video_id": id,
                "publishedAt": items["snippet"]["publishedAt"],
                "channelId": items["snippet"]["channelId"],
                "title": items["snippet"]["title"],
                "description": items["snippet"]["description"],
                "categoryId": items["snippet"]["categoryId"],
                "channelTitle": items["snippet"]["channelTitle"],
                "tags": ", ".join(items["snippet"].get("tags", [])),
                "duration": items["contentDetails"]["duration"],
                "madeForKids": items["status"]["madeForKids"]
            })

            logger.info(f"""Pulled Youtube Metadata on {items['snippet']['title']}""")
        except IndexError as e:
            print(e, "video with ID", id, "is not available")
            continue
        
    return pd.DataFrame(video_metadata)

def compile_timeseries_data(videos: List[str], api_key: str) -> pd.DataFrame:
    """
    Run the Youtube API on a list of videos to extract view statistics and metadata
    """
    from datetime import datetime
    from logzero import logger
    import pytz

    # It's important to ensure consistency by adding in a timezone.
    timezone = pytz.timezone('America/New_York')
    current_time = pd.to_datetime(datetime.now(tz=timezone).strftime('%Y-%m-%d %H:%M:%S'))
    minutes = current_time.minute
    if minutes < 15:
        current_time = current_time.replace(minute=0, second=0, microsecond=0)
    elif minutes < 45:
        current_time = current_time.replace(minute=30, second=0, microsecond=0)
    else:
        current_time = (current_time + pd.Timedelta(minutes=(60 - minutes))).replace(minute=0, second=0, microsecond=0)
    
    video_statistics = []
    for id in videos:
        try:
            items = _pull_video_data(id, api_key)["items"][0]

            video_stats = items["statistics"]
            video_stats["as_of_datetime"] = current_time
            video_stats["video_id"] = id

            video_statistics.append(video_stats)

            logger.info(f"""Pulled Youtube Time Series Data on {items['snippet']['title']}""")
        except IndexError as e:
            print(e, "video with ID", id, "is not available")
            continue

    return pd.DataFrame(video_statistics)

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
    
    # return str(dataset.id)

def update_or_create_metadataset(
        name: str, 
        data_frame: pd.DataFrame, 
        use_cases: Optional[UseCaseLike] = None, 
) -> None:
    """
    """
    dataset_id = _check_if_dataset_exists(name)

    if dataset_id is None:
        dataset: Dataset = Dataset.create_from_in_memory_data(
            data_frame=data_frame, use_cases=use_cases
        )
        dataset.modify(name=f"{name}")        
    
    # return str(dataset.id)

def create_modeling_dataset(combined_dataset_name: str, #TODO: change 'combined' to modeling or something
                                 metadataset_id: str, 
                                 timeseries_data: pd.DataFrame,
                                 use_cases: Optional[UseCaseLike] = None) -> None:
    """Prepare a dataset for modeling in DataRobot.
    
    Parameters
    ----------
    metadata : pd.DataFrame
        The raw metadata dataset to combine with timeseries data for modeling
    timeseries_data: pd.DataFrame
        The raw timeseries dataset to combine with metadata for modeling
    Returns
    -------
    str
        ID of the dataset prepared for modeling in DataRobot
    """
    # TODO: Should it return a dr.Dataset?
    # TODO: can I join datasets as dr.Datasets?
    # TODO: Should be uniform in terms of what I pass in for each dataframe (id, id OR name, name)
    metadata_df = dr.Dataset.get(metadataset_id).get_as_dataframe()

    # Join the metadata and timeseries data on the Video ID
    new_data = pd.merge(metadata_df, timeseries_data, on="video_id", how="inner").reset_index(drop=True)
    new_data["viewDiff"] = 0
    new_data["likeDiff"] = 0
    new_data["commentDiff"] = 0

    combined_dataset_id = _check_if_dataset_exists(combined_dataset_name)

    # TODO: Should this be idempotent? (use hash?)
    if combined_dataset_id is None:
        dataset: Dataset = Dataset.create_from_in_memory_data(
            data_frame=new_data, use_cases=use_cases
        )
        dataset.modify(name=f"{combined_dataset_name}")
    else:
        current_modeling_data = dr.Dataset.get(combined_dataset_id).get_as_dataframe()

        staging_data = pd.concat([current_modeling_data, new_data]).reset_index(drop=True)

        # Calculate the difference in viewCount from the previous hour for each entry
        #   for the first entry, it remains NaN?
        staging_data['as_of_datetime'] = pd.to_datetime(staging_data['as_of_datetime'], errors='coerce')
        staging_data = staging_data.sort_values(['video_id', 'as_of_datetime'])

        staging_data['viewDiff'] = staging_data.groupby('video_id')['viewCount'].diff()
        staging_data['likeDiff'] = staging_data.groupby('video_id')['likeCount'].diff()
        staging_data['commentDiff'] = staging_data.groupby('video_id')['commentCount'].diff()

        staging_data = staging_data.sort_values(by=["viewCount", "video_id"])

        dr.Dataset.create_version_from_in_memory_data(combined_dataset_id, staging_data)
