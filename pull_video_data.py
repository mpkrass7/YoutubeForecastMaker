import datetime as dt
from typing import Any, Dict, List, Tuple

import datarobot as dr
from logzero import logger
import requests
import pandas as pd
import yaml


CONFIG_FILE = "config.yaml"

with open(CONFIG_FILE, "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

with open("credentials.yaml", "r") as f:
    credentials = yaml.load(f, Loader=yaml.FullLoader)
    YOUTUBE_API_KEY = credentials["youtube_api_key"]
    CLIENT = dr.Client(endpoint=credentials["datarobot"]["endpoint"], token=credentials["datarobot"]["api_token"])

CURRENT_HOUR = str(pd.to_datetime(dt.datetime.now()).floor("H"))

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


def get_videos(playlist_id: str) -> List[str]:
    """
    Pull all the video ids from a playlist
    """
    request_header = "https://www.googleapis.com/youtube/v3/playlistItems?playlistId={}&key={}&maxResults=50&part=contentDetails"
    data = requests.get(request_header.format(playlist_id, YOUTUBE_API_KEY)).json()
    return [i['contentDetails']['videoId'] for i in data['items']]


def pull_video_data(video_id: str) -> Dict[str, Any]:
    """
    Pulls data from the Youtube API for a given video id
    """
    request_header = "https://www.googleapis.com/youtube/v3/videos?id={}&key={}&fields=items(id,snippet(publishedAt,channelId,title,description,categoryId,channelTitle, tags),statistics(viewCount,likeCount,commentCount),contentDetails,status)&part=snippet,statistics,contentDetails,Status"
    
    data = requests.get(request_header.format(video_id, YOUTUBE_API_KEY)).json()

    return data


def compile_data(videos: List[str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Run the Youtube API on a list of videos to extract view statistics and metadata
    """
    video_statistics, video_metadata = [], {}
    for id in videos:
        items = pull_video_data(id)["items"][0]
        video_stats = items["statistics"]
        video_stats["as_of_datetime"] = CURRENT_HOUR
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
        logger.info(f"""Pulled Youtube Metadata on "{items['snippet']['title']}" """)

    stats_data = {"as_of_date": CURRENT_HOUR, "data": video_statistics}
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


def write_new_assets_to_catalog(metadata: pd.DataFrame, stats: pd.DataFrame, config: Dict[str, Any]):
    """
    Write the metadata and stats dataframes to the AI Catalog
    """

    metadata_catalog_id = dr.Dataset.create_from_in_memory_data(metadata, fname=config['storage']['metadata']['name']).id
    stats_catalog_id = dr.Dataset.create_from_in_memory_data(stats, fname=config['storage']['statistics']['name']).id
    with open(CONFIG_FILE, "w") as f:
        config['storage']['metadata']['ai_catalog_id'] = metadata_catalog_id
        config['storage']['statistics']['ai_catalog_id'] = stats_catalog_id
        yaml.dump(config, f)


def write_new_version_in_catalog(stats_df: pd.DataFrame, config):
    """
    Write a new version of the datasets to the AI Catalog
    """
    stats_id = config['storage']['statistics']['ai_catalog_id']
    current_stats = dr.Dataset.get(stats_id).get_as_dataframe()
    if max(current_stats["AS_OF_DATE"]) < CURRENT_HOUR:
        full_stats = pd.concat([current_stats, stats_df])
        dr.Dataset.create_version_from_in_memory_data(stats_id, full_stats)


def remove_old_ai_catalog_assets(client: dr.client.RESTClientObject, dataset_id: str):
    
    url = f"datasets/{dataset_id}/versions/"
    dataset_versions = client.get(url).json()
    logger.info(f"Found {dataset_versions['count']} versions of {dataset_id}")
    if dataset_versions['count'] > 75:
        sorted_versions = sorted(dataset_versions['data'], key=lambda x: pd.to_datetime(x['creationDate']))
        for version in sorted_versions[:-50]:
            url = f"datasets/{dataset_id}/versions/{version['versionId']}"
            client.delete(url)
        logger.info(f"Deleted {dataset_versions['count'] - 50} versions of {dataset_id}")


if __name__ == "__main__":
    
    stats_all_df, metadata_all_df = pd.DataFrame(), pd.DataFrame()
    for playlist in config["playlists"]:
        logger.info(f"Pulling data from playlist {playlist['name']}")
        videos = get_videos(playlist['id'])
        stats, metadata = compile_data(videos)
        stats_df, metadata_df = convert_to_dataframe(stats, metadata)
        stats_all_df = pd.concat([stats_all_df, stats_df])
        metadata_all_df = pd.concat([metadata_all_df, metadata_df])
        metadata_df["PLAYLIST_NAME"] = playlist["name"]

    
    logger.info("Loading datasets into AI Catalog")
    if config['storage']['metadata']['ai_catalog_id'] is None:
        write_new_assets_to_catalog(metadata_all_df, stats_all_df, config)

    else:
        write_new_version_in_catalog(stats_all_df, config)
        remove_old_ai_catalog_assets(CLIENT, config['storage']['statistics']['ai_catalog_id'])
