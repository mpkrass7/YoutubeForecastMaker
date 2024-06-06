# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.
from kedro.pipeline import node, Pipeline
from kedro.pipeline.modular_pipeline import pipeline
from .nodes import (
                get_videos, 
                compile_timeseries_data,
                update_or_create_dataset,
                )


def create_pipeline(**kwargs) -> Pipeline:
    nodes = [
        # TODO: Let's assume you already have a usecase
        node(
            name="Get_IDs",
            func=get_videos,
            inputs={
                "playlist_id": "params:playlist_id",
                "api_key": "params:credentials.youtube_api_key"
            },
            outputs="video_id_list",
        ),
        node(
            name="Pull_Data",
            func=compile_timeseries_data,
            inputs={
                "videos": "video_id_list",
                "api_key": "params:credentials.youtube_api_key"
            },
            #TODO: Can I name the output based on the playlist name?
            #       Also, can there be more than 1 output? Can it 
            #       represent a tuple?
            outputs="time_series_data",
            #TODO: What are the tags for?
            tags=["checkpoint"],
        ),
        node(
            name="update_dataset",
            func=update_or_create_dataset,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "name": "params:dataset_name",
                "data_frame": "time_series_data",
                "use_cases": "params:credentials.datarobot.use_case_id",
            },
            outputs=None
        )
        # TODO: What is this for?
        # node(
        #     name="log_outputs",
        #     func=log_outputs,
        #     inputs="greeting",
        #     outputs=None,
        #     tags=["logging"],
        # )
    ]
    pipeline_inst = pipeline(nodes)
    return pipeline(
        pipeline_inst,
        namespace="get_data_pipeline",
        parameters={
            "params:credentials.datarobot.endpoint",
            "params:credentials.datarobot.api_token",
            "params:credentials.youtube_api_key",
            "params:credentials.datarobot.use_case_id",
        }
    )
