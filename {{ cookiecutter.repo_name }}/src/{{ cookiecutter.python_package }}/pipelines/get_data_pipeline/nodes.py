# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from typing import List, Dict, Any, Tuple, Union, Optional
import datarobot as dr
import pandas as pd


#TODO: delete these imports, well, not now 
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

# TODO: Making a change to this... it's too fragmented right now.
#   I think it makes sense to download and export to df in 1 function?
# TODO: bake into product?
def compile_metadata(videos: List[str], api_key: str) -> pd.DataFrame:
    """
    Run the Youtube API on a list of videos to extract view statistics and metadata
    """
    from logzero import logger

    video_metadata = []
    for id in videos:
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
        
    return pd.DataFrame(video_metadata)

def compile_timeseries_data(videos: List[str], api_key: str) -> pd.DataFrame:
    """
    Run the Youtube API on a list of videos to extract view statistics and metadata
    """
    # import logger
    # from .nodes import _pull_video_data
    from datetime import datetime
    from logzero import logger
    import pytz

    timezone = pytz.timezone('America/New_York')
    current_time = datetime.now(tz=timezone).strftime('%Y-%m-%d %H:%M')
    
    video_statistics = []
    for id in videos:
        items = _pull_video_data(id, api_key)["items"][0]
        video_stats = items["statistics"]
        video_stats["as_of_datetime"] = current_time
        video_stats["video_id"] = id

        video_statistics.append(video_stats)
        logger.info(f"""Pulled Youtube Time Series Data on {items['snippet']['title']}""")
    stats_data = pd.DataFrame(video_statistics)

    return stats_data

def _check_if_dataset_exists(name: str) -> Union[str, None]:
    """
    Check if a dataset with the given name exists in the AI Catalog
    Returns:
        id (string) or None
    """
    # TODO: May need to make a Client object?
    # 
    datasets = dr.Dataset.list()
    return next((dataset.id for dataset in datasets if dataset.name == name), None)

def _write_new_dataset_to_catalog(df: pd.DataFrame, dataset_name, client) -> str:
    """
    Write the metadata and stats dataframes to the AI Catalog
    """
    from logzero import logger

    dr_url = client.endpoint.split("/api")[0]
    catalog_id = dr.Dataset.create_from_in_memory_data(df, fname=dataset_name).id
    logger.info(f"Dataset {dataset_name} created: {dr_url + '/' + catalog_id}")
    return catalog_id

# TODO: update this (see notes from Marshall huddle) such that it doesn't upload new version of dataset
#   
def update_or_create_dataset(
        endpoint: str,
        token: str,
        name: str, 
        data_frame: pd.DataFrame, 
        use_cases: Optional[UseCaseLike] = None, #TODO: why is this plural and what do you put in here?
        **kwargs: Any,
) -> str:
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
        date_column = pd.to_datetime(current_data["as_of_datetime"])
        latest_time_pulled = date_column.max()
        time_pulled_this_df = pd.to_datetime(data_frame["as_of_datetime"]).max()
        print(time_pulled_this_df, "current time pulled")
        print(abs(latest_time_pulled - time_pulled_this_df), "\n\n")
        if abs(latest_time_pulled - time_pulled_this_df) <= timedelta(hours=0.5):
            print("returning\n\n")
            return
        else:
            # update dataset if time is greater than 2 hours
            updated_df = pd.concat([current_data, data_frame]).reset_index(drop=True)
            dr.Dataset.create_version_from_in_memory_data(dataset_id, updated_df)
            # _write_new_dataset_to_catalog(updated_df, dataset_name=name, client=CLIENT)


def combine_video_ids(
        list1: List[str],
        list2: List[str]
) -> List[str]:
    """
    """
    return list1 + list2

def _find_existing_dataset(
    timeout_secs: int, dataset_name: str, use_cases: Optional[UseCaseLike] = None
) -> str:
    for dataset in Dataset.list(use_cases=use_cases):
        if dataset_name in dataset.name:
            waited_secs = 0
            while True:
                status = Dataset.get(dataset.id).processing_state
                if status == "COMPLETED":
                    return str(dataset.id)
                elif status == "ERROR":
                    break
                elif waited_secs > timeout_secs:
                    raise TimeoutError("Timed out waiting for dataset to process.")
                time.sleep(3)
                waited_secs += 3

    raise KeyError("No matching dataset found")


def create_modeling_dataset(combined_dataset_name: str,
                                 metadataset_name: str, 
                                 timeseries_dataset_name: str,
                                 use_cases: Optional[UseCaseLike] = None) -> str:
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
    """#TODO: Should it return a dr.Dataset?
    # Join the metadata and timeseries data on the Video ID
    # TODO: can I join datasets as dr.Datasets?
    metadata_id = _find_existing_dataset(timeout_secs=30, dataset_name=metadataset_name, use_cases=use_cases)
    metadata_df = dr.Dataset.get(metadata_id).get_as_dataframe()

    timeseries_id = _find_existing_dataset(timeout_secs=30, dataset_name=timeseries_dataset_name, use_cases=use_cases)
    timeseries_df = dr.Dataset.get(timeseries_id).get_as_dataframe()

    new_data = pd.merge(metadata_df, timeseries_df, on="video_id", how="inner")

    combined_dataset_id = _check_if_dataset_exists(combined_dataset_name)

    # TODO: Should this be idempotent? (use hash?)
    if combined_dataset_id is None:
        dataset: Dataset = Dataset.create_from_in_memory_data(
            data_frame=new_data, use_cases=use_cases
        )
        dataset.modify(name=f"{combined_dataset_name}")
    else:
        current_data = dr.Dataset.get(combined_dataset_id).get_as_dataframe()
        updated_df = pd.concat([current_data, new_data]).reset_index(drop=True)
        dr.Dataset.create_version_from_in_memory_data(combined_dataset_id, updated_df)
    # dataset = dr.Dataset.create_from_in_memory_data(data_frame=data, use_cases=use_cases)

    return dataset
