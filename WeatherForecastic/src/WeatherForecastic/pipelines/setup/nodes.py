# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

from typing import List, Dict, Any, Tuple, Union, Optional
import datarobot as dr
import pandas as pd

from datarobot import Dataset
from datarobot.models.use_cases.utils import UseCaseLike
from datarobotx.idp.common.hashing import get_hash
from io import BytesIO

def create_notebook(
        locations: List[Dict[str, float]], 
        parameters: Dict[str, Any],
) -> bytes:
    """Creates the binary for notebook to be uploaded to your use case

    """
    import nbformat as nbf
    from nbformat.notebooknode import NotebookNode

    # Create a new notebook object
    nb: NotebookNode = nbf.v4.new_notebook()

    markdown_cell = nbf.v4.new_markdown_cell("## This notebook was generated from `kedro run -p 'setup'` ")
    nb.cells.append(markdown_cell)

    # Add a Code cell
    code_cell = nbf.v4.new_code_cell("print('Hello, world!')")
    nb.cells.append(code_cell)

    # Serialize the notebook object to JSON string
    notebook_json = nbf.writes(nb)

    # Convert the JSON string to a binary stream
    return BytesIO(notebook_json.encode('utf-8')).getvalue()

# Need to add get functionality
def get_or_update_notebook(
        token: str,
        use_case_id: str,
        binary_stream: BytesIO,
        name: Optional[str] = "scheduled_notebook",
) -> str:
    """
    """
    import requests
    import json
    # from io import BytesIO
    from logzero import logger

    url = "https://app.datarobot.com/api-gw/nbx/notebookImport/fromFile/"
    
    payload = {'useCaseId': use_case_id}
    files = [
        ('file',(f'{name}.ipynb',binary_stream,'application/octet-stream'))
    ]
    headers = {
        'Authorization': f'Bearer {token}',
        'Cookie': 'datarobot_nextgen=0'
    }

    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    if response.status_code != 201:
        print(response.text)
        response.raise_for_status()
    else:
        logger.info(f"Your notebook titled {name} has been generated in your use case (id : {use_case_id})")
        
        return str(json.loads(response.text)['id'])
    # return "66a28de33521dd8d44d020ae"

def schedule_notebook(
        token: str,
        endpoint:str,
        notebook_id: str,
        schedule: Any,
        title: str,
        use_case_id: str,
) -> None:
    import requests
    import json
    from logzero import logger
    import time
    DATAROBOT_HOST = "https://app.datarobot.com/"

    headers = {
            'Authorization': f"Token {token}",
        }
    # Start the notebook session
    start_response = requests.post(
        f'{DATAROBOT_HOST}api-gw/nbx/orchestrator/notebooks/{notebook_id}/start/',
        headers=headers
    )
    assert start_response.status_code == 200, (start_response.status_code, start_response.text)

    # We need to wait for the session to start before executing code (session status of "running")
    for _ in range(120):  # Waiting 2 minutes (120 seconds)
        status_response = requests.get(
            f'{DATAROBOT_HOST}api-gw/nbx/orchestrator/notebooks/{notebook_id}/',
            headers=headers
        )
        assert status_response.status_code == 200, (status_response.status_code, status_response.text)
        if status_response.json()['status'] == 'running':
            break
        time.sleep(1)

    # End the session so that we can schedule the job
    start_response = requests.post(
        f'{DATAROBOT_HOST}api-gw/nbx/orchestrator/notebooks/{notebook_id}/stop/',
        headers=headers
    )
    assert start_response.status_code == 200, (start_response.status_code, start_response.text)

    url = "https://app.datarobot.com/api-gw/nbx/scheduling/"

    payload = json.dumps({
        "useCaseId": use_case_id,
        "notebookId": notebook_id,
        "title": title,
        "enabled": True,
        "schedule": schedule
    })

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {token}',
        'Cookie': 'datarobot_nextgen=0'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code != 201:
        reason = json.loads(response.text)["message"]
        print(reason)
        response.raise_for_status()
    else:
        first_run = json.loads(response.text)["nextRunTime"]
        logger.info(f"Job scheduled to run first: {first_run} (UTC)")


