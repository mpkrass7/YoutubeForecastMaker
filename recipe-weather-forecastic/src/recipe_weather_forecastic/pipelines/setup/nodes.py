# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from typing import List, Dict, Any, Union, Optional, Tuple
import datarobot as dr
import pandas as pd

from datarobot.models.use_cases.utils import UseCaseLike


def _check_if_dataset_exists_in_usecase(
    name: str, use_cases: Optional[UseCaseLike] = None
) -> Union[str, None]:
    """Check if a dataset with the given name exists in your use case
    Returns:
        id (string) or None
    """
    datasets = dr.Dataset.list(use_cases=use_cases)
    return next((dataset.id for dataset in datasets if dataset.name == name), None)


def get_or_create_dataset_from_df(
    endpoint: str,
    token: str,
    name: str,
    data_frame: pd.DataFrame,
    use_cases: Optional[UseCaseLike] = None,
) -> str:
    """Get or create a DR dataset from a dataframe with requested parameters.
    Returns:
        id of dataset
    """
    import datarobot as dr

    dr.Client(token=token, endpoint=endpoint)  # type: ignore

    dataset_id = _check_if_dataset_exists_in_usecase(name=name, use_cases=use_cases)

    if dataset_id is None:
        dataset: dr.Dataset = dr.Dataset.create_from_in_memory_data(
            data_frame=data_frame, use_cases=use_cases
        )
        dataset.modify(name=name)
        return str(dataset.id)
    else:
        return dataset_id


def _check_if_notebook_exists(
    token: str,
    name: str,
    use_case_id: str,
) -> List[Tuple[str, str]]:
    """Check if usecase contains a notebook with the same name which we are trying upload
    Parameters
    ----------
    name: str
        name of the notebook we are attempting to upload to our use case

    Returns
    -------
        List of tuples, the first being the name of the notebook, the second the id of the notebook
        which match the inputted name
    """
    import requests

    headers = {"Authorization": f"Token {token}"}
    response = requests.get(
        f"https://app.datarobot.com/api-gw/nbx/notebooks/?useCaseId={use_case_id}",
        headers=headers,
    )

    notebook_names = [
        (notebook["name"], notebook["id"]) for notebook in response.json()["data"]
    ]
    matching_ids = [
        notebook_id
        for notebook_name, notebook_id in notebook_names
        if notebook_name == name
    ]

    return matching_ids


def _compare_notebook_content(
    notebook_json: str,
    notebook_id: str,
    token: str,
) -> Union[None, str]:
    """Compares server-side notebook cells with local notebook cells
    Parameters
    ----------
    notebook_json: str
        A json string representing the local notebook content.
    notebook_id: str
        The id of the server-side notebook which has the same name we are trying to give notebook to be uploaded

    Returns
    ------
    Union[None, str]
        If the notebooks' content matches, then return the id of the server-side notebook, else returns None.
    """
    import requests
    import json

    headers = {"Authorization": f"Token {token}"}
    response = requests.get(
        url=f"https://app.datarobot.com/api-gw/nbx/notebooks/{notebook_id}/cells/",
        headers=headers,
    )

    server_notebook_cells = "".join([cell["source"] for cell in response.json()])
    notebook_json = json.loads(notebook_json)
    local_notebook_cells = "".join(
        ["".join(cell["source"]) for cell in notebook_json["cells"]]
    )

    if server_notebook_cells == local_notebook_cells:
        return notebook_id
    else:
        return None


# Need to add get functionality
# change to get_update_or_replace... as in, delete replace
def get_or_update_notebook(
    token: str,
    use_case_id: str,
    notebook: Any,  # TODO: figure out what type this should be.
    name: Optional[str] = "scheduled_notebook",
) -> str:
    """Gets notebook from usecase if content matches local notebook, else uploads local notebook
    Parameters:
    -----------
    notebook:
        The local notebook, found in notebooks directory
    """
    import requests
    import json
    from io import BytesIO
    import logging
    import nbformat as nbf

    logger = logging.getLogger(__name__)

    notebook_json = nbf.writes(
        notebook
    )  # TODO: There may be a cleaner way to do this...
    binary_stream = BytesIO(notebook_json.encode("utf-8")).getvalue()

    # First, check if a notebook with that name already exists
    ids_with_matching_name = _check_if_notebook_exists(token, name, use_case_id)
    existing_id = None
    for notebook_id in ids_with_matching_name:
        existing_id = _compare_notebook_content(notebook_json, notebook_id, token)
        if existing_id:
            logger.info(
                f"Your notebook titled {name} was already generated (use_case_id : {use_case_id})"
            )
            return existing_id  # TODO: does returning here leave this loop on the stack, or is Python smart?

    url = "https://app.datarobot.com/api-gw/nbx/notebookImport/fromFile/"

    payload = {"useCaseId": use_case_id}

    files = [("file", (f"{name}.ipynb", binary_stream, "application/octet-stream"))]
    headers = {"Authorization": f"Bearer {token}", "Cookie": "datarobot_nextgen=0"}

    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    if response.status_code != 201:
        response.raise_for_status()
    else:
        logger.info(f"Your notebook titled {name} has been generated in your use case")
        logger.info(
            f"Link to your usecase=https://app.datarobot.com/usecases/{use_case_id}"
        )
        return str(json.loads(response.text)["id"])


