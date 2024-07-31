# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

import os
import subprocess
import shutil
from pathlib import Path
import stat

from ruamel.yaml import YAML

yaml = YAML()

def remove_readonly(func, path, excinfo):
    """Handle windows permission error.

    https://stackoverflow.com/questions/1889597/deleting-read-only-directory-in-python/1889686#1889686
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


print("Copying latest datarobotx-idp source into project..\n")
subprocess.run(
    [
        "git",
        "clone",
        "--branch",
        "main",
        "https://github.com/datarobot-community/datarobotx-idp.git",
    ],
    check=True,
)
shutil.copytree("datarobotx-idp/src/datarobotx", "src/datarobotx")
shutil.rmtree("datarobotx-idp", onerror=remove_readonly)

print("Updating credentials.yml")

file_path = 'conf/local/credentials.yml'
with open(file_path, 'r') as file:
    yaml_content = yaml.load(file)

try:
    yaml_content['datarobot']['endpoint'] = os.environ['DATAROBOT_ENDPOINT']
except KeyError:
    pass

try:
    import datarobot as dr
    prediction_server = dr.PredictionServer.list()[0]
    yaml_content['datarobot']['prediction_server_id'] = prediction_server.id
except:
    pass

with open(file_path, 'w') as file:
    yaml.dump(yaml_content, file)

print('YAML file updated successfully.')

# Handle case when kedro new happens in a DataRobot codespace
if "DATAROBOT_DEFAULT_USE_CASE" in os.environ:
    import datarobot as dr

    parameters_yaml = Path("conf/base/parameters.yml")
    use_case = dr.UseCase.get(os.environ["DATAROBOT_DEFAULT_USE_CASE"])

    with open(parameters_yaml, "r") as file:
        yaml_content = yaml.load(file)
        yaml_content["setup"]["use_case"]["name"] = use_case.name
        yaml_content["setup"]["use_case"]["description"] = use_case.description

    with open(parameters_yaml, "w") as file:
        yaml.dump(yaml_content, file, sort_keys=False)