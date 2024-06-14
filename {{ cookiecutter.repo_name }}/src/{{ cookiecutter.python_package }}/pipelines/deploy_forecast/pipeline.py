# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from kedro.pipeline import node, Pipeline
from kedro.pipeline.modular_pipeline import pipeline

import datarobot as dr
from datarobotx.idp.autopilot import get_or_create_autopilot_run
from datarobotx.idp.datasets import get_or_create_dataset_from_df
from datarobotx.idp.deployments import (
    get_replace_or_create_deployment_from_registered_model,
)

from datarobotx.idp.registered_model_versions import (
    get_or_create_registered_leaderboard_model_version,
)
from datarobotx.idp.use_cases import get_or_create_use_case

from .nodes import ensure_deployment_settings, prepare_dataset_for_modeling, put_forecast_distance_into_registered_model_name, get_modeling_dataset_id

def create_pipeline(**kwargs) -> Pipeline:
    nodes = [
        node(
            name="make_datarobot_use_case",
            func=get_or_create_use_case,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "name": "params:use_case.name",
            },
            outputs="use_case_id",
        ),
        #FInd metadata ID, find stats ID
        # Next node does dataprep, try to find name and create new version
        # If name doesn't
        node(
            name="get_modeling_dataset_id",
            func=get_modeling_dataset_id,
            inputs={
                "dataset_name": "params:dataset_name",
                "use_cases": "use_case_id"
            },
            outputs="preprocessed_timeseries_data_id", 
        ),
        node(
            name="make_autopilot_run",
            func=get_or_create_autopilot_run,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "name": "params:project.name",
                "dataset_id": "preprocessed_timeseries_data_id",
                "analyze_and_model_config": "params:project.analyze_and_model_config",
                "datetime_partitioning_config": "params:project.datetime_partitioning_config",
                "advanced_options_config": "params:project.advanced_options_config",
                "use_case": "use_case_id",
            },
            outputs="project_id"
        ),
        node(
            name="get_recommended_model",
            func=lambda project_id: dr.ModelRecommendation.get(project_id).model_id,
            inputs="project_id",
            outputs="recommended_model_id",
        ),
        node(
            name="make_registered_model_name",
            func=put_forecast_distance_into_registered_model_name,
            inputs={
                "registered_model_name": "params:registered_model.name",
                "forecast_window_start": "params:project.datetime_partitioning_config.forecast_window_start",
                "forecast_window_end": "params:project.datetime_partitioning_config.forecast_window_end",
            },
            outputs="modified_registered_model_name",
        ),
        node(
            name="make_registered_model",
            func=get_or_create_registered_leaderboard_model_version,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "model_id": "recommended_model_id",
                "registered_model_name": "modified_registered_model_name",
            },
            outputs="registered_model_version_id",
        ),
        node(
            name="make_deployment",
            func=get_replace_or_create_deployment_from_registered_model,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "registered_model_version_id": "registered_model_version_id",
                "registered_model_name": "modified_registered_model_name",
                "label": "params:deployment.label",
                "description": "params:deployment.description",
                "default_prediction_server_id": "params:credentials.datarobot.default_prediction_server_id",
            },
            outputs="deployment_id",
        ),
        node(
            name="prepare_dataset_for_modeling",
            func=prepare_dataset_for_modeling,
            inputs={
                "dataset_name": "params:dataset_name",
                "target": "params:project.analyze_and_model_config.target",
                "datetime_partition_column": "params:project.datetime_partitioning_config.datetime_partition_column",
                "multiseries_id_columns": "params:project.datetime_partitioning_config.multiseries_id_columns",
                "use_cases": "use_case_id"
            },
            outputs="scoring_data",
        ),
        # This is where we'll set up retraining
        node(
            name="ensure_deployment_settings",
            func=ensure_deployment_settings,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "deployment_id": "deployment_id",
                "prediction_interval": "params:deployment.prediction_interval",
            },
            outputs=None,
        ),
    ]
    pipeline_inst = pipeline(nodes)
    return pipeline(
        pipeline_inst,
        namespace="deploy_forecast",
        parameters={
            "params:credentials.datarobot.endpoint",
            "params:credentials.datarobot.api_token",
            "params:credentials.datarobot.default_prediction_server_id",
        },
        outputs={
            "scoring_data",
            "project_id",
            "recommended_model_id",
            "deployment_id",
            "preprocessed_timeseries_data_id"
        }
    )
