"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional


# region system variables (values are initialized on package load)
package_dir: Optional[str] = None           # Package folder path
package_name: str = "hydraulic_engine"      # Package name
user_folder_dir: Optional[str] = None       # User folder path for logs and configs

list_configs: List[str] = [                 # List of configuration files
    'init',
    'session',
    'dev',
    'hydraulic_engine',
    'user_params'
]

configs: Dict[str, List[Any]] = {}          # Dictionary of configuration files
                                            # [0] -> Filepath, [1] -> Instance of ConfigParser
configs['init'] = [None, None]              # User configuration file: init.config
configs['session'] = [None, None]           # Session configuration file: session.config
configs['dev'] = [None, None]               # Developer configuration file: dev.config
configs['hydraulic_engine'] = [None, None]  # Package configuration file: hydraulic_engine.config
configs['user_params'] = [None, None]       # Settings configuration file: user_params.config

logger: Optional[Any] = None                  # Instance of HeLogger from "/lib/tools_log.py"
# endregion


# region session variables (may change during execution)
session_vars: Dict[str, Any] = {}
session_vars['last_error'] = None             # Last error instance
session_vars['last_error_msg'] = None         # Last error message
session_vars['threads'] = []                  # List of active threads/tasks
session_vars['db_connection'] = None          # Active database connection
# endregion


# region Init Variables Functions

def init_global(p_package_dir: str, p_package_name: str, p_user_folder_dir: str) -> None:
    """
    Function to initialize the global variables needed to load package

    :param p_package_dir: Path to the package directory
    :param p_package_name: Name of the package
    :param p_user_folder_dir: Path to the user folder for configs and logs
    """
    global package_dir, package_name, user_folder_dir
    package_dir = p_package_dir
    package_name = p_package_name
    user_folder_dir = p_user_folder_dir


def reset_session() -> None:
    """Reset session variables to their initial state"""
    global session_vars
    session_vars['last_error'] = None
    session_vars['last_error_msg'] = None
    session_vars['threads'] = []
    session_vars['db_connection'] = None

# endregion
