# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from __future__ import annotations #Keep at top of file

import time
from typing import Any, List, TYPE_CHECKING, Union, Optional

from datarobot.models.use_cases.utils import UseCaseLike
from datarobot import Dataset 

if TYPE_CHECKING:
    import tempfile
    import datarobot as dr
    import pandas as pd

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


def prepare_dataset_for_modeling(dataset_name: str,
                                 target: str, 
                                 datetime_partition_column: str, 
                                 multiseries_id_columns: List[str],
                                 use_cases: Optional[UseCaseLike] = None) -> str:
    """Prepare a dataset for modeling in DataRobot.
    
    Parameters
    ----------
    metadata : pd.DataFrame
        The raw metadata dataset to combine with timeseries data for modeling
    timeseries_data: pd.DataFrame
        The raw timeseries dataset to combine with metadata for modeling
    target : str
        The name of the target column
    datetime_partition_column : str
        The name of the datetime partition column
    multiseries_id_columns : List[str]
        The name of the column that defines the multiseries id.
        Should be a list with one entry.
    
    Returns
    -------
    str
        ID of the dataset prepared for modeling in DataRobot
    """#TODO: Should it return a dr.Dataset?
    # Join the metadata and timeseries data on the Video ID
    # TODO: can I join datasets as dr.Datasets?
    print(use_cases, dataset_name)
    dataset_id = _find_existing_dataset(timeout_secs=30, dataset_name=dataset_name, use_cases=use_cases)

    current_data = dr.Dataset.get(dataset_id).get_as_dataframe()

    # Calculate the difference in viewCount from the previous hour for each entry
    #   for the first entry, it remains NaN?
    current_data['as_of_datetime'] = pd.to_datetime(current_data['as_of_datetime'])
    current_data = current_data.sort_values(['video_id', 'as_of_datetime'])

    current_data['video_diff'] = current_data.groupby('video_id')['viewCount'].diff()

    dr.Dataset.create_version_from_in_memory_data(dataset_id, current_data)
    return dataset_id


def put_forecast_distance_into_registered_model_name(registered_model_name: str, forecast_window_start: str, forecast_window_end: str) -> str:
    """Get or create a registered model for the time series model.

    The registered model name is comprised of the original model name,
    the start of the forecast window, and the end of the forecast window.
    
    Parameters
    ----------
    registered_model_name : str
        The name of the registered model
    forecast_window_start : str
        The start of the forecast window
    forecast_window_end : str
        The end of the forecast window
    
    Returns
    -------
    str
        The updated registered model name
    """
    
    return (
        registered_model_name + " (" +
        str(forecast_window_start) + ", " + str(forecast_window_end) +
        ")"
        )


def get_scoring_code(project_id: str, model_id: str) -> tempfile.TemporaryDirectory:
    """Get scoring code from a model

    Parameters
    ----------
    project_id : str
        The project id of a DataRobot automl project
    model_id : str
        The model id of a model in the project

    Returns
    -------
    tempfile.TemporaryDirectory
        A temporary directory containing the scoring code .jar file
    """

    import os

    import datarobot as dr
    
    d = tempfile.TemporaryDirectory()
    path_to_d = d.name

    model = dr.Model.get(project_id, model_id)

    model.download_scoring_code(file_name=os.path.join(path_to_d, "scoring_code.jar"))

    return d


def ensure_deployment_settings(
    endpoint: str,
    token: str,
    deployment_id: str,
    prediction_interval: int
) -> None:
    """Ensure deployment settings are properly configured.
    
    Parameters
    ----------
    prediction_interval: int
        The prediction interval to set for the deployment
    
    """
    import datarobot as dr

    dr.Client(endpoint=endpoint, token=token)

    deployment = dr.Deployment.get(deployment_id)
    deployment.update_predictions_data_collection_settings(enabled=True)
    deployment.update_drift_tracking_settings(target_drift_enabled=True)

    # TODO: Scoring data should have association_id
    # deployment.update_association_id_settings(
    #     column_names=["association_id"], required_in_prediction_requests=True
    # )
    deployment.update_prediction_intervals_settings(percentiles=[prediction_interval])