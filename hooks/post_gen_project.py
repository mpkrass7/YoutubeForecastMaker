# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

import os
import subprocess
import shutil
import stat

import datarobot as dr

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

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
    prediction_server = dr.PredictionServer.list()[0]
    yaml_content['datarobot']['default_prediction_server_id'] = prediction_server.id
except:
    pass

with open(file_path, 'w') as file:
    yaml.dump(yaml_content, file)

print('YAML file updated successfully.')

