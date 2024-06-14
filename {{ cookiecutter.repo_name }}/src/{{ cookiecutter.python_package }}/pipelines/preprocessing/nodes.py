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


def create_or_update_modeling_dataset(combined_dataset_name: str, #TODO: change 'combined' to modeling or something
                                 metadataset_name: str, 
                                 timeseries_data_name: str,
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
    metadata_df = dr.Dataset.get(_check_if_dataset_exists(metadataset_name)).get_as_dataframe()
    raw_ts_data = dr.Dataset.get(_check_if_dataset_exists(timeseries_data_name)).get_as_dataframe()

    # Join the metadata and timeseries data on the Video ID
    new_data = pd.merge(metadata_df, raw_ts_data, on="video_id", how="inner").reset_index(drop=True)

    # Add in columns for engineered features
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

        staging_data = staging_data.drop_duplicates()

        dataset = dr.Dataset.create_version_from_in_memory_data(combined_dataset_id, staging_data)

    return str(dataset.id)
    