def schedule_notebook(
    token: str,
    notebook_id: str,
    schedule: Any,
    title: str,
    use_case_id: str,
) -> None:
    """Puts the inputted notebooked onto a specified schedule"""
    import requests
    import json
    import logging

    logger = logging.getLogger(__name__)

    url = "https://app.datarobot.com/api-gw/nbx/scheduling/"

    payload = json.dumps(
        {
            "useCaseId": use_case_id,
            "notebookId": notebook_id,
            "title": title,
            "enabled": True,
            "schedule": schedule,
        }
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {token}",
        "Cookie": "datarobot_nextgen=0",
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code != 201:
        if (
            json.loads(response.text)["message"]
            == "You can only have one enabled schedule at a time."
        ):
            logger.info("Job already scheduled to run")
        else:
            response.raise_for_status()
    else:
        first_run = json.loads(response.text)["nextRunTime"]
        logger.info(f"Job scheduled to run first: {first_run} (UTC)")


def instantiate_env(token: str, notebook_id: str, **kwargs: Any) -> None:
    """Instantiates the server-side notebook with environment variables passed into kwargs"""
    import requests
    import json

    headers = {
        "Authorization": f"Token {token}",
    }
    data = {
        "data": [
            {
                "name": "locations",
                "value": json.dumps(kwargs.get("locations")),
                "description": "",
            },
            {
                "name": "parameters",
                "value": json.dumps(kwargs.get("parameters")),
                "description": "",
            },
            {
                "name": "modeling_dataset_name",
                "value": kwargs.get("modeling_dataset_name"),
                "description": "",
            },
        ]
    }

    response = requests.post(
        f"https://app.datarobot.com/api-gw/nbx/environmentVariables/{notebook_id}/",
        json=data,
        headers=headers,
    )
    assert response.status_code == 201


def get_historical_city_data(
    locations: List[Dict[str, float]], parameters: Dict[str, Any]
) -> pd.DataFrame:
    """Gets past 3 months of weather data (locations and parameters specified in parameters_setup.yml)"""
    import pandas as pd
    import logging

    import openmeteo_requests
    import datetime
    import pytz

    logger = logging.getLogger(__name__)

    # Setup the Open-Meteo API client with cache and retry on error
    openmeteo = openmeteo_requests.Client()

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"

    latitudes = [locations[city]["Latitude"] for city in locations]
    longitudes = [locations[city]["Longitude"] for city in locations]
    city_names = list(locations.keys())

    parameters["past_days"] = 90  # Set to past 3 months to get some historical data.
    parameters["forecast_days"] = (
        1  # Have to set forecast_days to 1 to get today's data
    )
    parameters["latitude"] = latitudes
    parameters["longitude"] = longitudes

    responses = openmeteo.weather_api(url, params=parameters)

    all_data = []
    for i, response in enumerate(responses):
        logger.info(f"Gathered weather data from {city_names[i]}")

        # Process hourly data. The order of variables needs to be the same as requested.
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_precipitation_probability = hourly.Variables(1).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(2).ValuesAsNumpy()
        hourly_uv_index = hourly.Variables(3).ValuesAsNumpy()

        timezone = pytz.timezone(response.Timezone())
        timestart = datetime.datetime.fromtimestamp(hourly.Time(), tz=timezone)
        timeend = datetime.datetime.fromtimestamp(hourly.TimeEnd(), tz=timezone)

        current_time = pd.Timestamp.now(tz=timezone)

        hourly_data = {
            "date": pd.date_range(
                start=timestart,
                end=timeend,
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": hourly_temperature_2m,
            "uv_index": hourly_uv_index,
            "precipitation_probability": hourly_precipitation_probability,
            "precipitation": hourly_precipitation,
            "elevation": response.Elevation(),
            "longitude": response.Latitude(),
            "latitude": response.Longitude(),
            "city": city_names[i],
        }
        # Filter out the forecast rows.
        current_time = pd.to_datetime(
            pd.Timestamp.now(tz=timezone).strftime("%Y-%m-%d %H:%M:%S")
        )
        new_data = pd.DataFrame(data=hourly_data)
        new_data["date"] = pd.to_datetime(new_data["date"])
        logger.info(f"Current time: {current_time}")

        new_data = new_data[new_data["date"] <= current_time]
        new_data = new_data.sort_values(by="date", ascending=True)

        logger.info(f"Most recent time in dataframe={new_data['date'].iloc[-1]}")

        all_data.append(pd.DataFrame(data=new_data))

    hourly_dataframe = pd.concat(all_data, ignore_index=True)
    return hourly_dataframe
