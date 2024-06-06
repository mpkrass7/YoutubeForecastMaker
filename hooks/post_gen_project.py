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
