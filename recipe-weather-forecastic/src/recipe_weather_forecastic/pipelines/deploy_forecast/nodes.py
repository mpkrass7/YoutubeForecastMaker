# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from __future__ import annotations #Keep at top of file

import time
from typing import Any, List, TYPE_CHECKING, Union, Optional, Dict

from datarobot.models.use_cases.utils import UseCaseLike
from datarobot import Dataset 

from datarobotx.idp.batch_predictions import get_update_or_create_batch_prediction_job
if TYPE_CHECKING:
    import tempfile
    import datarobot as dr
    import pandas as pd


def find_existing_dataset(
    dataset_name: str, use_cases: Optional[UseCaseLike] = None, timeout_secs: int = 60, 
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
        registered_model_name 
        + " (" 
        + str(forecast_window_start) 
        + ", " 
        + str(forecast_window_end) 
        + ")"
    )

def get_date_format(
    endpoint: str,
    token: str,
    project_id: str,
):
    "Get date format for project"
    import datarobot as dr

    client = dr.Client(endpoint=endpoint, token=token)
    url = "projects/{}/datetimePartitioning".format(project_id)
    response = client.get(url).json()
    return response["dateFormat"]

def ensure_deployment_settings(
    endpoint: str,
    token: str,
    deployment_id: str,
    datetime_partitioning_column: str,
    prediction_interval: int,
    date_format: str,
    association_id: Optional[str] = None,
) -> None:
    """Ensure deployment settings are properly configured.

    Parameters
    ----------
    datetime_partitioning_column: str
        The datetime partitioning column
    prediction_interval: int
        The prediction interval to set for the deployment
    date_format: str
        The date format derived from the dataset
    association_id: Optional[str]
        The association id, if any.
        When not set, the association id is auto-generated
    """
    import datarobot as dr

    deployment_settings_url = f"deployments/{deployment_id}/settings/"
    client = dr.Client(endpoint=endpoint, token=token)

    deployment = dr.Deployment.get(deployment_id)

    deployment.update_predictions_data_collection_settings(enabled=True)
    deployment.update_drift_tracking_settings(target_drift_enabled=True)

    deployment.update_prediction_intervals_settings(percentiles=[prediction_interval])

    datetime_partition_column = datetime_partitioning_column + " (actual)"
    request_body = {
        "predictionsByForecastDate": {
            "enabled": True,
            "columnName": datetime_partition_column,
            "datetimeFormat": date_format,
        },
        "automaticActuals": {"enabled": True},
    }

    if association_id is None:
        request_body["associationId"] = {
            "columnNames": ["association_id"],
            "requiredInPredictionRequests": False,
            "autoGenerateId": True,
        }
    else:
        request_body["associationId"] = {
            "columnNames": [association_id],
            "requiredInPredictionRequests": False,
            "autoGenerateId": False,
        }

    try:
        client.patch(deployment_settings_url, json=request_body)
    # Remove v2 on error
    except dr.errors.ClientError:
        request_body["predictionsByForecastDate"]["datetimeFormat"] = "v2" + date_format
        client.patch(deployment_settings_url, json=request_body)

    return

def setup_batch_prediction_job_definition(
    endpoint: str,
    token: str,
    deployment_id: str,
    dataset_id: str,
    enabled: bool,
    batch_prediction_job: dict,
    name: str,
    schedule: Optional[str | None]
):
    """Set up BatchPredictionJobDefinition for deployment to enable informed retraining.

    enabled: bool
        Whether or not the definition should be active on a scheduled basis. If True, `schedule` is required
    name: str
        * Must be unique to your organization *
        Name of batch prediction job definition. If given the name of an existing definition within the supplied
        deployment (according to deployment_id), this function will overwrite that existing definition with parameters
        specified in this function (batch_prediction_job, enabled, schedule).
    schedule : dict (optional)
        The ``schedule`` payload defines at what intervals the job should run, which can be
        combined in various ways to construct complex scheduling terms if needed. In all of
        the elements in the objects, you can supply either an asterisk ``["*"]`` denoting
        "every" time denomination or an array of integers (e.g. ``[1, 2, 3]``) to define
        a specific interval.
    """
    import datarobot as dr
    dr.Client(token=token, endpoint=endpoint)  # type: ignore

    batch_prediction_job["intake_settings"]["datasetId"] = dataset_id
    batch_prediction_job["deploymentId"] = deployment_id

    get_update_or_create_batch_prediction_job(endpoint=endpoint,
                                          token=token,
                                          deployment_id=deployment_id,
                                          batch_prediction_job=batch_prediction_job,
                                          enabled=enabled,
                                          name=name,
                                          schedule=schedule)