def get_historical_city_data(
        locations: List[Dict[str, float]], 
        parameters: Dict[str, Any]
) -> pd.DataFrame:
    """
    Pull all the video ids from a playlist
    """
    import openmeteo_requests

    import requests_cache
    import pandas as pd
    from retry_requests import retry
    import datetime
    import pytz

    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"

    latitudes = [locations[city]["Latitude"] for city in locations]
    longitudes = [locations[city]["Longitude"] for city in locations]
    city_names = list(locations.keys())

    parameters["past_days"] = 90 # Set to past 3 months to get some historical data.
    parameters["latitude"] = latitudes
    parameters["longitude"] = longitudes

    responses = openmeteo.weather_api(url, params=parameters)

    all_data = []
    for i, response in enumerate(responses):
        # TODO: Log this?
        # print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        # Print city as well
        # print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        # print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")
        

        # Process hourly data. The order of variables needs to be the same as requested.
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()        
        hourly_precipitation_probability = hourly.Variables(1).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(2).ValuesAsNumpy()
        hourly_uv_index = hourly.Variables(3).ValuesAsNumpy()

        timezone = pytz.timezone(response.Timezone())
        timestart = datetime.datetime.fromtimestamp(hourly.Time(), tz=timezone)
        timeend = datetime.datetime.fromtimestamp(hourly.TimeEnd(), tz=timezone)

        hourly_data = {
            "date": pd.date_range(
                        start = timestart,
                        end = timeend,
                        freq = pd.Timedelta(seconds = hourly.Interval()),
                        inclusive = "left"
                    ).strftime('%Y-%m-%d %H:%M:%S'),
            "temperature": hourly_temperature_2m,
            "uv_index": hourly_uv_index,
            "precipitation_probability": hourly_precipitation_probability,
            "precipitation": hourly_precipitation,
            "elevation": response.Elevation(),
            "longitude": response.Latitude(),
            "latitude": response.Longitude(),
            "city": city_names[i]
        }
        all_data.append(pd.DataFrame(data=hourly_data))
        

    hourly_dataframe = pd.concat(all_data, ignore_index=True)
    return hourly_dataframe


def _check_if_dataset_exists(name: str) -> Union[str, None]:
    """
    Check if a dataset with the given name exists in the AI Catalog
    Returns:
        id (string) or None
    """
    datasets = dr.Dataset.list()
    return next((dataset.id for dataset in datasets if dataset.name == name), None)

def update_or_create_timeseries_dataset(
        endpoint: str,
        token: str,
        name: str, 
        data_frame: pd.DataFrame, 
        use_cases: Optional[UseCaseLike] = None,
        **kwargs: Any,
) -> None:
    """
    """
    from datetime import timedelta
    CLIENT = dr.Client(token=token, endpoint=endpoint)
    dataset_token = get_hash(name, data_frame, use_cases, **kwargs)
    dataset_id = _check_if_dataset_exists(name)

    if dataset_id is None:
        dataset: Dataset = Dataset.create_from_in_memory_data(
            data_frame=data_frame, use_cases=use_cases
        )
        dataset.modify(name=f"{name}")
    else:
        current_data = dr.Dataset.get(dataset_id).get_as_dataframe()
        latest_time_pulled = pd.to_datetime(current_data["as_of_datetime"]).max()

        time_pulled_this_df = pd.to_datetime(data_frame["as_of_datetime"]).max()

        # Guard rail to ensure that there is sufficient time between data pulls.
        if abs(latest_time_pulled - time_pulled_this_df) <= timedelta(hours=0.5):
            return name
        else:
            # update dataset if time is greater than 2 hours
            updated_df = pd.concat([current_data, data_frame]).reset_index(drop=True)
            dataset = dr.Dataset.create_version_from_in_memory_data(dataset_id, updated_df)