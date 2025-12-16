"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("hydraulic-engine")
except PackageNotFoundError:
    __version__ = "0.1.0"

__author__ = "BGEO"
__email__ = "info@bgeo.es"

from .config import config
from .utils import tools_log

# Export connection functions at package level for convenience
from .utils.tools_db import (
    create_pg_connection,
    create_gpkg_connection,
    create_sqlite_connection,
    get_connection,
    close_connection,
)

# Export SWMM classes for direct access
from .swmm import SwmmRunner, SwmmInpHandler, SwmmRptHandler, SwmmOutHandler, SwmmResultHandler

# Export EPANET classes for direct access
from .epanet import EpanetRunner, EpanetInpHandler, EpanetRptHandler

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "config",
    "tools_log",
    # Connection functions
    "create_pg_connection",
    "create_gpkg_connection",
    "create_sqlite_connection",
    "get_connection",
    "close_connection",
    # SWMM
    "SwmmRunner",
    "SwmmInpHandler",
    "SwmmRptHandler",
    "SwmmOutHandler",
    "SwmmResultHandler",
    # EPANET
    "EpanetRunner",
    "EpanetInpHandler",
    "EpanetRptHandler",
]
