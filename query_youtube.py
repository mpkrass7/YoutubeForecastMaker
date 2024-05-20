import datetime as dt
from typing import Any, Dict, List, Tuple

import datarobot as dr
from logzero import logger
import requests
import pandas as pd
import yaml


def _metadata_to_dataframe(metadata: dict):
        metadata_keys = list(metadata.keys())
        listify_metadata = []
        for key in metadata_keys:
            info = metadata[key]
            info["video_id"] = key
            listify_metadata.append(info)
        df = pd.DataFrame(listify_metadata).rename(
            columns={"publishedAt": "DATEPUBLISHED"}
        )

        df.columns = [
            "DATE_PUBLISHED",
            "CHANNEL_ID",
            "TITLE",
            "DESCRIPTION",
            "CATEGORY_ID",
            "CHANNEL_TITLE",
            "TAGS",
            "DURATION",
            "MADE_FOR_KIDS",
            "VIDEO_ID",
        ]
        df["DATE_PUBLISHED"] = pd.to_datetime(df["DATE_PUBLISHED"]).astype(str).str[:19]
        return df


def get_videos(playlist_id: str, api_key: str) -> List[str]:
    """
    Pull all the video ids from a playlist
    """
    request_header = "https://www.googleapis.com/youtube/v3/playlistItems?playlistId={}&key={}&maxResults=50&part=contentDetails"
    data = requests.get(request_header.format(playlist_id, api_key)).json()
    return [i['contentDetails']['videoId'] for i in data['items']]


def pull_video_data(video_id: str, api_key: str) -> Dict[str, Any]:
    """
    Pulls data from the Youtube API for a given video id
    """
    request_header = "https://www.googleapis.com/youtube/v3/videos?id={}&key={}&fields=items(id,snippet(publishedAt,channelId,title,description,categoryId,channelTitle, tags),statistics(viewCount,likeCount,commentCount),contentDetails,status)&part=snippet,statistics,contentDetails,Status"
    
    data = requests.get(request_header.format(video_id, api_key)).json()

    return data


def compile_data(videos: List[str], api_key: str, current_hour: dt.datetime) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Run the Youtube API on a list of videos to extract view statistics and metadata
    """
    video_statistics, video_metadata = [], {}
    for id in videos:
        items = pull_video_data(id, api_key)["items"][0]
        video_stats = items["statistics"]
        video_stats["as_of_datetime"] = current_hour
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
        logger.info(f"""Pulled Youtube Metadata on {items['snippet']['title']}""")

    stats_data = {"as_of_date": current_hour, "data": video_statistics}
    return stats_data, video_metadata


def convert_to_dataframe(stats: Dict[str, Any], metadata: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    This function converts the data from the json files into a dataframe so that they can be written to snowflake
    """
    stats_dataframe = pd.DataFrame(stats["data"])

    stats_dataframe.columns = [
        "VIEW_COUNT",
        "LIKE_COUNT",
        "COMMENT_COUNT",
        "AS_OF_DATE",
        "VIDEO_ID",
    ]
    stats_dataframe["AS_OF_DATE"] = pd.to_datetime(
        stats_dataframe["AS_OF_DATE"]
    ).astype(str)

    metadata_dataframe = _metadata_to_dataframe(metadata)
    return stats_dataframe, metadata_dataframe