# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

import pathlib

import datarobot as dr
import pandas as pd
import pytest

from datarobot_predict.deployment import predict
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project


@pytest.fixture(scope="module", autouse=True)
def kedro_session():
    project_path = pathlib.Path(".").resolve()
    bootstrap_project(project_path)
    kedro_session = KedroSession.create(project_path)
    return kedro_session


@pytest.fixture(scope="module")
def project_context(kedro_session):
    return kedro_session.load_context()


@pytest.fixture
def dr_client(project_context):
    dr_api_key = project_context.config_loader["credentials"]["datarobot"]["api_token"]
    dr_endpoint = project_context.config_loader["credentials"]["datarobot"]["endpoint"]

    client = dr.Client(dr_api_key, dr_endpoint)
    client.headers["Connection"] = "close"
    dr.client.set_client(client)

    return client


@pytest.fixture()
def data(project_context):
    dataset_id = project_context.catalog.load("scoring_data_id")
    return dr.Dataset.get(dataset_id).get_as_dataframe()


@pytest.fixture
def deployment(project_context, dr_client):
    deployment_id = project_context.catalog.load("deployment_id")
    return dr.Deployment.get(deployment_id)


def test_deployment_can_predict(deployment, data, dr_client):
    predictions = predict(deployment, data)
    assert isinstance(predictions.dataframe, pd.DataFrame)
    assert not predictions.dataframe.empty