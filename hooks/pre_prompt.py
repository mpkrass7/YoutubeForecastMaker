# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

import shutil
import pathlib
import glob

# copy files and templatize key directories
shutil.copytree(
    "YoutubeForecastMaker",
    "{{ cookiecutter.repo_name }}",
    ignore=shutil.ignore_patterns("pyproject.toml", "datarobotx", "data"),
    dirs_exist_ok=True,
)
shutil.move(
    "{{ cookiecutter.repo_name }}/src/YoutubeForecastMaker",
    "{{ cookiecutter.repo_name }}/src/{{ cookiecutter.python_package }}",
)
shutil.move(
    "{{ cookiecutter.repo_name }}/include/YoutubeForecastMaker",
    "{{ cookiecutter.repo_name }}/include/{{ cookiecutter.python_package }}",
)
# templatize conf files
for filename in glob.iglob("{{ cookiecutter.repo_name }}/conf/**/**", recursive=True):
    file = pathlib.Path(filename)
    if file.is_file():
        contents = file.read_text()
        file.write_text(
            file.read_text()
            # .replace("Testing", "{{ cookiecutter.project_name }}") 
            .replace("YoutubeForecastMaker", "{{ cookiecutter.python_package }}")
        )

# add in key files from template repo base dir
shutil.copyfile("README.md", "{{ cookiecutter.repo_name }}/README.md")
shutil.copyfile("LICENSE.txt", "{{ cookiecutter.repo_name }}/LICENSE.txt")
# shutil.move(
#     "{{ cookiecutter.repo_name }}/conf/local/example-credentials.yml",
#     "{{ cookiecutter.repo_name }}/conf/local/credentials.yml",
# )