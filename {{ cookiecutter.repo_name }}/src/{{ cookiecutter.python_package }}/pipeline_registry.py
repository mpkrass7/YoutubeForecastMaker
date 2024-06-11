# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

"""Project pipelines."""
from typing import Dict

from kedro.pipeline import Pipeline
from .pipelines import get_data_pipeline as get_data_p
from .pipelines import deploy_forecast as deploy

def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    # The default pipeline will deploy the forecast and the streamlit app
    deploy_forecast = deploy.create_pipeline()
    # The pull data pipeline will pull data from Youtube
    pull_data = get_data_p.create_pipeline()
    return {
        "__default__": deploy_forecast, # TODO: add deploy streamlit
        "pull_data": pull_data,
    }