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
from .pipelines import deploy_streamlit_app as deploy_st
from .pipelines import preprocessing as prep

def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    return {
        "__default__": deploy.create_pipeline() + deploy_st.create_pipeline(),
        "pull_data": get_data_p.create_pipeline(),
        "data_prep": prep.create_pipeline(),
    }