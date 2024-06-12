# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

import tempfile
from typing import Any
import pandas as pd

from kedro.pipeline import node
from .nodes import prepare_yaml_content


def make_app_assets(
    app_py: str,
    helpers_py: str,
    app_parameters_yml: Any,
    requirements: str,
    dockerfile: str,
    logo: str,
    style_css: str,
    config_toml: str,
    secrets_toml: str,
    scoring_data: pd.DataFrame,
) -> tempfile.TemporaryDirectory:
    """Assemble directory of streamlit assets to be uploaded for a new DR execution environment.

    Parameters
    ----------
    app_py : str
        app.py contents to be included in execution environment
    helpers_py : str
        helpers.py contents to be included in execution environment
    app_parameters_yaml : dict or list
        app_parameters.yaml contents to be included in execution environment
    requirements_txt : str
        requirements.txt contents to be included in execution environment
    dockerfile : str
        Dockerfile contents to be included in execution environment
    logo : str
        location of logo to be included in execution environment
    style_css : str
        style.css contents to be included in execution environment
    config_toml : str
        config.toml contents to be included in execution environment
    secrets_toml : str
        secrets.toml contents to be included in execution environment
    scoring_data : pd.DataFrame
        Scoring data to be included in execution environment

    Returns
    -------
    tempfile.TemporaryDirectory :
        Temporary directory containing the contents to be uploaded to DR
    """
    import os
    import pathlib
    import tempfile

    import yaml

    d = tempfile.TemporaryDirectory()
    path_to_d = d.name

    files = zip(
        [
            app_py,
            helpers_py,
            yaml.dump(app_parameters_yml),
            requirements,
            dockerfile,
            style_css,
        ],
        [
            "app.py",
            "helpers.py",
            "app_parameters.yaml",
            "requirements.txt",
            "Dockerfile",
            "style.css",
        ],
    )
    for file, name in files:
        with open(os.path.join(path_to_d, name), "w") as f:
            f.write(file)

    logo.save(os.path.join(path_to_d, "DataRobot.png"))

    dot_streamlit_dir = pathlib.Path(d.name) / ".streamlit"
    dot_streamlit_dir.mkdir()

    with open(dot_streamlit_dir / "config.toml", "w") as f:
        f.write(config_toml)

    with open(dot_streamlit_dir / "secrets.toml", "w") as f:
        f.write(secrets_toml)

    scoring_data.to_csv(os.path.join(path_to_d, "scoring_data.csv"), index=False)

    return d


extra_nodes = [
    node(
        name="make_app_parameters",
        func=prepare_yaml_content,
        inputs={
            "deployment_id": "deployment_id",
            "page_title": "params:page_title",
            "graph_y_axis": "params:graph_y_axis",
            "lower_bound_forecast_at_0": "params:lower_bound_forecast_at_0",
            "headline_prompt": "params:headline.prompt",
            "headline_temperature": "params:headline.temperature",
            "analysis_temperature": "params:analysis.temperature",
            "model_name": "params:credentials.azure_openai_llm_credentials.deployment_name",
            "target": "params:project.analyze_and_model_config.target",
            "datetime_partition_column": "params:project.datetime_partitioning_config.datetime_partition_column",
            "multiseries_id_column": "params:project.datetime_partitioning_config.multiseries_id_columns",
            "prediction_interval": "params:deployment.prediction_interval",
        },
        outputs="app_parameters",
    ),
    node(
        name="make_app_assets",
        func=make_app_assets,
        inputs={
            "app_py": "app_code",
            "helpers_py": "app_helpers",
            "app_parameters_yml": "app_parameters",
            "requirements": "app_requirements",
            "dockerfile": "app_dockerfile",
            "logo": "app_logo",
            "style_css": "app_style",
            "config_toml": "app_config",
            "secrets_toml": "app_secrets",
            "scoring_data": "scoring_data",
        },
        outputs="app_assets",
    ),
]
