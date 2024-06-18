# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.
from kedro.pipeline import node, Pipeline
from kedro.pipeline.modular_pipeline import pipeline
from datarobotx.idp.use_cases import get_or_create_use_case

from .nodes import (
                get_videos, 
                compile_timeseries_data,
                update_or_create_dataset,
                compile_metadata,
                update_or_create_metadataset
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
            name="Get_playlists",
            func=get_videos,
            inputs={
                "playlist_ids": "params:playlist_ids",
                "api_key": "params:credentials.youtube_api_key"
            },
            outputs="combined_videos",
        ),
        node(
            name="Pull_Data",
            func=compile_timeseries_data,
            inputs={
                "videos": "combined_videos",
                "api_key": "params:credentials.youtube_api_key"
            },
            outputs="time_series_data",
            tags=["checkpoint"],
        ),
        node(
            name="Pull_metadata",
            func=compile_metadata,
            inputs={
                "videos": "combined_videos",
                "api_key": "params:credentials.youtube_api_key"
            },
            outputs="metadata",
            tags=["checkpoint"],
        ),
        node(
            name="update_timeseries_data",
            func=update_or_create_dataset,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "name": "params:timeseries_dataset_name",
                "data_frame": "time_series_data",
                "use_cases": "use_case_id",
            },
            outputs=None
        ),
        node(
            name="update_metadata",
            func=update_or_create_metadataset,
            inputs={
                "use_cases": "use_case_id",
                "name": "params:metadataset_name",
                "data_frame": "metadata",
            },
            outputs=None
        ),
    ]
    pipeline_inst = pipeline(nodes)
    return pipeline(
        pipeline_inst,
        namespace="get_data_pipeline",
        parameters={
            "params:credentials.datarobot.endpoint",
            "params:credentials.datarobot.api_token",
            "params:credentials.youtube_api_key",
        },
    )
