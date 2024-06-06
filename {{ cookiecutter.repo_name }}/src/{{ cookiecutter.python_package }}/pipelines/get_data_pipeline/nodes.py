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

# TODO: How in-depth do these docstrings need to be?
def get_videos(playlist_id: str, api_key: str) -> List[str]:
    """
    Pull all the video ids from a playlist
    """

    import requests

    request_header = "https://www.googleapis.com/youtube/v3/playlistItems?playlistId={}&key={}&maxResults=50&part=contentDetails"
    data = requests.get(request_header.format(playlist_id, api_key)).json()
    return [i['contentDetails']['videoId'] for i in data['items']]

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
    # import logger
    from .nodes import pull_video_data
    from datetime import datetime
    current_time = datetime.now()

    video_statistics, video_metadata = [], {}
    for id in videos:
        items = _pull_video_data(id, api_key)["items"][0]
        video_stats = items["statistics"]
        video_stats["as_of_datetime"] = current_time
        video_stats["video_id"] = id

        video_metadata[id] = {}
        video_metadata[id]["publishedAt"] = items["snippet"]["publishedAt"]
        video_metadata[id]["channelId"] = items["snippet"]["channelId"]
        video_metadata[id]["title"] = items["snippet"]["title"]
        video_metadata[id]["description"] = items["snippet"]["description"]
        video_metadata[id]["categoryId"] = items["snippet"]["categoryId"]
        video_metadata[id]["channelTitle"] = items["snippet"]["channelTitle"]
        video_metadata[id]["tags"] = ", ".join(items["snippet"].get("tags", []))
        video_metadata[id]["duration"] = items["contentDetails"]["duration"]
        video_metadata[id]["madeForKids"] = items["status"]["madeForKids"]

        video_statistics.append(video_stats)
        # logger.info(f"""Pulled Youtube Metadata on {items['snippet']['title']}""")
    
    return video_metadata

def compile_timeseries_data(videos: List[str], api_key: str) -> pd.DataFrame:
    """
    Run the Youtube API on a list of videos to extract view statistics and metadata
    """
    # import logger
    # from .nodes import _pull_video_data
    from datetime import datetime
    current_time = datetime.now()

    video_statistics = []
    for id in videos:
        items = _pull_video_data(id, api_key)["items"][0]
        video_stats = items["statistics"]
        video_stats["as_of_datetime"] = current_time
        video_stats["video_id"] = id

        video_statistics.append(video_stats)
        # logger.info(f"""Pulled Youtube Time Series Data on {items['snippet']['title']}""")
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
    dr.Client(token=token, endpoint=endpoint)
    dataset_token = get_hash(name, data_frame, use_cases, **kwargs)
    dataset_id = _check_if_dataset_exists(name)

    if dataset_id is None:
        dataset: Dataset = Dataset.create_from_in_memory_data(
            data_frame=data_frame, use_cases=use_cases
        )
        dataset.modify(name=f"{name} [{dataset_token}]")