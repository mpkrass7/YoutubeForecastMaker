# Copyright 2024 DataRobot, Inc. and its affiliates.
# All rights reserved.
# DataRobot, Inc.
# This is proprietary source code of DataRobot, Inc. and its
# affiliates.
# Released under the terms of DataRobot Tool and Utility Agreement.

import shutil

shutil.copyfile('README.md', '{{ cookiecutter.repo_name }}/README.md')
shutil.copyfile('LICENSE.txt', '{{ cookiecutter.repo_name }}/LICENSE.txt')