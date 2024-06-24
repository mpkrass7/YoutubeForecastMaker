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
import yaml

import datarobot as dr

def remove_readonly(func, path, excinfo):
    """Handle windows permission error.

    https://stackoverflow.com/questions/1889597/deleting-read-only-directory-in-python/1889686#1889686
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)

DATAROBOTX_IDP_VERSION = "{{ cookiecutter.datarobotx_idp_version }}"

print("Copying latest datarobotx-idp source into project..\n")
subprocess.run(
    [
        "git",
        "clone",
        "--branch",
        DATAROBOTX_IDP_VERSION,
        "https://github.com/datarobot-community/datarobotx-idp.git",
    ],
    check=True,
)
shutil.copytree("datarobotx-idp/src/datarobotx", "src/datarobotx")
shutil.rmtree("datarobotx-idp", onerror=remove_readonly)

# Put use case name in the parameters.yml file using default use case id
#   also fill in all dataset names.
# Try, Except clauses to fail gracefully
# Prediction Server ID and Endpoint should get set

usecase_name = dr.UseCase.get(os.environ['DATAROBOT_DEFAULT_USE_CASE']).name

print("Updating parameters.yml")
file_path = 'conf/base/parameters.yml'
with open(file_path, 'r') as file:
    yaml_content = yaml.safe_load(file)

yaml_content['get_data_pipeline']['use_case']['name'] = usecase_name
yaml_content['get_data_pipeline']['timeseries_dataset_name'] = usecase_name + ' Raw Time Series Data'
yaml_content['get_data_pipeline']['metadataset_name'] = usecase_name + ' Meta Data'

yaml_content['preprocessing']['use_case']['name'] = usecase_name
yaml_content['preprocessing']['timeseries_dataset_name'] = usecase_name + ' Raw Time Series Data'
yaml_content['preprocessing']['metadataset_name'] = usecase_name + ' Meta Data'
yaml_content['preprocessing']['modeling_dataset_name'] = usecase_name + ' Modeling Data'
yaml_content['preprocessing']['scoring_dataset_name'] = usecase_name + ' Scoring Data'

yaml_content['deploy_forecast']['use_case']['name'] = usecase_name
yaml_content['deploy_forecast']['dataset_name'] = usecase_name + ' Modeling Data'

yaml_content['deploy_streamlit_app']['scoring_dataset_name'] = usecase_name + ' Scoring Data'

print("Updating credentials.yml")
with open(file_path, 'w') as file:
    yaml.dump(yaml_content, file)

file_path = 'conf/local/credentials.yml'
with open(file_path, 'r') as file:
    yaml_content = yaml.safe_load(file)

try:
    yaml_content['datarobot']['endpoint'] = os.environ['DATAROBOT_ENDPOINT']
except KeyError:
    pass

try:
    prediction_server = dr.PredictionServer.list()[0]
    yaml_content['datarobot']['endpoint'] = prediction_server
except:
    pass

with open(file_path, 'w') as file:
    yaml.dump(yaml_content, file)

print('YAML file updated successfully.')

