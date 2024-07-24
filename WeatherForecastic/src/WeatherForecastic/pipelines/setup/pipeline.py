# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.
from kedro.pipeline import node, Pipeline
from kedro.pipeline.modular_pipeline import pipeline

from datarobotx.idp.use_cases import get_or_create_use_case
from datarobotx.idp.datasets import get_or_create_dataset_from_df

from .nodes import (
                update_or_create_timeseries_dataset,
                get_historical_city_data
                )


def create_pipeline(**kwargs) -> Pipeline:
    nodes = [
        node(
            name="make_or_get_datarobot_use_case",
            func=get_or_create_use_case,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "name": "params:use_case.name",
            },
            outputs="use_case_id",
        ),
        node(
            name="Get_historical_data",
            func=get_historical_city_data,
            inputs={
                "locations": "params:locations",
                "parameters": "params:weather_parameters"
            },
            outputs="weather_df",
        ),
        node(
            name="Create_historical_df",
            func=get_or_create_dataset_from_df,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "name": "params:datasets.timeseries_dataset_name",
                "data_frame": "weather_df",
                "use_cases": "use_case_id"
            },
            outputs="time_series_dataset_id"
        ),
        # This would be useful in another pipeline?
        # TODO: Not sure what else to do?
        # node(
        #     name="update_timeseries_data",
        #     func=update_or_create_timeseries_dataset,
        #     inputs={
        #         "endpoint": "params:credentials.datarobot.endpoint",
        #         "token": "params:credentials.datarobot.api_token",
        #         "name": "params:timeseries_dataset_name",
        #         "data_frame": "time_series_data",
        #         "use_cases": "use_case_id",
        #     },
        #     outputs=None
        # ),
    ]
    pipeline_inst = pipeline(nodes)
    return pipeline(
        pipeline_inst,
        namespace="setup",
        parameters={
            "params:credentials.datarobot.endpoint",
            "params:credentials.datarobot.api_token",
        },
    )
