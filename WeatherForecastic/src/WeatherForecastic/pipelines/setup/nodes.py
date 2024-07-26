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


def _check_if_dataset_exists_in_usecase(
        name: str, 
        use_cases: Optional[UseCaseLike] = None
) -> Union[str, None]:
    """
    Check if a dataset with the given name exists in your use case
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
    **kwargs: Any,
) -> str:
    """Get or create a DR dataset from a dataframe with requested parameters.

    Notes
    -----
    Records a checksum in the dataset name to allow future calls to this
    function to validate whether a desired dataset already exists
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

# Need to add get functionality
def get_or_update_notebook(
        token: str,
        use_case_id: str,
        notebook: Any,
        name: Optional[str] = "scheduled_notebook",
) -> str:
    """
    """
    import requests
    import json
    from io import BytesIO
    from logzero import logger
    import nbformat as nbf

    headers = {
        'Authorization': f"Token {token}",
    }

    url = "https://app.datarobot.com/api-gw/nbx/notebookImport/fromFile/"

    notebook_json = nbf.writes(notebook) #TODO: There may be a cleaner way to do this...
    binary_stream = BytesIO(notebook_json.encode('utf-8')).getvalue()
    
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

def schedule_notebook(
        token: str,
        endpoint:str,
        notebook_id: str,
        schedule: Any,
        title: str,
        use_case_id: str,
) -> None:
    """
    """
    import requests
    import json
    from logzero import logger
    import time
    DATAROBOT_HOST = "https://app.datarobot.com/"

    ####################################################
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
    #################################################### This can all be deleted once Christian's PR goes through.

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

def instantiate_env(
        token: str,
        notebook_id: str,
        **kwargs: Any
) -> None:
    """
    """
    import requests
    import json
    headers = {
        'Authorization': f"Token {token}",
    }
    data = {
        "data":[
            {"name": "locations", "value":json.dumps(kwargs.get("locations")), "description":""},
            {"name": "parameters", "value":json.dumps(kwargs.get("parameters")),"description":""},
            {"name": "modeling_dataset_name", "value":kwargs.get("modeling_dataset_name"),"description":""}
        ]
    }

    response = requests.post(f'https://app.datarobot.com/api-gw/nbx/environmentVariables/{notebook_id}/', json=data, headers=headers)
    # TODO: Assert response status, log message with enviornment variables

def get_historical_city_data(
        locations: List[Dict[str, float]], 
        parameters: Dict[str, Any]
) -> pd.DataFrame:
    """
    Pull all the video ids from a playlist
    """
    import openmeteo_requests

    import pandas as pd
    import datetime
    import pytz

    # Setup the Open-Meteo API client with cache and retry on error
    openmeteo = openmeteo_requests.Client()

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