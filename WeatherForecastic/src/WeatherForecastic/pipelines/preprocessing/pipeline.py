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
                create_or_update_modeling_dataset,
                remove_old_retraining_data,
                create_or_update_scoring_dataset
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
            name="preprocess_data",
            func=create_or_update_modeling_dataset,
            inputs={
                "modeling_dataset_name": "params:datasets.modeling_dataset_name",
                "metadataset_name": "params:datasets.metadataset_name",
                "timeseries_data_name": "params:datasets.timeseries_dataset_name",
                "use_cases": "use_case_id",
            },
            outputs="modeling_dataset_id",
        ),
        # No longer necessary, don't need association_id
        # node(
        #     name="scoring_data_update",
        #     func=create_or_update_scoring_dataset,
        #     inputs={
        #         "scoring_dataset_name": "params:scoring_dataset_name",
        #         "modeling_dataset_id": "modeling_dataset_id",
        #         "use_cases": "use_case_id"
        #     },
        #     outputs=None
        # ),
        node(
            name="data_versioning_overflow_mitigation",
            func=remove_old_retraining_data,
            inputs={
                "endpoint": "params:credentials.datarobot.endpoint",
                "token": "params:credentials.datarobot.api_token",
                "datasets_to_check": "params:datasets",
            },
            outputs=None,
        ),
    ]
    pipeline_inst = pipeline(nodes)
    return pipeline(
        pipeline_inst,
        namespace="preprocessing",
        parameters={
            "params:credentials.datarobot.endpoint",
            "params:credentials.datarobot.api_token",
        },
    )
