# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from __future__ import annotations
import os
from typing import Any, Dict, List, TYPE_CHECKING, Union

if TYPE_CHECKING:
    import pathlib


def prepare_yaml_content(*args: Any, **kwargs: Any) -> Union[Dict[str, Any], List[Any]]:
    """Passthrough node for gathering content to be serialized to yaml from upstream node(s).

    Parameters
    ----------
    args : Any
        Positional arguments to be passed as a list to the yaml renderer. If
        specified, all keyword arguments will be ignored.
    kwargs : Any
        Keyword arguments to be passed as a dict to the yaml render. Ignored
        if any positional arguments are passed.

    Returns
    -------
    list or dict :
        The yaml-serializable python object to pass to the yaml renderer.
    """
    if len(args):
        return list(args)
    else:
        return kwargs


def get_or_create_execution_environment_version_with_secrets(
    endpoint: str,
    token: str,
    azure_endpoint: str,
    azure_api_key: str,
    azure_api_version: str,
    execution_environment_id: str,
    secrets_template: str,
    app_assets: pathlib.Path,
) -> str:
    """Get or create the DR execution environment for the streamlit app.

    Bundles the secrets just in time before uploading so we don't accidentally
    persist them locally.

    Parameters
    ----------
    execution_environment_id : str
        DataRobot exeuction environment id in which a new version will be created
    app_assets : pathlib.Path
        Path to a directory containing all assets to be uploaded when creating the
        execution environment

    Returns
    -------
    str :
        DataRobot id of the created or retrieved execution environment version
    """
    from datarobotx.idp.execution_environment_versions import (
        get_or_create_execution_environment_version,
    )

    secrets_file = (secrets_template
                    .replace("<azure_endpoint>", azure_endpoint)
                    .replace("<azure_api_key>", azure_api_key)
                    .replace("<azure_api_version>", azure_api_version)
                    .replace("<datarobot_endpoint>", endpoint)
                    .replace("<datarobot_api_token>", token)
                    )

    # Overwrite the placeholder secrets.toml with real secrets
    with open(app_assets / ".streamlit/secrets.toml", "w") as f:
        f.write(secrets_file)

    return get_or_create_execution_environment_version(
        endpoint, token, execution_environment_id, app_assets
    )


def log_outputs(
    endpoint: str,
    project_id: str,
    model_id: str,
    deployment_id: str,
    application_id: str,
    project_name: str,
    deployment_name: str,
    app_name: str
) -> None:
    """Log URLs for DR deployments and app.

    Parameters
    ----------
    project_id : str
        DataRobot id of the project
    model_id : str
        DataRobot id of the model
    deployment_id : str
        DataRobot id of the deployment
    application_id : str
        DataRobot id of the custom application
    project_name : str
        Name of the project
    deployment_name : str
        Name of the deployment
    app_name : str
        Name of the deployed custom application
    """
    import logging
    from urllib.parse import urljoin

    base_url = urljoin(endpoint, "/")
    project_url = base_url + "projects/{project_id}/models/{model_id}/"
    deployment_url = base_url + "console/{deployment_id}/overview"
    application_url = base_url + "custom_applications/{application_id}/"

    logger = logging.getLogger(__name__)
    logger.info("Application is live!")
    msg = (
        "AutoPilot Project: "
        f"[link={project_url.format(project_id=project_id, model_id=model_id)}]"
        f"{project_name}[/link]"
    )
    logger.info(msg)
    msg = (
        "Deployment: "
        f"[link={deployment_url.format(deployment_id=deployment_id)}]"
        f"{deployment_name}[/link]"
    )
    logger.info(msg)
    msg = (
        "Custom application: "
        f"[link={application_url.format(application_id=application_id)}]"
        f"{app_name}[/link]"
    )
    logger.info(msg)