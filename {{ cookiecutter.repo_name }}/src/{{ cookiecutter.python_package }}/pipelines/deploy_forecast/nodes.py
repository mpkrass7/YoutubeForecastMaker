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
        registered_model_name + " (" +
        str(forecast_window_start) + ", " + str(forecast_window_end) +
        ")"
        )

def ensure_deployment_settings(
    endpoint: str,
    token: str,
    deployment_id: str,
    prediction_interval: int,
    prediction_environment_id: str = None,
) -> None:
    """Ensure deployment settings are properly configured.
    
    Parameters
    ----------
    prediction_interval: int
        The prediction interval to set for the deployment
    
    """
    import datarobot as dr

    client = dr.Client(endpoint=endpoint, token=token)

    deployment = dr.Deployment.get(deployment_id)
    deployment.update_predictions_data_collection_settings(enabled=True)
    deployment.update_drift_tracking_settings(target_drift_enabled=True)

    deployment.update_association_id_settings(
        column_names=["association_id"], required_in_prediction_requests=True
    )
    deployment.update_prediction_intervals_settings(percentiles=[prediction_interval])

    if prediction_environment_id is None:
        prediction_environment_id = deployment.prediction_environment["id"] 

    client.patch(f"deployments/{deployment_id}/settings",
                 json={
                     "automaticActuals": {"enabled": True}
                 })