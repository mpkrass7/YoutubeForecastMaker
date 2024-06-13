# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from kedro.pipeline import node, Pipeline
from kedro.pipeline.modular_pipeline import pipeline
from .nodes import get_or_create_execution_environment_version_with_secrets
from datarobotx.idp.custom_applications import get_replace_or_create_custom_app_from_env
from datarobotx.idp.execution_environments import get_or_create_execution_environment
from .nodes import log_outputs
from .nodes_extra import extra_nodes


def create_pipeline(**kwargs) -> Pipeline:
    nodes = [
        node(
            name="make_app_execution_environment",
            func=get_or_create_execution_environment,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "name": "params:environment_name",
                "use_cases": "params:environment_use_cases",
            },
            outputs="app_execution_environment_id",
        ),
        node(
            name="make_app_execution_environment_version",
            func=get_or_create_execution_environment_version_with_secrets,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "azure_endpoint": "params:credentials.azure_openai_llm_credentials.azure_endpoint",
                "azure_api_key": "params:credentials.azure_openai_llm_credentials.api_key",
                "azure_api_version": "params:credentials.azure_openai_llm_credentials.api_version",
                "execution_environment_id": "app_execution_environment_id",
                "secrets_template": "app_secrets",
                "app_assets": "app_assets",
            },
            outputs="execution_environment_version_id",
        ),
        node(
            name="deploy_app",
            func=get_replace_or_create_custom_app_from_env,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "name": "params:custom_app_name",
                "environment_id": "app_execution_environment_id",
                "env_version_id": "execution_environment_version_id",
            },
            outputs="application_id",
        ),
        node(
            name="log_outputs",
            func=log_outputs,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "project_id": "project_id",
                "model_id": "recommended_model_id",
                "deployment_id": "deployment_id",
                "application_id": "application_id",
                "project_name": "params:project.name",
                "deployment_name": "params:deployment.label",
                "app_name": "params:custom_app_name",
            },
            outputs=None,
        ),
    ]
    pipeline_inst = pipeline(nodes + extra_nodes)
    return pipeline(
        pipeline_inst,
        namespace="deploy_streamlit_app",
        parameters={
            "params:credentials.datarobot.endpoint": "params:credentials.datarobot.endpoint",
            "params:credentials.datarobot.api_token": "params:credentials.datarobot.api_token",
            "params:credentials.azure_openai_llm_credentials.azure_endpoint": "params:credentials.azure_openai_llm_credentials.azure_endpoint",
            "params:credentials.azure_openai_llm_credentials.api_key": "params:credentials.azure_openai_llm_credentials.api_key",
            "params:credentials.azure_openai_llm_credentials.api_version": "params:credentials.azure_openai_llm_credentials.api_version",
            "params:credentials.azure_openai_llm_credentials.deployment_name": "params:credentials.azure_openai_llm_credentials.deployment_name",
            "params:project.name": "params:deploy_forecast.project.name",
            "params:project.analyze_and_model_config.target": "params:deploy_forecast.project.analyze_and_model_config.target",
            "params:project.datetime_partitioning_config.multiseries_id_columns": "params:deploy_forecast.project.datetime_partitioning_config.multiseries_id_columns",
            "params:project.datetime_partitioning_config.datetime_partition_column": "params:deploy_forecast.project.datetime_partitioning_config.datetime_partition_column",
            "params:deployment.label": "params:deploy_forecast.deployment.label",
            "params:deployment.prediction_interval": "params:deploy_forecast.deployment.prediction_interval",
        },
        inputs={
            "project_id",
            "recommended_model_id",
            "deployment_id",
        },
    )
