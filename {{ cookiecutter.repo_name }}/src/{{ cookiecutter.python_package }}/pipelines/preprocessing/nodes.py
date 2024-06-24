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


def create_or_update_modeling_dataset(modeling_dataset_name: str, 
                                 metadataset_name: str, 
                                 timeseries_data_name: str,
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
    """
    metadata_df = dr.Dataset.get(_check_if_dataset_exists(metadataset_name)).get_as_dataframe()
    raw_ts_data = dr.Dataset.get(_check_if_dataset_exists(timeseries_data_name)).get_as_dataframe()

    # Join the metadata and timeseries data on the Video ID
    new_data = pd.merge(metadata_df, raw_ts_data, on="video_id", how="inner").reset_index(drop=True)

    # Add in columns for engineered features
    new_data["viewDiff"] = 0
    new_data["likeDiff"] = 0
    new_data["commentDiff"] = 0

    def _round_to_nearest_half_hour(time):
        # Find the number of minutes past the hour
        minutes = time.minute
        if minutes < 15:
            rounded_time = time.replace(minute=0, second=0, microsecond=0)
        elif minutes < 45:
            rounded_time = time.replace(minute=30, second=0, microsecond=0)
        else:
            rounded_time = (time + pd.Timedelta(minutes=(60 - minutes))).replace(minute=0, second=0, microsecond=0)
        return rounded_time

    modeling_dataset_id = _check_if_dataset_exists(modeling_dataset_name)

    # TODO: Should this be idempotent? (use hash?)
    if modeling_dataset_id is None:
        new_data["as_of_datetime"] = pd.to_datetime(new_data['as_of_datetime'], errors='coerce')
        new_data["as_of_datetime"] = new_data["as_of_datetime"].apply(_round_to_nearest_half_hour)
        dataset: Dataset = Dataset.create_from_in_memory_data(
            data_frame=new_data, use_cases=use_cases
        )
        dataset.modify(name=f"{modeling_dataset_name}")
        modeling_dataset_id = dataset.id
        staging_data = dataset.get_as_dataframe()
    else:     
        current_modeling_data = dr.Dataset.get(modeling_dataset_id).get_as_dataframe()
        staging_data = pd.concat([current_modeling_data, new_data]).reset_index(drop=True)

    # Calculate the difference in viewCount from the previous hour for each entry
    #   for the first entry, it remains 0
    staging_data['as_of_datetime'] = pd.to_datetime(staging_data['as_of_datetime'], errors='coerce')
    staging_data = staging_data.sort_values(['video_id', 'as_of_datetime'])

    staging_data['viewDiff'] = staging_data.groupby('video_id')['viewCount'].diff()
    staging_data['likeDiff'] = staging_data.groupby('video_id')['likeCount'].diff()
    staging_data['commentDiff'] = staging_data.groupby('video_id')['commentCount'].diff()

    staging_data = staging_data.drop_duplicates(subset=["video_id", "viewCount", "as_of_datetime"])

    staging_data = staging_data.groupby('video_id').apply(lambda group: group.iloc[::3]).reset_index(drop=True)

    staging_data.fillna(0, inplace=True)

    staging_data["viewDiff"] = staging_data["viewDiff"].apply(lambda x: max(x, 0))

    dataset = dr.Dataset.create_version_from_in_memory_data(modeling_dataset_id, staging_data)

    return str(dataset.id)

# TODO: Scoring data should have association_id
# Series (music video id) and the date--
# Scoring data is all historical data, 
#   known in advance 
#   future stuff is stacked, so would have to make another dataset
#   
# not sure I totally understand how the model uses this to know how the model is doing...
# does it score the predictions in the scoring dataset?
# 1. add "known_in_advance"
# How many rows would I add?
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

    modeling_df["association_id"] = modeling_df["video_id"] + "-" + modeling_df["as_of_datetime"]

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
                               dataset1_name: str,
                               dataset2_name: str):
    from logzero import logger

    client = dr.Client(endpoint=endpoint, token=token)
    datasets_to_check = [dataset1_name, dataset2_name]

    for dataset_name in datasets_to_check:
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

    
    
